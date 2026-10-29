"""Neutral original fixtures; standard library only, no live ThoughtSpot calls."""
import copy
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-translator/scripts/thoughtspot_capture.py'
spec = importlib.util.spec_from_file_location('thoughtspot_capture_tested', SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def snapshot():
    native = {'guid': 'lb-one', 'liveboard': {'name': 'Garden quantities',
        'visualizations': [{'id': 'Viz_1', 'viz_guid': 'viz-one', 'answer': {'search_query': '[Quantity]', 'chart': {'type': 'COLUMN'}}},
                           {'id': 'note-one', 'note': {'text': 'Synthetic observation'}}],
        'layout': {'tabs': [{'id': 'tab-one', 'name': 'Overview', 'tiles': [
            {'visualization_id': 'Viz_1', 'x': 0, 'y': 0},
            {'visualization_id': 'note-one', 'x': 1, 'y': 0}]}]}}}
    items = []
    for key, kind, parent, native_id, pointer, config in [
        ('root', 'liveboard', None, 'lb-one', '/liveboard', {}),
        ('tab-one', 'tab', 'root', 'tab-one', '/liveboard/layout/tabs/0', {}),
        ('visual-one', 'visual', 'root', 'Viz_1', '/liveboard/visualizations/0', {}),
        ('note-one', 'note', 'root', 'note-one', '/liveboard/visualizations/1', {}),
        ('placement-one', 'placement', 'tab-one', 'Viz_1', '/liveboard/layout/tabs/0/tiles/0', {'visual_key': 'visual-one'}),
        ('note-placement', 'placement', 'tab-one', 'note-one', '/liveboard/layout/tabs/0/tiles/1', {'content_key': 'note-one'})]:
        items.append({'key': key, 'kind': kind, 'parent_key': parent, 'native_id': native_id, 'definition_id': None,
            'disposition': 'include', 'reference': 'Independent synthetic inventory', 'configuration': config,
            'source_mapping': {'object_kind': 'liveboard', 'object_id': 'lb-one', 'pointer': pointer}})
    return {'schema_version': 'thoughtspot-api-snapshot.v1', 'identity': {
        'source_origin': 'https://thoughtspot.example.invalid', 'org_id': '0', 'product': 'cloud',
        'version': '26.10.0.cl', 'principal_ref': 'fixture-reader', 'chart_generation': 'new',
        'reference': 'Synthetic source identity; not a tenant verification'}, 'root': {'kind': 'liveboard', 'id': 'lb-one'},
        'objects': [{'kind': 'liveboard', 'id': 'lb-one', 'payload': native, 'evidence_ref': 'Synthetic TML JSON'}],
        'inventory': {'reference': 'Independent synthetic expected object list', 'completeness': 'selected_scope_declared',
                      'items': items}, 'gaps': ['synthetic_fixture_only']}


def operation(kind='metadata_search', key='metadata-one'):
    bodies = {
        'metadata_search': {'metadata': [{'identifier': 'lb-one', 'type': 'LIVEBOARD'}], 'record_offset': 0, 'record_size': 10},
        'tml_export': {'metadata': [{'identifier': 'lb-one', 'type': 'LIVEBOARD'}], 'export_associated': False,
                       'export_fqn': True, 'edoc_format': 'JSON', 'export_schema_version': 'v2'},
        'liveboard_data': {'metadata_identifier': 'lb-one', 'visualization_identifiers': ['viz-one'],
                           'data_format': 'COMPACT', 'record_offset': 0, 'record_size': 10},
        'liveboard_render': {'metadata_identifier': 'lb-one', 'visualization_identifiers': ['viz-one'],
                             'tab_identifiers': ['tab-one'], 'file_format': 'PDF'},
        'answer_data': {'metadata_identifier': 'answer-one', 'data_format': 'COMPACT', 'record_offset': 0, 'record_size': 10},
        'answer_render': {'metadata_identifier': 'answer-one', 'type': 'SAVED', 'file_format': 'PDF'}}
    return {'operation_id': key, 'kind': kind, 'body': bodies[kind], 'reference': 'Synthetic explicitly selected operation'}


def request(connected=False):
    value = snapshot()
    return {'schema_version': C.REQUEST, 'capture_id': 'synthetic-thoughtspot', 'identity': value['identity'],
        'root': value['root'], 'authorization_ref': 'Synthetic source-read request', 'credential_ref': 'host-bearer-reference',
        'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None, 'target_surface': 'both',
        'state': {'filters': {}, 'parameters': {}, 'timezone': 'UTC', 'locale': 'en-US', 'principal': 'fixture-reader',
                  'cache': None, 'reference': 'Synthetic requested state'},
        'snapshot_path': 'snapshot.json', 'originals_path': 'originals.json',
        'api_profile': 'rest2-cloud-26.10.v1' if connected else None,
        'operations': [operation()] if connected else []}


def original_record(source, source_pointer, target, kind='supplied_json', member=None):
    return {'source_path': source, 'source_kind': kind, 'source_pointer': source_pointer, 'target_pointer': target,
        'mapping': 'exact_json', 'member_path': member, 'reference': 'Synthetic original-file pointer crosswalk', 'mcp_evidence': None}


def supplied(root, value=None):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    value = value or snapshot()
    native = {'objects': [o['payload'] for o in value['objects']]}
    manifest = {'schema_version': 'thoughtspot-originals.v1', 'reference': 'Synthetic supplied originals', 'records': [
        original_record('native.json', '/objects/%d' % i, '/objects/%d/payload' % i) for i in range(len(value['objects']))] + [
        original_record('inventory.json', '', '/inventory')]}
    for name, data in [('snapshot.json', value), ('originals.json', manifest), ('native.json', native), ('inventory.json', value['inventory'])]:
        (root / name).write_bytes(C.encoded(data))
    return manifest


def prepare(root, req=None, connected=False):
    root = Path(root)
    supplied(root / 'supplied')
    r = req or request(connected)
    return r, C.import_local(r, root / 'supplied', root / 'capture', allow_source_read=True)


def evidence_spec():
    return {'schema_version': 'thoughtspot-supplied-evidence.v1', 'attachments': [{
        'attachment_id': 'numbers-one', 'object_key': 'visual-one', 'format': 'csv', 'source_path': 'numbers.csv', 'member_path': None,
        'origin': 'full', 'result_scope': 'query_result', 'observed_state': {'state': request()['state'],
        'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic observed state'},
        'population': {'key': 'garden', 'description': 'All synthetic garden rows', 'reference': 'Synthetic population'},
        'freshness': {'data_watermark': '2026-01-01', 'observed_at': '2026-01-01T00:00:00Z', 'reference': 'Synthetic watermark'},
        'completeness': {'status': 'complete', 'row_count': 2, 'reference': 'Synthetic complete export'},
        'reference': 'Synthetic independent numerical evidence'}]}


def compact_profile():
    return {'schema_version': 1, 'format': 'json', 'shape': 'compact_matrix', 'rows_pointer': '/data/rows',
        'headers_pointer': '/data/columns', 'header_id_key': 'id', 'column_ids': ['column-item', 'column-quantity'],
        'headers': ['Item', 'Quantity'], 'subtotal_policy': 'preserve', 'columns': [
            {'ordinal': 0, 'name': 'item', 'type': 'string', 'nullable': False, 'null_tokens': []},
            {'ordinal': 1, 'name': 'quantity', 'type': 'number', 'nullable': False, 'null_tokens': [],
             'decimal_separator': '.', 'group_separator': None, 'percent': False}]}


class FakeTransport:
    def __init__(self, raw=b'[]', status=200):
        self.raw, self.status, self.calls, self.grants = raw, status, [], []

    def authority(self, scope, fingerprint):
        self.grants.append((scope, copy.deepcopy(fingerprint)))
        return {'Authorization': 'Bearer fixture-never-retained-token'}

    def __call__(self, method, url, headers, body, maximum, timeout):
        self.calls.append((method, url, C.F.decode(body)))
        assert headers['Authorization'] == 'Bearer fixture-never-retained-token'
        return self.status, {'Content-Type': 'application/json'}, self.raw


def archive(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as out:
        for name, raw in entries:
            out.writestr(name, raw)
    return buffer.getvalue()


class ThoughtspotCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_passive_import_checks_originals_without_source_execution(self):
        _, out = prepare(self.root)
        self.assertEqual(C.check_capture(out['output'])['status'], 'verified_local_bytes')
        self.assertFalse(out['capture']['source_execution'])
        self.assertEqual(out['capture']['operations'], [])
        self.assertIn('source_identity_and_authority_references_not_authenticated', out['capture']['gaps'])

    def test_original_crosswalk_cannot_replace_native_payload_or_inventory(self):
        for name in ('native.json', 'inventory.json'):
            directory = self.root / name.replace('.', '-')
            supplied(directory)
            (directory / name).write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'pointer_missing|payload_mismatch'):
                C.import_local(request(), directory, directory / 'capture', allow_source_read=True)
        value = snapshot(); manifest = supplied(self.root / 'missing')
        manifest['records'].pop()
        with self.assertRaisesRegex(ValueError, 'object_denominator'):
            C.validate_originals(manifest, value)

    def test_tampered_original_and_missing_source_read_grant_rejected(self):
        supplied(self.root / 'supplied')
        with self.assertRaisesRegex(ValueError, 'source_read_grant'):
            C.import_local(request(), self.root / 'supplied', self.root / 'capture')
        _, out = prepare(self.root / 'valid')
        pin = out['capture']['source']['originals'][0]['file']
        (Path(out['output']).parent / pin['path']).write_bytes(b'{}')
        with self.assertRaises(ValueError):
            C.check_capture(out['output'])

    def test_shared_original_file_keeps_two_exact_mappings(self):
        value = snapshot()
        value['objects'].append({'kind': 'table', 'id': 'table-one', 'payload': {'guid': 'table-one', 'table': {'name': 'Garden'}},
                                 'evidence_ref': 'Synthetic table original'})
        supplied(self.root / 'supplied', value)
        out = C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        rows = out['capture']['source']['originals']
        self.assertEqual(rows[0]['file'], rows[1]['file'])
        self.assertEqual(C.check_capture(out['output'])['status'], 'verified_local_bytes')

    def test_native_json_tml_decodes_one_explicit_string_only(self):
        manifest = supplied(self.root / 'supplied')
        manifest['records'][0].update(source_pointer='/0/edoc', mapping='native_json_tml')
        original = [{'info': {'status': {'status_code': 'OK'}}, 'edoc': C.encoded(snapshot()['objects'][0]['payload']).decode()}]
        (self.root / 'supplied' / 'native.json').write_bytes(C.encoded(original))
        (self.root / 'supplied' / 'originals.json').write_bytes(C.encoded(manifest))
        out = C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        C.check_capture(out['output'])
        self.assertEqual(out['capture']['source']['originals'][0]['inspection']['interpretation'], 'native_json_tml_pointer')
        row = manifest['records'][0]
        for invalid in ('{"guid":"one","guid":"two"}', '{"number":NaN}', 'guid: YAML-is-not-JSON',
                        '"recursive encoded string"', '[]'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                C.inspect_original(row, C.encoded([{'edoc': invalid}]), snapshot())

    def test_nested_business_error_is_not_success_and_unknown_bytes_not_sanitized(self):
        op = operation('tml_export')
        with self.assertRaisesRegex(ValueError, 'business_error'):
            C.inspect_response(C.encoded([{'info': {'status': {'status_code': 'ERROR', 'error_message': 'Synthetic denied'}}}]), op)
        with self.assertRaisesRegex(ValueError, 'credential'):
            C.screen_opaque(b'api_key=synthetic-secret-value')
        self.assertEqual(C.screen_opaque(b'\x00\xff\x00'), 'opaque_bytes_not_assessed')

    def test_opaque_yaml_stays_inert_and_member_json_is_pinned(self):
        manifest = supplied(self.root / 'supplied')
        raw = b'!!python/object/apply:os.system ["must never execute"]\n'
        (self.root / 'supplied' / 'opaque.yaml').write_bytes(raw)
        manifest['records'].append({'source_path': 'opaque.yaml', 'source_kind': 'yaml', 'source_pointer': None,
            'target_pointer': None, 'mapping': 'opaque_preserved', 'member_path': None, 'mcp_evidence': None,
            'reference': 'Synthetic opaque original'})
        native = (self.root / 'supplied' / 'native.json').read_bytes()
        (self.root / 'supplied' / 'bundle.zip').write_bytes(archive([('export/native.json', native)]))
        manifest['records'][0].update(source_path='bundle.zip', source_kind='zip', member_path='export/native.json')
        (self.root / 'supplied' / 'originals.json').write_bytes(C.encoded(manifest))
        out = C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        self.assertFalse(out['capture']['source']['originals'][-1]['inspection']['source_code_execution'])
        C.check_capture(out['output'])

    def test_archive_path_symlink_alias_and_credential_payload_rejected(self):
        bad = [archive([('../escape', b'x')]), archive([('A.json', b'{}'), ('a.json', b'{}')]),
               archive([('folder', b'x'), ('folder/file', b'x')]), archive([('secret.txt', b'password=fixture-secret')])]
        info = zipfile.ZipInfo('link'); info.create_system = 3; info.external_attr = (stat.S_IFLNK | 0o777) << 16
        bad.append(archive([(info, b'elsewhere')]))
        for raw in bad:
            with self.subTest(raw_length=len(raw)), self.assertRaises(ValueError):
                C.zip_members(raw)

    def test_exact_numeric_evidence_and_archive_reverify(self):
        _, out = prepare(self.root)
        spec = evidence_spec(); row = spec['attachments'][0]
        row.update(source_path='evidence.zip', member_path='numbers.csv')
        (self.root / 'supplied' / 'evidence.zip').write_bytes(archive([('numbers.csv', b'item,quantity\nseed,2\nplant,3\n')]))
        updated = C.import_evidence(out['output'], spec, self.root / 'supplied')
        self.assertEqual(updated['capture']['attachments'][0]['inspection']['row_count'], 2)
        C.check_capture(updated['output'])
        self.assertEqual(len(C.file_pins(updated['capture'])), len(C.file_pins(out['capture'])) + 2)

    def test_complete_numeric_requires_observed_context_and_exact_row_count(self):
        spec = evidence_spec()['attachments'][0]
        spec['observed_state'] = None
        with self.assertRaisesRegex(ValueError, 'complete_result_evidence'):
            C.validate_attachment(spec, request(), snapshot())
        _, out = prepare(self.root)
        (self.root / 'supplied' / 'numbers.csv').write_bytes(b'item,quantity\nseed,2\n')
        with self.assertRaisesRegex(ValueError, 'result_count'):
            C.import_evidence(out['output'], evidence_spec(), self.root / 'supplied')

    def test_native_result_wrapper_is_not_ten_rows_complete(self):
        raw = C.encoded([{'data': [{'rows': [[i] for i in range(10)]}]}])
        info = C.inspect_attachment(raw, 'json')
        self.assertIsNone(info['row_count'])
        self.assertEqual(info['completeness'], 'not_inferred')
        with self.assertRaisesRegex(ValueError, 'credential'):
            C.inspect_attachment(b'password,value\nfixture-secret,2\n', 'csv')

    def test_compact_matrix_count_and_types_require_explicit_profile(self):
        raw = b'{"data":{"columns":[{"id":"column-item"},{"id":"column-quantity"}],"rows":[["seed",1.000000000000000001],["plant",3]]}}'
        _, out = prepare(self.root)
        spec = evidence_spec(); row = spec['attachments'][0]
        row.update(format='json', source_path='matrix.json', parser_profile=compact_profile())
        (self.root / 'supplied' / 'matrix.json').write_bytes(raw)
        updated = C.import_evidence(out['output'], spec, self.root / 'supplied')
        C.check_capture(updated['output'])
        stored = updated['capture']['attachments'][0]
        self.assertEqual(stored['inspection']['row_count'], 2)
        self.assertEqual(stored['parser_profile'], compact_profile())
        visual = C.module('thoughtspot_visual')
        binding = {'capture_content_hash': updated['capture']['content_hash'],
            'definition_fingerprint': updated['capture']['source']['definition_fingerprint'], 'object_key': 'visual-one',
            'attachment_id': 'numbers-one', 'state_sha256': C.sha(request()['state']), 'attachment_sha256': C.F.raw_sha(raw)}
        normalized = visual.normalize_results(raw, compact_profile(), binding)
        self.assertEqual(normalized['rows'][0]['quantity'], '1.000000000000000001')
        for label, profile in [('unknown', {**compact_profile(), 'shape': 'unknown'}),
                               ('headers', {**compact_profile(), 'column_ids': ['column-quantity', 'column-item']})]:
            with self.subTest(label=label), self.assertRaises(ValueError):
                C.inspect_attachment(raw, 'json', profile)
        broken = compact_profile(); broken['columns'][1]['type'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'unsupported_column_type'):
            C.inspect_attachment(raw, 'json', broken)

    def test_metadata_grant_fingerprint_and_readonly_claim(self):
        req, out = prepare(self.root, connected=True)
        transport = FakeTransport()
        updated = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
        self.assertEqual(updated['status'], 'acquired_requested_operations')
        self.assertFalse(updated['capture']['source_execution'])
        self.assertEqual(transport.grants[0][0], 'metadata')
        expected = C.operation_spec(req, req['operations'][0])
        self.assertEqual(transport.grants[0][1], {'request_sha256': C.sha(C.validate_request(req)),
            'method': 'POST', 'url': expected['url'], 'body_sha256': C.F.raw_sha(C.encoded(expected['body']))})
        self.assertEqual(updated['capture']['source'], out['capture']['source'])
        C.check_capture(updated['output'])

    def test_query_and_render_are_separate_execution_grants(self):
        for kind, scope, raw in [('liveboard_data', 'query', b'[]'), ('liveboard_render', 'render', b'%PDF-1.7\n%%EOF')]:
            req = request(True); req['operations'] = [operation(kind)]
            _, out = prepare(self.root / scope, req=req)
            transport = FakeTransport(raw)
            updated = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
            self.assertEqual(transport.grants[0][0], scope)
            self.assertTrue(updated['capture']['source_execution'])
            self.assertFalse(updated['capture']['arbitrary_source_code_execution'])
            self.assertEqual(updated['capture']['saved_query_execution' if scope == 'query' else 'render_execution'], 'attempted')
            C.check_capture(updated['output'])

    def test_unqualified_profile_and_unsaved_pinned_arbitrary_operations_denied(self):
        req = request(True); req['identity']['version'] = 'other-version'
        with self.assertRaisesRegex(ValueError, 'version_not_qualified'):
            C.validate_request(req)
        for kind in ('tml_import', 'searchdata', 'create', 'login'):
            req = request(True); req['operations'][0]['kind'] = kind
            with self.assertRaisesRegex(ValueError, 'reviewed_operation'):
                C.validate_request(req)
        req = request(True); req['operations'] = [operation('answer_render')]
        req['operations'][0]['body']['type'] = 'PINNED'
        with self.assertRaisesRegex(ValueError, 'pinned_or_unsaved'):
            C.validate_request(req)
        req = request(True); req['operations'][0]['body']['query'] = 'unscoped'
        with self.assertRaises(ValueError):
            C.validate_request(req)

    def test_pagination_duplicate_body_and_png_tab_boundaries(self):
        req = request(True); req['operations'].append({**copy.deepcopy(req['operations'][0]), 'operation_id': 'again'})
        with self.assertRaisesRegex(ValueError, 'duplicate_operation_body'):
            C.validate_request(req)
        for invalid in (0, True, 100001):
            req = request(True); req['operations'] = [operation('liveboard_data')]
            req['operations'][0]['body']['record_size'] = invalid
            with self.assertRaisesRegex(ValueError, 'bounded_pagination'):
                C.validate_request(req)
        req['operations'] = [operation('liveboard_render')]
        req['operations'][0]['body'].update(file_format='PNG', tab_identifiers=[])
        with self.assertRaises(ValueError):
            C.validate_request(req)

    def test_note_and_outside_tab_and_private_view_not_query_targets(self):
        req = request(True); req['operations'] = [operation('liveboard_data')]
        req['operations'][0]['body']['visualization_identifiers'] = ['note-one']
        with self.assertRaisesRegex(ValueError, 'note_or_unselected'):
            C.validate_operation_scope(C.validate_request(req), snapshot())
        req['operations'] = [operation('liveboard_render')]
        req['operations'][0]['body']['tab_identifiers'] = ['unselected-tab']
        with self.assertRaisesRegex(ValueError, 'tab_outside'):
            C.validate_operation_scope(C.validate_request(req), snapshot())
        req['operations'][0]['body']['tab_identifiers'] = ['tab-one']
        req['operations'][0]['body']['personalised_view_identifier'] = 'private-one'
        with self.assertRaisesRegex(ValueError, 'view_selection'):
            C.validate_operation_scope(C.validate_request(req), snapshot())

    def test_rest_visualization_requires_native_guid_not_local_layout_id(self):
        value = snapshot()
        C.validate_snapshot(value)
        for kind in ('liveboard_data', 'liveboard_render'):
            req = request(True); req['operations'] = [operation(kind)]
            C.validate_operation_scope(C.validate_request(req), value)
            req['operations'][0]['body']['visualization_identifiers'] = ['Viz_1']
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'unselected_visualization'):
                C.validate_operation_scope(C.validate_request(req), value)
        without_guid = copy.deepcopy(value)
        del without_guid['objects'][0]['payload']['liveboard']['visualizations'][0]['viz_guid']
        C.validate_snapshot(without_guid)
        req['operations'][0]['body']['visualization_identifiers'] = ['viz-one']
        with self.assertRaisesRegex(ValueError, 'unselected_visualization'):
            C.validate_operation_scope(C.validate_request(req), without_guid)

    def test_saved_answer_requires_selected_typed_answer_mapping(self):
        value = snapshot()
        value['objects'].append({'kind': 'answer', 'id': 'answer-one', 'payload': {'guid': 'answer-one',
            'answer': {'search_query': '[Quantity]', 'chart': {'type': 'COLUMN'}}}, 'evidence_ref': 'Synthetic saved Answer'})
        inline = next(row for row in value['inventory']['items'] if row['key'] == 'visual-one')
        inline.update(kind='answer', native_id='answer-one')
        value['objects'][0]['payload']['liveboard']['visualizations'][0]['viz_guid'] = 'answer-one'
        C.validate_snapshot(value)
        for kind in ('answer_data', 'answer_render'):
            req = request(True); req['operations'] = [operation(kind)]
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'answer_not_selected'):
                C.validate_operation_scope(C.validate_request(req), value)
        value['inventory']['items'].append({'key': 'saved-answer', 'kind': 'answer', 'parent_key': 'root',
            'native_id': 'answer-one', 'definition_id': None, 'disposition': 'include', 'reference': 'Selected saved Answer',
            'configuration': {}, 'source_mapping': {'object_kind': 'answer', 'object_id': 'answer-one', 'pointer': '/answer'}})
        C.validate_snapshot(value)
        for kind in ('answer_data', 'answer_render'):
            req['operations'] = [operation(kind)]
            C.validate_operation_scope(C.validate_request(req), value)

    def test_uncertain_post_blocks_blind_replay_and_retains_no_body(self):
        req, out = prepare(self.root, connected=True)
        transport = FakeTransport(b'sensitive failure must not be retained', 503)
        first = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
        self.assertEqual(first['status'], 'blocked')
        second = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(second['capture']['responses'], [])
        self.assertNotIn('sensitive failure', C.encoded(second['capture']).decode())
        C.check_capture(second['output'])

    def test_redirect_and_credential_echo_never_persist(self):
        for label, raw, status in [('redirect', b'{}', 302), ('echo', b'{"echo":"fixture-never-retained-token"}', 200),
                                  ('secret', b'{"password":"fixture-sensitive"}', 200)]:
            req, out = prepare(self.root / label, connected=True)
            transport = FakeTransport(raw, status)
            result = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['capture']['responses'], [])
            self.assertFalse(list(Path(out['output']).parent.glob('response-*')))
            C.check_capture(result['output'])

    def test_resume_changed_request_and_missing_host_authority_fail(self):
        req, out = prepare(self.root, connected=True)
        with self.assertRaisesRegex(ValueError, 'host_capture'):
            C.capture(req, Path(out['output']).parent)
        changed = copy.deepcopy(req); changed['state']['filters'] = {'region': 'east'}
        fake = FakeTransport()
        with self.assertRaisesRegex(ValueError, 'resume_request_changed'):
            C.capture(changed, Path(out['output']).parent, authority=fake.authority, transport=fake)
        self.assertEqual(fake.calls, [])

    def test_mcp_original_requires_identity_schema_and_provenance(self):
        value = snapshot(); manifest = supplied(self.root / 'supplied')
        row = manifest['records'][0]; row['source_kind'] = 'mcp_json'
        with self.assertRaisesRegex(ValueError, 'mcp_evidence'):
            C.validate_originals(manifest, value)
        row['mcp_evidence'] = {'tool_name': 'fixture_read', 'tool_call_id': 'call-one', 'session_ref': 'retained-session',
            'observed_at': '2026-01-01T00:00:00Z', 'principal_ref': 'fixture-reader', 'org_id': '0',
            'reference': 'Synthetic retained call', 'capabilities': ['metadata'], 'server_version': 'fixture-v1',
            'tool_schema_sha256': 'a' * 64, 'schema_reference': 'Retained discovery schema',
            'provenance_reference': 'Original retained message chain'}
        C.validate_originals(manifest, value)
        row['mcp_evidence']['org_id'] = 'other-org'
        with self.assertRaisesRegex(ValueError, 'mcp_identity'):
            C.validate_originals(manifest, value)

    def test_symlink_origin_and_mutated_operation_rejected(self):
        supplied(self.root / 'supplied')
        original = self.root / 'supplied' / 'native.json'
        original.rename(original.with_suffix('.original'))
        original.symlink_to(original.with_suffix('.original'))
        with self.assertRaises(ValueError):
            C.import_local(request(), self.root / 'supplied', self.root / 'capture', allow_source_read=True)
        for url in ('http://example.invalid', 'https://example.invalid/path', 'https://user@example.invalid', 'https://example.invalid:443'):
            req = request(); req['identity']['source_origin'] = url
            with self.assertRaises(ValueError):
                C.validate_request(req)
        req = request(True); op = copy.deepcopy(req['operations'][0]); op['body']['record_size'] = 20
        with self.assertRaisesRegex(ValueError, 'operation_not_selected'):
            C.operation_spec(req, op)

    def test_journal_history_cannot_be_deleted_or_rewritten(self):
        req, out = prepare(self.root, connected=True)
        fake = FakeTransport()
        latest = C.capture(req, Path(out['output']).parent, authority=fake.authority, transport=fake)
        first = Path(out['output']); first.unlink()
        with self.assertRaisesRegex(ValueError, 'journal_chain'):
            C.load_latest(Path(latest['output']).parent)

    def test_resealed_next_journal_cannot_reset_attempts_or_source(self):
        changes = {
            'attempts': lambda v: v.update(operations=[], responses=[], request_count=0, network_bytes=0,
                source_execution=False, saved_query_execution='not_requested', render_execution='not_requested', status='partial'),
            'created': lambda v: v.update(created_at_epoch=v['created_at_epoch'] + 1),
            'source': lambda v: v['source']['snapshot']['gaps'].append('changed-source'),
            'request': lambda v: v['request']['state']['filters'].update(region='different')}
        for label, change in changes.items():
            req, out = prepare(self.root / label, connected=True)
            transport = FakeTransport(b'{}', 503)
            result = C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
            root = Path(out['output']).parent
            value, _ = C._load(root)
            change(value)
            if label == 'source':
                value['source']['definition_fingerprint'] = C.sha(value['source']['snapshot'])
            if label == 'request':
                value['request_sha256'] = C.sha(value['request'])
                value['operations'] = []; value['request_count'] = value['network_bytes'] = 0
            C.advance(root, value)
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'immutable_capture_changed|counter_rollback|attempts_rewritten'):
                C.load_latest(root)
            with self.assertRaises(ValueError):
                C.capture(req, root, authority=transport.authority, transport=transport)
            self.assertEqual(len(transport.calls), 1)

    def test_terminal_attempt_and_retained_attachments_are_append_only(self):
        req, out = prepare(self.root, connected=True)
        transport = FakeTransport(b'{}', 503)
        C.capture(req, Path(out['output']).parent, authority=transport.authority, transport=transport)
        value, _ = C.load_latest(Path(out['output']).parent)
        altered = copy.deepcopy(value)
        altered['operations'][0]['status'] = 'rejected'
        altered['operations'][0]['http_status'] = 400
        with self.assertRaisesRegex(ValueError, 'terminal_attempt_rewritten'):
            C.validate_transition(value, altered)
        altered = copy.deepcopy(value); altered['retry_not_before_epoch'] = -1
        with self.assertRaisesRegex(ValueError, 'counter_rollback'):
            C.validate_transition(value, altered)
        previous = copy.deepcopy(value); previous['attachments'] = [{'attachment_id': 'fixed'}]
        with self.assertRaisesRegex(ValueError, 'evidence_rewritten'):
            C.validate_transition(previous, value)


if __name__ == '__main__':
    unittest.main()
