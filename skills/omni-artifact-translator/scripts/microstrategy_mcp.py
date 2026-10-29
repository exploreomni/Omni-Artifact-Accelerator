"""Passive Strategy MCP evidence checks; no remote calls or connector setup.

Actual retained tools/list schemas are required. Reviewed classifications are
evidence, not authority. Responses remain inert and are not numerical proof.
"""
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def need(ok, code):
    if not ok:
        raise ValueError('microstrategy.mcp.' + code)


_path = Path(__file__).with_name('powerbi_capture_files.py')
need(not any(p.is_symlink() for p in (_path, *_path.parents)), 'module_symlink')
_spec = importlib.util.spec_from_file_location('microstrategy_mcp_files', _path)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
sha = F.sha


def text(v):
    return type(v) is str and 0 < len(v) <= 2048 and all(ord(c) >= 32 for c in v)


def clean(v):
    raw = F.encoded(v)
    F.decode(raw); F.secret_check(v); F.safe_text(raw)
    need(not re.search(rb'(?i)(?:x-mstr-authtoken|set-cookie|jsessionid|authorization)["\s]*[:=]', raw),
         'session_material_rejected')


def pointer(v, path):
    need(type(path) is str and (path == '' or path.startswith('/')), 'pointer')
    for key in path.split('/')[1:] if path else []:
        need(not re.search(r'~(?![01])', key), 'pointer_escape')
        key = key.replace('~1', '/').replace('~0', '~')
        if type(v) is dict:
            need(key in v, 'pointer_missing'); v = v[key]
        elif type(v) is list:
            need(re.fullmatch(r'0|[1-9][0-9]*', key) and int(key) < len(v), 'pointer_index')
            v = v[int(key)]
        else:
            raise ValueError('microstrategy.mcp.pointer_missing')
    return v


def response_success(response):
    """Inspect structured and JSON-in-text MCP envelopes without executing content."""
    need(type(response) is dict, 'response_envelope')
    stack = [response]
    visited = 0
    while stack:
        item = stack.pop(); visited += 1
        need(visited <= 10000, 'response_bound')
        if type(item) is list:
            stack.extend(item)
        elif type(item) is dict:
            need(item.get('isError') is not True and not item.get('error') and item.get('success') is not False,
                 'failed_tool_response')
            need(str(item.get('status', '')).casefold() not in {'error', 'failed', 'failure', 'rejected', 'cancelled'},
                 'failed_tool_response')
            stack.extend(v for v in item.values() if type(v) in (dict, list))
            if item.get('type') == 'text' and type(item.get('text')) is str:
                body = item['text'].strip()
                if body.startswith(('{', '[')):
                    try:
                        decoded = F.decode(body.encode())
                    except (ValueError, UnicodeError):
                        raise ValueError('microstrategy.mcp.invalid_json_text') from None
                    stack.append(decoded)


