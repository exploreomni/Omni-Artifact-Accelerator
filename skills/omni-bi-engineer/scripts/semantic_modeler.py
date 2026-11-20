"""Build an offline Omni Topic change set from reviewed, bounded evidence.

The guarded project workflow owns persistence and dispatch. This module accepts
JSON values and returns JSON values. It has no command or provider interface.
"""
import copy
import hashlib
import json
import re


NAME = re.compile(r'[a-z_][a-z0-9_]{0,119}\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')
AGGREGATES = {'sum', 'count', 'count_distinct', 'average', 'min', 'max'}
MAX_BYTES = 8 * 1024 * 1024


class SpecError(ValueError):
    def __init__(self, code, path):
        super().__init__(code)
        self.code = code
        self.path = path


def require(condition, code, path):
    if not condition:
        raise SpecError(code, path)


def shape(value, required, optional, path):
    require(isinstance(value, dict) and required <= value.keys(), 'missing_or_invalid_object', path)
    require(value.keys() <= required | optional, 'unsupported_property', path)
    return value


def array(value, path):
    require(type(value) is list and len(value) <= 5000, 'invalid_or_oversized_list', path)
    return value


def string(value, path):
    require(type(value) is str and value.strip() and len(value) <= 2048 and
            all(ord(char) >= 32 and not 0xD800 <= ord(char) <= 0xDFFF for char in value), 'invalid_text', path)
    return value


def name(value, path):
    require(type(value) is str and NAME.fullmatch(value), 'unsupported_identifier', path)
    return value


def names(value, path):
    result = [name(item, path) for item in array(value, path)]
    require(len(result) == len(set(result)), 'duplicate_identifier', path)
    return result


def field(value, path):
    parts = string(value, path).split('.')
    require(len(parts) == 2 and all(NAME.fullmatch(part) for part in parts), 'expected_view_field', path)
    return tuple(parts)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=True)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def yaml_text(obj):
    """YAML block keys with quoted scalars and indented JSON flow collections."""
    output = []
    for key, value in obj.items():
        flow = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2)
        if '\n' in flow:
            output.append(key + ':\n' + ''.join('  ' + line + '\n' for line in flow.splitlines()))
        else:
            output.append(key + ': ' + flow + '\n')
    return ''.join(output)


