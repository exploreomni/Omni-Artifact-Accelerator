"""Looker source authority and separate App/dashboard target grants; no live tenant."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_tableau_mcp as prior

m = prior.m


class LookerHostTests(unittest.TestCase):
    setUp = prior.TableauHostTests.setUp
    write = prior.TableauHostTests.write
    runner = prior.TableauHostTests.runner

    def command(self, **kwargs):
        return m.LookerCommand(self.root, sys.executable, 'inputs/request.json', 'inputs/capture', self.runner, **kwargs)

    def test_default_tools_have_no_live_capture_or_app_mutation(self):
        names = {t['name'] for t in m.Bridge(self.root).definitions()}
        self.assertTrue({'looker_import_local', 'looker_import_api', 'looker_import_capture',
                         'looker_check_capture', 'looker_translate'} <= names)
        self.assertFalse({'looker_capture', 'app_execute', 'native_execute'} & names)

    def test_source_token_isolated_and_query_requires_startup_grant(self):
        self.write('inputs/queries.json', {'capture_id': 'one', 'queries': [{'id': 'reviewed'}]})
        with self.assertRaisesRegex(ValueError, 'query_not_authorized'):
            m.LookerCommand(self.root, sys.executable, 'inputs/queries.json', 'inputs/capture', self.runner)
        command = m.LookerCommand(self.root, sys.executable, 'inputs/queries.json', 'inputs/capture', self.runner,
                                  allow_query=True)
        with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': 'synthetic-source', 'OMNI_API_TOKEN': 'synthetic-target',
                                    'FABRIC_ACCESS_TOKEN': 'synthetic-other'}):
            command.capture(True)
        argv, options = self.calls[0]
        self.assertIn('--allow-source-query', argv)
        self.assertIn('--resume', argv)
        self.assertNotIn('synthetic-source', ' '.join(argv))
        self.assertEqual(options['input'], b'synthetic-source')
        self.assertFalse({'LOOKER_ACCESS_TOKEN', 'OMNI_API_TOKEN', 'FABRIC_ACCESS_TOKEN'} & set(options['env']))
        self.assertFalse(options['shell'])
        self.calls.clear()
        with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': 'synthetic-source'}):
            self.command().capture(False)
        self.assertNotIn('--allow-source-query', self.calls[0][0])

    def test_tokens_cannot_select_target_or_contain_multiple_lines(self):
        with self.assertRaisesRegex(ValueError, 'looker_token_variable'):
            self.command(token_env='OMNI_API_TOKEN')
        command = self.command()
        with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': 'first\nsecond'}):
            with self.assertRaisesRegex(ValueError, 'looker_token_required'):
                command.capture(False)
        self.assertFalse(self.calls)

    def test_render_also_requires_query_grant_and_capture_cannot_bypass_file_checks(self):
        self.write('inputs/renders.json', {'capture_id': 'one', 'renders': [{'id': 'reviewed'}]})
        with self.assertRaisesRegex(ValueError, 'query_not_authorized'):
            m.LookerCommand(self.root, sys.executable, 'inputs/renders.json', 'inputs/capture', self.runner)
        with self.assertRaisesRegex(ValueError, 'looker_format_required'):
            m.Bridge(self.root).call('looker_translate', {'source': 'inputs/request.json',
                'format': 'looker-capture', 'output': 'evidence/inventory.json'})

    def test_actual_source_cli_consumes_exact_stdin_token_and_writes_verified_capture(self):
        import test_looker_visual_bridge as source
        self.write('inputs/actual-request.json', source.request())
        code = '''import functools,socket,sys
sys.path.insert(0,sys.argv[1])
import test_looker_capture as p
def denied(*a,**k): raise AssertionError('network forbidden')
socket.socket.connect=denied
p.C.capture=functools.partial(p.C.capture,transport=p.Transport(),now=p.NOW)
raise SystemExit(p.C.main(sys.argv[2:]))
'''
        def runner(args, **options):
            return subprocess.run([args[0], '-c', code, str(Path(__file__).resolve().parent), *args[2:]], **options)
        command = m.LookerCommand(self.root, sys.executable, 'inputs/actual-request.json',
                                  'inputs/actual-capture', runner, allow_query=True)
        with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': source.p.TOKEN}):
            result = command.capture(False)
        self.assertEqual(result['status'], 'complete')
        checked = m.Bridge(self.root).call('looker_check_capture', {'source': result['evidence']['path']})
        self.assertEqual(checked['status'], 'consistent')
        m.Bridge(self.root).call('looker_import_capture', {'source': result['evidence']['path'],
            'output': 'inputs/actual-inventory.json'})
        inventory = json.loads((self.root / 'inputs/actual-inventory.json').read_text())
        self.assertEqual({(a['source_path'], a['kind']) for a in inventory['assets']}, set(source.EXPECTED))

    def test_changed_request_and_runtime_reject_before_process(self):
        command = self.command()
        original = Path.read_bytes
        helper = command.script.with_name('powerbi_capture_files.py')
        with patch.object(Path, 'read_bytes', lambda path: b'changed' if path == helper else original(path)):
            with self.assertRaisesRegex(ValueError, 'runtime_changed'):
                command.capture(False)
        (self.root / 'inputs/request.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'changed_file'):
            command.capture(False)
        self.assertFalse(self.calls)

    def test_batch_reserves_budget_before_interrupted_execution(self):
        (self.root / 'inputs/request.json').write_text(json.dumps({'capture_id': 'one'}))
        self.write('inputs/batch.json', {'kind': 'analyst_looker_capture_batch', 'schema_version': 1,
            'max_total_requests': 80, 'max_invocations': 2, 'captures': [
                {'capture_id': 'one', 'request': 'inputs/request.json', 'directory': 'inputs/capture'}]})
        batch = m.LookerBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        with self.assertRaisesRegex(ValueError, 'outside_batch'):
            batch.capture(False, 'other')
        with patch.object(batch.commands['one'], 'capture', side_effect=ValueError('interrupted')):
            with self.assertRaises(ValueError):
                batch.capture(False, 'one')
        restarted = m.LookerBatch(self.root, sys.executable, 'inputs/batch.json', self.runner)
        with patch.object(restarted.commands['one'], 'capture', return_value={'status': 'partial'}):
            restarted.capture(True, 'one')
            with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
                restarted.capture(True, 'one')
        journal = next((self.root / 'evidence').glob('looker-batch-*.json'))
        self.assertEqual(json.loads(journal.read_text()), {'invocations': 2, 'reserved_requests': 80})
        self.assertFalse(list((self.root / 'evidence').glob('sigma-batch-*.json')))

    def test_tool_arguments_cannot_expand_source_scope(self):
        bridge = m.Bridge(self.root, looker=self.command())
        for extra in ({'request': 'other.json'}, {'token': 'secret'}, {'allow_query': True}, {'url': 'https://other.invalid'}):
            with self.assertRaisesRegex(ValueError, 'arguments_rejected'):
                bridge.call('looker_capture', {'resume': False, **extra})
        self.assertFalse(self.calls)

    def test_unknown_process_outcome_has_no_automatic_retry(self):
        command = self.command()
        with patch.object(command, 'runner', side_effect=subprocess.TimeoutExpired('source', 60)) as runner:
            with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': 'synthetic-source'}):
                with self.assertRaisesRegex(ValueError, 'timeout_resume'):
                    command.capture(False)
        self.assertEqual(runner.call_count, 1)

    def test_process_cannot_redirect_capture_output(self):
        command = self.command()
        self.capture = self.write('evidence/unrelated.json', {'status': 'partial'})
        with patch.dict(os.environ, {'LOOKER_ACCESS_TOKEN': 'synthetic-source'}):
            with self.assertRaisesRegex(ValueError, 'output_escaped'):
                command.capture(False)

    def target(self, document):
        adapter = Mock()
        adapter.target = SimpleNamespace(document_id=document, base_url='https://synthetic.omniapp.co')
        adapter.execute.return_value = {'status': 'readback_matched', 'native_validation': 'not_run'}
        return adapter

    def test_dashboard_grant_does_not_authorize_app_and_surfaces_cannot_share_document(self):
        dashboard, app = self.target('dashboard'), self.target('app')
        bridge = m.Bridge(self.root, native=dashboard, allowed_candidate='dashboard-hash',
                          authorization_reference='synthetic-review', app=app)
        self.assertNotIn('app_execute', {t['name'] for t in bridge.definitions()})
        with self.assertRaisesRegex(ValueError, 'unknown_or_disabled'):
            bridge.call('app_execute', {'candidate_sha256': 'dashboard-hash'})
        with self.assertRaisesRegex(ValueError, 'separate_surface_documents'):
            m.Bridge(self.root, native=dashboard, app=self.target('dashboard'))
        alias = self.target('dashboard')
        alias.target.base_url = 'https://SYNTHETIC.omniapp.co:443'
        with self.assertRaisesRegex(ValueError, 'separate_surface_documents'):
            m.Bridge(self.root, native=dashboard, app=alias)
        with self.assertRaisesRegex(ValueError, 'app_startup_authority'):
            m.Bridge(self.root, app=app, allowed_app_candidate='app-hash')
        app.execute.assert_not_called()

    def test_app_exact_candidate_authority_and_dispatch(self):
        app = self.target('app')
        bridge = m.Bridge(self.root, app=app, allowed_app_candidate='app-hash',
                          app_authorization_reference='synthetic-app-review')
        with self.assertRaisesRegex(ValueError, 'app_candidate_not_authorized'):
            bridge.call('app_execute', {'candidate_sha256': 'dashboard-hash'})
        app.execute.assert_not_called()
        bridge.call('app_prepare', {'spec': 'contracts/reviewed-app.json'})
        app.prepare.assert_called_once_with('contracts/reviewed-app.json')
        bridge.call('app_execute', {'candidate_sha256': 'app-hash'})
        app.execute.assert_called_once_with('app-hash', 'synthetic-app-review')
        self.assertNotIn('native_execute', {t['name'] for t in bridge.definitions()})
