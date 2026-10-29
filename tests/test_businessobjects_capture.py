"""Neutral original evidence and injected transport; no SAP service or SDK."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('businessobjects_capture_tested', ROOT / 'skills/omni-artifact-translator/scripts/businessobjects_capture.py')
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)


def state():
    return {'filters': {k: [] for k in sorted(C.FILTER_STAGES)}, 'parameters': {'prompts': [], 'contexts': []},
        'timezone': 'UTC', 'locale': 'en-US', 'principal': 'fixture-reader', 'cache': 'saved source results',
        'reference': 'Synthetic observed state'}


def request(connected=False):
    identity = {'source_origin': 'https://source.example.invalid:8443', 'product_version': '4.3', 'service_pack': 5,
        'principal_ref': 'fixture-reader', 'document_id': '17', 'cuid': 'fixture-document', 'report_engine': 'webi',
        'reference': 'Synthetic pinned source identity'}
    return {'schema_version': C.REQUEST, 'capture_id': 'synthetic-webi', 'identity': identity, 'state': state(),
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json', 'authorization_ref': 'Synthetic source read',
        'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'api_profile': {'id': C.PROFILE, 'product_version': '4.3', 'service_pack': 5, 'rest_path': '/proxy/biprws',
            'build': 'Synthetic SP5 patch build', 'qualification_reference': 'Synthetic external host qualification',
            'reference': 'Synthetic version profile'} if connected else None,
        'operations': [operation('document_details'), operation('parameters')] if connected else []}


def operation(kind):
    return {'operation_id': kind, 'kind': kind, 'report_id': None, 'element_id': None, 'provider_id': None,
            'reference': 'Synthetic selected operation'}


def result_contract():
    return {'data_mode': 'full_data', 'row_limit': None, 'row_limit_stage': 'none',
            'aggregation_stage': 'native_report', 'reference': 'Synthetic full report population'}


def profile(format='json'):
    value = {'schema_version': 1, 'format': format, 'headers': ['district', 'yield'],
        'columns': [{'ordinal': i, 'name': name, 'type': typ, 'nullable': False, 'null_tokens': [], 'error_tokens': []}
                    for i, (name, typ) in enumerate([('district', 'string'), ('yield', 'number')])],
        'subtotal_policy': 'preserve', 'value_representation': 'raw', 'reference': 'Synthetic raw scalar export profile'}
    value['encoding' if format == 'csv' else 'rows_pointer'] = 'utf-8' if format == 'csv' else ''
    return value


def binding(raw):
    return {**{k: 'a' * 64 for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256')},
            'attachment_sha256': C.sha(raw), 'object_key': 'yield', 'attachment_id': 'result'}


def snapshot_fixture():
    responses = []
    for name, kind, report, payload, route in [
        ('document', 'document', None, {'document': {'id': 17, 'refreshOnOpen': False}}, '/documents/17'),
        ('element', 'element', '1', {'element': {'@type': 'VTable', 'id': 7, 'reference': '1.7',
            'content': {'axes': {'axis': {'@role': 'Column', 'id': 1, 'expressions': {'formula': {
                '@dataType': 'Numeric', '@dataObjectId': 'DP0.DO7', '$': '=[Yield]'}}}}}}}, '/documents/17/reports/1/elements/7'),
        ('providers', 'dataproviders', None, {'dataproviders': {'dataprovider': {'id': 'DP0', 'name': 'Yield query',
            'dataSourceId': '600', 'dataSourceType': 'unx', 'rowCount': 2, 'isPartial': False}}}, '/documents/17/dataproviders')]:
        raw = C.encoded(payload)
        responses.append({'key': name, 'kind': kind, 'report_id': report, 'provider_id': None, 'format': 'json',
            'encoding': 'utf-8', 'content': raw.decode(), 'sha256': C.sha(raw), 'bytes': len(raw),
            'reference': 'Synthetic retained native response', 'provenance': {'mode': 'supplied_rest',
                'method': 'GET', 'resource_path': route, 'status': 200}})
    return {'schema_version': 'businessobjects-api-snapshot.v1', 'identity': request()['identity'], 'responses': responses,
        'inventory': {'reference': 'Independent selected fixture scope', 'completeness': 'selected_scope_declared', 'items': [
            {'key': 'document', 'kind': 'document', 'parent_key': None, 'native_id': '17', 'report_id': None,
             'disposition': 'include', 'reference': 'Synthetic expected document', 'configuration': {},
             'source_mapping': {'response_key': 'document', 'locator': '/document'}},
            {'key': 'yield', 'kind': 'visual', 'parent_key': 'document', 'native_id': '7', 'report_id': '1',
             'disposition': 'include', 'reference': 'Synthetic expected visual', 'configuration': {'result_contract': result_contract()},
             'source_mapping': {'response_key': 'element', 'locator': '/element'}},
            {'key': 'provider', 'kind': 'provider', 'parent_key': 'document', 'native_id': 'DP0', 'report_id': None,
             'disposition': 'include', 'reference': 'Synthetic expected provider', 'configuration': {},
             'source_mapping': {'response_key': 'providers', 'locator': '/dataproviders/dataprovider'}}]}, 'gaps': ['synthetic_fixture_only']}


def prepare(root, connected=False):
    root = Path(root).resolve(); supplied = root / 'supplied'; supplied.mkdir(parents=True)
    snap, req = snapshot_fixture(), request(connected)
    records = []
    for row in snap['responses']:
        filename = row['key'] + '.json'; (supplied / filename).write_bytes(row['content'].encode())
        records.append({'source_path': filename, 'kind': 'response', 'response_key': row['key'], 'reference': 'Synthetic original response'})
    (supplied / 'inventory.json').write_bytes(C.encoded(snap['inventory']))
    records.append({'source_path': 'inventory.json', 'kind': 'inventory', 'response_key': None, 'reference': 'Independent scope original'})
    (supplied / 'snapshot.json').write_bytes(C.encoded(snap))
    (supplied / 'originals.json').write_bytes(C.encoded({'schema_version': 'businessobjects-originals.v1', 'reference': 'Synthetic source crosswalk', 'records': records}))
    out = C.import_local(req, supplied, root / 'capture', allow_source_read=True)
    return req, out


def capture_fixture(root):
    """Reusable positive numeric fixture for shared workflow checks."""
    root = Path(root).resolve(); req, out = prepare(root)
    cap, path = C.load_latest(root / 'capture')
    raw = b'[{"district":"West","yield":1.100000000000000001},{"district":"East","yield":9007199254740993}]'
    raw_path = root / 'supplied' / 'result.json'; raw_path.write_bytes(raw)
    attachment = {'attachment_id': 'result', 'object_key': 'yield', 'format': 'json', 'reference': 'Synthetic exact result',
        'source_path': 'result.json', 'origin': 'full', 'result_scope': 'query_result', 'parser_profile': profile(),
        'observed_state': {'state': state(), 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic observation',
            'execution_status': 'completed', 'execution_reference': 'Synthetic completed provider execution',
            'definition_fingerprint': cap['source']['definition_fingerprint'], 'provider_states': [
                {'provider_id': 'DP0', 'status': 'completed', 'reference': 'Synthetic provider status'}], 'result_context': result_contract()},
        'population': {'key': 'all-districts', 'description': 'Synthetic full report population', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic data watermark'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic full export'}}
    C.import_evidence(path, {'schema_version': 'businessobjects-supplied-evidence.v1', 'attachments': [attachment]}, root / 'supplied')
    cap, path = C.load_latest(root / 'capture')
    b = {**binding(raw), 'capture_content_hash': cap['content_hash'], 'definition_fingerprint': cap['source']['definition_fingerprint'], 'state_sha256': C.sha(cap['request']['state'])}
    return {'snapshot': cap['source']['snapshot'], 'request': req, 'envelope': cap, 'capture_path': path,
        'object_key': 'yield', 'profile': profile(), 'attachment': cap['attachments'][0], 'raw': raw, 'raw_path': raw_path,
        'binding': b, 'normalized': C.normalize_results(raw, profile(), b)}


class FakeTransport:
    def __init__(self, root, req, response=None):
        self.root, self.req, self.response, self.calls = root, req, response, []

    def authority(self, scope, fingerprint):
        value, _ = C.load_latest(self.root / 'capture', self.req)
        selected = C.pending_operation_spec(self.req, value)
        assert fingerprint == C.fingerprint(self.req, selected, value)
        assert scope == 'metadata'
        return {'X-SAP-LogonToken': '"fixture-secret"'}

    def __call__(self, method, url, headers, body, maximum, timeout):
        self.calls.append((method, url))
        if isinstance(self.response, Exception): raise self.response
        if self.response is not None: return self.response
        return 200, {}, C.encoded({'document': {'id': 17, 'refreshOnOpen': False}})


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root = Path(tmp.name).resolve()

    def test_import_binds_native_and_independent_inventory_bytes(self):
        req, out = prepare(self.root)
        cap, _ = C.load_latest(self.root / 'capture')
        self.assertEqual(C.check_capture(out['path'])['status'], 'ready')
        cap['source']['snapshot']['responses'][0]['content'] = '{}'
        cap['content_hash'] = C.sha({k: v for k, v in cap.items() if k != 'content_hash'})
        with self.assertRaises(ValueError): C.validate_envelope(cap)

    def test_original_source_symlink_is_rejected(self):
        req, out = prepare(self.root)
        original = self.root / 'supplied' / 'element.json'; moved = original.with_suffix('.original'); original.rename(moved)
        original.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, 'symlink'): C.import_local(req, self.root / 'supplied', self.root / 'another', allow_source_read=True)

    def test_request_and_original_scope_cannot_change_in_resealed_journal(self):
        req, _ = prepare(self.root)
        value, path = C.load_latest(self.root / 'capture')
        value['request']['authorization_ref'] = 'Changed approval reference'
        value['request_sha256'] = C.sha(value['request'])
        C.advance(self.root / 'capture', value, path)
        with self.assertRaisesRegex(ValueError, 'journal_transition'): C.load_latest(self.root / 'capture')

    def test_capture_budget_rejects_before_writing_unusable_revision(self):
        req, _ = prepare(self.root); value, path = C.load_latest(self.root / 'capture')
        old = C.MAX_ENVELOPE_BYTES
        try:
            C.MAX_ENVELOPE_BYTES = len(C.encoded(value)) - 1
            with self.assertRaisesRegex(ValueError, 'capture_byte_limit'): C.advance(self.root / 'capture', value, path)
            self.assertEqual(len(list((self.root / 'capture').glob('capture-*.json'))), 1)
        finally: C.MAX_ENVELOPE_BYTES = old

    def test_placement_observation_requires_nonempty_text(self):
        fixture = capture_fixture(self.root)
        for bad in ({'declared': True}, '', True):
            row = copy.deepcopy(fixture['attachment']); row['observed_state']['placement_reference'] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'placement_reference'):
                C.validate_attachment(row, fixture['envelope'])

    def test_unicode_capture_respects_shared_translator_budget(self):
        req, _ = prepare(self.root); value, path = C.load_latest(self.root / 'capture')
        value['gaps'].append('\u6f22' * 200)
        old = C.MAX_ENVELOPE_BYTES
        try:
            C.MAX_ENVELOPE_BYTES = len(C.encoded(value)) + 300
            self.assertGreater(C.intake_bytes(value), C.MAX_ENVELOPE_BYTES)
            with self.assertRaisesRegex(ValueError, 'capture_byte_limit'):
                C.advance(self.root / 'capture', value, path)
            self.assertEqual(len(list((self.root / 'capture').glob('capture-*.json'))), 1)
        finally: C.MAX_ENVELOPE_BYTES = old

    def test_connected_capture_requires_external_authority_and_pins_scope(self):
        req, _ = prepare(self.root, True)
        with self.assertRaisesRegex(ValueError, 'external_runtime_authority'): C.capture(req, self.root / 'capture')
        fake = FakeTransport(self.root, req)
        result = C.capture(req, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(result['status'], 'ready'); self.assertEqual(len(fake.calls), 2)
        C.capture(req, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(len(fake.calls), 2)

    def test_uncertain_get_never_blind_replays_or_cleans_borrowed_session(self):
        req, _ = prepare(self.root, True); fake = FakeTransport(self.root, req, OSError('untrusted failure body'))
        result = C.capture(req, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(result['status'], 'blocked'); self.assertEqual(len(fake.calls), 1)
        with self.assertRaisesRegex(ValueError, 'blocked'): C.capture(req, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertNotIn('untrusted failure body', Path(result['path']).read_text())
        self.assertFalse(any('logoff' in url for _, url in fake.calls))

    def test_echo_session_rotation_and_response_redirect_are_not_saved(self):
        for i, response in enumerate([(200, {}, b'{"document":"fixture-secret"}'),
            (200, {'Set-Cookie': 'changed'}, b'{}'), (302, {'Location': 'https://other.example.invalid'}, b'{}')]):
            root = self.root / str(i); req, _ = prepare(root, True); fake = FakeTransport(root, req, response)
            out = C.capture(req, root / 'capture', authority=fake.authority, transport=fake)
            self.assertEqual(out['status'], 'blocked'); self.assertNotIn('fixture-secret', Path(out['path']).read_text())

    def test_complete_results_require_exact_all_provider_observation(self):
        fixture = capture_fixture(self.root); cap = fixture['envelope']
        for field, changed in [('provider_states', []), ('execution_status', 'partial')]:
            value = copy.deepcopy(cap); value['attachments'][0]['observed_state'][field] = changed
            value['content_hash'] = C.sha({k: v for k, v in value.items() if k != 'content_hash'})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'complete_evidence_required'): C.validate_envelope(value)

    def test_comparison_replays_normalizer_and_requires_full_columns(self):
        f = capture_fixture(self.root); cap, pin = f['envelope'], f['attachment']
        asset = {'kind': 'visual', 'source_identity': {'object_key': 'yield', 'definition_fingerprint': cap['source']['definition_fingerprint']}}
        case = {'lane': 'numeric', 'source_capture': {'sha256': C.sha(C.encoded(cap))}, 'source_binding': {
            k: f['binding'][k] for k in ('definition_fingerprint', 'state_sha256', 'object_key', 'attachment_id')}}
        context = {**state(), **{k: v for k, v in result_contract().items() if k != 'reference'},
            'population': pin['population']['key'], 'data_watermark': pin['freshness']['data_watermark'], 'result_scope': pin['result_scope']}
        source = {'format': 'businessobjects-normalized', 'raw_file': {'sha256': pin['sha256']}, 'context': context}
        target = {'context': {**copy.deepcopy(context), 'cache': 'independent target policy'}}
        columns = [{'source': 'district', 'target': 'district'}, {'source': 'yield', 'target': 'yield'}]
        self.assertEqual(C.comparison_gaps(cap, asset, case, source, target, f['normalized'], columns), [])
        self.assertIn('source.businessobjects_compared_columns_incomplete', C.comparison_gaps(cap, asset, case, source, target, f['normalized'], columns[:1]))
        f['normalized']['rows'][0]['yield'] = '1.1'
        self.assertIn('source.businessobjects_normalization_changed', C.comparison_gaps(cap, asset, case, source, target, f['normalized'], columns))


class PureCaptureTests(unittest.TestCase):
    def test_metadata_profile_is_canonical_and_no_lov_computation(self):
        req = request(True)
        spec = C.operation_spec(req, req['operations'][1])
        self.assertEqual(spec['url'], 'https://source.example.invalid:8443/proxy/biprws/raylight/v1/documents/17/parameters?lovInfo=false')
        self.assertEqual(spec['headers'], {'Accept': 'application/json'})
        self.assertIsNone(spec['body'])
        self.assertEqual(spec['scope'], 'metadata')

    def test_refresh_save_logout_render_and_arbitrary_fields_are_rejected(self):
        req = request(True)
        for kind in ('refresh', 'render', 'save', 'cleanup', 'logoff', 'sap_refreshdata=true'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                C.validate_request({**req, 'operations': [operation(kind)]})
        for field, value in [('url', 'https://other.example.invalid'), ('body', {}), ('method', 'PUT'),
                             ('query', 'sap_refreshdata=true'), ('headers', {'Accept': 'application/pdf'})]:
            changed = copy.deepcopy(req); changed['operations'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): C.validate_request(changed)

    def test_source_identity_unsafe_paths_and_duplicate_operations(self):
        for origin in ('http://source.example.invalid', 'https://user@source.example.invalid', 'https://source.example.invalid/path',
                       'https://source.example.invalid:abc', 'https://source.example.invalid?x=1'):
            req = request(True); req['identity']['source_origin'] = origin
            with self.subTest(origin=origin), self.assertRaises(ValueError): C.validate_request(req)
        for path in ('/biprws/../other', '/biprws%2fother', '//biprws', '/biprws?x=1'):
            req = request(True); req['api_profile']['rest_path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError): C.validate_request(req)
        req = request(True); req['operations'].append(copy.deepcopy(req['operations'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate_operation'): C.validate_request(req)

    def test_unknown_runtime_and_report_engine_are_supplied_only(self):
        for field, value in [('product_version', 'latest'), ('service_pack', None), ('report_engine', 'crystal_classic')]:
            req = request(True); req['identity'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): C.validate_request(req)

    def test_stage_omission_duplicate_prompts_and_principal_mismatch(self):
        req = request(); del req['state']['filters']['block']
        with self.assertRaises(ValueError): C.validate_request(req)
        req = request(); req['state']['principal'] = 'another-reader'
        with self.assertRaisesRegex(ValueError, 'principal_mismatch'): C.validate_request(req)
        req = request(); p = {'id': '0', 'provider_id': 'DP0', 'answer_mode': 'explicit', 'value': 'West'}
        req['state']['parameters']['prompts'] = [p, p]
        with self.assertRaisesRegex(ValueError, 'duplicate_prompt'): C.validate_request(req)

    def test_redirects_and_credentials_are_not_retained(self):
        with self.assertRaisesRegex(ValueError, 'redirect_rejected'):
            C.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example.invalid')
        for raw in (b'{"logonToken":"fixture-value"}', b'<password>fixture-value</password>', b'X-SAP-LogonToken: fixture-value'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): C.screen(raw)
        for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
            with self.subTest(encoding=encoding), self.assertRaisesRegex(ValueError, 'credential_echo'):
                C.screen('fixture-secret'.encode(encoding), 'fixture-secret', opaque=True)
        self.assertEqual(C.screen(b'\xff\x01\x00', opaque=True), 'opaque_bytes_not_assessed')

    def test_cms_credential_attributes_are_screened_before_retention(self):
        for raw in (b'<attrs><attr name="logonToken" type="string">fixture-value</attr></attrs>',
                    b'{"attrs":{"attr":{"@name":"logonToken","$":"fixture-value"}}}',
                    b'{"lo\\u0067onToken":"fixture-value"}',
                    b'\xff<attr name="logonToken">fixture-value</attr>'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'credential_bearing_source'):
                C.screen(raw, opaque=True)

    def test_known_limit_stage_requires_actual_limit(self):
        for stage in ('before_aggregation', 'after_aggregation'):
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'result_limit_missing'):
                C.result_context({**result_contract(), 'row_limit_stage': stage})
            C.result_context({**result_contract(), 'row_limit_stage': stage, 'row_limit': 10})

    def test_json_decimal_precision_and_csv_are_preserved(self):
        raw = b'[{"district":"West","yield":1.100000000000000001},{"district":"East","yield":9007199254740993}]'
        normalized = C.normalize_results(raw, profile(), binding(raw))
        self.assertEqual([r['yield'] for r in normalized['rows']], ['1.100000000000000001', '9007199254740993'])
        csv = b'district,yield\nWest,1.100000000000000001\nEast,9007199254740993\n'
        self.assertEqual(C.normalize_results(csv, profile('csv'), binding(csv))['rows'], normalized['rows'])

    def test_errors_cannot_be_null_or_hidden_in_string_columns(self):
        for marker in ('#CONTEXT', '#INCOMPATIBLE', '#MULTIVALUE', '#DIV/0', '#TOREFRESH',
                       '#COMPUTATION', '#EXTERNAL', '#NODATA', '#RECURSIVE', '#SYNTAX'):
            p = profile(); p['columns'][0].update(nullable=True, null_tokens=[marker])
            raw = C.encoded([{'district': marker, 'yield': 1}])
            with self.subTest(marker=marker), self.assertRaisesRegex(ValueError, 'source_cell_error'):
                C.normalize_results(raw, p, binding(raw))
        raw = b'{"errors":[],"rows":[]}'
        p = profile(); p['rows_pointer'] = '/rows'
        with self.assertRaisesRegex(ValueError, 'source_result_error'): C.normalize_results(raw, p, binding(raw))

    def test_null_and_formatted_values_are_explicit(self):
        raw = b'[{"district":"West","yield":null}]'
        with self.assertRaisesRegex(ValueError, 'unexpected_null'): C.normalize_results(raw, profile(), binding(raw))
        p = profile(); p['columns'][1]['nullable'] = True
        self.assertIsNone(C.normalize_results(raw, p, binding(raw))['rows'][0]['yield'])
        raw = b'[{"district":"West","yield":"1,234.00"}]'
        with self.assertRaisesRegex(ValueError, 'raw_number_required'): C.normalize_results(raw, profile(), binding(raw))
        p = profile(); p['value_representation'] = 'formatted'
        with self.assertRaisesRegex(ValueError, 'normalization_profile'): C.normalize_results(raw, p, binding(raw))

    def test_duplicate_json_headers_rows_and_tampered_binding(self):
        raw = b'[{"district":"West","district":"East","yield":1}]'
        with self.assertRaises(ValueError): C.normalize_results(raw, profile(), binding(raw))
        raw = b'district,yield\nWest,1,extra\n'
        with self.assertRaises(ValueError): C.normalize_results(raw, profile('csv'), binding(raw))
        raw = b'[]'; b = binding(raw); b['attachment_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'normalization_binding'): C.normalize_results(raw, profile(), b)


if __name__ == '__main__': unittest.main()
