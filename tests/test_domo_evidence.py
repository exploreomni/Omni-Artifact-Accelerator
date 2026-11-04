"""Neutral original Domo evidence fixtures; no source runtime, APIs or browser."""
import copy
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('domo_evidence_test', ROOT / 'skills/omni-artifact-translator/scripts/domo_visual.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def seal(value):
    value['content_hash'] = D.sha({k: v for k, v in value.items() if k != 'content_hash'})
    return value


def write(root, path, raw):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(raw)
    return {'path': path, 'sha256': D.sha(raw), 'bytes': len(raw)}


def profile():
    return {'schema_version': 1, 'format': 'json', 'rows_pointer': '', 'headers': ['zone', 'amount'],
            'subtotal_policy': 'preserve', 'columns': [
                {'ordinal': 0, 'name': 'zone', 'type': 'string', 'nullable': False, 'null_tokens': []},
                {'ordinal': 1, 'name': 'amount', 'type': 'number', 'nullable': True, 'null_tokens': [''],
                 'decimal_separator': '.', 'group_separator': None, 'percent': False}]}


def png():
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(b'\x00\x22\x33\x44')) + chunk(b'IEND', b'')


def artifact(value, root, aid, kind, fmt, raw, keys):
    a = {'artifact_id': aid, 'kind': kind, 'format': fmt, 'file': write(root, 'originals/' + aid + '.' + fmt, raw),
         'source_channel': 'supplied', 'object_keys': keys, 'selection': copy.deepcopy(value['selection']),
         'state_sha256': D.sha(value['state']), 'principal_ref': value['identity']['principal_ref'],
         'captured_at': '2026-01-01T12:00:00+00:00', 'reference': 'evidence-ref://synthetic/' + aid}
    value['artifacts'].append(a)
    return a


