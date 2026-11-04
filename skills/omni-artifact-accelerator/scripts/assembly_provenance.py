"""First-party, ordered byte assembly and local provenance; never source execution.

Records retain bounded input snapshots. Hashes establish byte consistency, not
trusted authorship, semantic completeness, external freshness or review authority.
"""
import base64
import binascii
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path

POLICY = 'ordered-bytes-v1'
SCOPES = ('security', 'ui_ux', 'product_owner', 'qa')
KINDS = {'component', 'styles', 'query', 'asset', 'runtime', 'unknown'}
MAX_DEPENDENCIES = 128
MAX_INPUT_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_BYTES = 5 * 1024 * 1024
MAX_RECORD_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_SEPARATOR_BYTES = 4096


def _helpers(P):
    if P is None:
        spec = importlib.util.spec_from_file_location(
            'assembly_project', Path(__file__).with_name('analyst_project.py'))
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
    return P.routing_helper('stage_gates'), P


def _need(value, code):
    if not value:
        raise ValueError('assembly_' + code)


def _boundaries():
    return {'review_required_scopes': list(SCOPES), 'review_scope_reduction_allowed': False,
            'authority_changed': False, 'publication_authorized': False,
            'claims_authenticated': False, 'dependency_coverage': 'declared_only',
            'external_state_verified': False}


def _request(request, fields):
    _need(type(request) is dict and set(request) == set(fields), 'invalid_request')


def _stamp(value):
    _need(type(value) is str and len(value) <= 64, 'timestamp_required')
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('assembly_invalid_timestamp') from exc
    _need(result.tzinfo is not None, 'timezone_required')
    return result


def _freshness(dep):
    fresh = dep['freshness']
    _need(type(fresh) is dict and set(fresh) == {'mode', 'checked_at', 'expires_at'} and
          fresh['mode'] in {'immutable', 'until'}, 'invalid_freshness')
    checked = _stamp(fresh['checked_at'])
    if fresh['mode'] == 'immutable':
        _need(fresh['expires_at'] is None and dep['kind'] != 'runtime', 'runtime_expiry_required')
    else:
        _need(_stamp(fresh['expires_at']) > checked, 'invalid_freshness_window')


def _freshness_findings(dependencies, at):
    findings = []
    for dep in dependencies:
        fresh = dep['freshness']
        if _stamp(fresh['checked_at']) > at:
            findings.append('future_evidence:' + dep['id'])
        if fresh['mode'] == 'until' and _stamp(fresh['expires_at']) <= at:
            findings.append('expired_evidence:' + dep['id'])
        if dep['kind'] == 'unknown':
            findings.append('unknown_dependency:' + dep['id'])
    return findings


def _manifest(value, S):
    _need(type(value) is dict and set(value) == {
        'schema_version', 'kind', 'mode', 'separator_utf8', 'parts', 'dependencies'} and
        type(value['schema_version']) is int and value['schema_version'] == 1 and
        value['kind'] == 'assembly_manifest', 'invalid_manifest')
    _need(value['mode'] in {'utf8', 'bytes'}, 'unsupported_mode')
    separator = value['separator_utf8']
    _need(type(separator) is str, 'separator_required')
    try:
        _need(len(separator.encode('utf-8')) <= MAX_SEPARATOR_BYTES, 'separator_too_large')
    except UnicodeError as exc:
        raise ValueError('assembly_invalid_separator_utf8') from exc
    deps = value['dependencies']
    _need(type(deps) is list and 1 <= len(deps) <= MAX_DEPENDENCIES, 'dependencies_required')
    ids, paths, total = set(), set(), 0
    for dep in deps:
        _need(type(dep) is dict and set(dep) == {
            'id', 'kind', 'path', 'sha256', 'bytes', 'scopes', 'freshness'}, 'invalid_dependency')
        _need(S._ident(dep['id']) and dep['id'] not in ids and type(dep['kind']) is str and
              dep['kind'] in KINDS, 'invalid_dependency_identity')
        S._pin_shape({k: dep[k] for k in ('path', 'sha256', 'bytes')}, allow_empty=True)
        _need(dep['bytes'] <= MAX_INPUT_BYTES, 'input_too_large')
        _need(dep['path'] not in paths, 'duplicate_dependency_path')
        scopes = dep['scopes']
        _need(type(scopes) is list and bool(scopes) and all(type(s) is str for s in scopes) and
              scopes == sorted(set(scopes)) and set(scopes) <= set(SCOPES), 'invalid_scopes')
        _freshness(dep)
        total += dep['bytes']
        ids.add(dep['id'])
        paths.add(dep['path'])
    _need(total <= MAX_TOTAL_BYTES, 'inputs_too_large')
    parts = value['parts']
    _need(type(parts) is list and 1 <= len(parts) <= MAX_DEPENDENCIES and
          all(type(ident) is str and ident in ids for ident in parts), 'unmapped_part')
    return value


