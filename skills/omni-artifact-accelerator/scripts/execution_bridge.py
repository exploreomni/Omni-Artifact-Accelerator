"""Small, host-neutral tool surface over existing engagement functions.

Fixed operation names and project-relative JSON requests; no command, module or
credential selection. Native write capabilities remain with their guarded host.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('bridge_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

OPERATIONS = {
    'execution_prepare': ('work', 'context', 'preflight', 'claim'),
    'execution_record': ('dispatch', 'checkpoint', 'usage', 'blocker', 'review'),
    'execution_lifecycle': ('start', 'guidance', 'phase', 'stage', 'freeze', 'product_brief', 'product_check', 'intent_select', 'intent_check'),
    'execution_review': ('policy', 'impact', 'carry', 'manifest'),
    'execution_qualification': ('catalog', 'record', 'check'),
    'execution_assembly': ('build', 'verify', 'compare'),
    'execution_analysis': ('normalize', 'compare'),
    'execution_efficiency': ('configure', 'report'),
    'execution_host': ('status', 'launch', 'reconcile'),
}


def definitions(tool, string, runtime=None):
    values = [tool('execution_status', 'Read current gates and compact task progress; no invocation or authorization.', {}, read=True)]
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
                'tail_sha256', 'candidate_sha256', 'release_ready', 'choice_assurance', 'review_assurance')},
            'blockers': [{'area': 'stage', 'code': value} for value in gates.get('findings', [])],
            'next_action': {'stage': next_stage, 'tool': 'execution_lifecycle' if next_stage else 'execution_qualification',
                            'requires_current_preflight': True},
            'tasks': tasks['tasks'], 'external_mutations_authorized': False,
            'choice_bindings': gates.get('choice_bindings', {}),
            'qualification': 'Readiness and reported progress only; the actual host owns execution and permission.'}


def call(root, name, args, runtime=None):
    root, _ = P.load_project(root)
    if name == 'execution_status':
        P.need(args == {}, 'Status accepts no fields')
        return status(root)
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
    no_request = (name, operation) in {('execution_review', 'impact'), ('execution_qualification', 'catalog'), ('execution_efficiency', 'report'), ('execution_lifecycle', 'product_check'), ('execution_lifecycle', 'intent_check')}
    output_required = (name, operation) in {('execution_prepare', 'context'), ('execution_qualification', 'record')}
    expected = {'operation'} | (set() if no_request else {'request'}) | ({'output'} if output_required else set())
    P.need(set(args) == expected, 'Operation fields differ; use operation plus project-relative request and required output only')
    request = None if no_request else P.read_json(P.relative_file(root, args['request']))[0]
    if name == 'execution_prepare':
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
        helper = P.routing_helper('execution_efficiency')
        return helper.report(root) if operation == 'report' else helper.configure(root, request)
    helper = P.routing_helper('analytical_evidence' if name == 'execution_analysis' else 'assembly_provenance')
    return getattr(helper, operation)(root, request)


def contract(name, operation):
    fields = {
        ('execution_prepare', 'work'): ['role', 'inputs', 'output', 'assignment'],
        ('execution_prepare', 'context'): ['schema_version', 'kind', 'packet', 'mode', 'summary', 'decisions', 'constraints',
            'stop_conditions', 'evidence', 'classification', 'disclosure', 'shared_constraint_ids'],
        ('execution_prepare', 'preflight'): [],
        ('execution_prepare', 'claim'): ['attempt_id', 'packet'],
        ('execution_record', 'dispatch'): ['attempt_id', 'host_run_reference', 'observed_model', 'observed_effort',
            'requested_model', 'requested_effort', 'execution_mode', 'fallback_reason'],
        ('execution_record', 'checkpoint'): ['attempt_id', 'status', 'reason', 'outputs'],
        ('execution_record', 'usage'): ['attempt_id', 'observation_id', 'host_run_reference', 'context_mode', 'evidence'],
        ('execution_record', 'blocker'): ['attempt_id', 'event_id', 'error_family', 'detail'],
        ('execution_record', 'review'): ['attempt_id', 'action'],
        ('execution_lifecycle', 'phase'): ['action'],
        ('execution_lifecycle', 'product_brief'): ['output'],
        ('execution_lifecycle', 'intent_select'): ['spec', 'output'],
        ('execution_analysis', 'normalize'): ['source', 'layout', 'source_fields', 'bindings', 'output'],
        ('execution_analysis', 'compare'): ['comparison', 'provenance', 'output'],
        ('execution_efficiency', 'configure'): ['policy', 'reason'],
        ('execution_qualification', 'check'): ['report'],
        ('execution_assembly', 'build'): ['manifest', 'output', 'record'],
        ('execution_assembly', 'verify'): ['record'],
        ('execution_assembly', 'compare'): ['previous', 'current'],
    }
    optional = {
        ('execution_prepare', 'preflight'): ['action', 'packet', 'attempt_id', 'context_receipt'],
        ('execution_prepare', 'claim'): ['execution_mode', 'context_receipt'],
        ('execution_prepare', 'context'): ['max_packet_bytes', 'budget_reason', 'delta'],
        ('execution_record', 'usage'): ['usage', 'elapsed_ms', 'host_instruction_bytes'],
        ('execution_record', 'review'): ['changes', 'dependency_state', 'result', 'correction_attempt_id'],
    }
    guide = {'execution_qualification': 'execution-qualification.md', 'execution_assembly': 'assembly-provenance.md',
             'execution_lifecycle': 'execution-workflow.md', 'execution_analysis': 'analytical-evidence.md',
             'execution_host': 'host-execution.md'}.get(name, 'incremental-work.md')
    no_request = (name, operation) in {('execution_review', 'impact'), ('execution_qualification', 'catalog'), ('execution_efficiency', 'report'), ('execution_lifecycle', 'product_check'), ('execution_lifecycle', 'intent_check')}
    outer = ['operation'] + ([] if no_request else ['attempt_id'] if name == 'execution_host' else ['request'])
    if (name, operation) in {('execution_prepare', 'context'), ('execution_qualification', 'record')}:
        outer.append('output')
    return {'tool': name, 'operation': operation, 'argument_fields': outer,
            'required_request_fields': fields.get((name, operation)), 'optional_request_fields': optional.get((name, operation), []),
            'reference': 'skills/omni-artifact-accelerator/references/' + guide,
            'note': 'Conditional fields and evidence requirements remain validated by the existing operation; null means consult its scoped contract.',
            'publication_authorized': False}


def safe_error(name, args):
    """Do not echo raw exception text: it can contain source content or secrets."""
    operation = args.get('operation') if type(args) is dict else None
    if operation not in OPERATIONS.get(name, ()):
        operation = None
    return {'status': 'blocked', 'code': 'execution_request_rejected', 'tool': name if name in OPERATIONS else None,
            'operation': operation, 'next_action': 'Inspect execution_status and run execution_prepare/preflight with current pins; do not redispatch unchanged work.',
            'external_mutations_authorized': False, 'source_content_included': False}
