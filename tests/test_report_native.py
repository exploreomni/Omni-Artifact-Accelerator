"""Original local evidence fixtures. No native API, renderer, user or publication claim."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


N = load('report_native_under_test', 'skills/omni-report-builder/scripts/report_native.py')
P, D = N.P, N.D
G = load('native_report_stage_fixture', 'tests/stage_gate_fixture.py')
F = load('native_report_contract_fixture', 'tests/test_report_contract.py')
S = load('native_report_source_fixture', 'tests/test_crystal_report.py')


def target():
    return {'surface': 'report', 'state': 'published', 'instance': 'https://report.example.invalid',
            'document_id': 'synthetic-report', 'draft_id': None,
            'capability_evidence_path': 'inputs/capability.txt'}


def prepare_spec():
    return {'definition_path': 'deliverables/definition.rdlx-json', 'definition_format': 'rdlx-json',
            'requirements_path': 'contracts/visual.json', 'builders': ['fixture-builder']}


def qualification_spec():
    return {'target': {'base_url': target()['instance'], 'document_id': target()['document_id']},
            'runtime_version': 'synthetic-runtime-1', 'schema_version': 'synthetic-schema-1',
            'definition_format': 'rdlx-json', 'schema_evidence_path': 'inputs/schema.json',
            'capability_evidence_path': 'inputs/capability.txt', 'reference': 'Original synthetic supplied observation; not authority'}


def observation_spec(operation='readback'):
    return {'candidate_path': 'deliverables/candidate.json', 'qualification_path': 'evidence/runtime.json',
            'operation': operation, 'status': 'completed',
            'definition_path': 'evidence/readback.rdlx-json' if operation == 'readback' else None,
            'output_format': None if operation == 'readback' else 'pdf',
            'export_path': None if operation == 'readback' else 'evidence/report.pdf',
            'context_path': 'evidence/context.json', 'evidence_path': 'evidence/native.txt',
            'reference': 'Synthetic retained event; no live execution occurred'}


def setup(root):
    """Complete synthetic A-F design prerequisite for root integration checks."""
    P.init(root, 'Synthetic report observation', 'net-new', 'report', 'none')
    life = G.Lifecycle(root, P)
    original = G.selected_handoff
    snapshot = S.snapshot_fixture()
    P.write_json(root / 'inputs/source.json', snapshot)
    P.write_json(root / 'inputs/source-inventory.json', S.T.translate((root / 'inputs/source.json').read_bytes(), 'crystal-report'))
    # Register only the fixed package module for the existing workflow loader.
    import sys
    previous = sys.modules.get('analyst_project'); sys.modules['analyst_project'] = P
    try:
        W = P.routing_helper('visual_workflow')
    finally:
        if previous is None: del sys.modules['analyst_project']
        else: sys.modules['analyst_project'] = previous
    W.prepare(root, 'inputs/source.json', 'inputs/source-inventory.json', 'contracts/visual.json')

    def handoff(directory, api, option, version=None):
        path = original(directory, api, option, version)
        spec = copy.deepcopy(D.load_selected(directory)['spec'])
        design = P.read_json(directory / path)[0]
        design['report_contract'] = F.fixture_v2(spec)
        P.write_json(directory / 'inputs/query.json', {'fixture_only': True, 'rows': 0})
        (directory / 'inputs/decision.txt').write_text('Synthetic report preferences only.')
        (directory / 'inputs/capability.txt').write_text('Synthetic native target evidence only.')
        P.write_json(directory / 'inputs/schema.json', {'synthetic_schema': True})
        P.write_json(directory / 'deliverables/definition.rdlx-json', {'synthetic_definition': True})
        spec['selections'][0].update(target=target(), candidate_path='deliverables/definition.rdlx-json')
        P.write_json(directory / path, design, replace=True)
        spec_path = 'contracts/native-selected-spec.json'; P.write_json(directory / spec_path, spec)
        D.select(directory, directory / spec_path, 'contracts/native-selected-intent.json')
        G.refresh_request_review(directory, api)
        return path

    with P.trusted_stage_provider(life.host), patch.object(G, 'selected_handoff', handoff):
        life.through('design')
        N.prepare(root, prepare_spec(), 'deliverables/candidate.json')
    N.qualify(root, qualification_spec(), 'evidence/runtime.json')
    (root / 'evidence/readback.rdlx-json').write_bytes((root / 'deliverables/definition.rdlx-json').read_bytes())
    P.write_json(root / 'evidence/results.json', {'synthetic': [], 'complete': False})
    P.write_json(root / 'evidence/context.json', {'principal_ref': 'fixture-reader', 'locale': 'en-US',
        'timezone': 'UTC', 'as_of': 'synthetic-unknown', 'parameter_values': {},
        'query_results': [{'dataset_id': 'observations', 'path': 'evidence/results.json',
                           'population_reference': 'Synthetic bounded results; no numeric acceptance'}], 'asset_paths': []})
    (root / 'evidence/native.txt').write_text('Supplied synthetic observation only.')
    (root / 'evidence/report.pdf').write_bytes(b'%PDF-1.7\nSynthetic signature only; not a rendered PDF.\n')
    return life


class ReportNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.base = Path(cls.tmp.name).resolve()
        cls.original = cls.base / 'original'; setup(cls.original)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def setUp(self):
        # Engagement identity is bound to its actual path; reuse and restore fixture bytes.
        self.root = self.original
        self.original_files = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.addCleanup(self.restore)

    def restore(self):
        for p in self.root.rglob('*'):
            if p.is_file() or p.is_symlink():
                if p not in self.original_files: p.unlink()
        for p, raw in self.original_files.items():
            if p.is_symlink(): p.unlink()
            p.write_bytes(raw)

    def observe(self, operation='readback', output=None):
        return N.observe(self.root, observation_spec(operation), output or 'evidence/' + operation + '.json')

    def test_prepare_does_not_compile_or_confer_native_authority(self):
        value = N.check_candidate(self.root, 'deliverables/candidate.json')
        self.assertFalse(value['compiled']); self.assertFalse(value['native_authoring_qualified'])
        self.assertFalse(value['external_mutations_authorized'])
        self.assertEqual(len(value['obligations']), 3)
        other = self.base / 'too-early'; P.init(other, 'Synthetic early', 'net-new', 'report', 'none')
        with self.assertRaisesRegex(ValueError, 'workflow_startup_missing|stage_gate_'):
            N.prepare(other, prepare_spec(), 'deliverables/no.json')
        self.assertFalse((other / 'deliverables/no.json').exists())

    def test_schema_runtime_evidence_is_not_an_authority_flag(self):
        value = N.check_qualification(self.root, 'evidence/runtime.json')
        self.assertFalse(value['native_execution_qualified'])
        for changed in ({**qualification_spec(), 'approved': True},
                        {**qualification_spec(), 'definition_format': 'rdl'},
                        {**qualification_spec(), 'definition_format': 'rdlc'},
                        {**qualification_spec(), 'runtime_version': 'unverified'},
                        {**qualification_spec(), 'target': {'base_url': 'https://user:secret@example.invalid', 'document_id': 'x'}}):
            with self.assertRaises(ValueError): N.qualify(self.root, changed, 'evidence/bad.json')
        (self.root / 'inputs/schema.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'runtime_evidence_changed'): N.check_qualification(self.root, 'evidence/runtime.json')

    def test_matching_supplied_readback_is_not_execution_or_access_proof(self):
        value = self.observe()
        self.assertEqual(value['status'], 'readback_matched')
        self.assertFalse(value['claims_authenticated']); self.assertFalse(value['native_verified'])
        (self.root / 'evidence/readback.rdlx-json').write_text('{"different":true}')
        with self.assertRaisesRegex(ValueError, 'observation_or_context_changed'): N.check_observation(self.root, 'evidence/readback.json')
        other = self.observe(output='evidence/conflict.json')
        self.assertEqual(other['status'], 'readback_conflict'); self.assertFalse(other['replay_allowed'])

    def test_metadata_paths_and_credentials_remain_bounded(self):
        request = qualification_spec(); request['reference'] = 'Bearer test-secret-token-value'
        with self.assertRaisesRegex(ValueError, 'credential_metadata_forbidden'):
            N.qualify(self.root, request, 'evidence/bad.json')
        request = qualification_spec(); request['schema_evidence_path'] = '../outside.json'
        with self.assertRaises(ValueError): N.qualify(self.root, request, 'evidence/bad.json')
        with self.assertRaises(ValueError): N.qualify(self.root, qualification_spec(), '../outside.json')
        (self.root / 'evidence/duplicate.json').write_text('{"value":1,"value":2}')
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'): N.read(self.root, 'evidence/duplicate.json')

    def test_uncertain_receipts_and_local_candidates_cannot_become_native_delivery(self):
        request = observation_spec(); request['status'] = 'uncertain'
        N.observe(self.root, request, 'evidence/readback.json')
        N.coverage(self.root, 'deliverables/candidate.json', ['evidence/readback.json'], [], 'evidence/coverage.json')
        with self.assertRaisesRegex(ValueError, 'delivery_matched_readback_required'):
            N.verify_delivery(self.root, {'candidate_path': 'deliverables/candidate.json',
                'execution_receipt_path': 'evidence/readback.json', 'coverage_path': 'evidence/coverage.json'})

    def test_candidate_query_context_and_source_symlink_changes_reject(self):
        self.observe()
        (self.root / 'inputs/query.json').write_text('{"rows":1}')
        with self.assertRaises(ValueError): N.check_candidate(self.root, 'deliverables/candidate.json')
        self.restore(); self.observe()
        (self.root / 'evidence/results.json').write_text('{"other":true}')
        with self.assertRaisesRegex(ValueError, 'observation_or_context_changed'): N.check_observation(self.root, 'evidence/readback.json')
        self.restore()
        path = self.root / 'evidence/readback.rdlx-json'; path.unlink()
        path.symlink_to(self.root / 'deliverables/definition.rdlx-json')
        with self.assertRaisesRegex(ValueError, 'symlink'): self.observe()

    def test_observation_requires_exact_target_context_and_complete_parameter_ids(self):
        value = N.read(self.root, 'evidence/context.json'); value['parameter_values'] = {'invented': 1}
        P.write_json(self.root / 'evidence/context.json', value, replace=True)
        with self.assertRaisesRegex(ValueError, 'parameter_values_incomplete'): self.observe()
        self.restore(); value = N.read(self.root, 'evidence/context.json'); value['query_results'] = []
        P.write_json(self.root / 'evidence/context.json', value, replace=True)
        with self.assertRaisesRegex(ValueError, 'query_result_dataset_scope'): self.observe()

    def test_export_bytes_never_prove_rendering_or_numerical_quality(self):
        export = self.observe('export')
        self.assertEqual(export['status'], 'completed'); self.assertFalse(export['native_verified'])
        N.coverage(self.root, 'deliverables/candidate.json', ['evidence/export.json'], [], 'evidence/coverage.json')
        self.assertEqual(len(N.check_coverage(self.root, 'evidence/coverage.json')['pending_cases']), 3)
        bad = {'id': 'overflow', 'outcome': 'pass', 'basis': 'source', 'observation_path': 'evidence/export.json',
               'evidence_paths': ['evidence/native.txt'], 'reviewer': 'fixture-qa', 'notes': 'Source review only'}
        with self.assertRaisesRegex(ValueError, 'qa_basis_insufficient'):
            N.coverage(self.root, 'deliverables/candidate.json', ['evidence/export.json'], [bad], 'evidence/bad.json')
        bad.update(basis='rendered', reviewer='fixture-builder')
        with self.assertRaisesRegex(ValueError, 'independent_reviewer_required'):
            N.coverage(self.root, 'deliverables/candidate.json', ['evidence/export.json'], [bad], 'evidence/bad.json')

    def test_delivery_recomputes_all_pins_and_preserves_unqualified_gaps(self):
        self.observe(); self.observe('export')
        N.coverage(self.root, 'deliverables/candidate.json', ['evidence/readback.json', 'evidence/export.json'], [], 'evidence/coverage.json')
        delivery = {'candidate_path': 'deliverables/candidate.json', 'execution_receipt_path': 'evidence/readback.json',
                    'coverage_path': 'evidence/coverage.json'}
        proof = N.verify_delivery(self.root, delivery)
        self.assertEqual(proof['surface'], 'report'); self.assertFalse(proof['migration_accepted'])
        self.assertIn('report_native_execution_unqualified', {g.get('code') for g in proof['gaps']})
        self.assertEqual(sum(g.get('code') == 'pending_report_case' for g in proof['gaps']), 3)
        self.assertIn('report_source_binding_unqualified', {g.get('code') for g in proof['gaps']})
        self.assertIn('pending_report_source_parity', {g.get('code') for g in proof['gaps']})
        self.assertIn('report_source_defer', {g.get('code') for g in proof['gaps']})
        self.assertIn('report_source_gap', {g.get('code') for g in proof['gaps']})
        value = N.read(self.root, 'evidence/coverage.json'); value['pending_cases'] = []
        P.write_json(self.root / 'evidence/coverage.json', N.seal({k:v for k,v in value.items() if k!='sha256'}), replace=True)
        with self.assertRaisesRegex(ValueError, 'coverage_changed'): N.verify_delivery(self.root, delivery)

    def test_original_source_and_removed_migration_cases_invalidate_candidate(self):
        value = N.read(self.root, 'contracts/visual.json')
        next(item for item in value['items'] if item['required_cases'])['required_cases'] = []
        P.write_json(self.root / 'contracts/visual.json', value, replace=True)
        with self.assertRaisesRegex(ValueError, 'required_cases_removed'):
            N.check_candidate(self.root, 'deliverables/candidate.json')
        self.restore()
        value = N.read(self.root, 'inputs/source.json'); value['identity']['principal_ref'] = 'different-supplier'
        P.write_json(self.root / 'inputs/source.json', value, replace=True)
        with self.assertRaises(ValueError): N.check_candidate(self.root, 'deliverables/candidate.json')


if __name__ == '__main__': unittest.main()
