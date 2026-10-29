"""Local Report host contracts. Original fixtures; no native or source requests."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module


P = load('analyst_project', 'skills/omni-artifact-accelerator/scripts/analyst_project.py')
W = load('visual_workflow', 'skills/omni-artifact-accelerator/scripts/visual_workflow.py')
H = load('report_host_under_test', 'skills/omni-artifact-accelerator/scripts/visual_mcp.py')
R = load('report_host_rdl', 'tests/test_rdl_report.py')
C = load('report_host_crystal', 'tests/test_crystal_report.py')
F = load('report_host_capture', 'tests/test_report_source_capture.py')


class ReportHostTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / 'engagement'
        P.init(self.root, 'Synthetic report migration', 'migration', 'report', 'none')
        self.host = H.Bridge(self.root)

    def put(self, path, value):
        (self.root / path).write_text(json.dumps(value)); return path

    def test_tools_are_local_and_cannot_enable_native_execution(self):
        tools = {t['name']: t for t in self.host.definitions()}
        for name, tool in tools.items():
            if name.startswith(('report_', 'rdl_', 'crystal_')):
                self.assertFalse(tool['annotations']['openWorldHint'])
        self.assertFalse({'report_execute', 'report_publish', 'report_source_capture'} & set(tools))
        with self.assertRaisesRegex(ValueError, 'unknown_or_disabled_tool'):
            self.host.call('report_execute', {})
        with self.assertRaises(ValueError):
            H.report_host_module('untrusted')

    def test_three_source_routes_reproject_originals(self):
        for platform in ('ssrs', 'powerbi_paginated', 'crystal'):
            with self.subTest(platform=platform):
                snapshot = C.snapshot_fixture() if platform == 'crystal' else R.snapshot_fixture(platform)
                source = self.put('inputs/' + platform + '.json', snapshot)
                prefix = 'crystal' if platform == 'crystal' else 'rdl'
                result = self.host.call(prefix + '_check_snapshot', {'source': source})
                self.assertEqual(result['export_completeness'], 'not_established')
                output = 'inputs/' + platform + '-inventory.json'
                self.host.call(prefix + '_translate', {'source': source, 'output': output})
                inventory = H.workflow.source_inventory(self.root, source, output)
                self.assertEqual(inventory['source']['platform'], platform)
                self.assertFalse(inventory['source_execution'])

    def test_snapshot_builders_retain_bytes_and_reject_extra_authority(self):
        for prefix, snapshot, field in [('rdl', R.snapshot_fixture(), 'report_xml'), ('crystal', C.snapshot_fixture(), 'extraction')]:
            source = 'inputs/' + prefix + '-original.txt'
            (self.root / source).write_text(snapshot[field]['content'])
            metadata = {k: snapshot[k] for k in ('identity', 'inventory')}
            metadata['reference'] = snapshot[field]['reference']
            if prefix == 'rdl': metadata['gaps'] = snapshot['gaps']
            else: metadata.update(method=snapshot[field]['method'], extractor_version=snapshot[field]['extractor_version'])
            path = self.put('inputs/' + prefix + '-metadata.json', metadata)
            output = 'inputs/' + prefix + '-snapshot.json'
            self.host.call(prefix + '_prepare_snapshot', {'source': source, 'metadata': path, 'output': output})
            saved = H.workflow.load(self.root, output)
            self.assertEqual(saved[field]['content'], snapshot[field]['content'])
            metadata['approved'] = True; self.put(path, metadata)
            with self.assertRaises(ValueError):
                self.host.call(prefix + '_prepare_snapshot', {'source': source, 'metadata': path, 'output': output + '.other'})

    def test_capture_import_rechecks_original_and_attachment_files(self):
        base = self.root / 'inputs/source'; base.mkdir()
        request, source, _ = F.prepare(base)
        path = self.put('inputs/request.json', request)
        result = self.host.call('report_source_import_local', {'request': path,
            'source_root': 'inputs/source/supplied', 'directory': 'inputs/capture'})
        selected = result['evidence']['path']
        self.host.call('report_source_check_capture', {'source': selected})
        self.host.call('report_source_translate_capture', {'source': selected, 'output': 'inputs/capture-inventory.json'})
        H.workflow.source_inventory(self.root, selected, 'inputs/capture-inventory.json')
        (self.root / 'inputs/capture/definition-original.bin').write_text('tampered')
        with self.assertRaises(ValueError): self.host.call('report_source_check_capture', {'source': selected})

    def test_paths_overwrite_and_early_build_are_closed(self):
        source = self.put('inputs/source.json', R.snapshot_fixture())
        for path in ('../source.json', str(self.root / source), 'inputs/../source.json'):
            with self.assertRaises(ValueError): self.host.call('rdl_check_snapshot', {'source': path})
        (self.root / 'inputs/link.json').symlink_to(self.root / source)
        with self.assertRaises(ValueError): self.host.call('rdl_check_snapshot', {'source': 'inputs/link.json'})
        args = {'source': source, 'output': 'inputs/inventory.json'}
        self.host.call('rdl_translate', args)
        before = (self.root / args['output']).read_bytes()
        with self.assertRaises((ValueError, FileExistsError)): self.host.call('rdl_translate', args)
        self.assertEqual(before, (self.root / args['output']).read_bytes())
        self.put('inputs/early.json', {'definition_path': 'deliverables/report.json', 'definition_format': 'rdlx-json',
            'requirements_path': None, 'builders': ['fixture-builder']})
        with self.assertRaises(ValueError):
            self.host.call('report_prepare', {'spec': 'inputs/early.json', 'output': 'deliverables/early.json'})
        self.assertFalse((self.root / 'deliverables/early.json').exists())


if __name__ == '__main__': unittest.main()