def unique_keys(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError('duplicate key')
    return obj


def reject_constant(_):
    raise ValueError('nonfinite number')


def yaml_subset(raw):
    require(type(raw) is str and 0 < len(raw) <= MAX_BYTES, 'topic_bytes_unavailable', 'baseline.topic_files')
    decoded, sections = {}, []
    lines = iter(raw.splitlines(keepends=True))
    current = next(lines, None)
    while current is not None:
        if not current.strip() or current.startswith('#'):
            sections.append((None, current))
            current = next(lines, None)
            continue
        key, separator, value = current.rstrip('\r\n').partition(':')
        require(separator and NAME.fullmatch(key) and key not in decoded,
                'existing_yaml_requires_reviewed_manual_merge', 'baseline.topic_files')
        block = [current]
        current = next(lines, None)
        while current is not None and current.startswith('  '):
            block.append(current)
            current = next(lines, None)
        try:
            decoded[key] = json.loads(value + '\n' + ''.join(block[1:]), object_pairs_hook=unique_keys, parse_constant=reject_constant)
        except (ValueError, RecursionError):
            raise SpecError('existing_yaml_requires_reviewed_manual_merge', 'baseline.topic_files') from None
        sections.append((key, ''.join(block)))
    return decoded, sections


def _native_scalar(value):
    """Decode the scalar/short flow forms observed in native Topic readbacks."""
    if value.startswith(("'", '"', '[', '{')) or value in ('true', 'false', 'null') or re.match(r'^[-+]?\d', value):
        if value.startswith("'"):
            if not re.fullmatch(r"'(?:[^']|'')*'", value):
                raise ValueError('unsupported quoted value')
            return value[1:-1].replace("''", "'")
        try:
            return json.loads(value, object_pairs_hook=unique_keys, parse_constant=reject_constant)
        except ValueError:
            # Omni can format simple identifier lists as [ name, view.field ].
            if re.fullmatch(r'\[\s*[a-z_][a-z0-9_.]*(?:\s*,\s*[a-z_][a-z0-9_.]*)*\s*\]', value):
                return [_native_scalar(token.strip()) for token in value[1:-1].split(',')]
            raise
    if (not value or value[0] in '-?:,]}#&*!|>%@`' or ' #' in value or ': ' in value
            or value.endswith(':') or value.casefold() in {'~', 'yes', 'no', 'on', 'off', 'null', 'true', 'false',
                                                          '.nan', '.inf', '-.inf', '+.inf'}):
        raise ValueError('ambiguous scalar')
    return value


_NATIVE_KEY = re.compile(r'([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)?):(?: +(.*))?\Z')


def _native_tokens(text):
    text = text.replace('\r\n', '\n')
    if any((ord(c) < 32 and c != '\n') or c in ('\x85', '\u2028', '\u2029') for c in text):
        raise ValueError('unsupported YAML character')
    lines = text.splitlines(keepends=True)
    if len(lines) > 50000:
        raise ValueError('unsupported YAML whitespace')
    i, tokens = 0, []
    while i < len(lines):
        line = lines[i].rstrip('\n'); line_no = i; i += 1
        indent = len(line) - len(line.lstrip(' ')); body = line[indent:].rstrip(' ')
        if not body or body.startswith('#'):
            continue
        member = _NATIVE_KEY.fullmatch(body)
        if (member and not member[2] and i < len(lines) and lines[i].strip() == '[' and
                len(lines[i]) - len(lines[i].lstrip(' ')) > indent):
            width = len(lines[i]) - len(lines[i].lstrip(' '))
            i += 1
            pieces = []
            while i < len(lines) and len(lines[i]) - len(lines[i].lstrip(' ')) > width:
                pieces.append(lines[i].strip()); i += 1
            if i >= len(lines) or lines[i].rstrip('\n').rstrip(' ') != ' ' * width + ']':
                raise ValueError('unterminated native flow sequence')
            i += 1
            body = member[1] + ': [ ' + ' '.join(pieces) + ' ]'
        elif member and member[2] in ('|', '|-'):
            contents = []
            while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip(' ')) > indent):
                contents.append(lines[i]); i += 1
            first = next((s for s in contents if s.strip()), None)
            width = len(first) - len(first.lstrip(' ')) if first else indent + 1
            if any(s.strip() and not s.startswith(' ' * width) for s in contents):
                raise ValueError('unsupported literal indentation')
            literal = ''.join(s[width:] if s.strip() else s.lstrip(' ') for s in contents)
            if member[2] == '|-':
                literal = literal.rstrip('\n')
            elif literal.endswith('\n'):
                literal = literal.rstrip('\n') + '\n' if literal.strip('\n') else ''
            body = member[1] + ': ' + json.dumps(literal)
        if body.startswith('- ') and _NATIVE_KEY.fullmatch(body[2:]):
            tokens.append((indent, '-', line_no))
            tokens.append((indent + 2, body[2:], line_no))
        else:
            tokens.append((indent, body, line_no))
    return tokens


