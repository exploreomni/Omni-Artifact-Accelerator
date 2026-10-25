"""Original offline inputs exercise preparation, not live authorization/behavior."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'skills/omni-app-engineer/scripts/native_authoring.py'
SPEC = importlib.util.spec_from_file_location('authoring', PATH)
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def fixture():
    target = {'base_url': 'https://example.omniapp.co', 'document_id': 'operations', 'draft_id': 'draft-1',
              'model_id': 'model-1', 'workbook_model_id': 'workbook-1', 'key_scope': 'organization',
              'user_id': 'user-1', 'membership_id': 'member-1'}
    return target, {'target': target, 'identity': {'keyScope': 'organization', 'orgRole': 'ORG_ADMIN',
                     'user': {'id': 'user-1', 'membershipId': 'member-1'}},
                   'draft': {'identifier': 'draft-1', 'publishedIdentifier': 'operations', 'status': 'active',
                             'draftOutOfDate': False, 'workbookModelId': 'workbook-1', 'branch': None},
                   'document': {'modelId': 'model-1', 'workbookModelId': 'workbook-1',
                                'app': {'url': '/api/v2/documents/operations/draft/draft-1/app'},
                                'queryPresentations': {'data': {'1': {'query': {'fields': ['jobs.id']}}}}},
                   'app': {'html': '<html>before</html>', 'settings': {'allowDownloads': False, 'safeDomains': []}}}


class Authoring(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve() / 'legacy'
        helper = PATH.parents[2] / 'omni-artifact-accelerator/scripts/analyst_project.py'
        spec = importlib.util.spec_from_file_location('native_legacy_project', helper)
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
        P.init(self.root, 'Existing pre-policy App repair', 'enhancement', 'app', 'none')
        legacy = P.load_project(self.root)[1]
        legacy.pop('stage_gate_policy')
        legacy.pop('workflow_quality_policy', None)
        P.write_json(self.root / 'project.json', legacy, replace=True)
        (self.root / 'deliverables/app.html').write_text('<html>after</html>')

    def prepare(self, target, before, current):
        return a.prepare_app(target, before, current, '<html>after</html>',
                             project=self.root, artifact='deliverables/app.html')

    def test_preparation_requires_engagement_and_candidate(self):
        target, before = fixture()
        with self.assertRaisesRegex(ValueError, 'Engagement'):
            a.prepare_app(target, before, before, '<html>after</html>')

    def test_cli_response_empty_wrong_shape_and_duplicates(self):
        for raw in (b'', b' ', b'{}', b'{"error":1,"error":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                a.decode(raw, 'object')
        self.assertEqual(a.decode(b'[]', 'list'), [])
        self.assertEqual(a.decode(b'{"identifier":"d"}', 'object')['identifier'], 'd')

    def test_exact_commands_not_guessed_aliases(self):
        record = {'cli_version': '1.0.6', 'help_sha256': 'a' * 64,
                  'available_commands': ['documents list-drafts'], 'required_commands': ['documents v2-list-drafts']}
        self.assertEqual(a.route_check(record)['status'], 'route_incomplete')
        record['required_commands'] = ['documents list-drafts']
        self.assertEqual(a.route_check(record)['status'], 'supplied_route_consistent')

    def test_query_envelope_preserves_semantics_and_membership(self):
        query = {'fields': ['jobs.id'], 'filters': {'jobs.status': {'is': 'open'}}, 'limit': 20,
                 'sorts': [], 'calculations': [], 'fill_fields': []}
        before = copy.deepcopy(query)
        body = a.query_body(query, 'workbook-1', 'member-1')
        self.assertEqual(query, before)
        self.assertEqual(body['query'], {**query, 'modelId': 'workbook-1'})
        self.assertNotIn('modelId', body)
        self.assertEqual(body['userId'], 'member-1')
        with self.assertRaises(ValueError):
            a.query_body({**query, 'modelId': 'wrong'}, 'workbook-1')
        for malformed in ({'fields': 'jobs.id'}, {'fields': [None]}, {'sql': True}, {'sql': ' '}, {'fields': ['']}):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                a.query_body(malformed, 'workbook-1')
        self.assertEqual(a.query_body({'fields': [], 'sql': 'SELECT ID FROM PRODUCTION.CURATED.JOBS'},
                                     'workbook-1')['query']['fields'], [])

    def test_physical_drift_cannot_be_hidden_by_requested_sql_comment(self):
        record = {'expected': {'database': 'PRODUCTION', 'schema': 'CURATED', 'fields': ['jobs.id']},
                  'planned_sql': "SELECT id, 'PRODUCTION.CURATED.JOBS' FROM DEV.CURATED.JOBS -- PRODUCTION.CURATED.JOBS",
                  'columns': [{'name': 'jobs.id', 'type': 'STRING'}], 'rows': [{'jobs.id': 'j1'}]}
        self.assertIn('physical_source_mismatch', a.plan_check(record)['findings'])
        record['planned_sql'] = 'SELECT a.ID FROM DEV/* source */.CURATED.JOBS a JOIN PRODUCTION.CURATED.JOBS b ON a.ID=b.ID'
        self.assertIn('physical_source_mismatch', a.plan_check(record)['findings'])
        record['planned_sql'] = 'SELECT id FROM "PRODUCTION"."CURATED"."JOBS"'
        self.assertEqual(a.plan_check(record)['status'], 'bounded_plan_consistent')
        record['rows'] = [{}]
        record['columns'] = []
        self.assertEqual(set(a.plan_check(record)['findings']), {'semantic_metadata_mismatch', 'result_keys_mismatch'})
        record['planned_sql'] = 'SELECT id FROM JOBS'
        self.assertIn('physical_references_unresolved', a.plan_check(record)['findings'])

    def test_existing_org_and_user_scoped_html_only_preparation(self):
        for scope in ('organization', 'user'):
            target, before = fixture()
            target['key_scope'] = scope
            before['identity']['keyScope'] = scope
            plan = self.prepare(target, before, copy.deepcopy(before))
            self.assertEqual(plan['request']['body'], {'html': '<html>after</html>'})
            self.assertFalse(plan['publication_authorized'])
            after = copy.deepcopy(before)
            after['app']['html'] = '<html>after</html>'
            self.assertEqual(a.verify_app(plan, before, after)['status'], 'exact_draft_readback')

    def test_preparation_rejects_changed_snapshot_and_wrong_target(self):
        target, before = fixture()
        for section, key, value in [('app', 'settings', {'allowDownloads': True}),
                                    ('draft', 'draftOutOfDate', True), ('draft', 'identifier', 'other')]:
            current = copy.deepcopy(before)
            current[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                self.prepare(target, before, current)
        for origin in ('http://example.omniapp.co', 'https://user:secret@example.omniapp.co',
                       'https://example.omniapp.co/api', 'https://example.omniapp.co?x=1'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                a.target_check({**target, 'base_url': origin})

    def test_readback_preserves_queries_settings_and_detects_tampering(self):
        target, before = fixture()
        plan = self.prepare(target, before, copy.deepcopy(before))
        after = copy.deepcopy(before)
        after['app']['html'] = '<html>after</html>'
        after['app']['settings']['allowDownloads'] = True
        after['document']['queryPresentations']['data']['1']['query']['fields'] = ['jobs.other']
        self.assertEqual(set(a.verify_app(plan, before, after)['findings']), {'settings_changed', 'document_or_queries_changed'})
        plan['request']['path'] = '/api/v2/documents/other/app'
        with self.assertRaises(ValueError):
            a.verify_app(plan, before, after)

    def test_cli_writes_new_private_artifact_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, output = root / 'input.json', root / 'output.json'
            source.write_text(json.dumps({'query': {'fields': ['jobs.id'], 'limit': 10}, 'model_id': 'm1'}))
            cmd = [sys.executable, '-I', '-S', '-B', str(PATH), 'query-body', '--input', str(source), '--output', str(output)]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(b'jobs.id', result.stdout)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, timeout=10).returncode, 0)
            alias = root / 'alias.json'
            alias.symlink_to(source)
            with self.assertRaises(ValueError):
                a.read(alias)


if __name__ == '__main__':
    unittest.main()
