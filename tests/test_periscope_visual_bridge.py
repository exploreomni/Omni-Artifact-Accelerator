"""Original synthetic CDT adapter reports; no DMA imports or source execution.

Shapes and occurrence identities are derived from read-only inspection of DMA's
base/periscope/registry source at REVISION, not from running its optional parsers.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/omni-artifact-translator/scripts/translate_artifact.py'
REVISION = 'a88f2a3b4dd0cfa596766f938961f37d673cf9b9'
spec = importlib.util.spec_from_file_location('periscope_bridge_translator_test', SCRIPT)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def occurrence(category, path, locator, ordinal):
    return 'periscope:occurrence:' + sha(json.dumps([category, path, locator, ordinal], ensure_ascii=True))[:24]


def fixture(native_chart=True):
    """Hand-authored report over fictional garden data, with explicit gaps."""
    dashboard_token, chart_token = 'd' * 32, 'c' * 32
    folder = 'dashboards/Garden.' + dashboard_token
    chart_folder = folder + '/Weekly.' + chart_token
    dashboard_path, chart_path = folder + '/Garden.yaml', chart_folder + '/Weekly.yaml'
    sql_path, python_path = chart_folder + '/Weekly.sql', chart_folder + '/Weekly.py'
    orphan_path = folder + '/Detached.' + 'e' * 32 + '/Detached.sql'
    files = {
        dashboard_path: 'display_name: Garden\ndashboard_preferences:\n  settings:\n    owner: synthetic\n',
        chart_path: 'display_name: Weekly\nchart_type: line\ndatabase_name: fictional\n',
        sql_path: 'select day, sum(observations) from [garden_rows] group by 1\n',
        python_path: 'import imaginary_dependency\nraise RuntimeError("INERT_SOURCE_SENTINEL")\n',
        orphan_path: 'select 1 as detached_observation\n',
        'notes/uninterpreted.txt': 'Unsupported synthetic source must remain an obligation.\n',
        'views/.gitkeep': '',
    }

    def evidence(path, locator='$'):
        return {'path': path, 'locator': locator, 'sha256': sha(files[path])}

    def ident(category, path, locator, name):
        return 'periscope:' + category + ':' + sha(json.dumps([path, locator, str(name)], ensure_ascii=True))[:24]

    def obj(path, kind, name, native_id=None, locator='$', **details):
        return {'id': ident('object', path, locator, native_id if native_id is not None else name),
                'native_id': native_id, 'kind': kind, 'name': name,
                'evidence': evidence(path, locator), 'details': details}

    dashboard = obj(dashboard_path, 'dashboard', 'Garden', dashboard_token,
        native_path=folder, format_version='unversioned_cdt_git', native_configuration={
            'display_name': 'Garden', 'disable_filters': False,
            'configured_filters': {'visible': [{'Season': {'default': 'spring'}}]},
            'dashboard_preferences': {'settings': {'owner': 'synthetic'}}})
    chart = obj(chart_path, 'chart', 'Weekly', chart_token if native_chart else None,
        native_path=chart_folder, format_version='unversioned_cdt_git', native_configuration={
            'display_name': 'Weekly', 'chart_type': 'line', 'database_name': 'fictional',
            'code_language': 'python3', 'position': {'row': 2, 'column': 1},
            'size': {'width': 6, 'height': 4}, 'color_theme': 'synthetic-muted',
            'encrypted_definition': 'opaque-synthetic-settings', 'advanced': {'unknown_setting': 7}})
    control = obj(dashboard_path, 'filter', 'Season', locator='$.configured_filters.visible[0]',
        parent_id=dashboard['id'], visibility='visible', native_configuration={'default': 'spring'})
    orphan = obj(orphan_path, 'source_artifact', 'Detached', locator='$orphan',
        owning_configuration='missing_or_invalid')

    def expression(path, language, owner=None, locator='$', text=None, interpretation='preserved_original'):
        content = files[path] if text is None else text
        return {'id': ident('expression', path, locator, content), 'object_id': owner,
                'language': language, 'text': content, 'evidence': evidence(path, locator),
                'details': {'interpretation': interpretation}, 'content_sha256': sha(content)}

    def dependency(path, owner, target, kind, resolution, locator='$'):
        return {'source_id': owner, 'target': target, 'evidence': evidence(path, locator),
                'details': {'kind': kind, 'resolution': resolution}}

    gap_specs = [(dashboard_path, 'periscope.export_incomplete'),
                 (dashboard_path, 'periscope.inherited_filters_missing'),
                 (chart_path, 'periscope.encrypted_definition'),
                 (sql_path, 'periscope.template_unresolved'),
                 (python_path, 'periscope.code_not_interpreted'),
                 (orphan_path, 'periscope.configuration_missing'),
                 ('notes/uninterpreted.txt', 'periscope.unsupported_format')]
    result = {'schema_version': 1, 'kind': 'source_adapter_result', 'source': 'periscope',
        'adapter_version': 1, 'component_sha256': sha('synthetic producer component declaration'),
        'source_files': [{'path': path, 'sha256': sha(content),
            'status': 'parsed' if path == 'views/.gitkeep' else 'unsupported' if path.startswith('notes/') else 'partial',
            'reason': 'Synthetic supplied-file disposition, not complete export evidence.'}
            for path, content in sorted(files.items())],
        'objects': [dashboard, chart, control, orphan],
        'expressions': [expression(dashboard_path, 'yaml'), expression(chart_path, 'yaml'),
            expression(sql_path, 'sql', chart['id'], '$sql'),
            expression(python_path, 'python', chart['id'], '$code'),
            expression(dashboard_path, 'periscope_filter', control['id'], '$.configured_filters.visible[0]',
                       json.dumps({'Season': {'default': 'spring'}}), 'preserved_declaration'),
            expression(orphan_path, 'sql', orphan['id'], '$sql')],
        'dependencies': [dependency(chart_path, chart['id'], dashboard['id'], 'contained_in', 'declared'),
            dependency(dashboard_path, dashboard['id'], control['id'], 'configured_filter', 'declared',
                       '$.configured_filters.visible[0]'),
            dependency(sql_path, chart['id'], 'garden_rows', 'native_reference_candidate', 'unresolved', '$sql.offset[40:53]'),
            dependency(python_path, chart['id'], 'imaginary_dependency', 'module_reference_candidate', 'unresolved', 'line:1')],
        'gaps': [{'code': code, 'message': 'Original synthetic uncertainty: ' + code,
                  'evidence': evidence(path)} for path, code in gap_specs],
        'export_completeness': 'not_established', 'native_validation': 'not_run',
        'execution_performed': False,
        'limitations': ['Synthetic contract only; source files, native behavior and export completeness are unverified.']}
    result['coverage_summary'] = {'unit': 'supplied_source_files', 'expected': len(files),
        'observed': len(files), 'missing': 0,
        'statuses': {status: sum(row['status'] == status for row in result['source_files'])
                     for status in ('parsed', 'partial', 'unsupported')}}
    for category in ('objects', 'expressions', 'dependencies', 'gaps'):
        seen = {}
        for row in result[category]:
            path, locator = row['evidence']['path'], row['evidence']['locator']
            ordinal = seen.get((path, locator), 0)
            row['occurrence_id'] = occurrence(category, path, locator, ordinal)
            seen[(path, locator)] = ordinal + 1
    return result


class PeriscopeVisualBridge(unittest.TestCase):
    def parse(self, value=None, revision=REVISION):
        value = fixture() if value is None else value
        with mock.patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')):
            return T.translate(json.dumps(value, ensure_ascii=False).encode(), 'periscope-adapter', revision)

    def test_actual_shaped_objects_configs_expressions_and_coverage_are_preserved(self):
        original = fixture()
        before = copy.deepcopy(original)
        result = self.parse(original)
        self.assertEqual(original, before)
        self.assertEqual(result['upstream_payload'], original)
        self.assertEqual(result['upstream_expressions'], original['expressions'])
        self.assertEqual(result['source']['upstream_files'], original['source_files'])
        self.assertEqual(result['upstream_coverage'], original['coverage_summary'])
        self.assertEqual(len(result['assets']), 11)  # Four objects and all seven supplied files.
        objects = {a['source_id']: a for a in result['assets'] if a['source_id'] is not None}
        chart = objects[original['objects'][1]['id']]
        self.assertEqual(chart['kind'], 'visual')
        self.assertEqual(chart['source_payload'], original['objects'][1])
        self.assertEqual(chart['facets']['layout']['value'], {'position': {'row': 2, 'column': 1},
                                                              'size': {'width': 6, 'height': 4}})
        self.assertEqual(chart['facets']['visual']['value']['encrypted_definition'], 'opaque-synthetic-settings')
        self.assertEqual({e['language'] for e in chart['facets']['query']['value']}, {'sql', 'python'})
        self.assertIn('INERT_SOURCE_SENTINEL', chart['facets']['query']['value'][1]['text'])
        self.assertEqual(objects[original['objects'][2]['id']]['facets']['filters']['value'],
                         original['objects'][2]['details'])
        self.assertEqual(objects[original['objects'][3]['id']]['kind'], 'definition')
        self.assertIn('notes/uninterpreted.txt', {a['source_identity'].get('source_file') for a in result['assets']})

    def test_generated_identity_is_distinct_from_native_or_missing_native_identity(self):
        for native in (True, False):
            with self.subTest(native=native):
                value = fixture(native_chart=native)
                result = self.parse(value)
                chart = next(a for a in result['assets'] if a['kind'] == 'visual')
                self.assertEqual(chart['source_id'], value['objects'][1]['id'])
                self.assertEqual(chart['source_identity']['id_kind'], 'adapter_generated_id')
                self.assertEqual(chart['source_identity']['native_id'], 'c' * 32 if native else None)
                self.assertNotEqual(chart['source_id'], chart['source_identity']['native_id'])
                self.assertEqual(chart['source_identity']['adapter_occurrence_id'], value['objects'][1]['occurrence_id'])
                if not native:
                    self.assertIn('periscope.native_id_unavailable', {g['code'] for g in result['gaps']})

    def test_uncertain_dependencies_and_non_authority_claims_remain_explicit(self):
        value = fixture()
        # A target can exist while its relationship still remains only a candidate.
        value['dependencies'][2]['target'] = value['objects'][0]['id']
        value['dependencies'][2]['details']['resolution'] = 'candidate'
        result = self.parse(value)
        self.assertEqual(result['dependencies'], value['dependencies'])
        uncertain = [g for g in result['gaps'] if g['code'] == 'periscope.dependency_requires_review']
        self.assertEqual({g['source_path'] for g in uncertain}, {'/dependencies/2', '/dependencies/3'})
        self.assertFalse(result['build_authority'])
        self.assertFalse(result['source_execution'])
        self.assertEqual(result['network_calls'], 0)
        self.assertEqual(result['native_validation'], 'not_run')
        self.assertEqual(result['export_completeness'], 'not_established')
        self.assertEqual(result['coverage']['denominator'], 'supplied_artifact_only')
        self.assertEqual(result['source']['producer']['revision_evidence'], 'operator_declared_not_authenticated')
        for code in ('source_files_not_reverified', 'visual_denominator_not_established',
                     'effective_access_not_exported', 'render_and_result_capture_not_implemented'):
            self.assertIn('periscope.' + code, {g['code'] for g in result['gaps']})

    def test_unsupported_producer_product_schema_or_execution_claims_reject(self):
        for revision in (None, '', '0' * 40, T.DMA_REVISION):
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, 'producer_revision'):
                self.parse(revision=revision)
        variants = [('source', 'sisense_fusion'), ('kind', 'sisense_dashboard_export'),
                    ('schema_version', 2), ('schema_version', True), ('adapter_version', 2),
                    ('execution_performed', True), ('native_validation', 'passed'),
                    ('export_completeness', 'complete')]
        for field, value in variants:
            candidate = fixture(); candidate[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.parse(candidate)

    def test_structured_credentials_reject_and_source_text_stays_inert(self):
        for field in ('access_token', 'Authorization', 'api-key', 'credentials'):
            value = fixture()
            value['objects'][1]['details']['native_configuration'][field] = 'SYNTHETIC_SECRET_MARKER'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'credential_bearing_input'):
                self.parse(value)
        value = fixture()
        value['objects'][1]['details']['native_configuration']['access_token'] = '[REDACTED]'
        result = self.parse(value)
        self.assertIn('raise RuntimeError', result['upstream_expressions'][3]['text'])
        self.assertFalse(result['source_execution'])

    def test_hash_evidence_coverage_and_occurrence_contradictions_reject(self):
        mutations = [
            (lambda v: v['expressions'][2].update(content_sha256='0' * 64), 'expression_hash'),
            (lambda v: v['objects'][0]['evidence'].update(sha256='0' * 64), 'evidence_mismatch'),
            (lambda v: v['objects'][0]['evidence'].update(path='missing.yaml'), 'evidence_mismatch'),
            (lambda v: v['coverage_summary'].update(expected=999), 'coverage_mismatch'),
            (lambda v: v['coverage_summary'].update(missing=False), 'coverage_mismatch'),
            (lambda v: v['coverage_summary']['statuses'].update(parsed=99), 'coverage_mismatch'),
            (lambda v: v.update(component_sha256='not-a-hash'), 'component_hash'),
            (lambda v: v['objects'][0].update(occurrence_id='periscope:occurrence:' + 'f' * 24), 'occurrence'),
        ]
        for mutate, code in mutations:
            value = fixture(); mutate(value)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, code):
                self.parse(value)
        value = fixture()
        row = next(r for r in value['source_files'] if r['path'] == value['gaps'][0]['evidence']['path'])
        row['status'] = 'parsed'
        value['coverage_summary']['statuses']['partial'] -= 1
        value['coverage_summary']['statuses']['parsed'] += 1
        with self.assertRaisesRegex(ValueError, 'hidden_coverage_gap'):
            self.parse(value)

    def test_malformed_collections_dangling_owners_and_structure_limits_reject(self):
        for key in ('source_files', 'objects', 'expressions', 'dependencies', 'gaps', 'limitations'):
            value = fixture(); value[key] = {}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'collection_required'):
                self.parse(value)
        for category, field, code in [('expressions', 'object_id', 'expression_owner_missing'),
                                      ('dependencies', 'source_id', 'dependency_owner_missing')]:
            value = fixture(); value[category][0][field] = 'missing-generated-object'
            with self.subTest(category=category), self.assertRaisesRegex(ValueError, code):
                self.parse(value)
        value = fixture(); value['objects'] = [None] * 5001
        with self.assertRaisesRegex(ValueError, 'collection_required'):
            self.parse(value)
        value = fixture(); nested = {}
        value['objects'][0]['details']['deep'] = nested
        for _ in range(40):
            nested['child'] = {}; nested = nested['child']
        with self.assertRaisesRegex(ValueError, 'structure_limit'):
            self.parse(value)
        for path in ('../escape.yaml', '/absolute.yaml', 'folder\\file.yaml'):
            value = fixture(); value['source_files'][0]['path'] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'source_path_invalid'):
                self.parse(value)

    def test_cli_output_is_private_new_only_and_console_is_counts_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, output = root / 'source.json', root / 'inventory.json'
            source.write_text(json.dumps(fixture()))
            args = [sys.executable, '-I', '-S', '-B', str(SCRIPT), str(source),
                    '--format', 'periscope-adapter', '--producer-revision', REVISION,
                    '--output', str(output)]
            first = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            console = json.loads(first.stdout)
            self.assertEqual(set(console), {'status', 'assets', 'gaps', 'native_validation'})
            self.assertEqual(console['assets'], 11)
            self.assertGreater(console['gaps'], 0)
            self.assertEqual(console['native_validation'], 'not_run')
            self.assertEqual(first.stderr, '')
            self.assertNotIn('INERT_SOURCE_SENTINEL', first.stdout)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            saved = output.read_bytes()
            self.assertEqual(json.loads(saved)['upstream_payload'], fixture())
            second = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(second.stdout, '')
            value = fixture(); value['credentials'] = 'SYNTHETIC_SECRET_MARKER'
            source.write_text(json.dumps(value))
            args[-1] = str(root / 'rejected.json')
            rejected = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(rejected.returncode, 1)
            self.assertFalse((root / 'rejected.json').exists())
            self.assertNotIn('SYNTHETIC_SECRET_MARKER', rejected.stdout + rejected.stderr)
            self.assertNotIn('INERT_SOURCE_SENTINEL', rejected.stdout + rejected.stderr)


if __name__ == '__main__':
    unittest.main()
