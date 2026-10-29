"""Validate already-retained Spotter evidence. No network, SDK or tool dispatch.

These are evidence checks, not authorization or a general JSON Schema engine.
Tool schemas and raw responses remain source data. A search hit is not TML.
"""
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs

DISCOVERY = {'list_orgs', 'search_objects'}
QUERY = {'create_analysis_session', 'send_session_message', 'get_session_updates'}


def bounded_clean(value):
    path = Path(__file__).with_name('powerbi_capture_files.py')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('thoughtspot_mcp_files', path)
    files = importlib.util.module_from_spec(spec); spec.loader.exec_module(files)
    raw = files.encoded(value)
    files.decode(raw); files.secret_check(value); files.safe_text(raw)


def response_success(response):
    """Recognized MCP/structured envelopes only; unknown vendor semantics stay gaps."""
    for item in (response, response.get('structuredContent') if type(response) is dict else None):
        if type(item) is dict:
            need(item.get('isError') is not True and not item.get('error') and item.get('success') is not False,
                 'failed_tool_response')
            status = item.get('status')
            need(not (type(status) is str and status.casefold() in {'error', 'failed', 'failure', 'rejected'}),
                 'failed_tool_response')


def response_session(response, mappings, session):
    if 'session' in mappings:
        need(pointer(response, mappings['session']) == session, 'response_session_changed')
    for item in (response, response.get('structuredContent') if type(response) is dict else None):
        if type(item) is dict and 'analytical_session_id' in item:
            need(item['analytical_session_id'] == session, 'response_session_changed')


def need(condition, code):
    if not condition:
        raise ValueError('thoughtspot.mcp.' + code)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 2048 and all(ord(c) >= 32 for c in value)


def pointer(value, path):
    need(type(path) is str and (path == '' or path.startswith('/')) and len(path) <= 2048, 'pointer')
    for part in path.split('/')[1:] if path else []:
        need(not re.search(r'~(?![01])', part), 'pointer_escape')
        key = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(key in value, 'pointer_missing'); value = value[key]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', key) and int(key) < len(value), 'pointer_index')
            value = value[int(key)]
        else:
            raise ValueError('thoughtspot.mcp.pointer_missing')
    return value


