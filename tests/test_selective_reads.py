"""Local read/projection fixtures; no actual host or validation-pass claims."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

_spec = importlib.util.spec_from_file_location('selective_tests', Path(__file__).resolve().parents[1] /
    'skills/omni-artifact-accelerator/scripts/selective_reads.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
P = R.P


class SelectiveReadTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic selective reads', 'enhancement', 'app', branding='none')
        self.path = 'inputs/original.txt'
        (self.root / self.path).write_text('First original line\nSecond original line\nThird original line\n')
        self.request = {'artifact': self.artifact(self.path, 'text'),
                        'disclosure': {'allowed_classifications': ['confidential'], 'review_ref': 'explicit-local-review'},
                        'selection': {'kind': 'lines', 'start': 2, 'count': 1}}
        self.calls = 0
        self.full = {'stage': {'required': True, 'status': 'incomplete', 'next_stage': 'review',
                              'completed_stages': ['access'], 'tail_sha256': 'a' * 64,
                              'candidate_sha256': None, 'release_ready': False},
                     'tasks': [self.row('task-a'), self.row('task-b', status='stale')],
                     'blockers': [{'area': 'stage', 'code': 'missing_native_observation'}],
                     'external_mutations_authorized': False}

    def artifact(self, path, format):
        return {'path': path, 'sha256': P.digest((self.root / path).read_bytes()), 'format': format,
                'classification': 'confidential'}

    def row(self, identity, status='outputs_recorded'):
        return {'task_id': identity, 'domain_id': 'domain', 'stage': 'app', 'role': 'app-engineer',
                'status': status, 'authoring_mode': 'provisional', 'review_status': 'unverified',
                'unknowns': [], 'outputs': ['deliverables/private-candidate.html'],
                'next_action': 'Private source prose is not returned by this projection.'}

    def current(self, root):
        self.calls += 1
        return copy.deepcopy(self.full)

    def test_exact_lines_are_bounded_untrusted_and_keep_classification(self):
        result = R.artifact_read(self.root, self.request)
        self.assertEqual(result['items'], [{'line': 2, 'text': 'Second original line\n'}])
        self.assertEqual(result['classification'], 'confidential')
        self.assertTrue(result['private_output'])
        self.assertFalse(result['whole_source_in_response'])
        self.assertFalse(result['semantic_completeness_verified'])
        self.assertEqual(result['content_authority'], 'untrusted_data')

    def test_changed_file_and_disallowed_classification_reject(self):
        denied = copy.deepcopy(self.request)
        denied['disclosure']['allowed_classifications'] = ['public']
        with self.assertRaisesRegex(ValueError, 'disclosure_denied'):
            R.artifact_read(self.root, denied)
        (self.root / self.path).write_text('Changed source')
        with self.assertRaisesRegex(ValueError, 'artifact_changed'):
            R.artifact_read(self.root, self.request)

    def test_paths_extensions_and_symlinks_are_bounded(self):
        for path in ('../outside.txt', '.env', 'inputs/.secret.json', 'project.json', 'inputs/key.pem'):
            request = copy.deepcopy(self.request)
            request['artifact']['path'] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, '^selective\\.'):
                R.artifact_read(self.root, request)
        (self.root / 'inputs/link.txt').symlink_to(self.root / self.path)
        request = copy.deepcopy(self.request)
        request['artifact']['path'] = 'inputs/link.txt'
        with self.assertRaises(ValueError):
            R.artifact_read(self.root, request)

    def test_json_selection_is_literal_top_level_only_and_no_unselected_prose(self):
        path = 'evidence/object.json'
        (self.root / path).write_text(json.dumps({'status': 'pending', 'details': {'safe': True}, 'unselected': 'Private prose'}))
        request = dict(self.request, artifact=self.artifact(path, 'json'), selection={'kind': 'json_keys', 'keys': ['status']})
        result = R.artifact_read(self.root, request)
        self.assertEqual(result['items'], [{'key': 'status', 'value': 'pending'}])
        self.assertNotIn('Private prose', json.dumps(result))
        for key in ('details.safe', '$.details', '/details', '__missing__'):
            request['selection']['keys'] = [key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                R.artifact_read(self.root, request)

    def test_json_credentials_are_not_disclosed_even_in_text_mode(self):
        path = 'evidence/object.json'
        (self.root / path).write_text('{"status":"ready","credentials":{"short":"secret"}}')
        request = dict(self.request, artifact=self.artifact(path, 'text'), selection={'kind': 'lines', 'start': 1, 'count': 1})
        with self.assertRaisesRegex(ValueError, 'possible_secret'):
            R.artifact_read(self.root, request)

    def test_artifact_pages_have_exact_cursor_binding_and_progress(self):
        (self.root / self.path).write_text(''.join(str(i) + ' ' + 'x' * 500 + '\n' for i in range(12)))
        request = dict(self.request, artifact=self.artifact(self.path, 'text'),
                       selection={'kind': 'lines', 'start': 1, 'count': 12}, max_bytes=4096)
        first = R.artifact_read(self.root, request)
        self.assertLess(len(P.canonical(first)), 4097)
        self.assertIsNotNone(first['cursor'])
        second = R.artifact_read(self.root, dict(request, cursor=first['cursor']))
        self.assertEqual(second['omitted_before'], first['returned_units'])
        self.assertGreater(second['returned_units'], 0)
        changed = dict(request, selection={'kind': 'lines', 'start': 2, 'count': 11}, cursor=first['cursor'])
        with self.assertRaisesRegex(ValueError, 'cursor_binding_changed'):
            R.artifact_read(self.root, changed)

    def test_oversized_unit_requires_narrower_request_without_partial_text(self):
        (self.root / self.path).write_text('x' * 10000)
        request = dict(self.request, artifact=self.artifact(self.path, 'text'),
                       selection={'kind': 'lines', 'start': 1, 'count': 1}, max_bytes=4096)
        with self.assertRaisesRegex(ValueError, 'selected_unit_exceeds'):
            R.artifact_read(self.root, request)

    def test_requested_line_range_cannot_silently_shrink_at_end_of_source(self):
        request = dict(self.request, selection={'kind': 'lines', 'start': 2, 'count': 3})
        with self.assertRaisesRegex(ValueError, 'line_range_outside_source'):
            R.artifact_read(self.root, request)

    def test_replacement_after_verified_read_cannot_substitute_unpinned_content(self):
        path = self.root / self.path
        before = path.read_bytes()
        original = P.digest
        replaced = []
        def changed(raw):
            result = original(raw)
            if raw == before and not replaced:
                path.write_text('Unverified replacement')
                replaced.append(True)
            return result
        with mock.patch.object(P, 'digest', side_effect=changed):
            result = R.artifact_read(self.root, self.request)
        self.assertEqual(result['items'][0]['text'], 'Second original line\n')

    def test_symlink_replacement_after_path_check_is_not_followed(self):
        source = self.root / self.path
        other = self.root / 'inputs/replacement.txt'
        other.write_bytes(source.read_bytes())
        original = P.relative_file
        def replace(root, path):
            resolved = original(root, path)
            if path == self.path:
                source.unlink()
                source.symlink_to(other)
            return resolved
        with mock.patch.object(P, 'relative_file', side_effect=replace):
            with self.assertRaisesRegex(ValueError, '^selective\\.'):
                R.artifact_read(self.root, self.request)

    def test_filters_never_hide_global_or_out_of_scope_critical_presence(self):
        result = R.status_view(self.root, {'filter': {'task_ids': ['task-a']}}, self.current)
        self.assertEqual([row['task_id'] for row in result['tasks']], ['task-a'])
        self.assertEqual([row['task_id'] for row in result['critical_tasks']], ['task-b'])
        self.assertEqual(result['global_blocker_count'], 1)
        self.assertFalse(result['full_validation_pass'])
        self.assertNotIn('Private source prose', json.dumps(result))

    def test_source_incompleteness_and_assurance_survive_projection(self):
        self.full['incomplete'] = True
        self.full['task_snapshot'] = {'status': 'incomplete', 'snapshot_generation': None}
        self.full['stage']['choice_assurance'] = 'conversation_evidence'
        self.full['stage']['review_assurance'] = {'status': 'source_only', 'native_observation': 'pending'}
        result = R.status_view(self.root, {}, self.current)
        self.assertTrue(result['incomplete'])
        self.assertEqual(result['task_snapshot'], self.full['task_snapshot'])
        self.assertEqual(result['stage']['choice_assurance'], 'conversation_evidence')
        self.assertEqual(result['stage']['review_assurance'], self.full['stage']['review_assurance'])

    def test_since_always_runs_fresh_validation_including_file_and_expiry_changes(self):
        first = R.status_view(self.root, {}, self.current)
        unchanged = R.status_view(self.root, {'since': first['since']}, self.current)
        self.assertTrue(unchanged['unchanged_since'])
        self.assertEqual(self.calls, 2)
        self.assertEqual(unchanged['returned_tasks'], 0)
        self.assertEqual(unchanged['critical_task_count'], 1)
        # Simulate a fresh validator observing an expired capture despite no ledger edit.
        self.full['blockers'].append({'area': 'context', 'code': 'capture_expired'})
        changed = R.status_view(self.root, {'since': first['since']}, self.current)
        self.assertFalse(changed['unchanged_since'])
        self.assertEqual(changed['global_blocker_count'], 2)
        self.assertEqual(self.calls, 3)

    def test_file_drift_is_observed_with_unchanged_ledger(self):
        expected = P.digest((self.root / self.path).read_bytes())
        def fresh(root):
            value = self.current(root)
            if P.digest((root / self.path).read_bytes()) != expected:
                value['tasks'][0]['status'] = 'stale'
            return value
        first = R.status_view(self.root, {}, fresh)
        (self.root / self.path).write_text('Changed independent evidence')
        second = R.status_view(self.root, {'since': first['since']}, fresh)
        self.assertFalse(second['unchanged_since'])
        self.assertEqual(second['critical_task_count'], 2)

    def test_status_cursor_is_bound_to_current_project_filter_and_fresh_status(self):
        first = R.status_view(self.root, {'limit': 1}, self.current)
        second = R.status_view(self.root, {'limit': 1, 'cursor': first['cursor']}, self.current)
        self.assertEqual(second['tasks'][0]['task_id'], 'task-b')
        with self.assertRaisesRegex(ValueError, 'cursor_binding_changed'):
            R.status_view(self.root, {'filter': {'statuses': ['stale']}, 'cursor': first['cursor']}, self.current)
        self.full['tasks'][0]['status'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'cursor_binding_changed'):
            R.status_view(self.root, {'cursor': first['cursor']}, self.current)
        self.assertEqual(self.calls, 4)

    def test_large_status_accounts_for_omitted_critical_and_global_blockers(self):
        self.full['tasks'] = [self.row('task-' + str(i), status='blocked') for i in range(120)]
        self.full['blockers'] = [{'area': 'stage', 'code': 'blocker-' + str(i)} for i in range(120)]
        result = R.status_view(self.root, {'max_bytes': 4096, 'limit': 1}, self.current)
        self.assertLessEqual(len(P.canonical(result)), 4096)
        self.assertEqual(result['critical_task_count'], 120)
        self.assertGreater(result['critical_tasks_omitted'], 0)
        self.assertGreater(result['global_blockers_omitted'], 0)
        self.assertTrue(result['incomplete'])
        self.assertEqual(result['returned_tasks'], 1)

    def test_invalid_and_forged_since_cannot_bypass_full_validation(self):
        first = R.status_view(self.root, {}, self.current)
        forged = R.untoken(first['since'])
        forged['binding']['state_sha256'] = '0' * 64
        result = R.status_view(self.root, {'since': R.token(forged)}, self.current)
        self.assertFalse(result['unchanged_since'])
        self.assertEqual(self.calls, 2)
        with self.assertRaisesRegex(ValueError, '^selective\\.'):
            R.status_view(self.root, {'since': first['since']}, lambda root: (_ for _ in ()).throw(ValueError('sensitive source detail')))


if __name__ == '__main__':
    unittest.main()
