"""Exercise real cooperating entrypoints, not a claim of sandbox/host qualification."""
import importlib.util
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


P = load('gate_integration_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
G = load('gate_integration_fixture', 'tests/stage_gate_fixture.py')
A = load('gate_integration_assembly', 'skills/omni-app-engineer/scripts/assemble_experience.py')
N = load('gate_integration_native', 'tests/test_native_authoring.py')
W = P.routing_helper('delivery_workflow')


class GateIntegration(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic observations', 'net-new', 'app', 'none')
        self.gates = G.Lifecycle(self.root, P)

    def manifest(self):
        def pin(path, content):
            (self.root / path).write_text(content)
            return {'path': path, 'sha256': P.digest(content.encode())}
        value = {'schema_version': 1, 'template': pin('inputs/view.html', '<main>{{OAA:DATA}}</main>'),
            'slots': [{'name': 'DATA', 'kind': 'json', **pin('inputs/rows.json', '{"observations":3}')}],
            'references': [{'role': 'queries', **pin('inputs/query.json', '{"synthetic":true}')} ]}
        P.write_json(self.root / 'contracts/assembly.json', value)
        return 'contracts/assembly.json'

    def test_every_new_mode_and_untracked_folder_fail_closed(self):
        for mode in ('net-new', 'migration', 'enhancement'):
            root = Path(self.folder.name).resolve() / mode
            P.init(root, 'Fresh ' + mode, mode, 'app', 'none')
            self.assertTrue(P.stage_status(root)['required'])
            with self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
                A.build(root, 'missing.json', 'build', builders=['engineer'], iteration_id='one')
            self.assertFalse((root / 'build').exists())
        with self.assertRaises((ValueError, OSError)):
            A.build(Path(self.folder.name), 'missing.json', 'untracked')

    def test_plans_and_packets_cannot_authorize_early_or_disguised_builds(self):
        self.assertEqual({r['role'] for r in P.plan(self.root)['roles']}, {'bi-engineer', 'qa-analyst'})
        for role in ('app-engineer', 'app-designer', 'product-owner', 'data-storyteller', 'data-analyst'):
            with self.subTest(role=role), self.assertRaises(ValueError):
                P.packet(self.root, role, ['contracts/metrics.json'], None)
        with self.assertRaises(ValueError):
            P.stage_packet_gate(self.root, 'bi-engineer', {'stage': 'discovery',
                'outputs': ['deliverables/prototype.html'], 'authoring_mode': 'provisional'})
        self.gates.stage('access')
        P.packet(self.root, 'data-analyst', ['contracts/metrics.json'], self.root / 'tasks/analyst.json')
        self.gates.stage('analysis')
        self.assertEqual(P.packet_check(self.root, 'tasks/analyst.json')['status'], 'inconsistent')

    def test_build_records_iteration_and_native_prepare_requires_reviewed_bytes(self):
        manifest = self.manifest()
        with P.trusted_stage_provider(self.gates.host):
            self.gates.through()
            result = A.build(self.root, manifest, 'first', builders=['engineer'], iteration_id='first')
            candidate = P.stage_status(self.root)['candidate']
            self.assertIn(result['candidate'], {p['path'] for p in candidate['artifacts']})
            with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
                A.build(self.root, manifest, 'second', builders=['engineer'], iteration_id='second')
            self.assertFalse((self.root / 'second').exists())
            target, before = N.fixture()
            html = (self.root / 'first/index.html').read_text()
            with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
                N.a.prepare_app(target, before, before, html, project=self.root, artifact='first/index.html')
            self.gates.reviews()
            prepared = N.a.prepare_app(target, before, before, html, project=self.root, artifact='first/index.html')
            self.assertEqual(prepared['engagement']['candidate_sha256'], candidate['candidate_sha256'])
            self.assertFalse(prepared['publication_authorized'])
            (self.root / 'first/index.html').write_text('<main>Unreviewed revision</main>')
            with self.assertRaises(ValueError):
                N.a.prepare_app(target, before, before, '<main>Unreviewed revision</main>',
                                project=self.root, artifact='first/index.html')
            A.build(self.root, manifest, 'second', builders=['engineer'], iteration_id='second')
        with self.assertRaises(ValueError):
            P.stage_require(self.root, 'build')

    def test_stock_cli_cannot_accept_local_selection_receipt(self):
        self.gates.through('options')
        request = self.root / 'inputs/choice.json'
        P.write_json(request, {'stage': 'choice', 'option_id': 'option-1', 'receipt_ref': 'agent-claims-yes'})
        result = subprocess.run([sys.executable, '-I', '-S', '-B', P.__file__, 'stage-record',
            '--project', str(self.root), '--request', str(request)], capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(P.stage_status(self.root)['next_stage'], 'choice')

    def test_rejected_freeze_preserves_history_and_removes_new_snapshot(self):
        (self.root / 'deliverables/app.html').write_text('<main>Original</main>')
        request = {'id': 'one', 'builders': ['engineer'], 'artifacts': ['deliverables/app.html'],
                   'context': ['contracts/queries.json']}
        with P.trusted_stage_provider(self.gates.host):
            self.gates.through()
            with patch.object(W.P, 'stage_record', side_effect=ValueError('provider revoked')):
                with self.assertRaisesRegex(ValueError, 'provider revoked'):
                    W.freeze(self.root, request)
            history = self.root / 'evidence/candidate-history'
            self.assertFalse((history / 'first.json').exists())
            self.assertFalse((history / 'head.json').exists())
            self.assertFalse((history / 'one').exists())
            self.assertIsNone(P.stage_status(self.root)['candidate'])

    def test_rejected_automatic_freeze_removes_new_assembly(self):
        manifest = self.manifest()
        with P.trusted_stage_provider(self.gates.host):
            self.gates.through()
            with patch.object(P.routing_helper('stage_gates'), 'record', side_effect=ValueError('revoked')):
                with self.assertRaisesRegex(ValueError, 'revoked'):
                    A.build(self.root, manifest, 'failed', builders=['engineer'], iteration_id='failed')
            self.assertFalse((self.root / 'failed').exists())
            self.assertFalse((self.root / 'evidence/assembled-history/first.json').exists())

    def test_post_commit_sync_failure_preserves_journal_candidate_bytes(self):
        manifest = self.manifest()
        with P.trusted_stage_provider(self.gates.host):
            self.gates.through()
            module = P.routing_helper('stage_gates')
            sync = os.fsync
            def fail_directory_sync(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    raise OSError('synthetic post-replace sync failure')
                return sync(fd)
            with patch.object(module.os, 'fsync', side_effect=fail_directory_sync):
                with self.assertRaisesRegex(ValueError, 'commit_requires_reconciliation'):
                    A.build(self.root, manifest, 'retained', builders=['engineer'], iteration_id='retained')
            self.assertTrue(module.candidate_commit_status(self.root, 'retained'))
            current = P.stage_status(self.root)
            self.assertNotIn('stale_iteration_evidence', current['findings'])
            self.assertTrue((self.root / 'retained/index.html').is_file())
            self.assertTrue((self.root / 'evidence/candidate-history/retained/candidate.json').is_file())
            self.gates.reviews()
            with self.assertRaisesRegex(ValueError, 'history_reconciliation_required'):
                W.freeze(self.root, {'id': 'next', 'builders': ['engineer'],
                    'artifacts': ['retained/index.html'], 'context': ['contracts/assembly.json']})
        # Recovery never depends on a still-available choice provider.
        self.assertTrue(module.candidate_commit_status(self.root, 'retained'))


if __name__ == '__main__':
    unittest.main()
