"""Synthetic local source/startup fixtures; no actual host or source checkout calls."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

_spec = importlib.util.spec_from_file_location('bootstrap_tests', Path(__file__).resolve().parents[1] /
    'skills/omni-artifact-accelerator/scripts/engagement_bootstrap.py')
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
P, W = B.P, B.W


class EngagementBootstrapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name).resolve()
        self.package, self.root = self.parent / 'package', self.parent / 'engagement'
        self.package.mkdir()
        for path in (B.ENTRY, B.PROCEDURE, B.HELPER, 'skills/omni-data-analyst/SKILL.md', 'AGENTS.md', 'CLAUDE.md'):
            target = self.package / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('Synthetic first-party entry fixture: ' + path + '\n')
        (self.package / 'package.json').write_text('{"name":"synthetic-entry","version":"1.0.0"}')
        P.init(self.root, 'Synthetic sibling entry', 'net-new', 'app', branding='none')
        (self.root / 'inputs/brief.txt').write_text('Retain this original supplied brief.\n')
        (self.root / 'contracts/execution.json').write_text(json.dumps({'responsibilities': {'semantics': {
            'role': 'data-analyst', 'worker': 'analyst', 'mode': 'inline', 'rationale': 'Original local fixture'}}}))
        self.git = {'head': 'a' * 40, 'status': ''}
        for patcher in (mock.patch.object(W, 'source_root', return_value=self.package),
                        mock.patch.object(W, 'git_identity', side_effect=lambda package: copy.deepcopy(self.git)),
                        mock.patch.object(P, 'stage_status', return_value={'status': 'incomplete', 'next_stage': 'access', 'completed_stages': []})):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.request = {'schema_version': 1, 'id': 'first-entry',
            'host': {'name': 'Supplied host', 'execution_mode': 'instruction_guided',
                     'tools': ['approved_local_read', 'approved_local_helper'], 'constraints': ['No external writes']},
            'startup': {'brief': 'inputs/brief.txt', 'execution': 'contracts/execution.json',
                        'source_expectation': {'kind': 'current_checkout'}}}

    def prepare(self):
        return B.prepare(self.root, self.request)

    def start(self, result, **changes):
        record = P.read_json(self.root / result['record']['path'])[0]
        request = B.startup_request(record)
        request['loaded_guidance'] = [B.ENTRY, 'skills/omni-data-analyst/SKILL.md']
        request.update(changes)
        return W.start(self.root, request)

    def source_receipt(self, minutes_ago=0):
        path = 'evidence/source-check-fixture.json'
        P.write_json(self.root / path, {'schema_version': 1, 'kind': 'analyst_source_check',
            'project_id': P.load_project(self.root)[1]['id'], 'package_root': str(self.package),
            'revision': self.git['head'], 'ref': 'refs/heads/main',
            'checked_at': (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()}, replace=(self.root / path).exists())
        return path

    def test_missing_startup_is_actionable_private_and_does_not_install(self):
        protected = {path: path.read_bytes() for path in (self.root / 'START_HERE.md', self.package / 'AGENTS.md', self.package / 'CLAUDE.md')}
        result = self.prepare()
        self.assertEqual(result['status'], 'not_ready')
        self.assertEqual(result['workflow_observed']['startup_status'], 'missing')
        self.assertIn('startup_missing', result['findings'])
        self.assertEqual(result['next_actions'][0]['code'], 'record_startup')
        folder = self.root / Path(result['record']['path']).parent
        self.assertEqual(P.read_json(folder / 'STARTUP_REQUEST.json')[0]['loaded_guidance'], [])
        self.assertIn(str(self.package / B.ENTRY), (folder / 'START_HERE.md').read_text())
        self.assertEqual({path: path.read_bytes() for path in protected}, protected)
        self.assertEqual((folder / 'ENTRY.json').stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(self.root.glob('evidence/run-*.json')))
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['host_authority']['enforcement'], 'not_qualified')

    def test_exact_retry_reuses_files_and_rejects_changed_declaration(self):
        first = self.prepare()
        path = self.root / first['record']['path']
        before = path.read_bytes(), path.stat().st_mtime_ns
        repeated = self.prepare()
        self.assertEqual(repeated['record'], first['record'])
        self.assertEqual(repeated['preparation'], 'reused')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertEqual(len(list(self.parent.iterdir())), 2)
        self.request['host']['tools'].append('different_tool')
        with self.assertRaisesRegex(ValueError, 'immutable_entry_exists'):
            self.prepare()

    def test_actual_existing_startup_must_match_declared_host_and_paths(self):
        result = self.prepare()
        self.start(result)
        checked = B.check(self.root, {'record': result['record']})
        self.assertEqual(checked['status'], 'entry_current')
        self.assertEqual(checked['workflow_observed']['startup_status'], 'matching_local_record')
        self.assertEqual(checked['workflow_observed']['phase_status'], 'ready')
        self.assertEqual(checked['host_authority']['loading'], 'not_observed')
        self.assertFalse(checked['publication_authorized'])

    def test_an_unrelated_valid_startup_is_not_accepted(self):
        result = self.prepare()
        wrong = copy.deepcopy(self.request['host'])
        wrong['tools'] = ['different_approved_tool']
        self.start(result, host=wrong)
        checked = B.check(self.root, {'record': result['record']})
        self.assertEqual(checked['status'], 'not_ready')
        self.assertIn('startup_invalid_or_different_binding', checked['findings'])

    def test_stage_repair_is_not_misreported_as_missing_or_invalid_startup(self):
        result = self.prepare()
        self.start(result)
        with mock.patch.object(P, 'stage_status', return_value={'status': 'blocked', 'next_stage': 'repair_state', 'completed_stages': []}):
            checked = B.check(self.root, {'record': result['record']})
        self.assertEqual(checked['status'], 'not_ready')
        self.assertEqual(checked['workflow_observed']['startup_status'], 'matching_local_record')
        self.assertIn('stage_state_requires_repair', checked['findings'])

    def test_unresolved_phase_ownership_is_not_ready(self):
        (self.root / 'contracts/execution.json').write_text('{"responsibilities":{}}')
        result = self.prepare()
        self.start(result)
        checked = B.check(self.root, {'record': result['record']})
        self.assertEqual(checked['workflow_observed']['phase_status'], 'blocked')
        self.assertEqual(checked['workflow_observed']['startup_status'], 'matching_local_record')
        self.assertIn('phase_requirements_pending', checked['findings'])

    def test_current_checkout_drift_invalidates_record_without_updating_it(self):
        result = self.prepare()
        original = (self.root / result['record']['path']).read_bytes()
        (self.package / B.ENTRY).write_text('Changed source entry\n')
        checked = self.prepare()
        self.assertIn('package_source_changed', checked['findings'])
        self.assertEqual(checked['package_check']['status'], 'changed')
        self.assertEqual((self.root / result['record']['path']).read_bytes(), original)

    def test_pinned_revision_reuses_existing_clean_checkout_rules(self):
        self.request['startup']['source_expectation'] = {'kind': 'pinned_revision', 'revision': self.git['head']}
        self.git['status'] = ' M synthetic'
        with self.assertRaisesRegex(ValueError, 'source_expectation_not_satisfied'):
            self.prepare()
        self.git['status'] = ''
        result = self.prepare()
        self.git['head'] = 'b' * 40
        self.assertIn('package_source_changed', B.check(self.root, {'record': result['record']})['findings'])

    def test_offline_entry_retains_exact_manifest_expectation(self):
        self.request['startup']['source_expectation'] = {'kind':'offline_snapshot',
            'manifest_sha256':P.digest(P.canonical(W.source_manifest(self.package)))}
        result = self.prepare()
        self.start(result)
        checked = B.check(self.root, {'record':result['record']})
        self.assertEqual(checked['package_check']['source_expectation'], 'offline_snapshot')
        self.assertEqual(checked['status'], 'entry_current')

    def test_host_entry_receipt_is_bound_to_startup_and_rechecked(self):
        helper = W.host_entry_helper()
        request = {'schema_version':1,'id':'host-entry','host':self.request['host'],
                   'loaded_package_path':str(self.package),
                   'source_expectation':self.request['startup']['source_expectation'],
                   'routes':[{'kind':kind,'name':kind,'availability':'unknown'} for kind in helper.ROUTES]}
        with mock.patch.object(helper, 'W', W), mock.patch.object(helper, 'P', P), \
                mock.patch.object(W, 'host_entry_helper', return_value=helper):
            pointer = helper.prepare(self.root,request)['record']
            self.request['host_entry'] = pointer
            result = self.prepare()
            self.start(result)
            checked = B.check(self.root, {'record':result['record']})
            self.assertEqual(checked['status'],'entry_current')
            self.assertEqual(checked['host_entry']['host_boundary']['mode'],'advisory')
            (self.root/pointer['path']).write_text('{}')
            self.assertIn('host_entry_changed_or_unavailable', B.check(self.root,{'record':result['record']})['findings'])

    def test_latest_source_check_is_reused_without_network_or_renewed_age_on_inspection(self):
        verification = self.source_receipt()
        self.request['startup']['source_expectation'] = {'kind': 'latest_main', 'revision': self.git['head'], 'verification_path': verification}
        with mock.patch.object(W.subprocess, 'run', side_effect=AssertionError('No network or Git subprocess in fixture')):
            result = self.prepare()
            with mock.patch.object(W, 'source_expectation', side_effect=AssertionError('Check must not renew latest-main freshness')):
                checked = B.check(self.root, {'record': result['record']})
        self.assertEqual(checked['package_check']['status'], 'matching')
        self.assertEqual(checked['status'], 'not_ready')

    def test_expired_latest_source_receipt_rejects_new_preparation(self):
        verification = self.source_receipt(minutes_ago=11)
        self.request['startup']['source_expectation'] = {'kind': 'latest_main', 'revision': self.git['head'], 'verification_path': verification}
        with self.assertRaisesRegex(ValueError, 'source_expectation_not_satisfied'):
            self.prepare()
        self.assertFalse((self.root / 'evidence/entry-first-entry').exists())

    def test_changed_brief_or_execution_is_not_a_current_entry(self):
        result = self.prepare()
        (self.root / 'inputs/brief.txt').write_text('Different original request\n')
        checked = B.check(self.root, {'record': result['record']})
        self.assertIn('startup_inputs_changed_or_unavailable', checked['findings'])

    def test_supplied_runtime_evidence_never_authenticates_host(self):
        path = 'evidence/runtime.txt'
        (self.root / path).write_text('Supplied runtime observation; no trusted attestation.\n')
        self.request['runtime_observation'] = {'path': path, 'sha256': P.digest(P.read_bytes(self.root / path))}
        result = self.prepare()
        self.assertEqual(result['host_authority']['runtime_observation'], 'supplied_evidence_only')
        self.assertEqual(result['host_authority']['enforcement'], 'not_qualified')
        (self.root / path).write_text('Changed supplied observation\n')
        self.assertIn('startup_inputs_changed_or_unavailable', B.check(self.root, {'record': result['record']})['findings'])

    def test_sibling_and_paths_are_required_and_errors_do_not_echo_input(self):
        self.request['startup']['brief'] = '../private-secret.txt'
        with self.assertRaisesRegex(ValueError, '^entry\\.') as caught:
            self.prepare()
        self.assertNotIn('private-secret', str(caught.exception))
        self.request['startup']['brief'] = 'inputs/brief.txt'
        other = self.parent / 'nested'
        other.mkdir()
        nested = other / 'engagement'
        P.init(nested, 'Nested fixture', 'enhancement', 'app', branding='none')
        with self.assertRaisesRegex(ValueError, 'sibling_engagement_required'):
            B.prepare(nested, self.request)

    def test_retained_entry_documents_and_record_require_exact_bytes(self):
        result = self.prepare()
        fragment = self.root / result['instruction_fragment']
        fragment.write_text('Changed instructions\n')
        with self.assertRaisesRegex(ValueError, 'entry_document_changed'):
            B.check(self.root, {'record': result['record']})
        altered = dict(result['record'], sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'entry_record_changed'):
            B.check(self.root, {'record': altered})


if __name__ == '__main__':
    unittest.main()
