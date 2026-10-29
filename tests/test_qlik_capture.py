"""Original neutral Qlik fixtures; no live calls, browser or external runtime."""
import copy
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('qlik_capture_tested', ROOT / 'skills/omni-artifact-translator/scripts/qlik_capture.py')
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)


def snapshot():
    objects = [{'kind': kind, 'id': oid, 'payload': payload, 'evidence_ref': 'Synthetic retained QIX properties'} for kind, oid, payload in [
        ('app', 'app-one', {'qFileName': 'app-one', 'qTitle': 'Garden quantities'}),
        ('sheet', 'sheet-one', {'qInfo': {'qId': 'sheet-one', 'qType': 'sheet'}, 'cells': [{'name': 'chart-one'}]}),
        ('visual', 'chart-one', {'qInfo': {'qId': 'chart-one', 'qType': 'barchart'},
            'qHyperCubeDef': {'qDimensions': [{'qDef': {'qFieldDefs': ['Item']}}],
                              'qMeasures': [{'qDef': {'qDef': 'Sum(Quantity)'}}]}})]]
    items = []
    for key, kind, parent, object_kind, oid, pointer, config in [
        ('app', 'app', None, 'app', 'app-one', '', {}), ('sheet', 'sheet', 'app', 'sheet', 'sheet-one', '', {}),
        ('visual', 'visual', 'app', 'visual', 'chart-one', '', {}),
        ('place-one', 'placement', 'sheet', 'sheet', 'sheet-one', '/cells/0', {'visual_key': 'visual'})]:
        items.append({'key': key, 'kind': kind, 'parent_key': parent, 'native_id': 'chart-one' if kind == 'placement' else oid,
            'definition_id': None, 'disposition': 'include', 'reference': 'Independent synthetic inventory',
            'configuration': config, 'source_mapping': {'object_kind': object_kind, 'object_id': oid, 'pointer': pointer}})
    return {'schema_version': 'qlik-api-snapshot.v1', 'identity': {'source_origin': 'https://source.example.invalid',
        'tenant_id': 'tenant-one', 'product': 'cloud', 'version': 'synthetic-cloud', 'principal_ref': 'fixture-reader',
        'engine_version': 'synthetic-engine', 'reference': 'Synthetic source identity'}, 'root': {'kind': 'app', 'id': 'app-one'},
        'objects': objects, 'inventory': {'reference': 'Independent expected inventory', 'completeness': 'selected_scope_declared',
                                        'items': items}, 'gaps': ['synthetic_fixture_only']}


def operation(sheet=False):
    template = {'appId': 'app-one', 'selectionType': 'selectionsByState', 'selectionStrategy': 'failOnErrors',
        'selectionsByState': {'$': []}, 'sheet' if sheet else 'visualization': {
            'id': 'sheet-one' if sheet else 'chart-one', 'widthPx': 1200, 'heightPx': 800,
            **({} if sheet else {'type': 'visualization'})}}
    return {'operation_id': 'render-one', 'kind': 'report', 'object_key': 'sheet' if sheet else 'visual',
        'reference': 'Synthetic selected render', 'body': {'type': 'sense-sheet-1.0' if sheet else 'sense-image-1.0',
        'output': {'type': 'pdf', 'outputId': 'output-one', 'pdfOutput': {'size': 'A4', 'orientation': 'L', 'resizeType': 'autofit'}},
        'senseSheetTemplate' if sheet else 'senseImageTemplate': template}}


def request(connected=False):
    value = snapshot()
    return {'schema_version': C.REQUEST, 'capture_id': 'synthetic-qlik', 'identity': value['identity'], 'root': value['root'],
        'authorization_ref': 'Synthetic source-read request', 'credential_ref': 'host-bearer-reference',
        'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {'selectionType': 'selectionsByState', 'selectionsByState': {'$': []}}, 'parameters': {},
                  'timezone': 'UTC', 'locale': 'en-US', 'principal': 'fixture-reader', 'cache': None, 'reference': 'Synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json', 'api_profile': C.PROFILE if connected else None,
        'operations': [operation()] if connected else []}


def supplied(root, value=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True); value = value or snapshot()
    records = [{'source_path': 'native.json', 'source_kind': 'qix_json', 'source_pointer': '/%d' % i,
        'target_pointer': '/objects/%d/payload' % i, 'mapping': 'exact_json', 'member_path': None, 'mcp_evidence': None,
        'reference': 'Synthetic original QIX response'} for i in range(len(value['objects']))]
    records.append({'source_path': 'inventory.json', 'source_kind': 'supplied_json', 'source_pointer': '', 'target_pointer': '/inventory',
        'mapping': 'exact_json', 'member_path': None, 'mcp_evidence': None, 'reference': 'Independent original inventory'})
    manifest = {'schema_version': 'qlik-originals.v1', 'reference': 'Synthetic original-file crosswalk', 'records': records}
    for path, data in [('snapshot.json', value), ('originals.json', manifest), ('inventory.json', value['inventory']),
                       ('native.json', [o['payload'] for o in value['objects']])]:
        (root / path).write_bytes(C.encoded(data))
    return manifest


