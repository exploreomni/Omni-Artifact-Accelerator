"""Neutral source evidence and injected transport; no tenant or dependencies."""
import copy
import base64
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('microstrategy_capture_tested', ROOT / 'skills/omni-artifact-translator/scripts/microstrategy_capture.py')
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
OID, IID, PROJECT, METRIC = '2' * 32, '3' * 32, '1' * 32, '4' * 32


def result_definition():
    return {'attributes': [], 'metrics': [{'id': METRIC}]}


def snapshot():
    payload = {'information': {'objectId': OID, 'name': 'Garden quantities', 'subType': 'report_grid'}}
    return {'schema_version': 'microstrategy-api-snapshot.v1', 'identity': {
        'source_origin': 'https://source.example.invalid', 'context_path': '/MicroStrategyLibrary', 'project_id': PROJECT,
        'principal_ref': 'fixture-reader', 'library_version': '2026.10', 'intelligence_server_version': '2026.10',
        'model_generation': 'classic', 'delivery_context': 'library', 'reference': 'Synthetic source identity'},
        'root': {'kind': 'report', 'id': OID}, 'objects': [{'kind': 'report', 'id': OID, 'payload': payload, 'evidence_ref': 'Synthetic native metadata'}],
        'inventory': {'reference': 'Independent selected source scope', 'completeness': 'selected_scope_declared', 'items': [{
            'key': 'report', 'kind': 'report', 'parent_key': None, 'native_id': OID, 'definition_id': OID,
            'disposition': 'include', 'reference': 'Independent expected report', 'configuration': {},
            'source_mapping': {'object_kind': 'report', 'object_id': OID, 'pointer': ''}}]}, 'gaps': ['synthetic_fixture_only']}


def operation(kind, name=None, body=None):
    return {'operation_id': name or kind, 'kind': kind, 'object_key': 'report',
            'instance_from': None if kind in ('definition', 'create_instance') else 'create_instance',
            'body': body, 'reference': 'Synthetic selected source operation'}


def schema_for(operations, kind='report'):
    paths = {}
    for op in operations:
        method, path = C.schema_route({'root': {'kind': kind}}, op)
        paths.setdefault(path, {})[method] = {'description': 'Synthetic version-scoped schema operation'}
    return {'openapi': '3.0.0', 'paths': paths}


def request(connected=False):
    value = snapshot()
    ops = [operation('definition'), operation('create_instance'), operation('prompts'),
           operation('state_readback', body={'filter_pointers': {k: '/filters/' + k for k in C.FILTER_STAGES}}),
           operation('data', body={'offset': 0, 'limit': 2})] if connected else []
    r = {'schema_version': C.REQUEST, 'capture_id': 'synthetic-strategy', 'identity': value['identity'], 'root': value['root'],
        'authorization_ref': 'Synthetic source-read request', 'credential_ref': 'host-session-reference',
        'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {k: [] for k in C.FILTER_STAGES}, 'parameters': {'prompts': []}, 'timezone': 'UTC', 'locale': 'en-US',
                  'principal': 'fixture-reader', 'cache': None, 'reference': 'Synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json', 'operations': ops, 'api_profile': None}
    if connected:
        r['api_profile'] = {'id': C.PROFILE, 'library_version': '2026.10', 'intelligence_server_version': '2026.10',
            'api_schema_path': 'schema.json', 'api_schema_sha256': C.F.raw_sha(C.encoded(schema_for(ops))),
            'reference': 'Synthetic exact API-schema qualification'}
    return r


