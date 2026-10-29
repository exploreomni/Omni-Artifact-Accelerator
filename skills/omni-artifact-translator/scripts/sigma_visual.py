"""Passive Sigma evidence verification and exact result normalization.

No upstream engine imports, source execution, credential acquisition or writes.
Hashes establish supplied-byte consistency, never authenticated provenance.
"""
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
from urllib.parse import urlsplit

LEGACY = 'sigma-visual-capture.v1'
SCHEMA = 'sigma-source-evidence-bundle.v1'
PACKAGE = 'sigma-prepush-package.v1'
MAX_BYTES = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILES = 512
STATE_KEYS = {'filters', 'parameters', 'timezone', 'locale', 'cache', 'principal'}
SELECTION_KEYS = {'mode', 'version', 'tag', 'view_id', 'reference'}
ARTIFACT_KINDS = {'rest_snapshot', 'workbook_contents', 'page_render', 'element_render', 'results', 'mcp_capture', 'unknown'}
CHANNELS = {'rest_v2', 'workbook_contents_beta', 'render_export', 'passive_mcp', 'supplied', 'unknown'}
SECRET_KEYS = {'password', 'passwd', 'pwd', 'apitoken', 'apikey', 'accesstoken', 'refreshtoken',
               'clientsecret', 'authorization', 'cookie', 'setcookie', 'privatekey', 'credentials', 'credential'}


def need(value, code):
    if not value:
        raise ValueError('sigma.' + code)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 4096 and not any(ord(c) < 32 for c in value)


