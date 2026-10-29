"""BusinessObjects local MCP boundaries; no tenant or dependency execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
workflow = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
host = load('businessobjects_host', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
fixture = load('businessobjects_host_fixture', 'tests/test_businessobjects_visual.py')
capture_fixture = load('businessobjects_host_capture_fixture', 'tests/test_businessobjects_capture.py')


class BusinessObjectsHostTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic source workflow', 'migration', 'both')
        self.source = self.root / 'inputs/source.json'
        self.source.write_text(json.dumps(fixture.snapshot_fixture()))
        self.bridge = host.Bridge(self.root)

    def test_default_tools_only_local_and_projection_rechecks_original(self):
        definitions = {t['name']: t for t in self.bridge.definitions()}
        self.assertNotIn('businessobjects_capture', definitions)
        self.assertNotIn('businessobjects_refresh', definitions)
        for name in [n for n in definitions if n.startswith('businessobjects_')]:
            self.assertFalse(definitions[name]['annotations']['openWorldHint'])
        result = self.bridge.call('businessobjects_check_snapshot', {'source': 'inputs/source.json'})
        self.assertEqual(result['export_completeness'], 'not_established')
        self.bridge.call('businessobjects_translate', {'source': 'inputs/source.json', 'output': 'inputs/inventory.json'})
        inventory = workflow.source_inventory(self.root, 'inputs/source.json', 'inputs/inventory.json')
        self.assertEqual(inventory['source']['platform'], 'businessobjects')
        self.assertFalse(inventory['source_execution'])
        self.assertEqual(inventory['network_calls'], 0)

    def test_source_files_cannot_add_execution_authority(self):
        value = fixture.snapshot_fixture()
        value['enable_capture'] = True
        self.source.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.bridge.call('businessobjects_check_snapshot', {'source': 'inputs/source.json'})
        with self.assertRaisesRegex(ValueError, 'unknown_or_disabled_tool'):
            self.bridge.call('businessobjects_capture', {'resume': True})
        with self.assertRaisesRegex(ValueError, 'external_authority_required'):
            host.BusinessObjectsCommand(self.root, 'inputs/source.json', 'inputs/capture', authority=None)

    def test_engagement_paths_symlinks_and_overwrite_rejected(self):
        for source in ('../outside.json', str(self.source), 'inputs/../source.json'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.bridge.call('businessobjects_check_snapshot', {'source': source})
        (self.root / 'inputs/link.json').symlink_to(self.source)
        with self.assertRaises(ValueError):
            self.bridge.call('businessobjects_check_snapshot', {'source': 'inputs/link.json'})
        args = {'source': 'inputs/source.json', 'output': 'inputs/inventory.json'}
        self.bridge.call('businessobjects_translate', args)
        before = (self.root / args['output']).read_bytes()
        with self.assertRaises((ValueError, FileExistsError)):
            self.bridge.call('businessobjects_translate', args)
        self.assertEqual(before, (self.root / args['output']).read_bytes())
        with self.assertRaises(ValueError):
            self.bridge.call('businessobjects_translate', {**args, 'output': '../outside.json'})

    def test_native_authoring_not_exposed_by_source_specialist(self):
        names = {t['name'] for t in self.bridge.definitions()}
        self.assertFalse({'native_execute', 'app_execute', 'businessobjects_save'} & names)
        value = copy.deepcopy(fixture.snapshot_fixture())
        value['responses'][0]['content'] += ' '
        self.source.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.bridge.call('businessobjects_translate', {'source': 'inputs/source.json', 'output': 'inputs/bad.json'})
        self.assertFalse((self.root / 'inputs/bad.json').exists())

    def test_capture_import_and_numeric_normalization_are_passive_and_exact(self):
        source = self.root / 'inputs/originals'
        req, _ = capture_fixture.prepare(source)
        (self.root / 'inputs/request.json').write_text(json.dumps(req))
        result = self.bridge.call('businessobjects_import_local', {'request': 'inputs/request.json',
            'source_root': 'inputs/originals/supplied', 'directory': 'inputs/copied-capture'})
        capture_path = result['evidence']['path']
        checked = self.bridge.call('businessobjects_check_capture', {'source': capture_path})
        self.assertEqual(checked['native_validation'], 'not_run')
        self.bridge.call('businessobjects_import_capture', {'source': capture_path, 'output': 'inputs/capture-inventory.json'})
        workflow.source_inventory(self.root, capture_path, 'inputs/capture-inventory.json')
        f = capture_fixture.capture_fixture(self.root / 'inputs/numeric')
        for name in ('profile', 'binding'):
            (self.root / ('inputs/' + name + '.json')).write_text(json.dumps(f[name]))
        self.bridge.call('businessobjects_normalize_results', {
            'source': str(f['raw_path'].relative_to(self.root)), 'profile': 'inputs/profile.json',
            'binding': 'inputs/binding.json', 'output': 'inputs/normalized.json'})
        normalized = workflow.load(self.root, 'inputs/normalized.json')
        self.assertEqual(normalized, f['normalized'])
        self.assertEqual(normalized['rows'][1]['yield'], '9007199254740993')

    def test_injected_metadata_host_pins_runtime_scope_and_blocks_request_drift(self):
        base = self.root / 'inputs/connected'
        req, _ = capture_fixture.prepare(base, connected=True)
        req_path = self.root / 'inputs/connected-request.json'
        req_path.write_text(json.dumps(req))
        seen = []
        def authority(scope, fingerprint):
            self.assertEqual(scope, 'metadata')
            self.assertEqual(fingerprint['method'], 'GET')
            self.assertTrue(fingerprint['url'].startswith(req['identity']['source_origin'] + '/proxy/biprws/'))
            self.assertIn('businessobjects_capture.py', fingerprint['runtime_sha256'])
            seen.append(fingerprint)
            return {'X-SAP-LogonToken': 'fixture-host-token'}
        def transport(method, url, headers, body, maximum, timeout):
            self.assertIsNone(body)
            return 200, {}, b'{"document":{"id":17}}'
        command = host.BusinessObjectsCommand(self.root, 'inputs/connected-request.json',
            'inputs/connected/capture', authority=authority, transport=transport)
        bridge = host.Bridge(self.root, businessobjects=command)
        names = {t['name']: t for t in bridge.definitions()}
        self.assertTrue(names['businessobjects_capture']['annotations']['openWorldHint'])
        out = bridge.call('businessobjects_capture', {'resume': True})
        self.assertEqual(out['status'], 'ready')
        self.assertEqual(len(seen), 2)
        bridge.call('businessobjects_capture', {'resume': True})
        self.assertEqual(len(seen), 2)
        req_path.write_text(req_path.read_text() + ' ')
        with self.assertRaises(ValueError):
            bridge.call('businessobjects_capture', {'resume': True})


if __name__ == '__main__':
    unittest.main()
