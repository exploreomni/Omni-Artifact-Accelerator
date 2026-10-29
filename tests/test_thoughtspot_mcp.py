"""Retained MCP evidence only; never connects or executes Spotter tools."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('thoughtspot_mcp_tested', ROOT /
    'skills/omni-artifact-translator/scripts/thoughtspot_mcp.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def fixture(query=False):
    identity = {'source_origin': 'https://source.example.invalid', 'org_id': '7',
                'principal_ref': 'fixture-persona', 'reference': 'synthetic scope'}
    names = ['search_objects', 'create_analysis_session', 'send_session_message', 'get_session_updates']
    schemas = [{'name': n, 'inputSchema': {'type': 'object', 'properties': {
        'data_source_id': {'type': 'string'}, 'analytical_session_id': {'type': 'string'}},
        'additionalProperties': False}} for n in names]
    def call(n, args, response, pointers):
        return {'id': n, 'tool': n, 'arguments': args, 'response': response,
                'schema_sha256': M.sha(next(s for s in schemas if s['name'] == n)),
                'identity': copy.deepcopy(identity), 'response_pointers': pointers,
                'reference': 'original synthetic tool response'}
    calls = [call('search_objects', {}, {'objects': []}, {})]
    if query:
        calls += [call('create_analysis_session', {'data_source_id': 'model-1'},
                       {'structuredContent': {'session': 'session-1'}}, {'session': '/structuredContent/session'}),
                  call('send_session_message', {'analytical_session_id': 'session-1'}, {'success': True}, {}),
                  call('get_session_updates', {'analytical_session_id': 'session-1'},
                       {'structuredContent': {'is_done': True, 'answer': {'answer_id': 'answer-1'}}},
                       {'is_done': '/structuredContent/is_done'})]
    return {'schema_version': 'thoughtspot-mcp-evidence.v1', 'server': {
        'endpoint': 'https://agent.thoughtspot.app/mcp?api-version=2026-06-01',
        'effective_version': 'observed-synthetic-version', 'schemas': schemas, 'reference': 'schema export'},
        'identity': identity, 'query_authorization_ref': 'explicit prior query decision' if query else None,
        'calls': calls}


class ThoughtspotMcp(unittest.TestCase):
    def test_discovery_never_claims_definition_or_authority(self):
        report = M.validate_evidence(fixture())
        self.assertFalse(report['authorizes_remote_call']); self.assertFalse(report['authorizes_target_write'])
        self.assertEqual(report['sessions'], {})
        self.assertIn('search_metadata_does_not_replace_native_tml_or_independent_inventory', report['gaps'])

    def test_complete_and_incomplete_session_evidence(self):
        value = fixture(True); report = M.validate_evidence(value)
        self.assertEqual(report['sessions']['session-1']['completed_generations'], [1])
        value['calls'][-1]['response']['structuredContent']['is_done'] = False
        self.assertEqual(M.validate_evidence(value)['status'], 'incomplete')
        value['calls'][-1]['response']['structuredContent']['is_done'] = 'true'
        with self.assertRaisesRegex(ValueError, 'completion_boolean'): M.validate_evidence(value)

    def test_scope_schema_and_endpoint_cannot_drift(self):
        for path, replacement in [('org', '8'), ('schema', '0' * 64), ('url', 'https://evil.example/mcp?api-version=2026-06-01'),
                                  ('url', 'https://agent.thoughtspot.app/mcp?api-version=latest')]:
            value = fixture(True)
            if path == 'org': value['calls'][-1]['identity']['org_id'] = replacement
            elif path == 'schema': value['calls'][-1]['schema_sha256'] = replacement
            else: value['server']['endpoint'] = replacement
            with self.subTest(path=path), self.assertRaises(ValueError): M.validate_evidence(value)

    def test_query_grant_data_source_session_and_completion_are_required(self):
        changes = [lambda v: v.update(query_authorization_ref=None),
                   lambda v: v['calls'][1]['arguments'].clear(),
                   lambda v: v['calls'][-1]['arguments'].update(analytical_session_id='wrong'),
                   lambda v: v['calls'][-1]['response_pointers'].update(is_done='/missing')]
        for change in changes:
            value = fixture(True); change(value)
            with self.assertRaises(ValueError): M.validate_evidence(value)

    def test_secret_scope_and_failed_response_cannot_look_complete(self):
        for kind in ['secret', 'bearer', 'org', 'source', 'failed', 'error', 'session', 'nested-session']:
            value = fixture(True)
            call = value['calls'][-1]
            if kind == 'secret': call['response']['nested'] = {'access_token': 'synthetic-sensitive-value'}
            elif kind == 'bearer': call['response']['text'] = 'Bearer synthetic-sensitive-value'
            elif kind == 'org': call['arguments']['org_id'] = 'different'
            elif kind == 'source': call['arguments']['data_source_id'] = 'different'
            elif kind == 'failed': call['response']['isError'] = True
            elif kind == 'error': call['response']['structuredContent']['error'] = {'message': 'Failure'}
            elif kind == 'session': call['response']['analytical_session_id'] = 'different'
            else:
                call['response']['structuredContent']['session'] = 'different'
                call['response_pointers']['session'] = '/structuredContent/session'
            # Admit documented scope selectors into the supplied schema to prove
            # the semantic scope check, not just additionalProperties, rejects.
            schema = value['server']['schemas'][-1]
            schema['inputSchema']['properties']['org_id'] = {'type': 'string'}
            call['schema_sha256'] = M.sha(schema)
            with self.subTest(kind=kind), self.assertRaises(ValueError): M.validate_evidence(value)

    def test_writes_org_switch_duplicates_and_overlapping_generations_rejected(self):
        for name in ['switch_org', 'create_dashboard', 'execute_sql', 'getDataSourceSuggestions']:
            value = fixture(); value['calls'][0]['tool'] = name
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'tool_not_supported'):
                M.validate_evidence(value)
        value = fixture(); value['calls'].append(copy.deepcopy(value['calls'][0]))
        with self.assertRaisesRegex(ValueError, 'call_identity'): M.validate_evidence(value)
        value = fixture(True); extra = copy.deepcopy(value['calls'][2]); extra['id'] = 'second-message'
        value['calls'].insert(3, extra)
        with self.assertRaisesRegex(ValueError, 'overlapping_generation'): M.validate_evidence(value)


if __name__ == '__main__':
    unittest.main()
