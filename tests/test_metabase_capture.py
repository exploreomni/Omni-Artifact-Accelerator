"""Original synthetic Metabase capture tests; no vendor runtime or network."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-translator/scripts/metabase_capture.py'
spec = importlib.util.spec_from_file_location('metabase_capture_tested', SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def snapshot():
    return {'schema_version': C.SNAPSHOT_SCHEMA,
        'identity': {'source_origin': 'https://metabase.example.invalid', 'version': 'v-synthetic', 'principal_ref': 'fixture-reader'},
        'dashboard': {'id': 1, 'name': 'Synthetic garden inventory', 'tabs': [{'id': 2, 'name': 'Main'}],
            'parameters': [{'id': 'region', 'type': 'string/=', 'name': 'Region'}],
            'dashcards': [{'id': 100, 'card_id': 10, 'dashboard_tab_id': 2, 'row': 0, 'col': 0,
                'size_x': 8, 'size_y': 6, 'parameter_mappings': [{'parameter_id': 'region', 'card_id': 10,
                    'target': ['dimension', ['field', 30, None]]}], 'visualization_settings': {}},
                {'id': 101, 'card_id': 10, 'dashboard_tab_id': 2, 'row': 6, 'col': 0,
                 'series': [{'id': 11}], 'parameter_mappings': [], 'visualization_settings': {}}]},
        'cards': [{'id': 10, 'name': 'Garden totals', 'updated_at': '2026-01-01T00:00:00Z', 'display': 'bar',
            'dataset_query': {'type': 'query', 'database': 4, 'query': {'source-table': 'card__11'}},
            'visualization_settings': {'graph.dimensions': ['region']}, 'parameters': []},
            {'id': 11, 'name': 'Garden rows', 'display': 'table',
             'dataset_query': {'type': 'native', 'database': 4, 'native': {'query': 'SELECT region, quantity FROM garden'}},
             'visualization_settings': {}, 'parameters': []}],
        'metadata': [{'kind': 'table', 'id': 20, 'payload': {'id': 20, 'name': 'garden', 'db_id': 4}}],
        'coverage': {'dashboard': 'complete', 'cards': 'complete', 'metadata': 'complete',
                     'reference': 'Synthetic selected scope listing; not tenant evidence'}, 'gaps': ['synthetic_only']}


def request(query=False):
    s = snapshot()
    return {'schema_version': C.REQUEST_SCHEMA, 'capture_id': 'synthetic-metabase',
        **s['identity'], 'dashboard_id': 1, 'authorization_ref': 'synthetic source read request',
        'credential_ref': 'host-synthetic-reference', 'evidence_mode': 'synthetic_fixture',
        'api_contract': {'reference': 'synthetic fixed API contract', 'version': 'v-synthetic', 'auth_header': 'x-api-key'},
        'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {'region': 'West'}, 'parameters': [], 'timezone': 'UTC', 'locale': 'en-US',
                  'principal': 'fixture-reader', 'reference': 'synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json',
        'card_ids': [10, 11], 'metadata': [{'kind': 'table', 'id': 20}],
        'queries': [{'query_id': 'q10', 'card_id': 10, 'body': {'parameters': [], 'ignore_cache': True},
                     'definition_sha256': C.sha(s['cards'][0]), 'read_only_reference': 'Synthetic restricted DB role evidence'}] if query else []}


def supplied(root, source=None):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = copy.deepcopy(source or snapshot())
    records = []
    objects = [('/dashboard', source['dashboard'])] + [('/cards/%d' % i, c) for i, c in enumerate(source['cards'])] + [
        ('/metadata/%d/payload' % i, m['payload']) for i, m in enumerate(source['metadata'])]
    for i, (target, payload) in enumerate(objects):
        filename = 'original-%d.json' % i
        (root / filename).write_bytes(C.encoded(payload))
        records.append({'source_path': filename, 'source_kind': 'rest_response', 'source_pointer': '',
            'target_pointer': target, 'mapping': 'exact_json', 'reference': 'Original synthetic REST-shaped bytes',
            'tool_name': None, 'tool_call_id': None})
    manifest = {'schema_version': 'metabase-originals.v1', 'records': records}
    (root / 'snapshot.json').write_bytes(C.encoded(source))
    (root / 'originals.json').write_bytes(C.encoded(manifest))
    return manifest


def prepare(root, query=False):
    root = Path(root).resolve()
    supplied(root / 'supplied')
    req = request(query)
    result = C.import_local(req, root / 'supplied', root / 'capture', allow_source_read=True)
    return req, result


def evidence_spec(format='csv', complete=True):
    return {'schema_version': 'metabase-supplied-evidence.v1', 'attachments': [{
        'attachment_id': 'evidence-one', 'object_key': 'dashcard:100', 'card_id': 10, 'dashcard_id': 100, 'tab_id': 2,
        'format': format, 'source_path': 'result.' + format, 'origin': 'full', 'result_scope': 'query_result',
        'observed_state': {'state': request()['state'], 'observed_at': '2026-01-01T00:00:00Z',
            'reference': 'Synthetic explicit observation', 'placement_reference': 'Synthetic region mapping evidence'},
        'population': {'key': 'garden-rows', 'description': 'All synthetic rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic freshness'},
        'completeness': {'status': 'complete' if complete else 'unknown', 'reference': 'Synthetic full export' if complete else None,
                         'row_count': 2}, 'reference': 'Original synthetic numerical evidence'}]}


class FakeTransport:
    def __init__(self, *, query_error=False, sensitive=False, redirect=False, changed=False):
        self.calls, self.grants = [], []
        self.query_error, self.sensitive, self.redirect, self.changed = query_error, sensitive, redirect, changed

    def authority(self, operation, fingerprint):
        self.grants.append((operation, copy.deepcopy(fingerprint)))
        return 'synthetic-host-credential'

    def __call__(self, method, url, headers, body, maximum, timeout):
        self.calls.append((method, url, body))
        assert headers['x-api-key'] == 'synthetic-host-credential'
        s = snapshot()
        if self.redirect:
            return 302, {'Location': 'https://other.example.invalid'}, b''
        if method == 'POST':
            if self.query_error:
                raise TimeoutError('uncertain fixture submission')
            return 200, {}, C.encoded({'status': 'completed', 'data': {'rows': [['West', 2], ['East', 3]], 'cols': []}})
        path = url.split('/api/')[1]
        value = {'dashboard/1': s['dashboard'], 'card/10': s['cards'][0], 'card/11': s['cards'][1], 'table/20': s['metadata'][0]['payload']}[path]
        if self.changed and path == 'card/10':
            value['name'] = 'Changed after reviewed definition'
        if self.sensitive and path == 'table/20':
            value['details'] = {'password': 'synthetic-secret-never-retain'}
        return 200, {}, C.encoded(value)


class MetabaseCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def test_supplied_originals_preserve_all_objects_and_tamper_rejected(self):
        req, out = prepare(self.root)
        cap = out['capture']
        self.assertEqual(cap['source']['snapshot'], snapshot())
        self.assertEqual(len(cap['source']['originals']), 4)
        self.assertFalse(cap['target_write_authority'])
        self.assertEqual(cap['saved_query_execution'], 'not_requested')
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')
        self.assertEqual(C.load_latest(self.root / 'capture', req)[0], cap)
        for pin in C.file_pins(cap):
            self.assertEqual(stat.S_IMODE((self.root / 'capture' / pin['path']).stat().st_mode), 0o600)
        (self.root / 'capture' / cap['source']['originals'][0]['file']['path']).write_text('{}')
        with self.assertRaises(ValueError):
            C.check_capture(out['output'])

    def test_conflicts_missing_dependencies_and_malformed_collections(self):
        for mutate in (
            lambda s: s['dashboard']['dashcards'][0].update(card={'id': 10, 'name': 'Conflicting revision'}),
            lambda s: s['cards'].pop(),
            lambda s: s['dashboard']['parameters'].append(copy.deepcopy(s['dashboard']['parameters'][0])),
            lambda s: s['dashboard']['dashcards'][1]['series'].append({'id': 11}),
            lambda s: s['dashboard']['dashcards'][0].update(parameter_mappings={}),
            lambda s: s['dashboard']['dashcards'][0].update(visualization_settings=[]),
            lambda s: s['cards'][0].update(parameters=[{}]),
            lambda s: s['dashboard']['dashcards'][0].update(dashboard_tab_id=999),
            lambda s: s['cards'].append({'id': 999, 'dataset_query': {}}),
        ):
            value = snapshot(); mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                C.validate_snapshot(value, C.validate_request(request()))

    def test_native_template_and_modern_saved_question_dependencies_are_scoped(self):
        for query in [
            {'type': 'native', 'native': {'query': 'SELECT * FROM {{#11-rows}}',
                'template-tags': {'#11-rows': {'type': 'card', 'card-id': 11}}}},
            {'database': 4, 'stages': [{'source-card': 11}]},
        ]:
            s = snapshot(); s['cards'][0]['dataset_query'] = query
            s['dashboard']['dashcards'][1]['series'] = []
            self.assertEqual(C.card_references({}, s['cards']), {11})
            C.validate_snapshot(s, C.validate_request(request()))
            s['cards'].pop()
            with self.assertRaisesRegex(ValueError, 'missing_card_dependencies'): C.validate_snapshot(s)

    def test_positive_image_document_evidence_remains_nonrendered(self):
        def chunk(kind, body):
            return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
            chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff')) + chunk(b'IEND', b'')
        self.assertEqual(C.inspect_attachment(png, 'png')['width'], 1)
        self.assertEqual(C.inspect_attachment(b'%PDF-1.4\nsynthetic\n%%EOF\n', 'pdf')['validation'], 'signature_only_not_rendered')

    def test_mcp_crosswalk_and_inert_serialization_are_not_rest_proof(self):
        s = snapshot()
        for k in ('dashboard', 'cards', 'metadata'): s['coverage'][k] = 'partial'
        source = self.root / 'supplied'; manifest = supplied(source, s)
        row = manifest['records'][0]
        row.update(source_kind='mcp_tool_response', source_pointer='/content', mapping='explicit_normalized',
                   tool_name='synthetic_dashboard_read', tool_call_id='synthetic-call-1')
        raw = C.encoded({'content': [{'type': 'text', 'text': 'Opaque original tool envelope'}], 'isError': False})
        (source / row['source_path']).write_bytes(raw)
        (source / 'opaque.yaml').write_text('!!python/object/apply:os.system [DO_NOT_EXECUTE]\n')
        manifest['records'].append({'source_path': 'opaque.yaml', 'source_kind': 'serialization_yaml',
            'source_pointer': None, 'target_pointer': None, 'mapping': 'inert_unsupported',
            'reference': 'Synthetic opaque serialization', 'tool_name': None, 'tool_call_id': None})
        (source / 'originals.json').write_bytes(C.encoded(manifest))
        out = C.import_local(request(), source, self.root / 'capture', allow_source_read=True)
        self.assertIn('mcp_normalization_supplied_not_rest_observation', out['capture']['gaps'])
        self.assertIn('serialization_yaml_inert_unsupported', out['capture']['gaps'])
        self.assertEqual(C.check(out['output'])['status'], 'verified_local_bytes')
        s['coverage']['cards'] = 'complete'
        with self.assertRaisesRegex(ValueError, 'partial_coverage'):
            C.validate_originals(manifest, s)

    def test_safe_paths_credentials_and_invalid_bytes_reject_before_retention(self):
        source = self.root / 'supplied'; supplied(source)
        req = request(); req['snapshot_path'] = '../escape.json'
        with self.assertRaises(ValueError): C.validate_request(req)
        (source / 'snapshot.json').unlink()
        (source / 'snapshot.json').symlink_to(source / 'original-0.json')
        with self.assertRaises(ValueError): C.import_local(request(), source, self.root / 'capture', allow_source_read=True)
        (source / 'snapshot.json').unlink(); supplied(source)
        raw = json.loads((source / 'original-3.json').read_text()); raw['details'] = {'password': 'never-store'}
        (source / 'original-3.json').write_bytes(C.encoded(raw))
        with self.assertRaisesRegex(ValueError, 'credential'):
            C.import_local(request(), source, self.root / 'capture2', allow_source_read=True)
        self.assertEqual(list((self.root / 'capture2').iterdir()), [])
        for raw, fmt in [(b'not-pdf', 'pdf'), (b'bad-png', 'png'), (b'a,b\n1\n', 'csv'), (b'{"x":1,"x":2}', 'json')]:
            with self.subTest(fmt=fmt), self.assertRaises(ValueError): C.inspect_attachment(raw, fmt)

    def test_observed_attachment_bound_to_bytes_state_and_population(self):
        _, out = prepare(self.root)
        source = self.root / 'evidence'; source.mkdir()
        (source / 'result.csv').write_text('region,quantity\nWest,2\nEast,3\n')
        result = C.import_evidence(out['output'], evidence_spec(), source)
        a = result['capture']['attachments'][0]
        self.assertEqual(a['inspection']['row_count'], 2)
        self.assertIn('placement_reference', a['observed_state'])
        self.assertEqual(C.check_capture(result['output'])['status'], 'verified_local_bytes')
        with self.assertRaisesRegex(ValueError, 'current_snapshot'):
            C.import_evidence(out['output'], evidence_spec(), source)
        forged = copy.deepcopy(result['capture']); forged['attachments'][0]['inspection']['row_count'] = 1
        forged['content_hash'] = C.sha({k:v for k,v in forged.items() if k != 'content_hash'})
        with self.assertRaises(ValueError): C.verify_capture_files(forged, self.root / 'capture')

    def test_complete_result_cannot_override_explicit_truncation_or_missing_observation(self):
        _, out = prepare(self.root)
        source = self.root / 'evidence'; source.mkdir()
        (source / 'result.json').write_bytes(C.encoded({'status': 'completed', 'data': {'rows': [[1], [2]], 'rows_truncated': True}}))
        with self.assertRaisesRegex(ValueError, 'explicitly_incomplete'):
            C.import_evidence(out['output'], evidence_spec('json'), source)
        spec = evidence_spec('json'); spec['attachments'][0]['observed_state'] = None
        with self.assertRaisesRegex(ValueError, 'complete_evidence'):
            C.import_evidence(out['output'], spec, source)
        spec = evidence_spec('json'); spec['attachments'][0]['card_id'] = True
        with self.assertRaises(ValueError): C.import_evidence(out['output'], spec, source)

    def test_connected_fresh_capture_scope_query_hash_and_unknown_observation(self):
        req, transport = request(True), FakeTransport()
        out = C.capture(req, self.root / 'capture', authority=transport.authority, transport=transport, now=lambda:100)
        self.assertEqual(out['status'], 'acquired_requested_operations')
        self.assertEqual(len(transport.calls), 5)
        self.assertEqual(transport.calls[-1][2], C.encoded(req['queries'][0]['body']))
        self.assertEqual(transport.grants[-1][0], 'query')
        self.assertEqual(transport.grants[-1][1]['body_sha256'], C.sha(req['queries'][0]['body']))
        a = out['capture']['attachments'][0]
        self.assertFalse(out['capture']['arbitrary_source_code_execution'])
        self.assertEqual(out['capture']['saved_query_execution'], 'attempted')
        self.assertIsNone(a['observed_state']); self.assertEqual(a['completeness']['status'], 'unknown')
        self.assertEqual(C.check_capture(self.root / 'capture')['status'], 'verified_local_bytes')
        self.assertFalse(any('/api/database' in c[1] for c in transport.calls))
        for mutate in (lambda c: c['source']['originals'].pop(),
                       lambda c: c['source']['originals'][0].update(target_pointer='/cards/0')):
            forged = copy.deepcopy(out['capture']); mutate(forged)
            forged['content_hash'] = C.sha({k:v for k,v in forged.items() if k != 'content_hash'})
            with self.assertRaises(ValueError): C.validate_envelope(forged)

    def test_query_requires_host_grant_reviewed_definition_and_fixed_read_only_body(self):
        with self.assertRaisesRegex(ValueError, 'host_authority'):
            C.capture(request(True), self.root / 'unconfigured')
        for change in ('definition_sha256', 'read_only_reference'):
            req = request(True); del req['queries'][0][change]
            with self.assertRaises(ValueError): C.validate_request(req)
        req = request(True); req['queries'][0]['body']['query'] = 'DELETE FROM garden'
        with self.assertRaisesRegex(ValueError, 'saved_query_body'): C.validate_request(req)
        req = request(True); req['queries'][0]['body']['ignore_cache'] = 'true'
        with self.assertRaises(ValueError): C.validate_request(req)
        transport = FakeTransport(changed=True)
        out = C.capture(request(True), self.root / 'changed', authority=transport.authority, transport=transport, now=lambda:100)
        self.assertEqual(out['status'], 'blocked'); self.assertFalse(any(c[0] == 'POST' for c in transport.calls))
        self.assertEqual(C.check(out['output'])['status'], 'verified_local_bytes')

    def test_uncertain_post_is_not_retried_and_resume_binding_is_fixed(self):
        transport = FakeTransport(query_error=True); req = request(True)
        out = C.capture(req, self.root / 'capture', authority=transport.authority, transport=transport, now=lambda:100)
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(out['capture']['operations'][-1]['status'], 'uncertain')
        out = C.capture(req, self.root / 'capture', authority=transport.authority, transport=transport, resume=True, now=lambda:101)
        self.assertEqual(sum(c[0] == 'POST' for c in transport.calls), 1)
        self.assertIn('saved_question_submission_uncertain_no_blind_retry', out['capture']['gaps'])
        changed = copy.deepcopy(req); changed['state']['filters']['region'] = 'East'
        with self.assertRaisesRegex(ValueError, 'resume_request_changed'):
            C.capture(changed, self.root / 'capture', authority=transport.authority, transport=transport, resume=True)

    def test_resume_budget_and_journal_chain(self):
        transport = FakeTransport(); req = request(); req['max_requests_per_invocation'] = 1
        for i in range(4):
            out = C.capture(req, self.root / 'capture', authority=transport.authority, transport=transport, resume=i>0, now=lambda:100)
            self.assertEqual(len(transport.calls), i + 1)
            C.check_capture(self.root / 'capture')
        self.assertEqual(out['status'], 'acquired_requested_operations')
        path = self.root / 'capture' / 'capture-000002.json'
        value = C.F.decode(path.read_bytes()); value['previous_capture']['sha256'] = 'a'*64
        value['content_hash'] = C.sha({k:v for k,v in value.items() if k != 'content_hash'}); path.write_bytes(C.encoded(value))
        with self.assertRaisesRegex(ValueError, 'journal_chain'): C.load_latest(self.root / 'capture')

    def test_redirect_and_sensitive_metadata_never_retained(self):
        for name, transport in [('redirect', FakeTransport(redirect=True)), ('sensitive', FakeTransport(sensitive=True))]:
            out = C.capture(request(), self.root / name, authority=transport.authority, transport=transport, now=lambda:100)
            self.assertNotEqual(out['status'], 'acquired_requested_operations')
            C.check(out['output'])
            for path in (self.root / name).iterdir():
                if path.is_file(): self.assertNotIn(b'synthetic-secret-never-retain', path.read_bytes())
            if name == 'sensitive':
                self.assertIn('response_sha256', out['capture']['operations'][-1])
        with self.assertRaisesRegex(ValueError, 'redirect'):
            C.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid')

    def test_cli_no_overwrite_and_no_source_payload_output(self):
        source = self.root / 'supplied'; supplied(source)
        req = self.root / 'request.json'; req.write_bytes(C.encoded(request()))
        args = [sys.executable, '-I', '-S', '-B', str(SCRIPT), 'import-local', '--request', str(req),
                '--source-root', str(source), '--directory', str(self.root / 'capture'), '--allow-source-read']
        first = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(set(json.loads(first.stdout)), {'status', 'native_validation'})
        self.assertNotIn('Garden', first.stdout)
        second = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.assertEqual(second.returncode, 1)
        self.assertNotIn('Garden', second.stderr)


if __name__ == '__main__':
    unittest.main()
