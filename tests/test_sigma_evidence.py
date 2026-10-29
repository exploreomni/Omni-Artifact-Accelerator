"""Original neutral Sigma byte/state fixtures; no network or upstream imports."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'skills/omni-artifact-translator/scripts/sigma_visual.py'
spec = importlib.util.spec_from_file_location('sigma_evidence_under_test', PATH)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def seal(value):
    value['content_hash'] = S.sha({k: v for k, v in value.items() if k != 'content_hash'})
    return value


def write(root, name, raw):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'path': name, 'sha256': S.sha(raw), 'bytes': len(raw)}


def png():
    def chunk(kind, raw):
        return struct.pack('>I', len(raw)) + kind + raw + struct.pack('>I', zlib.crc32(kind + raw) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(b'\x00\x22\x33\x44')) + chunk(b'IEND', b'')


def legacy_fixture(root):
    req = {'schema_version': 'sigma-visual-capture-request.v1', 'capture_id': 'capture-1',
           'workbook_id': 'workbook-1', 'page_id': 'page-1', 'element_id': 'element-1', 'data_model_id': 'model-1',
           'expected_organization_id': 'organization-1', 'expected_user_id': 'user-1',
           'principal_ref': 'principal-ref://synthetic/viewer',
           'authorization_ref': 'human-authorization-ref://synthetic/source', 'api_base_url': 'https://example.invalid',
           'approved_api_host': 'example.invalid', 'source_freeze': {'strategy': 'version_tag',
           'workbook_tag_name': 'reviewed', 'data_model_document_version': 3}, 'parameters': {'region': 'Zone 1'},
           'timezone': 'UTC', 'row_limit': 10, 'evidence_mode': 'synthetic_fixture'}
    baseline = {'identity': {'organizationId': 'organization-1', 'userId': 'user-1'},
                'workbook': {'workbookId': 'workbook-1', 'version': 3},
                'tags': [{'tagName': 'reviewed', 'sourceVersion': 3}], 'tag_source_version': '3',
                'data_model_specification': {'dataModelId': 'model-1', 'documentVersion': 3, 'pages': []}}
    revision = {'workbook': baseline['workbook'], 'tags': baseline['tags']}
    snapshot = {'workbookId': 'workbook-1', 'tag': 'reviewed', 'pages': [{'pageId': 'page-1',
                'elements': [{'elementId': 'element-1', 'type': 'chart', 'title': 'Synthetic throughput'}]}],
                'revisionEvidence': revision, 'revisionEvidenceSha256': S.sha(revision),
                'coherence': 'unchanged_before_after_not_atomic'}
    value = {'schema_version': S.LEGACY, 'capture_id': req['capture_id'], 'request': req,
             'original_request': copy.deepcopy(req), 'request_sha256': S.sha(req), 'original_request_sha256': S.sha(req),
             'status': 'complete', 'evidence_mode': 'synthetic_fixture', 'journal_revision': 1,
             'previous_content_hash': None, 'created_at': '2026-01-01T12:00:00+00:00', 'gaps': [],
             'target_write_authority': False, 'native_validation': 'not_performed', 'business_acceptance': 'not_assessed',
             'source': {'tagged_snapshot': snapshot, 'tagged_snapshot_sha256': S.sha(snapshot),
                        'baseline': baseline, 'baseline_sha256': S.sha(baseline), 'coherence_sha256': S.sha(baseline),
                        'coherence': snapshot['coherence'], 'final_observation': copy.deepcopy(baseline),
                        'final_observation_sha256': S.sha(baseline)}, 'jobs': [], 'attachments': []}
    for kind, raw in [('png', png()), ('json', b'[{"zone":"Zone 1","count":12}]')]:
        body = {'tag': 'reviewed', 'elementId': 'element-1', 'parameters': req['parameters'], 'format': {'type': kind}}
        if kind == 'json':
            body['rowLimit'] = 10
        qid = 'query-' + kind
        value['jobs'].append({'kind': kind, 'request_body': body, 'request_sha256': S.sha(body),
                              'status': 'downloaded', 'query_id': qid, 'creation_response': {'queryId': qid}})
        a = {**write(root, 'element.' + kind, raw), 'format': kind,
             'media_type': 'image/png' if kind == 'png' else 'application/json', 'query_id': qid,
             'request_sha256': S.sha(req), 'source_snapshot_sha256': S.sha(snapshot),
             **{k: req[k] for k in ('capture_id', 'workbook_id', 'page_id', 'element_id')}}
        a.update({'actual_dimensions': {'width': 1, 'height': 1}, 'requested_dimensions': None} if kind == 'png' else
                 {'observed_rows': 1, 'requested_row_limit': 10, 'row_completeness': 'not_established', 'result_shape': 'array'})
        value['attachments'].append(a)
    return seal(value)


def profile(fmt='json'):
    value = {'schema_version': 1, 'format': fmt, 'subtotal_policy': 'preserve', 'headers': ['zone', 'count'],
             'columns': [{'ordinal': 0, 'name': 'zone', 'type': 'string', 'nullable': False, 'null_tokens': []},
                         {'ordinal': 1, 'name': 'count', 'type': 'number', 'nullable': True, 'null_tokens': [''],
                          'decimal_separator': '.', 'group_separator': None, 'percent': False}]}
    value.update({'rows_pointer': ''} if fmt == 'json' else {'encoding': 'utf-8'})
    return value


def v2_fixture(root, page=True):
    value = legacy_fixture(root)
    req = value['request']
    req.update(schema_version='sigma-visual-capture-request.v2', target_kind='page' if page else 'element',
               data_model_id=None)
    req['source_freeze']['data_model_document_version'] = None
    if page:
        req['element_id'] = None
        value['jobs'] = value['jobs'][:1]
        value['attachments'] = value['attachments'][:1]
    value['original_request'] = copy.deepcopy(req)
    value['request_sha256'] = value['original_request_sha256'] = S.sha(req)
    baseline = value['source']['baseline']
    baseline['data_model_specification'] = None
    value['source']['baseline_sha256'] = value['source']['coherence_sha256'] = S.sha(baseline)
    value['source']['final_observation'] = copy.deepcopy(baseline)
    value['source']['final_observation_sha256'] = S.sha(baseline)
    snapshot = value['source']['tagged_snapshot']
    snapshot['elements'] = copy.deepcopy(snapshot['pages'][0]['elements'])
    value['source']['tagged_snapshot_sha256'] = S.sha(snapshot)
    for job in value['jobs']:
        if page:
            job['request_body'].pop('elementId')
            job['request_body']['pageId'] = req['page_id']
        job['request_sha256'] = S.sha(job['request_body'])
    for attachment in value['attachments']:
        attachment.update(request_sha256=S.sha(req), element_id=req['element_id'], source_snapshot_sha256=S.sha(snapshot))
    return seal(value)


def bundle_fixture(root):
    identity = {'source_origin': 'https://example.invalid', 'organization_id': 'organization-1',
                'principal_ref': 'principal-ref://synthetic/viewer', 'workbook_id': 'workbook-1'}
    selection = {'mode': 'tagged', 'version': '3', 'tag': 'reviewed', 'view_id': None, 'reference': 'evidence-ref://selection'}
    state = {'filters': {}, 'parameters': {'region': 'Zone 1'}, 'timezone': 'UTC', 'locale': 'en-US',
             'cache': {'mode': 'observed_existing'}, 'principal': identity['principal_ref']}
    definition = {'elementId': 'element-1', 'type': 'chart', 'columns': ['zone', 'count'], 'unknown_facet': {'retained': True}}
    items = []
    for key, kind, native, parent in [('workbook', 'workbook', 'workbook-1', None),
                                      ('page', 'page', 'page-1', 'workbook'), ('visual', 'visual', 'element-1', 'page')]:
        items.append({'key': key, 'kind': kind, 'native_id': native, 'page_id': 'page-1' if key != 'workbook' else None,
                      'parent_key': parent, 'disposition': 'include', 'reference': 'evidence-ref://inventory', 'configuration': {}})
    items[-1]['configuration']['definition_sha256'] = S.sha(definition)
    items[-1]['source_mapping'] = {'artifact_id': 'definition', 'pointer': '/elements/0'}
    value = {'schema_version': S.SCHEMA, 'identity': identity, 'selection': selection, 'state': state,
             'inventory': {'reference': 'independent-ref://inventory', 'completeness': 'selected_scope_declared', 'items': items},
             'status': 'complete', 'target_write_authority': False, 'native_validation': 'not_performed',
             'business_acceptance': 'not_assessed', 'gaps': [], 'artifacts': []}
    raw = b'[{"zone":"Zone 1","count":12345678901234567890.1234567890123456789}]'
    for aid, kind, fmt, file, keys in [
        ('definition', 'rest_snapshot', 'json', write(root, 'originals/definition.json', S.encoded({'elements': [definition]})), ['workbook', 'page', 'visual']),
        ('result', 'results', 'json', write(root, 'originals/result.json', raw), ['visual'])]:
        a = {'artifact_id': aid, 'kind': kind, 'source_channel': 'rest_v2', 'format': fmt, 'file': file,
             'object_keys': keys, 'selection': copy.deepcopy(selection), 'state_sha256': S.sha(state),
             'principal_ref': identity['principal_ref'], 'captured_at': '2026-01-01T12:00:00+00:00',
             'reference': 'evidence-ref://' + aid}
        if kind == 'results':
            a.update(parser_profile=profile(), completeness={'status': 'complete', 'flags': [], 'row_count': 1,
                     'reference': 'evidence-ref://complete'}, population={'key': 'population-1', 'reference': 'evidence-ref://population'},
                     freshness={'observed_at': a['captured_at'], 'data_watermark': 'watermark-1', 'reference': 'evidence-ref://freshness'},
                     observed_state={'state': copy.deepcopy(state), 'selection': copy.deepcopy(selection),
                     'definition_sha256': S.sha(definition), 'execution_status': 'completed', 'result_scope': 'full_data',
                     'row_limit': None, 'reference': 'evidence-ref://result-state'})
        value['artifacts'].append(a)
    return seal(value)


def comparison_fixture(root):
    value = bundle_fixture(root)
    a = value['artifacts'][1]
    binding = S._binding(value, a)
    normalized = S.normalize_results((root / a['file']['path']).read_bytes(), a['parser_profile'], binding)
    asset = {'kind': 'visual', 'source_id': 'element-1', 'source_identity': {'object_key': 'visual',
             'workbook_id': value['identity']['workbook_id'], 'definition_fingerprint': S.definition_fingerprint(value)}}
    case = {'lane': 'numeric', 'source_capture': {'path': 'capture.json'}, 'source_binding': {
            'object_key': 'visual', 'attachment_id': 'result', 'state_sha256': S.sha(value['state']),
            'definition_fingerprint': S.definition_fingerprint(value)}}
    context = {**copy.deepcopy(value['state']), 'population': a['population']['key'],
               'data_watermark': a['freshness']['data_watermark'], 'freshness_reference': a['freshness']['reference']}
    source = {'format': 'sigma-normalized', 'raw_file': a['file'], 'context': context}
    target = {'format': 'json', 'context': copy.deepcopy(context)}
    columns = [{'source': 'zone', 'target': 'zone'}, {'source': 'count', 'target': 'count'}]
    return value, asset, case, source, target, normalized, columns


def package_fixture(root):
    source, target = {'workbookId': 'workbook-1'}, {'instance': 'https://target.invalid', 'allowed_changes': 'model_changes'}
    raw_files = {'source.json': S.encoded(source), 'target.json': S.encoded(target), 'queries/example.sql': b'SELECT 1 AS value'}
    build = {'schema_version': 'sigma-prepush-build.v1', 'route': 'omni_semantic_reconstruction',
             'target_write_authority': False, 'production_ready': False}
    manifest = {'schema_version': S.PACKAGE, 'route': build['route'], 'synthetic': True,
                'source_sha256': S.sha(source), 'target_sha256': S.sha(target),
                'files': {name: S.sha(raw) for name, raw in raw_files.items()}, 'build': build,
                'target_write_authority': False, 'migration_accepted': False, 'live_validation': 'not_performed'}
    manifest['review'] = {'decision': 'accept', 'actor': {'uid': 1001, 'name': 'Synthetic reviewer'},
        **{k: manifest[k] for k in ('route', 'source_sha256', 'target_sha256')},
        'proposal_sha256': S.sha({**build, 'files': {'queries/example.sql': 'SELECT 1 AS value'}})}
    for name, raw in raw_files.items():
        write(root, name, raw)
    write(root, 'manifest.json', S.encoded(manifest))
    return manifest


class SigmaEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_legacy_actual_files_verify_without_completeness_upgrade(self):
        value = legacy_fixture(self.root)
        report = S.verify_capture_files(value, self.root)
        self.assertEqual(len(report['verified_files']), 2)
        self.assertFalse(report['target_write_authority'])
        self.assertIn('sigma.result_completeness_not_established', report['gaps'])

    def test_legacy_changed_file_rejected(self):
        value = legacy_fixture(self.root)
        (self.root / 'element.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, 'evidence_bytes_changed'):
            S.verify_capture_files(value, self.root)

    def test_v2_page_is_visual_only_without_fabricated_model(self):
        value = v2_fixture(self.root)
        report = S.verify_capture_files(value, self.root)
        self.assertEqual(len(report['verified_files']), 1)
        self.assertIn('sigma.page_capture_has_no_numeric_result', report['gaps'])
        asset = {'kind': 'page', 'source_id': 'page-1'}
        with self.assertRaisesRegex(ValueError, 'page_capture_has_no_numeric_result'):
            S.case_binding(asset, {'lane': 'numeric', 'source_binding': {}}, value)

    def test_v2_page_binds_exact_workbook_request_and_selection(self):
        value = v2_fixture(self.root)
        asset = {'kind': 'page', 'source_id': 'page-1', 'source_identity': {'scope': 'workbook-1'}}
        binding = {'workbook_id': 'workbook-1', 'page_id': 'page-1',
                   'capture_content_hash': value['content_hash'], 'request_sha256': value['request_sha256'],
                   'source_snapshot_sha256': value['source']['tagged_snapshot_sha256']}
        case = {'lane': 'visual', 'source_binding': binding}
        self.assertEqual(S.case_binding(asset, case, value), binding)
        asset['source_identity'] = {'workbook_id': 'workbook-1'}
        self.assertEqual(S.case_binding(asset, case, value), binding)
        for key in binding:
            with self.subTest(key=key):
                changed = {**binding, key: 'different'}
                with self.assertRaisesRegex(ValueError, 'page_capture_binding_mismatch'):
                    S.case_binding(asset, {**case, 'source_binding': changed}, value)
        with self.assertRaisesRegex(ValueError, 'page_capture_binding_mismatch'):
            S.case_binding(asset, {**case, 'source_binding': {}}, value)

    def test_v2_page_cannot_bind_same_page_id_from_another_workbook(self):
        value = v2_fixture(self.root)
        binding = {'workbook_id': 'workbook-1', 'page_id': 'page-1',
                   'capture_content_hash': value['content_hash'], 'request_sha256': value['request_sha256'],
                   'source_snapshot_sha256': value['source']['tagged_snapshot_sha256']}
        for identity in ({'scope': 'workbook-2'}, {'workbook_id': 'workbook-2'}, {},
                         {'scope': 'workbook-1', 'workbook_id': 'workbook-2'}):
            with self.subTest(identity=identity):
                asset = {'kind': 'page', 'source_id': 'page-1', 'source_identity': identity}
                with self.assertRaisesRegex(ValueError, 'page_capture_workbook_identity'):
                    S.case_binding(asset, {'lane': 'visual', 'source_binding': binding}, value)

    def test_v2_element_optional_model_and_selection_binding(self):
        value = v2_fixture(self.root, page=False)
        S.verify_capture_files(value, self.root)
        value['request']['data_model_id'] = 'model-1'
        value['original_request'] = copy.deepcopy(value['request'])
        value['request_sha256'] = value['original_request_sha256'] = S.sha(value['request']); seal(value)
        with self.assertRaisesRegex(ValueError, 'visual_model_pair'):
            S.validate_capture(value)

    def test_v2_page_export_cannot_inject_element_or_results_job(self):
        value = v2_fixture(self.root)
        value['jobs'][0]['request_body']['elementId'] = 'element-1'
        value['jobs'][0]['request_sha256'] = S.sha(value['jobs'][0]['request_body']); seal(value)
        with self.assertRaisesRegex(ValueError, 'visual_job_request_mismatch'):
            S.validate_capture(value)

    def test_legacy_json_metadata_cannot_be_resealed_complete(self):
        value = legacy_fixture(self.root)
        value['attachments'][1]['row_completeness'] = 'complete'
        seal(value)
        with self.assertRaisesRegex(ValueError, 'legacy_result_metadata_mismatch'):
            S.verify_capture_files(value, self.root)

    def test_legacy_source_drift_rejected(self):
        value = legacy_fixture(self.root)
        value['source']['final_observation']['workbook']['version'] = 4
        value['source']['final_observation_sha256'] = S.sha(value['source']['final_observation'])
        seal(value)
        with self.assertRaisesRegex(ValueError, 'final_observation_changed'):
            S.validate_capture(value)

    def test_legacy_job_parameters_cannot_change(self):
        value = legacy_fixture(self.root)
        value['jobs'][0]['request_body']['parameters'] = {}
        value['jobs'][0]['request_sha256'] = S.sha(value['jobs'][0]['request_body'])
        seal(value)
        with self.assertRaisesRegex(ValueError, 'job_request_mismatch'):
            S.validate_capture(value)

    def test_paths_and_symlinks_are_rejected(self):
        value = legacy_fixture(self.root)
        for bad in ('../element.json', '/element.json', 'x/../element.json', 'x\\element.json', 'x//element.json'):
            changed = copy.deepcopy(value); changed['attachments'][1]['path'] = bad; seal(changed)
            with self.assertRaises(ValueError): S.validate_capture(changed)
        (self.root / 'element.json').rename(self.root / 'real.json')
        (self.root / 'element.json').symlink_to(self.root / 'real.json')
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            S.verify_capture_files(value, self.root)

    def test_non_regular_file_is_rejected_without_blocking(self):
        import os
        os.mkfifo(self.root / 'pipe')
        with self.assertRaisesRegex(ValueError, 'file_type_or_size'):
            S._read(self.root, 'pipe')

    def test_bundle_preserves_distinct_sources_and_unknowns(self):
        value = bundle_fixture(self.root)
        report = S.verify_capture_files(value, self.root)
        self.assertEqual(report['provenance'], 'supplied_not_authenticated')
        self.assertEqual(len(report['verified_files']), 2)
        self.assertIn(b'unknown_facet', (self.root / 'originals/definition.json').read_bytes())

    def test_definition_pointer_must_match_original_bytes(self):
        value = bundle_fixture(self.root)
        value['inventory']['items'][-1]['configuration']['definition_sha256'] = 'a' * 64
        seal(value)
        with self.assertRaisesRegex(ValueError, 'original_definition_hash'):
            S.verify_capture_files(value, self.root)

    def test_independent_inventory_missing_artifact_is_gap(self):
        value = bundle_fixture(self.root)
        row = copy.deepcopy(value['inventory']['items'][-1]); row.update(key='other', native_id='element-2')
        row.pop('source_mapping'); value['inventory']['items'].append(row); seal(value)
        report = S.verify_capture_files(value, self.root)
        self.assertIn('sigma.inventory_object_evidence_missing:other', report['gaps'])

    def test_bundle_principal_conflict_rejected(self):
        value = bundle_fixture(self.root); value['artifacts'][1]['principal_ref'] = 'principal-ref://other'; seal(value)
        with self.assertRaisesRegex(ValueError, 'state_or_principal'):
            S.validate_capture(value)

    def test_actual_count_rejects_false_complete_claim(self):
        value = bundle_fixture(self.root); value['artifacts'][1]['completeness']['row_count'] = 2; seal(value)
        with self.assertRaisesRegex(ValueError, 'row_count_mismatch'):
            S.verify_capture_files(value, self.root)

    def test_json_precision_and_csv_percent_are_exact(self):
        value = bundle_fixture(self.root); a = value['artifacts'][1]
        normalized = S.normalize_results((self.root / a['file']['path']).read_bytes(), a['parser_profile'], S._binding(value, a))
        self.assertEqual(normalized['rows'][0]['count'], '12345678901234567890.1234567890123456789')
        raw = b'zone,count\nZone 1,12.345678901234567890%\n'
        p = profile('csv'); p['columns'][1]['percent'] = True
        binding = {**S._binding(value, a), 'attachment_sha256': S.sha(raw)}
        normalized = S.normalize_results(raw, p, binding)
        self.assertEqual(normalized['rows'][0]['count'], '0.12345678901234567890')
        self.assertEqual(normalized['completeness'], 'not_established')

    def test_duplicate_json_nonfinite_nested_and_error_rejected(self):
        value = bundle_fixture(self.root); a = value['artifacts'][1]
        for raw in (b'[{"zone":"a","zone":"b","count":1}]', b'[{"zone":"a","count":NaN}]',
                    b'[{"zone":"a","count":{"error":"failed"}}]'):
            with self.assertRaises(ValueError):
                S.normalize_results(raw, profile(), {**S._binding(value, a), 'attachment_sha256': S.sha(raw)})

    def test_error_token_cannot_hide_in_dimension_or_null_mapping(self):
        value = bundle_fixture(self.root); a = value['artifacts'][1]
        raw = b'zone,count\n#ERROR!,\n'; p = profile('csv')
        p['columns'][0].update(nullable=True, null_tokens=['#ERROR!'])
        with self.assertRaisesRegex(ValueError, 'result_error_token'):
            S.normalize_results(raw, p, {**S._binding(value, a), 'attachment_sha256': S.sha(raw)})

    def test_original_secret_aliases_and_nested_config_rejected(self):
        for secret in ({'api_token': 'synthetic-sensitive-value'}, {'raw': '{"credentials":"sensitive-value"}'},
                       {'raw': 'authorization=Bearer synthetic-sensitive-value'}):
            with self.assertRaisesRegex(ValueError, 'credential'):
                S._screen(secret)

    def test_state_bound_comparison_allows_only_scoped_evidence(self):
        args = comparison_fixture(self.root)
        S.verify_capture_files(args[0], self.root)
        self.assertEqual(S.comparison_gaps(*args), [])
        args[4]['context']['cache'] = {'mode': 'different_target_policy'}
        self.assertEqual(S.comparison_gaps(*args), [])

    def test_same_selection_with_separate_observation_references(self):
        args = comparison_fixture(self.root)
        args[0]['artifacts'][1]['selection']['reference'] = 'evidence-ref://result-selection'
        args[0]['artifacts'][1]['observed_state']['selection']['reference'] = 'evidence-ref://observed-selection'
        seal(args[0]); args[5]['binding']['capture_content_hash'] = args[0]['content_hash']
        self.assertEqual(S.comparison_gaps(*args), [])

    def test_file_prefix_case_collision_and_ambiguous_placement_rejected(self):
        with self.assertRaisesRegex(ValueError, 'file_path_collision'):
            S._paths(['Originals/one.json', 'originals/two.json'])
        value = bundle_fixture(self.root)
        placement = copy.deepcopy(value['inventory']['items'][-1])
        placement.update(key='placement', kind='placement', source_mapping=None,
                         configuration={'visual_key': 'visual', 'content_key': 'page'})
        value['inventory']['items'].append(placement); seal(value)
        with self.assertRaisesRegex(ValueError, 'placement_target'): S.validate_capture(value)

    def test_v2_invalid_nested_types_and_producer_row_limit_rejected(self):
        value = v2_fixture(self.root)
        value['jobs'][0] = []; seal(value)
        with self.assertRaisesRegex(ValueError, 'visual_job_set'): S.validate_capture(value)
        value = v2_fixture(self.root)
        value['request']['row_limit'] = 50001
        value['original_request'] = copy.deepcopy(value['request'])
        value['request_sha256'] = value['original_request_sha256'] = S.sha(value['request'])
        for attachment in value['attachments']: attachment['request_sha256'] = value['request_sha256']
        seal(value)
        with self.assertRaisesRegex(ValueError, 'legacy_row_limit'): S.validate_capture(value)

    def test_published_result_cannot_clear_tagged_comparison(self):
        args = comparison_fixture(self.root)
        args[0]['artifacts'][1]['observed_state']['selection'].update(mode='published', tag=None)
        seal(args[0]); args[5]['binding']['capture_content_hash'] = args[0]['content_hash']
        self.assertIn('source.sigma_observed_version_tag_or_view_mismatch', S.comparison_gaps(*args))

    def test_sample_incomplete_and_subset_columns_stay_gaps(self):
        args = comparison_fixture(self.root)
        result = args[0]['artifacts'][1]
        result['observed_state']['result_scope'] = 'sample'
        result['completeness'].update(status='partial', flags=['truncated'])
        seal(args[0]); args[5]['binding']['capture_content_hash'] = args[0]['content_hash']
        args[6].pop()
        gaps = S.comparison_gaps(*args)
        self.assertIn('source.sigma_execution_or_population_unqualified', gaps)
        self.assertIn('source.sigma_result_completeness_unqualified', gaps)
        self.assertIn('source.sigma_complete_column_mapping_required', gaps)

    def test_parent_exclusion_and_cycles_rejected(self):
        args = comparison_fixture(self.root)
        args[0]['inventory']['items'][1]['disposition'] = 'out_of_scope'; seal(args[0])
        with self.assertRaisesRegex(ValueError, 'scope_restricted'): S.comparison_gaps(*args)
        args[0]['inventory']['items'][1]['parent_key'] = 'visual'; seal(args[0])
        with self.assertRaisesRegex(ValueError, 'parent_or_cycle'): S.validate_capture(args[0])

    def test_passive_mcp_provenance_is_required_not_authority(self):
        value = bundle_fixture(self.root)
        a = copy.deepcopy(value['artifacts'][0]); a.update(artifact_id='mcp', kind='mcp_capture', source_channel='passive_mcp',
            file=write(self.root, 'originals/mcp.json', b'{"tools":[]}'))
        value['artifacts'].append(a); seal(value)
        with self.assertRaisesRegex(ValueError, 'passive_mcp_provenance'): S.validate_capture(value)
        a['mcp_evidence'] = {k: 'evidence-ref://synthetic/' + k for k in
                             ('server_ref', 'protocol_version', 'tool_schema_ref', 'tool_name', 'session_ref', 'reference')}
        seal(value)
        self.assertIn('sigma.passive_mcp_not_execution_authority', S.verify_capture_files(value, self.root)['gaps'])

    def test_package_bytes_and_canonical_input_bindings(self):
        manifest = package_fixture(self.root)
        result = S.verify_package_files(manifest, self.root)
        self.assertEqual(result['review'], 'supplied_os_review_not_authenticated')
        self.assertFalse(result['target_write_authority'])
        (self.root / 'queries/example.sql').write_text('SELECT 2 AS value')
        with self.assertRaisesRegex(ValueError, 'file_changed'): S.verify_package_files(manifest, self.root)

    def test_package_unlisted_symlink_and_target_hash_rejected(self):
        manifest = package_fixture(self.root)
        (self.root / 'unlisted.txt').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'inventory_mismatch'): S.verify_package_files(manifest, self.root)
        (self.root / 'unlisted.txt').unlink()
        manifest['target_sha256'] = 'a' * 64; manifest['review']['target_sha256'] = 'a' * 64
        (self.root / 'manifest.json').write_bytes(S.encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'input_binding'): S.verify_package_files(manifest, self.root)

    def test_package_proposal_review_does_not_authorize_native_writes(self):
        manifest = package_fixture(self.root)
        manifest['review']['proposal_sha256'] = 'b' * 64
        (self.root / 'manifest.json').write_bytes(S.encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'proposal_review_binding'): S.verify_package_files(manifest, self.root)
        manifest['target_write_authority'] = True
        with self.assertRaisesRegex(ValueError, 'authority'): S.validate_package(manifest)


if __name__ == '__main__':
    unittest.main()
