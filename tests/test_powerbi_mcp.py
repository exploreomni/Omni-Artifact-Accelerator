"""Fixed Power BI host contracts with synthetic credentials, never a tenant."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_tableau_mcp as prior
import test_powerbi_visual_bridge as fixtures

m = prior.m


class PowerBIHostTests(unittest.TestCase):
    setUp = prior.TableauHostTests.setUp
    write = prior.TableauHostTests.write
    runner = prior.TableauHostTests.runner

    def command(self, **kwargs):
        return m.PowerBICommand(self.root, sys.executable, 'inputs/request.json', 'inputs/capture', self.runner, **kwargs)

    def test_default_tools_are_local_only(self):
        names = {t['name'] for t in m.Bridge(self.root).definitions()}
        self.assertTrue({'powerbi_import_local', 'powerbi_import_fabric', 'powerbi_import_capture', 'powerbi_check_capture'} <= names)
        self.assertNotIn('powerbi_capture', names)
        self.assertNotIn('native_execute', names)

    def test_local_and_fabric_intake_keep_original_definition_without_credentials(self):
        self.write('inputs/local-request.json', fixtures.request())
        definition = self.root / 'inputs/definition'
        for path, raw in fixtures.definitions().items():
            target = definition / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        bridge = m.Bridge(self.root)
        with patch.dict(os.environ, {}, clear=True):
            imported = bridge.call('powerbi_import_local', {'request': 'inputs/local-request.json',
                'definition_root': 'inputs/definition', 'directory': 'inputs/local-import'})
        self.assertEqual(imported['status'], 'partial')
        source = imported['evidence']['path']
        self.assertEqual(bridge.call('powerbi_check_capture', {'source': source})['status'], 'consistent')
        projected = bridge.call('powerbi_import_capture', {'source': source, 'output': 'inputs/projected.json'})
        inventory = m.workflow.load(self.root, projected['path'])
        self.assertEqual(len(inventory['assets']), 19)
        self.write('inputs/fabric-response.json', {'definition': {'parts': [
            {'path': path, 'payload': base64.b64encode(raw).decode(), 'payloadType': 'InlineBase64'}
            for path, raw in fixtures.definitions().items()]}})
        fabric = bridge.call('powerbi_import_fabric', {'request': 'inputs/local-request.json',
            'response': 'inputs/fabric-response.json', 'directory': 'inputs/fabric-import'})
        self.assertEqual(fabric['status'], 'partial')
        with self.assertRaisesRegex(ValueError, 'local_directory_required'):
            bridge.call('powerbi_import_local', {'request': 'inputs/local-request.json',
                'definition_root': '../outside', 'directory': 'inputs/escaped'})
        record = m.workflow.load(self.root, source)['source']['definition_files'][0]
        (self.root / source).parent.joinpath(record['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            bridge.call('powerbi_check_capture', {'source': source})

    def test_source_session_uses_stdin_without_target_environment(self):
        command = self.command()
        with patch.dict(os.environ, {'FABRIC_ACCESS_TOKEN': 'synthetic-fabric', 'POWERBI_ACCESS_TOKEN': 'synthetic-powerbi',
                                    'OMNI_API_TOKEN': 'synthetic-target', 'TABLEAU_SESSION_TOKEN': 'synthetic-tableau'}):
            result = command.capture(True)
        argv, options = self.calls[0]
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(json.loads(options['input']), {'fabric_token': 'synthetic-fabric', 'powerbi_token': 'synthetic-powerbi'})
        self.assertIn('--tokens-stdin', argv)
        self.assertIn('--resume', argv)
        self.assertNotIn('--allow-source-query', argv)
        self.assertFalse(any('synthetic-' in str(arg) for arg in argv))
        self.assertFalse(any(key in options['env'] for key in ('OMNI_API_TOKEN', 'TABLEAU_SESSION_TOKEN', 'FABRIC_ACCESS_TOKEN', 'POWERBI_ACCESS_TOKEN')))
        self.assertFalse(options['shell'])
        self.assertEqual(options['timeout'], 60)

    def test_query_requires_separate_startup_grant(self):
        (self.root / 'inputs/request.json').write_text(json.dumps(fixtures.request()))
        with self.assertRaisesRegex(ValueError, 'query_not_authorized'):
            self.command()
        command = self.command(allow_query=True)
        with patch.dict(os.environ, {'POWERBI_ACCESS_TOKEN': 'synthetic-query'}):
            command.capture(False)
        self.assertIn('--allow-source-query', self.calls[0][0])

    def test_changed_request_rejects_before_source_process(self):
        command = self.command()
        (self.root / 'inputs/request.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed_file'):
            command.capture(False)
        self.assertFalse(self.calls)

    def test_changed_source_helper_rejects_before_credentials_or_process(self):
        command = self.command()
        helper = command.script.with_name('powerbi_capture_files.py')
        read_bytes = Path.read_bytes
        with patch.object(Path, 'read_bytes', lambda path: b'changed' if path == helper else read_bytes(path)):
            with self.assertRaisesRegex(ValueError, 'runtime_changed'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_token_variable_cannot_select_target_credential(self):
        for variable in ('OMNI_API_TOKEN', 'TABLEAU_SESSION_TOKEN'):
            with self.assertRaisesRegex(ValueError, 'powerbi_token_variable'):
                self.command(fabric_token_env=variable)
        command = self.command()
        with patch.dict(os.environ, {'FABRIC_ACCESS_TOKEN': 'a\nsecond'}):
            with self.assertRaisesRegex(ValueError, 'powerbi_token_invalid'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_unexpected_capture_output_directory_rejects(self):
        command = self.command()
        self.capture = self.write('evidence/unrelated.json', {'status': 'complete'})
        with patch.dict(os.environ, {'FABRIC_ACCESS_TOKEN': 'synthetic-session'}):
            with self.assertRaisesRegex(ValueError, 'capture_output_escaped'):
                command.capture(False)

    def test_finite_batch_reserves_across_restart_and_does_not_mix_sigma(self):
        # No explicit per-invocation budget: Power BI source default is exactly 20.
        (self.root / 'inputs/request.json').write_text(json.dumps({'capture_id': 'one'}))
        self.write('inputs/batch.json', {'kind': 'analyst_powerbi_capture_batch', 'schema_version': 1,
            'max_total_requests': 40, 'max_invocations': 2, 'captures': [
                {'capture_id': 'one', 'request': 'inputs/request.json', 'directory': 'inputs/capture'}]})
        batch = m.PowerBIBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        bridge = m.Bridge(self.root, powerbi=batch)
        definition = next(t for t in bridge.definitions() if t['name'] == 'powerbi_capture')
        self.assertEqual(definition['inputSchema']['properties']['capture_id']['enum'], ['one'])
        with self.assertRaisesRegex(ValueError, 'outside_batch'):
            batch.capture(False, 'unselected')
        with patch.object(batch.commands['one'], 'capture', side_effect=ValueError('interruption')):
            with self.assertRaises(ValueError):
                batch.capture(False, 'one')
        restarted = m.PowerBIBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        with patch.object(restarted.commands['one'], 'capture', return_value={'status': 'partial'}):
            restarted.capture(True, 'one')
            with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
                restarted.capture(True, 'one')
        record = json.loads(next((self.root / 'evidence').glob('powerbi-batch-*.json')).read_text())
        self.assertEqual(record, {'invocations': 2, 'reserved_requests': 40})
        self.assertFalse(list((self.root / 'evidence').glob('sigma-batch-*.json')))
        with self.assertRaisesRegex(ValueError, 'batch_contract'):
            m.SigmaBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)

    def test_tool_arguments_cannot_change_source_scope_or_session(self):
        bridge = m.Bridge(self.root, powerbi=self.command())
        for extra in ({'request': 'inputs/other.json'}, {'fabric_token': 'fake'}, {'allow_query': True}, {'url': 'https://unselected.invalid'}):
            with self.assertRaisesRegex(ValueError, 'arguments_rejected'):
                bridge.call('powerbi_capture', {'resume': False, **extra})
        self.assertFalse(self.calls)

    def test_timeout_is_returned_without_retry(self):
        command = self.command()
        with patch.object(command, 'runner', side_effect=subprocess.TimeoutExpired('fixed source', 60)) as runner:
            with patch.dict(os.environ, {'FABRIC_ACCESS_TOKEN': 'synthetic-session'}):
                with self.assertRaisesRegex(ValueError, 'capture_timeout_resume_from_journal'):
                    command.capture(False)
        self.assertEqual(runner.call_count, 1)
