#!/usr/bin/env python3
"""Offline CLI/API preparation and readback checks for native authoring.

Standard library only. Never reads credentials, connects, runs SQL/HTML, creates
drafts, writes to Omni or confers authority. The host performs authorized official
operations; retained captures are evidence inputs, not authenticated permissions.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

MAX_JSON = 16 * 1024 * 1024
MAX_HTML = 2 * 1024 * 1024
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
CREATE_ID = re.compile(r'[a-z0-9](?:[a-z0-9_-]{0,126}[a-z0-9])?\Z')
# This new-create route is deliberately narrower than the general vendor API.
# Empty allowlists remain enabled; no external resource/navigation permission is
# inferred from old documents or from a local preparation record.
CREATE_SETTINGS = {
    'allowClipboard': False, 'allowDefaultMapProviders': False,
    'allowDownloads': False, 'allowExternalNavigation': False,
    'allowFullscreen': False, 'allowInternalNavigation': False, 'allowModals': False,
    'externalNavOpensInNewTab': True, 'frameDomains': [], 'frameDomainsEnabled': True,
    'navAllowedDomains': [], 'navAllowedDomainsEnabled': True,
    'safeDomains': [], 'safeDomainsEnabled': True,
}
CREATE_TILE_KEYS = {'aiConfig', 'automaticVis', 'description', 'filterOrder', 'isSql', 'name',
                    'prefersChart', 'query', 'resultConfig', 'sourceQueryPresentationKey',
                    'subTitle', 'topicName', 'type', 'visConfig'}
CREATE_QUERY_KEYS = {'calculations', 'column_totals', 'controls', 'custom_summary_types',
                     'default_group_by', 'fields', 'fill_fields', 'filters', 'join_via_map',
                     'join_paths_from_topic_name', 'limit', 'period_over_period_computations', 'pivots', 'row_totals',
                     'sorts', 'table', 'transposed_measures', 'userEditedSQL', 'version'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def decode(raw, shape=None):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_JSON, 'Empty or oversized response')
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('Non-finite JSON')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    encoded(value)  # Also reject overflowed JSON exponents, e.g. 1e999.
    if shape:
        need(type(value) is {'object': dict, 'list': list}[shape], 'Unexpected response shape')
        if shape == 'object':
            need(bool(value), 'Empty object is not a usable response')
    return value


def read_bytes(path, limit):
    path = Path(path).absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(), 'Canonical regular input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        meta = os.fstat(stream.fileno())
        need(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= limit, 'Invalid or oversized input file')
        raw = stream.read(limit + 1)
    need(0 < len(raw) <= limit, 'Invalid or oversized input bytes')
    return raw


def read(path):
    return decode(read_bytes(path, MAX_JSON))


def query_body(query, model_id, user_id=None):
    """Preserve inspected query defaults; modelId belongs INSIDE query."""
    need(type(query) is dict and query and 'query' not in query, 'Supply the inspected query, not an envelope')
    need(type(model_id) is str and ID.fullmatch(model_id), 'Exact model required')
    need(query.get('modelId', model_id) == model_id, 'Query model mismatch')
    fields, sql = query.get('fields', []), query.get('sql', '')
    need(type(fields) is list and all(type(f) is str and f.strip() for f in fields)
         and len(fields) == len(set(fields)), 'Query fields must be unique nonblank strings')
    need(type(sql) is str and (bool(fields) or bool(sql.strip())), 'Query fields or SQL text required')
    result = {'query': {**copy.deepcopy(query), 'modelId': model_id},
              'resultType': 'json', 'formatResults': False}
    if user_id is not None:
        need(type(user_id) is str and ID.fullmatch(user_id), 'Invalid user membership ID')
        result['userId'] = user_id
    return result


def route_check(record):
    """Check an explicitly supplied, version-qualified command inventory."""
    need(type(record) is dict and type(record.get('cli_version')) is str
         and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][\w.-]+)?', record['cli_version']), 'CLI version required')
    commands = record.get('available_commands')
    requested = record.get('required_commands')
    need(type(commands) is list and type(requested) is list and requested
         and all(type(x) is str and x.strip() for x in commands + requested), 'Exact command inventory required')
    need(type(record.get('help_sha256')) is str and re.fullmatch(r'[a-f0-9]{64}', record['help_sha256']),
         'Retain installed help hash')
    missing = [c for c in requested if c not in commands]
    return {'status': 'route_incomplete' if missing else 'supplied_route_consistent',
            'cli_version': record['cli_version'], 'missing_commands': missing,
            'help_sha256': record['help_sha256'], 'native_verified': False,
            'note': 'Inventory is supplied evidence. Use official API for missing operations; do not guess command names.'}


def sql_references(sql):
    """Bounded lexical screen of explicit three-part identifiers, NOT a SQL parser.

    Skip SQL strings/comments before collecting catalog.schema.object tokens.
    Unqualified/dynamic dependencies and view expansion need plan/source review.
    """
    need(type(sql) is str and 0 < len(sql.encode()) <= MAX_JSON, 'Planned SQL required')
    token = re.compile(r"\s+|--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/|'(?:''|[^'])*'|\$\$[\s\S]*?\$\$|\"(?:\"\"|[^\"])*\"|[A-Za-z_][A-Za-z0-9_$]*|.")
    tokens = []
    for match in token.finditer(sql):
        value = match.group()
        if value.isspace() or value.startswith(('--', '/*')):
            continue
        if value.startswith(("'", '$$')):
            # Comments behave like whitespace; literals cannot join identifiers.
            tokens.append(None)
            continue
        if value.startswith('"'):
            tokens.append(('id', value[1:-1].replace('""', '"')))
        elif re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', value):
            tokens.append(('id', value.upper()))
        else:
            tokens.append(value)
    refs = set()
    i = 0
    while i < len(tokens):
        if type(tokens[i]) is not tuple:
            i += 1
            continue
        parts = [tokens[i][1]]
        j = i + 1
        while j + 1 < len(tokens) and tokens[j] == '.' and type(tokens[j + 1]) is tuple:
            parts.append(tokens[j + 1][1]); j += 2
        if len(parts) >= 3:
            refs.add(tuple(parts[:3]))
        i = j
    return sorted(refs)


def plan_check(record):
    need(type(record) is dict, 'Plan record required')
    expected = record.get('expected')
    need(type(expected) is dict and set(expected) == {'database', 'schema', 'fields'}
         and all(type(expected[k]) is str and expected[k] for k in ('database', 'schema'))
         and type(expected['fields']) is list and expected['fields']
         and all(type(f) is str and f for f in expected['fields'])
         and len(set(expected['fields'])) == len(expected['fields']), 'Exact physical and field contract required')
    refs = sql_references(record.get('planned_sql'))
    findings = []
    if not refs:
        findings.append('physical_references_unresolved')
    if any(r[:2] != (expected['database'], expected['schema']) for r in refs):
        findings.append('physical_source_mismatch')
    columns = record.get('columns')
    if not (type(columns) is list and columns and all(type(c) is dict
            and type(c.get('name')) is str and type(c.get('type')) is str and c['type'] for c in columns)
            and [c['name'] for c in columns] == expected['fields']):
        findings.append('semantic_metadata_mismatch')
    rows = record.get('rows')
    if not (type(rows) is list and all(type(r) is dict and set(r) == set(expected['fields']) for r in rows)):
        findings.append('result_keys_mismatch')
    return {'status': 'query_needs_review' if findings else 'bounded_plan_consistent',
            'findings': findings, 'explicit_references': [list(r) for r in refs],
            'input_sha256': digest(record), 'native_callback_verified': False,
            'note': 'Lexical screen only: inspect unqualified/dynamic objects and view expansion separately. '
                    'Retain raw plan/export hashes. Counts, types, grain and independent totals use native_query_probe.py.'}


def target_check(target):
    required = {'base_url', 'document_id', 'draft_id', 'model_id', 'workbook_model_id',
                'key_scope', 'user_id', 'membership_id'}
    need(type(target) is dict and set(target) == required, 'Exact enhancement target required')
    need(type(target['base_url']) is str, 'HTTPS origin must be text')
    origin = urlsplit(target['base_url'])
    need(origin.scheme == 'https' and origin.hostname and not origin.username and not origin.password
         and not origin.path and not origin.query and not origin.fragment and origin.port in (None, 443),
         'Target must be a pinned HTTPS origin')
    for key in required - {'base_url', 'key_scope'}:
        need(type(target[key]) is str and ID.fullmatch(target[key]), 'Invalid target identifier')
    need(target['key_scope'] in {'organization', 'user'} and target['document_id'] != target['draft_id'],
         'Explicit organization/user scope and named draft required')
    return '/api/v2/documents/' + target['document_id'] + '/draft/' + target['draft_id'] + '/app'


def snapshot_check(snapshot, target):
    route = target_check(target)
    need(type(snapshot) is dict and set(snapshot) == {'target', 'identity', 'draft', 'document', 'app'}
         and snapshot['target'] == target, 'Snapshot target mismatch')
    identity, draft, document, app = (snapshot[k] for k in ('identity', 'draft', 'document', 'app'))
    need(all(type(x) is dict for x in (identity, draft, document, app)), 'Invalid snapshot capture')
    need(type(identity.get('user')) is dict and type(document.get('app')) is dict
         and type(document.get('queryPresentations')) is dict, 'Missing snapshot identity or App query bindings')
    need(identity.get('keyScope') == target['key_scope']
         and identity.get('user', {}).get('id') == target['user_id']
         and identity.get('user', {}).get('membershipId') == target['membership_id'], 'Identity mismatch')
    need(draft.get('identifier') == target['draft_id'] and draft.get('publishedIdentifier') == target['document_id']
         and draft.get('status') == 'active' and draft.get('draftOutOfDate') is False
         and draft.get('workbookModelId') == target['workbook_model_id'], 'Draft missing, stale or mismatched')
    need(document.get('modelId') == target['model_id'] and document.get('workbookModelId') == target['workbook_model_id']
         and document.get('app', {}).get('url') == route
         and type(document.get('queryPresentations', {}).get('data')) is dict
         and document['queryPresentations']['data'], 'Existing query-backed App required')
    need(set(app) == {'html', 'settings'} and type(app['html']) is str
         and 0 < len(app['html'].encode()) <= MAX_HTML and type(app['settings']) is dict, 'Invalid App capture')
    return route


def project_helper():
    helper = Path(__file__).resolve().parents[2] / 'omni-artifact-accelerator/scripts/analyst_project.py'
    spec = importlib.util.spec_from_file_location('native_project_gate', helper)
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    return P


def prepare_app(target, baseline, current, html, *, project=None, artifact=None):
    need(project is not None and type(artifact) is str, 'Engagement and local candidate artifact required')
    P = project_helper()
    root, metadata = P.load_project(project)
    gate = P.stage_require(root, 'build')
    candidate = P.relative_file(root, artifact)
    need(candidate.stat().st_size <= MAX_HTML and candidate.read_bytes() == html.encode('utf-8'),
         'Candidate bytes differ from the selected engagement artifact')
    html_sha = hashlib.sha256(html.encode()).hexdigest()
    if gate['required']:
        need(gate.get('candidate') is not None and
             any(pin['sha256'] == html_sha for pin in gate['candidate']['artifacts']),
             'Freeze and review this exact candidate before native preparation')
    route = snapshot_check(baseline, target)
    snapshot_check(current, target)
    need(digest(baseline) == digest(current), 'Target drift: reconcile before preparing a write')
    need(type(html) is str and 0 < len(html.encode()) <= MAX_HTML and html != baseline['app']['html'],
         'Bounded changed candidate HTML required')
    return {'kind': 'native_app_enhancement_request', 'schema_version': 1,
            'target': target, 'baseline_sha256': digest(baseline),
            'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
            'engagement': {'project_id': metadata['id'], 'artifact': artifact,
                           'stage_bindings': gate.get('stage_bindings', {}),
                           'candidate_sha256': gate.get('candidate_sha256')},
            'request': {'method': 'PUT', 'path': route, 'body': {'html': html}},
            'publication_authorized': False, 'settings_changes': False, 'query_changes': False,
            'note': 'Prepared request only; trusted host must verify existing human authorization and '
                    'fresh target immediately before execution. No create/publish or automatic retry.'}


def verify_app(prepared, baseline, after):
    need(type(prepared) is dict and prepared.get('kind') == 'native_app_enhancement_request'
         and prepared.get('schema_version') == 1, 'Prepared enhancement required')
    target = prepared['target']
    route = snapshot_check(baseline, target)
    snapshot_check(after, target)
    request = prepared.get('request')
    need(type(request) is dict and set(request) == {'method', 'path', 'body'}
         and request['method'] == 'PUT' and request['path'] == route
         and type(request['body']) is dict and set(request['body']) == {'html'}
         and type(request['body']['html']) is str
         and 0 < len(request['body']['html'].encode()) <= MAX_HTML, 'Unscoped request')
    need(prepared['baseline_sha256'] == digest(baseline)
         and prepared['html_sha256'] == hashlib.sha256(request['body']['html'].encode()).hexdigest(), 'Request pin drift')
    findings = []
    if after['app']['html'] != request['body']['html']:
        findings.append('html_readback_mismatch')
    if digest(after['app']['settings']) != digest(baseline['app']['settings']):
        findings.append('settings_changed')
    if digest(after['document']) != digest(baseline['document']):
        findings.append('document_or_queries_changed')
    if digest(after['identity']) != digest(baseline['identity']):
        findings.append('identity_changed')
    # Timestamps may change on the selected draft; its binding and branch may not.
    if after['draft'].get('branch') != baseline['draft'].get('branch'):
        findings.append('draft_branch_changed')
    return {'status': 'readback_mismatch' if findings else 'exact_draft_readback',
            'findings': findings, 'html_sha256': prepared['html_sha256'],
            'after_sha256': digest(after), 'native_verified': False, 'published': False}


def create_spec_check(spec):
    """Only a new personal document with reviewed semantic query tiles.

    No folder/permissions/overwrite/endpoint/SQL/settings overrides are accepted.
    The server, not this offline check, establishes slug availability.
    """
    need(type(spec) is dict and set(spec) == {
        'base_url', 'slug', 'model_id', 'name', 'description', 'queryPresentations'},
        'Exact new personal App specification required')
    need(type(spec['base_url']) is str and not any(c.isspace() or ord(c) < 32 or ord(c) == 127
                                                 for c in spec['base_url'])
         and '\\' not in spec['base_url'],
         'Pinned HTTPS origin required')
    origin = urlsplit(spec['base_url'])
    need(origin.scheme == 'https' and origin.hostname and not origin.username and not origin.password
         and not origin.path and not origin.query and not origin.fragment and origin.port in (None, 443)
         and origin.geturl() == spec['base_url'],
         'Pinned HTTPS origin required')
    for field in ('slug', 'model_id'):
        need(type(spec[field]) is str and ID.fullmatch(spec[field]), 'Invalid create identifier')
    need(CREATE_ID.fullmatch(spec['slug']), 'Invalid new document identifier')
    need(type(spec['name']) is str and 0 < len(spec['name']) <= 200 and spec['name'].strip() == spec['name']
         and type(spec['description']) is str and len(spec['description']) <= 4000,
         'Bounded explicit name and description required')
    presentations = spec['queryPresentations']
    need(type(presentations) is dict and set(presentations) == {'data', 'order'}
         and type(presentations['data']) is dict and 0 < len(presentations['data']) <= 48
         and type(presentations['order']) is list, 'Exact nonempty query collection required')
    keys, order = set(presentations['data']), presentations['order']
    need(all(type(k) is str and ID.fullmatch(k) for k in keys)
         and all(type(k) is str for k in order) and len(order) == len(keys)
         and set(order) == keys, 'Query order must name every unique query key once')
    for tile in presentations['data'].values():
        need(type(tile) is dict and set(tile) <= CREATE_TILE_KEYS
             and {'name', 'query', 'topicName', 'type', 'isSql'} <= set(tile)
             and tile['type'] == 'query' and tile['isSql'] is False
             and tile.get('sourceQueryPresentationKey') is None
             and all(type(tile[k]) is str and tile[k].strip() for k in ('name', 'topicName')),
             'Unsupported query presentation or linked/SQL tile')
        query = tile['query']
        need(type(query) is dict and set(query) <= CREATE_QUERY_KEYS
             and {'fields', 'table', 'limit'} <= set(query)
             and type(query['fields']) is list and query['fields']
             and all(type(f) is str and f.strip() for f in query['fields'])
             and len(set(query['fields'])) == len(query['fields'])
             and type(query['table']) is str and query['table'].strip()
             and ('join_paths_from_topic_name' not in query
                  or query['join_paths_from_topic_name'] == tile['topicName'])
             and type(query['limit']) is int and 0 < query['limit'] <= 10000
             and query.get('userEditedSQL', '') == '', 'Unsupported semantic query')
    need(len(encoded(spec)) <= MAX_JSON, 'Oversized create specification')
    return spec


def create_body(spec, html):
    return {'name': spec['name'], 'description': spec['description'], 'identifier': spec['slug'],
            'modelId': spec['model_id'], 'queryPresentations': copy.deepcopy(spec['queryPresentations']),
            'app': {'html': html, 'settings': copy.deepcopy(CREATE_SETTINGS)}}


def prepare_create(*, project, artifact, spec_artifact):
    """Prepare only; A-F readiness is not authorization for the actual POST."""
    P = project_helper()
    root, metadata = P.load_project(project)
    gate = P.stage_require(root, 'release')
    need(gate.get('required') is True and gate.get('release_ready') is True
         and 'app' in metadata['surfaces'], 'New App creation requires current A-F release reviews')
    selected = P.intent_helper().check(root)
    app_candidates = {s.get('candidate_path') for s in selected.get('selections', []) if s.get('surface') == 'app'}
    need(selected.get('status') == 'consistent' and artifact in app_candidates,
         'New App creation requires the selected App artifact')
    html_raw = read_bytes(P.relative_file(root, artifact), MAX_HTML)
    spec_raw = read_bytes(P.relative_file(root, spec_artifact), MAX_JSON)
    html_sha, spec_sha = (hashlib.sha256(raw).hexdigest() for raw in (html_raw, spec_raw))
    pins = {pin['sha256'] for pin in gate['candidate']['artifacts']}
    need({html_sha, spec_sha} <= pins, 'Freeze and review the exact HTML and create specification')
    html = html_raw.decode('utf-8')
    spec = create_spec_check(decode(spec_raw, 'object'))
    body = create_body(spec, html)
    need(P.stage_require(root, 'release')['tail_sha256'] == gate['tail_sha256'],
         'Engagement changed during preparation')
    return {'kind': 'native_app_create_request', 'schema_version': 1,
            'base_url': spec['base_url'],
            'engagement': {'project_id': metadata['id'], 'artifact': artifact,
                           'spec_artifact': spec_artifact, 'html_sha256': html_sha,
                           'spec_sha256': spec_sha, 'candidate_sha256': gate['candidate_sha256'],
                           'stage_bindings': gate['stage_bindings'], 'tail_sha256': gate['tail_sha256']},
            'request': {'method': 'POST', 'path': '/api/v2/documents', 'body': body},
            'request_sha256': digest(body), 'creation_scope': 'new_personal_document',
            'publishes_immediately': True, 'publication_authorized': False,
            'native_verified': False,
            'note': 'Offline preparation only. The actual host must review the exact POST under the user\'s '
                    'separate creation/publication authorization and current identity. Omitted folder uses '
                    'personal documents. Creation immediately publishes the initial version. Slug availability '
                    'is not established here; never overwrite, auto-retry, or reinterpret a conflict as an edit. '
                    'The official API labels App creation as currently in development.'}


def demo_pin(root, record, P):
    need(type(record) is dict and set(record) == {'path', 'sha256'} and
         type(record['sha256']) is str and re.fullmatch(r'[a-f0-9]{64}', record['sha256']),
         'Exact demo evidence pin required')
    raw = read_bytes(P.relative_file(root, record['path']), MAX_JSON)
    need(hashlib.sha256(raw).hexdigest() == record['sha256'], 'Demo evidence changed')
    return raw


def demo_candidate_bindings(root, project_id, gate, expected, P):
    """Resolve direct stage pins or the guarded freeze's original-to-snapshot map."""
    candidate = gate['candidate']
    reviewed = {(p['path'], p['sha256']) for p in candidate['artifacts']}
    if set(expected.items()) <= reviewed:
        return {path: {'path': path, 'sha256': sha} for path, sha in expected.items()}
    envelope = 'evidence/candidate-history/' + candidate['iteration_id'] + '/candidate.json'
    binding = next((p for p in candidate['artifacts'] if p['path'] == envelope), None)
    need(binding is not None, 'Freeze exact HTML, create specification and demo scope before preparation')
    retained, raw = P.read_json(P.relative_file(root, envelope))
    need(P.digest(raw) == binding['sha256'] and retained.get('schema_version') == 1
         and retained.get('kind') == 'analyst_candidate' and retained.get('project_id') == project_id
         and retained.get('id') == candidate['iteration_id'], 'Demo freeze envelope differs from current candidate')
    artifacts, mapping = retained.get('artifacts'), retained.get('retained')
    need(type(artifacts) is dict and type(mapping) is dict and set(artifacts) == set(mapping),
         'Demo retained artifact inventory differs')
    result = {}
    for original, sha in expected.items():
        need(artifacts.get(original) == sha and type(mapping.get(original)) is str,
             'Demo original bytes differ from the reviewed freeze mapping')
        saved = mapping[original]
        need((saved, sha) in reviewed and P.digest(P.relative_file(root, saved).read_bytes()) == sha,
             'Demo retained snapshot is not pinned to the current candidate')
        result[original] = {'path': saved, 'sha256': sha}
    return result


