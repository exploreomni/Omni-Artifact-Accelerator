"""Hex host authority, credential isolation and separate initial App writes."""
import os
import json
import sys
import unittest
from unittest.mock import Mock, patch

import test_tableau_mcp as prior

m = prior.m


class HexHostTests(unittest.TestCase):
    setUp = prior.TableauHostTests.setUp
    write = prior.TableauHostTests.write
    runner = prior.TableauHostTests.runner

    def command(self, **kwargs):
        return m.HexCommand(self.root, sys.executable, 'inputs/request.json', 'inputs/capture', self.runner, **kwargs)

    def test_default_tools_do_not_enable_tenant_capture_or_mutation(self):
        names = {t['name'] for t in m.Bridge(self.root).definitions()}
        self.assertTrue({'hex_import_local', 'hex_import_evidence', 'hex_import_capture',
                         'hex_check_capture', 'hex_translate'} <= names)
        self.assertFalse({'hex_capture', 'app_execute_initial', 'app_execute', 'native_execute'} & names)

    def test_actual_offline_import_keeps_bytes_and_host_cannot_hide_tampering(self):
        import test_hex_capture as source
        incoming = self.root / 'inputs/supplied'
        incoming.mkdir()
        (incoming / 'inventory.hex.yaml').write_text(json.dumps(source.native()))
        self.write('inputs/hex-request.json', source.request())
        bridge = m.Bridge(self.root)
        result = bridge.call('hex_import_local', {'request': 'inputs/hex-request.json',
            'source_root': 'inputs/supplied', 'directory': 'inputs/hex-local'})
        captured = result['evidence']['path']
        bridge.call('hex_check_capture', {'source': captured})
        bridge.call('hex_import_capture', {'source': captured, 'output': 'inputs/hex-inventory.json'})
        inventory = json.loads((self.root / 'inputs/hex-inventory.json').read_text())
        self.assertEqual(inventory['source']['platform'], 'hex')
        self.assertGreater(len(inventory['assets']), 28)
        envelope = json.loads((self.root / captured).read_text())
        attachment = (self.root / captured).parent / envelope['source']['definition_files'][0]['path']
        attachment.write_bytes(attachment.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            bridge.call('hex_check_capture', {'source': captured})
        with self.assertRaises(ValueError):
            bridge.call('hex_import_capture', {'source': captured, 'output': 'inputs/invalid.json'})
        self.assertFalse((self.root / 'inputs/invalid.json').exists())

    def test_capture_uses_only_startup_pins_and_isolated_stdin_token(self):
        command = self.command()
        bridge = m.Bridge(self.root, hex_source=command)
        with patch.dict(os.environ, {'HEX_ACCESS_TOKEN': 'synthetic-source', 'OMNI_API_TOKEN': 'synthetic-target'}):
            result = bridge.call('hex_capture', {'resume': True})
        self.assertEqual(result['status'], 'partial')
        argv, options = self.calls[0]
        self.assertIn('--resume', argv)
        self.assertNotIn('--allow-source-query', argv)
        self.assertNotIn('synthetic-source', ' '.join(argv))
        self.assertEqual(options['input'], b'synthetic-source')
        self.assertFalse({'HEX_ACCESS_TOKEN', 'OMNI_API_TOKEN'} & set(options['env']))
        self.assertFalse(options['shell'])
        with self.assertRaises(ValueError):
            bridge.call('hex_capture', {'resume': False, 'project_id': 'another-project'})

    def test_source_execution_and_target_token_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hex_token_variable'):
            self.command(token_env='OMNI_API_TOKEN')
        self.write('inputs/run.json', {'runs': ['unreviewed']})
        with self.assertRaisesRegex(ValueError, 'execution_not_supported'):
            m.HexCommand(self.root, sys.executable, 'inputs/run.json', 'inputs/capture', self.runner)
        command = self.command()
        with patch.dict(os.environ, {'HEX_ACCESS_TOKEN': 'first\nsecond'}):
            with self.assertRaisesRegex(ValueError, 'hex_token_required'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_changed_source_request_cannot_resume(self):
        command = self.command()
        (self.root / 'inputs/request.json').write_text('{"capture_id":"changed"}')
        with patch.dict(os.environ, {'HEX_ACCESS_TOKEN': 'synthetic-source'}):
            with self.assertRaisesRegex(ValueError, 'changed_file'):
                command.capture(True)
        self.assertFalse(self.calls)

    def test_initial_app_grant_is_distinct_from_edit_authority(self):
        app = Mock()
        app.execute_initial.return_value = {'status': 'readback_matched', 'native_verified': False}
        edit_only = m.Bridge(self.root, app=app, allowed_app_candidate='a' * 64,
                             app_authorization_reference='reviewed-edit')
        self.assertNotIn('app_execute_initial', {t['name'] for t in edit_only.definitions()})
        with self.assertRaisesRegex(ValueError, 'unknown_or_disabled'):
            edit_only.call('app_execute_initial', {'candidate_sha256': 'a' * 64})
        create = m.Bridge(self.root, app=app, allowed_app_initial_candidate='b' * 64,
                          app_initial_authorization_reference='reviewed-initial')
        self.assertNotIn('app_execute', {t['name'] for t in create.definitions()})
        with self.assertRaisesRegex(ValueError, 'candidate_not_authorized'):
            create.call('app_execute_initial', {'candidate_sha256': 'a' * 64})
        result = create.call('app_execute_initial', {'candidate_sha256': 'b' * 64})
        self.assertEqual(result['status'], 'readback_matched')
        app.execute_initial.assert_called_once_with('b' * 64, 'reviewed-initial')

    def test_initial_app_reconciliation_cannot_execute(self):
        app = Mock()
        bridge = m.Bridge(self.root, app=app)
        bridge.call('app_reconcile_initial', {'candidate_sha256': 'b' * 64})
        app.reconcile_initial.assert_called_once_with('b' * 64)
        app.execute_initial.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'initial_startup_authority'):
            m.Bridge(self.root, app=app, allowed_app_initial_candidate='b' * 64)


if __name__ == '__main__':
    unittest.main()