def prepare(root, req=None, connected=False):
    root = Path(root); supplied(root / 'supplied'); r = req or request(connected)
    return r, C.import_local(r, root / 'supplied', root / 'capture', allow_source_read=True)


def evidence_spec():
    return {'schema_version': 'qlik-supplied-evidence.v1', 'attachments': [{
        'attachment_id': 'numbers-one', 'object_key': 'visual', 'format': 'csv', 'source_path': 'numbers.csv', 'member_path': None,
        'origin': 'full', 'result_scope': 'query_result', 'observed_state': {'state': request()['state'],
        'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic observed state'},
        'population': {'key': 'garden', 'description': 'All synthetic garden rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic watermark'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic complete export'}, 'reference': 'Synthetic source results'}]}


class FakeTransport:
    def __init__(self, directory=None, req=None, overrides=None):
        self.directory, self.req, self.overrides = directory, req, overrides or {}
        self.calls, self.grants = [], []

    def authority(self, scope, fingerprint):
        self.grants.append((scope, copy.deepcopy(fingerprint)))
        if self.directory is not None:
            value, _ = C.load_latest(self.directory, self.req)
            selected = C.pending_operation_spec(self.req, value)
            self_fingerprint = {'request_sha256': C.sha(C.validate_request(self.req)), 'operation_id': selected['operation_id'],
                'phase': selected['phase'], 'method': selected['method'], 'url': selected['url'], 'body_sha256': C.sha(selected['body'])}
            assert fingerprint == self_fingerprint
        return {'Authorization': 'Bearer fixture-never-retained-token'}

    def __call__(self, method, url, headers, body, maximum, timeout):
        phase = 'create' if method == 'POST' else 'status' if url.endswith('/status') else 'outputs' if url.endswith('/outputs') else 'download'
        self.calls.append((phase, method, url, body))
        default = {'create': (202, C.encoded({'requestId': 'job-one', 'outputsUrl': 'https://source.example.invalid/api/v1/reports/job-one/outputs'})),
            'status': (200, b'{"status":"done"}'), 'outputs': (200, C.encoded({'data': [{'status': 'done', 'outputId': 'output-one',
                'location': 'https://source.example.invalid:443/api/v1/temp-contents/output-one?inline=1'}], 'links': {}})),
            'download': (200, b'%PDF-1.7\n%%EOF')}
        status, raw = self.overrides.get(phase, default[phase])
        return status, {'Content-Type': 'application/pdf' if phase == 'download' else 'application/json'}, raw


class QlikCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def run_capture(self, *, req=None, overrides=None):
        req, out = prepare(self.root, req=req, connected=True)
        transport = FakeTransport(Path(out['output']).parent, req, overrides)
        result = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
        return req, result, transport

    def test_passive_originals_are_pinned_without_execution(self):
        _, out = prepare(self.root)
        self.assertFalse(out['capture']['source_execution']); self.assertEqual(out['capture']['operations'], [])
        self.assertEqual(C.check_capture(out['output'])['status'], 'verified_local_bytes')

    def test_original_mapping_tamper_and_missing_grant_rejected(self):
        supplied(self.root / 'supplied')
        with self.assertRaisesRegex(ValueError, 'source_read_grant'):
            C.import_local(request(), self.root / 'supplied', self.root / 'capture')
        (self.root / 'supplied' / 'native.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, 'pointer_missing'):
            C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)

    def test_report_lifecycle_derives_only_verified_routes(self):
        req, result, transport = self.run_capture()
        self.assertEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual([x[0] for x in transport.calls], ['create', 'status', 'outputs', 'download'])
        self.assertTrue(result['capture']['source_execution']); self.assertEqual(result['capture']['saved_query_execution'], 'not_requested')
        self.assertTrue(all(x[0] == 'render' for x in transport.grants))
        self.assertTrue(all(x['inspection']['observed_state'] is None for x in result['capture']['responses']))
        C.check_capture(result['output'])

    def test_existing_sheet_pdf_is_supported(self):
        req = request(True); req['operations'] = [operation(sheet=True)]
        _, result, _ = self.run_capture(req=req)
        self.assertEqual(result['status'], 'acquired_requested_operations')

    def test_sheet_render_requires_every_native_child_selected(self):
        req = request(True); req['operations'] = [operation(sheet=True)]
        for change in (
            lambda v: v['objects'][2]['payload'].update(qMeta={'published': False}),
            lambda v: v['inventory']['items'][2].update(disposition='out_of_scope'),
            lambda v: v['inventory']['items'][3].update(disposition='manual_review'),
            lambda v: v['inventory']['items'].pop(),
            lambda v: v['objects'][1]['payload']['cells'].append({'name': 'unmapped-chart'}),
        ):
            value = snapshot(); change(value)
            with self.assertRaisesRegex(ValueError, 'sheet_child_not_selected'):
                C.validate_scope(req, value)
        value = snapshot(); value['objects'][1]['payload']['qChildren'] = [{'qId': 'container'}]
        with self.assertRaisesRegex(ValueError, 'sheet_unknown_child'):
            C.validate_scope(req, value)

    def test_http_evidence_cannot_claim_no_dispatch(self):
        _, result, _ = self.run_capture()
        value = copy.deepcopy(result['capture'])
        for record in value['operations']: record['dispatched'] = False
        C._execution_state(value)
        value['content_hash'] = C.sha({k: v for k, v in value.items() if k != 'content_hash'})
        with self.assertRaisesRegex(ValueError, 'operation_record'):
            C.validate_envelope(value)

    def test_unreviewed_body_options_and_internal_templates_rejected(self):
        variants = []
        for key in ('jsOpts', 'patches', 'callback'):
            req = request(True); req['operations'][0]['body']['senseImageTemplate']['visualization'][key] = {}
            variants.append(req)
        req = request(True); req['operations'][0]['body']['requestCallBackAction'] = {'httpRequest': {'uri': 'https://other.invalid'}}; variants.append(req)
        req = request(True); req['operations'][0]['body']['type'] = 'sense-story-1.0'; variants.append(req)
        req = request(True); req['operations'][0]['body']['senseImageTemplate']['visualization']['type'] = 'sessionobject'; variants.append(req)
        for req in variants:
            with self.assertRaises(ValueError): C.validate_request(req)

    def test_requested_state_is_not_silently_discarded(self):
        req = request(True); req['state']['parameters'] = {'variable': 'value'}
        with self.assertRaisesRegex(ValueError, 'requested_state_mismatch'): C.validate_request(req)
        req = request(True); req['operations'][0]['body']['senseImageTemplate']['selectionStrategy'] = 'ignoreErrorsNoDetails'
        with self.assertRaisesRegex(ValueError, 'report_template'): C.validate_request(req)
        req = request(True); req['state']['filters']['selectionsByState']['alt'] = []
        with self.assertRaisesRegex(ValueError, 'requested_state_mismatch'): C.validate_request(req)

    def test_client_managed_passive_only_and_scope_mismatch(self):
        req = request(True); req['identity']['product'] = 'client_managed'
        with self.assertRaisesRegex(ValueError, 'connected_cloud_only'): C.validate_request(req)
        req['operations'] = []; C.validate_request(req)
        req = request(True); req['operations'][0]['body']['senseImageTemplate']['visualization']['id'] = 'other-chart'
        with self.assertRaisesRegex(ValueError, 'native_object_binding'): C.validate_scope(C.validate_request(req), snapshot())

    def test_private_source_cannot_be_promoted_by_inventory(self):
        value = snapshot(); value['objects'][2]['payload']['qMeta'] = {'published': False}
        with self.assertRaisesRegex(ValueError, 'scope_not_selected'): C.validate_scope(request(True), value)
        value['inventory']['items'][2]['configuration']['selection_reference'] = 'Explicit selected private scope'
        C.validate_scope(request(True), value)

    def test_output_url_is_same_origin_fixed_temp_content_only(self):
        for location in ('https://other.invalid/api/v1/temp-contents/one', 'https://source.example.invalid/api/v1/apps/app-one',
                         'https://source.example.invalid/api/v1/temp-contents/%2e%2e',
                         'https://source.example.invalid/api/v1/temp-contents/one?access_token=secret',
                         'https://user@source.example.invalid/api/v1/temp-contents/one'):
            with self.assertRaises(ValueError): C.safe_output_url(request(), location)

    def test_selection_errors_reject_done_response_before_download(self):
        _, result, transport = self.run_capture(overrides={'status': (200, b'{"status":"done","requestErrors":[{"meta":{"selectionErrors":[{"detail":"failed"}]}}]}')})
        self.assertNotEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual([x[0] for x in transport.calls], ['create', 'status'])
        C.check_capture(result['output'])

    def test_uncertain_post_never_replayed(self):
        req, result, transport = self.run_capture(overrides={'create': (503, b'private failure body')})
        self.assertEqual(result['status'], 'blocked')
        updated = C.capture(req, Path(result['output']).parent, authority=transport.authority, transport=transport)
        self.assertEqual(len(transport.calls), 1); self.assertEqual(updated['capture']['responses'], [])
        self.assertNotIn('private failure', C.encoded(updated['capture']).decode())

    def test_secrets_and_redirect_bodies_are_not_retained(self):
        _, result, transport = self.run_capture(overrides={'create': (202, b'{"requestId":"job-one","password":"fixture-sensitive"}')})
        self.assertEqual(result['status'], 'blocked'); self.assertEqual(result['capture']['responses'], [])
        self.assertFalse(list(Path(result['output']).parent.glob('response-*')))
        with self.assertRaises(ValueError): C.inspect_attachment(b'password,value\nsecret,2\n', 'csv')

    def test_unknown_download_route_requires_supplied_transfer(self):
        _, result, transport = self.run_capture(overrides={'outputs': (200, C.encoded({'data': [{'status': 'done',
            'outputId': 'output-one', 'location': 'https://other.invalid/file.pdf'}], 'links': {}}))})
        self.assertEqual(len(transport.calls), 3); self.assertNotEqual(result['status'], 'acquired_requested_operations')
        self.assertIn('source_response_uncertain_or_unsupported_transfer_redacted', result['capture']['gaps'])

    def test_download_signature_and_size_are_checked(self):
        _, result, _ = self.run_capture(overrides={'download': (200, b'<html>error</html>')})
        self.assertNotEqual(result['status'], 'acquired_requested_operations')
        self.assertEqual(len(result['capture']['responses']), 3)

    def test_status_processing_requires_later_bounded_resume(self):
        req, result, transport = self.run_capture(overrides={'status': (200, b'{"status":"processing"}')})
        self.assertEqual(len(transport.calls), 2); self.assertEqual(result['status'], 'partial')
        C.capture(req, Path(result['output']).parent, authority=transport.authority, transport=transport)
        self.assertEqual(len(transport.calls), 2)
        transport.overrides.clear()
        future = result['capture']['retry_not_before_epoch'] + 1
        result = C.capture(req, Path(result['output']).parent, authority=transport.authority, transport=transport, now=lambda: future)
        self.assertEqual([x[0] for x in transport.calls].count('create'), 1)
        self.assertEqual(result['status'], 'acquired_requested_operations')
        C.check_capture(result['output'])

    def test_host_denial_is_not_source_execution(self):
        req, out = prepare(self.root, connected=True)
        def deny(*args): raise ValueError('private authority details')
        with self.assertRaisesRegex(ValueError, 'host_authority_rejected'):
            C.capture(req, Path(out['output']).parent, authority=deny, transport=FakeTransport())
        value, _ = C.load_latest(Path(out['output']).parent)
        self.assertFalse(value['source_execution']); self.assertEqual(value['operations'][0]['status'], 'denied')

    def test_resealed_journal_cannot_reset_or_swap_source(self):
        req, result, transport = self.run_capture(overrides={'create': (503, b'{}')})
        root = Path(result['output']).parent; value, _ = C._load(root)
        value.update(operations=[], responses=[], request_count=0, network_bytes=0, source_execution=False,
                     render_execution='not_run', status='partial')
        C.advance(root, value)
        with self.assertRaises(ValueError): C.load_latest(root)
        with self.assertRaises(ValueError): C.capture(req, root, authority=transport.authority, transport=transport)
        self.assertEqual(len(transport.calls), 1)

    def test_supplied_csv_has_observed_state_and_exact_count(self):
        _, out = prepare(self.root)
        (self.root / 'supplied' / 'numbers.csv').write_bytes(b'item,quantity\nseed,2\nplant,3\n')
        result = C.import_evidence(out['output'], evidence_spec(), self.root / 'supplied')
        C.check_capture(result['output']); self.assertEqual(result['capture']['attachments'][0]['inspection']['row_count'], 2)

    def test_archive_members_inert_and_paths_bounded(self):
        def archive(name, raw):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w') as z: z.writestr(name, raw)
            return buf.getvalue()
        with self.assertRaises(ValueError): C.zip_members(archive('../escape', b'x'))
        with self.assertRaises(ValueError): C.zip_members(archive('code.qvs', b'password=secret'))
        members = C.zip_members(archive('readme.txt', b'Original inert fixture'))
        self.assertEqual(members['readme.txt']['raw'], b'Original inert fixture')

    def test_source_symlink_and_changed_resume_request_rejected(self):
        req, out = prepare(self.root, connected=True)
        changed = copy.deepcopy(req); changed['identity']['tenant_id'] = 'other-tenant'
        with self.assertRaises(ValueError): C.capture(changed, Path(out['output']).parent, authority=FakeTransport().authority)
        pin = out['capture']['source']['originals'][0]['file']; path = Path(out['output']).parent / pin['path']
        path.rename(path.with_suffix('.other')); path.symlink_to(path.with_suffix('.other'))
        with self.assertRaises(ValueError): C.check_capture(out['output'])


if __name__ == '__main__':
    unittest.main()