def supplied(root, value=None, req=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True); value = value or snapshot()
    records = [{'source_path': 'native.json', 'source_kind': 'rest_json', 'source_pointer': '/%d' % i,
        'target_pointer': '/objects/%d/payload' % i, 'mapping': 'exact_json', 'member_path': None, 'mcp_evidence': None,
        'reference': 'Synthetic retained native response'} for i in range(len(value['objects']))]
    records.append({'source_path': 'inventory.json', 'source_kind': 'supplied_json', 'source_pointer': '', 'target_pointer': '/inventory',
        'mapping': 'exact_json', 'member_path': None, 'mcp_evidence': None, 'reference': 'Independent original inventory'})
    manifest = {'schema_version': 'microstrategy-originals.v1', 'reference': 'Synthetic original crosswalk', 'records': records}
    for path, data in [('snapshot.json', value), ('originals.json', manifest), ('inventory.json', value['inventory']),
                       ('native.json', [o['payload'] for o in value['objects']])]:
        (root / path).write_bytes(C.encoded(data))
    if req and req['api_profile']:
        (root / 'schema.json').write_bytes(C.encoded(schema_for(req['operations'], req['root']['kind'])))
    return manifest


def prepare(root, req=None, value=None, connected=False):
    root = Path(root); req = req or request(connected); supplied(root / 'supplied', value, req)
    return req, C.import_local(req, root / 'supplied', root / 'capture', allow_source_read=True)


class FakeTransport:
    def __init__(self, directory, req, overrides=None):
        self.directory, self.req, self.overrides = Path(directory), req, overrides or {}
        self.calls, self.grants = [], []

    def authority(self, scope, fingerprint):
        self.grants.append(scope)
        value, _ = C.load_latest(self.directory, self.req)
        selected = C.pending_operation_spec(self.req, value)
        assert C.fingerprint(self.req, selected) == fingerprint
        assert scope == selected['scope']
        return {'X-MSTR-AuthToken': 'fixture-token-not-real', 'Cookie': 'SESSION=fixture-cookie-not-real', 'X-MSTR-ProjectID': PROJECT}

    def __call__(self, method, url, headers, body, maximum, timeout):
        self.calls.append((method, url))
        value, _ = C.load_latest(self.directory, self.req)
        selected = C.pending_operation_spec(self.req, value)
        phase = selected['phase']
        if phase in self.overrides:
            override = self.overrides[phase]
            if isinstance(override, Exception): raise override
            return override
        if phase == 'definition': raw = value['source']['snapshot']['objects'][0]['payload']
        elif phase == 'create_instance': raw = {'id': OID, 'mid' if self.req['root']['kind'] == 'dossier' else 'instanceId': IID, 'status': 1}
        elif phase == 'prompts': raw = []
        elif phase == 'state_readback': raw = {'id': OID, 'instanceId': IID, 'status': 1, 'filters': self.req['state']['filters']}
        elif phase == 'data': raw = {'id': OID, 'instanceId': IID, 'status': 1,
            'definition': result_definition(), 'data': {'paging': {'offset': 0, 'limit': 2, 'total': 2, 'current': 2}}}
        elif phase == 'pdf': return 200, {}, b'%PDF-1.7\nsynthetic\n%%EOF'
        else: return 204, {}, b''
        return C.expected_status(selected), {}, C.encoded(raw)


