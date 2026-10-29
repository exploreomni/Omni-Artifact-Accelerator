"""Retained synthetic MCP observations only; no connection or vendor runtime."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('qlik_mcp_tested', ROOT /
    'skills/omni-artifact-translator/scripts/qlik_mcp.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def fixture(query=False):
    identity = {'source_origin': 'https://source.example.invalid', 'tenant_id': 'tenant-1',
                'principal_ref': 'persona-1', 'reference': 'Synthetic scope'}
    names = ['qlik_list_sheets', 'qlik_get_current_selections', 'qlik_select_values', 'qlik_get_chart_data']
    schemas = [{'name': n, 'inputSchema': {'type': 'object', 'properties': {
        'appId': {'type': 'string'}, 'objectId': {'type': 'string'}}, 'required': ['appId'],
        'additionalProperties': False}} for n in names]
    def call(n, i, response, rp, session=None):
        args = {'appId': 'app-1'}; ap = {'app_id': '/appId'}
        if n == 'qlik_get_chart_data': args['objectId'] = 'chart-1'; ap['object_id'] = '/objectId'
        return {'id': i, 'tool': n, 'arguments': args, 'response': response,
                'schema_sha256': M.sha(next(s for s in schemas if s['name'] == n)),
                'identity': copy.deepcopy(identity), 'argument_pointers': ap, 'response_pointers': rp,
                'session_ref': session, 'reference': 'Synthetic retained call'}
    calls = [call('qlik_list_sheets', 'discover', {'sheets': []}, {})]
    if query:
        calls += [call('qlik_get_current_selections', 'before', {'state': {'$': {}}}, {'state': '/state'}, 'session-1'),
                  call('qlik_select_values', 'select', {'success': True}, {}, 'session-1'),
                  call('qlik_get_current_selections', 'after', {'state': {'$': {'District': ['West']}}}, {'state': '/state'}, 'session-1'),
                  call('qlik_get_chart_data', 'data', {'rows': []}, {}, 'session-1')]
    return {'schema_version': 'qlik-mcp-evidence.v1', 'server': {
        'endpoint': identity['source_origin'] + '/api/ai/mcp', 'effective_version': 'synthetic-profile-v1',
        'schemas': schemas, 'reference': 'Synthetic catalog'}, 'identity': identity, 'app_id': 'app-1',
        'query_authorization_ref': 'Prior query decision' if query else None,
        'selection_authorization_ref': 'Prior isolated-session selection decision' if query else None, 'calls': calls}


class QlikMcp(unittest.TestCase):
    def test_discovery_keeps_qualification_separate(self):
        r = M.validate_evidence(fixture())
        self.assertFalse(r['authorizes_remote_call']); self.assertFalse(r['authorizes_target_write'])
        self.assertIn('metadata_is_not_native_definition_or_complete_inventory', r['gaps'])

    def test_changed_state_must_be_observed_before_query(self):
        v = fixture(True); r = M.validate_evidence(v)
        self.assertEqual(r['calls'][-1]['observed_state_sha256'], M.sha({'$': {'District': ['West']}}))
        del v['calls'][3]
        with self.assertRaisesRegex(ValueError, 'selection_readback_required'): M.validate_evidence(v)

    def test_pending_selection_is_incomplete(self):
        v = fixture(True); v['calls'] = v['calls'][:3]
        self.assertEqual(M.validate_evidence(v)['status'], 'incomplete')

    def test_scope_schema_and_endpoint_rejected(self):
        changes = [lambda v: v['calls'][-1]['identity'].update(tenant_id='other'),
                   lambda v: v['calls'][-1]['arguments'].update(appId='other'),
                   lambda v: v['calls'][-1].update(schema_sha256='0'*64),
                   lambda v: v['server'].update(endpoint='https://other.example.invalid/api/ai/mcp'),
                   lambda v: v['calls'][-1].update(session_ref='other'),
                   lambda v: v['calls'][-1]['argument_pointers'].clear()]
        for change in changes:
            v = fixture(True); change(v)
            with self.assertRaises(ValueError): M.validate_evidence(v)

    def test_grants_are_separate_and_only_retained_evidence(self):
        for name in ('query_authorization_ref', 'selection_authorization_ref'):
            v = fixture(True); v[name] = None
            with self.subTest(name=name), self.assertRaises(ValueError): M.validate_evidence(v)

    def test_source_writes_and_ad_hoc_calculations_rejected(self):
        for name in ('qlik_create_sheet', 'qlik_create_data_object', 'qlik_start_app_reload',
                     'qlik_update_script', 'qlik_delete_bookmark', 'qlik_start_automation_run'):
            v = fixture(); v['calls'][0]['tool'] = name
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'unsupported_tool'): M.validate_evidence(v)

    def test_errors_secrets_duplicates_and_wrong_response_binding_rejected(self):
        changes = [lambda v: v['calls'][-1]['response'].update(isError=True),
                   lambda v: v['calls'][-1]['response'].update(access_token='synthetic-sensitive-value'),
                   lambda v: v['calls'].append(copy.deepcopy(v['calls'][0])),
                   lambda v: v['calls'][3]['response'].update(state=[])]
        for change in changes:
            v = fixture(True); change(v)
            with self.assertRaises(ValueError): M.validate_evidence(v)
        v = fixture(True); v['calls'][-1]['response'].update(app='other')
        v['calls'][-1]['response_pointers']['app_id'] = '/app'
        with self.assertRaisesRegex(ValueError, 'response_app_changed'): M.validate_evidence(v)

    def test_json_text_errors_and_ambiguous_envelopes_are_rejected(self):
        for raw in ('{"error":{"message":"source refused"}}', '{"success":false}',
                    '{"structuredContent":{"status":"failed"}}',
                    '{"success":false,"success":true}', '{"value":NaN}', '{"incomplete":'):
            v = fixture(); v['calls'][0]['response'] = {'content': [{'type': 'text', 'text': raw}]}
            with self.subTest(raw=raw), self.assertRaises(ValueError): M.validate_evidence(v)
        v = fixture(); v['calls'][0]['response'] = {'content': [{'type': 'text', 'text': '{"sheets":[]}'}]}
        self.assertEqual(M.validate_evidence(v)['status'], 'consistent_supplied_evidence')


if __name__ == '__main__':
    unittest.main()
