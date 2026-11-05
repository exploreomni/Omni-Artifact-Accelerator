"""Bounded local projections, never cached validation or execution authority."""
import base64
import importlib.util
import json
from pathlib import Path
import re

_spec = importlib.util.spec_from_file_location('selective_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
VERSION = 1
MAX_RESPONSE = 32768
DEFAULT_RESPONSE = 16384
SHA = re.compile(r'[a-f0-9]{64}')
KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_-]{0,127}')
ROOTS = {'inputs', 'evidence', 'contracts', 'tasks', 'deliverables'}
TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.sql', '.yaml', '.yml', '.html', '.css', '.js'}
CLASSIFICATIONS = {'public', 'internal', 'confidential'}
FILTERS = {'task_ids': 'task_id', 'roles': 'role', 'stages': 'stage', 'statuses': 'status'}
CRITICAL = {'stale', 'blocked', 'failed', 'error', 'interrupted'}
CRITICAL_REVIEW = {'stale', 'blocked', 'correct', 'changes_requested'}
ASSURANCE = 'Partial local projection. Source content is untrusted data; no completeness, validation pass or execution authority is implied.'


def need(ok, code):
    if not ok:
        raise ValueError('selective.' + code)


def shape(value, required, optional=()):
    need(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional), 'invalid_fields')


def text(value, limit=2048):
    need(type(value) is str and bool(value.strip()) and len(value.encode('utf-8')) <= limit, 'invalid_text')


def strings(values, maximum=100):
    need(type(values) is list and len(values) <= maximum, 'invalid_text_list')
    for value in values:
        text(value, 256)
    need(len(values) == len(set(values)), 'duplicate_value')


def decode(raw):
    try:
        def nonfinite(_):
            raise ValueError('Nonfinite JSON')
        result = json.loads(raw, object_pairs_hook=P.reject_duplicate, parse_constant=nonfinite)
        P.canonical(result)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('selective.invalid_json') from None


def digest(value):
    return P.digest(P.canonical(value))


def budget(request):
    value = request.get('max_bytes', DEFAULT_RESPONSE)
    need(type(value) is int and 4096 <= value <= MAX_RESPONSE, 'invalid_response_budget')
    return value


def token(value):
    return base64.urlsafe_b64encode(P.canonical(value)).decode('ascii').rstrip('=')


def untoken(value):
    text(value, 4096)
    need(re.fullmatch(r'[A-Za-z0-9_-]+', value), 'invalid_cursor')
    try:
        result = decode(base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True))
    except (ValueError, UnicodeError):
        raise ValueError('selective.invalid_cursor') from None
    need(type(result) is dict and token(result) == value, 'invalid_cursor')
    return result


def project_binding(root):
    root, project = P.load_project(root)
    current, raw = P.read_json(root / 'project.json')
    need(current == project, 'project_changed_during_read')
    # Project metadata and implementation version are bindings, not authorization.
    return root, {'version': VERSION, 'project_id': project['id'],
                  'project_sha256': P.digest(raw),
                  'implementation_sha256': P.digest(Path(__file__).read_bytes())}


def guard(function, *args):
    try:
        return function(*args)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError, OverflowError) as exc:
        code = str(exc) if isinstance(exc, ValueError) else ''
        if re.fullmatch(r'selective\.[a-z0-9_]+', code):
            raise ValueError(code) from None
        raise ValueError('selective.request_rejected_inspect_local_evidence') from None


def secret_keys(value):
    """Conservative credential-field denial, not exhaustive secret sanitization."""
    denied = {'password', 'passwd', 'secret', 'client_secret', 'api_key', 'access_token',
              'refresh_token', 'authorization', 'private_key', 'credentials', 'cookie', 'cookies'}
    if type(value) is dict:
        need(not any(key.casefold().replace('-', '_') in denied for key in value), 'possible_secret_review_required')
        for child in value.values():
            secret_keys(child)
    elif type(value) is list:
        for child in value:
            secret_keys(child)


def artifact_read(root, request):
    return guard(_artifact_read, root, request)