def validate_evidence(value):
    clean(value)
    need(type(value) is dict and set(value) == {'schema_version', 'server', 'identity', 'tool_policy',
         'query_authorization_ref', 'calls'} and value['schema_version'] == 'microstrategy-mcp-evidence.v1', 'contract')
    server, identity = value['server'], value['identity']
    need(type(server) is dict and set(server) == {'endpoint', 'effective_version', 'schemas', 'reference'}, 'server')
    need(text(server['effective_version']) and text(server['reference']), 'server_evidence')
    need(type(identity) is dict and set(identity) == {'source_origin', 'project_id', 'principal_ref', 'reference'}
         and all(text(v) for v in identity.values()), 'identity')
    source, endpoint = urlsplit(identity['source_origin']), urlsplit(server['endpoint'])
    need(source.scheme == 'https' and source.hostname and source.netloc == source.hostname
         and not source.path and not source.query and not source.fragment, 'source_origin')
    need(endpoint.scheme == 'https' and endpoint.netloc == source.netloc and
         endpoint.path in ('/collaboration/mcp/agent', '/collaboration/mcp/mosaic') and
         not endpoint.query and not endpoint.fragment, 'endpoint')
    schemas = server['schemas']
    need(type(schemas) is list and 0 < len(schemas) <= 100, 'schemas')
    by_name = {}
    for schema in schemas:
        need(type(schema) is dict and {'name', 'inputSchema'} <= set(schema) and text(schema['name'])
             and type(schema['inputSchema']) is dict and schema['name'] not in by_name, 'tool_schema')
        by_name[schema['name']] = schema
    policy = value['tool_policy']
    need(type(policy) is list and 0 < len(policy) <= len(schemas), 'tool_policy')
    reviewed = {}
    for rule in policy:
        need(type(rule) is dict and set(rule) == {'tool', 'schema_sha256', 'classification', 'reference'}, 'policy_rule')
        name = rule['tool']
        need(name in by_name and name not in reviewed and rule['schema_sha256'] == sha(by_name[name]), 'schema_changed')
        need(rule['classification'] in ('metadata', 'query') and text(rule['reference']), 'source_writing_excluded')
        annotations = by_name[name].get('annotations', {})
        need(type(annotations) is dict and annotations.get('destructiveHint') is not True
             and annotations.get('readOnlyHint') is not False, 'source_writing_excluded')
        need(not re.search(r'(?i)(?:^|_)(?:delete|create|update|write|publish|grant|revoke|drop|execute_script)(?:_|$)', name),
             'source_writing_excluded')
        reviewed[name] = rule
    calls = value['calls']
    need(type(calls) is list and 0 < len(calls) <= 500, 'calls')
    ids, receipts = set(), []
    for call in calls:
        need(type(call) is dict and set(call) == {'id', 'tool', 'arguments', 'response', 'schema_sha256',
             'identity', 'scope', 'response_pointers', 'reference'}, 'call')
        name = call['tool']
        need(text(call['id']) and call['id'] not in ids and text(call['reference']), 'call_identity')
        ids.add(call['id'])
        need(name in reviewed and call['schema_sha256'] == sha(by_name[name]), 'unreviewed_or_changed_tool')
        need(call['identity'] == identity, 'project_or_principal_changed')
        args, scope, mappings = call['arguments'], call['scope'], call['response_pointers']
        need(type(args) is dict and type(scope) is dict and set(scope) == {'project_id', 'model_id', 'cube_id',
             'agent_id', 'state_sha256', 'reference'} and scope['project_id'] == identity['project_id']
             and text(scope['reference']), 'scope')
        for key in ('model_id', 'cube_id', 'agent_id'):
            need(scope[key] is None or text(scope[key]), 'source_object')
        need(scope['state_sha256'] is None or re.fullmatch('[a-f0-9]{64}', scope['state_sha256']), 'state_pin')
        schema = by_name[name]['inputSchema']
        need(type(schema.get('properties')) is dict and set(schema.get('required', [])) <= set(args), 'arguments_schema')
        if schema.get('additionalProperties') is False:
            need(set(args) <= set(schema['properties']), 'arguments_schema')
        need(type(mappings) is dict and set(mappings) <= {'project_id', 'principal_ref', 'model_id', 'cube_id', 'agent_id', 'state_sha256'},
             'response_mappings')
        for key, path in mappings.items():
            need(pointer(call['response'], path) == (identity[key] if key in identity else scope[key]), 'response_scope_changed')
        # Explicit selector aliases cannot silently override the retained scope.
        for key, expected in {**identity, **scope}.items():
            if key != 'reference' and key in args:
                need(args[key] == expected, 'argument_scope_changed')
        response_success(call['response'])
        if reviewed[name]['classification'] == 'query':
            need(text(value['query_authorization_ref']) and any(scope[k] for k in ('model_id', 'cube_id', 'agent_id'))
                 and scope['state_sha256'] is not None, 'query_scope_evidence_required')
        receipts.append({'call_id': call['id'], 'call_sha256': sha(call), 'classification': reviewed[name]['classification']})
    return {'schema_version': 1, 'kind': 'microstrategy_mcp_evidence_check', 'status': 'consistent_retained_evidence',
        'evidence_sha256': sha(value), 'identity': identity, 'calls': receipts, 'authorizes_execution': False,
        'native_validation': 'not_run', 'gaps': ['tool_policy_and_identity_not_authenticated',
        'nested_vendor_schema_validation_belongs_to_qualified_host', 'mcp_is_not_dashboard_layout_or_export_evidence',
        'generated_prose_and_tool_answers_are_not_numerical_proof', 'effective_access_not_verified']}
