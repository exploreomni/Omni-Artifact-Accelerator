"""Protocol-level lifecycle coverage using original synthetic evidence only."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-accelerator/scripts'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load('execution_bridge_test', SCRIPTS / 'execution_bridge.py')
load('visual_workflow', SCRIPTS / 'visual_workflow.py')
M = load('execution_mcp_test', SCRIPTS / 'visual_mcp.py')
G = load('execution_gate_fixture', ROOT / 'tests/stage_gate_fixture.py')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / 'engagement'
        B.P.init(self.root, 'Neutral qualification fixture', 'net-new', 'app', branding='none', context_policy='bounded-context-v1')
        self.bridge = M.Bridge(self.root, tool_profile='execution')

    def save(self, name, value):
        path = 'inputs/' + name + '.json'
        B.P.write_json(self.root / path, value)
        return path

    def test_small_profile_excludes_unselected_sources_and_native_writes(self):
        names = {t['name'] for t in self.bridge.definitions()}
        self.assertEqual(len(names), 10)
        self.assertTrue(all(n.startswith('execution_') for n in names))
        self.assertNotIn('execution_host', names)
        with self.assertRaises(ValueError):
            self.bridge.call('native_execute', {'candidate': 'anything'})

    def test_selected_profile_cannot_expand_from_tool_arguments(self):
        bridge = M.Bridge(self.root, tool_profile='selected', enabled_tools=[])
        self.assertEqual(bridge.definitions(), self.bridge.definitions())
        with self.assertRaises(ValueError):
            bridge.call('execution_status', {'enabled_tools': ['native_execute']})

    def test_build_gate_is_visible_and_cannot_be_skipped(self):
        request = self.save('early-build', {'action': 'build'})
        report = self.bridge.call('execution_prepare', {'operation': 'preflight', 'request': request})
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['publication_authorized'])
        status = self.bridge.call('execution_status', {})
        self.assertFalse(status['stage']['release_ready'])

    def test_no_module_paths_commands_or_outside_requests(self):
        for args in ({'operation': 'shell', 'request': '/etc/passwd'},
                     {'operation': 'work', 'request': '../outside.json'},
                     {'operation': 'work', 'request': '/etc/passwd'},
                     {'operation': 'work', 'request': 'inputs/x.json', 'command': 'echo denied'}):
            with self.assertRaises((ValueError, OSError)):
                self.bridge.call('execution_prepare', args)

    def test_protocol_errors_are_structured_and_do_not_echo_source_content(self):
        self.bridge.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': M.PROTOCOL}})
        self.bridge.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        reply = self.bridge.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'execution_prepare', 'arguments': {'operation': 'unknown-secret'}}})
        self.assertTrue(reply['result']['isError'])
        value = json.loads(reply['result']['content'][0]['text'])
        self.assertEqual(value['code'], 'execution_request_rejected')
        self.assertNotIn('unknown-secret', str(value))

    def test_stdio_transport_discovers_profile_and_reports_gate(self):
        frames = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': M.PROTOCOL}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'execution_status', 'arguments': {}}},
        ]
        result = subprocess.run([sys.executable, '-I', '-S', '-B', str(SCRIPTS / 'visual_mcp.py'),
            '--project', str(self.root), '--tool-profile', 'execution'],
            input=''.join(json.dumps(f) + '\n' for f in frames), text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(len(replies[1]['result']['tools']), 10)
        status = json.loads(replies[2]['result']['content'][0]['text'])
        self.assertFalse(status['external_mutations_authorized'])

    def test_catalog_keeps_native_and_human_evidence_separate(self):
        catalog = self.bridge.call('execution_qualification', {'operation': 'catalog'})
        self.assertTrue({'host', 'native', 'visual', 'access', 'human'} <= {c['lane'] for c in catalog['scenarios']})
        self.assertFalse(catalog['publication_authorized'])

    def test_contract_discovery_is_scoped_and_usage_does_not_invent_billing(self):
        result = self.bridge.call('execution_contract', {'tool': 'execution_prepare', 'operation': 'claim'})
        self.assertEqual(result['required_request_fields'], ['attempt_id', 'packet'])
        report = self.bridge.call('execution_efficiency', {'operation': 'report'})
        self.assertFalse(result['publication_authorized'])
        self.assertIsNone(report['dollars'])

    def test_stage_sequence_requires_choice_before_design(self):
        gates = G.Lifecycle(self.root, B.P)
        gates.through('options')
        with self.assertRaises(ValueError):
            B.P.stage_require(self.root, 'build')
        self.assertEqual(self.bridge.call('execution_status', {})['stage']['next_stage'], 'choice')

    def test_reference_lifecycle_selection_bounded_worker_freeze_and_review(self):
        # One local vertical slice through real package operations. The synthetic
        # choice/driver/review evidence here never qualifies an actual agent host.
        gates = G.Lifecycle(self.root, B.P)
        with B.P.trusted_stage_provider(gates.host):
            intent = B.P.intent_helper()
            selections = []
            def select_through_bridge(root, spec, output):
                selections.append(output)
                request = self.save('intent-selection-' + str(len(selections)),
                    {'spec': Path(spec).relative_to(root).as_posix(), 'output': output})
                return self.bridge.call('execution_lifecycle', {'operation': 'intent_select', 'request': request})
            intent.select = select_through_bridge
            with patch.object(B.P, 'intent_helper', return_value=intent):
                gates.through()
            self.assertTrue(selections)
            self.assertEqual(self.bridge.call('execution_lifecycle', {'operation': 'intent_check'})['status'], 'consistent')
            self.bridge.call('execution_lifecycle', {'operation': 'product_brief', 'request': self.save('brief-output',
                {'output': 'deliverables/product-brief.md'})})
            selected = B.P.intent_helper().load_selected(self.root)['spec']
            output = 'deliverables/app.html'
            request = {'role': 'app-engineer', 'inputs': ['inputs/brief.txt'], 'output': 'tasks/integrated.json',
                'assignment': {'schema_version': 1, 'task_id': 'integrated-build', 'domain_id': 'observations',
                    'stage': 'app', 'role': 'app-engineer', 'scope_ids': [r['id'] for r in selected['requirements']],
                    'objective': 'Implement the selected original synthetic candidate', 'outputs': [output],
                    'acceptance': ['Preserve selected analytical and quality requirements'], 'dependency_paths': [],
                    'unknowns': ['Actual native runtime remains unobserved'], 'authoring_mode': 'reviewed_candidate'}}
            prepared = self.bridge.call('execution_prepare', {'operation': 'work', 'request': self.save('work', request)})
            packet = B.P.read_json(self.root / prepared['packet'])[0]
            context = {'schema_version': 1, 'kind': 'analyst_context_request',
                'packet': {'path': prepared['packet'], 'sha256': prepared['packet_sha256']}, 'mode': 'initial',
                'summary': 'Complete only this original selected fixture.', 'decisions': ['Retain selected direction'],
                'constraints': ['No external calls or packages'], 'stop_conditions': packet['stop_conditions'],
                'evidence': [{'id': 'original-brief', 'path': 'inputs/brief.txt',
                    'sha256': B.P.digest((self.root / 'inputs/brief.txt').read_bytes()),
                    'classification': 'internal', 'purpose': 'Original synthetic request',
                    'ranges': [[1, 1]], 'review_original': True}], 'classification': 'internal',
                'disclosure': {'allowed_classifications': ['internal'], 'review_ref': 'synthetic-local-case'},
                'shared_constraint_ids': packet.get('design_context', {}).get('shared_constraint_ids', [])}
            receipt = self.bridge.call('execution_prepare', {'operation': 'context', 'request': self.save('context', context), 'output': 'tasks/integrated-context'})
            self.bridge.call('execution_prepare', {'operation': 'claim', 'request': self.save('claim',
                {'attempt_id': 'integrated', 'packet': prepared['packet'], 'context_receipt': receipt['receipt_path']})})
            root = self.root
            class Driver:
                def launch(self, payload):
                    (root / output).parent.mkdir(exist_ok=True, parents=True)
                    (root / output).write_text('<!doctype html><main>Original synthetic observation candidate</main>')
                    self.observation = {'launch_id': payload['launch_id'], 'status': 'completed',
                        'host_run_reference': 'synthetic-local-invocation', 'context_mode': 'fresh',
                        'task_sha256': payload['task_sha256'], 'observed_model': None, 'observed_effort': None,
                        'tool_scope': ['assigned_file_write'], 'evidence_reference': 'synthetic-reference-driver'}
                    return self.observation
                def reconcile(self, launch_id):
                    return self.observation
            runtime = B.P.routing_helper('execution_runtime').Runtime(root, Driver(), {
                'adapter_id': 'original-reference-driver', 'adapter_version': '1', 'host_version': 'fixture',
                'configuration_sha256': 'a' * 64, 'tool_scope': ['assigned_file_write'], 'context_mode': 'fresh',
                'model': None, 'effort': None})
            bridge = M.Bridge(root, tool_profile='execution', execution_runtime=runtime)
            observed = bridge.call('execution_host', {'operation': 'launch', 'attempt_id': 'integrated'})
            self.assertEqual(observed['status'], 'completed')
            self.assertFalse(observed['host_isolation_verified'])
            bridge.call('execution_record', {'operation': 'checkpoint', 'request': self.save('checkpoint',
                {'attempt_id': 'integrated', 'status': 'outputs_recorded', 'reason': 'Synthetic completion', 'outputs': [output]})})
            bridge.call('execution_lifecycle', {'operation': 'freeze', 'request': self.save('freeze',
                {'id': 'integrated', 'builders': ['synthetic-local-invocation'], 'artifacts': [output],
                 'context': ['contracts/execution.json']})})
            gates.reviews()
            status = bridge.call('execution_status', {})
            self.assertTrue(status['stage']['release_ready'])
            self.assertFalse(status['stage']['review_assurance']['native_acceptance'])
            self.assertFalse(status['external_mutations_authorized'])
            self.assertEqual(bridge.call('execution_efficiency', {'operation': 'report'})['dispatch_count'], 1)


if __name__ == '__main__':
    unittest.main()
