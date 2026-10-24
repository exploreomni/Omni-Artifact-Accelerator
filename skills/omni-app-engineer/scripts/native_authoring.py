#!/usr/bin/env python3
"""Offline CLI/API preparation and readback checks for native authoring.

Standard library only. Never reads credentials, connects, runs SQL/HTML, creates
drafts, writes to Omni or confers authority. The host performs authorized official
operations; retained captures are evidence inputs, not authenticated permissions.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

MAX_JSON = 16 * 1024 * 1024
MAX_HTML = 2 * 1024 * 1024
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')


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


def prepare_app(target, baseline, current, html):
    route = snapshot_check(baseline, target)
    snapshot_check(current, target)
    need(digest(baseline) == digest(current), 'Target drift: reconcile before preparing a write')
    need(type(html) is str and 0 < len(html.encode()) <= MAX_HTML and html != baseline['app']['html'],
         'Bounded changed candidate HTML required')
    return {'kind': 'native_app_enhancement_request', 'schema_version': 1,
            'target': target, 'baseline_sha256': digest(baseline),
            'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['cli-json', 'route-check', 'query-body', 'plan-check', 'app-prepare', 'app-verify'])
    parser.add_argument('--input', required=True, help='Response file or JSON request describing local input paths')
    parser.add_argument('--output', required=True, help='New private output file; never overwrite')
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
            raw = read_bytes(local(record['html']), MAX_HTML)
            result = prepare_app(record['target'], read(local(record['baseline'])),
                                 read(local(record['current'])), raw.decode('utf-8'))
        else:
            result = verify_app(read(local(record['prepared'])), read(local(record['baseline'])), read(local(record['after'])))
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
