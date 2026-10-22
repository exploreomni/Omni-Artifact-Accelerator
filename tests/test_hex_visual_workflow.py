"""Independent Hex input/placement/state expectations; no source-code execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/omni-artifact-accelerator/scripts'))
import visual_workflow as v  # noqa: E402


def module(name):
    path = ROOT / 'skills/omni-artifact-translator/scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location('hex_workflow_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


P, V, C, INPUT, N, R = ['10000000-0000-4000-8000-' + str(n).zfill(12) for n in range(1, 7)]


def native():
    return {'schemaVersion': 3, 'meta': {'projectId': P, 'sourceVersionId': V, 'title': 'Capacity planning', 'hexType': 'PROJECT'},
            'cells': [
                {'cellId': INPUT, 'cellType': 'INPUT', 'config': {'name': 'region', 'inputType': 'DROPDOWN', 'defaultValue': 'West'}},
                {'cellId': C, 'cellType': 'CHARTV2', 'config': {'chartSpec': {'type': 'bar', 'dataFrame': 'capacity'}}},
                {'cellId': N, 'cellType': 'MARKDOWN', 'config': {'source': 'Review capacity before changing a scenario.'}}],
            'appLayout': {'tabs': [{'name': 'View ' + str(n), 'rows': [{'columns': [{'start': 0, 'end': 120,
                'elements': [{'cellId': C}, {'cellId': INPUT}, {'cellId': N}]}]}]} for n in range(7)]},
            'genAppFiles': [{'path': 'App.js', 'contents': '// source data only; never executed by the importer\n'}]}


def request():
    return {'schema_version': 'hex-visual-capture-request.v1', 'capture_id': 'capacity',
            'source_origin': 'https://hex.synthetic.invalid', 'workspace_id': 'synthetic-workspace',
            'principal_ref': 'synthetic-viewer', 'authorization_ref': 'synthetic-read-scope',
            'evidence_mode': 'synthetic_fixture', 'route': 'reuse_existing', 'route_reference': 'synthetic-existing-model',
            'target_surface': 'both', 'exports': [{'project_id': P, 'version': 'latest',
                'expected_source_version_id': V, 'source_path': 'capacity.hex.yaml'}],
            'outputs': [{'output_id': 'capacity', 'project_id': P, 'source_version_id': V, 'cell_id': C,
                'static_id': C, 'run_id': R, 'source_mode': 'published', 'expected_project_version': '8',
                'identity_reference': 'synthetic-version-crosswalk'}], 'images': [],
            'state': {'state_id': 'default-west', 'inputs': {'region': 'West'}, 'filters': {}, 'timezone': 'UTC',
                      'locale': 'en-US', 'principal': 'synthetic-viewer', 'data_time_policy': 'frozen-synthetic-population'}}


def profile():
    return {'schema_version': 1, 'format': 'csv', 'encoding': 'utf-8', 'subtotal_policy': 'preserve',
            'headers': ['site', 'amount'], 'columns': [
                {'ordinal': 0, 'name': 'site', 'type': 'string', 'nullable': False, 'null_tokens': []},
                {'ordinal': 1, 'name': 'amount', 'type': 'number', 'nullable': True, 'null_tokens': ['NULL'],
                 'decimal_separator': '.', 'group_separator': None, 'percent': False}]}


def capture_fixture(root, supplied_request=None):
    source = root / 'inputs/supplied'
    source.mkdir(parents=True, exist_ok=True)
    (source / 'capacity.hex.yaml').write_text(json.dumps(native()))
    return module('hex_capture').import_local(supplied_request or request(), source,
                                             root / 'inputs/hex-capture', allow_source_read=True)


class HexVisualWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'engagement'
        v.ap.init(self.root, 'Synthetic Hex workflow', 'migration', 'both')
        self.c, self.b, self.t = module('hex_capture'), module('hex_visual'), module('translate_artifact')
        self.result = capture_fixture(self.root)
        self.raw = b'site,amount\nWest,12345678901234567890.123456789\nEast,NULL\nNorth,0\n'
        (self.root / 'inputs/supplied/results.csv').write_bytes(self.raw)
        self.context = {**request()['state'], 'data_watermark': 'fixture-three-sites',
                        'cache_reference': 'source-cache-reference', 'population': 'all-three-sites'}
        self.put('evidence/candidate.json', {'kind': 'synthetic_candidate'})
        self.refresh()

    def put(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def refresh(self):
        self.original = str(Path(self.result['output']).relative_to(self.root))
        self.capture = self.result['capture']
        raw = (self.root / self.original).read_bytes()
        self.inventory = self.t.translate(raw, 'hex-capture')
        self.put('inputs/inventory.json', self.inventory)
        (self.root / 'contracts/visual.json').unlink(missing_ok=True)
        v.prepare(self.root, self.original, 'inputs/inventory.json', 'contracts/visual.json')
        self.req = v.load(self.root, 'contracts/visual.json')
        self.req['route_reference'] = 'synthetic-existing-model'
        self.item = next(i for i in self.req['items'] if i['source_identity'].get('cell_id') == C and i['kind'] == 'visual')
        self.case = next(c for c in self.item['required_cases'] if c['case_id'].endswith('/numeric/default'))
        self.binding = {k: self.item['source_identity'].get(k) for k in ('object_id', 'project_id', 'source_version_id', 'cell_id')}
        self.binding.update(output_id='capacity', state_sha256=self.b.sha(self.capture['request']['state']))
        self.case.update(source_capture=v.pin(self.root, self.original), source_binding=self.binding)
        self.put('contracts/visual.json', self.req)

    def evidence(self, observed=True, complete=True, flags=None):
        observation = {**request()['outputs'][0], **self.context, 'state_sha256': self.binding['state_sha256'],
                       'applied': True, 'reference': 'synthetic-independent-observer',
                       'execution_reference': 'fixture-execution-8', 'output_freshness_reference': 'fixture-result-source-hash'}
        spec = {'schema_version': 1, 'kind': 'hex_evidence_import', 'capture_content_hash': self.capture['content_hash'],
                'attachments': [{'output_id': 'capacity', 'path': 'results.csv', 'format': 'csv',
                    'provenance_reference': 'fixture-original-csv', 'result_completeness': {
                        'status': 'complete' if complete else 'partial', 'reference': 'fixture-three-sites', 'flags': flags or []}}],
                'state_observations': [observation] if observed else [], 'render_state_observations': []}
        self.result = self.c.import_evidence(Path(self.result['output']), spec, self.root / 'inputs/supplied')
        self.refresh()

    def comparison(self):
        attachment = next(a for a in self.capture['attachments'] if a.get('format') == 'csv')
        binding = {k: self.binding[k] for k in ('project_id', 'source_version_id', 'cell_id', 'output_id', 'state_sha256')}
        binding.update(capture_content_hash=self.capture['content_hash'], attachment_sha256=self.b.sha(self.raw))
        self.put('inputs/normalized.json', self.b.normalize_results(self.raw, profile(), binding))
        self.put('evidence/target.json', [{'site': 'West', 'amount': '12345678901234567890.123456789'},
                                         {'site': 'East', 'amount': None}, {'site': 'North', 'amount': 0}])
        return {'schema_version': 1, 'kind': 'analyst_numeric_comparison_spec', 'case_id': self.case['case_id'],
                'requirements': v.pin(self.root, 'contracts/visual.json'), 'candidate': v.pin(self.root, 'evidence/candidate.json'),
                'source': {'file': v.pin(self.root, 'inputs/normalized.json'),
                           'raw_file': v.pin(self.root, str(Path(self.original).parent / attachment['path'])),
                           'format': 'hex-normalized', 'context': copy.deepcopy(self.context),
                           'complete': True, 'completeness_reference': 'fixture-three-sites'},
                'target': {'file': v.pin(self.root, 'evidence/target.json'), 'format': 'json',
                           'context': {**self.context, 'principal': 'target-viewer', 'cache_reference': 'target-cache'},
                           'complete': True, 'completeness_reference': 'fixture-three-sites'},
                'persona_equivalence_reference': 'synthetic-permission-review', 'keys': ['site'], 'columns': [
                    {'name': 'site', 'type': 'string', 'source': 'site', 'target': 'site'},
                    {'name': 'amount', 'type': 'number', 'source': 'amount', 'target': 'amount', 'nullable': True}]}

    def compare(self, spec):
        self.put('contracts/comparison.json', spec)
        (self.root / 'evidence/comparison.json').unlink(missing_ok=True)
        v.compare(self.root, 'contracts/comparison.json', 'evidence/comparison.json')
        return v.load(self.root, 'evidence/comparison.json')

    def test_controls_content_and_repeated_placements_keep_separate_obligations(self):
        _, req = v.requirements(self.root, 'contracts/visual.json')
        controls = [i for i in req['items'] if i['source_identity'].get('cell_id') == INPUT]
        self.assertEqual(len([i for i in req['items'] if i['kind'] == 'placement']), 21)
        self.assertTrue(controls)
        self.assertFalse(any(c['lane'] == 'numeric' for i in controls for c in i['required_cases']))
        self.assertTrue(any(i['kind'] == 'control' and any(c['case_id'].endswith('/interaction/pending_run_reset')
                        for c in i['required_cases']) for i in controls))
        self.assertTrue(any(i['source_identity'].get('generated_interface_unobserved') for i in req['items']))

    def test_matching_preview_without_observation_is_inconclusive(self):
        self.evidence(observed=False, complete=False)
        result = self.compare(self.comparison())
        self.assertEqual(result['status'], 'inconclusive')
        self.assertIn('source.hex_value_observation_required', result['gaps'])
        self.assertIn('source.hex_result_completeness_unverified', result['gaps'])

    def test_complete_state_preserves_decimal_null_zero_and_separate_cache_identity(self):
        self.evidence()
        spec = self.comparison()
        self.assertEqual(self.compare(spec)['status'], 'pass')
        rows = v.load(self.root, 'evidence/target.json')
        rows[0]['amount'] = '12345678901234567890.123456790'
        rows[1]['amount'], rows[2]['amount'] = 0, None
        self.put('evidence/target.json', rows)
        spec['target']['file'] = v.pin(self.root, 'evidence/target.json')
        result = self.compare(spec)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['mismatch_count'], 3)

    def test_wrong_output_state_and_definition_fail_before_comparison(self):
        for key, value in (('cell_id', INPUT), ('output_id', 'unknown'), ('state_sha256', '0' * 64), ('object_id', 'wrong')):
            bad = copy.deepcopy(self.req)
            case = next(c for i in bad['items'] for c in i['required_cases'] if c['case_id'] == self.case['case_id'])
            case['source_binding'][key] = value
            self.put('contracts/visual.json', bad)
            with self.assertRaises(ValueError):
                v.requirements(self.root, 'contracts/visual.json')
        self.put('contracts/visual.json', self.req)

    def test_same_definition_from_another_workspace_cannot_replace_frozen_source(self):
        frozen = copy.deepcopy(self.req)
        other_request = request()
        other_request.update(source_origin='https://other-hex.synthetic.invalid', workspace_id='other-workspace')
        other = self.c.import_local(other_request, self.root / 'inputs/supplied', self.root / 'inputs/other-capture', allow_source_read=True)
        case = next(c for i in frozen['items'] for c in i['required_cases'] if c['case_id'] == self.case['case_id'])
        case['source_capture'] = v.pin(self.root, str(Path(other['output']).relative_to(self.root)))
        self.put('contracts/visual.json', frozen)
        with self.assertRaisesRegex(ValueError, 'hex_workspace_mismatch'):
            v.requirements(self.root, 'contracts/visual.json')

    def test_changed_input_or_missing_persona_reference_cannot_pass(self):
        self.evidence()
        spec = self.comparison()
        spec['target']['context']['inputs'] = {'region': 'East'}
        self.assertIn('context.inputs', self.compare(spec)['gaps'])
        spec = self.comparison()
        del spec['persona_equivalence_reference']
        self.assertEqual(self.compare(spec)['status'], 'inconclusive')

    def test_surface_assignment_requires_reference_and_scopes_case_coverage(self):
        control = next(i for i in self.req['items'] if i['kind'] == 'control')
        control['target_surfaces'] = ['app']
        self.put('contracts/visual.json', self.req)
        with self.assertRaisesRegex(ValueError, 'assignment_reference'):
            v.requirements(self.root, 'contracts/visual.json')
        control['assignment_reference'] = 'reviewed-app-only-control'
        self.put('contracts/visual.json', self.req)
        self.put('evidence/dashboard.json', {'contract': 'oaa-omni-native-v1'})
        v.coverage(self.root, 'contracts/visual.json', 'evidence/dashboard.json', [], 'evidence/dashboard-coverage.json')
        result = v.load(self.root, 'evidence/dashboard-coverage.json')
        self.assertFalse(set(c['case_id'] for c in control['required_cases']) & set(result['pending_cases']))
        self.assertTrue(result['pending_cases'])


if __name__ == '__main__':
    unittest.main()
