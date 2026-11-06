"""Candidate-bound visible data declarations. Source integrity, never runtime proof.

No query execution, timers, cache changes, permission grants or generated results.
The native caller supplies the exact HTML and complete saved presentations it is
about to use, plus the artifacts retained by the existing candidate review.
"""
from html.parser import HTMLParser
from pathlib import Path
import re


POLICY = 'candidate-release-v1'
MANIFEST = 'contracts/native-data-consumers.json'
MAX_CONSUMERS = 256
ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,127}\Z')
QUERY_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')


def need(ok, reason):
    if not ok:
        raise ValueError('native_data_consumers.' + reason)


def text(value):
    return type(value) is str and 0 < len(value.strip()) <= 4096


def strings(value, maximum=256):
    return (type(value) is list and 0 < len(value) <= maximum
            and all(text(v) for v in value) and len(set(value)) == len(value))


def pin(value):
    need(type(value) is dict and set(value) == {'path', 'sha256'}
         and text(value['path']) and type(value['sha256']) is str
         and SHA.fullmatch(value['sha256']), 'evidence_pin_required')
    path = Path(value['path'])
    need(not path.is_absolute() and '..' not in path.parts and '\\' not in value['path']
         and path.as_posix() == value['path'] and value['path'].startswith(('inputs/', 'evidence/')),
         'private_evidence_path_required')
    return value