def validate_evidence(value):
    """Check original call/schema pins and a bounded complete-session chronology.

    Query authorization references document prior operator decisions; they cannot
    authorize a future call. Unknown calls or changing Org require another review.
    """
    bounded_clean(value)
    need(type(value) is dict and set(value) == {'schema_version', 'server', 'identity',
         'query_authorization_ref', 'calls'}, 'contract')
    need(value['schema_version'] == 'thoughtspot-mcp-evidence.v1', 'schema')
    server = value['server']
    need(type(server) is dict and set(server) == {'endpoint', 'effective_version', 'schemas', 'reference'}, 'server')
    need(text(server['reference']) and text(server['effective_version']), 'server_reference')
    endpoint = urlsplit(server['endpoint'])
    query = parse_qs(endpoint.query, strict_parsing=True, keep_blank_values=True)
    need(endpoint.scheme == 'https' and endpoint.netloc == 'agent.thoughtspot.app' and
         endpoint.path in ('/mcp', '/token/mcp') and not endpoint.fragment and
         set(query) == {'api-version'} and len(query['api-version']) == 1, 'endpoint')
    version = query['api-version'][0]
    need(re.fullmatch(r'\d{4}-\d{2}-\d{2}', version), 'version_pin')
    datetime.date.fromisoformat(version)
    identity = value['identity']
    need(type(identity) is dict and set(identity) == {'source_origin', 'org_id', 'principal_ref', 'reference'}
         and all(text(v) for v in identity.values()), 'identity')
    origin = urlsplit(identity['source_origin'])
    need(origin.scheme == 'https' and origin.hostname and not origin.username and not origin.password
         and origin.path == '' and not origin.query and not origin.fragment, 'source_origin')
    schemas = server['schemas']
    need(type(schemas) is list and 0 < len(schemas) <= 100, 'schemas')
    by_name = {}
    for tool in schemas:
        need(type(tool) is dict and set(tool) == {'name', 'inputSchema'} and text(tool['name'])
             and type(tool['inputSchema']) is dict, 'tool_schema')
        need(tool['name'] not in by_name, 'duplicate_schema')
        by_name[tool['name']] = tool
    calls = value['calls']
    need(type(calls) is list and 0 < len(calls) <= 500, 'calls')
    sessions, ids, receipts = {}, set(), []
    for call in calls:
        need(type(call) is dict and set(call) == {'id', 'tool', 'arguments', 'response',
             'schema_sha256', 'identity', 'response_pointers', 'reference'}, 'call')
        name = call['tool']
        need(name in DISCOVERY | QUERY, 'tool_not_supported')
        need(text(call['id']) and call['id'] not in ids and text(call['reference']), 'call_identity')
        ids.add(call['id'])
        need(name in by_name and call['schema_sha256'] == sha(by_name[name]), 'schema_changed')
        need(call['identity'] == identity, 'org_or_principal_changed')
        args, mappings = call['arguments'], call['response_pointers']
        need(type(args) is dict and type(mappings) is dict, 'arguments')
        response_success(call['response'])
        # These documented selectors are the only scope overrides understood here.
        # Alternate selector semantics need an explicit new reviewed profile.
        for selector, expected in (('org_id', identity['org_id']), ('source_origin', identity['source_origin']),
                                   ('principal_ref', identity['principal_ref'])):
            need(selector not in args or args[selector] == expected, 'argument_scope_changed')
        scope_aliases = {'org', 'orgId', 'organization_id', 'tenant', 'tenant_id', 'dataSourceId', 'model_id'}
        need(not scope_aliases.intersection(args), 'unsupported_scope_selector')
        schema = by_name[name]['inputSchema']
        # Full vendor schema validation belongs to the configured MCP host. These
        # checks catch missing/extra top-level fields without resolving any $ref.
        properties = schema.get('properties')
        need(type(properties) is dict and set(schema.get('required', [])) <= set(args), 'arguments_schema')
        if schema.get('additionalProperties') is False:
            need(set(args) <= set(properties), 'arguments_schema')
        if name in QUERY:
            need(text(value['query_authorization_ref']), 'query_authorization_evidence_required')
        if name == 'create_analysis_session':
            need(text(args.get('data_source_id')), 'explicit_data_source_required')
            need(set(mappings) == {'session'}, 'session_pointer_required')
            session = pointer(call['response'], mappings['session'])
            need(text(session) and session not in sessions, 'session_identity')
            response_session(call['response'], mappings, session)
            sessions[session] = {'data_source_id': args['data_source_id'], 'pending': False,
                                 'generation': 0, 'completed_generations': [], 'poll_call_ids': []}
        elif name in {'send_session_message', 'get_session_updates'}:
            session = args.get('analytical_session_id')
            need(text(session) and session in sessions, 'unknown_session')
            state = sessions[session]
            need('data_source_id' not in args or args['data_source_id'] == state['data_source_id'], 'data_source_changed')
            response_session(call['response'], mappings, session)
            if name == 'send_session_message':
                need(not state['pending'] and set(mappings) <= {'session'}, 'overlapping_generation')
                state['generation'] += 1; state['pending'] = True
            else:
                need(state['pending'] and {'is_done'} <= set(mappings) <= {'is_done', 'session'}, 'poll_sequence')
                done = pointer(call['response'], mappings['is_done'])
                need(type(done) is bool, 'completion_boolean')
                state['poll_call_ids'].append(call['id'])
                if done:
                    state['pending'] = False
                    state['completed_generations'].append(state['generation'])
        else:
            need(mappings == {}, 'unexpected_response_mapping')
        receipts.append({'call_id': call['id'], 'tool': name, 'classification':
                         'discovery' if name in DISCOVERY else 'query', 'call_sha256': sha(call)})
    gaps = ['supplied_evidence_not_authenticated', 'tool_schema_semantics_require_host_validation',
            'search_metadata_does_not_replace_native_tml_or_independent_inventory',
            'session_generation_ordinal_is_not_a_rest_export_generation_number',
            'source_numeric_visual_and_effective_access_qualification_pending']
    if any(s['pending'] or not s['completed_generations'] for s in sessions.values()):
        gaps.append('session_incomplete')
    return {'schema_version': 1, 'kind': 'analyst_thoughtspot_mcp_evidence_check',
            'source_sha256': sha(value), 'identity': copy.deepcopy(identity),
            'requested_api_version': version, 'effective_version': server['effective_version'],
            'schema_sha256': sha(schemas), 'calls': receipts, 'sessions': sessions,
            'status': 'incomplete' if 'session_incomplete' in gaps else 'consistent_supplied_evidence',
            'gaps': gaps, 'authorizes_remote_call': False, 'authorizes_target_write': False}
