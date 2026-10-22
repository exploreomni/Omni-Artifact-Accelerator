"""Tableau host boundaries using a fixed fake source process; never a tenant."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/omni-artifact-accelerator/scripts'))
import visual_mcp as m  # noqa: E402


class TableauHostTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'run'
        m.workflow.ap.init(self.root, 'Tableau host boundary', 'migration', 'dashboard')
        self.write('inputs/request.json', {'capture_id': 'one', 'max_requests_per_invocation': 20})
        self.folder = self.root / 'inputs/capture'
        self.folder.mkdir()
        self.capture = self.write('inputs/capture/capture-000001.json', {'status': 'partial'})
        self.calls = []

    def write(self, path, value):
        destination = self.root / path
        m.workflow.ap.write_json(destination, value)
        return destination

    def runner(self, argv, **options):
        self.calls.append((argv, options))
        return SimpleNamespace(returncode=0, stdout=json.dumps({'status': 'partial', 'output': str(self.capture)}).encode())

    def command(self, **kwargs):
        return m.TableauCommand(self.root, sys.executable, 'inputs/request.json', 'inputs/capture', self.runner, **kwargs)

    def test_default_tools_are_local_only(self):
        names = {t['name'] for t in m.Bridge(self.root).definitions()}
        self.assertTrue({'tableau_import_capture', 'tableau_check_capture'} <= names)
        self.assertNotIn('tableau_capture', names)
        self.assertNotIn('native_execute', names)

    def test_retained_official_mcp_intake_never_needs_source_credentials(self):
        import test_tableau_capture as fixtures
        self.write('inputs/mcp-request.json', fixtures.request())
        self.write('inputs/mcp-response.json', {'schema_version': 'tableau-mcp-intake.v1', 'records': [{
            'record_id': 'legacy-result', 'tool': 'get-view-data',
            'arguments': {'viewId': 'sheet-1', 'viewFilters': fixtures.request()['state']['filters']},
            'response': fixtures.text_response('Site,Units\nEast,21\n')}]})
        bridge = m.Bridge(self.root)
        result = bridge.call('tableau_import_mcp', {'request': 'inputs/mcp-request.json',
            'response': 'inputs/mcp-response.json', 'directory': 'inputs/imported'})
        self.assertEqual(result['status'], 'partial')
        self.assertTrue((self.root / result['evidence']['path']).is_file())
        with self.assertRaises(ValueError):
            bridge.call('tableau_import_mcp', {'request': 'inputs/mcp-request.json',
                'response': 'inputs/mcp-response.json', 'directory': '../outside'})

    def test_capture_import_verifies_real_attachments_and_reprojects(self):
        import test_tableau_visual_bridge as fixtures
        result = fixtures.capture_fixture(self.root / 'inputs/complete')
        source = str(Path(result['output']).relative_to(self.root))
        bridge = m.Bridge(self.root)
        self.assertEqual(bridge.call('tableau_check_capture', {'source': source})['status'], 'consistent')
        projected = bridge.call('tableau_import_capture', {'source': source, 'output': 'inputs/real-inventory.json'})
        inventory = m.workflow.load(self.root, projected['path'])
        self.assertEqual(inventory, result['inventory'])
        attachment = result['capture']['attachments'][0]['path']
        (Path(result['output']).parent / attachment).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            bridge.call('tableau_check_capture', {'source': source})

    def test_source_session_uses_stdin_without_target_environment(self):
        command = self.command()
        with patch.dict(os.environ, {'TABLEAU_SESSION_TOKEN': 'synthetic-tableau-session', 'OMNI_API_TOKEN': 'synthetic-target-secret'}):
            result = command.capture(True)
        argv, options = self.calls[0]
        self.assertEqual(result['status'], 'partial')
        self.assertNotIn('synthetic-tableau-session', ' '.join(argv))
        self.assertIn('--session-token-stdin', argv)
        self.assertIn('--resume', argv)
        self.assertEqual(options['input'], b'synthetic-tableau-session\n')
        self.assertNotIn('OMNI_API_TOKEN', options['env'])
        self.assertNotIn('TABLEAU_SESSION_TOKEN', options['env'])
        self.assertFalse(options['shell'])
        self.assertEqual(options['timeout'], 60)

    def test_changed_request_rejects_before_source_process(self):
        command = self.command()
        (self.root / 'inputs/request.json').write_text('{}')
        with patch.dict(os.environ, {'TABLEAU_SESSION_TOKEN': 'synthetic-session'}):
            with self.assertRaisesRegex(ValueError, 'changed_file'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_changed_source_helper_rejects_before_credentials_or_process(self):
        command = self.command()
        helper = command.script.with_name('tableau_capture_files.py')
        read_bytes = Path.read_bytes
        def changed(path):
            return b'changed validation runtime' if path == helper else read_bytes(path)
        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'runtime_changed'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_token_variable_cannot_select_target_credential(self):
        with self.assertRaisesRegex(ValueError, 'tableau_token_variable'):
            self.command(token_env='OMNI_API_TOKEN')
        command = self.command()
        with patch.dict(os.environ, {'TABLEAU_SESSION_TOKEN': 'a\nsecond'}):
            with self.assertRaisesRegex(ValueError, 'tableau_session_required'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_unexpected_capture_output_directory_rejects(self):
        command = self.command()
        self.capture = self.write('evidence/unrelated.json', {'status': 'complete'})
        with patch.dict(os.environ, {'TABLEAU_SESSION_TOKEN': 'synthetic-session'}):
            with self.assertRaisesRegex(ValueError, 'capture_output_escaped'):
                command.capture(False)

    def test_finite_batch_reserves_across_restart_and_does_not_mix_sigma(self):
        self.write('inputs/two.json', {'capture_id': 'two', 'max_requests_per_invocation': 20})
        self.write('inputs/batch.json', {'kind': 'analyst_tableau_capture_batch', 'schema_version': 1,
            'max_total_requests': 40, 'max_invocations': 2, 'captures': [
                {'capture_id': 'one', 'request': 'inputs/request.json', 'directory': 'inputs/capture'},
                {'capture_id': 'two', 'request': 'inputs/two.json', 'directory': 'inputs/two-capture'}]})
        batch = m.TableauBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        bridge = m.Bridge(self.root, tableau=batch)
        definition = next(t for t in bridge.definitions() if t['name'] == 'tableau_capture')
        self.assertEqual(definition['inputSchema']['properties']['capture_id']['enum'], ['one', 'two'])
        with self.assertRaisesRegex(ValueError, 'outside_batch'):
            bridge.call('tableau_capture', {'resume': False, 'capture_id': 'unselected'})
        with patch.object(batch.commands['one'], 'capture', side_effect=ValueError('interruption')):
            with self.assertRaises(ValueError):
                batch.capture(False, 'one')
        restarted = m.TableauBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        with patch.object(restarted.commands['two'], 'capture', return_value={'status': 'partial'}):
            restarted.capture(False, 'two')
            with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
                restarted.capture(True, 'two')
        self.assertEqual(len(list((self.root / 'evidence').glob('tableau-batch-*.json'))), 1)
        self.assertFalse(list((self.root / 'evidence').glob('sigma-batch-*.json')))
        with self.assertRaisesRegex(ValueError, 'batch_contract'):
            m.SigmaBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)

    def test_tool_arguments_cannot_change_source_scope_or_session(self):
        bridge = m.Bridge(self.root, tableau=self.command())
        for extra in ({'request': 'inputs/other.json'}, {'session_token': 'fake'}, {'url': 'https://unselected.invalid'}):
            with self.assertRaisesRegex(ValueError, 'arguments_rejected'):
                bridge.call('tableau_capture', {'resume': False, **extra})
        self.assertFalse(self.calls)


if __name__ == '__main__':
    unittest.main()
