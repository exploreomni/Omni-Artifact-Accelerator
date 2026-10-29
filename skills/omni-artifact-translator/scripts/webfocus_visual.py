"""Passive WebFOCUS semantic/visual evidence bridge; no vendor runtime imports.

The DMA report is a bounded declaration contract, not a visual denominator.
Literal GRAPH/STYLE/GRAPH_JS recognition preserves source order and opaque gaps;
it never executes FEX, Dialogue Manager, JavaScript or follows an include/URL.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata


def module(name):
    spec = importlib.util.spec_from_file_location('webfocus_' + name, Path(__file__).with_name(name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


F = module('powerbi_capture_files')
DMA_REVISION = 'fcec34fb8e83bf7b663ab5ed0e1e945224dd03fd'
PRIVATE_REVISION = 'c513474e87af9c2c31deebd2ae675c8602955203'
_COMMON = {
    'scripts/source_adapters/webfocus.py': '77ec8294c52c2dfdc54e209ed81c17bbfac28440c573626446d3ecc5408bf0a4',
    'scripts/source_adapters/sql.py': '7a62123fc5c11e29c31f4e21fddeef2afccb5ec2d82a730eefa1adc062ba09c5',
    'references/source-adapters/webfocus.md': '11b757e2e3aad49e23f240f8a673db1fac4cce0be5aad6793937d624ebbe099a'}
PRODUCERS = {
    DMA_REVISION: {**_COMMON,
        'scripts/source_adapters/base.py': '21509c6403e64ea3218373fc6291d1074800ada543d635a473032d231d6a1e67',
        'scripts/source_adapters/registry.py': '9d6b9b53b77d9fa263bcea194d07014f9084df88040bff870baff50e654f2f06',
        'scripts/source_adapters/errors.py': '6505fb092376641cf97f13c45665b3c23ea9d9ce1af3f98030542c499d37b9c6'},
    PRIVATE_REVISION: {**_COMMON,
        'scripts/source_adapters/base.py': 'e848c873c2e5718c8c9ff284197cc9c615da5ad2176deea966d51c4bcf98debb',
        'scripts/source_adapters/registry.py': 'd204e5b05dbae983e71d62790b2be5126ad4766288bbd3ee2088e9764f690186'}}
MAX_ITEMS = 5000
MAX_FEX_UNITS = 800
MAX_FEX_CHARS = 32768
SHA = re.compile(r'[a-f0-9]{64}\Z')


def need(value, code):
    if not value:
        raise ValueError('webfocus.' + code)


def text(value):
    return type(value) is str and 0 < len(value) <= 10000


def encoded(value):
    return F.encoded(value)


def sha(value):
    return F.raw_sha(value) if type(value) is bytes else F.sha(value)


def digest(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _source_path(value):
    F.source_path(value)
    need(bool(PurePosixPath(value).parts), 'source_path')
    return value


def _secret_check(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, val in item.items():
                if re.sub('[^a-z]', '', key.lower()) in {
                    'authorization', 'password', 'passwd', 'clientsecret', 'accesstoken', 'refreshtoken',
                    'apikey', 'apitoken', 'privatekey', 'credentials'}:
                    need(val in (None, '', '[REDACTED]') or val == {'redacted': 'secret'}, 'credential_bearing_input')
                stack.append(val)
        elif type(item) is list:
            stack.extend(item)


def _generated_id(category, path, locator, value):
    # Exact producer JSON encoding, distinct from this bridge's canonical JSON.
    material = json.dumps([path, locator, str(value)], ensure_ascii=True).encode()
    return 'webfocus:' + category + ':' + hashlib.sha256(material).hexdigest()[:24]


def validate(value, revision):
    """Validate supplied contract structure; neither producer nor signer authentication."""
    need(revision in PRODUCERS, 'unsupported_or_missing_producer_revision')
    F.decode(encoded(value))
    required = {'schema_version', 'kind', 'source', 'adapter_version', 'source_files', 'coverage_summary',
                'objects', 'expressions', 'dependencies', 'gaps', 'export_completeness', 'native_validation',
                'execution_performed', 'limitations'}
    need(type(value) is dict and required <= set(value) <= required | {'component_sha256'}
         and type(value['schema_version']) is int and value['schema_version'] == 1
         and type(value['adapter_version']) is int and value['adapter_version'] == 1
         and value['kind'] == 'source_adapter_result' and value['source'] == 'webfocus', 'adapter_contract')
    need(value['execution_performed'] is False and value['native_validation'] == 'not_run'
         and value['export_completeness'] == 'not_established', 'unsupported_execution_or_acceptance_claim')
    if 'component_sha256' in value:
        need(digest(value['component_sha256']), 'component_hash')
    _secret_check(value)
    for key in ('source_files', 'objects', 'expressions', 'dependencies', 'gaps', 'limitations'):
        need(type(value[key]) is list and len(value[key]) <= MAX_ITEMS, 'bounded_collection')
    need(len(value['source_files']) <= 512 and all(text(x) for x in value['limitations']), 'file_or_limitations_contract')
    files, normalized = {}, {}
    for row in value['source_files']:
        need(type(row) is dict and set(row) == {'path', 'sha256', 'status', 'reason'}, 'file_record')
        path = _source_path(row['path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in normalized and not any(folded.startswith(p + '/') or p.startswith(folded + '/')
             for p in normalized), 'source_path_collision')
        # Also reject different spellings of shared directory prefixes.
        for previous in files:
            for a, b in zip(PurePosixPath(path).parts, PurePosixPath(previous).parts):
                if unicodedata.normalize('NFC', a).casefold() != unicodedata.normalize('NFC', b).casefold():
                    break
                need(a == b, 'source_path_collision')
        normalized[folded] = path
        need(digest(row['sha256']) and row['status'] in ('parsed', 'partial', 'unsupported')
             and type(row['reason']) is str, 'file_evidence')
        files[path] = row
    expected = {'unit': 'supplied_source_files', 'expected': len(files), 'observed': len(files), 'missing': 0,
        'statuses': {s: sum(f['status'] == s for f in files.values()) for s in ('parsed', 'partial', 'unsupported')}}
    need(value['coverage_summary'] == expected and all(type(value['coverage_summary'][k]) is int
         for k in ('expected', 'observed', 'missing')) and all(type(n) is int
         for n in value['coverage_summary']['statuses'].values()), 'coverage_mismatch')
    objects, ids, full_source = {}, set(), {}
    for category in ('objects', 'expressions', 'dependencies', 'gaps'):
        ordinals = {}
        for row in value[category]:
            need(type(row) is dict, 'record_shape')
            e = row.get('evidence')
            need(type(e) is dict and set(e) == {'path', 'locator', 'sha256'}
                 and e['path'] in files and text(e['locator']) and e['sha256'] == files[e['path']]['sha256'], 'evidence_mismatch')
            position = (e['path'], e['locator'])
            ordinal = ordinals.get(position, 0)
            material = json.dumps([category, *position, ordinal], ensure_ascii=True).encode()
            expected_id = 'webfocus:occurrence:' + hashlib.sha256(material).hexdigest()[:24]
            need(row.get('occurrence_id') == expected_id, 'occurrence_binding_mismatch')
            ordinals[position] = ordinal + 1
            if category in ('objects', 'expressions'):
                need(text(row.get('id')) and row['id'] not in ids and type(row.get('details')) is dict, 'object_or_expression_identity')
                ids.add(row['id'])
            if category == 'objects':
                need(set(row) == {'id', 'native_id', 'kind', 'name', 'evidence', 'details', 'occurrence_id'}
                     and text(row['kind']) and type(row['name']) is str
                     and (row['native_id'] is None or text(row['native_id'])), 'object_shape')
                need(row['id'] == _generated_id('object', *position, row['native_id'] if row['native_id'] is not None else row['name']),
                     'generated_object_identity')
                objects[row['id']] = row
            elif category == 'expressions':
                need(set(row) == {'id', 'object_id', 'language', 'text', 'evidence', 'details', 'occurrence_id', 'content_sha256'}
                     and text(row['language']) and type(row['text']) is str and len(row['text'].encode()) <= 8 * 1024 * 1024
                     and row['content_sha256'] == sha(row['text'].encode()), 'expression_hash_or_shape')
                need(row['id'] == _generated_id('expression', *position, row['text']), 'generated_expression_identity')
                if e['locator'] == '$source':
                    need(e['path'] not in full_source and row['content_sha256'] == e['sha256'], 'full_source_binding')
                    need(row['language'] == 'webfocus:' + PurePosixPath(e['path']).suffix.lower()[1:], 'source_language_mismatch')
                    full_source[e['path']] = row['text']
            elif category == 'dependencies':
                need(set(row) == {'source_id', 'target', 'evidence', 'details', 'occurrence_id'} and text(row['target'])
                     and type(row['details']) is dict and row['details'].get('resolution') == 'unresolved', 'dependency_shape_or_resolution')
            else:
                need(set(row) == {'code', 'message', 'evidence', 'occurrence_id'} and text(row['code'])
                     and type(row['message']) is str and files[e['path']]['status'] != 'parsed', 'gap_shape_or_hidden_coverage')
    need(sum(len(t.encode()) for t in full_source.values()) <= 32 * 1024 * 1024, 'source_byte_budget')
    for path, row in files.items():
        known = PurePosixPath(path).suffix.lower() in {'.fex', '.mas', '.acx'}
        need((known and path in full_source and row['status'] == 'partial' and any(
            g['code'] == 'webfocus.runtime_context_unverified' and g['evidence']['path'] == path for g in value['gaps']))
            or (not known and row['status'] == 'unsupported'), 'source_coverage_contract')
    for row in value['objects']:
        parent = row['details'].get('parent_id')
        need(parent is None or (parent in objects and objects[parent]['evidence']['path'] == row['evidence']['path']), 'parent_owner_missing')
        seen = {row['id']}
        while parent is not None:
            need(parent in objects and parent not in seen, 'parent_cycle_or_missing')
            seen.add(parent); parent = objects[parent]['details'].get('parent_id')
    for row in value['expressions']:
        need(row['object_id'] is None or (row['object_id'] in objects and
             objects[row['object_id']]['evidence']['path'] == row['evidence']['path']), 'expression_owner_missing')
    for row in value['dependencies']:
        need(row['source_id'] in objects and objects[row['source_id']]['evidence']['path'] == row['evidence']['path'],
             'dependency_owner_missing')
    return files, objects


def _split_literal(value, delimiter):
    result, start, quote, index = [], 0, None, 0
    while index < len(value):
        char = value[index]
        if quote:
            if char == quote:
                if index + 1 < len(value) and value[index + 1] == quote:
                    index += 2; continue
                quote = None
        elif char in "'\"": quote = char
        elif char == delimiter:
            result.append(value[start:index]); start = index + 1
            need(len(result) <= MAX_FEX_UNITS, 'visual_structure_limit')
        index += 1
    need(quote is None, 'unterminated_literal')
    return result, value[start:]


def inspect_fex(source, path):
    """Original source recognizer, never a stylesheet cascade or JavaScript engine."""
    _source_path(path)
    need(type(source) is str and len(source.encode()) <= 8 * 1024 * 1024, 'fex_bytes')
    out = {'source_path': path, 'sha256': sha(source.encode()), 'hash_basis': 'decoded_text_encoded_as_utf8',
           'graph_requests': [], 'style_blocks': [],
           'graph_js_blocks': [], 'graph_script_blocks': [], 'gaps': [],
           'interpretation': 'bounded_inert_declarations', 'execution_performed': False}
    def gap(code, line):
        out['gaps'].append({'code': 'webfocus.' + code, 'locator': 'line:' + str(line)})
    lines = source.splitlines()
    if len(lines) > 20000:
        gap('visual_structure_limit', 1); return out
    graph, style, js, script, budget = None, None, None, None, MAX_FEX_UNITS
    def finish_style(block, end, terminated):
        block.update(end_line=end, terminated=terminated, records=[])
        body = '\n'.join(block.pop('lines'))
        block['original_text'] = body
        if not terminated: gap('style_unterminated', block['start_line'])
        try:
            need(len(body) <= MAX_FEX_CHARS, 'style_structure_limit')
            records, trailing = _split_literal(body, '$')
            if trailing.strip(): gap('style_unterminated_record', block['start_line'])
            for sequence, raw in enumerate(records):
                if not raw.strip(): continue
                attrs, status = [], 'literal_attributes_preserved'
                parts, tail = _split_literal(raw, ',')
                need(len(parts) <= 32, 'style_attribute_limit')
                for attr in parts + [tail]:
                    if not attr.strip(): continue
                    match = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*', attr, re.S)
                    if not match or '&' in attr:
                        status = 'opaque'; continue
                    attrs.append({'name': match[1], 'value': match[2]})
                if status == 'opaque': gap('style_dynamic_or_opaque', block['start_line'])
                block['records'].append({'sequence': sequence, 'original_text': raw, 'attributes': attrs, 'status': status})
        except ValueError:
            gap('style_malformed_literal', block['start_line'])
        out['style_blocks'].append(block)
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if script is not None:
            budget -= 1
            if budget < 0 or len(raw) > MAX_FEX_CHARS:
                gap('visual_structure_limit', number); break
            if line.upper() == '*END':
                script.update(original_text='\n'.join(script.pop('lines')), end_line=number, terminated=True)
                out['graph_script_blocks'].append(script); script = None
            else:
                script['lines'].append(raw)
            continue
        if not line or line.startswith('-*'): continue
        budget -= 1
        if budget < 0 or len(raw) > MAX_FEX_CHARS:
            gap('visual_structure_limit', number); break
        if js is not None:
            if line.upper() == '*END':
                body = '\n'.join(js.pop('lines'))
                js.update(original_text=body, end_line=number, terminated=True, data=None, interpretation='opaque')
                try:
                    need(len(body) <= MAX_FEX_CHARS and '&' not in body, 'graph_js_dynamic_or_limit')
                    data = F.decode(body.encode())
                    need(type(data) is dict, 'graph_js_object_required')
                    js.update(data=data, interpretation='strict_json_data_only')
                except ValueError: gap('graph_js_opaque_or_dynamic', js['start_line'])
                out['graph_js_blocks'].append(js); js = None
            else:
                js['lines'].append(raw)
            continue
        if line.upper() == '*GRAPH_JS':
            js = {'start_line': number, 'graph_key': graph, 'style_start_line': style['start_line'] if style else None, 'lines': []}
            continue
        if line.upper() == '*GRAPH_SCRIPT':
            script = {'start_line': number, 'graph_key': graph, 'style_start_line': style['start_line'] if style else None,
                      'lines': [], 'interpretation': 'opaque', 'data': None}
            gap('graph_script_unsupported', number)
            continue
        if style is not None:
            if line.upper() == 'ENDSTYLE':
                finish_style(style, number, True); style = None
            else: style['lines'].append(raw)
            continue
        match = re.fullmatch(r'GRAPH\s+FILE\s+([A-Za-z_][A-Za-z0-9_.$/-]*)', line, re.I)
        if re.match(r'GRAPH\s+FILE\b', line, re.I):
            graph = path + '#line:' + str(number)
            out['graph_requests'].append({'key': graph, 'start_line': number, 'original_text': raw,
                'native_source': match[1] if match else None, 'status': 'literal_declaration' if match else 'dynamic_or_opaque'})
            if match is None: gap('graph_dynamic_or_opaque', number)
        elif re.fullmatch(r'ON\s+(?:GRAPH|TABLE)\s+SET\s+STYLE\s+\*', line, re.I):
            style = {'start_line': number, 'graph_key': graph, 'lines': []}
        elif line.upper() == 'END': graph = None
        elif line.startswith('-') or '&' in line or re.match(r'(SET|ENGINE|SQL|FILEDEF|APP|EX|EXEC)\b', line, re.I):
            gap('visual_runtime_context_opaque', number)
        elif re.match(r'ON\s+(?:GRAPH|TABLE)\s+SET\s+STYLE\b', line, re.I):
            gap('external_or_opaque_style_not_loaded', number)
    if js is not None:
        js.update(original_text='\n'.join(js.pop('lines')), terminated=False, data=None, interpretation='opaque')
        out['graph_js_blocks'].append(js); gap('graph_js_unterminated', js['start_line'])
    if script is not None:
        script.update(original_text='\n'.join(script.pop('lines')), terminated=False)
        out['graph_script_blocks'].append(script); gap('graph_script_unterminated', script['start_line'])
    if style is not None: finish_style(style, len(lines), False)
    return out


def visual_declarations(report):
    return [inspect_fex(e['text'], e['evidence']['path']) for e in report['expressions']
            if e['evidence']['locator'] == '$source' and e['language'] == 'webfocus:fex']


def parse_adapter(payload, raw, helpers, revision):
    files, objects = validate(payload, revision)
    result = helpers['base'](payload, raw, 'webfocus', 'supplied_webfocus_source_adapter_result')
    result['source'].update(projection_version='1.0.0', producer={'name': 'DataModelAccelerator', 'revision': revision,
        'revision_evidence': 'operator_declared_not_authenticated', 'component_sha256': payload.get('component_sha256'),
        'reviewed_component_file_pins': copy.deepcopy(PRODUCERS[revision]),
        'component_qualification': 'known_source_files_only; runtime_component_hash_not_recomputed'},
        upstream_files=copy.deepcopy(payload['source_files']))
    result.update(upstream_coverage=copy.deepcopy(payload['coverage_summary']), upstream_gaps=copy.deepcopy(payload['gaps']),
                  upstream_expressions=copy.deepcopy(payload['expressions']), build_authority=False,
                  migration_context={'route': None, 'build_authority': False, 'target_write_authority': False,
                      'native_validation': 'not_established', 'business_acceptance': 'not_assessed'})
    declarations = visual_declarations(payload)
    by_path = {d['source_path']: d for d in declarations}
    result['webfocus_visual_declarations'] = declarations
    expressions = {}
    for e in payload['expressions']: expressions.setdefault(e['object_id'], []).append(e)
    for i, row in enumerate(payload['objects']):
        details = row['details']
        facets = {'query': {'status': 'declared' if row['id'] in expressions else 'unobserved',
                   'value': copy.deepcopy(expressions.get(row['id'], []))},
            'content': {'status': 'declared', 'value': {'name': row['name'], 'native_attributes': details.get('native_attributes')}},
            'visual': {'status': 'needs_review', 'value': copy.deepcopy(by_path.get(row['evidence']['path']))},
            'layout': {'status': 'unobserved', 'value': None}, 'filters': {'status': 'needs_review', 'value': None},
            'interactions': {'status': 'needs_review', 'value': None}, 'security': {'status': 'unobserved', 'value': None}}
        helpers['add_asset'](result, 'definition', row, '/objects/' + str(i), row['id'], row['evidence']['path'], facets,
            id_kind='adapter_generated_id', source_identity={'source_platform': 'webfocus', 'adapter_kind': row['kind'],
                'native_id': row['native_id'], 'adapter_occurrence_id': row['occurrence_id'], 'evidence': copy.deepcopy(row['evidence']),
                'parent_id': details.get('parent_id'), 'query_visual': False,
                'definition_sha256': row['evidence']['sha256'],
                'report_obligation': row['kind'] in ('procedure', 'report_request')})
    for i, row in enumerate(payload['source_files']):
        helpers['add_asset'](result, 'definition', row, '/source_files/' + str(i), None, row['path'],
            {'content': {'status': 'declared', 'value': copy.deepcopy(row)}}, id_kind='source_file',
            source_identity={'source_platform': 'webfocus', 'source_file': row['path'], 'definition_sha256': row['sha256'],
                             'query_visual': False, 'report_obligation': row['path'].lower().endswith('.fex')})
    result['dependencies'] = copy.deepcopy(payload['dependencies'])
    for i, row in enumerate(payload['dependencies']): helpers['gap'](result, 'webfocus.dependency_unresolved', '/dependencies/' + str(i), row)
    for i, row in enumerate(payload['gaps']): helpers['gap'](result, 'webfocus.upstream_gap', '/gaps/' + str(i), row)
    for declaration in declarations:
        for row in declaration['gaps']: helpers['gap'](result, row['code'], declaration['source_path'], row)
    for code in ('visual_denominator_not_established', 'source_files_not_reverified', 'effective_access_not_verified',
                 'native_results_and_behavior_required', 'style_cascade_and_graph_semantics_unverified'):
        helpers['gap'](result, 'webfocus.' + code)
    return result


def validate_capture(value):
    return module('webfocus_capture').validate_capture(value)


def verify_capture_files(value, root):
    return module('webfocus_capture').verify_capture_files(value, root)


def scope_flags(key, inventory):
    """Retain the most restrictive declared scope across parents and placements.

    These flags are conservative workflow constraints, not access or approval
    evidence. An out-of-scope dependency requires a reviewed original source.
    """
    pending, seen, dispositions = [key], set(), set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        need(current in inventory, 'scope_object_missing')
        seen.add(current)
        row = inventory[current]
        dispositions.add(row['disposition'])
        if row['parent_key'] is not None:
            pending.append(row['parent_key'])
        if row['kind'] == 'placement':
            config = row['configuration']
            pending.append(config.get('visual_key', config.get('content_key')))
    return {'restricted_private_scope': 'out_of_scope' in dispositions,
            'requires_source_review': bool(dispositions - {'include'})}


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    source, request = payload['source'], payload['request']
    report = source.get('adapter_report')
    result = (parse_adapter(report, encoded(report), helpers, request['producer_revision']) if report is not None
              else helpers['base'](payload, raw, 'webfocus', 'supplied_webfocus_visual_capture'))
    base = helpers['base'](payload, raw, 'webfocus', 'supplied_webfocus_visual_capture')
    result.update(source=base['source'], upstream_payload=copy.deepcopy(payload), build_authority=False)
    identity = {k: copy.deepcopy(request[k]) for k in ('product', 'source_origin', 'product_version', 'source_revision', 'root_key')}
    namespace = request['source_origin'] + '/webfocus/' + request['root_key']
    result['source'].update(source_identity=identity, namespace=namespace,
        definition_fingerprint=source['definition_fingerprint'], capture_content_hash=payload['content_hash'])
    declarations = {d['source_path']: d for d in result.get('webfocus_visual_declarations', [])}
    for pin in source['files']:
        inspected = pin.get('inspection', {}).get('visual_declarations')
        if type(inspected) is dict:
            declarations[pin['source_path']] = copy.deepcopy(inspected)
    result['webfocus_visual_declarations'] = list(declarations.values())
    inventory = {o['key']: o for o in source['inventory']['objects']}
    for asset in result['assets']:
        asset['source_identity'].update(adapter_evidence_only=True, query_visual=False,
            definition_fingerprint=source['definition_fingerprint'], namespace=namespace,
            **scope_flags(request['root_key'], inventory))
    # Replaced only by the separate declared enumeration, never a completeness pass.
    result['gaps'] = [g for g in result['gaps'] if g['code'] != 'webfocus.visual_denominator_not_established']
    crosswalk = {o['key']: o for o in source['crosswalk']['rows']}
    objects = {o['id']: o for o in report['objects']} if report else {}
    for i, row in enumerate(source['inventory']['objects']):
        key, config = row['key'], row['configuration']
        semantic = objects.get(row['source_object_id'])
        target = inventory[config.get('visual_key', config.get('content_key'))] if row['kind'] == 'placement' else row
        visual_key = target['key'] if target['kind'] == 'visual' else None
        facets = {'visual': {'status': 'declared', 'value': copy.deepcopy(config)},
            'layout': {'status': 'declared', 'value': {'parent_key': row['parent_key'], 'configuration': copy.deepcopy(config)}},
            'filters': {'status': 'declared' if row['kind'] in ('control', 'parameter') else 'needs_review', 'value': copy.deepcopy(config)},
            'content': {'status': 'declared', 'value': {'name': row['name']}},
            'query': {'status': 'declared' if semantic else 'unobserved', 'value': copy.deepcopy([
                e for e in report['expressions'] if semantic and e['object_id'] == semantic['id']]) if report else []},
            'interactions': {'status': 'needs_review', 'value': copy.deepcopy(config)},
            'security': {'status': 'unobserved', 'value': None}}
        normalized_kind = 'layout' if row['kind'] in ('section', 'container') else row['kind']
        helpers['add_asset'](result, normalized_kind, row, '/source/inventory/objects/' + str(i), key, namespace, facets,
            id_kind='independently_enumerated_source_key', source_identity={**identity, 'source_platform': 'webfocus',
                'object_key': key, 'visual_key': visual_key, 'namespace': namespace, 'source_object_id': row['source_object_id'],
                'native_kind': row['kind'],
                'definition_fingerprint': source['definition_fingerprint'], 'definition_sha256': source['definition_fingerprint'],
                'identity_crosswalk': copy.deepcopy(crosswalk[key]), 'query_visual': target['kind'] == 'visual',
                'declared_disposition': row['disposition'], **scope_flags(key, inventory)})
        if scope_flags(key, inventory)['restricted_private_scope']:
            helpers['gap'](result, 'webfocus.source_scope_not_selected', '/source/inventory/objects/' + str(i))
        if row['kind'] == 'unknown' or scope_flags(key, inventory)['requires_source_review']:
            helpers['gap'](result, 'webfocus.independent_object_requires_review', '/source/inventory/objects/' + str(i))
        if crosswalk[key]['resource_path'] is None:
            helpers['gap'](result, 'webfocus.native_resource_identity_unverified', '/source/crosswalk/' + key)
    result.setdefault('migration_context', {}).update(route=None if request['route'] == 'unselected' else request['route'],
        route_reference=request['route_reference'], target_surface=request['target_surface'], build_authority=False,
        target_write_authority=False, native_validation='not_established', business_acceptance='not_assessed')
    result['webfocus_coverage'] = {'enumerated_objects': len(inventory),
        **{kind + 's': sum(o['kind'] == kind for o in inventory.values()) for kind in (
            'app', 'dashboard', 'page', 'section', 'container', 'visual', 'control', 'parameter', 'action', 'placement', 'content', 'unknown')},
        'manifest_completeness': source['inventory']['completeness'], 'source_export_completeness': 'not_established',
        'enumeration_provenance': 'supplied_independent_enumeration_not_authenticated', 'behavior_coverage': 'not_verified'}
    for gap in payload['gaps']: helpers['gap'](result, 'webfocus.capture_gap', detail=gap)
    helpers['gap'](result, 'webfocus.actual_files_require_verification')
    return result


def validate_case(value, capture):
    validate_capture(capture)
    need(type(value) is dict and type(value.get('source_binding')) is dict, 'case_binding_required')
    binding = value['source_binding']
    need(binding.get('state_sha256') == sha(capture['request']['state']) and
         binding.get('definition_fingerprint') == capture['source']['definition_fingerprint'], 'case_capture_binding')
    return binding


def case_binding(asset, case, capture):
    binding = validate_case(case, capture)
    identity, request = asset.get('source_identity', {}), capture['request']
    need(identity.get('definition_fingerprint') == capture['source']['definition_fingerprint'] and
         all(identity.get(k) == request[k] for k in ('product', 'source_origin', 'product_version', 'source_revision', 'root_key')),
         'case_source_identity_mismatch')
    selected_key = identity.get('object_key')
    inventory = {o['key']: o for o in capture['source']['inventory']['objects']}
    need(selected_key in inventory and not scope_flags(selected_key, inventory)['restricted_private_scope'],
         'case_object_scope')
    selected = inventory[selected_key]
    config = selected['configuration']
    key = config.get('visual_key', config.get('content_key')) if selected['kind'] == 'placement' else selected_key
    placement = selected_key if selected['kind'] == 'placement' else None
    need(key in inventory and inventory[key]['disposition'] != 'out_of_scope' and
         binding.get('object_key') == key and binding.get('placement_key') == placement, 'case_object_or_placement_mismatch')
    aid = binding.get('attachment_id')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == aid and a['object_key'] in {key, selected_key}]
    if aid is not None: need(len(matches) == 1, 'case_attachment_mismatch')
    if case.get('lane') == 'numeric':
        need(inventory[key]['kind'] == 'visual' and aid is not None and matches[0]['format'] in ('csv', 'json'),
             'case_numeric_result_required')
    return binding


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(digest(binding[k]) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and all(text(binding[k]) for k in ('object_key', 'attachment_id')), 'normalization_binding')
    need(type(profile) is dict and profile.get('format') in ('csv', 'json'), 'normalization_profile')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'],
              'state_sha256': binding['state_sha256'], 'attachment_sha256': binding['attachment_sha256']}
    result = module('powerbi_visual').normalize_results(raw, profile, mapped)
    result.update(kind='webfocus_normalized_results', binding=copy.deepcopy(binding))
    return result


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps, request = [], capture['request']
    if case.get('source_capture') is None: gaps.append('source.webfocus_case_capture_required')
    if capture.get('status') == 'blocked': gaps.append('source.webfocus_capture_blocked')
    if request['source_revision']['kind'] == 'unknown': gaps.append('source.webfocus_revision_unverified')
    raw_pin = source.get('raw_file') if source.get('format') == 'webfocus-normalized' else source.get('file')
    need(type(raw_pin) is dict, 'comparison_raw_pin_required')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding.get('attachment_id') and
               a['format'] in ('csv', 'json') and a['sha256'] == raw_pin.get('sha256')]
    if len(matches) != 1: return gaps + ['source.webfocus_result_not_bound']
    a = matches[0]
    if a['completeness']['status'] != 'complete' or not a['completeness']['reference']:
        gaps.append('source.webfocus_completeness_unverified')
    if a['origin'] == 'unknown' or a['result_scope'] == 'unknown': gaps.append('source.webfocus_result_origin_unverified')
    observed = a['observed_state']
    if observed is None: gaps.append('source.webfocus_observed_state_missing')
    else:
        for key in ('filters', 'parameters', 'timezone', 'locale', 'cache', 'principal'):
            wanted = request['state'][key]
            if wanted is None or observed['state'][key] != wanted or source['context'].get(key) != wanted:
                gaps.append('source.webfocus_observed.' + key)
            # Target cache/refresh is an independently selected product policy.
            # Freshness/population evidence below is the comparison invariant.
            if key not in ('principal', 'cache') and target['context'].get(key) != wanted: gaps.append('context.' + key)
    if asset['kind'] == 'placement' and not (observed or {}).get('placement_reference'):
        gaps.append('source.webfocus_placement_parameter_evidence_required')
    inventory = {o['key']: o for o in capture['source']['inventory']['objects']}
    crosswalk = {r['key']: r for r in capture['source']['crosswalk']['rows']}
    visual_key = binding['object_key']
    if crosswalk[visual_key]['resource_path'] is None: gaps.append('source.webfocus_native_identity_unverified')
    # Stored report calculations may differ from client-side/in-document results.
    # Preserve an explicit inventory declaration rather than guessing from SQL/FEX.
    config = inventory[visual_key]['configuration']
    contract = config.get('result_contract')
    result_context = (observed or {}).get('result_context')
    if contract is None:
        gaps.append('source.webfocus_result_contract_missing')
    else:
        module('webfocus_capture').validate_result_context(contract)
    if result_context is None:
        gaps.append('source.webfocus_observed_result_context_missing')
    else:
        for key in ('data_mode', 'row_limit', 'row_limit_stage', 'aggregation_stage'):
            actual = result_context[key]
            if contract is not None and contract[key] != actual:
                gaps.append('source.webfocus_requested_result.' + key)
            if source['context'].get(key, '__absent__') != actual:
                gaps.append('source.webfocus_observed_result.' + key)
            if target['context'].get(key, '__absent__') != actual:
                gaps.append('context.' + key)
        if result_context['data_mode'] in ('test', 'unknown') or result_context['row_limit_stage'] == 'unknown' or \
           result_context['aggregation_stage'] == 'unknown':
            gaps.append('source.webfocus_result_semantics_unqualified')
        if source['context'].get('result_context_reference') != result_context['reference']:
            gaps.append('source.webfocus_result_context_reference')
        if not text(target['context'].get('result_context_reference')):
            gaps.append('target.webfocus_result_context_reference')
    if (config.get('post_query_calculation') is True or
        (result_context or {}).get('aggregation_stage') == 'in_document') and \
       (a['origin'] != 'transformed' or a['result_scope'] != 'transformed'):
        gaps.append('source.webfocus_transformed_results_required')
    for key, wanted in {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                        'freshness_reference': a['freshness']['reference'], 'result_scope': a['result_scope']}.items():
        if wanted is None or not a['freshness']['observed_at'] or source['context'].get(key) != wanted:
            gaps.append('source.webfocus_context.' + key)
        if key == 'freshness_reference':
            if not target['context'].get(key): gaps.append('target.webfocus_freshness_reference')
        elif target['context'].get(key) != wanted: gaps.append('context.' + key)
    if source.get('format') == 'webfocus-normalized':
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': capture['source']['definition_fingerprint'],
            'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'],
            'state_sha256': binding['state_sha256'], 'attachment_sha256': raw_pin['sha256']}
        if type(normalized) is not dict or normalized.get('binding') != expected:
            gaps.append('source.webfocus_normalization_binding_mismatch')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                   target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    return gaps