def digest(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def module(name):
    need(name in {'powerbi_capture_files', 'powerbi_visual', 'migration_sources', 'translate_artifact'}, 'module_not_allowed')
    path = Path(__file__).with_name(name + '.py').absolute()
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('sigma_local_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def decode(raw):
    need(type(raw) is bytes and len(raw) <= MAX_BYTES, 'json_byte_limit')
    return module('powerbi_capture_files').decode(raw)


def _bounded(value):
    module('translate_artifact').bounded(value)
    _screen(value)


def _screen(value):
    stack = [value]
    while stack:
        row = stack.pop()
        if type(row) is dict:
            for key, val in row.items():
                normal = re.sub('[^a-z]', '', key.lower())
                need(normal not in SECRET_KEYS or val in (None, '', '[REDACTED]') or val == {'redacted': 'secret'},
                     'credential_bearing_evidence')
                stack.append(val)
        elif type(row) is list:
            stack.extend(row)
        elif type(row) is str:
            need(not re.search(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}', row), 'credential_bearing_evidence')
            # Strings can contain retained nested JSON/configuration. These are
            # inspected as inert text, never evaluated or recursively executed.
            pattern = r'''(?ix)(?:["']?(?:api[_-]?token|api[_-]?key|access[_-]?token|client[_-]?secret|password|authorization|cookie|credentials?)["']?\s*[:=]\s*["']?)([^\s,;"'}]+)'''
            for found in re.finditer(pattern, row):
                need(found.group(1) in ('[REDACTED]', 'null', 'None'), 'credential_bearing_evidence')


def _path(value):
    need(text(value), 'file_path')
    path = PurePosixPath(value)
    need(value not in ('.', '') and not path.is_absolute() and path.as_posix() == value and '..' not in path.parts
         and len(path.parts) <= 32 and not any(c in value for c in ('\\', ':', '\x00')),
         'file_path')
    return value


def _paths(values):
    seen, prefixes = set(), {}
    for name in values:
        _path(name)
        parts = name.split('/')
        for size in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:size])
            folded = unicodedata.normalize('NFC', prefix).casefold()
            need(folded not in prefixes or prefixes[folded] == prefix, 'file_path_collision')
            prefixes[folded] = prefix
        key = unicodedata.normalize('NFC', name).casefold()
        need(key not in seen and not any(key.startswith(v + '/') or v.startswith(key + '/') for v in seen),
             'file_path_collision')
        seen.add(key)


def _read(root, relative, maximum=MAX_BYTES):
    """Open each directory without following links; reject FIFO/device before read."""
    _path(relative)
    root = Path(root).absolute()
    need('..' not in root.parts, 'root_path')
    fd = None
    try:
        fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for component in (*root.parts[1:], *PurePosixPath(relative).parts[:-1]):
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        child = os.open(PurePosixPath(relative).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        os.close(fd)
        fd = child
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum, 'file_type_or_size')
        chunks, count = [], 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
            need(count <= maximum, 'file_byte_limit')
        after = os.fstat(fd)
        need(before.st_size == after.st_size == count and before.st_mtime_ns == after.st_mtime_ns
             and before.st_ino == after.st_ino, 'file_changed_during_read')
        return b''.join(chunks)
    except OSError:
        raise ValueError('sigma.file_unavailable_or_unsafe') from None
    finally:
        if fd is not None:
            os.close(fd)


def _pin(value):
    need(type(value) is dict and set(value) == {'path', 'sha256', 'bytes'} and digest(value.get('sha256'))
         and type(value.get('bytes')) is int and 0 < value['bytes'] <= MAX_BYTES, 'file_pin')
    _path(value['path'])


def _read_pin(root, pin):
    _pin(pin)
    raw = _read(root, pin['path'])
    need(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'evidence_bytes_changed')
    return raw


def _origin(value):
    need(text(value), 'source_origin')
    parsed = urlsplit(value)
    need(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
         and not parsed.path and not parsed.query and not parsed.fragment and value == 'https://' + parsed.netloc,
         'source_origin')
    try:
        parsed.port
    except ValueError:
        raise ValueError('sigma.source_origin') from None


def _time(value):
    need(text(value), 'timestamp')
    try:
        observed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(observed.tzinfo is not None, 'timestamp_timezone')
    except ValueError:
        raise ValueError('sigma.timestamp') from None


def _pointer(value, pointer):
    need(type(pointer) is str and (pointer == '' or pointer.startswith('/')), 'definition_pointer')
    for part in pointer.split('/')[1:]:
        need(re.search(r'~(?![01])', part) is None, 'definition_pointer_escape')
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(part in value, 'definition_pointer_missing')
            value = value[part]
        elif type(value) is list:
            need(re.fullmatch('0|[1-9][0-9]*', part) and int(part) < len(value), 'definition_pointer_index')
            value = value[int(part)]
        else:
            raise ValueError('sigma.definition_pointer_missing')
    return value


def validate_selection(value):
    need(type(value) is dict and set(value) == SELECTION_KEYS and text(value.get('reference')), 'selection')
    need(value['mode'] in {'tagged', 'published', 'draft', 'saved_view', 'unknown'}, 'selection_mode')
    for field in ('version', 'tag', 'view_id'):
        need(value[field] is None or text(value[field]), 'selection_field')
    need(value['mode'] != 'tagged' or text(value['tag']) and text(value['version']), 'tag_version_required')
    need(value['mode'] != 'saved_view' or text(value['view_id']), 'view_identity_required')
    return value


def _same_selection(left, right):
    # Evidence references can differ while describing the same exact selection.
    return all(left[k] == right[k] for k in SELECTION_KEYS - {'reference'})


def validate_state(value):
    need(type(value) is dict and set(value) == STATE_KEYS, 'state')
    need(all(value[k] is None or type(value[k]) is dict for k in ('filters', 'parameters')), 'state_controls')
    need(all(value[k] is None or text(value[k]) for k in ('timezone', 'locale', 'principal')), 'state_identity')
    need(value['cache'] is None or type(value['cache']) in (dict, str), 'state_cache')
    _screen(value)
    return value


def _bridge(value, method):
    # Call the existing bounded structural validator directly, avoiding a new
    # upstream dependency and avoiding translation dispatch recursion.
    t, m = module('translate_artifact'), module('migration_sources')
    helpers = {key: getattr(t, key) for key in ('base', 'add_asset', 'gap', 'rows', 'require', 'decode', 'facet', 'identity')}
    bridge = m.Bridge(helpers)
    result = t.base(value, encoded(value), 'sigma', 'supplied_sigma_evidence')
    bridge.context(result, value)
    getattr(bridge, method)(result, value)
    return result


def _validate_v2_capture(value):
    """Validate the source agent's v2 request in its unchanged v1 envelope."""
    req, original = value.get('request'), value.get('original_request')
    need(type(req) is dict and type(original) is dict, 'visual_request')
    need(value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'})
         and value.get('request_sha256') == sha(req) and value.get('original_request_sha256') == sha(original),
         'visual_capture_hash')
    def subset(effective, supplied):
        if type(supplied) is dict:
            return type(effective) is dict and all(k in effective and subset(effective[k], v) for k, v in supplied.items())
        return effective == supplied
    need(subset(req, original) and req.get('schema_version') == 'sigma-visual-capture-request.v2'
         and value.get('capture_id') == req.get('capture_id'), 'visual_original_request')
    for key in ('capture_id', 'workbook_id', 'page_id', 'expected_organization_id', 'expected_user_id', 'principal_ref'):
        need(text(req.get(key)), 'visual_request_identity')
    page = req.get('target_kind') == 'page'
    need(req.get('target_kind') in {'element', 'page'} and
         (req.get('element_id') is None if page else text(req.get('element_id'))), 'visual_target_kind')
    freeze = req.get('source_freeze')
    need(type(freeze) is dict and freeze.get('strategy') == 'version_tag' and text(freeze.get('workbook_tag_name')),
         'visual_tag_required')
    mid, version = req.get('data_model_id'), freeze.get('data_model_document_version')
    need((mid is None and version is None) or text(mid) and type(version) is int and version > 0, 'visual_model_pair')
    need(value.get('status') in {'complete', 'partial', 'blocked'} and value.get('target_write_authority') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed',
         'visual_authority_or_status')
    need(type(value.get('journal_revision')) is int and value['journal_revision'] > 0
         and (value.get('previous_content_hash') is None or digest(value['previous_content_hash'])), 'visual_revision')
    need(req.get('evidence_mode') in {'synthetic_fixture', 'live_tenant'} and value.get('evidence_mode') == req['evidence_mode']
         and type(value.get('gaps')) is list and all(text(g) for g in value['gaps']), 'visual_evidence_mode_or_gaps')
    jobs, attachments = value.get('jobs'), value.get('attachments')
    kinds = {'png'} if page else {'png', 'json'}
    need(type(jobs) is list and len(jobs) == len(kinds) and all(type(j) is dict for j in jobs)
         and {j.get('kind') for j in jobs} == kinds and type(attachments) is list
         and all(type(a) is dict for a in attachments), 'visual_job_set')
    by_kind, query_ids = {}, set()
    for job in jobs:
        kind = job['kind']
        body = {'tag': freeze['workbook_tag_name'], 'pageId' if page else 'elementId': req['page_id'] if page else req['element_id'],
                'parameters': req.get('parameters'), 'format': {'type': kind}}
        if kind == 'json':
            body['rowLimit'] = req.get('row_limit')
        need(job.get('request_body') == body and job.get('request_sha256') == sha(body) and text(job.get('status')),
             'visual_job_request_mismatch')
        qid = job.get('query_id')
        if qid is not None:
            need(text(qid) and qid not in query_ids, 'visual_query_identity')
            query_ids.add(qid)
        if job.get('creation_response') is not None:
            need(type(job['creation_response']) is dict and job['creation_response'].get('queryId') == qid,
                 'visual_query_response')
        by_kind[kind] = job
    source = value.get('source')
    if source is None:
        need(not attachments and value['status'] != 'complete' and all(j['status'] != 'downloaded' for j in jobs),
             'visual_source_missing')
        return
    need(type(source) is dict and type(source.get('tagged_snapshot')) is dict and type(source.get('baseline')) is dict,
         'visual_source')
    snapshot, baseline = source['tagged_snapshot'], source['baseline']
    need(source.get('tagged_snapshot_sha256') == sha(snapshot) and source.get('baseline_sha256') == sha(baseline),
         'visual_source_hash')
    need(snapshot.get('workbookId') == req['workbook_id'] and snapshot.get('tag') == freeze['workbook_tag_name']
         and snapshot.get('coherence') == source.get('coherence') == 'unchanged_before_after_not_atomic', 'visual_selection')
    identity = baseline.get('identity')
    need(type(identity) is dict and identity.get('organizationId') == req['expected_organization_id']
         and identity.get('userId') == req['expected_user_id'], 'visual_principal')
    def coherence(observation):
        need(type(observation) is dict and type(observation.get('identity')) is dict, 'visual_observation')
        return sha({**observation, 'identity': {k: observation['identity'].get(k) for k in ('organizationId', 'userId')}})
    need(source.get('coherence_sha256') == coherence(baseline), 'visual_coherence_hash')
    revision = {'workbook': baseline.get('workbook'), 'tags': baseline.get('tags')}
    need(snapshot.get('revisionEvidence') == revision and snapshot.get('revisionEvidenceSha256') == sha(revision),
         'visual_revision_binding')
    def native_id(row, *keys):
        need(type(row) is dict, 'visual_native_identity')
        candidates = [row[k] for k in keys if row.get(k) is not None]
        need(all(text(x) for x in candidates), 'visual_native_identity')
        values = set(candidates)
        need(len(values) == 1, 'visual_native_identity')
        return next(iter(values))
    need(native_id(baseline.get('workbook'), 'workbookId', 'id') == req['workbook_id'], 'visual_workbook')
    tags = baseline.get('tags')
    need(type(tags) is list and all(type(t) is dict for t in tags), 'visual_tags')
    tags = [t for t in tags if (t.get('tagName') or t.get('name')) == freeze['workbook_tag_name']]
    need(len(tags) == 1, 'visual_selected_tag')
    versions = {str(tags[0][k]) for k in ('sourceVersion', 'version', 'workbookVersion') if tags[0].get(k) is not None}
    need(len(versions) == 1 and baseline.get('tag_source_version') in versions, 'visual_tag_version')
    model = baseline.get('data_model_specification')
    if mid is None:
        need(model is None, 'visual_unselected_model')
    else:
        need(native_id(model, 'dataModelId', 'id') == mid and str(model.get('documentVersion')) == str(version), 'visual_model')
    pages, seen_pages, seen_elements, selected = snapshot.get('pages'), set(), set(), None
    need(type(pages) is list, 'visual_pages')
    for p in pages:
        pid = native_id(p, 'pageId', 'id')
        need(pid not in seen_pages and type(p.get('elements', [])) is list, 'visual_page_identity')
        seen_pages.add(pid)
        for element in p.get('elements', []):
            eid = native_id(element, 'elementId', 'id')
            need(eid not in seen_elements, 'visual_ambiguous_element')
            seen_elements.add(eid)
            if pid == req['page_id'] and eid == req.get('element_id'):
                selected = element
    need(req['page_id'] in seen_pages, 'visual_page_missing')
    if not page:
        need(selected is not None and selected.get('type') in {'chart', 'table'}, 'visual_element_missing')
        bulk = snapshot.get('elements')
        need(type(bulk) is list, 'visual_bulk_required')
        bulk = [r for r in bulk if native_id(r, 'elementId', 'id') == req['element_id']]
        need(len(bulk) == 1 and all(selected[k] == bulk[0][k] for k in selected.keys() & bulk[0].keys()),
             'visual_element_definition_conflict')
    final = source.get('final_observation')
    if final is not None:
        need(source.get('final_observation_sha256') == sha(final) and
             (coherence(final) == source['coherence_sha256'] or value['status'] == 'blocked'), 'visual_final_observation')
    need(value['status'] != 'complete' or final is not None, 'visual_final_observation_missing')
    seen = set()
    for a in attachments:
        kind = a.get('format')
        need(kind in by_kind and kind not in seen, 'visual_attachment_set')
        seen.add(kind)
        job = by_kind[kind]
        need(job['status'] == 'downloaded' and text(job.get('query_id')) and a.get('query_id') == job['query_id'], 'visual_attachment_job')
        need(all(a.get(k) == req.get(k) for k in ('capture_id', 'workbook_id', 'page_id', 'element_id'))
             and a.get('request_sha256') == value['request_sha256']
             and a.get('source_snapshot_sha256') == source['tagged_snapshot_sha256'], 'visual_attachment_binding')
    need(seen == {j['kind'] for j in jobs if j['status'] == 'downloaded'} and
         (value['status'] != 'complete' or seen == kinds), 'visual_attachment_missing')


def validate_capture(value):
    _bounded(value)
    need(type(value) is dict, 'capture_object')
    if value.get('schema_version') == LEGACY:
        if value.get('request', {}).get('schema_version') == 'sigma-visual-capture-request.v2':
            _validate_v2_capture(value)
        else:
            _bridge(value, 'sigma_visual_capture')
        req = value['request']
        need(type(req.get('row_limit')) is int and 1 <= req['row_limit'] <= 50000, 'legacy_row_limit')
        need(type(req.get('parameters')) is dict and len(req['parameters']) <= 100
             and all(text(k) and type(v) is str and len(v) <= 4096 for k, v in req['parameters'].items()),
             'legacy_parameters')
        if 'api_base_url' in req:
            _origin(req['api_base_url'].rstrip('/'))
            need(req.get('approved_api_host') == urlsplit(req['api_base_url']).hostname, 'legacy_host_mismatch')
        if value.get('created_at') is not None:
            _time(value['created_at'])
        _paths([a['path'] for a in value['attachments']])
        for a in value['attachments']:
            _pin({k: a[k] for k in ('path', 'bytes', 'sha256')})
            if a.get('captured_at') is not None:
                _time(a['captured_at'])
        return value
    need(value.get('schema_version') == SCHEMA, 'capture_schema')
    need(value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'bundle_hash')
    need(value.get('target_write_authority') is False and value.get('native_validation') == 'not_performed'
         and value.get('business_acceptance') == 'not_assessed', 'bundle_authority')
    need(value.get('status') in {'complete', 'partial', 'blocked'}, 'bundle_status')
    identity = value.get('identity')
    need(type(identity) is dict and set(identity) == {'source_origin', 'organization_id', 'principal_ref', 'workbook_id'}
         and all(text(v) for v in identity.values()), 'bundle_identity')
    _origin(identity['source_origin'])
    validate_selection(value.get('selection'))
    state = validate_state(value.get('state'))
    need(state['principal'] in (None, identity['principal_ref']), 'state_principal_mismatch')
    inv = value.get('inventory')
    need(type(inv) is dict and text(inv.get('reference')) and inv.get('completeness') in {'partial', 'selected_scope_declared'}
         and type(inv.get('items')) is list and 0 < len(inv['items']) <= 5000, 'independent_inventory')
    indexed = {}
    for row in inv['items']:
        need(type(row) is dict and text(row.get('key')) and row['key'] not in indexed
             and text(row.get('kind')) and text(row.get('reference')) and row.get('disposition') in
             {'include', 'out_of_scope', 'deferred', 'unknown'} and type(row.get('configuration')) is dict,
             'inventory_item')
        for field in ('native_id', 'page_id', 'parent_key'):
            need(field in row and (row[field] is None or text(row[field])), 'inventory_identity')
        indexed[row['key']] = row
    for key, row in indexed.items():
        chain, parent = {key}, row['parent_key']
        while parent is not None:
            need(parent in indexed and parent not in chain, 'inventory_parent_or_cycle')
            chain.add(parent)
            parent = indexed[parent]['parent_key']
        if row['kind'] == 'placement':
            need(sum(k in row['configuration'] for k in ('visual_key', 'content_key')) == 1, 'placement_target')
            target = row['configuration'].get('visual_key', row['configuration'].get('content_key'))
            need(target in indexed and target != key, 'placement_target')
    artifacts = value.get('artifacts')
    need(type(artifacts) is list and 1 <= len(artifacts) <= MAX_FILES, 'bundle_artifacts')
    seen, total = set(), 0
    for a in artifacts:
        need(type(a) is dict and text(a.get('artifact_id')) and a['artifact_id'] not in seen
             and a.get('kind') in ARTIFACT_KINDS and a.get('source_channel') in CHANNELS
             and a.get('format') in {'json', 'csv', 'png', 'pdf', 'opaque'} and text(a.get('reference')), 'artifact')
        seen.add(a['artifact_id'])
        _pin(a.get('file'))
        total += a['file']['bytes']
        keys = a.get('object_keys')
        need(type(keys) is list and all(text(k) and k in indexed for k in keys)
             and len(set(keys)) == len(keys), 'artifact_object_scope')
        validate_selection(a.get('selection'))
        need(a.get('state_sha256') == sha(state) and a.get('principal_ref') == identity['principal_ref'], 'artifact_state_or_principal')
        _time(a.get('captured_at'))
        need(a['kind'] not in {'rest_snapshot', 'workbook_contents', 'mcp_capture'} or a['format'] == 'json', 'artifact_json_required')
        need(a['kind'] not in {'page_render', 'element_render'} or a['format'] in {'png', 'pdf'}, 'artifact_render_required')
        if a['kind'] == 'workbook_contents':
            need(a['source_channel'] == 'workbook_contents_beta', 'contents_beta_channel_required')
        if a['kind'] == 'mcp_capture':
            proof = a.get('mcp_evidence')
            need(a['source_channel'] == 'passive_mcp' and type(proof) is dict and all(text(proof.get(k)) for k in
                 ('server_ref', 'protocol_version', 'tool_schema_ref', 'tool_name', 'session_ref', 'reference')),
                 'passive_mcp_provenance_required')
        if a['kind'] == 'results':
            need(a['format'] in {'csv', 'json'} and len(keys) == 1 and type(a.get('parser_profile')) is dict,
                 'result_profile_and_single_object_required')
            _validate_result_evidence(a, value)
    need(total <= MAX_TOTAL, 'bundle_total_bytes')
    for row in inv['items']:
        mapping = row.get('source_mapping')
        if mapping is not None:
            need(type(mapping) is dict and set(mapping) == {'artifact_id', 'pointer'}
                 and type(mapping['pointer']) is str and (mapping['pointer'] == '' or mapping['pointer'].startswith('/')),
                 'inventory_source_mapping')
            definitions = [a for a in artifacts if a['artifact_id'] == mapping['artifact_id'] and
                           a['kind'] in {'rest_snapshot', 'workbook_contents'} and row['key'] in a['object_keys']]
            need(len(definitions) == 1 and digest(row['configuration'].get('definition_sha256')), 'inventory_definition_binding')
    _paths([a['file']['path'] for a in artifacts])
    need(type(value.get('gaps')) is list and all(text(g) for g in value['gaps']), 'bundle_gaps')
    return value


def _validate_result_evidence(a, bundle):
    complete = a.get('completeness')
    need(type(complete) is dict and complete.get('status') in {'complete', 'partial', 'unknown'}
         and type(complete.get('flags')) is list and all(text(g) for g in complete['flags'])
         and (complete.get('row_count') is None or type(complete['row_count']) is int and complete['row_count'] >= 0)
         and (complete.get('reference') is None or text(complete['reference'])), 'result_completeness')
    if complete['status'] == 'complete':
        need(complete['row_count'] is not None and text(complete['reference']) and not complete['flags'], 'complete_evidence_required')
    for name, fields in [('population', ('key', 'reference')), ('freshness', ('observed_at', 'data_watermark', 'reference'))]:
        obj = a.get(name)
        need(type(obj) is dict and set(obj) == set(fields)
             and all(v is None or text(v) for v in obj.values()), 'result_' + name)
    if a['freshness']['observed_at'] is not None:
        _time(a['freshness']['observed_at'])
    observed = a.get('observed_state')
    if observed is not None:
        need(type(observed) is dict and text(observed.get('reference')) and digest(observed.get('definition_sha256'))
             and observed.get('execution_status') in {'completed', 'partial', 'unknown'}
             and observed.get('result_scope') in {'full_data', 'preview', 'sample', 'unknown'}, 'observed_result')
        validate_state(observed.get('state'))
        validate_selection(observed.get('selection'))
        need(observed['state']['principal'] in (None, bundle['identity']['principal_ref']), 'observed_principal')
        if observed.get('placement_reference') is not None:
            need(text(observed['placement_reference']), 'placement_reference')
        limit = observed.get('row_limit')
        need(limit is None or type(limit) is int and limit > 0, 'observed_row_limit')


def definition_fingerprint(value):
    if value['schema_version'] == LEGACY:
        return (value.get('source') or {}).get('tagged_snapshot_sha256')
    return sha({'identity': value['identity'], 'selection': value['selection'], 'inventory': value['inventory'],
                'original_definitions': [{k: a[k] for k in ('artifact_id', 'kind', 'source_channel', 'file', 'selection')}
                                         for a in value['artifacts'] if a['kind'] in {'rest_snapshot', 'workbook_contents'}]})


def _binding(value, a):
    legacy = value['schema_version'] == LEGACY
    return {'capture_content_hash': value['content_hash'], 'definition_fingerprint': definition_fingerprint(value),
            'object_key': value['request']['element_id'] if legacy else a['object_keys'][0],
            'attachment_id': a['query_id'] if legacy else a['artifact_id'],
            'state_sha256': sha(value['request']) if legacy else sha(value['state']),
            'attachment_sha256': a['sha256'] if legacy else a['file']['sha256']}


def verify_capture_files(value, root):
    validate_capture(value)
    legacy = value['schema_version'] == LEGACY
    rows = value['attachments'] if legacy else value['artifacts']
    verified, gaps, total, originals = [], list(value.get('gaps', [])), 0, {}
    for a in rows:
        pin = {k: a[k] for k in ('path', 'sha256', 'bytes')} if legacy else a['file']
        raw = _read_pin(root, pin)
        total += len(raw)
        need(total <= MAX_TOTAL, 'capture_total_bytes')
        kind = a['format']
        info = {}
        if kind == 'png':
            info['actual_dimensions'] = module('powerbi_capture_files').png_info(raw)
            if legacy:
                need(a.get('actual_dimensions') == info['actual_dimensions'] and a.get('requested_dimensions') is None,
                     'image_dimensions_mismatch')
                need(a.get('media_type', '').split(';')[0].strip().lower() == 'image/png', 'image_media_type')
        elif kind == 'json':
            data = decode(raw)
            _screen(data)
            if not legacy:
                originals[a['artifact_id']] = data
            need(type(data) in (dict, list), 'json_evidence_object_or_array')
            if legacy:
                need(a.get('media_type', '').split(';')[0].strip().lower() == 'application/json', 'json_media_type')
                result_rows = data if type(data) is list else data.get('rows')
                count = len(result_rows) if type(result_rows) is list else None
                need(count is None or count <= value['request']['row_limit'], 'legacy_result_row_limit')
                expected = {'observed_rows': count, 'requested_row_limit': value['request']['row_limit'],
                            'row_completeness': 'not_established', 'result_shape': 'array' if type(data) is list else 'object'}
                need(all(a.get(k) == v for k, v in expected.items()), 'legacy_result_metadata_mismatch')
                info.update(expected)
        elif kind == 'csv':
            try:
                _screen(raw.decode('utf-8-sig'))
            except UnicodeError:
                raise ValueError('sigma.csv_utf8_required') from None
        elif kind == 'pdf':
            need(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:], 'pdf_signature')
            gaps.append('sigma.pdf_content_and_rendering_not_qualified')
        else:
            gaps.append('sigma.opaque_content_not_interpreted_or_sanitized')
        if not legacy and a['kind'] == 'results':
            result = normalize_results(raw, a['parser_profile'], _binding(value, a))
            count = a['completeness']['row_count']
            need(count is None or count == result['row_count'], 'result_row_count_mismatch')
            info['observed_rows'] = result['row_count']
        if not legacy:
            if not _same_selection(a['selection'], value['selection']):
                gaps.append('sigma.artifact_version_tag_or_view_mismatch')
            if a['kind'] == 'workbook_contents':
                gaps.append('sigma.workbook_contents_beta_schema_not_compiled')
            if a['kind'] == 'mcp_capture':
                gaps.append('sigma.passive_mcp_not_execution_authority')
        verified.append({**pin, 'format': kind, 'inspection': info})
    if legacy:
        gaps.extend(['sigma.result_completeness_not_established', 'sigma.legacy_state_observation_incomplete',
                     'sigma.journal_history_not_reverified'])
        if value['request'].get('target_kind') == 'page':
            gaps.append('sigma.page_capture_has_no_numeric_result')
    else:
        for row in value['inventory']['items']:
            mapping = row.get('source_mapping')
            if mapping is not None:
                node = _pointer(originals[mapping['artifact_id']], mapping['pointer'])
                need(type(node) is dict and sha(node) == row['configuration']['definition_sha256'], 'original_definition_hash')
        captured = {key for a in rows for key in a['object_keys']}
        for row in value['inventory']['items']:
            if row['disposition'] == 'include' and row['key'] not in captured:
                gaps.append('sigma.inventory_object_evidence_missing:' + row['key'])
        if value['inventory']['completeness'] != 'selected_scope_declared':
            gaps.append('sigma.independent_inventory_partial')
    return {'schema_version': 1, 'kind': 'sigma_file_verification', 'capture_content_hash': value['content_hash'],
            'verified_files': verified, 'gaps': sorted(set(gaps)), 'provenance': 'supplied_not_authenticated',
            'target_write_authority': False, 'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}


def normalize_results(raw, profile, binding):
    keys = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id', 'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == keys and all(digest(binding.get(k)) for k in
         ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and text(binding['object_key']) and text(binding['attachment_id']) and binding['attachment_sha256'] == sha(raw),
         'normalization_binding')
    need(type(raw) is bytes and len(raw) <= MAX_BYTES and type(profile) is dict and profile.get('format') in {'csv', 'json'},
         'normalization_profile')
    need('shape' not in profile or profile['format'] == 'json' and profile['shape'] == 'object_rows', 'normalization_shape')
    error_tokens = {'#ERROR', '#ERROR!', '#N/A', '#DIV/0!', '#VALUE!', '#REF!', '#NUM!', '#NAME?', '#NULL!'}
    custom = profile.get('error_tokens', [])
    need(type(custom) is list and all(text(t) for t in custom), 'normalization_error_tokens')
    error_tokens.update(custom)
    def check_errors(value):
        if type(value) is dict:
            need(not any(k.lower() in {'error', 'errors'} and v for k, v in value.items()), 'result_error')
            for v in value.values():
                check_errors(v)
        elif type(value) is list:
            for v in value:
                check_errors(v)
        elif type(value) is str:
            need(value not in error_tokens, 'result_error_token')
    if profile['format'] == 'json':
        decoded = decode(raw)
        _screen(decoded)
        check_errors(decoded)
    else:
        try:
            _screen(raw.decode('utf-8-sig'))
        except UnicodeError:
            raise ValueError('sigma.csv_utf8_required') from None
        # Explicit profile drives the same bounded CSV iterator as normalization.
        # Check original cells before null mappings can erase an error token.
        for row in module('powerbi_visual').common().csv_rows(raw, profile.get('headers'), 'sigma'):
            check_errors(row)
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'],
              'state_sha256': binding['state_sha256'], 'attachment_sha256': binding['attachment_sha256']}
    result = module('powerbi_visual').normalize_results(raw, profile, mapped)
    result.update(kind='sigma_normalized_results', binding=copy.deepcopy(binding), parser_profile=copy.deepcopy(profile),
                  raw_sha256=sha(raw), qualification='generic_arithmetic_only_until_state_and_completeness_bound',
                  target_write_authority=False)
    return result