def _native_document(text):
    if text.lstrip().startswith('{'):
        return json.loads(text, object_pairs_hook=unique_keys, parse_constant=reject_constant)
    tokens = _native_tokens(text)
    def parse(i, depth, level):
        if level > 24 or i >= len(tokens) or tokens[i][0] != depth:
            raise ValueError('unexpected YAML indentation')
        sequence = tokens[i][1] == '-' or tokens[i][1].startswith('- ')
        result = [] if sequence else {}
        while i < len(tokens) and tokens[i][0] == depth:
            _, line, last = tokens[i]
            if (line == '-' or line.startswith('- ')) != sequence:
                break
            if sequence:
                key, rest = None, line[1:].lstrip(' ')
            else:
                m = _NATIVE_KEY.fullmatch(line)
                if not m or m[1] in result:
                    raise ValueError('unsupported or duplicate YAML key')
                key, rest = m[1], m[2] or ''
            i += 1
            if rest:
                # Native formatting sometimes wraps a long plain SQL or prose value.
                while i < len(tokens) and tokens[i][0] > depth:
                    extra = tokens[i][1]
                    if (key not in ('description', 'label', 'on_sql', 'sql') or rest.startswith(('"', "'", '[', '{'))
                            or tokens[i][2] != last + 1 or _NATIVE_KEY.fullmatch(extra) or extra.startswith(('#', '- ', '&', '*', '!'))):
                        raise ValueError('unsupported YAML continuation')
                    rest += ' ' + extra
                    last = tokens[i][2]; i += 1
                value = _native_scalar(rest)
            else:
                if i >= len(tokens) or tokens[i][0] <= depth and not (
                        not sequence and tokens[i][0] == depth and tokens[i][1].startswith('-')):
                    raise ValueError('missing YAML value')
                value, i = parse(i, tokens[i][0], level + 1)
            if sequence:
                result.append(value)
            else:
                result[key] = value
        return result, i
    result, end = parse(0, 0, 0)
    if end != len(tokens):
        raise ValueError('trailing YAML content')
    return result


