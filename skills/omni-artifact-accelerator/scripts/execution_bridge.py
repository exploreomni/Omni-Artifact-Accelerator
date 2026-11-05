"""Small, host-neutral tool surface over existing engagement functions.

Fixed operation names and project-relative JSON requests; no command, module or
credential selection. Native write capabilities remain with their guarded host.
"""
import importlib.util
from pathlib import Path
import time

_spec = importlib.util.spec_from_file_location('bridge_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

OPERATIONS = P.routing_helper('execution_contracts').OPERATIONS


def definitions(tool, string, runtime=None):
    values = [tool('execution_status', 'Read current gates and task progress; optional request selects bounded status pages. No invocation or authorization.', {'request': string}, [], read=True)]
    values.append(tool('execution_contract', 'Read the small request contract for one fixed operation before preparing its JSON.',
        {'tool': {**string, 'enum': list(OPERATIONS)}, 'operation': string}, read=True))
    descriptions = {
        'execution_prepare': 'Prepare scoped work, bounded context, consolidated preflight or reservation using existing contracts.',
        'execution_record': 'Retain a supplied dispatch, checkpoint, usage, blocker or review; supplied records do not authenticate execution.',
        'execution_lifecycle': 'Advance the existing engagement through guarded startup, guidance, phase, stage and candidate operations.',
        'execution_review': 'Inspect or explicitly adopt incremental source-review policy; no native or human acceptance implied.',
        'execution_qualification': 'Inspect fixed qualification requirements or retain/check separately qualified supplied evidence.',
        'execution_assembly': 'Build or verify reproducible candidate bytes and compare pinned dependencies; existing build gates apply.',
        'execution_analysis': 'Bind result fields by explicit identity or compare original-source evidence through existing migration checks.',
        'execution_efficiency': 'Read measured task/context usage or explicitly adopt bounded context; never changes app caching or authorization.',
        'execution_host': 'Invoke or reconcile the operator-configured worker adapter; no caller-selected commands, tools or credentials.',
    }
    for name, choices in OPERATIONS.items():
        if name == 'execution_host' and runtime is None:
            continue
        props = {'operation': {**string, 'enum': list(choices)}}
        if name == 'execution_host':
            props['attempt_id'] = string
            required = ['operation', 'attempt_id']
        else:
            props.update(request=string, output=string)
            required = ['operation']
        values.append(tool(name, descriptions[name], props, required, external=name == 'execution_host'))
    return values


def status(root):
    gates = P.stage_status(root)
    tasks = P.routing_helper('task_operations').status(root)
    next_stage = gates.get('next_stage')
    return {'stage': {k: gates.get(k) for k in ('required', 'status', 'next_stage', 'completed_stages',
                'tail_sha256', 'candidate_sha256', 'release_ready', 'choice_assurance', 'review_assurance', 'experience_intent')},
            'blockers': ([{'area': 'stage', 'code': value} for value in gates.get('findings', [])] +
                         [{'area': 'tasks', 'code': value} for value in tasks.get('findings', [])]),
            'next_action': {'stage': next_stage, 'tool': 'execution_lifecycle' if next_stage else 'execution_qualification',
                            'requires_current_preflight': True},
            'tasks': tasks['tasks'], 'external_mutations_authorized': False,
            'incomplete': tasks.get('incomplete', False),
            'task_snapshot': {key: tasks.get(key) for key in ('status', 'snapshot_generation')},
            'choice_bindings': gates.get('choice_bindings', {}),
            'qualification': 'Readiness and reported progress only; the actual host owns execution and permission.'}


def call(root, name, args, runtime=None, host_context=None):
    """Measure fixed operation envelopes, never their source contents."""
    started = time.monotonic_ns()
    value, outcome, counters = None, 'rejected', None
    operation = args.get('operation') if type(args) is dict else None
    operation = operation if operation in OPERATIONS.get(name, ()) else None
    read_only = name == 'execution_status' or (name, operation) in {
        ('execution_prepare', 'preflight'), ('execution_lifecycle', 'product_check'),
        ('execution_lifecycle', 'intent_check'), ('execution_review', 'impact'),
        ('execution_qualification', 'check')}
    try:
        if read_only and hasattr(P, 'validation_operation'):
            with P.validation_operation(root) as scope:
                value = _call(root, name, args, runtime, host_context)
            counters = scope.counters()
        else:
            value = _call(root, name, args, runtime, host_context)
        outcome = 'returned'
        return value
    finally:
        if name in {*OPERATIONS, 'execution_status', 'execution_contract'} and (name, operation) != ('execution_efficiency', 'local_metrics'):
            # The observer contains only structural values. It cannot affect a
            # successful action or erase the original exception on failure.
            try:
                P.routing_helper('execution_observability').record(root, tool=name, operation=operation,
                    arguments=args, result=value, started_ns=started, outcome=outcome,
                    configuration=host_context or {'tool_profile': 'cli_execution', 'host_observed': False}, counters=counters)
            except (ValueError, OSError, TypeError, KeyError):
                pass


def _call(root, name, args, runtime=None, host_context=None):
    root, _ = P.load_project(root)
    if name == 'execution_status':
        P.need(type(args) is dict and set(args) <= {'request'}, 'Status accepts only a scoped request path')
        if not args:
            return status(root)
        request = P.read_json(P.relative_file(root, args['request']))[0]
        return P.routing_helper('selective_reads').status_view(root, request, lambda current_root: status(current_root))
    if name == 'execution_contract':
        P.need(type(args) is dict and set(args) == {'tool', 'operation'}, 'Tool and operation required')
        P.need(args['tool'] in OPERATIONS and args['operation'] in OPERATIONS[args['tool']], 'Unknown operation contract')
        return contract(args['tool'], args['operation'])
    P.need(name in OPERATIONS and type(args) is dict, 'Unknown execution tool')
    operation = args.get('operation')
    P.need(operation in OPERATIONS[name], 'Unknown execution operation')
    if name == 'execution_host':
        P.need(set(args) == {'operation', 'attempt_id'} and runtime is not None, 'Operator-configured worker adapter required')
        P.need(runtime.root == root, 'Runtime belongs to a different engagement')
        return getattr(runtime, operation)(args['attempt_id'])
    contracts = P.routing_helper('execution_contracts')
    contracts.validate_outer(name, operation, args)
    request = None
    if (name, operation) not in contracts.NO_REQUEST:
        request_path = P.relative_file(root, args['request'])
        try:
            request = P.read_json(request_path)[0]
        except (ValueError, UnicodeError):
            contracts.fail('invalid_json')
        contracts.validate(name, operation, request)
    if name == 'execution_prepare':
        if operation == 'recipe':
            return P.routing_helper('execution_preparation').prepare(root, request)
        if operation == 'context':
            return P.routing_helper('context_packets').build(root, request, args['output'])
        if operation == 'claim':
            return P.routing_helper('task_operations').claim(root, request)
        helper = P.routing_helper('execution_efficiency')
        return (helper.prepare if operation == 'work' else helper.preflight)(root, request)
    if name == 'execution_record':
        if operation in {'usage', 'blocker'}:
            helper = P.routing_helper('execution_efficiency')
            return (helper.record_usage if operation == 'usage' else helper.record_blocker)(root, request)
        helper = P.routing_helper('task_operations')
        return {'dispatch': helper.record_dispatch, 'checkpoint': helper.checkpoint, 'review': helper.review_work}[operation](root, request)
    if name == 'execution_lifecycle':
        if operation in {'entry_prepare', 'entry_check'}:
            helper = P.routing_helper('engagement_bootstrap')
            return (helper.prepare if operation == 'entry_prepare' else helper.check)(root, request)
        if operation == 'intent_check':
            return P.intent_helper().check(root)
        if operation == 'intent_select':
            P.need(type(request) is dict and set(request) == {'spec', 'output'}, 'Intent selection requires scoped spec and new output')
            return P.intent_helper().select(root, P.relative_file(root, request['spec']), request['output'])
        if operation == 'product_check':
            return P.routing_helper('product_intent').check(root)
        if operation == 'product_brief':
            P.need(type(request) is dict and set(request) == {'output'}, 'Product brief requires a new output path')
            return P.routing_helper('product_intent').generate(root, request['output'])
        if operation == 'stage':
            return P.stage_record(root, request)
        helper = P.routing_helper('delivery_workflow')
        if operation == 'phase':
            P.need(type(request) is dict and set(request) == {'action'}, 'Phase requires action only')
            return helper.phase_check(root, request['action'])
        return {'start': helper.start, 'guidance': helper.record_guidance, 'freeze': helper.freeze}[operation](root, request)
    if name == 'execution_review':
        helper = P.routing_helper('incremental_review')
        if operation == 'impact':
            P.stage_status(root)  # Register a fresh final observer for its direct journal reader.
        return helper.impact(root) if operation == 'impact' else {
            'policy': helper.adopt, 'carry': helper.carry_forward, 'manifest': helper.manifest_template}[operation](root, request)
    if name == 'execution_qualification':
        helper = P.routing_helper('execution_qualification')
        if operation == 'catalog':
            return helper.catalog()
        if operation == 'record':
            return helper.record(root, args['request'], args['output'])
        P.need(type(request) is dict and set(request) == {'report'}, 'Qualification check requires report path only')
        return helper.check(root, request['report'])
    if name == 'execution_efficiency':
        if operation == 'configuration':
            return configuration(root, runtime, host_context)
        if operation == 'local_metrics':
            return P.routing_helper('execution_observability').report(root)
        helper = P.routing_helper('execution_efficiency')
        return helper.report(root) if operation == 'report' else helper.configure(root, request)
    if name == 'execution_analysis' and operation == 'read':
        return P.routing_helper('selective_reads').artifact_read(root, request)
    helper = P.routing_helper('analytical_evidence' if name == 'execution_analysis' else 'assembly_provenance')
    return getattr(helper, operation)(root, request)


def contract(name, operation):
    description = P.routing_helper('execution_contracts').describe(name, operation)
    guide = {'execution_qualification': 'execution-qualification.md', 'execution_assembly': 'assembly-provenance.md',
             'execution_lifecycle': 'execution-workflow.md', 'execution_analysis': 'analytical-evidence.md',
             'execution_host': 'host-execution.md'}.get(name, 'incremental-work.md')
    return {'tool': name, 'operation': operation, **description,
            'reference': 'skills/omni-artifact-accelerator/references/' + guide,
            'note': 'Conditional fields remain validated by the operation; null means consult its scoped contract.',
            'publication_authorized': False}


def safe_error(name, args, error=None):
    """Do not echo raw exception text: it can contain source content or secrets."""
    operation = args.get('operation') if type(args) is dict else None
    if operation not in OPERATIONS.get(name, ()):
        operation = None
    repair = P.routing_helper('execution_contracts').diagnostic(name, operation, error)
    result = {'status': 'blocked', 'code': 'execution_request_rejected', 'tool': name if name in OPERATIONS else None,
            'operation': operation, 'next_action': 'Inspect execution_status and run execution_prepare/preflight with current pins; do not redispatch unchanged work.',
            'external_mutations_authorized': False, 'source_content_included': False}

    if repair:
        result.update(repair)
    return result


def configuration(root, runtime=None, host_context=None):
    root, project = P.load_project(root)
    host = host_context or {'tool_profile': 'cli_execution', 'tool_names': None}
    binding = runtime.binding if runtime is not None else None
    ledger = root / 'task-operations.json'
    attempts = P.read_json(ledger)[0].get('attempts', []) if ledger.exists() else []
    observed = []
    for attempt in reversed(attempts):
        dispatch = attempt.get('dispatch')
        if not dispatch:
            continue
        usage = attempt.get('usage_observation', {})
        launch = attempt.get('host_launch', {})
        observation = (launch.get('observations') or [{}])[-1]
        observed.append({'requested_model': dispatch.get('requested_model'), 'requested_effort': dispatch.get('requested_effort'),
                         'observed_model': dispatch.get('observed_model'), 'observed_effort': dispatch.get('observed_effort'),
                         'context_mode': observation.get('context_mode', usage.get('context_mode', 'unknown')),
                         'tool_scope': observation.get('tool_scope'), 'assurance': 'host_reported_not_authenticated'})
        if len(observed) == 16:
            break
    warnings = []
    if host.get('tool_profile') == 'legacy': warnings.append('compatibility_tool_profile')
    if project.get('context_policy', 'legacy-index-v1') != 'bounded-context-v1': warnings.append('compatibility_context_policy')
    if binding is None: warnings.append('worker_adapter_not_configured')
    if not observed: warnings.append('actual_host_behavior_unobserved')
    tools = host.get('tool_names')
    return {'kind': 'execution_effective_configuration', 'package': P.routing_helper('execution_observability').package_identity(),
            'context_policy': project.get('context_policy', 'legacy-index-v1'),
            'tool_profile': host.get('tool_profile'), 'tool_names': tools, 'tool_count': len(tools) if tools is not None else None,
            'configured_worker': binding, 'recent_observations': observed,
            'observations_omitted': max(0, sum(bool(a.get('dispatch')) for a in attempts) - len(observed)),
            'warnings': warnings, 'settings_changed': False, 'model_changed': False, 'cache_policy_changed': False,
            'host_isolation_verified': False, 'external_mutations_authorized': False}