def _selected(value, key):
    index = {r['key']: r for r in value['inventory']['items']}
    need(key in index, 'case_inventory_key')
    selected = index[key]
    target = selected
    if selected['kind'] == 'placement':
        target = index[selected['configuration'].get('visual_key', selected['configuration'].get('content_key'))]
    for start in (selected, target):
        row = start
        while row is not None:
            need(row['disposition'] == 'include' and not row['configuration'].get('restricted')
                 and not row['configuration'].get('private'), 'case_scope_restricted')
            row = index.get(row['parent_key'])
    return selected, target


def case_binding(asset, case, capture):
    validate_capture(capture)
    binding = case.get('source_binding')
    identity = asset.get('source_identity', {})
    need(type(binding) is dict, 'case_binding_required')
    if capture['schema_version'] == LEGACY:
        req = capture['request']
        if req.get('target_kind') == 'page':
            need(asset.get('kind') == 'page' and asset.get('source_id') == req['page_id']
                 and case.get('lane') != 'numeric', 'page_capture_has_no_numeric_result')
            workbooks = [identity[k] for k in ('workbook_id', 'scope') if k in identity]
            need(workbooks and all(v == req['workbook_id'] for v in workbooks), 'page_capture_workbook_identity')
            snapshot_hash = (capture.get('source') or {}).get('tagged_snapshot_sha256')
            need(digest(snapshot_hash), 'page_capture_selection_missing')
            expected = {'workbook_id': req['workbook_id'], 'page_id': req['page_id'],
                        'capture_content_hash': capture['content_hash'], 'request_sha256': capture['request_sha256'],
                        'source_snapshot_sha256': snapshot_hash}
            need(all(binding.get(k) == v for k, v in expected.items()), 'page_capture_binding_mismatch')
            return binding
        need(asset.get('source_id') == req['element_id'] and identity.get('page_id') == req['page_id']
             and identity.get('workbook_id') == req['workbook_id'], 'legacy_case_identity')
        return binding
    key = identity.get('object_key', identity.get('inventory_key'))
    selected, target = _selected(capture, key)
    need(identity.get('definition_fingerprint') == definition_fingerprint(capture) and
         identity.get('workbook_id') == capture['identity']['workbook_id'], 'case_definition_identity')
    need(binding.get('object_key') == key and binding.get('definition_fingerprint') == definition_fingerprint(capture)
         and binding.get('state_sha256') == sha(capture['state']), 'case_state_or_definition')
    matches = [a for a in capture['artifacts'] if a['artifact_id'] == binding.get('attachment_id')
               and a['object_keys'] == [key]]
    need(len(matches) == 1 and (case.get('lane') != 'numeric' or matches[0]['kind'] == 'results'), 'case_artifact')
    return binding


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    if capture['schema_version'] == LEGACY:
        return ['source.sigma_legacy_completeness_unqualified', 'source.sigma_legacy_state_observation_incomplete']
    gaps = []
    if not case.get('source_capture'):
        gaps.append('source.sigma_case_capture_required')
    a = next(a for a in capture['artifacts'] if a['artifact_id'] == binding['attachment_id'])
    if capture['status'] == 'blocked':
        gaps.append('source.sigma_capture_blocked')
    selected, target_item = _selected(capture, binding['object_key'])
    expected_definition = target_item['configuration'].get('definition_sha256')
    if not digest(expected_definition) or target_item.get('source_mapping') is None:
        gaps.append('source.sigma_definition_evidence_missing')
    pin = source.get('raw_file') if source.get('format') == 'sigma-normalized' else source.get('file')
    if type(pin) is not dict or pin.get('sha256') != a['file']['sha256'] or pin.get('bytes') != a['file']['bytes']:
        gaps.append('source.sigma_result_bytes_not_bound')
    full = a['completeness']
    if full['status'] != 'complete' or not full['reference'] or full['flags']:
        gaps.append('source.sigma_result_completeness_unqualified')
    selection = capture['selection']
    if selection['mode'] not in {'tagged', 'published'} or not text(selection['version']):
        gaps.append('source.sigma_selection_unqualified')
    if not _same_selection(a['selection'], selection):
        gaps.append('source.sigma_version_tag_or_view_mismatch')
    definitions = [x for x in capture['artifacts'] if x['kind'] in {'rest_snapshot', 'workbook_contents'}
                   and any(k in x['object_keys'] for k in (selected['key'], target_item['key']))]
    if not definitions or any(not _same_selection(x['selection'], selection) for x in definitions):
        gaps.append('source.sigma_definition_selection_unqualified')
    observed = a.get('observed_state')
    if observed is None:
        gaps.append('source.sigma_observed_state_missing')
    else:
        if observed['execution_status'] != 'completed' or observed['result_scope'] != 'full_data':
            gaps.append('source.sigma_execution_or_population_unqualified')
        if not _same_selection(observed['selection'], selection):
            gaps.append('source.sigma_observed_version_tag_or_view_mismatch')
        if observed['definition_sha256'] != expected_definition:
            gaps.append('source.sigma_observed_definition_mismatch')
        if observed.get('row_limit') is not None and full.get('row_count') is not None and full['row_count'] >= observed['row_limit']:
            gaps.append('source.sigma_result_at_limit')
        if selected['kind'] == 'placement' and not observed.get('placement_reference'):
            gaps.append('source.sigma_placement_state_unqualified')
        for key in STATE_KEYS:
            expected = capture['state'][key]
            if expected is None or observed['state'].get(key) != expected or source.get('context', {}).get(key) != expected:
                gaps.append('source.sigma_state.' + key)
            if key not in {'principal', 'cache'} and target.get('context', {}).get(key) != expected:
                gaps.append('context.' + key)
    for key, expected in {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                          'freshness_reference': a['freshness']['reference']}.items():
        if not expected or not a['freshness']['observed_at'] or source.get('context', {}).get(key) != expected:
            gaps.append('source.sigma_context.' + key)
        if key == 'freshness_reference':
            if not text(target.get('context', {}).get(key)):
                gaps.append('target.sigma_freshness_reference')
        elif target.get('context', {}).get(key) != expected:
            gaps.append('context.' + key)
    if source.get('format') != 'sigma-normalized' or type(normalized) is not dict or normalized.get('binding') != _binding(capture, a):
        gaps.append('source.sigma_normalization_binding_required')
    else:
        if normalized.get('parser_profile') != a['parser_profile'] or normalized.get('row_count') != full.get('row_count'):
            gaps.append('source.sigma_parser_profile_or_row_count')
        fields = [c['name'] for c in a['parser_profile'].get('columns', [])]
        if type(columns) is not list or len(columns) != len(fields) or {c.get('source') for c in columns} != set(fields):
            gaps.append('source.sigma_complete_column_mapping_required')
        for col in a['parser_profile'].get('columns', []):
            if col.get('currency') is not None:
                mapped = [c.get('target') for c in columns or [] if c.get('source') == col['name']]
                code = col['currency']['code']
                if len(mapped) != 1 or source.get('context', {}).get('currencies', {}).get(col['name']) != code or \
                        target.get('context', {}).get('currencies', {}).get(mapped[0]) != code:
                    gaps.append('context.currency.' + col['name'])
    return sorted(set(gaps))