def prepare_demo(*, project, artifact, spec_artifact, demo_artifact):
    """Prepare an observation-limited demonstration, never an authorized write.

All source consultations and recorded minima are mandatory. Supplied resolved
records remain unauthenticated claims; the host must independently enforce the
exact principal, audience and operation before a POST that publishes immediately.
"""
    P = project_helper()
    root, metadata = P.load_project(project)
    gate = P.stage_require(root, 'review')
    need(gate.get('required') is True and gate.get('candidate') is not None and
         not gate.get('findings') and 'app' in metadata['surfaces'],
         'Demo requires current A-E and a frozen candidate without gate findings')
    selected = P.intent_helper().check(root)
    app_candidates = {s.get('candidate_path') for s in selected.get('selections', []) if s.get('surface') == 'app'}
    need(selected.get('status') == 'consistent' and artifact in app_candidates,
         'Demo requires the selected App artifact')
    raw = {key: read_bytes(P.relative_file(root, path), MAX_HTML if key == 'html' else MAX_JSON)
           for key, path in (('html', artifact), ('spec', spec_artifact), ('demo', demo_artifact))}
    hashes = {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
    reviewed_artifacts = demo_candidate_bindings(root, metadata['id'], gate,
        {artifact: hashes['html'], spec_artifact: hashes['spec'], demo_artifact: hashes['demo']}, P)
    spec = create_spec_check(decode(raw['spec'], 'object'))
    demo = decode(raw['demo'], 'object')
    need(set(demo) == {'schema_version', 'kind', 'html', 'create_spec', 'destination', 'minimums', 'pending_observations'}
         and type(demo['schema_version']) is int and demo['schema_version'] == 1
         and demo['kind'] == 'native_demo_scope', 'Exact demo scope required')
    need(demo['html'] == {'path': artifact, 'sha256': hashes['html']} and
         demo['create_spec'] == {'path': spec_artifact, 'sha256': hashes['spec']}, 'Demo source bindings differ')
    destination = demo['destination']
    need(type(destination) is dict and set(destination) == {'origin', 'model_id', 'document_id', 'operation', 'principal', 'audience'}
         and destination['origin'] == spec['base_url'] and destination['model_id'] == spec['model_id']
         and destination['document_id'] == spec['slug'] and destination['operation'] == 'initial_create',
         'Demo destination contradicts the exact create specification')
    principal = destination['principal']
    need(type(principal) is dict and set(principal) == {'key_scope', 'user_id', 'membership_id'}
         and principal['key_scope'] == 'user' and
         all(type(principal[k]) is str and ID.fullmatch(principal[k]) for k in ('user_id', 'membership_id')),
         'Demo requires one explicit user-scoped test principal')
    need(destination['audience'] == {'kind': 'named_test_principal', 'membership_id': principal['membership_id']},
         'Demo audience must be the same named test principal')
    minimums = demo['minimums']
    need(type(minimums) is dict and set(minimums) == {'security', 'numerical', 'permission', 'design'},
         'Every demo minimum must be explicitly accounted for')
    for item in minimums.values():
        need(type(item) is dict and set(item) == {'status', 'scope', 'evidence'} and item['status'] == 'resolved'
             and type(item['scope']) is str and 0 < len(item['scope'].strip()) <= 2048
             and type(item['evidence']) is list and 0 < len(item['evidence']) <= 32,
             'Unresolved numerical, permission, security or design minimum blocks demo preparation')
        for evidence in item['evidence']:
            demo_pin(root, evidence, P)
    reviews = gate['reviews']
    need(set(reviews) == {'security', 'ui_ux', 'product_owner', 'qa'}, 'All four current consultations required for demo')
    need(all(reviews[k]['outcome'] == 'resolved' for k in ('security', 'product_owner')),
         'Security and product-owner consultations must be resolved')
    need(all(reviews[k]['outcome'] in {'resolved', 'unobserved'} for k in ('ui_ux', 'qa')),
         'Known review defects block demonstration')
    pending = demo['pending_observations']
    need(type(pending) is list and 0 < len(pending) <= 2, 'Explicit observation-only demo gaps required')
    scopes = set()
    for item in pending:
        need(type(item) is dict and set(item) == {'scope', 'basis', 'reason', 'required_observation'}
             and item['scope'] in {'ui_ux', 'qa'} and item['scope'] not in scopes
             and item['basis'] in {'rendered', 'native', 'human'}
             and all(type(item[k]) is str and 0 < len(item[k].strip()) <= 2048 for k in ('reason', 'required_observation')),
             'Only explicit UI/QA observation gaps may remain pending')
        review = reviews[item['scope']]
        need(review['outcome'] == 'unobserved' and review['basis'] == item['basis'],
             'Demo pending scope contradicts the current consultation')
        scopes.add(item['scope'])
    need(scopes == {key for key, review in reviews.items() if review['outcome'] == 'unobserved'},
         'Account for every unobserved consultation')
    body = create_body(spec, raw['html'].decode('utf-8'))
    need(P.stage_require(root, 'review')['tail_sha256'] == gate['tail_sha256'], 'Engagement changed during demo preparation')
    return {'schema_version': 1, 'kind': 'native_demo_create_request', 'base_url': spec['base_url'],
            'destination': destination, 'engagement': {'project_id': metadata['id'], 'artifact': artifact,
                'spec_artifact': spec_artifact, 'demo_artifact': demo_artifact, 'html_sha256': hashes['html'],
                'spec_sha256': hashes['spec'], 'demo_sha256': hashes['demo'], 'candidate_sha256': gate['candidate_sha256'],
                'stage_bindings': gate['stage_bindings'], 'tail_sha256': gate['tail_sha256']},
            'query_sha256': digest(spec['queryPresentations']), 'request_sha256': digest(body),
            'reviewed_artifacts': reviewed_artifacts,
            'request': {'method': 'POST', 'path': '/api/v2/documents', 'body': body},
            'consultations': {key: review['event_sha256'] for key, review in reviews.items()},
            'minimums': minimums, 'pending_observations': pending, 'creation_scope': 'new_demo_document',
            'publishes_immediately': True, 'execution_authorized': False, 'publication_authorized': False,
            'release_validated': False, 'native_verified': False, 'audience_verified': False,
            'claims_authenticated': False,
            'note': 'Offline demo preparation only. Recorded minima are supplied claims, not verified access. '
                    'A trusted operator must independently authorize and enforce this exact destination, user '
                    'and audience before immediate publication. Personal-folder defaults do not prove privacy. '
                    'Do not retry an uncertain create, overwrite a conflict or call this a validated release.'}


def create_capture(capture, origin, method, path, status):
    """Retained host observations, never authenticated receipts or permissions."""
    need(type(capture) is dict and set(capture) == {'base_url', 'method', 'path', 'status', 'body'}
         and capture['base_url'] == origin and capture['method'] == method and capture['path'] == path
         and type(capture['status']) is int and capture['status'] == status
         and type(capture['body']) is dict and capture['body'], 'Mismatched create/readback capture route or status')
    need(len(encoded(capture)) <= MAX_JSON, 'Oversized capture')
    return capture['body']


def verify_create(prepared, created, document, app, *, project, artifact, spec_artifact):
    """Compare supplied create + per-create GET captures with current reviewed bytes.

    Nothing is transported. No unknown/default/generated fields are silently
    normalized. Capture consistency cannot qualify identity, permissions, native
    runtime callbacks, render quality or independent publication authorization.
    """
    expected = prepare_create(project=project, artifact=artifact, spec_artifact=spec_artifact)
    return verify_create_captures(expected, prepared, created, document, app)


def verify_create_captures(expected, prepared, created, document, app):
    """Shared exact-capture comparison; caller supplies its separately gated route."""
    need(type(prepared) is dict and encoded(prepared) == encoded(expected), 'Prepared create request drift')
    origin, body = expected['base_url'], expected['request']['body']
    response = create_capture(created, origin, 'POST', '/api/v2/documents', 201)
    need(set(response) <= {'identifier', 'name', 'description', 'warnings'}
         and {'identifier', 'name', 'description'} <= set(response)
         and type(response['identifier']) is str and response['identifier'] == body['identifier'],
         'Unsupported create response')
    identifier = response['identifier']
    route = '/api/v2/documents/' + identifier
    doc = create_capture(document, origin, 'GET', route, 200)
    app_body = create_capture(app, origin, 'GET', route + '/app', 200)
    need(type(doc.get('workbookModelId')) is str and ID.fullmatch(doc['workbookModelId']),
         'Created workbook model identifier missing')
    findings = []
    if response['name'] != body['name'] or response['description'] != body['description']:
        findings.append('create_metadata_mismatch')
    if response.get('warnings'):
        findings.append('create_warnings_require_review')
    if set(doc) != {'app', 'description', 'modelId', 'name', 'queryPresentations', 'workbookModelId'}:
        findings.append('unsupported_document_readback_fields')
    if any(doc.get(k) != body[k] for k in ('name', 'description', 'modelId')):
        findings.append('document_metadata_or_model_mismatch')
    if doc.get('app') != {'url': route + '/app'}:
        findings.append('app_route_mismatch')
    if encoded(doc.get('queryPresentations')) != encoded(body['queryPresentations']):
        findings.append('query_presentations_mismatch')
    if set(app_body) != {'html', 'settings'}:
        findings.append('unsupported_app_readback_fields')
    if app_body.get('html') != body['app']['html']:
        findings.append('html_readback_mismatch')
    if encoded(app_body.get('settings')) != encoded(body['app']['settings']):
        findings.append('settings_readback_mismatch')
    return {'status': 'readback_mismatch' if findings else 'exact_create_readback', 'findings': findings,
            'request_sha256': expected['request_sha256'],
            'capture_sha256': {'created': digest(created), 'document': digest(document), 'app': digest(app)},
            'derived_identifiers': {'document': identifier, 'workbook_model': doc['workbookModelId'],
                                    'query_keys': list(body['queryPresentations']['order'])},
            'native_verified': False, 'publication_authorized': False,
            'note': 'Consistency of supplied per-create captures only. Identity, permissions, real host '
                    'execution, initial publication and App runtime/rendering need separate evidence.'}


def verify_demo(prepared, created, document, app, identity, *, project, artifact, spec_artifact, demo_artifact):
    expected = prepare_demo(project=project, artifact=artifact, spec_artifact=spec_artifact, demo_artifact=demo_artifact)
    result = verify_create_captures(expected, prepared, created, document, app)
    principal = expected['destination']['principal']
    who = create_capture(identity, expected['base_url'], 'GET',
                         '/api/v1/whoami?modelId=' + expected['destination']['model_id'], 200)
    need(who.get('keyScope') == principal['key_scope'] and type(who.get('user')) is dict
         and who['user'].get('id') == principal['user_id']
         and who['user'].get('membershipId') == principal['membership_id'], 'Demo principal readback mismatch')
    result['capture_sha256']['identity'] = digest(identity)
    result.update(status='exact_demo_readback' if not result['findings'] else 'readback_mismatch',
                  destination=expected['destination'], pending_observations=expected['pending_observations'],
                  execution_authorized=False, release_validated=False, audience_verified=False,
                  claims_authenticated=False,
                  note='Supplied demo capture consistency only. Identity and audience are not authenticated; '
                       'pending native/rendered/human observations and separate release evidence remain outstanding.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['cli-json', 'route-check', 'query-body', 'plan-check',
        'app-prepare', 'app-verify', 'app-create-prepare', 'app-create-verify', 'app-demo-prepare', 'app-demo-verify'])
    parser.add_argument('--input', required=True, help='Response file or JSON request describing local input paths')
    parser.add_argument('--output', required=True, help='New private output file; never overwrite')
    parser.add_argument('--project', help='Required engagement root for App preparation and create verification')
    parser.add_argument('--shape', choices=['object', 'list'], default='object')
    args = parser.parse_args()
    output = Path(args.output).absolute()
    need(not output.exists() and output.parent.is_dir()
         and not any(p.is_symlink() for p in (output, *output.parents)), 'Output must be new and canonical')
    base = Path(args.input).absolute().parent
    def local(path):
        need(type(path) is str, 'Input path required')
        value = Path(path)
        return value if value.is_absolute() else base / value
    if args.operation == 'cli-json':
        value = decode(read_bytes(args.input, MAX_JSON), args.shape)
        result = {'status': 'response_shape_valid', 'shape': args.shape, 'response_sha256': digest(value)}
    else:
        record = read(args.input)
        if args.operation == 'route-check':
            result = route_check(record)
        elif args.operation == 'query-body':
            result = query_body(record['query'], record['model_id'], record.get('user_id'))
        elif args.operation == 'plan-check':
            result = plan_check(record)
        elif args.operation == 'app-prepare':
            need(args.project is not None, 'Engagement required for App preparation')
            P = project_helper()
            root, _ = P.load_project(args.project)
            raw = read_bytes(P.relative_file(root, record['html']), MAX_HTML)
            result = prepare_app(record['target'], read(local(record['baseline'])),
                                 read(local(record['current'])), raw.decode('utf-8'),
                                 project=args.project, artifact=record['html'])
        elif args.operation == 'app-verify':
            result = verify_app(read(local(record['prepared'])), read(local(record['baseline'])), read(local(record['after'])))
        else:
            need(args.project is not None, 'Engagement required for App creation preparation/readback')
            if args.operation == 'app-demo-prepare':
                need(set(record) == {'html', 'spec', 'demo'}, 'Exact demo input paths required')
                result = prepare_demo(project=args.project, artifact=record['html'], spec_artifact=record['spec'],
                                      demo_artifact=record['demo'])
            elif args.operation == 'app-demo-verify':
                need(set(record) == {'html', 'spec', 'demo', 'prepared', 'created', 'document', 'app', 'identity'},
                     'Exact demo readback input paths required')
                result = verify_demo(read(local(record['prepared'])), read(local(record['created'])),
                    read(local(record['document'])), read(local(record['app'])), read(local(record['identity'])),
                    project=args.project, artifact=record['html'], spec_artifact=record['spec'], demo_artifact=record['demo'])
            elif args.operation == 'app-create-prepare':
                need(set(record) == {'html', 'spec'}, 'Exact create input paths required')
                result = prepare_create(project=args.project, artifact=record['html'], spec_artifact=record['spec'])
            else:
                need(set(record) == {'html', 'spec', 'prepared', 'created', 'document', 'app'},
                     'Exact create readback input paths required')
                result = verify_create(read(local(record['prepared'])), read(local(record['created'])),
                    read(local(record['document'])), read(local(record['app'])), project=args.project,
                    artifact=record['html'], spec_artifact=record['spec'])
    data = encoded(result) + b'\n'
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    status = result.get('status', 'prepared')
    print(json.dumps({'status': status, 'output': str(output)}))
    return int(status in {'route_incomplete', 'query_needs_review', 'readback_mismatch'})


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        # No raw API errors, paths, row values or candidate HTML in diagnostics.
        raise SystemExit('Authoring input rejected; inspect the retained local captures and contract.')