def matches_readback(expected_text, actual_text):
    """Check a generated Topic against full native file text, without executing YAML.

    Fast-path exact bytes; otherwise restrict parsing to native block/flow forms
    and compare the complete typed tree. A single literal-block terminator in
    a description is presentation-only. SQL, filters, grants and lists are exact.
    """
    if not all(type(value) is str and 0 < len(value) <= MAX_BYTES for value in (expected_text, actual_text)):
        return False
    if expected_text == actual_text:
        return True
    try:
        expected, _ = yaml_subset(expected_text)
        if not isinstance(expected.get('base_view'), str) or not isinstance(expected.get('fields'), list):
            return False
        try:
            actual, _ = yaml_subset(actual_text)
        except ValueError:
            actual = _native_document(actual_text)
        def comparable(value, key=None):
            if isinstance(value, dict):
                return {k: comparable(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [comparable(v) for v in value]
            if key == 'description' and isinstance(value, str) and value.endswith('\n'):
                return value[:-1]
            return value
        return canonical(comparable(expected)) == canonical(comparable(actual))
    except (ValueError, TypeError, RecursionError, UnicodeError):
        return False


def topic_path(path, topic):
    parts = string(path, 'topic.path').split('/')
    require(all(NAME.fullmatch(part) for part in parts[:-1]) and
            parts[-1] in {topic + ext for ext in ('.topic', '.topic.yaml', '.topic.yml')},
            'invalid_topic_filename', 'topic.path')
    return path


def baseline_inputs(baseline):
    shape(baseline, {'model_id', 'branch_id', 'evidence_ref', 'topic_names', 'views', 'user_attributes', 'access_grants'},
          {'topic_files', 'model_version_id', 'relationships'}, 'baseline')
    for key in ('model_id', 'branch_id', 'evidence_ref'):
        string(baseline[key], 'baseline.' + key)
    if 'model_version_id' in baseline:
        string(baseline['model_version_id'], 'baseline.model_version_id')
    names(baseline['topic_names'], 'baseline.topic_names')
    names(baseline['user_attributes'], 'baseline.user_attributes')
    names(baseline['access_grants'], 'baseline.access_grants')
    views = baseline['views']
    require(isinstance(views, dict) and 0 < len(views) <= 5000, 'physical_views_required', 'baseline.views')
    dimensions, measures = set(), set()
    for view, entry in views.items():
        name(view, 'baseline.views')
        shape(entry, {'physical_binding', 'dimensions', 'measures'}, set(), 'baseline.views.' + view)
        string(entry['physical_binding'], 'baseline.views.' + view + '.physical_binding')
        dims = names(entry['dimensions'], 'baseline.views.' + view + '.dimensions')
        mets = names(entry['measures'], 'baseline.views.' + view + '.measures')
        require(not set(dims).intersection(mets), 'field_name_collision', 'baseline.views.' + view)
        dimensions.update(view + '.' + item for item in dims)
        measures.update(view + '.' + item for item in mets)
    return dimensions, measures


def join_definitions(rows, base, dimensions, baseline):
    joins, relationships = {}, []
    scope = {base}
    observed = {}
    if rows:
        for entry in array(baseline.get('relationships'), 'baseline.relationships'):
            shape(entry, {'from_field', 'to_field', 'join_type', 'relationship_type'}, set(), 'baseline.relationships')
            pair = frozenset((field(entry['from_field'], 'baseline.relationships')[0],
                              field(entry['to_field'], 'baseline.relationships')[0]))
            observed.setdefault(pair, []).append(entry)
    for i, row in enumerate(array(rows, 'joins')):
        path = 'joins.' + str(i)
        shape(row, {'from_field', 'to_field', 'join_type', 'relationship_type', 'review_ref'}, set(), path)
        left = field(row['from_field'], path)[0]
        right = field(row['to_field'], path)[0]
        require(left == base and right not in scope, 'unsupported_or_ambiguous_join_path', path)
        require(row['from_field'] in dimensions and row['to_field'] in dimensions, 'join_operand_unresolved', path)
        require(row['join_type'] in ('left', 'inner', 'always_left') and
                row['relationship_type'] in ('many_to_one', 'one_to_one'), 'unsupported_join_semantics', path)
        string(row['review_ref'], path + '.review_ref')
        scope.add(right)
        joins[right] = {}
        matching = observed.get(frozenset((left, right)), [])
        if matching:
            require(len(matching) == 1 and all(row[k] == v for k, v in matching[0].items()),
                    'relationship_conflicts_with_baseline', path)
        else:
            relationships.append({'join_from_view': left, 'join_to_view': right, 'join_type': row['join_type'],
                                  'relationship_type': row['relationship_type'],
                                  'on_sql': '${' + row['from_field'] + '} = ${' + row['to_field'] + '}'})
    return joins, relationships, scope


def literal_filters(filters, dimensions, scope, path):
    require(isinstance(filters, dict) and len(filters) <= 100, 'invalid_filter_map', path)
    result = {}
    for identifier, condition in filters.items():
        view = field(identifier, path)[0]
        require(identifier in dimensions and view in scope, 'filter_field_unresolved', path)
        shape(condition, {'is'}, set(), path)
        value = condition['is']
        require(value is None or type(value) in (bool, int, float, str), 'literal_filter_required', path)
        if isinstance(value, str):
            string(value, path)
            require('{{' not in value and '${' not in value, 'dynamic_filter_unsupported', path)
        result[identifier] = {'is': value}
    return result


def measure_definitions(rows, dimensions, existing, scope):
    overrides, generated = {}, set()
    for i, row in enumerate(array(rows, 'measures')):
        path = 'measures.' + str(i)
        shape(row, {'view', 'name', 'field', 'aggregate_type', 'review_ref'}, {'label', 'description', 'filters'}, path)
        view = name(row['view'], path)
        member = name(row['name'], path)
        identity = view + '.' + member
        require(view in scope and row['field'] in dimensions and field(row['field'], path)[0] == view,
                'measure_operand_unresolved', path)
        require(type(row['aggregate_type']) is str and row['aggregate_type'] in AGGREGATES,
                'unsupported_measure_aggregation', path)
        require(identity not in existing | dimensions | generated, 'measure_name_collision', path)
        string(row['review_ref'], path + '.review_ref')
        definition = {'sql': '${' + row['field'] + '}', 'aggregate_type': row['aggregate_type']}
        if 'filters' in row:
            definition['filters'] = literal_filters(row['filters'], dimensions, {view}, path + '.filters')
        for key in ('label', 'description'):
            if key in row:
                definition[key] = string(row[key], path + '.' + key)
        overrides.setdefault(view, {'measures': {}})['measures'][member] = definition
        generated.add(identity)
    return overrides, generated


def reviewed_policy(policy, baseline, dimensions, scope):
    shape(policy, {'review_ref', 'access_filters', 'required_access_grants'}, {'always_where_filters'}, 'policy')
    string(policy['review_ref'], 'policy.review_ref')
    filters = []
    for row in array(policy['access_filters'], 'policy.access_filters'):
        shape(row, {'field', 'user_attribute'}, set(), 'policy.access_filters')
        view = field(row['field'], 'policy.access_filters')[0]
        attr = name(row['user_attribute'], 'policy.access_filters')
        require(view in scope and row['field'] in dimensions and attr in baseline['user_attributes'],
                'access_binding_unresolved', 'policy.access_filters')
        require(row not in filters, 'duplicate_access_filter', 'policy.access_filters')
        filters.append(dict(row))
    grants = names(policy['required_access_grants'], 'policy.required_access_grants')
    require(set(grants) <= set(baseline['access_grants']), 'access_grant_unresolved', 'policy.required_access_grants')
    return {'access_filters': filters, 'required_access_grants': grants,
            'always_where_filters': literal_filters(policy.get('always_where_filters', {}), dimensions, scope, 'policy.always_where_filters')}


def topic_document(spec):
    baseline, topic = spec['baseline'], spec['topic']
    dimensions, existing = baseline_inputs(baseline)
    shape(topic, {'name', 'base_view', 'label', 'fields'}, {'path', 'description'}, 'topic')
    topic_name = name(topic['name'], 'topic.name')
    base = name(topic['base_view'], 'topic.base_view')
    require(base in baseline['views'], 'base_view_unresolved', 'topic.base_view')
    path = topic_path(topic.get('path', topic_name + '.topic'), topic_name)
    joins, relationships, scope = join_definitions(spec.get('joins', []), base, dimensions, baseline)
    overrides, generated = measure_definitions(spec.get('measures', []), dimensions, existing, scope)
    targets = {f for f in dimensions | existing | generated if f.split('.')[0] in scope}
    fields = array(topic['fields'], 'topic.fields')
    for identifier in fields:
        field(identifier, 'topic.fields')
        require(identifier in targets, 'selected_field_unresolved', 'topic.fields')
    require(fields and len(fields) == len(set(fields)), 'unique_explicit_fields_required', 'topic.fields')
    document = {'base_view': base, 'label': string(topic['label'], 'topic.label')}
    if 'description' in topic:
        document['description'] = string(topic['description'], 'topic.description')
    document.update({'joins': joins, 'fields': fields})
    if relationships:
        document['relationships'] = relationships
    if overrides:
        document['views'] = overrides
    policies = reviewed_policy(spec['policy'], baseline, dimensions, scope)
    document.update({k: v for k, v in policies.items() if v})
    mapping_targets = set(fields) | generated | {topic_name}
    mapping_targets.update('relationship:' + base + '->' + child for child in joins)
    mapping_targets.update('access_filter:' + row['field'] + ':' + row['user_attribute'] for row in policies['access_filters'])
    mapping_targets.update('required_access_grant:' + grant for grant in policies['required_access_grants'])
    mapping_targets.update('population_filter:' + identifier for identifier in policies['always_where_filters'])
    return path, document, mapping_targets


def plan_change(spec, path, document):
    baseline = spec['baseline']
    files = baseline.get('topic_files', {})
    require(isinstance(files, dict) and all(isinstance(key, str) for key in files), 'invalid_file_inventory', 'baseline.topic_files')
    topic = spec['topic']['name']
    aliases = [key for key in files if key.rsplit('/', 1)[-1] in (topic + '.topic', topic + '.topic.yml', topic + '.topic.yaml')]
    update = spec.get('update')
    if update is None:
        require(topic not in baseline['topic_names'] and not aliases, 'topic_name_collision', 'topic.name')
        return yaml_text(document), None
    shape(update, {'expected_sha256', 'review_ref'}, set(), 'update')
    string(update['review_ref'], 'update.review_ref')
    require(topic in baseline['topic_names'] and aliases == [path], 'update_baseline_missing_or_ambiguous', 'update')
    old = files[path]
    require(type(old) is str and sha(old) == update['expected_sha256'], 'update_baseline_hash_mismatch', 'update')
    original, sections = yaml_subset(old)
    # A complete desired definition is required. Policy, inherited behavior and
    # unmentioned keys stay intact. New members can only extend existing lists/maps.
    require(original.get('base_view') == document['base_view'], 'base_view_change_unsupported', 'update')
    require(type(original.get('fields')) is list and original['fields'] and type(original.get('joins')) is dict,
            'implicit_topic_scope_requires_manual_merge', 'update')
    require(set(original) <= {'base_view', 'label', 'description', 'joins', 'fields', 'relationships', 'views',
                              'access_filters', 'required_access_grants', 'always_where_filters'}, 'existing_semantics_require_manual_merge', 'update')
    require(original.keys() <= document.keys(), 'existing_topic_properties_omitted', 'update')
    for key in ('access_filters', 'required_access_grants', 'always_where_filters'):
        require(original.get(key, []) == document.get(key, []), 'existing_policy_change_requires_manual_review', 'update')
    def retains(before, after):
        if isinstance(before, dict):
            return isinstance(after, dict) and all(k in after and retains(v, after[k]) for k, v in before.items())
        if isinstance(before, list):
            return isinstance(after, list) and before == after[:len(before)]
        return type(before) is type(after) and before == after
    require(all(retains(before, document[key]) for key, before in original.items()), 'non_additive_topic_change', 'update')
    # Keep original lines, comments, and newline style for untouched properties.
    newline = '\r\n' if '\r\n' in old else '\n'
    changed = {k for k, v in document.items() if original.get(k) != v}
    result = []
    for key, block in sections:
        result.append(yaml_text({key: document[key]}).replace('\n', newline) if key in changed else block)
    additions = {k: v for k, v in document.items() if k not in original}
    if additions:
        if result and not result[-1].endswith('\n'):
            result.append(newline)
        result.append(yaml_text(additions).replace('\n', newline))
    return ''.join(result), old


def source_crosswalk(spec, targets, gaps):
    inventory = spec.get('source_inventory')
    rows = array(spec.get('source_bindings', []), 'source_bindings')
    if inventory is None:
        require(not rows, 'source_inventory_required', 'source_bindings')
        return []
    require(isinstance(inventory, dict) and inventory.get('kind') == 'omni_analyst_source_inventory' and
            type(inventory.get('schema_version')) is int and inventory['schema_version'] == 1,
            'expected_oaa_source_inventory', 'source_inventory')
    source = inventory.get('source')
    require(isinstance(source, dict) and type(source.get('input_sha256')) is str and SHA.fullmatch(source['input_sha256']),
            'adapter_input_pin_required', 'source_inventory.source')
    require('upstream_payload' in inventory and source.get('payload_sha256') == sha(canonical(inventory['upstream_payload'])),
            'adapter_upstream_payload_changed', 'source_inventory.upstream_payload')
    platform = string(source.get('platform'), 'source_inventory.source.platform')
    assets = array(inventory.get('assets'), 'source_inventory.assets')
    originals = None
    if source.get('format') == 'declared_normalized_inventory':
        upstream = inventory['upstream_payload']
        originals = upstream.get('assets') if isinstance(upstream, dict) else None
        require(type(originals) is list and len(originals) == len(assets) and upstream.get('platform') == platform,
                'adapter_inventory_original_mismatch', 'source_inventory.assets')
    for item in array(inventory.get('gaps', []), 'source_inventory.gaps'):
        require(isinstance(item, dict), 'invalid_adapter_gap', 'source_inventory.gaps')
        code = string(item.get('code'), 'source_inventory.gaps.code')
        location = item.get('source_path', '')
        if location != '':
            string(location, 'source_inventory.gaps.source_path')
        gaps.append({'code': 'source_adapter_gap', 'source_code': code, 'path': location, 'blocking': False})
    bindings, crosswalk, seen = {}, [], set()
    for row in rows:
        shape(row, {'asset_key', 'target', 'review_ref', 'semantics'}, set(), 'source_bindings')
        for key in row:
            string(row[key], 'source_bindings.' + key)
        require(row['asset_key'] not in bindings, 'ambiguous_source_mapping', 'source_bindings')
        bindings[row['asset_key']] = row
    for asset in assets:
        require(isinstance(asset, dict), 'invalid_source_asset', 'source_inventory.assets')
        key = string(asset.get('asset_key'), 'source_inventory.assets.asset_key')
        require(key not in seen, 'duplicate_adapter_asset', 'source_inventory.assets')
        seen.add(key)
        source_id = asset.get('source_id')
        if source_id is not None:
            string(source_id, 'source_inventory.assets.source_id')
        location = asset.get('source_path')
        if location != '':
            string(location, 'source_inventory.assets.source_path')
        fingerprint = asset.get('source_payload_sha256')
        require('source_payload' in asset and fingerprint == sha(canonical(asset['source_payload'])),
                'adapter_asset_payload_changed', 'source_inventory.assets')
        identity = asset.get('source_identity')
        require(isinstance(identity, dict) and 'raw_id' in identity and
                (str(identity['raw_id']) if identity['raw_id'] is not None else None) == source_id,
                'adapter_source_identity_changed', 'source_inventory.assets')
        if originals is not None:
            locator = re.fullmatch(r'/assets/(0|[1-9][0-9]{0,5})', location)
            require(type(asset['source_payload']) is dict and locator and int(locator[1]) < len(originals) and
                    canonical(originals[int(locator[1])]) == canonical(asset['source_payload']) and
                    asset['source_payload'].get('source_id') == identity['raw_id'] and
                    asset.get('kind') == asset['source_payload'].get('kind') and
                    identity.get('scope') == asset['source_payload'].get('scope') and
                    key == 'asset:' + sha(canonical([platform, asset['kind'], location]))[:24],
                    'adapter_asset_original_mismatch', 'source_inventory.assets')
        row = {'platform': platform, 'input_sha256': source['input_sha256'], 'asset_key': key, 'source_id': source_id,
               'source_path': location, 'source_payload_sha256': fingerprint, 'status': 'unresolved'}
        row.update({k: copy.deepcopy(identity[k]) for k in ('id_kind', 'scope') if k in identity})
        id_kind = identity.get('id_kind')
        observed = id_kind in {'native_id', 'scoped_native_id', 'supplier_declared_id', 'lookml_declared_name',
                               'independent_inventory_key', 'independently_enumerated_source_key', 'source_file', 'supplied_path'}
        if id_kind == 'adapter_generated_id' and identity.get('native_id') is not None:
            observed = True
            row['native_source_id'] = identity['native_id']
        if identity.get('definition_state') not in (None, 'definition_complete'):
            observed = False
        binding = bindings.get(key)
        evidence = asset['source_payload'].get('facets', {}) if originals is not None else asset.get('facets', {})
        supported = set()
        if isinstance(evidence, dict):
            supported = {k for k, v in evidence.items() if isinstance(v, dict) and
                         v.get('status') in ('observed', 'declared') and v.get('value') is not None}
        wanted = {'query'}
        if binding:
            target = binding['target']
            if target.startswith(('access_filter:', 'required_access_grant:')):
                wanted = {'security'}
            elif target.startswith('population_filter:'):
                wanted = {'filters', 'query'}
            elif isinstance(spec.get('topic'), dict) and target == spec['topic'].get('name'):
                wanted = {'query', 'content'}
        if binding and source_id is not None and observed and binding['target'] in targets and wanted & supported:
            row.update(status='reviewed_mapping', target=binding['target'], semantics=binding['semantics'], review_ref=binding['review_ref'])
        else:
            if binding:
                row['proposed_mapping'] = copy.deepcopy(binding)
            gaps.append({'code': 'source_mapping_unresolved', 'path': key, 'blocking': False})
        crosswalk.append(row)
    require(bindings.keys() <= seen, 'unknown_adapter_asset_key', 'source_bindings')
    return crosswalk


def build_candidate(spec):
    """Return candidate YAML + guarded inverse, or a blocked result with no files."""
    result = {'schema_version': 1, 'kind': 'oaa_semantic_model_candidate', 'status': 'blocked',
              'files': {}, 'changes': [], 'rollback': [], 'crosswalk': [], 'gaps': [], 'candidate_sha256': None,
              'native_verified': False, 'authorizes_target_write': False}
    try:
        encoded = canonical(spec)
        require(len(encoded) <= MAX_BYTES, 'spec_too_large', 'spec')
        shape(spec, {'schema_version', 'baseline', 'topic', 'policy'},
              {'measures', 'joins', 'source_inventory', 'source_bindings', 'update'}, 'spec')
        require(type(spec['schema_version']) is int and spec['schema_version'] == 1, 'unsupported_spec_version', 'schema_version')
        try:
            path, document, targets = topic_document(spec)
        except SpecError:
            # A blocked target does not erase the reviewed source denominator.
            result['crosswalk'] = source_crosswalk(spec, set(), result['gaps'])
            raise
        result['crosswalk'] = source_crosswalk(spec, targets, result['gaps'])
        if spec.get('source_inventory') is not None:
            require(any(row['status'] == 'reviewed_mapping' for row in result['crosswalk']),
                    'reviewed_source_mapping_required', 'source_bindings')
        native, old = plan_change(spec, path, document)
        change = 'create' if old is None else ('unchanged' if old == native else 'update')
        after, before = sha(native), None if old is None else sha(old)
        scope = {key: spec['baseline'][key] for key in ('model_id', 'branch_id', 'model_version_id', 'evidence_ref') if key in spec['baseline']}
        changes = [] if change == 'unchanged' else [{'path': path, 'operation': change, 'expected_sha256': before, 'sha256': after}]
        rollback = [] if not changes else [{'path': path, 'operation': 'remove_created' if old is None else 'restore_exact',
                                            'expected_sha256': after, 'restore_text': old}]
        result.update(status='candidate', files={path: native}, changes=changes, rollback=rollback,
                      topic_name=spec['topic']['name'], base_view=document['base_view'],
                      destination=scope, spec_sha256=sha(encoded))
        result['candidate_sha256'] = sha(canonical({'destination': scope, 'spec_sha256': result['spec_sha256'],
                                                    'files': result['files'], 'changes': changes}))
        for code in ('native_model_validation_pending', 'independent_query_comparison_pending', 'effective_access_unverified'):
            result['gaps'].append({'code': code, 'path': path, 'blocking': False})
    except SpecError as exc:
        result['gaps'].append({'code': exc.code, 'path': exc.path, 'blocking': True})
    except (TypeError, ValueError, RecursionError, UnicodeError):
        result['gaps'].append({'code': 'invalid_json_value', 'path': 'spec', 'blocking': True})
    return result