def validate_package(value):
    _bounded(value)
    need(type(value) is dict and value.get('schema_version') == PACKAGE, 'package_schema')
    _bridge(value, 'sigma_package')
    need(value.get('live_validation') == 'not_performed' and type(value.get('synthetic')) is bool, 'package_status')
    files = value['files']
    need(0 < len(files) <= MAX_FILES and 'manifest.json' not in files, 'package_file_count')
    _paths(list(files))
    build = value.get('build')
    need(type(build) is dict and build.get('schema_version') == 'sigma-prepush-build.v1'
         and build.get('route') == value['route'] and build.get('target_write_authority') is False
         and build.get('production_ready') is False, 'package_build')
    actor = value['review'].get('actor')
    need(type(actor) is dict and type(actor.get('uid')) is int and actor['uid'] >= 0 and text(actor.get('name'))
         and digest(value['review'].get('proposal_sha256')), 'package_supplied_os_review')
    return value


def verify_package_files(value, root):
    validate_package(value)
    root = Path(root).absolute()
    manifest_raw = _read(root, 'manifest.json')
    need(decode(manifest_raw) == value, 'package_manifest_changed')
    actual = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        need(not any((Path(directory) / d).is_symlink() for d in dirs), 'package_directory_symlink')
        for name in files:
            actual.add((Path(directory) / name).relative_to(root).as_posix())
            need(len(actual) <= MAX_FILES + 1, 'package_file_count')
    need(actual == set(value['files']) | {'manifest.json'}, 'package_inventory_mismatch')
    verified, parsed, contents, total, gaps = [], {}, {}, len(manifest_raw), []
    for name, expected in sorted(value['files'].items()):
        raw = _read(root, name)
        total += len(raw)
        need(total <= MAX_TOTAL and sha(raw) == expected, 'package_file_changed_or_budget')
        if name.lower().endswith('.json'):
            parsed[name] = decode(raw)
            _screen(parsed[name])
        try:
            contents[name] = raw.decode('utf-8')
            _screen(contents[name])
        except UnicodeError:
            raise ValueError('sigma.package_utf8_required') from None
        verified.append({'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
    for name, field in [('source.json', 'source_sha256'), ('target.json', 'target_sha256')]:
        need(type(parsed.get(name)) is dict and sha(parsed[name]) == value[field], 'package_input_binding')
    proposal = {**value['build'], 'files': {k: v for k, v in contents.items() if k not in {'source.json', 'target.json'}}}
    need(sha(proposal) == value['review']['proposal_sha256'], 'package_proposal_review_binding')
    return {'schema_version': 1, 'kind': 'sigma_package_verification', 'manifest_sha256': sha(value),
            'verified_files': verified, 'route': value['route'], 'review': 'supplied_os_review_not_authenticated',
            'gaps': ['sigma.package_target_semantics_not_compiled', 'sigma.source_access_and_live_parity_not_verified'],
            'target_write_authority': False, 'migration_accepted': False, 'native_validation': 'not_performed'}