class CaptureTests(unittest.TestCase):
    def test_passive_roundtrip_and_original_tamper(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            req, out = prepare(tmp)
            self.assertEqual(C.check_capture(Path(tmp) / 'capture')['status'], 'verified_local_bytes')
            self.assertFalse(out['capture']['source_execution'])
            (Path(tmp) / 'capture' / 'original-0000.bin').write_bytes(b'[]')
            with self.assertRaises(ValueError): C.check_capture(Path(tmp) / 'capture')

    def test_source_read_requires_explicit_grant(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            supplied(Path(tmp) / 'source')
            with self.assertRaisesRegex(ValueError, 'source_read_grant'): C.import_local(request(), Path(tmp) / 'source', Path(tmp) / 'out')

    def test_original_payload_crosswalk_cannot_be_fabricated(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            src = Path(tmp) / 'source'; supplied(src)
            (src / 'native.json').write_bytes(C.encoded([{'id': OID}]))
            with self.assertRaisesRegex(ValueError, 'payload_mismatch'): C.import_local(request(), src, Path(tmp) / 'out', allow_source_read=True)

    def test_unknown_versions_and_nonclassic_connected_rejected(self):
        for key, value in [('library_version', 'latest'), ('intelligence_server_version', 'unknown'), ('model_generation', 'mosaic')]:
            r = request(True); r['identity'][key] = value
            if key != 'model_generation': r['api_profile'][key] = value
            with self.assertRaises(ValueError): C.validate_request(r)
        r = request(); r['identity']['library_version'] = 'unknown'
        C.validate_request(r)

    def test_principal_continuity_and_passive_unknown(self):
        r = request(); r['state']['principal'] = None; C.validate_request(r)
        for principal in ('different-reader', None):
            r = request(True); r['state']['principal'] = principal
            with self.assertRaisesRegex(ValueError, 'principal_mismatch'): C.validate_request(r)

    def test_mcp_original_requires_explicit_provenance(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            src = Path(tmp) / 'source'; manifest = supplied(src)
            manifest['records'][0]['source_kind'] = 'mcp_json'
            (src / 'originals.json').write_bytes(C.encoded(manifest))
            with self.assertRaisesRegex(ValueError, 'mcp_provenance'):
                C.import_local(request(), src, Path(tmp) / 'out', allow_source_read=True)

    def test_schema_hash_and_missing_route_fail(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r = request(True); src = Path(tmp) / 'source'; supplied(src, req=r)
            (src / 'schema.json').write_bytes(C.encoded({'paths': {'/unqualified': {'get': {}}}}))
            with self.assertRaisesRegex(ValueError, 'schema_hash'): C.import_local(r, src, Path(tmp) / 'out', allow_source_read=True)
            r['api_profile']['api_schema_sha256'] = C.F.raw_sha((src / 'schema.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'route_not_qualified'): C.import_local(r, src, Path(tmp) / 'out2', allow_source_read=True)

    def test_unsafe_origin_context_and_routes_rejected(self):
        for key, value in [('source_origin', 'https://source.example.invalid@elsewhere.invalid'), ('context_path', '/Library/../api')]:
            r = request(); r['identity'][key] = value
            with self.assertRaises(ValueError): C.validate_request(r)
        r = request(True); r['operations'][0]['kind'] = 'logout'
        with self.assertRaises(ValueError): C.validate_request(r)

    def test_datamart_execution_rejected(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            snap = snapshot(); snap['objects'][0]['payload']['information']['subType'] = 'report_datamart'
            with self.assertRaisesRegex(ValueError, 'ordinary_saved_report'): prepare(tmp, value=snap, connected=True)

    def test_connected_acquisition_has_distinct_grants_and_preserves_snapshot(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, imported = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r)
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(out['status'], 'acquired_requested_operations')
            self.assertEqual(t.grants, ['metadata', 'execution', 'metadata', 'execution', 'execution'])
            self.assertTrue(out['capture']['source_execution']); self.assertEqual(out['capture']['source'], imported['capture']['source'])
            self.assertEqual(C.check_capture(t.directory)['status'], 'verified_local_bytes')

    def test_uncertain_create_is_never_replayed(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r, {'create_instance': OSError('do not log')})
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(out['status'], 'blocked'); calls = len(t.calls)
            C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(len(t.calls), calls)
            C.check_capture(t.directory)

    def test_host_denial_has_no_source_dispatch(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r)
            def deny(*_): raise ValueError('secret must not escape')
            with self.assertRaisesRegex(ValueError, 'host_authority_rejected'): C.capture(r, t.directory, authority=deny, transport=t)
            value, _ = C.load_latest(t.directory)
            self.assertFalse(value['source_execution']); self.assertEqual(t.calls, [])
            self.assertFalse(value['operations'][0]['dispatched'])

    def test_credential_echo_and_rotation_are_not_retained(self):
        for headers, raw in [({}, b'{"value":"fixture-token-not-real"}'),
                             ({}, b'{"value":"fixture-cookie-not-real"}'),
                             ({'Set-Cookie': 'SESSION=rotated-secret'}, C.encoded(snapshot()['objects'][0]['payload']))]:
            with self.subTest(headers=bool(headers)), tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
                r, _ = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r, {'definition': (200, headers, raw)})
                out = C.capture(r, t.directory, authority=t.authority, transport=t)
                self.assertEqual(out['capture']['responses'], [])
                retained = b''.join(p.read_bytes() for p in t.directory.iterdir() if p.is_file())
                self.assertNotIn(b'fixture-token-not-real', retained); self.assertNotIn(b'rotated-secret', retained)
                if headers:
                    count = len(t.calls); C.capture(r, t.directory, authority=t.authority, transport=t)
                    self.assertEqual(len(t.calls), count)
                C.check_capture(t.directory)

    def test_definition_drift_stops_before_create(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True); payload = snapshot()['objects'][0]['payload']; payload['information']['name'] = 'Changed'
            t = FakeTransport(Path(tmp) / 'capture', r, {'definition': (200, {}, C.encoded(payload))})
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(len(t.calls), 1); self.assertFalse(out['capture']['source_execution'])

    def test_state_mismatch_blocks_data(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True); filters = copy.deepcopy(r['state']['filters']); filters['view'] = [{'unselected': True}]
            t = FakeTransport(Path(tmp) / 'capture', r, {'state_readback': (200, {}, C.encoded({'id': OID, 'instanceId': IID, 'status': 1, 'filters': filters}))})
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(out['status'], 'blocked'); self.assertEqual(len(t.calls), 4)
            C.check_capture(t.directory)

    def test_missing_completed_status_blocks_data(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True)
            t = FakeTransport(Path(tmp) / 'capture', r, {'state_readback': (200, {}, C.encoded({'id': OID, 'instanceId': IID, 'filters': r['state']['filters']}))})
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(out['status'], 'blocked'); self.assertEqual(len(t.calls), 4)

    def test_pdf_is_dossier_scoped_separately_granted_and_not_numeric_proof(self):
        body = {'pageHeight': 11, 'pageWidth': 8.5, 'orientation': 'AUTO', 'pageOption': 'ALL', 'includeOverview': True,
                'includeDetailedPages': True, 'waitingTimeBeforeExport': 0, 'includeHeader': False, 'includeFooter': False}
        r = request(True); r['operations'].append(operation('pdf', body=body))
        with self.assertRaisesRegex(ValueError, 'pdf_profile'): C.validate_request(r)
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            value = snapshot(); value['root']['kind'] = 'dossier'; value['objects'][0].update(kind='dossier', payload={'id': OID, 'chapters': []})
            value['inventory']['items'][0]['kind'] = 'dossier'; value['inventory']['items'][0]['source_mapping']['object_kind'] = 'dossier'
            r['root'] = value['root']; r['operations'] = [o for o in r['operations'] if o['kind'] != 'data']
            r['api_profile']['api_schema_sha256'] = C.F.raw_sha(C.encoded(schema_for(r['operations'], 'dossier')))
            prepare(tmp, r, value); t = FakeTransport(Path(tmp) / 'capture', r)
            out = C.capture(r, t.directory, authority=t.authority, transport=t)
            self.assertEqual(out['status'], 'acquired_requested_operations'); self.assertEqual(t.grants[-1], 'render')
            self.assertEqual(out['capture']['responses'][-1]['inspection']['numerical_completeness'], 'not_established')
            C.check_capture(t.directory)

    def test_prompt_keys_can_repeat_ids_not_keys(self):
        r = request(); prompt = {'key': 'one', 'id': '5' * 32, 'answer_mode': 'empty', 'value': None}
        r['state']['parameters']['prompts'] = [prompt, {**prompt, 'key': 'two'}]; C.validate_request(r)
        r['state']['parameters']['prompts'][1]['key'] = 'one'
        with self.assertRaisesRegex(ValueError, 'prompt_state'): C.validate_request(r)
        actual = [{'key': 'one', 'id': '5' * 32, 'type': 'VALUE', 'closed': True, 'required': True, 'answers': []}]
        r['state']['parameters']['prompts'] = [prompt]
        self.assertFalse(C.prompt_readback(actual, r)[1])

    def test_complete_numeric_requires_instance_definition_and_execution_evidence(self):
        row = {'attachment_id': 'numbers', 'object_key': 'report', 'format': 'csv', 'origin': 'full', 'result_scope': 'query_result',
            'observed_state': {'state': request()['state'], 'observed_at': '2026-01-01', 'reference': 'Synthetic state'},
            'population': {'key': 'garden', 'description': 'Full garden', 'reference': 'Synthetic population'},
            'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01', 'reference': 'Synthetic freshness'},
            'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic full export'}, 'reference': 'Synthetic evidence'}
        with self.assertRaisesRegex(ValueError, 'complete_result'): C.validate_attachment(row, request(), snapshot())
        row['observed_state'].update(instance_id=IID, result_definition_sha256='a' * 64, definition_reference='Exact result definition',
                                     execution_status='completed', execution_reference='Instance completed readback')
        C.validate_attachment(row, request(), snapshot())
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, out = prepare(tmp); (Path(tmp) / 'supplied' / 'numbers.csv').write_text('Item,Quantity\nSeed,2\nSoil,4\n')
            spec = {'schema_version': 'microstrategy-supplied-evidence.v1', 'attachments': [{**row, 'source_path': 'numbers.csv', 'member_path': None}]}
            imported = C.import_evidence(out['output'], spec, Path(tmp) / 'supplied')
            C.check_capture(Path(tmp) / 'capture')
            self.assertFalse(imported['capture']['source_execution'])

    def test_zip_and_secret_screening(self):
        for name, data in [('../escape.json', b'{}'), ('source.json', b'{"password":"synthetic-bad-secret"}')]:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z: z.writestr(name, data)
            with self.assertRaises(ValueError): C.zip_members(stream.getvalue())
        with self.assertRaises(ValueError): C.screen_bytes(b'X-MSTR-AuthToken=synthetic-bad-secret')

    def test_pdf_base64_is_bounded_and_decoded_before_echo_screen(self):
        raw = b'%PDF-1.7\nsynthetic\n%%EOF'
        self.assertEqual(C.pdf_bytes(C.encoded({'data': base64.b64encode(raw).decode()})), raw)
        with self.assertRaisesRegex(ValueError, 'pdf_base64'): C.pdf_bytes(C.encoded({'data': 'not_base64!'}))
        wrapped = C.encoded({'data': base64.b64encode(b'%PDF-1.7\nfixture-token-not-real\n%%EOF').decode()})
        with self.assertRaisesRegex(ValueError, 'credential_echo'):
            C.screen_granted_echo(C.pdf_bytes(wrapped), {'X-MSTR-AuthToken': 'fixture-token-not-real', 'Cookie': 'SESSION=fixture-cookie-not-real'})

    def test_journal_reseal_cannot_reset_attempts_or_source(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            r, _ = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r)
            C.capture(r, t.directory, authority=t.authority, transport=t)
            value, _ = C._load(t.directory)
            value['operations'] = []; value['responses'] = []; value['request_count'] = 0; value['network_bytes'] = 0
            value['status'] = 'partial'; C._execution_state(value); C._save(t.directory, value)
            with self.assertRaisesRegex(ValueError, 'rollback|rewritten'): C.load_latest(t.directory)

    def test_redirect_and_business_error_bodies_not_saved(self):
        for status, raw in [(302, b'elsewhere'), (200, b'{"code":"ERR","message":"sensitive"}')]:
            with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
                r, _ = prepare(tmp, connected=True); t = FakeTransport(Path(tmp) / 'capture', r, {'definition': (status, {}, raw)})
                out = C.capture(r, t.directory, authority=t.authority, transport=t)
                self.assertFalse(out['capture']['responses']); self.assertEqual(len(t.calls), 1)
                C.check_capture(t.directory)


if __name__ == '__main__': unittest.main()
