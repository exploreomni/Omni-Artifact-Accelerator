"""Passive checks of retained official Qlik MCP calls; no remote tool client.

Schema/call pins establish supplied consistency, not authenticated provenance.
Unknown schema semantics, source completeness and effective access stay unverified.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

DISCOVERY = {'qlik_search', 'qlik_describe_app', 'qlik_get_fields', 'qlik_list_sheets',
             'qlik_get_sheet_details', 'qlik_get_chart_info', 'qlik_list_dimensions',
             'qlik_list_measures', 'qlik_list_bookmarks', 'qlik_get_data_model',
             'qlik_get_script', 'qlik_get_lineage'}
QUERY = {'qlik_get_chart_data', 'qlik_get_field_values', 'qlik_search_field_values'}
SELECTION = {'qlik_select_values', 'qlik_clear_selections', 'qlik_select_bookmark'}
READBACK = {'qlik_get_current_selections'}


def need(condition, code):
    if not condition:
        raise ValueError('qlik.mcp.' + code)


def text(value):
    return type(value) is str and 0 < len(value) <= 2048 and all(32 <= ord(c) != 127 for c in value)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def pointer(value, path):
    need(type(path) is str and len(path) <= 2048 and (path == '' or path.startswith('/')), 'pointer')
    for part in path.split('/')[1:] if path else []:
        need(not re.search(r'~(?![01])', part), 'pointer_escape')
        key = part.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            need(key in value, 'pointer_missing'); value = value[key]
        elif type(value) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', key) and int(key) < len(value), 'pointer_index')
            value = value[int(key)]
        else:
            raise ValueError('qlik.mcp.pointer_missing')
    return value


def bounded_clean(value):
    path = Path(__file__).with_name('powerbi_capture_files.py')
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'module_symlink')
    spec = importlib.util.spec_from_file_location('qlik_mcp_files', path)
    files = importlib.util.module_from_spec(spec); spec.loader.exec_module(files)
    raw = files.encoded(value)
    files.decode(raw); files.secret_check(value); files.safe_text(raw)


def successful(response):
    need(type(response) is dict, 'response_object')
    envelopes = [response, response.get('structuredContent')]
    if 'content' in response:
        need(type(response['content']) is list, 'content_array')
        for block in response['content']:
            need(type(block) is dict, 'content_block')
            if block.get('type') != 'text':
                continue
            raw = block.get('text')
            need(type(raw) is str, 'content_text')
            if not raw.lstrip().startswith(('{', '[')):
                continue
            def pairs(items):
                result = {}
                for key, value in items:
                    need(key not in result, 'duplicate_response_key')
                    result[key] = value
                return result
            def invalid_constant(value):
                raise ValueError('qlik.mcp.nonfinite_response')
            try:
                decoded = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
            except (ValueError, RecursionError):
                raise ValueError('qlik.mcp.invalid_json_text_response') from None
            # Inspect only explicit envelopes, not arbitrary tabular data rows.
            if type(decoded) is dict:
                envelopes.extend((decoded, decoded.get('structuredContent')))
    for item in envelopes:
        if type(item) is dict:
            need(item.get('isError') is not True and not item.get('error') and item.get('success') is not False,
                 'failed_response')
            status = item.get('status')
            need(not (type(status) is str and status.casefold() in ('error', 'failed', 'rejected')), 'failed_response')


def validate_evidence(value):
    bounded_clean(value)
    need(type(value) is dict and set(value) == {'schema_version', 'server', 'identity', 'app_id',
         'query_authorization_ref', 'selection_authorization_ref', 'calls'}, 'contract')
    need(value['schema_version'] == 'qlik-mcp-evidence.v1' and text(value['app_id']), 'schema_or_app')
    identity = value['identity']
    need(type(identity) is dict and set(identity) == {'source_origin', 'tenant_id', 'principal_ref', 'reference'}
         and all(text(v) for v in identity.values()), 'identity')
    origin = urlsplit(identity['source_origin'])
    need(origin.scheme == 'https' and origin.hostname and origin.netloc == origin.hostname
         and not origin.path and not origin.query and not origin.fragment, 'origin')
    server = value['server']
    need(type(server) is dict and set(server) == {'endpoint', 'effective_version', 'schemas', 'reference'}
         and text(server['reference']) and text(server['effective_version']), 'server')
    need(server['endpoint'] == identity['source_origin'] + '/api/ai/mcp', 'endpoint')
    schemas = server['schemas']
    need(type(schemas) is list and 0 < len(schemas) <= 100, 'schemas')
    indexed = {}
    for schema in schemas:
        need(type(schema) is dict and set(schema) == {'name', 'inputSchema'} and text(schema['name'])
             and type(schema['inputSchema']) is dict and schema['name'] not in indexed, 'schema_entry')
        indexed[schema['name']] = schema
    calls = value['calls']
    need(type(calls) is list and 0 < len(calls) <= 500, 'calls')
    ids, sessions, receipts = set(), {}, []
    for call in calls:
        need(type(call) is dict and set(call) == {'id', 'tool', 'arguments', 'response', 'schema_sha256',
             'identity', 'argument_pointers', 'response_pointers', 'session_ref', 'reference'}, 'call')
        name = call['tool']
        need(name in DISCOVERY | QUERY | SELECTION | READBACK, 'unsupported_tool')
        need(text(call['id']) and call['id'] not in ids and text(call['reference']), 'call_identity')
        ids.add(call['id'])
        need(name in indexed and call['schema_sha256'] == sha(indexed[name]), 'schema_changed')
        need(call['identity'] == identity, 'identity_changed')
        args, ap, rp = call['arguments'], call['argument_pointers'], call['response_pointers']
        need(type(args) is dict and type(ap) is dict and type(rp) is dict, 'arguments')
        need(set(ap) <= {'app_id', 'object_id'} and set(rp) <= {'app_id', 'object_id', 'state'}, 'mapping')
        schema = indexed[name]['inputSchema']
        need(type(schema.get('properties')) is dict and type(schema.get('required', [])) is list
             and all(type(k) is str for k in schema.get('required', []))
             and set(schema.get('required', [])) <= set(args), 'arguments_schema')
        if schema.get('additionalProperties') is False:
            need(set(args) <= set(schema['properties']), 'arguments_schema')
        successful(call['response'])
        # Mappings are explicit declarations checked against retained bytes, never
        # guessed vendor argument names or an authenticated scope grant.
        app_scoped = name not in {'qlik_search', 'qlik_get_lineage'}
        if app_scoped:
            need('app_id' in ap and pointer(args, ap['app_id']) == value['app_id'], 'app_binding')
        for alias in ('appId', 'app_id'):
            need(alias not in args or args[alias] == value['app_id'], 'app_scope_changed')
        for alias, expected in (('tenant_id', identity['tenant_id']), ('tenantId', identity['tenant_id']),
                                ('source_origin', identity['source_origin']), ('principal_ref', identity['principal_ref'])):
            need(alias not in args or args[alias] == expected, 'identity_scope_changed')
        if 'app_id' in rp:
            need(pointer(call['response'], rp['app_id']) == value['app_id'], 'response_app_changed')
        if name in {'qlik_get_chart_info', 'qlik_get_chart_data', 'qlik_get_sheet_details'}:
            need('object_id' in ap and text(pointer(args, ap['object_id'])), 'object_binding')
        if 'object_id' in rp:
            need('object_id' in ap and pointer(call['response'], rp['object_id']) == pointer(args, ap['object_id']),
                 'response_object_changed')
        if name in QUERY | SELECTION | READBACK:
            need(text(call['session_ref']), 'session_reference')
            session = sessions.setdefault(call['session_ref'], {'state': None, 'readback_call': None, 'pending': False})
            if name in QUERY:
                need(text(value['query_authorization_ref']), 'query_authorization_evidence')
                need(session['state'] is not None and not session['pending'], 'selection_readback_required')
            elif name in SELECTION:
                need(text(value['selection_authorization_ref']), 'selection_authorization_evidence')
                session['pending'] = True; session['state'] = None; session['readback_call'] = None
            else:
                need('state' in rp and type(pointer(call['response'], rp['state'])) is dict, 'observed_state_required')
                session.update(state=sha(pointer(call['response'], rp['state'])), readback_call=call['id'], pending=False)
        else:
            need(call['session_ref'] is None, 'unexpected_session_reference')
        receipts.append({'call_id': call['id'], 'tool': name, 'call_sha256': sha(call),
            'classification': 'selection_change' if name in SELECTION else 'query' if name in QUERY else 'metadata',
            'observed_state_sha256': sessions[call['session_ref']]['state'] if call['session_ref'] in sessions else None})
    incomplete = any(s['pending'] for s in sessions.values())
    return {'schema_version': 1, 'kind': 'analyst_qlik_mcp_evidence_check', 'source_sha256': sha(value),
        'identity': copy.deepcopy(identity), 'app_id': value['app_id'], 'schema_sha256': sha(schemas),
        'effective_version': server['effective_version'], 'calls': receipts, 'sessions': sessions,
        'status': 'incomplete' if incomplete else 'consistent_supplied_evidence',
        'gaps': ['supplied_evidence_not_authenticated', 'argument_mapping_and_session_isolation_require_host_qualification',
                 'full_vendor_schema_validation_not_performed', 'metadata_is_not_native_definition_or_complete_inventory',
                 'chart_pagination_population_and_reload_must_be_qualified_separately',
                 'source_numeric_visual_and_effective_access_qualification_pending'] +
                (['selection_readback_pending'] if incomplete else []),
        'authorizes_remote_call': False, 'authorizes_target_write': False}
