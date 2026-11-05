"""Shared outer request contracts and safe repair diagnostics; no source values."""
import copy

OPERATIONS = {
    'execution_prepare': ('work', 'context', 'preflight', 'claim', 'recipe'),
    'execution_record': ('dispatch', 'checkpoint', 'usage', 'blocker', 'review'),
    'execution_lifecycle': ('entry_prepare', 'entry_check', 'start', 'guidance', 'phase', 'stage', 'freeze', 'product_brief', 'product_check', 'intent_select', 'intent_check'),
    'execution_review': ('policy', 'impact', 'carry', 'manifest'),
    'execution_qualification': ('catalog', 'record', 'check'),
    'execution_assembly': ('build', 'verify', 'compare'),
    'execution_analysis': ('normalize', 'compare', 'read'),
    'execution_efficiency': ('configure', 'report', 'configuration', 'local_metrics'),
    'execution_host': ('status', 'launch', 'reconcile'),
}

# These are envelope contracts. Existing operation validators remain authoritative
# for nested fields, current evidence, selection, permissions and conditional rules.
FIELDS = {
    ('execution_lifecycle', 'entry_prepare'): (['schema_version', 'id', 'host', 'startup'], ['runtime_observation']),
    ('execution_lifecycle', 'entry_check'): (['record'], []),
    ('execution_prepare', 'work'): (['role', 'inputs', 'output', 'assignment'], []),
    ('execution_prepare', 'context'): (['schema_version', 'kind', 'packet', 'mode', 'summary', 'decisions', 'constraints',
        'stop_conditions', 'evidence', 'classification', 'disclosure', 'shared_constraint_ids'], ['max_packet_bytes', 'budget_reason', 'delta', 'layout']),
    ('execution_prepare', 'preflight'): ([], ['action', 'packet', 'attempt_id', 'context_receipt']),
    ('execution_prepare', 'claim'): (['attempt_id', 'packet'], ['execution_mode', 'context_receipt']),
    ('execution_prepare', 'recipe'): (['schema_version', 'idempotency_key', 'work', 'context', 'context_output', 'action', 'attempt_id'], ['execution_mode']),
    ('execution_record', 'dispatch'): (['attempt_id', 'host_run_reference', 'observed_model', 'observed_effort',
        'requested_model', 'requested_effort', 'execution_mode', 'fallback_reason'], []),
    ('execution_record', 'checkpoint'): (['attempt_id', 'status', 'reason', 'outputs'], []),
    ('execution_record', 'usage'): (['attempt_id', 'observation_id', 'host_run_reference', 'context_mode', 'evidence'],
        ['usage', 'elapsed_ms', 'host_instruction_bytes']),
    ('execution_record', 'blocker'): (['attempt_id', 'event_id', 'error_family', 'detail'], []),
    ('execution_record', 'review'): (['attempt_id', 'action'], ['changes', 'dependency_state', 'result', 'correction_attempt_id']),
    ('execution_lifecycle', 'phase'): (['action'], []),
    ('execution_lifecycle', 'product_brief'): (['output'], []),
    ('execution_lifecycle', 'intent_select'): (['spec', 'output'], []),
    ('execution_analysis', 'normalize'): (['source', 'layout', 'source_fields', 'bindings', 'output'], []),
    ('execution_analysis', 'compare'): (['comparison', 'provenance', 'output'], []),
    ('execution_efficiency', 'configure'): (['policy', 'reason'], []),
    ('execution_qualification', 'check'): (['report'], []),
    ('execution_assembly', 'build'): (['manifest', 'output', 'record'], []),
    ('execution_assembly', 'verify'): (['record'], []),
    ('execution_assembly', 'compare'): (['previous', 'current'], []),
}
NO_REQUEST = {('execution_review', 'impact'), ('execution_qualification', 'catalog'),
    ('execution_efficiency', 'report'), ('execution_efficiency', 'configuration'), ('execution_efficiency', 'local_metrics'),
    ('execution_lifecycle', 'product_check'), ('execution_lifecycle', 'intent_check')}
OUTPUT_REQUIRED = {('execution_prepare', 'context'), ('execution_qualification', 'record')}
LIST_FIELDS = {'inputs', 'decisions', 'constraints', 'stop_conditions', 'shared_constraint_ids', 'outputs', 'source_fields', 'bindings', 'changes'}
OBJECT_FIELDS = {'assignment', 'disclosure', 'work', 'context', 'usage', 'delta', 'comparison', 'provenance', 'host', 'startup', 'runtime_observation'}
INTEGER_FIELDS = {'schema_version', 'max_packet_bytes', 'elapsed_ms', 'host_instruction_bytes'}
NULLABLE = {'observed_model', 'observed_effort', 'requested_model', 'requested_effort', 'fallback_reason', 'usage', 'elapsed_ms', 'host_instruction_bytes', 'changes'}
FLEXIBLE = {'packet', 'source', 'evidence', 'result', 'record'}


def fail(code, field='request'):
    raise ValueError('execution.contract.' + code + '|' + field)


