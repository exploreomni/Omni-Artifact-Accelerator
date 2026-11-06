"""Synthetic visible-data contract checks; no native execution or numerical proof."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/omni-artifact-accelerator/scripts'


def module(name):
    spec = importlib.util.spec_from_file_location('consumer_test_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


P, N, R = module('analyst_project'), module('native_data_consumers'), module('data_refresh')


class ConsumerContractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        P.init(self.root, 'Inspection workspace', 'net-new', 'app')
        project, _ = P.read_json(self.root / 'project.json')
        project['app_release_policy'] = N.POLICY
        P.write_json(self.root / 'project.json', project, replace=True)
        self.html = ('<main><section id="total" data-oaa-consumer="total-panel"></section>'
                     '<section id="detail" data-oaa-consumer="detail-panel"></section>'
                     '<section id="archive" data-oaa-consumer="archive-panel">Snapshot · Period A · Retained inspection export</section>'
                     '<section id="scenario" data-oaa-consumer="scenario-panel">Scenario estimate</section></main>'
                     '<script>bind("total-panel","1");bind("detail-panel","2");'
                     'estimate("scenario-panel","total-panel","detail-panel");</script>')
        self.presentations = {'order': ['1', '2'], 'data': {key: {
            'type': 'query', 'isSql': False, 'topicName': 'inspection', 'name': 'Inspection ' + key,
            'query': {'fields': ['inspection.id', 'inspection.value'], 'filters': {'inspection.area': 'A'},
                      'table': 'inspection', 'limit': 20}} for key in ('1', '2')}}
        expected = self.put('evidence/independent.json', {'method': 'independent_calculation', 'total': 12})
        common = {'expectation': expected, 'expectation_basis': 'independent_calculation'}
        consumers = [{**common, 'id': ident, 'element_id': element, 'mode': 'live', 'sources': [{
            'query_key': key, 'fields': ['inspection.value'],
            'tile_sha256': P.digest(P.canonical(self.presentations['data'][key])),
            'script_fragment': 'bind("' + ident + '","' + key + '")'}]}
            for ident, element, key in [('total-panel', 'total', '1'), ('detail-panel', 'detail', '2')]]
        consumers += [{**common, 'id': 'archive-panel', 'element_id': 'archive', 'mode': 'snapshot',
                       'label': 'Snapshot', 'period': 'Period A', 'source_label': 'Retained inspection export',
                       'source': self.put('inputs/snapshot.json', {'period': 'A', 'value': 11})},
                      {**common, 'id': 'scenario-panel', 'element_id': 'scenario', 'mode': 'scenario',
                       'label': 'Scenario estimate', 'base_consumer_ids': ['total-panel', 'detail-panel'],
                       'assumptions': self.put('inputs/assumptions.json', {'factor': 1.1}),
                       'script_fragment': 'estimate("scenario-panel","total-panel","detail-panel")'}]
        self.policy = R.policy({'kind': 'app_data_refresh', 'mode': 'no_custom_policy'})
        self.manifest = {'schema_version': 1, 'kind': 'native_data_consumers', 'document_id': 'inspection-app',
                         'html_sha256': P.digest(self.html.encode()),
                         'presentations_sha256': P.digest(P.canonical(self.presentations)),
                         'refresh_policy': self.policy, 'consumers': consumers}
        self.selected = {'spec': {'surfaces': ['app'], 'product': {'note_paths': ['inputs/brief.txt'],
            'data_refresh': {'schema_version': 1, 'requirement_id': 'freshness'}},
            'requirements': [{'id': 'freshness', 'category': 'interaction', 'purpose': 'Display age honestly',
                'required': True, 'surfaces': ['app'], 'origin': 'user', 'disposition': 'selected',
                'decision_ref': 'inputs/brief.txt', 'value': {'kind': 'app_data_refresh', 'mode': 'no_custom_policy'},
                'product': {'basis': 'user_statement', 'source_refs': ['inputs/brief.txt'],
                            'acceptance': ['Initial and manual refresh only']}}]}}

    def put(self, path, value):
        raw = P.canonical(value)
        (self.root / path).write_bytes(raw)
        return {'path': path, 'sha256': P.digest(raw)}

    def inspect(self, manifest=None, **kwargs):
        args = {'document_id': 'inspection-app', 'app_html': self.html,
                'presentations': self.presentations, 'refresh_policy': self.policy, 'P': P}
        return N.inspect(self.manifest if manifest is None else manifest, **{**args, **kwargs})

    def guard(self, reviewed=None):
        current = self.put(N.MANIFEST, self.manifest)
        with patch.object(P, 'intent_helper', return_value=SimpleNamespace(load_selected=lambda _: self.selected)):
            return N.guard(self.root, P, document_id='inspection-app', app_html=self.html,
                           presentations=self.presentations, reviewed_artifacts=[current] if reviewed is None else reviewed)

    def test_every_later_query_and_classification_is_source_bound_only(self):
        result = self.guard()
        self.assertEqual(result['consumer_count'], 4)
        self.assertEqual([row['query_key'] for row in result['bindings']], ['1', '2'])
        self.assertEqual(result['status'], 'source_bound')
        for lane in ('runtime_verified', 'numerical_verified', 'visual_coverage_verified', 'access_verified'):
            self.assertIs(result[lane], False)
        self.assertNotIn('evidence', result)

    def test_second_consumer_missing_callback_or_binding_blocks(self):
        bad = copy.deepcopy(self.manifest)
        bad['consumers'].pop(1)
        with self.assertRaisesRegex(ValueError, 'unmapped_visible_consumer'):
            self.inspect(bad)
        bad = copy.deepcopy(self.manifest)
        bad['consumers'][1]['sources'][0]['script_fragment'] = 'bind("detail-panel","1")'
        with self.assertRaisesRegex(ValueError, 'callback_fragment_missing'):
            self.inspect(bad)
        bad['consumers'][1]['sources'][0]['script_fragment'] = 'bind("detail-panel","2")'
        bad['consumers'][1]['sources'][0]['fields'] = ['inspection.other']
        with self.assertRaisesRegex(ValueError, 'consumer_field_missing'):
            self.inspect(bad)

    def test_exact_candidate_and_complete_query_collection_required(self):
        with self.assertRaisesRegex(ValueError, 'candidate_html_changed'):
            self.inspect(app_html=self.html + ' ')
        changed = copy.deepcopy(self.presentations)
        changed['data']['2']['query']['filters'] = {'inspection.area': 'B'}
        with self.assertRaisesRegex(ValueError, 'saved_queries_changed'):
            self.inspect(presentations=changed)
        changed['order'] = ['1']
        with self.assertRaisesRegex(ValueError, 'complete_presentations_required'):
            self.inspect(presentations=changed)

    def test_existing_named_query_key_preserved_exactly(self):
        self.presentations['data']['saved-detail'] = self.presentations['data'].pop('2')
        self.presentations['order'][1] = 'saved-detail'
        self.html = self.html.replace('"detail-panel","2"', '"detail-panel","saved-detail"')
        self.manifest['html_sha256'] = P.digest(self.html.encode())
        self.manifest['presentations_sha256'] = P.digest(P.canonical(self.presentations))
        source = self.manifest['consumers'][1]['sources'][0]
        source.update(query_key='saved-detail', script_fragment='bind("detail-panel","saved-detail")')
        self.assertEqual(self.guard()['bindings'][1]['query_key'], 'saved-detail')

    def test_snapshot_labels_and_independent_originals_are_required(self):
        for field in ('label', 'period', 'source_label'):
            bad = copy.deepcopy(self.manifest)
            bad['consumers'][2][field] = 'not present'
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.inspect(bad)
        bad = copy.deepcopy(self.manifest)
        bad['consumers'][2]['expectation'] = {**bad['consumers'][2]['source'], 'path': 'evidence/copied.json'}
        with self.assertRaisesRegex(ValueError, 'independent_expectation_is_source'):
            self.inspect(bad)
        (self.root / 'inputs/snapshot.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'original_evidence_missing_or_changed'):
            self.guard()

    def test_scenario_never_self_justifies_or_uses_unknown_base(self):
        bad = copy.deepcopy(self.manifest)
        bad['consumers'][3]['base_consumer_ids'] = ['scenario-panel']
        with self.assertRaisesRegex(ValueError, 'scenario_base_missing_or_recursive'):
            self.inspect(bad)
        bad['consumers'][3]['base_consumer_ids'] = ['unknown']
        with self.assertRaises(ValueError):
            self.inspect(bad)
        bad = copy.deepcopy(self.manifest)
        bad['consumers'][3]['expectation_basis'] = 'same_query'
        with self.assertRaisesRegex(ValueError, 'independent_expectation_required'):
            self.inspect(bad)

    def test_hidden_duplicate_and_inert_source_bindings_rejected(self):
        for html in (self.html.replace('<main>', '<main hidden>'),
                     self.html.replace('id="detail"', 'id="total"'),
                     self.html.replace('<script>', '<script type="application/json">'),
                     self.html.replace('<script>', '<script src="local.js">')):
            bad = {**self.manifest, 'html_sha256': P.digest(html.encode())}
            with self.subTest(html=html[:40]), self.assertRaises(ValueError):
                self.inspect(bad, app_html=html)

    def test_freeze_requires_current_bytes_including_retained_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'freeze_and_review_current_consumer_manifest'):
            self.guard(reviewed=[])
        retained = self.put('evidence/frozen-consumers.json', self.manifest)
        self.assertEqual(self.guard(reviewed=[retained])['status'], 'source_bound')
        (self.root / retained['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'reviewed_consumer_manifest_changed'):
            self.guard(reviewed=[retained])
        self.manifest['consumers'][0]['expectation_basis'] = 'independent_query'
        with self.assertRaisesRegex(ValueError, 'freeze_and_review_current_consumer_manifest'):
            self.guard(reviewed=[retained])

    def test_selected_refresh_meaning_never_defaults_or_changes(self):
        self.selected['spec']['requirements'][0]['disposition'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'recover_existing_refresh_question'):
            self.guard()
        self.selected['spec']['requirements'][0]['disposition'] = 'selected'
        self.manifest['refresh_policy'] = {**self.policy, 'query_cache': 'bypass'}
        with self.assertRaisesRegex(ValueError, 'selected_refresh_policy_changed'):
            self.guard()

    def test_legacy_is_unassessed_and_unknown_policy_cannot_opt_out(self):
        project, _ = P.read_json(self.root / 'project.json')
        project.pop('app_release_policy')
        P.write_json(self.root / 'project.json', project, replace=True)
        self.assertEqual(N.guard(self.root, P, document_id='', app_html='', presentations={})['status'], 'not_assessed')
        project['app_release_policy'] = 'disabled'
        P.write_json(self.root / 'project.json', project, replace=True)
        with self.assertRaisesRegex(ValueError, 'invalid_app_release_policy|unsupported_policy'):
            N.guard(self.root, P, document_id='', app_html='', presentations={})

    def test_evidence_cannot_escape_private_paths_or_use_symlink(self):
        for path in ('../secret', '/secret', 'evidence/../secret', 'contracts/current.json'):
            bad = copy.deepcopy(self.manifest)
            bad['consumers'][0]['expectation']['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.inspect(bad)
        target = self.root / 'inputs/snapshot.json'
        saved = target.read_bytes()
        target.unlink()
        external = self.root.parent / 'external.json'
        external.write_bytes(saved)
        target.symlink_to(external)
        with self.assertRaises(ValueError):
            self.guard()


if __name__ == '__main__':
    unittest.main()