class Markup(HTMLParser):
    """Inspect declared source locations; CSS visibility and execution stay unobserved."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.stack, self.markers, self.ids, self.scripts = [], {}, set(), []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        keys = [key for key, _ in attrs]
        need(len(keys) == len(set(keys)), 'duplicate_html_attribute')
        data = dict(attrs)
        ident = data.get('id')
        if ident is not None:
            need(ident not in self.ids, 'duplicate_html_id')
            self.ids.add(ident)
        hidden = (any(r['hidden'] for r in self.stack) or tag in {'script', 'style', 'template', 'noscript'}
                  or 'hidden' in data or 'inert' in data or (data.get('aria-hidden') or '').lower() == 'true')
        marker = data.get('data-oaa-consumer')
        if 'data-oaa-consumer' in data:
            need(type(marker) is str and ID.fullmatch(marker) and marker not in self.markers and not hidden
                 and not any(r['marker'] for r in self.stack), 'invalid_hidden_or_nested_consumer_marker')
            self.markers[marker] = {'element_id': ident, 'text': []}
        active_script = (tag == 'script' and 'src' not in data and not any(r['hidden'] for r in self.stack)
                         and (data.get('type') or '').lower() in {'', 'text/javascript', 'application/javascript', 'module'})
        row = {'tag': tag, 'marker': marker, 'hidden': hidden, 'script': [] if active_script else None}
        if tag not in self.VOID:
            self.stack.append(row)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        # Reject ambiguous nesting for the annotated contract rather than emulate
        # a browser's error recovery and silently inspect a different tree.
        need(self.stack and self.stack[-1]['tag'] == tag, 'ambiguous_html_nesting')
        row = self.stack.pop()
        if row['script'] is not None:
            self.scripts.append(''.join(row['script']))

    def handle_data(self, data):
        if self.stack and self.stack[-1]['script'] is not None:
            self.stack[-1]['script'].append(data)
        if not any(row['hidden'] for row in self.stack):
            for row in self.stack:
                if row['marker']:
                    self.markers[row['marker']]['text'].append(data)


def fragment(markup, value, identifiers):
    need(text(value) and any(value in script for script in markup.scripts), 'callback_fragment_missing')
    # This records exact candidate source sites, not a JavaScript execution proof.
    for ident in identifiers:
        need(any(quote + ident + quote in value for quote in ('"', "'")), 'callback_identity_missing')


def inspect(manifest, *, document_id, app_html, presentations, refresh_policy, P):
    """Validate supplied source structure, returning pins to read in guard()."""
    fields = {'schema_version', 'kind', 'document_id', 'html_sha256', 'presentations_sha256',
              'refresh_policy', 'consumers'}
    need(type(manifest) is dict and set(manifest) == fields and type(manifest['schema_version']) is int
         and manifest['schema_version'] == 1 and manifest['kind'] == 'native_data_consumers', 'manifest_schema_invalid')
    need(text(document_id) and manifest['document_id'] == document_id, 'document_changed')
    need(type(app_html) is str and 0 < len(app_html.encode('utf-8')) <= 2 * 1024 * 1024
         and manifest['html_sha256'] == P.digest(app_html.encode('utf-8')), 'candidate_html_changed')
    need(type(presentations) is dict and set(presentations) == {'data', 'order'}
         and type(presentations['data']) is dict and type(presentations['order']) is list
         and len(presentations['data']) <= 256
         and all(type(k) is str and QUERY_ID.fullmatch(k) for k in presentations['data'])
         and all(type(k) is str for k in presentations['order'])
         and len(presentations['order']) == len(set(presentations['order']))
         and set(presentations['data']) == set(presentations['order']), 'complete_presentations_required')
    need(manifest['presentations_sha256'] == P.digest(P.canonical(presentations)), 'saved_queries_changed')
    need(type(refresh_policy) is dict and P.canonical(manifest['refresh_policy']) == P.canonical(refresh_policy),
         'selected_refresh_policy_changed')
    consumers = manifest['consumers']
    need(type(consumers) is list and 0 < len(consumers) <= MAX_CONSUMERS, 'consumer_inventory_required')
    markup = Markup(app_html)
    need(not markup.stack, 'unclosed_html')
    ids, rows, evidence, bindings = set(), {}, [], []
    common = {'id', 'element_id', 'mode', 'expectation', 'expectation_basis'}
    variants = {'live': {'sources'}, 'snapshot': {'label', 'period', 'source_label', 'source'},
                'scenario': {'label', 'base_consumer_ids', 'assumptions', 'script_fragment'}}
    for row in consumers:
        need(type(row) is dict and type(row.get('mode')) is str and row['mode'] in variants
             and set(row) == common | variants[row['mode']], 'consumer_fields_invalid')
        ident = row['id']
        need(type(ident) is str and ID.fullmatch(ident) and ident not in ids, 'consumer_id_invalid')
        ids.add(ident)
        rows[ident] = row
        marker = markup.markers.get(ident)
        need(marker is not None and text(row['element_id']) and marker['element_id'] == row['element_id'],
             'consumer_element_missing')
        need(type(row['expectation_basis']) is str and row['expectation_basis'] in {'independent_query', 'independent_calculation'},
             'independent_expectation_required')
        evidence.append(pin(row['expectation']))
        if row['mode'] == 'live':
            sources = row['sources']
            need(type(sources) is list and 0 < len(sources) <= 64, 'live_query_bindings_required')
            keys = set()
            for source in sources:
                need(type(source) is dict and set(source) == {'query_key', 'tile_sha256', 'fields', 'script_fragment'},
                     'live_source_fields_invalid')
                key = source['query_key']
                need(type(key) is str and key in presentations['data'] and key not in keys, 'live_query_missing_or_duplicate')
                keys.add(key)
                tile = presentations['data'][key]
                need(type(tile) is dict and source['tile_sha256'] == P.digest(P.canonical(tile)), 'live_query_changed')
                query = tile.get('query')
                need(tile.get('type') == 'query' and tile.get('isSql', False) is False
                     and type(tile.get('queryType', 'TOPIC')) is str and tile.get('queryType', 'TOPIC').upper() == 'TOPIC'
                     and text(tile.get('topicName'))
                     and type(query) is dict and strings(query.get('fields'))
                     and not query.get('userEditedSQL') and not any(k in tile for k in ('sql', 'rawSql', 'rawSQL')),
                     'structured_topic_query_required')
                need(strings(source['fields']) and set(source['fields']) <= set(query['fields']), 'consumer_field_missing')
                fragment(markup, source['script_fragment'], [ident, key])
                bindings.append({'consumer_id': ident, 'query_key': key, 'topic': tile['topicName'],
                                 'fields': source['fields'], 'tile_sha256': source['tile_sha256']})
        else:
            rendered = ' '.join(' '.join(marker['text']).split())
            label = row['label']
            need(text(label) and ' '.join(label.split()) in rendered, 'visible_classification_label_missing')
            if row['mode'] == 'snapshot':
                need('snapshot' in label.casefold() and text(row['period']) and text(row['source_label'])
                     and ' '.join(row['period'].split()) in rendered and ' '.join(row['source_label'].split()) in rendered,
                     'snapshot_period_and_source_label_required')
                evidence.append(pin(row['source']))
                need(row['source']['sha256'] != row['expectation']['sha256'], 'independent_expectation_is_source')
            else:
                need(any(word in label.casefold() for word in ('scenario', 'estimate'))
                     and strings(row['base_consumer_ids'], MAX_CONSUMERS), 'scenario_basis_required')
                evidence.append(pin(row['assumptions']))
                need(row['assumptions']['sha256'] != row['expectation']['sha256'], 'independent_expectation_is_assumptions')
                fragment(markup, row['script_fragment'], [ident] + row['base_consumer_ids'])
    need(ids == set(markup.markers), 'unmapped_visible_consumer')
    for row in consumers:
        if row['mode'] == 'scenario':
            need(all(key in rows and rows[key]['mode'] in {'live', 'snapshot'} for key in row['base_consumer_ids']),
                 'scenario_base_missing_or_recursive')
    if any(row['mode'] == 'live' for row in consumers):
        need(refresh_policy.get('mode') != 'not_applicable', 'live_refresh_policy_required')
    return {'status': 'source_bound', 'consumer_count': len(consumers), 'bindings': bindings,
            'evidence': evidence, 'runtime_verified': False, 'numerical_verified': False,
            'visual_coverage_verified': False, 'access_verified': False}


def guard(root, P, *, document_id, app_html, presentations, reviewed_artifacts=None):
    """Re-read current inputs at guarded native preparation/verification boundaries."""
    if root is None or not (Path(root) / 'project.json').is_file():
        return {'status': 'not_assessed', 'reason': 'no_engagement_policy'}
    root, project = P.load_project(root)
    if 'app_release_policy' not in project:
        return {'status': 'not_assessed', 'reason': 'legacy_engagement'}
    need(project['app_release_policy'] == POLICY and 'app' in project['surfaces'], 'unsupported_policy')
    if P.validation_helper().active() is None:
        with P.validation_operation(root):
            return guard(root, P, document_id=document_id, app_html=app_html, presentations=presentations,
                         reviewed_artifacts=reviewed_artifacts)
    need((root / MANIFEST).is_file(), 'manifest_required_at_contracts_native_data_consumers_json')
    manifest, raw = P.read_json(P.relative_file(root, MANIFEST))
    manifest_pin = {'path': MANIFEST, 'sha256': P.digest(raw)}
    # Freeze retains snapshots under its own paths. Identical retained bytes are
    # required; do not insist that the frozen copy has the mutable input path.
    reviewed = [item for item in reviewed_artifacts if type(item) is dict and
                item.get('sha256') == manifest_pin['sha256'] and text(item.get('path'))] if type(reviewed_artifacts) is list else []
    need(reviewed, 'freeze_and_review_current_consumer_manifest')
    need(P.read_bytes(P.relative_file(root, reviewed[0]['path'])) == raw, 'reviewed_consumer_manifest_changed')
    selected = P.intent_helper().load_selected(root)
    refresh = P.routing_helper('product_intent').refresh_report(selected['spec'])
    need(refresh['status'] in {'ready', 'not_applicable'}, 'recover_existing_refresh_question_before_preparation')
    result = inspect(manifest, document_id=document_id, app_html=app_html, presentations=presentations,
                     refresh_policy=refresh['policy'], P=P)
    for record in result.pop('evidence'):
        original = P.read_bytes(P.relative_file(root, record['path']))
        need(original and P.digest(original) == record['sha256'], 'original_evidence_missing_or_changed')
    return {**result, 'policy': POLICY, 'manifest': manifest_pin}