def fixture(root):
    producer = {'contract_version': 'omnikit.domo.evidence.v1', 'mode': 'manual', 'objects': [], 'edges': [],
                'coverage': [], 'manual_capture_queue': [], 'checkpoints': [], 'diagnostics': []}
    for kind, native in [('card', 'card-1'), ('page', 'page-1')]:
        producer['objects'].append({'object_type': kind, 'object_id': native, 'tenant_ref': 'tenant-ref://synthetic',
                                    'attributes': {'definition': {'id': native}}, 'redaction_state': 'not_required',
                                    'definition_state': 'definition_complete', 'title': 'Synthetic ' + kind})
    producer['bundle_fingerprint'] = 'sha256:' + D.sha(producer)
    value = {'schema_version': D.SCHEMA, 'status': 'complete', 'evidence_mode': 'synthetic_fixture',
             'identity': {'source_origin': 'https://example.invalid', 'tenant_ref': 'tenant-ref://synthetic',
                          'principal_ref': 'principal-ref://synthetic/reader'},
             'selection': {'scope_id': 'page-1', 'version': 'revision-1', 'reference': 'evidence-ref://selection'},
             'state': {'filters': {}, 'variables': {'zone': 'Zone 1'}, 'timezone': 'UTC', 'locale': 'en-US',
                       'cache': {'mode': 'observed_existing'}, 'principal': 'principal-ref://synthetic/reader'},
             'producer': {'contract_version': producer['contract_version'], 'revision': D.PRODUCER_PIN,
                          'file': write(root, 'originals/producer.json', D.encoded(producer))},
             'inventory': {'reference': 'independent-ref://synthetic/inventory', 'completeness': 'selected_scope_declared',
                           'expected_counts': {'page': 1, 'card': 1, 'query': 1, 'placement': 2}, 'items': []},
             'artifacts': [], 'gaps': [], 'target_write_authority': False,
             'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}
    definitions = {}
    for key, kind, native, parent, config in [
        ('page', 'page', 'page-1', None, {}), ('card', 'card', 'card-1', 'page', {}),
        ('query', 'query', 'query-1', 'card', {'result_owner_key': 'card'}),
        ('place-a', 'placement', 'place-a', 'page', {'target_key': 'card'}),
        ('place-b', 'placement', 'place-b', 'page', {'target_key': 'card'})]:
        definitions[key] = {'id': native, 'kind': kind, 'source_formula': 'SUM(`amount`)', 'context': key}
        row = {'key': key, 'kind': kind, 'native_id': native, 'parent_key': parent, 'disposition': 'include',
               'reference': 'evidence-ref://synthetic/' + key, 'configuration': {**config, 'definition_sha256': D.sha(definitions[key])},
               'required_evidence_kinds': ['definition'], 'source_mapping': {'artifact_id': 'definitions', 'pointer': '/' + key}}
        if key != 'page':
            row['page_id'] = 'page-1'
        if kind in {'placement', 'query'}:
            row['card_id'] = 'card-1'
        if kind == 'placement':
            row['placement_id'] = native
        if kind == 'query':
            row['query_id'] = native
        value['inventory']['items'].append(row)
    artifact(value, root, 'definitions', 'definition', 'json', D.encoded(definitions), list(definitions))
    raw = b'[{"zone":"Zone 1","amount":12345678901234567890.1234567890123456789}]'
    req = artifact(value, root, 'request', 'request', 'json', D.encoded({'cardId': 'card-1', 'variables': {'zone': 'Zone 1'}}), ['place-a'])
    resp = artifact(value, root, 'response', 'response', 'json', raw, ['place-a'])
    req['query_id'] = resp['query_id'] = 'query-1'
    a = artifact(value, root, 'results', 'results', 'json', raw, ['place-a'])
    a.update(query_id='query-1', parser_profile=profile(), completeness={'status': 'complete', 'row_count': 1, 'flags': [],
             'reference': 'evidence-ref://complete'}, population={'key': 'population-1', 'reference': 'evidence-ref://population'},
             freshness={'observed_at': a['captured_at'], 'data_watermark': 'watermark-1', 'reference': 'evidence-ref://freshness'},
             observed_state={'reference': 'evidence-ref://state', 'state': copy.deepcopy(value['state']),
                 'selection': copy.deepcopy(value['selection']), 'definition_sha256': D.sha(definitions['card']),
                 'execution_status': 'completed', 'execution_kind': 'card', 'result_scope': 'full_data', 'row_limit': None,
                 'placement_id': 'place-a', 'query_id': 'query-1', 'request_artifact_id': 'request', 'response_artifact_id': 'response'})
    return seal(value)


def app_fixture(root):
    value = fixture(root)
    for key, kind, native, parent, config in [('app', 'app', 'app-1', None, {'app_family': 'app_studio', 'version': '4'}),
                                           ('app-page', 'app_page', 'app-page-1', 'app', {}),
                                           ('component', 'component', 'component-1', 'app-page', {})]:
        row = {'key': key, 'kind': kind, 'native_id': native, 'parent_key': parent, 'app_id': 'app-1',
               'page_id': 'app-page-1' if kind == 'component' else None, 'reference': 'evidence-ref://app/' + key,
               'disposition': 'include', 'configuration': config, 'required_evidence_kinds': ['definition']}
        if kind == 'component':
            row['behaviors'] = {facet: {'disposition': 'not_applicable', 'owner_ref': 'owner-ref://synthetic',
                                     'evidence_refs': ['evidence-ref://facet/' + facet],
                                     'acceptance_refs': ['case-ref://facet/' + facet]} for facet in D.BEHAVIOR_FACETS}
        value['inventory']['items'].append(row)
        value['inventory']['expected_counts'][kind] = 1
    value['app_handoff'] = {'schema_version': D.HANDOFF_SCHEMA, 'assignment_only': True, 'mode': 'read_only',
                            'owner_ref': 'owner-ref://synthetic', 'handoff_ref': 'handoff-ref://synthetic',
                            'app_keys': ['app'], 'evidence_refs': ['evidence-ref://app'], 'side_effect_kinds': [],
                            'operations': [], 'build_authority': False, 'target_write_authority': False,
                            'publish_authority': False, 'acceptance_authority': False}
    return seal(value)


def comparison_fixture(root):
    value = fixture(root)
    a = next(a for a in value['artifacts'] if a['kind'] == 'results')
    binding = D.result_binding(value, a)
    normalized = D.normalize_results((root / a['file']['path']).read_bytes(), a['parser_profile'], binding)
    asset = next(a for a in D.project_assets(value) if a['source_identity']['object_key'] == 'place-a')
    case = {'lane': 'numeric', 'source_capture': {'path': 'capture.json'}, 'source_binding': binding}
    context = {**copy.deepcopy(value['state']), 'population': a['population']['key'],
               'data_watermark': a['freshness']['data_watermark'], 'freshness_reference': a['freshness']['reference']}
    source = {'format': 'domo-normalized', 'raw_file': a['file'], 'context': context}
    target = {'format': 'json', 'context': copy.deepcopy(context)}
    columns = [{'source': 'zone', 'target': 'zone'}, {'source': 'amount', 'target': 'amount'}]
    return value, asset, case, source, target, normalized, columns


class DomoEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_original_contract_and_repeated_placements_preserved(self):
        value = fixture(self.root)
        result = D.verify_capture_files(value, self.root)
        self.assertEqual(len(result['verified_files']), 5)
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['provenance'], 'supplied_not_authenticated')
        self.assertFalse(result['target_write_authority'])
        places = [r for r in D.project_assets(value) if r['source_identity']['inventory_kind'] == 'placement']
        self.assertEqual([p['source_id'] for p in places], ['place-a', 'place-b'])
        self.assertEqual(len({p['scope'] for p in places}), 2)

    def test_changed_bytes_rejected(self):
        value = fixture(self.root)
        (self.root / 'originals/results.json').write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, 'evidence_bytes_changed'):
            D.verify_capture_files(value, self.root)

    def test_original_producer_revision_and_hash_remain_enforced(self):
        value = fixture(self.root)
        value['producer']['revision'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'producer_contract_revision'):
            D.validate_capture(seal(value))
        value = fixture(self.root)
        producer = D.decode((self.root / value['producer']['file']['path']).read_bytes())
        producer['objects'][0]['title'] = 'Changed after producer fingerprint'
        value['producer']['file'] = write(self.root, 'originals/producer.json', D.encoded(producer))
        with self.assertRaisesRegex(ValueError, 'bundle_fingerprint_mismatch'):
            D.verify_capture_files(seal(value), self.root)

    def test_definition_pointer_must_match_actual_bytes(self):
        value = fixture(self.root)
        value['inventory']['items'][1]['configuration']['definition_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'original_definition_hash'):
            D.verify_capture_files(seal(value), self.root)

    def test_partial_denominator_never_becomes_complete(self):
        value = fixture(self.root)
        value['inventory']['expected_counts']['placement'] = 3
        with self.assertRaisesRegex(ValueError, 'inventory_denominator_mismatch'):
            D.validate_capture(seal(value))
        value['inventory']['completeness'] = 'partial'
        self.assertIn('domo.independent_inventory_partial', D.verify_capture_files(seal(value), self.root)['gaps'])

    def test_duplicate_placement_and_ancestry_conflict_rejected(self):
        for change in ('duplicate', 'parent'):
            value = fixture(self.root)
            p = value['inventory']['items'][-1]
            if change == 'duplicate':
                p['native_id'] = p['placement_id'] = 'place-a'
            else:
                p['page_id'] = 'other-page'
            with self.assertRaises(ValueError):
                D.validate_capture(seal(value))

    def test_missing_required_render_is_reported(self):
        value = fixture(self.root)
        value['inventory']['items'][-1]['required_evidence_kinds'].append('component_render')
        self.assertIn('domo.required_evidence_missing:place-b:component_render', D.verify_capture_files(seal(value), self.root)['gaps'])

    def test_query_must_belong_to_captured_card(self):
        value = fixture(self.root)
        value['artifacts'][-1]['query_id'] = 'arbitrary-query'
        value['artifacts'][-1]['observed_state']['query_id'] = 'arbitrary-query'
        with self.assertRaisesRegex(ValueError, 'result_query_membership'):
            D.validate_capture(seal(value))

    def test_exact_numbers_not_binary_float_roundtripped(self):
        args = comparison_fixture(self.root)
        result = args[-2]
        self.assertEqual(result['rows'][0]['amount'], '12345678901234567890.1234567890123456789')
        self.assertEqual(D.comparison_gaps(*args), [])

    def test_variable_change_cannot_reuse_case(self):
        args = list(comparison_fixture(self.root))
        args[0]['state']['variables']['zone'] = 'Zone 2'
        for artifact_row in args[0]['artifacts']:
            artifact_row['state_sha256'] = D.sha(args[0]['state'])
        seal(args[0])
        with self.assertRaisesRegex(ValueError, 'case_state_or_definition'):
            D.comparison_gaps(*args)

    def test_observed_state_change_survives_resealing_as_gap(self):
        args = list(comparison_fixture(self.root))
        value = args[0]
        value['artifacts'][-1]['observed_state']['state']['variables']['zone'] = 'Zone 2'
        seal(value)
        args[2]['source_binding'] = D.result_binding(value, value['artifacts'][-1])
        args[-2]['binding'] = args[2]['source_binding']
        self.assertIn('source.domo_state.variables', D.comparison_gaps(*args))

    def test_dataset_query_is_not_card_result(self):
        args = list(comparison_fixture(self.root))
        args[0]['artifacts'][-1]['observed_state']['execution_kind'] = 'dataset'
        seal(args[0])
        args[2]['source_binding'] = D.result_binding(args[0], args[0]['artifacts'][-1])
        args[-2]['binding'] = args[2]['source_binding']
        self.assertIn('source.domo_execution_kind_not_artifact_result', D.comparison_gaps(*args))

    def test_wrong_placement_observation_cannot_pass(self):
        args = list(comparison_fixture(self.root))
        args[0]['artifacts'][-1]['observed_state']['placement_id'] = 'place-b'
        seal(args[0])
        args[2]['source_binding'] = D.result_binding(args[0], args[0]['artifacts'][-1])
        args[-2]['binding'] = args[2]['source_binding']
        self.assertIn('source.domo_placement_state_unqualified', D.comparison_gaps(*args))

    def test_original_response_cannot_contain_different_rows(self):
        value = fixture(self.root)
        value['artifacts'][2]['file'] = write(self.root, 'originals/response.json', b'[]')
        with self.assertRaisesRegex(ValueError, 'response_result_bytes_mismatch'):
            D.validate_capture(seal(value))

    def test_missing_execution_originals_are_not_parity(self):
        args = list(comparison_fixture(self.root))
        args[0]['artifacts'][-1]['observed_state']['request_artifact_id'] = None
        seal(args[0])
        args[2]['source_binding'] = D.result_binding(args[0], args[0]['artifacts'][-1])
        args[-2]['binding'] = args[2]['source_binding']
        self.assertIn('source.domo_original_execution_request_artifact_id_required', D.comparison_gaps(*args))

    def test_read_only_app_handoff_has_honest_zero_side_effects(self):
        value = app_fixture(self.root)
        result = D.verify_capture_files(value, self.root)
        self.assertFalse(result['target_write_authority'])
        self.assertEqual(value['app_handoff']['operations'], [])
        self.assertIn('domo.definition_evidence_missing:app', result['gaps'])
        value['app_handoff']['side_effect_kinds'] = ['external_write']
        with self.assertRaisesRegex(ValueError, 'read_only_app_has_side_effects'):
            D.validate_capture(seal(value))

    def test_missing_component_facet_owner_or_acceptance_rejected(self):
        for field in ('facet', 'owner', 'acceptance'):
            value = app_fixture(self.root)
            behaviors = value['inventory']['items'][-1]['behaviors']
            if field == 'facet':
                del behaviors['navigation']
            elif field == 'owner':
                behaviors['navigation'].pop('owner_ref')
            else:
                behaviors['navigation']['acceptance_refs'] = []
            with self.assertRaises(ValueError):
                D.validate_capture(seal(value))

    def test_unresolved_component_behavior_preserved(self):
        value = app_fixture(self.root)
        value['inventory']['items'][-1]['behaviors']['navigation']['disposition'] = 'unverified'
        self.assertIn('domo.behavior_unresolved:component:navigation', D.evidence_gaps(seal(value)))

    def test_operational_handoff_requires_all_owners_and_controls(self):
        value = app_fixture(self.root)
        value['inventory']['items'].append({'key': 'operation', 'kind': 'operation', 'native_id': 'op-1',
            'parent_key': 'component', 'disposition': 'include', 'reference': 'evidence-ref://operation',
            'configuration': {'component_key': 'component', 'side_effect_kind': 'external_write'},
            'required_evidence_kinds': ['definition']})
        value['inventory']['expected_counts']['operation'] = 1
        h = value['app_handoff']
        h.update(mode='operational', side_effect_kinds=['external_write'], operations=[{
            'operation_id': 'op-1', 'component_key': 'component', 'owner_ref': 'owner-ref://synthetic', 'disposition': 'deferred',
            'side_effect_kind': 'external_write', 'execution_authorized': False, 'source_evidence_ref': 'evidence-ref://operation',
            'target_ref': 'target-ref://unresolved', 'authorization_requirement_ref': 'requirement-ref://authorization',
            'retry_policy_ref': 'requirement-ref://no_automatic_retry', 'failure_behavior_ref': 'case-ref://failure',
            'acceptance_ref': 'case-ref://operation'}])
        D.validate_capture(seal(value))
        h['operations'][0].pop('retry_policy_ref')
        with self.assertRaisesRegex(ValueError, 'operation_retry_policy_ref'):
            D.validate_capture(seal(value))

    def test_read_only_handoff_cannot_omit_inventory_operation(self):
        value = app_fixture(self.root)
        value['inventory']['items'].append({'key': 'operation', 'kind': 'operation', 'native_id': 'op-1',
            'parent_key': 'component', 'disposition': 'include', 'reference': 'evidence-ref://operation',
            'configuration': {'component_key': 'component', 'side_effect_kind': 'external_write'},
            'required_evidence_kinds': ['definition']})
        value['inventory']['expected_counts']['operation'] = 1
        with self.assertRaisesRegex(ValueError, 'app_operation_denominator'):
            D.validate_capture(seal(value))

    def test_image_metadata_cannot_smuggle_plaintext_credential(self):
        value = fixture(self.root)
        artifact(value, self.root, 'image', 'source_asset', 'jpeg',
                 b'\xff\xd8\xff\xe1 api_key=synthetic-secret-value \xff\xd9', ['card'])
        with self.assertRaisesRegex(ValueError, 'credential_bearing_evidence'):
            D.verify_capture_files(seal(value), self.root)

    def test_self_asserted_authority_and_secret_content_rejected(self):
        for field, val in [('build_authority', True), ('X-DOMO-Developer-Token', 'synthetic-secret-value')]:
            value = fixture(self.root)
            value['inventory']['items'][0]['configuration'][field] = val
            with self.assertRaises(ValueError):
                D.validate_capture(seal(value))
        value = fixture(self.root)
        a = artifact(value, self.root, 'source', 'source_asset', 'javascript',
                     b'const client_secret = "synthetic-never-output";', ['card'])
        with self.assertRaisesRegex(ValueError, 'credential_bearing_evidence'):
            D.verify_capture_files(seal(value), self.root)

    def test_code_is_retained_and_never_executed(self):
        value = fixture(self.root)
        artifact(value, self.root, 'code', 'source_asset', 'javascript', b'throw new Error("must stay inert");', ['card'])
        result = D.verify_capture_files(seal(value), self.root)
        self.assertIn('domo.source_asset_inert_not_security_qualified:code', result['gaps'])
        self.assertEqual(result['verified_files'][-1]['inspection']['execution'], 'never_executed')

    def test_paths_symlinks_and_archives_rejected(self):
        value = fixture(self.root)
        value['artifacts'][0]['file']['path'] = '../outside.json'
        with self.assertRaises(ValueError):
            D.validate_capture(seal(value))
        value = fixture(self.root)
        target = self.root / 'originals/definitions.json'
        raw = target.read_bytes()
        target.unlink()
        other = self.root / 'other.json'
        other.write_bytes(raw)
        target.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'file_unavailable_or_unsafe'):
            D.verify_capture_files(value, self.root)
        target.unlink()
        value = fixture(self.root)
        artifact(value, self.root, 'archive', 'source_asset', 'text', b'PK\x03\x04not an executed archive', ['card'])
        with self.assertRaisesRegex(ValueError, 'archives_and_executable_containers'):
            D.verify_capture_files(seal(value), self.root)

    def test_png_bytes_and_dimensions_checked(self):
        value = fixture(self.root)
        a = artifact(value, self.root, 'render', 'component_render', 'png', png(), ['place-a'])
        a.update(viewport={'width': 800, 'height': 600, 'device_scale': 1}, theme_ref='theme-ref://source',
                 actual_dimensions={'width': 1, 'height': 1})
        D.verify_capture_files(seal(value), self.root)
        a['actual_dimensions']['width'] = 2
        with self.assertRaisesRegex(ValueError, 'image_dimensions_mismatch'):
            D.verify_capture_files(seal(value), self.root)

    def test_source_asset_extension_cannot_hide_archive(self):
        value = fixture(self.root)
        a = artifact(value, self.root, 'container', 'source_asset', 'text', b'not extracted', ['card'])
        a['file'] = write(self.root, 'originals/container.zip', b'not extracted')
        with self.assertRaisesRegex(ValueError, 'archives_and_executable_containers'):
            D.verify_capture_files(seal(value), self.root)

    def test_case_binding_cannot_swap_card_for_placement(self):
        args = list(comparison_fixture(self.root))
        args[1]['source_id'] = 'card-1'
        with self.assertRaisesRegex(ValueError, 'case_source_identity'):
            D.comparison_gaps(*args)

    def test_error_tokens_cannot_be_hidden_as_nulls(self):
        value = fixture(self.root)
        raw = b'[{"zone":"Zone 1","amount":"#ERROR!"}]'
        a = value['artifacts'][-1]
        a['file'] = write(self.root, 'originals/results.json', raw)
        a['parser_profile']['columns'][1]['null_tokens'].append('#ERROR!')
        with self.assertRaisesRegex(ValueError, 'result_error_token'):
            D.normalize_results(raw, a['parser_profile'], D.result_binding(value, a))


if __name__ == '__main__':
    unittest.main()