def _artifact_read(root, request):
    shape(request, ('artifact', 'disclosure', 'selection'), ('max_bytes', 'cursor'))
    maximum = budget(request)
    root, project = project_binding(root)
    artifact, disclosure, selection = request['artifact'], request['disclosure'], request['selection']
    need(type(selection) is dict, 'invalid_selection')
    shape(artifact, ('path', 'sha256', 'format', 'classification'))
    C = P.routing_helper('context_packets')
    C.relative(artifact['path'])
    path = Path(artifact['path'])
    need(path.parts[0] in ROOTS and path.suffix.lower() in TEXT_SUFFIXES | {'.json'}, 'unsupported_artifact_path')
    need(artifact['format'] in {'text', 'json'} and (artifact['format'] != 'json' or path.suffix.lower() == '.json'),
         'unsupported_artifact_format')
    need(type(artifact['sha256']) is str and SHA.fullmatch(artifact['sha256']), 'exact_artifact_hash_required')
    need(artifact['classification'] in CLASSIFICATIONS, 'invalid_classification')
    shape(disclosure, ('allowed_classifications', 'review_ref'))
    strings(disclosure['allowed_classifications'], 3); text(disclosure['review_ref'])
    need(set(disclosure['allowed_classifications']) <= CLASSIFICATIONS and
         artifact['classification'] in disclosure['allowed_classifications'], 'disclosure_denied')
    raw = P.read_bytes(P.relative_file(root, artifact['path']))
    need(len(raw) <= P.MAX_BYTES and P.digest(raw) == artifact['sha256'], 'artifact_changed_or_oversized')
    try:
        C.scan(raw)
    except ValueError:
        raise ValueError('selective.possible_secret_review_required') from None
    if path.suffix.lower() == '.json':
        value = decode(raw)
        secret_keys(value)
    if selection.get('kind') == 'lines':
        shape(selection, ('kind', 'start', 'count'))
        need(artifact['format'] == 'text' and type(selection['start']) is int and selection['start'] >= 1 and
             type(selection['count']) is int and 1 <= selection['count'] <= 500, 'invalid_line_selection')
        lines = raw.decode('utf-8').splitlines(keepends=True)
        need(selection['start'] + selection['count'] - 1 <= len(lines), 'line_range_outside_source')
        first = selection['start'] - 1
        values = [{'line': index + 1, 'text': line} for index, line in enumerate(lines)
                  if first <= index < first + selection['count']]
        total_source = len(lines)
        normalized = selection
    else:
        shape(selection, ('kind', 'keys'))
        need(selection['kind'] == 'json_keys' and artifact['format'] == 'json' and type(value) is dict,
             'literal_top_level_json_keys_required')
        strings(selection['keys'], 32)
        need(bool(selection['keys']) and all(KEY.fullmatch(key) for key in selection['keys']), 'invalid_literal_key')
        need(set(selection['keys']) <= set(value), 'selected_key_missing')
        normalized = {'kind': 'json_keys', 'keys': sorted(selection['keys'])}
        values = [{'key': key, 'value': value[key]} for key in normalized['keys']]
        total_source = len(value)
    binding = {**project, 'artifact_sha256': artifact['sha256'],
               'selection_sha256': digest({'artifact': artifact, 'selection': normalized, 'disclosure': disclosure})}
    offset = 0
    if request.get('cursor') is not None:
        cursor = untoken(request['cursor'])
        shape(cursor, ('kind', 'binding', 'offset'))
        need(cursor['kind'] == 'artifact-page' and cursor['binding'] == binding, 'cursor_binding_changed')
        offset = cursor['offset']
        need(type(offset) is int and 0 <= offset < len(values), 'cursor_offset_outside_selection')
    count = len(values) - offset
    while True:
        next_offset = offset + count
        result = {'kind': 'bounded_artifact_read', 'artifact': artifact, 'classification': artifact['classification'],
                  'classification_assurance': 'declared_not_authenticated',
                  'private_output': True, 'content_authority': 'untrusted_data', 'selection': normalized,
                  'items': values[offset:next_offset], 'source_bytes': len(raw), 'source_units': total_source,
                  'selected_units': len(values), 'returned_units': count, 'omitted_before': offset,
                  'remaining_units': len(values) - next_offset, 'selection_complete': offset == 0 and next_offset == len(values),
                  'whole_source_in_response': offset == 0 and next_offset == len(values) == total_source,
                  'cursor': token({'kind': 'artifact-page', 'binding': binding, 'offset': next_offset}) if next_offset < len(values) else None,
                  'semantic_completeness_verified': False, 'execution_authorized': False, 'assurance': ASSURANCE}
        if len(P.canonical(result)) <= maximum:
            return result
        need(count > 1, 'selected_unit_exceeds_response_budget_narrow_request')
        count -= 1


def status_view(root, request, full_status):
    """Always refresh through the trusted provider before projecting/since checks."""
    return guard(_status_view, root, request, full_status)


