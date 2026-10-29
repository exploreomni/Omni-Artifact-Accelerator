"""Original neutral WebFOCUS fixtures; no live service, vendor code or decoder."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-translator/scripts/webfocus_capture.py'
spec = importlib.util.spec_from_file_location('webfocus_capture_tested', SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def request(connected=False):
    return {'schema_version': C.REQUEST, 'capture_id': 'synthetic-webfocus', 'product': 'webfocus',
        'source_origin': 'https://webfocus.example.invalid', 'product_version': 'synthetic-9.3.3',
        'product_evidence_ref': 'Synthetic product declaration', 'principal_ref': 'fixture-reader',
        'authorization_ref': 'Synthetic source-read request', 'credential_ref': 'host-session-reference',
        'evidence_mode': 'synthetic_fixture', 'source_revision': {'kind': 'supplied_snapshot', 'value': 'fixture-one',
        'reference': 'Synthetic supplied export'}, 'root_key': 'page-main', 'route': 'unselected',
        'route_reference': None, 'target_surface': 'both', 'state': {'filters': {}, 'parameters': {'REGION': 'West'},
        'timezone': 'UTC', 'locale': 'en-US', 'principal': 'fixture-reader', 'cache': None,
        'reference': 'Synthetic requested state'}, 'originals_path': 'originals.json', 'inventory_path': 'inventory.json',
        'crosswalk_path': 'crosswalk.json', 'operations': [{'operation_id': 'content-one', 'action': 'getContent',
        'resource_path': '/WFC/Repository/garden/report.fex', 'reference': 'Synthetic reviewed operation'}] if connected else [],
        'api_contract': {'context_path': '/ibi_apps', 'wrapper': 'ibfsrpc.v1', 'auth_header': 'Cookie',
        'reference': 'Synthetic pinned API contract'} if connected else None}


def supplied(root, *, archive=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    originals = [('report.fex', 'fex', 'utf-8', b'TABLE FILE garden\nSUM QUANTITY BY REGION\nEND\n'),
        ('theme.sty', 'sty', 'windows-1252', 'TYPE=REPORT, TITLE=\'Caf\xe9 totals\', $'.encode('cp1252')),
        ('page.html', 'html', 'utf-8', b'<html><script>throw new Error("must remain inert")</script></html>')]
    if archive is not None:
        originals.append(('change.zip', 'cm_zip', 'binary', archive))
    records = []
    for path, kind, encoding, raw in originals:
        (root / path).write_bytes(raw)
        records.append({'source_path': path, 'kind': kind, 'encoding': encoding, 'sha256': C.F.raw_sha(raw),
                        'reference': 'Original synthetic bytes'})
    manifest = {'schema_version': 'webfocus-originals.v1', 'reference': 'Synthetic originals list', 'records': records}
    objects = []
    for key, kind, parent, configuration in [('page-main', 'page', None, {}), ('visual-one', 'visual', 'page-main', {}),
        ('place-one', 'placement', 'page-main', {'visual_key': 'visual-one'}), ('filter-one', 'control', 'page-main', {})]:
        objects.append({'key': key, 'kind': kind, 'name': key, 'parent_key': parent, 'source_object_id': None,
            'disposition': 'include', 'disposition_reference': 'Synthetic scope', 'evidence_reference': 'Separate fixture listing',
            'configuration': configuration})
    inventory = {'schema_version': 'webfocus-source-enumeration.v1', 'method': 'separate_source_enumeration',
        'reference': 'Separate synthetic expected object listing', 'completeness': 'selected_scope_declared', 'objects': objects}
    crosswalk = {'schema_version': 'webfocus-identity-crosswalk.v1', 'reference': 'Synthetic explicit identity crosswalk',
        'rows': [{'key': x['key'], 'resource_path': '/WFC/Repository/garden/report.fex' if x['kind'] in ('visual', 'placement')
                 else '/WFC/Repository/garden' if x['kind'] == 'page' else None, 'source_object_id': None,
                 'reference': 'Synthetic mapping'} for x in objects]}
    for name, value in [('originals', manifest), ('inventory', inventory), ('crosswalk', crosswalk)]:
        (root / (name + '.json')).write_bytes(C.encoded(value))
    return manifest


def prepare(root, connected=False, req=None):
    supplied(root / 'supplied')
    r = req or request(connected)
    return r, C.import_local(r, root / 'supplied', root / 'capture', allow_source_read=True)


def evidence_spec():
    return {'schema_version': 'webfocus-supplied-evidence.v1', 'attachments': [{
        'attachment_id': 'numbers-one', 'object_key': 'visual-one', 'format': 'csv', 'source_path': 'numbers.csv',
        'origin': 'full', 'result_scope': 'query_result', 'observed_state': {'state': request()['state'],
        'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic observed parameters'},
        'population': {'key': 'garden', 'description': 'All synthetic garden rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic watermark'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic full export'},
        'reference': 'Synthetic exact numerical evidence'}]}


class FakeTransport:
    def __init__(self, status=200, raw=b'TABLE FILE garden\nPRINT QUANTITY\nEND\n', media='text/plain'):
        self.status, self.raw, self.media = status, raw, media
        self.calls, self.grants = [], []

    def authority(self, operation, fingerprint):
        self.grants.append((operation, copy.deepcopy(fingerprint)))
        return {'Cookie': 'SYNTHETICSESSION=fixture-never-retained'}

    def __call__(self, method, url, headers, body, maximum, timeout):
        self.calls.append((method, url, body))
        assert headers['Cookie'] == 'SYNTHETICSESSION=fixture-never-retained'
        assert method == 'GET' and body is None
        return self.status, {'Content-Type': self.media}, self.raw


class WebfocusCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_original_bytes_and_independent_denominator_preserved(self):
        _, out = prepare(self.root)
        cap = out['capture']
        self.assertEqual(C.check_capture(out['output'])['status'], 'verified_local_bytes')
        self.assertEqual(len(cap['source']['inventory']['objects']), 4)
        self.assertFalse(cap['source_execution'])
        self.assertEqual(cap['status'], 'partial')
        self.assertEqual(cap['source']['files'][1]['inspection']['encoding'], 'windows-1252')
        self.assertEqual((self.root / 'capture' / cap['source']['files'][2]['path']).read_bytes(),
                         (self.root / 'supplied/page.html').read_bytes())

    def test_cli_returns_current_journal_without_dumping_source(self):
        _, out = prepare(self.root)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(C.main(['check', '--capture', str(self.root / 'capture')]), 0)
        response = C.F.decode(stdout.getvalue().encode())
        self.assertEqual(response, {'status': 'verified_local_bytes', 'output': out['output'],
                                    'native_validation': 'not_performed'})

    def test_csv_credentials_and_malformed_result_contract_reject(self):
        for raw in (b'region,password\nWest,synthetic-secret\n',
                    b'api_key,value\nsynthetic-key,2\n'):
            with self.assertRaisesRegex(ValueError, 'credential'):
                C.inspect_attachment(raw, 'csv')
        C.inspect_attachment(b'region,password\nWest,\n', 'csv')
        supplied(self.root / 'supplied')
        path = self.root / 'supplied/inventory.json'
        inv = C.F.decode(path.read_bytes())
        inv['objects'][1]['configuration']['result_contract'] = {'data_mode': 'full_data'}
        path.write_bytes(C.encoded(inv))
        with self.assertRaisesRegex(ValueError, 'result_context'):
            C.import_local(request(), self.root / 'supplied', self.root / 'bad-result', allow_source_read=True)

    def test_source_authority_and_hashes_required(self):
        supplied(self.root / 'supplied')
        with self.assertRaisesRegex(ValueError, 'source_read_grant'):
            C.import_local(request(), self.root / 'supplied', self.root / 'no-grant')
        (self.root / 'supplied/report.fex').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'original_source_hash'):
            C.import_local(request(), self.root / 'supplied', self.root / 'changed', allow_source_read=True)

    def test_crosswalk_scope_and_inventory_cycles_fail(self):
        supplied(self.root / 'supplied')
        cross = C.F.decode((self.root / 'supplied/crosswalk.json').read_bytes())
        cross['rows'].pop()
        (self.root / 'supplied/crosswalk.json').write_bytes(C.encoded(cross))
        with self.assertRaisesRegex(ValueError, 'crosswalk_denominator'):
            C.import_local(request(), self.root / 'supplied', self.root / 'bad-crosswalk', allow_source_read=True)
        supplied(self.root / 'supplied')
        inv = C.F.decode((self.root / 'supplied/inventory.json').read_bytes())
        inv['objects'][1]['parent_key'] = 'place-one'
        inv['objects'][2]['parent_key'] = 'visual-one'
        (self.root / 'supplied/inventory.json').write_bytes(C.encoded(inv))
        with self.assertRaisesRegex(ValueError, 'cycle'):
            C.import_local(request(), self.root / 'supplied', self.root / 'cycle', allow_source_read=True)

    def test_pinned_bytes_cannot_be_replaced_or_symlinked(self):
        _, out = prepare(self.root)
        pin = out['capture']['source']['files'][0]
        target = self.root / 'capture' / pin['path']
        target.write_bytes(b'edited')
        with self.assertRaisesRegex(ValueError, 'evidence_bytes_changed'):
            C.check_capture(out['output'])
        target.unlink()
        target.symlink_to(self.root / 'supplied/report.fex')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            C.check_capture(out['output'])

    def test_capture_journal_is_immutable_and_evidence_is_pinned(self):
        _, out = prepare(self.root)
        (self.root / 'supplied/numbers.csv').write_bytes(b'region,quantity\nWest,2.50\nEast,3.75\n')
        added = C.import_evidence(out['output'], evidence_spec(), self.root / 'supplied')
        self.assertNotEqual(out['output'], added['output'])
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')
        self.assertEqual(added['capture']['attachments'][0]['inspection']['row_count'], 2)
        self.assertEqual(len(C.F.decode(Path(out['output']).read_bytes())['attachments']), 0)
        with self.assertRaisesRegex(ValueError, 'evidence_import'):
            C.import_evidence(out['output'], evidence_spec(), self.root / 'supplied')

    def test_result_completeness_needs_observed_principal_and_count(self):
        _, out = prepare(self.root)
        (self.root / 'supplied/numbers.csv').write_bytes(b'region,quantity\nWest,2\n')
        with self.assertRaisesRegex(ValueError, 'count_contradiction'):
            C.import_evidence(out['output'], evidence_spec(), self.root / 'supplied')
        e = evidence_spec()
        e['attachments'][0]['observed_state']['state']['principal'] = None
        with self.assertRaisesRegex(ValueError, 'complete_result_evidence'):
            C.import_evidence(out['output'], e, self.root / 'supplied')

    def test_zip_member_inventory_only_and_unsafe_members_rejected(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('cm/report.fex', 'TABLE FILE garden\nEND\n')
        supplied(self.root / 'supplied', archive=data.getvalue())
        out = C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        info = out['capture']['source']['files'][-1]['inspection']
        self.assertEqual(info['interpretation'], 'cm_zip_members_inventoried_only')
        self.assertFalse((self.root / 'capture/cm').exists())
        for name, mode in [('../escape.fex', 0), ('link', (stat.S_IFLNK | 0o777) << 16)]:
            blob = io.BytesIO()
            with zipfile.ZipFile(blob, 'w') as z:
                entry = zipfile.ZipInfo(name); entry.external_attr = mode
                z.writestr(entry, 'target')
            with self.assertRaises(ValueError):
                C.inspect_zip(blob.getvalue())

    def test_request_rejects_executable_actions_and_path_injection(self):
        for action in ('run', 'runAdHocFex', 'describeFex', 'getDetails', 'delete', 'get&IBIRS_action=run'):
            r = request(True); r['operations'][0]['action'] = action
            with self.assertRaisesRegex(ValueError, 'read_operation'):
                C.validate_request(r)
        for path in ('/WFC/Repository/../hidden', '/WFC/Repository/%2e%2e/x', '/WFC/Repository/a?IBIRS_action=run',
                     '/WFC/Repository//x', '/outside/file.fex'):
            r = request(True); r['operations'][0]['resource_path'] = path
            with self.assertRaises(ValueError):
                C.operation_url(r, r['operations'][0])
        r = request(True)
        bad = copy.deepcopy(r['operations'][0]); bad['resource_path'] = '/WFC/Repository/unreviewed.fex'
        with self.assertRaisesRegex(ValueError, 'not_reviewed'):
            C.operation_url(r, bad)

    def test_properties_uses_separate_documented_route(self):
        r = request(True); r['operations'][0]['action'] = 'properties'
        self.assertEqual(C.operation_url(r, r['operations'][0]),
            'https://webfocus.example.invalid/ibi_apps/rs?IBIRS_path=%2FWFC%2FRepository%2Fgarden%2Freport.fex&IBIRS_action=properties&IBIRS_service=ibfs')

    def test_connected_capture_requires_host_and_keeps_credentials_out(self):
        r, _ = prepare(self.root, True)
        fake = FakeTransport()
        with self.assertRaisesRegex(ValueError, 'host_capture'):
            C.capture(r, self.root / 'capture', transport=fake)
        out = C.capture(r, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(out['status'], 'acquired_requested_operations')
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')
        self.assertEqual(len(fake.calls), 1)
        C.capture(r, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn(b'fixture-never-retained', b''.join(p.read_bytes() for p in (self.root / 'capture').iterdir() if p.is_file()))
        self.assertFalse(out['capture']['source_execution'])

    def test_http_redirect_and_business_failure_never_succeed(self):
        r = request(True); r['operations'][0]['action'] = 'properties'
        _, _ = prepare(self.root, req=r)
        fake = FakeTransport(raw=b'<ibfsrpc returncode="10001" subreturncode="0"/>', media='application/xml')
        out = C.capture(r, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(out['capture']['operations'][-1]['status'], 'rejected')
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')
        redirect_root = self.root / 'redirect'
        redirect_root.mkdir()
        r, _ = prepare(redirect_root, True)
        fake = FakeTransport(status=302)
        out = C.capture(r, redirect_root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(out['capture']['api_pages'], [])

    def test_xml_entities_unknown_wrappers_and_business_returncodes(self):
        for raw in (b'<!DOCTYPE x [<!ENTITY z SYSTEM "file:///no">]><ibfsrpc/>',
                    '<!DOCTYPE x [<!ENTITY z "x">]><ibfsrpc/>'.encode('utf-16')):
            with self.assertRaisesRegex(ValueError, 'dtd_entity'):
                C.inspect_response(raw, 'get', 'application/xml')
        unknown = C.inspect_response(b'<newwrapper status="ok"/>', 'get', 'application/xml')
        self.assertIsNone(unknown['business_success'])
        ok = C.inspect_response(b'<ibfsrpc returncode="10000" subreturncode="0"/>', 'get', 'application/xml')
        self.assertTrue(ok['business_success'])

    def test_budget_and_resume_changes_are_enforced(self):
        r = request(True)
        r['max_requests_per_invocation'] = 1
        r['operations'].append({'operation_id': 'props-one', 'action': 'properties',
            'resource_path': r['operations'][0]['resource_path'], 'reference': 'Synthetic second read'})
        _, _ = prepare(self.root, req=r)
        fake = FakeTransport()
        out = C.capture(r, self.root / 'capture', authority=fake.authority, transport=fake)
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(len(fake.calls), 1)
        changed = copy.deepcopy(r); changed['state']['parameters'] = {}
        with self.assertRaisesRegex(ValueError, 'resume_request_changed'):
            C.capture(changed, self.root / 'capture', authority=fake.authority, transport=fake)

    def test_error_details_are_redacted(self):
        r, _ = prepare(self.root, True)
        fake = FakeTransport()
        def failure(*args):
            raise RuntimeError('PRIVATE_RESPONSE_WITH_CREDENTIAL')
        out = C.capture(r, self.root / 'capture', authority=fake.authority, transport=failure)
        self.assertEqual(out['status'], 'partial')
        self.assertNotIn('PRIVATE_RESPONSE', C.encoded(out).decode())
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')

    def test_manual_fex_declarations_do_not_require_dma_report(self):
        manifest = supplied(self.root / 'supplied')
        raw = b'GRAPH FILE garden\nSUM QUANTITY BY REGION\nON GRAPH SET STYLE *\nTYPE=REPORT, COLOR=BLUE, $\nENDSTYLE\nEND\n'
        (self.root / 'supplied/report.fex').write_bytes(raw)
        manifest['records'][0]['sha256'] = C.F.raw_sha(raw)
        (self.root / 'supplied/originals.json').write_bytes(C.encoded(manifest))
        out = C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        declaration = out['capture']['source']['files'][0]['inspection']['visual_declarations']
        self.assertEqual(declaration['graph_requests'][0]['native_source'], 'garden')
        self.assertEqual(len(declaration['style_blocks']), 1)
        self.assertFalse(declaration['execution_performed'])
        self.assertIsNone(out['capture']['source']['adapter_report'])
        C.check_capture(out['output'])

    def test_standalone_visual_root_needs_no_fabricated_page(self):
        supplied(self.root / 'supplied')
        inv = C.F.decode((self.root / 'supplied/inventory.json').read_bytes())
        inv['objects'] = [inv['objects'][1]]
        inv['objects'][0]['parent_key'] = None
        inv['objects'][0]['configuration']['artifact_type'] = 'report'
        cross = C.F.decode((self.root / 'supplied/crosswalk.json').read_bytes())
        cross['rows'] = [cross['rows'][1]]
        (self.root / 'supplied/inventory.json').write_bytes(C.encoded(inv))
        (self.root / 'supplied/crosswalk.json').write_bytes(C.encoded(cross))
        r = request(); r['root_key'] = 'visual-one'
        out = C.import_local(r, self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        self.assertEqual(len(out['capture']['source']['inventory']['objects']), 1)
        C.check_capture(out['output'])

    def test_echoed_credentials_and_secret_source_are_not_persisted(self):
        for index, raw in enumerate((b'SYNTHETICSESSION=fixture-never-retained', b'PASSWORD="synthetic-sensitive-value"',
                                    b'<unknown password="synthetic-sensitive-value"/>')):
            root = self.root / ('case-%d' % index); root.mkdir()
            r, _ = prepare(root, True)
            fake = FakeTransport(raw=raw)
            out = C.capture(r, root / 'capture', authority=fake.authority, transport=fake)
            self.assertEqual(out['status'], 'partial')
            self.assertEqual(out['capture']['api_pages'], [])
            self.assertFalse(list((root / 'capture').glob('response-*')))
            self.assertNotIn(b'synthetic-sensitive-value', C.encoded(out))
            C.check_capture(root / 'capture')

    def test_zip_text_member_secret_rejected_and_opaque_marked(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('cm/source.acx', 'PASSWORD="synthetic-sensitive-value"')
        with self.assertRaisesRegex(ValueError, 'credential'):
            C.inspect_zip(data.getvalue())
        opaque = io.BytesIO()
        with zipfile.ZipFile(opaque, 'w') as z:
            z.writestr('cm/blob.bin', b'\x00\xff')
        result = C.inspect_zip(opaque.getvalue())
        self.assertEqual(result['members'][0]['credential_screening'], 'opaque_bytes_not_assessed')

    def test_unknown_xml_version_and_plain_xml_error_remain_unqualified(self):
        info = C.inspect_response(b'<ibfsrpc version="9" returncode="10000" subreturncode="0"/>', 'get', 'application/xml')
        self.assertIsNone(info['business_success'])
        info = C.inspect_response(b'<ibfsrpc returncode="10001" subreturncode="0"/>', 'getContent', 'text/plain')
        self.assertFalse(info['business_success'])

    def test_observed_result_limit_context_is_preserved_and_validated(self):
        _, out = prepare(self.root)
        (self.root / 'supplied/numbers.csv').write_bytes(b'region,quantity\nWest,2\nEast,3\n')
        e = evidence_spec()
        context = {'data_mode': 'preview', 'row_limit': 50, 'row_limit_stage': 'before_aggregation',
                   'aggregation_stage': 'native_report', 'reference': 'Synthetic explicit preview limit observation'}
        e['attachments'][0]['observed_state']['result_context'] = context
        added = C.import_evidence(out['output'], e, self.root / 'supplied')
        self.assertEqual(added['capture']['attachments'][0]['observed_state']['result_context'], context)
        C.check_capture(added['output'])
        invalid = copy.deepcopy(context); invalid['row_limit'] = None
        with self.assertRaisesRegex(ValueError, 'result_limit_stage'):
            C.validate_result_context(invalid)


if __name__ == '__main__':
    unittest.main()
