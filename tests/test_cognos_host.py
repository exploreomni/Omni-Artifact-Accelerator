"""Offline Cognos import and MCP boundaries with original synthetic XML."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


ap = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
v = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
h = load('cognos_host', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
f = load('cognos_host_fixture', 'tests/test_cognos_visual.py')
c = load('cognos_import_cli', 'skills/omni-artifact-translator/scripts/cognos_import.py')


class CognosHostTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        ap.init(self.root, 'Synthetic report migration', 'migration', 'both')
        self.snapshot = f.snapshot_fixture()
        (self.root / 'inputs/report.xml').write_text(self.snapshot['report_xml']['content'], encoding='utf-8')
        meta = {k: self.snapshot[k] for k in ('identity', 'inventory')}
        meta['reference'] = self.snapshot['report_xml']['reference']
        (self.root / 'inputs/metadata.json').write_text(json.dumps(meta))
        self.host = h.Bridge(self.root)

    def args(self, output='inputs/snapshot.json'):
        return {'source': 'inputs/report.xml', 'metadata': 'inputs/metadata.json', 'output': output}

    def test_import_translate_and_read_only_check_are_local(self):
        tools = {t['name']: t for t in self.host.definitions()}
        self.assertFalse({'cognos_capture', 'cognos_execute', 'native_execute', 'app_execute'} & tools.keys())
        for name in ('cognos_import_report', 'cognos_translate', 'cognos_check_snapshot'):
            self.assertFalse(tools[name]['annotations']['openWorldHint'])
        self.host.call('cognos_import_report', self.args())
        check = self.host.call('cognos_check_snapshot', {'source': 'inputs/snapshot.json'})
        self.assertEqual(check['native_validation'], 'not_run')
        self.assertEqual(check['export_completeness'], 'not_established')
        self.host.call('cognos_translate', {'source': 'inputs/snapshot.json', 'output': 'inputs/inventory.json'})
        inventory = v.source_inventory(self.root, 'inputs/snapshot.json', 'inputs/inventory.json')
        self.assertEqual(inventory['source']['platform'], 'cognos')
        self.assertFalse(inventory['source_execution'])
        self.assertEqual(inventory['network_calls'], 0)

    def test_outside_paths_links_and_overwrite_are_rejected(self):
        for key, value in (('source', '../outside.xml'), ('metadata', str(self.root / 'inputs/metadata.json')),
                           ('output', '../escape.json'), ('output', 'inputs/../escape.json')):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.host.call('cognos_import_report', {**self.args(), key: value})
        (self.root / 'inputs/link.xml').symlink_to(self.root / 'inputs/report.xml')
        with self.assertRaises(ValueError):
            self.host.call('cognos_import_report', {**self.args(), 'source': 'inputs/link.xml'})
        self.host.call('cognos_import_report', self.args())
        original = (self.root / 'inputs/snapshot.json').read_bytes()
        with self.assertRaises((ValueError, FileExistsError)):
            self.host.call('cognos_import_report', self.args())
        self.assertEqual((self.root / 'inputs/snapshot.json').read_bytes(), original)
        with self.assertRaises(ValueError):
            self.host.call('cognos_capture', {})

    def test_import_cli_does_not_echo_rejected_source(self):
        marker = 'synthetic-sensitive-marker'
        (self.root / 'inputs/report.xml').write_text('<!DOCTYPE report [<!ENTITY x "' + marker + '">]><report>&x;</report>')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = c.main([str(self.root / 'inputs/report.xml'), '--metadata',
                str(self.root / 'inputs/metadata.json'), '--output', str(self.root / 'inputs/rejected.json')])
        self.assertEqual(status, 1)
        self.assertNotIn(marker, stdout.getvalue() + stderr.getvalue())
        self.assertFalse((self.root / 'inputs/rejected.json').exists())

    def test_metadata_cannot_introduce_connection_or_execution_authority(self):
        path = self.root / 'inputs/metadata.json'
        meta = json.loads(path.read_text())
        meta['execute'] = True
        path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'import_metadata_fields'):
            self.host.call('cognos_import_report', self.args())

    def test_importer_refuses_symlinked_sibling_module(self):
        isolated = self.root / 'isolated'
        isolated.mkdir()
        source = ROOT / 'skills/omni-artifact-translator/scripts'
        (isolated / 'cognos_import.py').write_bytes((source / 'cognos_import.py').read_bytes())
        (isolated / 'translate_artifact.py').symlink_to(source / 'translate_artifact.py')
        importer = load('isolated_cognos_import', isolated / 'cognos_import.py')
        with self.assertRaisesRegex(ValueError, 'module_symlink'):
            importer.module('translate_artifact')


if __name__ == '__main__':
    unittest.main()