def _pin(path, raw, P):
    return {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}


def _builder(S, P):
    # Fixed package sources only. Request data cannot select imports or builders.
    sources = []
    for name, path in sorted((('assembler', __file__), ('path_helpers', S.__file__),
                             ('project_helpers', P.__file__))):
        path = P.no_links(path)
        _need(path.is_file() and path.stat().st_size <= MAX_INPUT_BYTES, 'invalid_builder_source')
        raw = path.read_bytes()
        _need(len(raw) <= MAX_INPUT_BYTES, 'invalid_builder_source')
        sources.append({'name': name, 'sha256': P.digest(raw), 'bytes': len(raw)})
    return {'policy': POLICY, 'sources': sources, 'sha256': P.digest(P.canonical(sources))}


def _assemble(manifest, content):
    parts, size = [], 0
    separator = manifest['separator_utf8'].encode('utf-8')
    for ident in manifest['parts']:
        raw = content[ident]
        if manifest['mode'] == 'utf8':
            try:
                raw.decode('utf-8')
            except UnicodeError as exc:
                raise ValueError('assembly_invalid_utf8:' + ident) from exc
        size += len(raw)
        _need(size + (len(manifest['parts']) - 1) * len(separator) <= MAX_OUTPUT_BYTES,
              'output_too_large')
        parts.append(raw)
    return separator.join(parts)


def _b64(raw):
    return base64.b64encode(raw).decode('ascii')


