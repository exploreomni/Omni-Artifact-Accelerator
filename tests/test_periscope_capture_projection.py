"""Supplied CDT projection/case checks; synthetic observations are not a pilot."""
import copy
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('periscope_capture_fixture', ROOT / 'tests/test_periscope_capture.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
C, V = G.C, G.V
T = G.load('translate_artifact')


def profile():
    return {'schema_version': 1, 'format': 'csv', 'encoding': 'utf-8', 'headers': ['place', 'value'],
            'subtotal_policy': 'preserve', 'columns': [
                {'ordinal': 0, 'name': 'place', 'type': 'string', 'nullable': False, 'null_tokens': []},
                {'ordinal': 1, 'name': 'value', 'type': 'number', 'nullable': False, 'null_tokens': [],
                 'decimal_separator': '.', 'group_separator': None, 'percent': False}]}


def case(capture, placement=None):
    return {'case_id': 'synthetic-quantity', 'lane': 'numeric', 'source_capture': {'path': 'capture.json'},
            'source_binding': {'object_key': 'quantity', 'placement_key': placement,
             'state_sha256': V.sha(capture['request']['state']),
             'definition_fingerprint': capture['source']['definition_fingerprint'], 'attachment_id': 'quantity-result'}}


def normalization_binding(capture):
    return {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': capture['source']['definition_fingerprint'],
            'object_key': 'quantity', 'attachment_id': 'quantity-result', 'state_sha256': V.sha(capture['request']['state']),
            'attachment_sha256': capture['attachments'][0]['sha256']}


class PeriscopeCaptureProjection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.no_network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network permitted'))
        self.no_network.start()
        req, result = G.prepare(self.root)
        self.raw = b'place,value\nWest,1.10\nEast,2.20\n'
        (self.root / 'supplied/result.csv').write_bytes(self.raw)
        self.result = C.import_evidence(Path(result['output']), G.evidence_spec(), self.root / 'supplied')
        self.capture = self.result['capture']

    def tearDown(self):
        self.no_network.stop()
        self.temp.cleanup()

    def projected(self):
        return T.translate(C.encoded(self.capture), 'periscope-capture')

    def asset(self, key='quantity'):
        return next(a for a in self.projected()['assets'] if a['source_id'] == key)

    def side(self):
        context = copy.deepcopy(self.capture['request']['state'])
        context.update(population='all-garden-rows', data_watermark='fixture-v1', freshness_reference='synthetic watermark',
                       result_scope='query_result')
        return {'file': self.capture['attachments'][0], 'format': 'csv', 'context': context,
                'complete': True, 'completeness_reference': 'synthetic exact two-row fixture'}

    def test_projection_preserves_primary_visual_controls_and_multiple_placements(self):
        result = self.projected()
        self.assertEqual(self.capture, result['upstream_payload'])
        counts = result['periscope_coverage']
        self.assertEqual((1, 1, 2), (counts['visuals'], counts['controls'], counts['placements']))
        self.assertEqual('not_established', counts['source_export_completeness'])
        self.assertEqual('not_verified', counts['behavior_coverage'])
        self.assertEqual(1, sum(a['kind'] == 'visual' for a in result['assets']))
        self.assertTrue(all(a['kind'] == 'definition' for a in result['assets'] if a['source_identity'].get('adapter_evidence_only')))
        self.assertTrue(self.asset('place-one')['source_identity']['query_visual'])
        self.assertEqual('quantity', self.asset('place-two')['source_identity']['visual_key'])
        self.assertEqual('d' * 32, self.asset('board')['source_identity']['identity_crosswalk']['git_token'])
        self.assertFalse(result['build_authority'])
        self.assertFalse(result['migration_context']['build_authority'])
        self.assertFalse(result['migration_context']['target_write_authority'])
        self.assertEqual('not_established', result['migration_context']['native_validation'])

    def test_case_rejects_wrong_object_placement_revision_and_stale_state(self):
        self.assertEqual('quantity', V.case_binding(self.asset(), case(self.capture), self.capture)['object_key'])
        V.case_binding(self.asset('place-one'), case(self.capture, 'place-one'), self.capture)
        for mutate in [lambda v: v['source_binding'].update(object_key='board'),
                       lambda v: v['source_binding'].update(placement_key='place-two'),
                       lambda v: v['source_binding'].update(state_sha256='0' * 64),
                       lambda v: v['source_binding'].update(attachment_id='unknown')]:
            bad = case(self.capture)
            mutate(bad)
            with self.assertRaises(ValueError):
                V.case_binding(self.asset(), bad, self.capture)
        bad_asset = self.asset()
        bad_asset['source_identity']['source_revision']['value'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'source_identity'):
            V.case_binding(bad_asset, case(self.capture), self.capture)

    def test_csv_normalization_preserves_decimal_null_and_duplicate_headers_require_mapping(self):
        normalized = V.normalize_results(self.raw, profile(), normalization_binding(self.capture))
        self.assertEqual('periscope_normalized_results', normalized['kind'])
        self.assertEqual([{'place': 'West', 'value': '1.10'}, {'place': 'East', 'value': '2.20'}], normalized['rows'])
        self.assertEqual('not_established', normalized['completeness'])
        raw = b'place,value\nWest,NULL\n'
        binding = normalization_binding(self.capture)
        binding['attachment_sha256'] = V.sha(raw)
        p = profile()
        p['columns'][1].update(nullable=True, null_tokens=['NULL'])
        self.assertIsNone(V.normalize_results(raw, p, binding)['rows'][0]['value'])
        p['columns'][1]['nullable'] = False
        with self.assertRaises(ValueError):
            V.normalize_results(raw, p, binding)
        with self.assertRaises(ValueError):
            V.normalize_results(raw, {**p, 'format': 'json'}, binding)
        raw = b'place,place\nWest,1\n'
        binding['attachment_sha256'] = V.sha(raw)
        p = profile()
        p['headers'] = ['place', 'place']
        with self.assertRaisesRegex(ValueError, 'duplicate_headers'):
            V.normalize_results(raw, p, binding)

    def test_normalization_binding_cannot_relabel_other_source_file(self):
        for field in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'):
            binding = normalization_binding(self.capture)
            binding[field] = 'not-a-pin'
            with self.assertRaisesRegex(ValueError, 'normalization_binding'):
                V.normalize_results(self.raw, profile(), binding)
        source, target = self.side(), self.side()
        normal = V.normalize_results(self.raw, profile(), normalization_binding(self.capture))
        source.update(format='periscope-normalized', raw_file=source['file'])
        normal['binding']['object_key'] = 'different-visual'
        gaps = V.comparison_gaps(self.capture, self.asset(), case(self.capture), source, target, normal)
        self.assertIn('source.periscope_normalization_binding_mismatch', gaps)

    def test_complete_supplied_context_has_no_extra_numeric_gaps_without_render(self):
        source, target = self.side(), self.side()
        C.check_capture(Path(self.result['output']))
        self.assertEqual([], V.comparison_gaps(self.capture, self.asset(), case(self.capture), source, target))
        self.assertEqual([], [a for a in self.capture['attachments'] if a['format'] == 'pdf'])
        self.assertEqual('not_performed', self.capture['native_validation'])

    def test_unknown_origin_or_missing_observation_freshness_population_blocks(self):
        for field, replacement, wanted in [
            ('origin', 'unknown', 'source.periscope_result_origin_unverified'),
            ('observed_state', None, 'source.periscope_observed_state_missing'),
            ('freshness', {'data_watermark': None, 'observed_at': None, 'reference': None}, 'source.periscope_context.data_watermark'),
            ('population', {'key': None, 'description': None, 'reference': None}, 'source.periscope_context.population')]:
            capture = copy.deepcopy(self.capture)
            a = capture['attachments'][0]
            a[field] = replacement
            a['completeness']['status'] = 'unknown'
            capture['content_hash'] = V.sha({k: v for k, v in capture.items() if k != 'content_hash'})
            gaps = V.comparison_gaps(capture, self.asset(), case(capture), self.side(), self.side())
            self.assertIn(wanted, gaps)
            self.assertIn('source.periscope_completeness_unverified', gaps)

    def test_displayed_and_transformed_population_cannot_masquerade_as_query_results(self):
        for mode in ('displayed', 'transformed'):
            capture = copy.deepcopy(self.capture)
            a = capture['attachments'][0]
            a.update(origin=mode, result_scope=mode)
            capture['content_hash'] = V.sha({k: v for k, v in capture.items() if k != 'content_hash'})
            gaps = V.comparison_gaps(capture, self.asset(), case(capture), self.side(), self.side())
            self.assertIn('source.periscope_context.result_scope', gaps)
            self.assertIn('context.result_scope', gaps)

    def chart_code_capture(self, label, *, language='python', chart_bound=True, configured=False, transformed=False):
        run = self.root / label
        run.mkdir()
        req, _ = G.prepare(run)
        supplied = run / 'supplied'
        report = C.F.decode((supplied / 'adapter.json').read_bytes())
        if configured:
            # Keep the new native configuration and its original YAML hash coherent.
            chart = next(row for row in report['objects'] if row['id'] == 'adapter-v')
            chart['details']['native_configuration']['code_language'] = language
            path = 'dashboards/chart.yaml'
            raw = ('chart_type: bar\ncode_language: ' + language + '\n').encode()
            (supplied / path).write_bytes(raw)
            next(row for row in report['source_files'] if row['path'] == path)['sha256'] = V.sha(raw)
            chart['evidence']['sha256'] = V.sha(raw)
        else:
            # This is an inert expression record, not an import or execution.
            path = 'modules/inert.py'
            raw = (supplied / path).read_bytes()
            occurrence = 'periscope:occurrence:' + V.sha(json.dumps(['expressions', path, '$', 0], ensure_ascii=True).encode())[:24]
            report['expressions'].append({'id': 'expr-post-query', 'object_id': 'adapter-v' if chart_bound else None,
                'language': language, 'text': raw.decode(), 'content_sha256': V.sha(raw),
                'evidence': {'path': path, 'locator': '$', 'sha256': V.sha(raw)}, 'details': {}, 'occurrence_id': occurrence})
        (supplied / 'adapter.json').write_bytes(C.encoded(report))
        result = C.import_local(req, supplied, run / 'qualified-capture', allow_source_read=True)
        (supplied / 'result.csv').write_bytes(self.raw)
        evidence = G.evidence_spec()
        if transformed:
            evidence['attachments'][0].update(origin='transformed', result_scope='transformed')
        result = C.import_evidence(Path(result['output']), evidence, supplied)
        C.check_capture(Path(result['output']))
        return result['capture']

    def test_chart_python_r_requires_transformed_results_for_visual_and_placement(self):
        variants = [('python-expression', 'python', False), ('r-expression', 'r', False),
                    ('python-config', 'python3.6', True), ('r-config', 'r3.2', True)]
        for label, language, configured in variants:
            for transformed in (False, True):
                with self.subTest(language=language, configured=configured, transformed=transformed):
                    capture = self.chart_code_capture(label + ('-transformed' if transformed else '-sql'),
                        language=language, configured=configured, transformed=transformed)
                    projection = T.translate(C.encoded(capture), 'periscope-capture')
                    for key, placement in [('quantity', None), ('place-one', 'place-one')]:
                        asset = next(a for a in projection['assets'] if a['source_id'] == key)
                        source, target = self.side(), self.side()
                        source['file'] = capture['attachments'][0]
                        if transformed:
                            source['context']['result_scope'] = target['context']['result_scope'] = 'transformed'
                        gaps = V.comparison_gaps(capture, asset, case(capture, placement), source, target)
                        if transformed:
                            self.assertEqual([], gaps)
                        else:
                            self.assertEqual(['source.periscope_chart_transformed_results_required'], gaps)

    def test_unbound_python_dependency_does_not_relabel_sql_chart_output(self):
        capture = self.chart_code_capture('unbound-python', chart_bound=False)
        projection = T.translate(C.encoded(capture), 'periscope-capture')
        source, target = self.side(), self.side()
        source['file'] = capture['attachments'][0]
        for key, placement in [('quantity', None), ('place-one', 'place-one')]:
            asset = next(a for a in projection['assets'] if a['source_id'] == key)
            self.assertEqual([], V.comparison_gaps(capture, asset, case(capture, placement), source, target))

    def test_resigned_envelope_cannot_override_original_definition_or_counts(self):
        for mutate in [lambda v: v['source']['inventory']['objects'][1].update(name='changed'),
                       lambda v: v['source']['files'][0].update(sha256='0' * 64),
                       lambda v: v.update(target_write_authority=True),
                       lambda v: v['attachments'][0]['completeness'].update(row_count=99)]:
            bad = copy.deepcopy(self.capture)
            mutate(bad)
            bad['content_hash'] = V.sha({k: v for k, v in bad.items() if k != 'content_hash'})
            with self.assertRaises(ValueError):
                V.verify_capture_files(bad, self.root / 'capture')


if __name__ == '__main__':
    unittest.main()
