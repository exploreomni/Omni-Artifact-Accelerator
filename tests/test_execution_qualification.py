"""Synthetic contract fixtures only; no actual host/native/access qualification."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('execution_qualification_tests',
    ROOT / 'skills/omni-artifact-accelerator/scripts/execution_qualification.py')
Q = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Q)
P = Q.P


class ExecutionQualificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic execution coverage', 'enhancement', 'app', branding='none')
        self.proof = self.save('evidence/observations.txt', 'Synthetic fixture bytes; no actual execution.\n')
        self.implementation = self.save('evidence/runtime-source.txt', 'Opaque retained runtime fingerprint input.\n')
        self.tools = self.save('evidence/tool-profile.json', {'tools': ['bounded_local_read'], 'network': False})
        self.candidate = self.save('deliverables/candidate.html', '<p>Synthetic candidate</p>')
        moment = datetime.now(timezone.utc)
        self.window = {'observed_at': (moment - timedelta(hours=1)).isoformat(),
                       'valid_until': (moment + timedelta(hours=1)).isoformat(),
                       'basis': 'Explicit synthetic review window'}
        self.target = {'schema_version': 1, 'kind': 'execution_qualification_target',
                       'origin': 'https://target.example', 'principal': 'test-principal',
                       'model_id': 'model-1', 'document_id': 'document-1', 'draft_id': 'draft-1',
                       'operation': 'draft_edit', 'audience': {'visibility': 'restricted', 'principal_refs': ['test-principal']},
                       'freshness': self.window, 'evidence': [self.proof]}
        self.profile = {'schema_version': 1, 'kind': 'execution_host_profile',
                        'profile_id': 'local-profile', 'profile_version': '1',
                        'host': {'name': 'local-host', 'version': 'fixture-1'},
                        'runtime': {'name': 'local-runtime', 'version': 'fixture-1'},
                        'implementation': [self.implementation], 'tool_profile': self.tools, 'freshness': self.window,
                        'capabilities': {key: {'status': 'unknown', 'reason': 'Not observed', 'evidence': []}
                                         for key in Q.CAPABILITIES}}
        self.spec = {'schema_version': 1, 'kind': 'execution_qualification_spec',
                     'catalog_version': Q.VERSION, 'profile': self.save('evidence/profile.json', self.profile),
                     'candidate': self.candidate, 'target': None, 'scope': {'migration': False, 'semantic_adaptation': False},
                     'observations': []}

    def save(self, path, value):
        destination = self.root / path
        destination.write_text(json.dumps(value) if isinstance(value, dict) else value)
        return {'path': path, 'sha256': P.digest(destination.read_bytes())}

    def refresh_profile(self):
        self.spec['profile'] = self.save('evidence/profile.json', self.profile)

    def observation(self, scenario, kind=None, outcome='pass', suffix=''):
        lane = next(lane for lane, names in Q.LANES.items() if scenario in names)
        value = {'schema_version': 1, 'kind': 'execution_observation', 'observation_id': scenario + suffix,
                 'scenario_id': scenario, 'profile': self.spec['profile'], 'candidate': self.candidate, 'target': self.spec['target'],
                 'outcome': outcome, 'summary': 'Synthetic fixture for supplied coverage only.',
                 'provenance': None if outcome == 'pending' else {
                     'kind': kind or sorted(Q.KINDS[lane])[0], 'observer': 'fixture-observer',
                     'run_reference': 'fixture-run-' + scenario, 'recorded_at': self.window['observed_at'],
                     'valid_until': self.window['valid_until'],
                     'method': 'Synthetic schema fixture; not a real invocation.'},
                 'evidence': [] if outcome == 'pending' else [self.proof]}
        binding = self.save('evidence/observation-' + scenario + suffix + '.json', value)
        self.spec['observations'].append(binding)
        return value, binding

    def complete(self, lanes=None, kind=None):
        if lanes is None or 'native' in lanes or 'access' in lanes:
            self.spec['target'] = self.save('evidence/target.json', self.target)
        for row in self.profile['capabilities'].values():
            row.update(status='reported_supported', reason='Supplied fixture claim', evidence=[self.proof])
        self.refresh_profile()
        for lane, names in Q.LANES.items():
            if lanes is not None and lane not in lanes:
                continue
            if lane == 'migration' and not self.spec['scope']['migration']:
                continue
            if lane == 'semantic' and not self.spec['scope']['semantic_adaptation']:
                continue
            for scenario in names:
                self.observation(scenario, kind=kind)

    def record(self):
        self.save('evidence/qualification-spec.json', self.spec)
        return Q.record(self.root, 'evidence/qualification-spec.json', 'evidence/qualification-report.json')

    def test_catalog_includes_gate_concurrency_resume_and_dynamic_scenarios(self):
        rows = {r['scenario_id'] for r in Q.catalog()['scenarios']}
        self.assertTrue({'stage_d_artifact_discovery', 'stage_e_three_options_actual_selection_and_design', 'missing_gate_denial',
                         'duplicate_claim', 'output_overlap_denial', 'concurrency_limit', 'unchanged_blocker_stop',
                         'uncertain_launch_reconciliation', 'checkpoint_resume', 'demo_release_separation',
                         'dynamic_data_and_control_binding', 'independent_source_target_comparison'} <= rows)

    def test_absence_is_pending_with_explicit_unknown_capabilities(self):
        result = Q.assess(self.root, self.spec)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(set(result['unknown_capabilities']), set(Q.CAPABILITIES))
        for lane in ('host', 'native', 'visual', 'access', 'human'):
            self.assertEqual(result['lanes'][lane]['status'], 'incomplete')
        self.assertEqual(result['lanes']['migration']['status'], 'not_selected')
        self.assertIsNone(result['tokens']); self.assertIsNone(result['cost'])

    def test_local_end_to_end_leaves_native_and_human_pending(self):
        self.complete(lanes={'host'})
        result = Q.assess(self.root, self.spec)
        self.assertEqual(result['lanes']['host']['status'], 'supplied_evidence_complete')
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['lanes']['native']['reported_pass'], 0)
        self.assertEqual(result['lanes']['human']['reported_pass'], 0)

    def test_even_complete_supplied_observations_never_grant_authority(self):
        self.complete()
        result = Q.assess(self.root, self.spec)
        self.assertEqual(result['status'], 'supplied_evidence_complete')
        for key in ('execution_authorized', 'publication_authorized', 'host_isolation_verified',
                    'provenance_authenticated', 'native_verified', 'effective_access_verified',
                    'human_acceptance_verified'):
            self.assertIs(result[key], False)

    def test_synthetic_and_imported_assertions_do_not_count_as_host_observations(self):
        self.observation('bounded_dispatch', kind='local_synthetic')
        self.observation('duplicate_claim', kind='imported_assertion')
        result = Q.assess(self.root, self.spec)
        statuses = {r['scenario_id']: r['status'] for r in result['scenarios']}
        self.assertEqual(statuses['bounded_dispatch'], 'synthetic_only')
        self.assertEqual(statuses['duplicate_claim'], 'assertion_only')
        self.assertEqual(result['lanes']['host']['reported_pass'], 0)

    def test_wrong_lane_provenance_cannot_establish_human_acceptance(self):
        self.observation('explicit_acceptance', kind='host_observation')
        result = Q.assess(self.root, self.spec)
        row = next(r for r in result['scenarios'] if r['scenario_id'] == 'explicit_acceptance')
        self.assertEqual(row['status'], 'incompatible_provenance')

    def test_failed_observation_is_visible_and_blocks_complete_coverage(self):
        self.observation('concurrency_limit', outcome='fail')
        result = Q.assess(self.root, self.spec)
        self.assertEqual(result['status'], 'reported_fail')
        self.assertEqual(result['lanes']['host']['status'], 'reported_fail')

    def test_report_roundtrip_is_immutable_and_recomputes(self):
        report = self.record()
        path = self.root / report['report']['path']
        before = path.stat().st_mtime_ns
        self.assertEqual(self.record(), report)
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertEqual(Q.check(self.root, report['report']['path']), report)
        self.observation('bounded_dispatch')
        with self.assertRaisesRegex(ValueError, 'immutable_report'):
            self.record()

    def test_modified_summary_cannot_forge_complete_coverage(self):
        report = self.record()
        path = report['report']['path']
        value = P.read_json(self.root / path)[0]
        value['assessment']['status'] = 'supplied_evidence_complete'
        self.save(path, value)
        self.assertEqual(Q.check(self.root, path)['status'], 'inconsistent')

    def test_candidate_profile_tool_runtime_and_evidence_changes_invalidate_report(self):
        self.observation('bounded_dispatch')
        self.record()
        for path in ('deliverables/candidate.html', 'evidence/profile.json', 'evidence/tool-profile.json',
                     'evidence/runtime-source.txt', 'evidence/observations.txt',
                     'evidence/observation-bounded_dispatch.json', 'evidence/qualification-spec.json'):
            with self.subTest(path=path):
                file = self.root / path
                before = file.read_bytes()
                file.write_bytes(before + b' ')
                self.assertEqual(Q.check(self.root, 'evidence/qualification-report.json')['status'], 'inconsistent')
                file.write_bytes(before)

    def test_observation_wrong_candidate_or_profile_rejected(self):
        value, binding = self.observation('bounded_dispatch')
        original = copy.deepcopy(value)
        for key in ('candidate', 'profile', 'target'):
            with self.subTest(key=key):
                value = copy.deepcopy(original)
                value[key] = {'path': 'evidence/wrong.json', 'sha256': '0' * 64}
                self.spec['observations'][0] = self.save(binding['path'], value)
                with self.assertRaisesRegex(ValueError, 'binding_differs'):
                    Q.assess(self.root, self.spec)

    def test_duplicate_scenario_or_observation_identity_rejected(self):
        self.observation('bounded_dispatch')
        self.observation('bounded_dispatch', suffix='-again')
        with self.assertRaisesRegex(ValueError, 'duplicate_observation'):
            Q.assess(self.root, self.spec)
        self.spec['observations'].pop()
        value, binding = self.observation('duplicate_claim')
        value['observation_id'] = 'bounded_dispatch'
        self.spec['observations'][-1] = self.save(binding['path'], value)
        with self.assertRaisesRegex(ValueError, 'duplicate_observation'):
            Q.assess(self.root, self.spec)

    def test_unknown_capability_and_unsupported_core_remain_incomplete(self):
        self.complete()
        for status in ('unknown', 'reported_unsupported'):
            with self.subTest(status=status):
                self.profile['capabilities']['restricted_tools']['status'] = status
                self.refresh_profile()
                for binding in self.spec['observations']:
                    value = P.read_json(self.root / binding['path'])[0]
                    value['profile'] = self.spec['profile']
                    binding.update(self.save(binding['path'], value))
                result = Q.assess(self.root, self.spec)
                self.assertEqual(result['status'], 'incomplete')
                key = 'unknown_capabilities' if status == 'unknown' else 'unsupported_capabilities'
                self.assertIn('restricted_tools', result[key])

    def test_migration_and_adaptation_add_obligations_without_comparing_or_executing(self):
        self.spec['scope'].update(migration=True, semantic_adaptation=True)
        result = Q.assess(self.root, self.spec)
        self.assertIn('independent_source_target_comparison', result['lanes']['migration']['unresolved'])
        self.assertIn('adaptation_owner_decision', result['lanes']['semantic']['unresolved'])
        self.assertIn('zero_null_negative_and_sparse', result['lanes']['semantic']['unresolved'])

    def test_pending_and_pass_require_distinct_provenance_and_evidence(self):
        value, binding = self.observation('bounded_dispatch', outcome='pending')
        self.assertEqual(Q.assess(self.root, self.spec)['lanes']['host']['reported_pass'], 0)
        value['outcome'] = 'pass'
        self.spec['observations'][0] = self.save(binding['path'], value)
        with self.assertRaisesRegex(ValueError, 'invalid_pin_list'):
            Q.assess(self.root, self.spec)

    def test_schema_extra_authority_fields_and_incompatible_catalog_rejected(self):
        changed = dict(self.spec, execution_authorized=True)
        with self.assertRaisesRegex(ValueError, 'invalid_fields'):
            Q.assess(self.root, changed)
        changed = dict(self.spec, catalog_version='future-version')
        with self.assertRaisesRegex(ValueError, 'unsupported_spec'):
            Q.assess(self.root, changed)

    def test_path_escape_symlink_and_missing_evidence_rejected(self):
        changed = copy.deepcopy(self.spec)
        changed['candidate']['path'] = '../outside'
        with self.assertRaises(ValueError):
            Q.assess(self.root, changed)
        (self.root / 'deliverables/link.html').symlink_to(self.root / self.candidate['path'])
        changed['candidate']['path'] = 'deliverables/link.html'
        with self.assertRaises(ValueError):
            Q.assess(self.root, changed)
        changed['candidate']['path'] = 'deliverables/missing.html'
        with self.assertRaises(ValueError):
            Q.assess(self.root, changed)

    def test_observation_timestamp_requires_explicit_offset(self):
        value, binding = self.observation('bounded_dispatch')
        value['provenance']['recorded_at'] = '2026-01-01T12:00:00'
        self.spec['observations'][0] = self.save(binding['path'], value)
        with self.assertRaisesRegex(ValueError, 'invalid_observation_timestamp'):
            Q.assess(self.root, self.spec)

    def test_native_and_access_need_exact_target_not_just_candidate(self):
        self.observation('candidate_readback')
        self.observation('allowed_principal')
        result = Q.assess(self.root, self.spec)
        statuses = {r['scenario_id']: r['status'] for r in result['scenarios']}
        self.assertEqual(statuses['candidate_readback'], 'target_unbound')
        self.assertEqual(statuses['allowed_principal'], 'target_unbound')

    def test_expired_runtime_target_or_observation_does_not_count(self):
        expired = {'observed_at': '2000-01-01T00:00:00+00:00', 'valid_until': '2000-01-02T00:00:00+00:00',
                   'basis': 'Expired supplied record'}
        self.profile['freshness'] = expired
        self.refresh_profile()
        self.observation('bounded_dispatch')
        self.target['freshness'] = expired
        self.spec['target'] = self.save('evidence/target.json', self.target)
        # Keep every observation attached to the same exact selected destination.
        binding = self.spec['observations'][0]
        value = P.read_json(self.root / binding['path'])[0]
        value['target'] = self.spec['target']
        binding.update(self.save(binding['path'], value))
        self.observation('candidate_readback')
        value, binding = self.observation('duplicate_claim')
        value['provenance'].update(recorded_at=expired['observed_at'], valid_until=expired['valid_until'])
        self.spec['observations'][-1] = self.save(binding['path'], value)
        result = Q.assess(self.root, self.spec)
        statuses = {r['scenario_id']: r['status'] for r in result['scenarios']}
        self.assertEqual(statuses['bounded_dispatch'], 'expired_profile')
        self.assertEqual(statuses['candidate_readback'], 'expired_target')
        self.assertEqual(statuses['duplicate_claim'], 'expired_observation')

    def test_target_origin_principal_model_draft_operation_audience_pins_are_exact(self):
        self.complete(lanes={'native'})
        report = self.record()
        path = self.spec['target']['path']
        for key, replacement in (('origin', 'https://other.example'), ('principal', 'other-principal'),
                                 ('model_id', 'other-model'), ('draft_id', 'other-draft'),
                                 ('operation', 'publish'), ('audience', {'visibility': 'shared', 'principal_refs': ['other-principal']})):
            with self.subTest(key=key):
                changed = dict(self.target, **{key: replacement})
                self.save(path, changed)
                self.assertEqual(Q.check(self.root, report['report']['path'])['status'], 'inconsistent')
                self.save(path, self.target)

    def replace_after_digest(self, binding, replacement):
        """Swap the file exactly after its original buffer has been hashed."""
        path = self.root / binding['path']
        original_bytes, original_digest = path.read_bytes(), P.digest
        state = {'replaced': False}
        def digest_then_replace(raw):
            result = original_digest(raw)
            if raw == original_bytes and not state['replaced']:
                path.write_text(json.dumps(replacement))
                state['replaced'] = True
            return result
        return path, original_bytes, state, mock.patch.object(P, 'digest', side_effect=digest_then_replace)

    def test_pinned_profile_target_and_observation_parse_only_verified_snapshot(self):
        target_binding = self.save('evidence/target.json', self.target)
        observation, observation_binding = self.observation('bounded_dispatch')
        cases = [
            (self.spec['profile'], dict(self.profile, profile_id='unverified-replacement'),
             lambda: Q.profile(self.root, self.spec['profile']), lambda result: result['profile_id'] == 'local-profile'),
            (target_binding, dict(self.target, operation='unverified-operation'),
             lambda: Q.target(self.root, target_binding), lambda result: result['freshness'] == 'current'),
            (observation_binding, dict(observation, outcome='fail'),
             lambda: Q.observation(self.root, observation_binding, self.spec, {'bounded_dispatch': 'host'}),
             lambda result: result['outcome'] == 'pass')]
        for binding, replacement, read, expected in cases:
            with self.subTest(path=binding['path']):
                path, original, state, patched = self.replace_after_digest(binding, replacement)
                try:
                    with patched:
                        result = read()
                    self.assertTrue(state['replaced'])
                    self.assertTrue(expected(result))
                    with self.assertRaisesRegex(ValueError, 'pinned_bytes_changed'):
                        Q.pin(self.root, binding)
                finally:
                    path.write_bytes(original)

    def test_report_check_parses_verified_spec_buffer_even_if_path_is_replaced(self):
        self.observation('bounded_dispatch')
        report = self.record()
        binding = self.pin_from_path('evidence/qualification-spec.json')
        replacement = dict(self.spec, observations=[])
        path, original, state, patched = self.replace_after_digest(binding, replacement)
        try:
            with patched:
                result = Q.check(self.root, report['report']['path'])
            self.assertTrue(state['replaced'])
            self.assertEqual(result['status'], 'consistent')
            self.assertEqual(Q.check(self.root, report['report']['path'])['status'], 'inconsistent')
        finally:
            path.write_bytes(original)

    def pin_from_path(self, path):
        return {'path': path, 'sha256': P.digest((self.root / path).read_bytes())}

    def test_verified_json_retains_duplicate_nonfinite_and_size_rejection(self):
        for raw in ('{"key":1,"key":2}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}', 'not JSON'):
            with self.subTest(raw=raw):
                binding = self.save('evidence/invalid-json.json', raw)
                with self.assertRaisesRegex(ValueError, 'invalid_pinned_json'):
                    Q.pinned_json(self.root, binding)
        binding = self.save('evidence/invalid-json.json', '{"value":"long enough to exceed the chosen bound"}')
        with mock.patch.object(P, 'MAX_BYTES', 16), self.assertRaises(ValueError):
            Q.pinned_json(self.root, binding)


if __name__ == '__main__':
    unittest.main()
