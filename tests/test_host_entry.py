"""Original offline host-entry fixtures. No target modules, packages or live tools."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts/host_entry.py'
SPEC = importlib.util.spec_from_file_location('test_host_entry_module', SCRIPT)
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)
P, W = H.P, H.W


class QualifiedFixture:
    """An in-process synthetic observer, never a live host qualification."""
    def verify_entry(self, binding):
        return {'binding_sha256': P.digest(P.canonical(binding)),
                'loaded_package_path': binding['loaded_package']['path'], 'routes': binding['routes'],
                'qualification_reference': 'synthetic:independent-boundary-check',
                'denied_probes': [{'kind': r['kind'], 'name': r['name'], 'outcome': 'denied',
                                   'evidence_reference': 'synthetic:denial-' + r['kind']}
                                  for r in binding['routes'] if r['availability'] == 'available']}


class HostEntryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.package = self.parent / 'verified-package'
        self.loaded = self.parent / 'loaded-package'
        for package in (self.package, self.loaded):
            for relative in (H.ENTRY, H.HELPER):
                path = package / 'skills' / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('raise AssertionError("Loaded package code must never execute")\n')
            (package / 'package.json').write_text('{"name":"fixture-package","version":"1.0.0"}')
        self.root = self.parent / 'engagement'
        P.init(self.root, 'Original source verification fixture', 'net-new', 'app', branding='none')
        (self.root / 'inputs/brief.txt').write_text('Inspect one collection and retain context on return.')
        (self.root / 'contracts/execution.json').write_text('{"responsibilities":{}}')
        self.git = {'head': 'a' * 40, 'status': ''}
        self.old_git = copy.deepcopy(self.git)
        for patcher in (mock.patch.object(W, 'source_root', return_value=self.package),
                        mock.patch.object(W, 'git_identity', side_effect=lambda p: copy.deepcopy(
                            self.git if Path(p) == self.package else self.old_git)),
                        mock.patch.object(W, 'host_entry_helper', return_value=H)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.request = {'schema_version': 1, 'id': 'entry',
            'host': {'name': 'Chosen host', 'execution_mode': 'instruction_guided',
                     'tools': ['local process interface'], 'constraints': ['No target access']},
            'loaded_package_path': str(self.loaded), 'source_expectation': {'kind': 'current_checkout'},
            'routes': [{'kind': kind, 'name': 'fixture-' + kind, 'availability': 'available'} for kind in H.ROUTES]}

    def source_receipt(self, age=0):
        path = 'evidence/source-check-fixture.json'
        P.write_json(self.root / path, {'schema_version':1, 'kind':'analyst_source_check',
            'project_id': P.load_project(self.root)[1]['id'], 'package_root': str(self.package),
            'ref':'refs/heads/main', 'revision':self.git['head'],
            'checked_at':(datetime.now(timezone.utc) - timedelta(minutes=age)).isoformat()})
        self.request['source_expectation'] = {'kind':'latest_main','revision':self.git['head'],'verification_path':path}
        return path

    def start(self, pointer):
        return W.start(self.root, {'id':'first', 'source_mode':'repository_only',
            'host':self.request['host'], 'entrypoint':'Explicit current package entry',
            'brief':'inputs/brief.txt', 'execution':'contracts/execution.json',
            'loaded_guidance':['skills/' + H.ENTRY], 'source_expectation':self.request['source_expectation'],
            'host_entry':pointer})

    def test_stale_loaded_copy_diagnoses_both_revisions_and_blocks_start(self):
        self.source_receipt()
        self.old_git['head'] = 'b' * 40
        (self.loaded / 'skills' / H.ENTRY).write_text('Old source entry')
        prepared = H.prepare(self.root, self.request)
        report = prepared['entry']
        self.assertEqual(report['loaded_package']['revision'], 'b'*40)
        self.assertEqual(report['verifier_package']['revision'], 'a'*40)
        self.assertIn('loaded_package_differs_from_verifier', report['findings'])
        self.assertFalse(report['current_release_test'])
        with self.assertRaisesRegex(ValueError, 'source_not_ready'):
            self.start(prepared['record'])
        self.assertFalse((self.root / 'evidence/run-first.json').exists())

    def test_installed_copy_matches_by_bytes_without_inventing_revision(self):
        installed = self.parent / 'installed'
        (self.loaded / 'skills').rename(installed)
        self.request['loaded_package_path'] = str(installed)
        self.source_receipt()
        report = H.check(self.root, self.request)
        self.assertEqual(report['status'], 'source_ready')
        self.assertIsNone(report['loaded_package']['revision'])
        self.assertEqual(report['release_status'], 'latest_main_verified_at_entry')
        self.assertFalse(report['current_release_test'])
        self.assertEqual(report['host_boundary']['mode'], 'advisory')

    def test_offline_snapshot_binds_exact_source_and_retains_offline_status(self):
        self.request['source_expectation'] = {'kind':'offline_snapshot',
            'manifest_sha256':P.digest(P.canonical(W.source_manifest(self.package)))}
        with mock.patch.object(W.subprocess, 'run', side_effect=AssertionError('No remote or package execution')):
            record = H.prepare(self.root, self.request)
        self.assertEqual(record['entry']['release_status'], 'offline_bytes_verified')
        self.assertFalse(record['entry']['current_release_test'])
        (self.package / 'package.json').write_text('{"version":"changed"}')
        self.assertIn('requested_release_unverified', H.check(self.root, self.request)['findings'])

    def test_current_checkout_is_explicitly_latest_unverified(self):
        report = H.check(self.root, self.request)
        self.assertEqual(report['release_status'], 'checkout_recorded_latest_unverified')
        self.assertFalse(report['current_release_test'])

    def test_pinned_retry_and_resume_preserve_original_receipts(self):
        self.request['source_expectation'] = {'kind':'pinned_revision','revision':self.git['head']}
        first = H.prepare(self.root, self.request)
        raw = (self.root / first['record']['path']).read_bytes()
        self.assertEqual(H.prepare(self.root, self.request)['status'], 'reused')
        self.start(first['record'])
        run, _ = W.active_run(self.root, P.load_project(self.root)[1])
        self.assertEqual(run['host_entry'], first['record'])
        self.assertEqual((self.root / first['record']['path']).read_bytes(), raw)
        (self.loaded / 'skills' / H.ENTRY).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'source_not_ready'):
            W.active_run(self.root, P.load_project(self.root)[1])

    def test_latest_source_expires_before_new_start_but_recorded_resume_stays_historical(self):
        self.source_receipt(age=11)
        self.assertIn('requested_release_unverified', H.check(self.root, self.request)['findings'])
        self.assertFalse(H.check(self.root, self.request)['current_release_test'])
        report = H.check(self.root, self.request, _resume=True)
        self.assertEqual(report['release_status'], 'latest_main_verified_at_recorded_entry')
        self.assertFalse(report['current_release_test'])

    def test_actual_startup_rechecks_expiry_while_existing_resume_uses_original_entry(self):
        self.source_receipt()
        first = H.prepare(self.root, self.request)
        self.start(first['record'])
        original = (self.root / 'evidence/run-first.json').read_bytes()
        later = datetime.now(timezone.utc) + timedelta(minutes=11)
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return later
        with mock.patch.object(W, 'datetime', Clock):
            run, _ = W.active_run(self.root, P.load_project(self.root)[1])
            self.assertEqual(run['host_entry'], first['record'])
            with self.assertRaisesRegex(ValueError, 'source_not_ready'):
                H.verify_record(self.root, first['record'], self.request['host'], self.request['source_expectation'])
        self.assertEqual((self.root / 'evidence/run-first.json').read_bytes(), original)

    def test_git_identity_does_not_borrow_a_parent_repository_revision(self):
        original = self.parent / 'unrelated'
        original.mkdir()
        response = type('Result', (), {'returncode':0,'stdout':str(self.parent)})()
        # Call the original function beneath the fixture's patched Git observer.
        spec = importlib.util.spec_from_file_location('entry_workflow_git_test', SCRIPT.with_name('delivery_workflow.py'))
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        with mock.patch.object(workflow.subprocess, 'run', return_value=response) as invoked:
            self.assertEqual(workflow.git_identity(original), {'head':None,'status':None})
            self.assertEqual(invoked.call_count, 1)

    def test_route_inventory_cannot_omit_shell_or_self_claim_enforcement(self):
        self.request['routes'] = [r for r in self.request['routes'] if r['kind'] != 'shell']
        with self.assertRaisesRegex(ValueError, 'route_inventory_required|all_route_kinds_required'):
            H.check(self.root, self.request)
        self.request['routes'].append({'kind':'shell','name':'shell','availability':'available','enforced':True})
        with self.assertRaisesRegex(ValueError, 'invalid_fields'):
            H.check(self.root, self.request)

    def test_trusted_provider_must_cover_every_actual_route_and_current_challenge(self):
        self.source_receipt()
        observer = QualifiedFixture()
        report = H.check(self.root, self.request, provider=observer)
        self.assertEqual(report['host_boundary']['mode'], 'enforced')
        self.assertTrue(report['current_release_test'])
        self.assertFalse(report['execution_authorized'])
        self.assertFalse(report['publication_authorized'])
        captured = []
        original = observer.verify_entry
        def retain(binding):
            captured.append(original(binding))
            return captured[-1]
        with mock.patch.object(observer, 'verify_entry', side_effect=retain):
            H.check(self.root, self.request, provider=observer)
        with mock.patch.object(observer, 'verify_entry', return_value=captured[-1]):
            self.assertEqual(H.check(self.root, self.request, provider=observer)['host_boundary']['mode'], 'advisory')
        def incomplete(binding):
            value = original(binding)
            value['denied_probes'] = value['denied_probes'][:-1]
            return value
        with mock.patch.object(observer, 'verify_entry', side_effect=incomplete):
            self.assertEqual(H.check(self.root, self.request, provider=observer)['host_boundary']['mode'], 'advisory')

    def test_saved_provider_result_cannot_grant_enforcement_on_resume(self):
        first = H.prepare(self.root, self.request, provider=QualifiedFixture())
        self.assertEqual(first['entry']['host_boundary']['mode'], 'enforced')
        report = H.verify_record(self.root, first['record'], self.request['host'], self.request['source_expectation'])
        self.assertEqual(report['host_boundary']['mode'], 'advisory')

    def test_unknown_route_or_observer_failure_is_advisory(self):
        self.request['routes'][-1]['availability'] = 'unknown'
        self.assertEqual(H.check(self.root, self.request, provider=QualifiedFixture())['host_boundary']['mode'], 'advisory')
        self.assertEqual(H.check(self.root, self.request, provider=object())['host_boundary']['mode'], 'advisory')

    def test_immutable_requests_and_tampered_receipt_reject(self):
        first = H.prepare(self.root, self.request)
        changed = copy.deepcopy(self.request)
        changed['host']['name'] = 'Changed host'
        with self.assertRaisesRegex(ValueError, 'immutable_record_conflict'):
            H.prepare(self.root, changed)
        (self.root / first['record']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'record_changed'):
            H.verify_record(self.root, first['record'], self.request['host'], self.request['source_expectation'])

    def test_loaded_symlinks_and_executable_target_are_never_followed(self):
        entry = self.loaded / 'skills' / H.ENTRY
        entry.unlink()
        entry.symlink_to(self.package / 'skills' / H.ENTRY)
        report = H.check(self.root, self.request)
        self.assertIn('loaded_package_unavailable_or_invalid', report['findings'])


if __name__ == '__main__':
    unittest.main()
