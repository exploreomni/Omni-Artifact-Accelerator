"""Retained synthetic tool evidence; no remote MCP or third-party runtime."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ms_mcp', ROOT / 'skills/omni-artifact-translator/scripts/microstrategy_mcp.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def fixture():
    # Deliberately not an invented vendor tool name: this synthetic schema
    # proves that actual discovery, rather than a hardcoded catalog, is required.
    schema = {'name': 'fixture_semantics', 'inputSchema': {'type': 'object', 'properties': {
        'project_id': {'type': 'string'}, 'model_id': {'type': 'string'}},
        'required': ['project_id'], 'additionalProperties': False}, 'annotations': {'readOnlyHint': True}}
    identity = {'source_origin': 'https://strategy.example.invalid', 'project_id': 'project-one',
        'principal_ref': 'fixture-reader', 'reference': 'Synthetic identity, not authentication'}
    scope = {'project_id': 'project-one', 'model_id': 'model-one', 'cube_id': None, 'agent_id': None,
        'state_sha256': '1' * 64, 'reference': 'Synthetic scoped state'}
    return {'schema_version': 'microstrategy-mcp-evidence.v1', 'server': {
        'endpoint': identity['source_origin'] + '/collaboration/mcp/mosaic', 'effective_version': 'fixture-version',
        'schemas': [schema], 'reference': 'Synthetic original tools/list'}, 'identity': identity,
        'tool_policy': [{'tool': schema['name'], 'schema_sha256': M.sha(schema), 'classification': 'metadata',
                         'reference': 'Synthetic operator review'}], 'query_authorization_ref': None,
        'calls': [{'id': 'one', 'tool': schema['name'], 'arguments': {'project_id': 'project-one', 'model_id': 'model-one'},
            'response': {'structuredContent': {'project_id': 'project-one', 'model_id': 'model-one'}},
            'schema_sha256': M.sha(schema), 'identity': copy.deepcopy(identity), 'scope': scope,
            'response_pointers': {'project_id': '/structuredContent/project_id', 'model_id': '/structuredContent/model_id'},
            'reference': 'Synthetic retained call'}]}


class MicrostrategyMcpTests(unittest.TestCase):
    def test_dynamic_catalog_is_passive_and_not_layout_or_numeric_proof(self):
        result = M.validate_evidence(fixture())
        self.assertFalse(result['authorizes_execution'])
        self.assertIn('mcp_is_not_dashboard_layout_or_export_evidence', result['gaps'])
        self.assertEqual(result['status'], 'consistent_retained_evidence')

    def test_schema_identity_endpoint_and_response_drift(self):
        mutations = [lambda x: x['server']['schemas'][0]['inputSchema'].update(required=[]),
            lambda x: x['calls'][0]['identity'].update(principal_ref='another-reader'),
            lambda x: x['server'].update(endpoint='https://elsewhere.example.invalid/collaboration/mcp/mosaic'),
            lambda x: x['calls'][0]['response']['structuredContent'].update(model_id='another-model'),
            lambda x: x['calls'][0]['arguments'].update(project_id='another-project')]
        for mutate in mutations:
            v = fixture(); mutate(v)
            with self.assertRaises(ValueError): M.validate_evidence(v)

    def test_query_authority_and_state_are_separate_retained_evidence(self):
        v = fixture(); v['tool_policy'][0]['classification'] = 'query'
        with self.assertRaisesRegex(ValueError, 'query_scope'): M.validate_evidence(v)
        v['query_authorization_ref'] = 'Synthetic past query grant'
        self.assertEqual(M.validate_evidence(v)['calls'][0]['classification'], 'query')
        v['calls'][0]['scope']['state_sha256'] = None
        with self.assertRaisesRegex(ValueError, 'query_scope'): M.validate_evidence(v)

    def test_writes_and_errors_never_become_evidence(self):
        v = fixture(); v['tool_policy'][0]['classification'] = 'source_write'
        with self.assertRaisesRegex(ValueError, 'writing'): M.validate_evidence(v)
        for response in [{'isError': True}, {'content': [{'type': 'text', 'text': '{"error":"denied"}'}]},
                         {'structuredContent': {'status': 'failed'}}]:
            v = fixture(); v['calls'][0].update(response=response, response_pointers={})
            with self.assertRaisesRegex(ValueError, 'failed_tool'): M.validate_evidence(v)

    def test_session_material_is_not_retained(self):
        v = fixture(); v['calls'][0]['response']['X-MSTR-AuthToken'] = 'fixture-token'
        with self.assertRaises(ValueError): M.validate_evidence(v)


if __name__ == '__main__': unittest.main()