def _unb64(value, limit):
    _need(type(value) is str and len(value) <= 4 * ((limit + 2) // 3), 'snapshot_too_large')
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('assembly_invalid_snapshot') from exc
    _need(len(raw) <= limit and _b64(raw) == value, 'invalid_snapshot')
    return raw


@contextmanager
def _parent(fd, relative, S):
    S._relative(relative)
    current = os.dup(fd)
    try:
        for part in Path(relative).parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = new
        yield current, Path(relative).name
    finally:
        os.close(current)


def _write_new_pair(fd, output, raw, record_path, record_raw, S):
    # Claim both new names before writing. Existing files are never replaced.
    with _parent(fd, output, S) as (out_parent, out_name), _parent(fd, record_path, S) as (rec_parent, rec_name):
        handles, created = [], []
        try:
            for parent, name in ((out_parent, out_name), (rec_parent, rec_name)):
                handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
                handles.append(handle)
                created.append((parent, name))
            for handle, data in zip(handles, (raw, record_raw)):
                view = memoryview(data)
                while view:
                    count = os.write(handle, view)
                    _need(count > 0, 'write_failed')
                    view = view[count:]
                os.fsync(handle)
            os.fsync(out_parent)
            os.fsync(rec_parent)
        except BaseException:
            for parent, name in created:
                os.unlink(name, dir_fd=parent)
            raise
        finally:
            for handle in handles:
                os.close(handle)


def build(root, request, *, P=None, provider=None):
    """Build an immutable local candidate after the existing workflow build guard."""
    _request(request, {'manifest', 'output', 'record'})
    S, P = _helpers(P)
    for key in request:
        S._relative(request[key])
    _need(request['output'].endswith('.html') and request['record'].endswith('.json') and
          len(set(request.values())) == 3, 'distinct_output_paths_required')
    S.require_action(root, 'build', P=P, provider=provider)
    builder = _builder(S, P)
    with S._root_fd(root, P) as (_, fd):
        manifest_raw = S._read(fd, request['manifest'], MAX_MANIFEST_BYTES)
        manifest = _manifest(S._json(manifest_raw, P), S)
        protected = {request['manifest'], *(d['path'] for d in manifest['dependencies'])}
        _need(not {request['output'], request['record']} & protected, 'input_output_overlap')
        stale = [finding for finding in _freshness_findings(manifest['dependencies'], datetime.now(timezone.utc))
                 if not finding.startswith('unknown_dependency:')]
        _need(not stale, 'stale_dependencies:' + ';'.join(stale))
        content = {}
        for dep in manifest['dependencies']:
            raw = S._read(fd, dep['path'], MAX_INPUT_BYTES)
            _need(_pin(dep['path'], raw, P) == {k: dep[k] for k in ('path', 'sha256', 'bytes')},
                  'dependency_pin_mismatch:' + dep['id'])
            content[dep['id']] = raw
        output = _assemble(manifest, content)
        record = {'schema_version': 1, 'kind': 'assembly_provenance', 'builder': builder,
                  'manifest': {**_pin(request['manifest'], manifest_raw, P), 'content_base64': _b64(manifest_raw)},
                  'inputs': [{'id': dep['id'], 'content_base64': _b64(content[dep['id']])}
                             for dep in manifest['dependencies']],
                  'output': _pin(request['output'], output, P)}
        record['sha256'] = P.digest(P.canonical(record))
        record_raw = P.canonical(record) + b'\n'
        _need(len(record_raw) <= MAX_RECORD_BYTES, 'record_too_large')
        # Recheck pins before writing; retained snapshots preserve exactly what was assembled.
        _need(S._read(fd, request['manifest'], MAX_MANIFEST_BYTES) == manifest_raw, 'manifest_changed')
        for dep in manifest['dependencies']:
            _need(S._read(fd, dep['path'], MAX_INPUT_BYTES) == content[dep['id']],
                  'dependency_changed:' + dep['id'])
        _need(_builder(S, P) == builder, 'builder_changed')
        _write_new_pair(fd, request['output'], output, request['record'], record_raw, S)
    return {'status': 'built', 'record': _pin(request['record'], record_raw, P),
            'provenance_sha256': record['sha256'], 'output': record['output'], **_boundaries()}


def _load(fd, path, S, P):
    S._relative(path)
    raw = S._read(fd, path, MAX_RECORD_BYTES)
    record = S._json(raw, P)
    _need(type(record) is dict and set(record) == {
        'schema_version', 'kind', 'builder', 'manifest', 'inputs', 'output', 'sha256'} and
        type(record['schema_version']) is int and record['schema_version'] == 1 and
        record['kind'] == 'assembly_provenance', 'invalid_record')
    body = {key: value for key, value in record.items() if key != 'sha256'}
    _need(S._hash(record['sha256']) and P.digest(P.canonical(body)) == record['sha256'], 'record_hash_mismatch')
    builder = record['builder']
    _need(type(builder) is dict and set(builder) == {'policy', 'sources', 'sha256'} and
          builder['policy'] == POLICY and type(builder['sources']) is list and
          len(builder['sources']) == 3, 'unknown_builder')
    names = []
    for source in builder['sources']:
        _need(type(source) is dict and set(source) == {'name', 'sha256', 'bytes'} and
              type(source['name']) is str and S._hash(source['sha256']) and
              type(source['bytes']) is int and 0 < source['bytes'] <= MAX_INPUT_BYTES, 'invalid_builder')
        names.append(source['name'])
    _need(names == ['assembler', 'path_helpers', 'project_helpers'] and
          P.digest(P.canonical(builder['sources'])) == builder['sha256'], 'invalid_builder')
    manifest_pin = record['manifest']
    _need(type(manifest_pin) is dict and set(manifest_pin) == {
        'path', 'sha256', 'bytes', 'content_base64'}, 'invalid_manifest_snapshot')
    S._pin_shape({k: manifest_pin[k] for k in ('path', 'sha256', 'bytes')})
    manifest_raw = _unb64(manifest_pin['content_base64'], MAX_MANIFEST_BYTES)
    _need(_pin(manifest_pin['path'], manifest_raw, P) == {
        k: manifest_pin[k] for k in ('path', 'sha256', 'bytes')}, 'manifest_snapshot_mismatch')
    manifest = _manifest(S._json(manifest_raw, P), S)
    _need(type(record['inputs']) is list and len(record['inputs']) == len(manifest['dependencies']),
          'incomplete_snapshots')
    content = {}
    for dep, snapshot in zip(manifest['dependencies'], record['inputs']):
        _need(type(snapshot) is dict and set(snapshot) == {'id', 'content_base64'} and
              snapshot['id'] == dep['id'], 'unmapped_snapshot')
        data = _unb64(snapshot['content_base64'], MAX_INPUT_BYTES)
        _need(_pin(dep['path'], data, P) == {k: dep[k] for k in ('path', 'sha256', 'bytes')},
              'input_snapshot_mismatch:' + dep['id'])
        content[dep['id']] = data
    S._pin_shape(record['output'], allow_empty=True)
    output = _assemble(manifest, content)
    _need(_pin(record['output']['path'], output, P) == record['output'], 'unmapped_output_bytes')
    return record, manifest, content, _pin(path, raw, P)


def _inspect(fd, path, S, P, *, current, at):
    findings = []
    try:
        record, manifest, content, pin = _load(fd, path, S, P)
        if record['builder'] != _builder(S, P):
            findings.append('stale_builder')
        findings.extend(_freshness_findings(manifest['dependencies'], at))
        output = S._read(fd, record['output']['path'], MAX_OUTPUT_BYTES)
        if _pin(record['output']['path'], output, P) != record['output']:
            findings.append('unmapped_output_change')
        if current:
            manifest_raw = S._read(fd, record['manifest']['path'], MAX_MANIFEST_BYTES)
            if _pin(record['manifest']['path'], manifest_raw, P) != {
                    k: record['manifest'][k] for k in ('path', 'sha256', 'bytes')}:
                findings.append('stale_manifest')
            for dep in manifest['dependencies']:
                raw = S._read(fd, dep['path'], MAX_INPUT_BYTES)
                if raw != content[dep['id']]:
                    findings.append('stale_dependency:' + dep['id'])
        return {'record': record, 'manifest': manifest, 'pin': pin, 'findings': findings}
    except (ValueError, OSError, TypeError, KeyError, OverflowError) as exc:
        return {'record': None, 'manifest': None, 'pin': None,
                'findings': findings + ['invalid_or_unavailable_record:' + str(exc)]}


def verify(root, request, *, P=None):
    """Reproduce retained bytes and check live inputs/output without executing them."""
    _request(request, {'record'})
    S, P = _helpers(P)
    S._relative(request['record'])
    with S._root_fd(root, P) as (_, fd):
        state = _inspect(fd, request['record'], S, P, current=True, at=datetime.now(timezone.utc))
    record = state['record']
    return {'status': 'unknown' if state['findings'] else 'verified',
            'record': state['pin'], 'provenance_sha256': record['sha256'] if record else None,
            'output': record['output'] if record else None, 'findings': state['findings'], **_boundaries()}


def compare(root, request, *, P=None):
    """Explain declared changes; no classification can narrow an existing review."""
    _request(request, {'previous', 'current'})
    S, P = _helpers(P)
    for path in request.values():
        S._relative(path)
    with S._root_fd(root, P) as (_, fd):
        at = datetime.now(timezone.utc)
        older = _inspect(fd, request['previous'], S, P, current=False, at=at)
        newer = _inspect(fd, request['current'], S, P, current=True, at=at)
    findings = ['previous:' + reason for reason in older['findings']]
    findings.extend('current:' + reason for reason in newer['findings'])
    changed, hints, recipe_changed, output_changed = [], {}, False, None
    if older['record'] and newer['record']:
        old = {d['id']: d for d in older['manifest']['dependencies']}
        new = {d['id']: d for d in newer['manifest']['dependencies']}
        if set(old) != set(new):
            findings.append('dependency_inventory_changed')
        changed = sorted(ident for ident in set(old) | set(new) if old.get(ident) != new.get(ident))
        for ident in changed:
            hints[ident] = sorted(set((old.get(ident) or {}).get('scopes', [])) |
                                 set((new.get(ident) or {}).get('scopes', [])))
            if ident in old and ident in new and any(old[ident][k] != new[ident][k] for k in ('kind', 'scopes')):
                findings.append('dependency_mapping_changed:' + ident)
        recipe_changed = any(older['manifest'][k] != newer['manifest'][k]
                             for k in ('mode', 'separator_utf8', 'parts'))
        output_changed = any(older['record']['output'][k] != newer['record']['output'][k]
                             for k in ('sha256', 'bytes'))
        if output_changed and not changed and not recipe_changed:
            findings.append('unmapped_output_change')
    return {'status': 'unknown' if findings else 'changed' if changed or recipe_changed else 'unchanged',
            'changed_dependency_ids': changed, 'scope_hints': hints, 'recipe_changed': recipe_changed,
            'output_changed': output_changed, 'findings': findings,
            'previous': older['pin'], 'current': newer['pin'], **_boundaries()}
