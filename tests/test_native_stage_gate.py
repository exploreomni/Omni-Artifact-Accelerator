"""Real native authoring routes; original stdlib fixtures, no producer or tenant.

Semantic/runtime validators are explicit stubs here: this suite establishes gate
ordering and candidate binding only, not vendor contracts or native validation.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

TESTS = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load('native_gate_app', TESTS.parent / 'skills/omni-app-engineer/scripts/omni_app_native.py')
native = app.n
G = load('native_gate_fixture', TESTS / 'stage_gate_fixture.py')
P = native.WORKFLOW.ap
HTML = '<main><!--owned:start--><h1>Before</h1><!--owned:end--></main>'


class SyntheticTransport:
    """Only transport and unrelated validators are replaced; guards stay real."""
    def __init__(self, root, kind):
        target = native.TargetConfig('https://synthetic.invalid', 'test', 'doc', 'draft', 'model', 'member', 'branch')
        super().__init__(root, target, runner=self.unexpected, http=self.unexpected)
        self.kind, self.calls, self.http_calls, self.patch_count = kind, [], [], 0
        self.state = {'name': 'Before', 'workbookModelId': 'workbook',
                      'queryPresentations': {'data': {}, 'order': []}}
        self.app = None if kind == 'initial' else {'html': HTML, 'settings': {}}
        if kind == 'patch':
            self.state['app'] = {'url': '/api/v2/documents/doc/draft/draft/app'}

    @staticmethod
    def unexpected(*args, **kwargs):
        raise AssertionError('No subprocess or network transport is permitted')

    def inspect(self):
        self.calls.append('inspect')
        result = {'state': copy.deepcopy(self.state), 'app': copy.deepcopy(self.app),
                  'identity': {'user': 'synthetic'}, 'draft_context': {
                      'identifier': 'draft', 'publishedIdentifier': 'doc', 'workbookModelId': 'workbook',
                      'branch': {'id': 'branch'}, 'status': 'active', 'draftOutOfDate': False}}
        result['snapshot_sha256'] = native.digest(result)
        return result

    inspect_initial = inspect

    def _cli(self, args, body=None, **kwargs):
        self.calls.append(args)
        if '--help' in args:
            return 'Synthetic usage --body'
        if '--version' in args:
            return 'synthetic-only'
        assert args[:2] == ['documents', 'v2-patch-draft-by-identifier']
        self.require_intent()
        self.patch_count += 1
        self.state.update(copy.deepcopy(body))
        return {'identifier': 'doc', 'draftIdentifier': 'draft'}

    def require_intent(self):
        assert list((self.store / 'executions').glob('*/intent.json'))

    def _rest(self, method, route, body=None, **kwargs):
        self.http_calls.append((method, route, body))
        self.require_intent()
        self.patch_count += 1
        if method == 'PUT':
            self.app = copy.deepcopy(body)
            self.state['app'] = {'url': '/api/v2/documents/doc/draft/draft/app'}
        else:
            assert method == 'PATCH'
            for edit in body['htmlEdits']:
                self.app['html'] = self.app['html'].replace(edit['search'], edit['replace'], 1)
        return 200, {}, native.encoded({'identifier': 'doc', 'draftIdentifier': 'draft', 'app': self.app})

    def _requirements(self, paths):
        return {'synthetic': True}

    def _baseline_check(self, *args, **kwargs):
        return None

    def baseline(self, path, live=None):
        return self._read(path)

    initial_baseline = baseline

    def _runtime(self, *args):
        return None

    def _validate_bindings(self, *args):
        return None


class DashboardAdapter(SyntheticTransport, native.NativeAdapter):
    pass


class AppAdapter(SyntheticTransport, app.AppNativeAdapter):
    pass


class NativeStageGateTests(unittest.TestCase):
    def fixture(self, kind):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name).resolve() / 'engagement'
        P.init(root, 'Original native gate fixture', 'migration', 'dashboard' if kind == 'dashboard' else 'app')
        adapter = (DashboardAdapter if kind == 'dashboard' else AppAdapter)(root, kind)
        fixture = SimpleNamespace(root=root, adapter=adapter, fake=adapter, kind=kind, gates=G.Lifecycle(root, P))
        def write(path, value):
            (root / path).write_text(json.dumps(value))
        for path in ('source.json', 'semantic.json', 'requirements.json', 'runtime.json'):
            write(path, {'synthetic': True})
        if kind == 'dashboard':
            write('payload.json', {'name': 'Reviewed'})
            write('ownership.json', {'query_keys': [], 'control_ids': [], 'container_keys': [], 'settings': [],
                'metadata': ['name'], 'tab_order': False, 'control_order': False})
        else:
            fixture.config = {'candidate_spec': 'spec.json', 'patch_path': 'patch.json', 'body_path': 'body.json'}
            body = {'html': HTML.replace('Before', 'Reviewed'), 'settings': copy.deepcopy(app.LOCKED_SETTINGS)}
            write('body.json', body)
            write('patch.json', {'htmlEdits': [{'search': '<h1>Before</h1>', 'replace': '<h1>Reviewed</h1>'}]})
            write('baseline.json', {'kind': app.INITIAL_BASELINE if kind == 'initial' else app.BASELINE,
                'requirements': adapter._pin('requirements.json'), 'body': adapter._pin('body.json'),
                'initial_body': body, 'semantic_sha256': 'a' * 64, 'semantic_snapshot': {}, 'bindings': [],
                'runtime': adapter._pin('runtime.json'), 'inspection': adapter.inspect()})
            write('spec.json', {'schema_version': 1,
                'kind': 'analyst_native_app_initial_spec' if kind == 'initial' else 'analyst_native_app_spec',
                'review_ref': 'synthetic-review', 'baseline_path': 'baseline.json',
                'requirements_path': 'requirements.json', 'body_path': 'body.json', 'patch_path': 'patch.json',
                'owned_regions': [{'start': '<!--owned:start-->', 'end': '<!--owned:end-->'}]})
        self.clear_calls(fixture)
        return fixture

    @staticmethod
    def clear_calls(fixture):
        fixture.fake.calls.clear()
        fixture.fake.http_calls.clear()

    def no_transport(self, fixture):
        self.assertEqual(fixture.fake.calls, [])
        self.assertEqual(fixture.fake.http_calls, [])
        self.assertEqual(fixture.fake.patch_count, 0)

    def prepare(self, fixture):
        if fixture.kind == 'dashboard':
            value = fixture.adapter.prepare('payload.json', ['source.json'], 'semantic.json', 'ownership.json', 'synthetic-review')
        elif fixture.kind == 'initial':
            value = fixture.adapter.prepare_initial(fixture.config['candidate_spec'])
        else:
            value = fixture.adapter.prepare(fixture.config['candidate_spec'])
        return value if isinstance(value, str) else value['candidate_sha256']

    def execute(self, fixture, candidate):
        operation = fixture.adapter.execute_initial if fixture.kind == 'initial' else fixture.adapter.execute
        return operation(candidate, 'synthetic-explicit-exact-candidate-authorization')

    def artifact(self, fixture):
        if fixture.kind == 'dashboard':
            return 'payload.json'
        if fixture.kind == 'initial':
            html = fixture.adapter._read(fixture.config['body_path'])['html']
        else:
            settings = fixture.adapter._read(fixture.config['candidate_spec'])
            html = app.apply_edits(fixture.fake.app['html'],
                fixture.adapter._read(fixture.config['patch_path']), settings['owned_regions'])
        path = 'deliverables/reviewed-app.html'
        (fixture.root / path).write_bytes(html.encode('utf-8'))
        return path

    def stage(self, fixture, artifact, iteration='one', outcome='resolved'):
        P.stage_record(fixture.root, {'stage': 'candidate', 'iteration_id': iteration,
            'builders': ['synthetic-engineer'], 'artifacts': [artifact]})
        if outcome:
            fixture.gates.reviews(outcome)

    def test_fresh_projects_and_missing_project_block_all_authoring_before_transport(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                with self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
                    self.prepare(fixture)
                with self.assertRaisesRegex(ValueError, 'predecessor_incomplete'):
                    self.execute(fixture, 'a' * 64)
                self.assertFalse((fixture.adapter.store / 'candidates').exists())
                self.assertFalse((fixture.adapter.store / 'executions').exists())
                self.no_transport(fixture)
                (fixture.root / 'project.json').unlink()
                with self.assertRaises(ValueError):
                    self.prepare(fixture)
                with self.assertRaises(ValueError):
                    self.execute(fixture, 'a' * 64)
                self.no_transport(fixture)

    def test_design_alone_and_unreviewed_candidate_do_not_allow_preparation(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                with P.trusted_stage_provider(fixture.gates.host):
                    fixture.gates.through()
                    with self.assertRaisesRegex(ValueError, 'current staged candidate artifact'):
                        self.prepare(fixture)
                    self.stage(fixture, self.artifact(fixture), outcome=None)
                    with self.assertRaisesRegex(ValueError, 'iteration_reviews_required'):
                        self.prepare(fixture)
                self.no_transport(fixture)

    def test_other_reviewed_bytes_cannot_authorize_preparation(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                (fixture.root / 'deliverables/other.txt').write_text('Different reviewed artifact')
                with P.trusted_stage_provider(fixture.gates.host):
                    fixture.gates.through()
                    self.stage(fixture, 'deliverables/other.txt')
                    with self.assertRaisesRegex(ValueError, 'current staged candidate artifact'):
                        self.prepare(fixture)
                self.no_transport(fixture)

    def test_reviewed_exact_content_prepares_and_executes_in_all_three_routes(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                with P.trusted_stage_provider(fixture.gates.host):
                    fixture.gates.through()
                    self.stage(fixture, self.artifact(fixture))
                    candidate = self.prepare(fixture)
                    prepared = fixture.adapter._candidate(candidate)
                    self.assertEqual(prepared['engagement']['candidate_sha256'],
                                     P.stage_status(fixture.root)['candidate_sha256'])
                    receipt = self.execute(fixture, candidate)
                self.assertEqual(receipt['status'], 'readback_matched')
                self.assertEqual(fixture.fake.patch_count, 1)

    def test_unresolved_review_blocks_execute_without_transport_or_intent(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                with P.trusted_stage_provider(fixture.gates.host):
                    fixture.gates.through()
                    self.stage(fixture, self.artifact(fixture), outcome='changes_requested')
                    candidate = self.prepare(fixture)
                    self.clear_calls(fixture)
                    with self.assertRaisesRegex(ValueError, 'resolved_reviews_required'):
                        self.execute(fixture, candidate)
                    self.assertFalse((fixture.adapter.store / 'executions').exists())
                    self.no_transport(fixture)

    def test_next_iteration_cannot_reuse_prepared_request_even_for_identical_bytes(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                with P.trusted_stage_provider(fixture.gates.host):
                    fixture.gates.through()
                    artifact = self.artifact(fixture)
                    self.stage(fixture, artifact)
                    candidate = self.prepare(fixture)
                    self.stage(fixture, artifact, iteration='two')
                    self.clear_calls(fixture)
                    with self.assertRaisesRegex(ValueError, 'stage binding changed'):
                        self.execute(fixture, candidate)
                    self.no_transport(fixture)

    def test_provider_loss_blocks_execute_before_transport(self):
        fixture = self.fixture('dashboard')
        with P.trusted_stage_provider(fixture.gates.host):
            fixture.gates.through()
            self.stage(fixture, self.artifact(fixture))
            candidate = self.prepare(fixture)
        self.clear_calls(fixture)
        with self.assertRaises(ValueError):
            self.execute(fixture, candidate)
        self.no_transport(fixture)

    def test_dashboard_embedded_payload_must_equal_the_reviewed_file(self):
        fixture = self.fixture('dashboard')
        with P.trusted_stage_provider(fixture.gates.host):
            fixture.gates.through()
            self.stage(fixture, self.artifact(fixture))
            candidate = self.prepare(fixture)
            record = fixture.adapter._candidate(candidate)
            record['payload']['name'] = 'Unreviewed replacement'
            record.pop('candidate_sha256')
            changed = native.digest(record)
            record['candidate_sha256'] = changed
            fixture.adapter._write(f'.omni-native/candidates/{changed}.json', record, exclusive=True)
            self.clear_calls(fixture)
            with self.assertRaisesRegex(ValueError, 'payload differs'):
                self.execute(fixture, changed)
            self.no_transport(fixture)

    def test_historical_pre_policy_projects_retain_existing_native_behavior(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                G.pre_policy_project(fixture.root, P)
                self.assertFalse(P.stage_status(fixture.root)['required'])
                candidate = self.prepare(fixture)
                self.assertNotIn('engagement', fixture.adapter._candidate(candidate))
                self.assertEqual(self.execute(fixture, candidate)['status'], 'readback_matched')

    def test_read_only_capability_probe_does_not_require_authoring_gates(self):
        for kind in ('dashboard', 'patch', 'initial'):
            with self.subTest(kind=kind):
                fixture = self.fixture(kind)
                (fixture.root / 'project.json').unlink()
                fixture.adapter.capabilities()
                self.assertEqual(fixture.fake.patch_count, 0)


if __name__ == '__main__':
    unittest.main()