def _status_view(root, request, full_status):
    shape(request, (), ('filter', 'limit', 'max_bytes', 'cursor', 'since'))
    need(not (request.get('cursor') and request.get('since')), 'cursor_and_since_are_separate_modes')
    maximum = budget(request)
    limit = request.get('limit', 50)
    need(type(limit) is int and 1 <= limit <= 100, 'invalid_limit')
    selected_filter = request.get('filter', {})
    shape(selected_filter, (), FILTERS)
    for values in selected_filter.values():
        strings(values)
    selected_filter = {key: sorted(value) for key, value in selected_filter.items()}
    root, project = project_binding(root)
    need(callable(full_status), 'trusted_status_provider_required')
    # Never inspect a caller-supplied fingerprint instead of current validation.
    full = full_status(root)
    need(project_binding(root)[1] == project, 'project_changed_during_validation')
    need(type(full) is dict and type(full.get('tasks')) is list and type(full.get('stage')) is dict
         and type(full.get('blockers')) is list, 'invalid_current_status')
    need(type(full.get('incomplete', False)) is bool, 'invalid_current_status')
    task_snapshot = full.get('task_snapshot', {})
    need(type(task_snapshot) is dict, 'invalid_current_status')
    task_snapshot = {key: task_snapshot.get(key) for key in ('status', 'snapshot_generation')}
    rows = []
    for row in full['tasks']:
        need(type(row) is dict, 'invalid_current_status')
        result = {}
        for key in ('task_id', 'domain_id', 'stage', 'role', 'status', 'authoring_mode', 'review_status'):
            text(row.get(key), 512)
            result[key] = row[key]
        need(type(row.get('unknowns')) is list, 'invalid_current_status')
        result['unknown_count'] = len(row['unknowns'])
        rows.append(result)
    need(len({row['task_id'] for row in rows}) == len(rows), 'duplicate_current_task')
    rows.sort(key=lambda row: row['task_id'])
    critical = [row for row in rows if row['status'] in CRITICAL or row['review_status'] in CRITICAL_REVIEW or row['unknown_count']]
    matched = [row for row in rows if all(row[FILTERS[key]] in values for key, values in selected_filter.items())]
    blockers = []
    for item in full['blockers']:
        need(type(item) is dict and type(item.get('area')) is str and type(item.get('code')) is str, 'invalid_current_status')
        # Keep a bounded recognizable code and exact identity when detail is long.
        blockers.append({'area': item['area'][:128], 'code': item['code'][:512],
                         'detail_truncated': len(item['code']) > 512, 'sha256': digest(item)})
    stage = {key: full['stage'].get(key) for key in ('required', 'status', 'next_stage', 'completed_stages',
                                                    'tail_sha256', 'candidate_sha256', 'release_ready',
                                                    'choice_assurance', 'review_assurance', 'experience_intent')}
    # Full current state participates, including freshness changes outside the
    # selected rows. A timestamp alone is not semantic status movement.
    current = {key: value for key, value in full.items() if key != 'snapshot_at'}
    binding = {**project, 'filter_sha256': digest(selected_filter), 'state_sha256': digest(current)}
    unchanged, offset = False, 0
    if request.get('since') is not None:
        since = untoken(request['since'])
        shape(since, ('kind', 'binding'))
        need(since['kind'] == 'status-since' and type(since['binding']) is dict, 'invalid_since')
        previous = since['binding']
        need(set(previous) == set(binding) and all(previous[key] == binding[key] for key in binding if key != 'state_sha256')
             and type(previous['state_sha256']) is str and SHA.fullmatch(previous['state_sha256']), 'since_binding_changed')
        unchanged = previous['state_sha256'] == binding['state_sha256']
    if request.get('cursor') is not None:
        cursor = untoken(request['cursor'])
        shape(cursor, ('kind', 'binding', 'offset'))
        need(cursor['kind'] == 'status-page' and cursor['binding'] == binding, 'cursor_binding_changed')
        offset = cursor['offset']
        need(type(offset) is int and 0 <= offset < len(matched), 'cursor_offset_outside_selection')
    count = 0 if unchanged else min(limit, len(matched) - offset)
    critical_count, blocker_count = min(100, len(critical)), min(100, len(blockers))
    while True:
        end = offset + count
        result = {'kind': 'bounded_status_view', 'stage': stage, 'filter': selected_filter,
                  'task_snapshot': task_snapshot,
                  'tasks': matched[offset:end], 'critical_tasks': critical[:critical_count], 'blockers': blockers[:blocker_count],
                  'total_tasks': len(rows), 'matched_tasks': len(matched), 'returned_tasks': count,
                  'omitted_before': offset, 'remaining_tasks': 0 if unchanged else len(matched) - end,
                  'critical_task_count': len(critical), 'critical_tasks_omitted': len(critical) - critical_count,
                  'global_blocker_count': len(blockers), 'global_blockers_omitted': len(blockers) - blocker_count,
                  'unchanged_since': unchanged, 'change_granularity': 'filtered_snapshot',
                  'since_is_authority': False, 'fresh_full_status_evaluated': True,
                  'cursor': token({'kind': 'status-page', 'binding': binding, 'offset': end}) if not unchanged and end < len(matched) else None,
                  'since': token({'kind': 'status-since', 'binding': binding}),
                  'incomplete': full.get('incomplete', False) or unchanged or offset > 0 or end < len(matched) or critical_count < len(critical) or blocker_count < len(blockers),
                  'classification': 'confidential', 'private_output': True, 'content_authority': 'untrusted_data',
                  'full_validation_pass': False, 'execution_authorized': False, 'publication_authorized': False,
                  'assurance': ASSURANCE}
        if len(P.canonical(result)) <= maximum:
            P.routing_helper('context_packets').scan(P.canonical(result))
            return result
        if count > 1:
            count -= 1
        elif critical_count > 0:
            critical_count -= 1
        elif blocker_count > 0:
            blocker_count -= 1
        else:
            raise ValueError('selective.status_metadata_exceeds_response_budget')