def describe(name, operation):
    spec = FIELDS.get((name, operation))
    required, optional = copy.deepcopy(spec) if spec else (None, [])
    outer = ['operation'] + ([] if (name, operation) in NO_REQUEST else ['attempt_id'] if name == 'execution_host' else ['request'])
    if (name, operation) in OUTPUT_REQUIRED:
        outer.append('output')
    template = None if required is None else {key: None for key in required}
    return {'argument_fields': outer, 'required_request_fields': required,
            'optional_request_fields': optional, 'request_template': template,
            'template_is_executable': False, 'nested_validation_required': True}


def validate_outer(name, operation, args):
    expected = set(describe(name, operation)['argument_fields'])
    if type(args) is not dict:
        fail('object_required')
    missing = expected - set(args)
    if missing:
        fail('missing_field', sorted(missing)[0])
    if set(args) - expected:
        fail('unexpected_fields')
    for key in expected:
        if type(args[key]) is not str or not args[key].strip():
            fail('string_required', key)


def validate(name, operation, value):
    spec = FIELDS.get((name, operation))
    if spec is None:
        return
    if type(value) is not dict:
        fail('object_required')
    required, optional = spec
    if set(required) - set(value):
        fail('missing_field', sorted(set(required) - set(value))[0])
    if set(value) - set(required) - set(optional):
        fail('unexpected_fields')
    for key, item in value.items():
        if item is None and key in NULLABLE:
            continue
        if key in FLEXIBLE:
            continue  # The same field has different nested shapes by operation.
        expected = list if key in LIST_FIELDS else dict if key in OBJECT_FIELDS else int if key in INTEGER_FIELDS else str
        if type(item) is not expected:
            fail({str: 'string_required', dict: 'object_required', list: 'array_required', int: 'integer_required'}[expected], key)


def diagnostic(name, operation, error):
    message = error.args[0] if error and error.args and type(error.args[0]) is str else ''
    remedies = {
        'stage_gate_experience_intent_required': ('experience_discovery', 'intent', 'Recover the actual task, promise and first/repeat-use outcome in canonical experience intent; then record the D checkpoint. See experience-continuity.md.'),
        'stage_gate_experience_intent_checkpoint_required': ('experience_checkpoint', 'intent', 'Record adopted experience intent at D in the same engagement; preserve the prior journal and actual decisions.'),
        'experience_contract.experience_concept_mode_changed_reopen_options': ('experience_options_stale', 'options', 'Reconcile changed mode meaning, prepare current options and retain the actual user selection against that option set.'),
        'experience_review.assigned_creative_reviewer_required': ('creative_review_binding', 'reviewer', 'Use the currently assigned independent creative reviewer and retain their actual comparison of the three pinned concepts.'),
        'experience_review.experience_findings_unresolved': ('experience_fit_pending', 'review', 'Keep gaps or unobserved outcomes open; correct the affected candidate and review the revised evidence.'),
        'entry.initialized_sibling_engagement_required': ('entry_location', 'project', 'Use the selected repository and an initialized sibling engagement; do not install skills or replace an existing project to bypass this route.'),
        'entry.source_expectation_not_satisfied': ('entry_source', 'source_expectation', 'Inspect the chosen checkout and existing source-check evidence; do not silently update or claim latest main.'),
        'Preparation identity or inputs changed; use a new version': ('preparation_stale', 'idempotency_key', 'Prepare a new version against the changed inputs; preserve the prior preparation.'),
        'Preparation inputs changed before reservation': ('inputs_changed', 'request', 'Refresh the changed evidence and prepare a new version before reserving work.'),
        'Bounded context receipt required before managed dispatch': ('context_required', 'context_receipt', 'Build the bounded context through execution_prepare/context or recipe.'),
        'Context receipt or pinned inputs changed; rebuild the bounded context': ('context_stale', 'context_receipt', 'Retain the old receipt and build a new one from current evidence.'),
        'Specialist concurrency limit reached': ('capacity_reached', 'attempt_id', 'Reuse or finish existing reserved work before creating another specialist.'),
        'context.packet_changed': ('packet_stale', 'packet', 'Prepare a new packet with current evidence bindings.'),
        'context.source_changed': ('source_stale', 'evidence', 'Retain the original and register the changed source before rebuilding context.'),
        'context.packet_exceeds_byte_budget_narrow_or_split_task': ('context_budget', 'evidence', 'Narrow or split coherent work; retain all required evidence and restrictions.'),
    }
    if message in remedies:
        code, field, action = remedies[message]
        return {'code': 'execution_' + code, 'field': field, 'expected': 'Current scoped evidence and existing workflow limits.', 'next_action': action}
    code, _, field = message.partition('|')
    known = {'missing_field', 'unexpected_fields', 'object_required', 'string_required', 'array_required', 'integer_required', 'invalid_json'}
    permitted_fields = {'request', 'operation', 'attempt_id', 'output'}
    spec = FIELDS.get((name, operation))
    if spec:
        permitted_fields.update(spec[0] + spec[1])
    short = code.removeprefix('execution.contract.')
    if not code.startswith('execution.contract.') or short not in known or field not in permitted_fields:
        return None
    return {'code': 'execution_' + short, 'field': field,
            'expected': {'missing_field': 'Provide this required field using the scoped contract.',
                         'unexpected_fields': 'Use only the fields declared by the scoped contract.',
                         'invalid_json': 'A valid bounded JSON request file.'}.get(short, short.removesuffix('_required')),
            'next_action': 'Correct this field, then rerun the same scoped request through its existing guards.'}
