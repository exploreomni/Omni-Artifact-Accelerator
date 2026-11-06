"""Whole-draft contract and write-boundary regressions using original fixtures.

No tenant, browser, dependency activation or real permission is exercised.
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C = load('publish_fixture_create', 'tests/test_native_create.py')
F = load('publish_fixture_draft', 'tests/test_native_authoring.py')
W = load('write_gate', 'skills/omni-app-engineer/scripts/native_write_gate.py')
A, P = C.a, C.P


class Publish(unittest.TestCase):
    def setUp(self):
        self.fixture = C.NativeCreate()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.target, self.snapshot = F.fixture()
        self.snapshot['app']['html'] = C.HTML
        self.snapshot['document']['name'] = 'Original operations fixture'
        self.snapshot['document']['description'] = 'Synthetic publishing contract'
        self.snapshot_path = 'contracts/draft-snapshot.json'
        (self.root / self.snapshot_path).write_text(json.dumps(self.snapshot))

    def stage(self):
        self.fixture.stage(artifacts=[self.fixture.html_path, self.fixture.spec_path, self.snapshot_path])

    def prepare(self, current=None):
        return A.prepare_publish(project=self.root, artifact=self.fixture.html_path,
            snapshot_artifact=self.snapshot_path, current=current or self.snapshot)

    def captures(self, prepared):
        route = '/api/v2/documents/' + self.target['document_id']
        def capture(method, path, body):
            return {'base_url': self.target['base_url'], 'method': method, 'path': path, 'status': 200, 'body': body}
        doc = copy.deepcopy(self.snapshot['document'])
        doc['app'] = {'url': route + '/app'}
        return (capture('POST', route + '/draft/publish', {'identifier': self.target['document_id'],
                    'name': doc['name'], 'description': doc['description']}),
                capture('GET', route, doc), capture('GET', route + '/app', copy.deepcopy(self.snapshot['app'])))

    def test_requires_whole_candidate_and_all_reviews(self):
        with self.assertRaises(ValueError):
            self.prepare()
        self.fixture.stage()
        with self.assertRaisesRegex(ValueError, 'complete draft snapshot'):
            self.prepare()

    def test_exact_publish_and_readback_preserve_pending_render_and_runtime(self):
        self.stage()
        request = self.prepare()
        self.assertEqual(request['request'], {'method': 'POST', 'path': '/api/v2/documents/operations/draft/publish'})
        result = A.verify_publish(request, *self.captures(request), project=self.root)
        self.assertEqual(result['status'], 'exact_publication_readback')
        self.assertFalse(result['native_verified'])
        self.assertFalse(request['publication_authorized'])
        self.assertFalse(result['rendered_quality_verified'])

    def test_draft_query_settings_html_and_branch_drift_rejected(self):
        self.stage()
        for lane in ('query', 'settings', 'html', 'branch'):
            current = copy.deepcopy(self.snapshot)
            if lane == 'query':
                current['document']['queryPresentations']['data']['1']['query']['fields'] = ['other.id']
            elif lane == 'settings':
                current['app']['settings']['allowDownloads'] = True
            elif lane == 'html':
                current['app']['html'] += 'different'
            else:
                current['draft']['branch'] = {'id': 'other'}
            with self.subTest(lane=lane), self.assertRaises(ValueError):
                self.prepare(current)

    def test_changed_query_or_wrong_published_capture_is_not_success(self):
        self.stage()
        request = self.prepare()
        for lane in ('query', 'html', 'draft'):
            captures = self.captures(request)
            if lane == 'query':
                captures[1]['body']['queryPresentations'] = {}
            elif lane == 'html':
                captures[2]['body']['html'] = 'not reviewed'
            else:
                captures[1]['body']['draftOf'] = {'identifier': 'operations'}
            with self.subTest(lane=lane):
                result = A.verify_publish(request, *captures, project=self.root)
                self.assertEqual(result['status'], 'readback_mismatch')


class Boundary(unittest.TestCase):
    def setUp(self):
        self.fixture = C.NativeCreate()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.fixture.stage()
        self.request = self.fixture.prepare()
        class Host:
            def __init__(self):
                self.sent = []
            def authorize(self, binding):
                return {'authorized': True, 'binding_sha256': A.digest(binding), 'reference': 'synthetic-host-choice'}
            def preflight_create(self, binding):
                return True
            def send(self, request):
                self.sent.append(request)
        self.host = Host()

    def test_exact_managed_request_needs_readback_and_cannot_replay(self):
        result = W.execute(self.root, self.request, host=self.host)
        self.assertEqual(result['status'], 'submitted_readback_required')
        self.assertEqual(len(self.host.sent), 1)
        self.assertFalse(result['host_enforcement_verified'])
        with self.assertRaisesRegex(ValueError, 'Prior attempt'):
            W.execute(self.root, self.request, host=self.host)
        self.assertEqual(len(self.host.sent), 1)

    def test_denied_action_and_tampered_route_never_reach_transport(self):
        changed = copy.deepcopy(self.request)
        changed['request']['path'] = '/unrelated/write'
        with self.assertRaisesRegex(ValueError, 'drift'):
            W.execute(self.root, changed, host=self.host)
        self.host.authorize = lambda binding: {'authorized': False, 'binding_sha256': A.digest(binding), 'reference': 'denied'}
        with self.assertRaisesRegex(ValueError, 'authorization'):
            W.execute(self.root, self.request, host=self.host)
        self.assertFalse(self.host.sent)

    def test_candidate_changed_during_authorization_never_reaches_transport(self):
        original = self.host.authorize
        def authorize(binding):
            (self.root / self.fixture.html_path).write_text('Changed after approval request')
            return original(binding)
        self.host.authorize = authorize
        with self.assertRaises(ValueError):
            W.execute(self.root, self.request, host=self.host)
        self.assertFalse(self.host.sent)

    def test_uncertain_result_redacts_errors_and_blocks_replay(self):
        def failing(request):
            raise RuntimeError('do not expose transport credentials')
        self.host.send = failing
        result = W.execute(self.root, self.request, host=self.host)
        self.assertEqual(result['status'], 'outcome_unknown')
        self.assertNotIn('credentials', json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'Prior attempt'):
            W.execute(self.root, self.request, host=self.host)

    def test_changed_review_metadata_cannot_reopen_the_same_native_operation(self):
        W.execute(self.root, self.request, host=self.host)
        newer = copy.deepcopy(self.request)
        newer['engagement']['tail_sha256'] = 'f' * 64
        with patch.object(W, 'rebuild', return_value=newer):
            with self.assertRaisesRegex(ValueError, 'Prior attempt'):
                W.execute(self.root, newer, host=self.host)
        self.assertEqual(len(self.host.sent), 1)

    def test_directory_persistence_failure_stops_before_transport(self):
        with patch.object(W, 'sync_directory', side_effect=OSError('synthetic persistence failure')):
            with self.assertRaises(OSError):
                W.execute(self.root, self.request, host=self.host)
        self.assertFalse(self.host.sent)


if __name__ == '__main__':
    unittest.main()
