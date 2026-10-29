"""Neutral report geometry and evidence checks, no native/rendering claim."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    loader = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(loader); loader.loader.exec_module(result)
    return result


P = load('report_contract_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
R = load('report_contract_check', 'skills/omni-artifact-accelerator/scripts/report_contract.py')
F = load('report_contract_quality', 'tests/test_experience_contract.py')


def fixture():
    return {'schema_version': 1,
        'profile': {'release_label': 'Beta', 'runtime_version': 'unverified',
                    'authoring_route': 'unverified', 'evidence_path': None},
        'paper': {'unit': 'mm', 'width': 210, 'height': 297, 'orientation': 'portrait',
            'margins': {'top': 15, 'right': 15, 'bottom': 15, 'left': 15},
            'header_height': 12, 'footer_height': 10, 'page_numbering': 'Page n of N', 'layout_mode': 'flow'},
        'datasets': [{'id': 'observations', 'query_path': 'inputs/query.json', 'grain': 'One row per garden',
            'sort': 'Stable garden key ascending', 'filter_scope': 'Selected period before aggregation',
            'totals': 'Sum observed amount, preserve nulls',
            'fields': [{'id': 'garden.id', 'report_name': 'garden_key', 'type': 'string'},
                       {'id': 'garden.amount', 'report_name': 'amount', 'type': 'decimal'}]}],
        'parameters': [],
        'sections': [{'id': 'table', 'destination_id': 'main', 'dataset_id': 'observations', 'width': 180,
            'columns': [{'id': 'key', 'field_id': 'garden.id', 'width': 100, 'format': 'text', 'long_text': 'wrap'},
                        {'id': 'amount', 'field_id': 'garden.amount', 'width': 80, 'format': '0.00', 'long_text': 'wrap'}],
            'grouping': 'None', 'repeat_headers': 'Every continued page', 'keep_together': 'Keep labels with first row',
            'page_breaks': 'Flow after printable body', 'overflow': 'Continue rows; no truncation', 'empty_state': 'No observations'}],
        'outputs': [{'id': 'pdf', 'format': 'pdf', 'capability_id': 'pdf-output', 'pagination': 'Physical page size',
                     'sheet_policy': 'Not applicable to PDF', 'filename_policy': 'Period and report ID'}],
        'data_policy': {'locale': 'en-US', 'timezone': 'UTC', 'as_of': 'Show actual data timestamp',
            'caching': 'Keep existing Omni policy', 'refresh': 'No automatic refresh requested',
            'distribution': 'No sends or schedules requested', 'decision_ref': 'inputs/decision.txt'},
        'asset_ids': [],
        'capabilities': [{'id': 'pdf-output', 'requirement_ids': ['quality'], 'behavior': 'Export paginated PDF',
            'status': 'unverified', 'evidence_path': None, 'disposition': 'native', 'decision_ref': None}],
        'acceptance': [{'id': 'values', 'output_format': 'pdf', 'lane': 'numerical',
                        'scenario': 'All rows and total', 'expected': 'Reconcile independent source values'},
                       {'id': 'overflow', 'output_format': 'pdf', 'lane': 'pagination',
                        'scenario': 'First overflowing row', 'expected': 'New page repeats heading and preserves row'},
                       {'id': 'export', 'output_format': 'pdf', 'lane': 'export',
                        'scenario': 'Final exported file', 'expected': 'Expected page geometry with no clipping'}]}


def fixture_v2(spec=None):
    value = fixture(); value['schema_version'] = 2
    requirements = [r for r in (spec or F.specimen(['report']))['requirements'] if 'report' in r['surfaces']]
    value['capabilities'][0]['requirement_ids'] = [r['id'] for r in requirements]
    for case in value['acceptance']: case.update(section_ids=['table'], parameter_ids=[])
    value['requirement_bindings'] = [
        {'id': 'mapping-' + str(i), 'requirement_id': r['id'], 'section_ids': ['table'], 'parameter_ids': [],
         'output_ids': ['pdf'], 'acceptance_ids': [c['id'] for c in value['acceptance']],
         'disposition': 'implemented', 'decision_ref': None} for i, r in enumerate(requirements)]
    return value


class ReportContractTests(unittest.TestCase):
    def setUp(self):
        self.spec = F.specimen(['report']); self.design = F.design()
        self.design['destinations'][0]['surface'] = 'report'
        self.design['report_contract'] = fixture()

    def check(self, value=None):
        return R.validate(value or self.design['report_contract'], self.spec, self.design['destinations'])

    def test_page_geometry_and_unverified_capability_remain_separate(self):
        result = self.check()
        self.assertEqual((result['printable_width'], result['printable_height']), (180, 245))
        self.assertEqual(result['gaps'][0]['status'], 'unverified')
        self.assertFalse(result['native_authoring_qualified'])
        self.assertEqual(result['rendered_quality'], 'not_assessed')

    def test_impossible_page_and_column_geometry_rejects(self):
        mutations = [lambda c: c['paper'].update(width=True), lambda c: c['paper'].update(width=float('nan')),
                     lambda c: c['paper']['margins'].update(left=220),
                     lambda c: c['paper'].update(orientation='landscape'),
                     lambda c: c['sections'][0].update(width=181),
                     lambda c: c['sections'][0]['columns'][0].update(width=101)]
        for change in mutations:
            value = fixture(); change(value)
            with self.subTest(value=value), self.assertRaises(ValueError): self.check(value)

    def test_static_cover_does_not_need_fictitious_data_binding(self):
        value = fixture(); value['sections'][0].update(dataset_id=None, columns=[])
        value['datasets'] = []
        self.assertEqual(self.check(value)['printable_width'], 180)
        value['sections'][0]['columns'] = fixture()['sections'][0]['columns']
        with self.assertRaisesRegex(ValueError, 'static_section_cannot_claim_data_columns'): self.check(value)

    def test_missing_field_dataset_and_report_destination_reject(self):
        for key, val in [('dataset_id', 'missing'), ('destination_id', 'missing')]:
            value = fixture(); value['sections'][0][key] = val
            with self.assertRaises(ValueError): self.check(value)
        value = fixture(); value['sections'][0]['columns'][0]['field_id'] = 'invented'
        with self.assertRaises(ValueError): self.check(value)
        self.design['destinations'].append({'id': 'missing', 'surface': 'report'})
        with self.assertRaisesRegex(ValueError, 'destinations_uncovered'): self.check()

    def test_format_obligations_cannot_silently_disappear(self):
        value = fixture(); extra = copy.deepcopy(value['outputs'][0]); extra.update(id='excel', format='xlsx')
        value['outputs'].append(extra)
        with self.assertRaisesRegex(ValueError, 'acceptance_coverage'): self.check(value)
        value['acceptance'].append({'id': 'excel-export', 'output_format': 'xlsx', 'lane': 'export',
            'scenario': 'Excel output', 'expected': 'Correct worksheet names and types'})
        with self.assertRaisesRegex(ValueError, 'acceptance_coverage'): self.check(value)
        value['acceptance'].append({'id': 'excel-values', 'output_format': 'xlsx', 'lane': 'numerical',
            'scenario': 'Excel output', 'expected': 'Independent total reconciles every row'})
        self.assertFalse(self.check(value)['native_authoring_qualified'])
        value = fixture(); value['outputs'][0]['capability_id'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'output_capability_missing'): self.check(value)

    def test_v2_maps_actual_parts_and_legacy_is_readable_not_qualified(self):
        self.assertFalse(self.check()['requirement_mapping_qualified'])
        self.assertIn('legacy_report_contract_mapping_unqualified', {g.get('code') for g in self.check()['gaps']})
        value = fixture_v2(self.spec)
        self.assertTrue(self.check(value)['requirement_mapping_qualified'])
        self.assertEqual(R.obligations(value)[0]['requirement_ids'], ['quality'])
        for target, replacement in [('section_ids', ['not-a-section']), ('acceptance_ids', []), ('output_ids', [])]:
            changed = copy.deepcopy(value); changed['requirement_bindings'][0][target] = replacement
            with self.subTest(target=target), self.assertRaises(ValueError): self.check(changed)

    def test_v2_requires_every_format_to_cover_actual_parts(self):
        value = fixture_v2(self.spec)
        extra = copy.deepcopy(value['outputs'][0]); extra.update(id='sheet', format='xlsx'); value['outputs'].append(extra)
        value['acceptance'].extend([dict(c, id='xlsx-' + c['id'], output_format='xlsx', section_ids=[])
                                    for c in value['acceptance'] if c['lane'] != 'pagination'])
        binding = value['requirement_bindings'][0]
        binding['output_ids'].append('sheet'); binding['acceptance_ids'] = [c['id'] for c in value['acceptance']]
        with self.assertRaisesRegex(ValueError, 'per_format_part_acceptance_uncovered'): self.check(value)
        for case in value['acceptance']: case['section_ids'] = ['table']
        self.assertTrue(self.check(value)['requirement_mapping_qualified'])

    def test_v2_cannot_hide_required_behavior_with_local_deferred_flag(self):
        value = fixture_v2(self.spec); mapping = value['requirement_bindings'][0]
        mapping.update(disposition='deferred', decision_ref='inputs/invented.txt', section_ids=[], output_ids=[], acceptance_ids=[])
        with self.assertRaisesRegex(ValueError, 'matching_actual_decision'): self.check(value)

    def test_required_report_requirement_cannot_be_omitted_from_capabilities(self):
        req = copy.deepcopy(self.spec['requirements'][0]); req['id'] = 'conditional-section'
        self.spec['requirements'].append(req)
        with self.assertRaisesRegex(ValueError, 'required_report_capabilities_uncovered'): self.check()
        self.design['report_contract']['capabilities'][0]['requirement_ids'].append(req['id'])
        self.assertEqual(self.check()['gaps'][0]['status'], 'unverified')

    def test_declared_native_capabilities_need_evidence_and_never_grant_authority(self):
        value = fixture(); value['capabilities'][0]['status'] = 'observed'
        with self.assertRaisesRegex(ValueError, 'capability_evidence_required'): self.check(value)
        value['capabilities'][0]['evidence_path'] = 'inputs/native.txt'
        self.assertFalse(self.check(value)['native_authoring_qualified'])
        value['capabilities'][0].update(status='unsupported', disposition='deferred')
        with self.assertRaisesRegex(ValueError, 'actual_decision'): self.check(value)

    def prepare_files(self, root):
        for name in ('inputs', 'contracts', 'concepts'): (root / name).mkdir()
        (root / 'inputs/query.json').write_text('{"fixture_only":true,"rows":0}')
        (root / 'inputs/decision.txt').write_text('Synthetic preferences only; no real approval.')
        (root / 'concepts/a.svg').write_text(F.SVG)
        P.write_json(root / 'concepts/a.json', F.concept('report'))
        P.write_json(root / 'contracts/design.json', self.design)

    def test_selected_handoff_pins_queries_and_decisions_and_preserves_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); self.prepare_files(root)
            result = P.routing_helper('experience_contract').validate_handoff(root, 'contracts/design.json', self.spec, P)
            paths = {p['path']: p['sha256'] for p in result['dependencies']}
            self.assertIn('inputs/query.json', paths); self.assertIn('inputs/decision.txt', paths)
            self.assertFalse(result['metadata']['report_native_authoring_qualified'])
            self.assertEqual(result['metadata']['report_capability_gaps'][0]['status'], 'unverified')
            (root / 'inputs/query.json').write_text('{"fixture_only":true,"rows":1}')
            changed = P.routing_helper('experience_contract').validate_handoff(root, 'contracts/design.json', self.spec, P)
            self.assertNotEqual(paths['inputs/query.json'], {p['path']:p['sha256'] for p in changed['dependencies']}['inputs/query.json'])

    def test_report_handoff_cannot_omit_contract_or_follow_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); self.prepare_files(root)
            self.design.pop('report_contract'); P.write_json(root / 'contracts/design.json', self.design, replace=True)
            with self.assertRaisesRegex(ValueError, 'contract_fields'):
                P.routing_helper('experience_contract').validate_handoff(root, 'contracts/design.json', self.spec, P)
            self.design['report_contract'] = fixture()
            (root / 'inputs/query.json').unlink(); (root / 'inputs/query.json').symlink_to(root / 'inputs/decision.txt')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                R.validate_handoff(root, self.design, self.spec, P)


if __name__ == '__main__': unittest.main()
