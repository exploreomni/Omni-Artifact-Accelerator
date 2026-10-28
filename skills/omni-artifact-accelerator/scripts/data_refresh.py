"""App refresh decisions over canonical intent; no query, timer or cache mutation."""
import copy


def need(ok, message):
    if not ok:
        raise ValueError('data_refresh.' + message)


def text(value):
    return type(value) is str and 0 < len(value.strip()) <= 8192


def metadata(spec):
    return spec.get('product', {}).get('data_refresh')


def policy(value):
    """Normalize selected meaning for handoffs, never provider API arguments."""
    need(type(value) is dict and value.get('kind') == 'app_data_refresh', 'policy_required')
    mode = value.get('mode')
    if mode == 'not_applicable':
        need(set(value) == {'kind', 'mode', 'rationale'} and text(value['rationale']), 'applicability_reason_required')
        return copy.deepcopy(value)
    if mode == 'no_custom_policy':
        need(set(value) == {'kind', 'mode'}, 'no_custom_policy_has_overrides')
        return {'query_cache': 'inherit', 'refresh_mode': 'manual', 'interval_ms': None,
                'return_after_ms': None, 'max_age_ms': None, 'hidden_behavior': 'pause',
                'stale_display': 'timestamp', 'recovery': 'Manual retry; clear denied or changed-scope results.'}
    need(mode == 'custom', 'unknown_policy_mode')
    fields = {'kind', 'mode', 'query_cache', 'refresh_mode', 'interval_ms', 'return_after_ms',
              'max_age_ms', 'hidden_behavior', 'stale_display', 'recovery'}
    need(set(value) == fields, 'custom_policy_fields_invalid')
    need(value['query_cache'] in ('inherit', 'bypass'), 'query_cache_mode_invalid')
    need(value['refresh_mode'] in ('manual', 'on_return', 'interval', 'interval_and_return'), 'refresh_mode_invalid')
    need(value['hidden_behavior'] in ('pause', 'continue'), 'hidden_behavior_invalid')
    need(value['stale_display'] in ('timestamp', 'label', 'withhold') and text(value['recovery']), 'recovery_required')
    for field in ('interval_ms', 'return_after_ms', 'max_age_ms'):
        amount = value[field]
        need(amount is None or (type(amount) is int and 0 < amount <= 9007199254740991), 'invalid_' + field)
    interval = value['refresh_mode'] in ('interval', 'interval_and_return')
    returning = value['refresh_mode'] in ('on_return', 'interval_and_return')
    need((value['interval_ms'] is not None) == interval, 'interval_requires_selected_trigger')
    need((value['return_after_ms'] is not None) == returning, 'return_threshold_requires_selected_trigger')
    need(value['hidden_behavior'] != 'continue' or interval, 'hidden_polling_requires_interval')
    need(value['max_age_ms'] is not None or value['stale_display'] != 'withhold', 'withholding_requires_expiry')
    need(value['max_age_ms'] is None or value['stale_display'] != 'timestamp', 'expiry_requires_visible_stale_state')
    return {k: copy.deepcopy(value[k]) for k in fields - {'kind', 'mode'}}


def validate(spec):
    meta = metadata(spec)
    if meta is None:
        return
    need('app' in spec.get('surfaces', []), 'app_surface_required')
    need(type(meta) is dict and {'schema_version', 'requirement_id'} <= set(meta)
         and set(meta) <= {'schema_version', 'requirement_id', 'delegation_requirement_id'}, 'index_fields_invalid')
    need(type(meta['schema_version']) is int and meta['schema_version'] == 1, 'version_invalid')
    ids = [meta['requirement_id']]
    if 'delegation_requirement_id' in meta:
        ids.append(meta['delegation_requirement_id'])
    need(all(text(i) for i in ids) and len(set(ids)) == len(ids), 'requirement_ids_invalid')
    rows = {r['id']: r for r in spec['requirements']}
    need(set(ids) <= set(rows), 'requirement_missing')
    notes = spec['product']['note_paths']
    for ident in ids:
        req = rows[ident]
        need(req.get('category') == 'interaction' and req.get('required') is True
             and req.get('surfaces') == ['app'], 'required_app_interaction_expected')
        attr = req.get('product', {})
        refs = attr.get('source_refs')
        need(type(refs) is list and refs and all(text(r) and r.split('#', 1)[0] in notes for r in refs), 'source_notes_required')
        need(attr.get('acceptance') and type(attr['acceptance']) is list
             and all(text(a) for a in attr['acceptance']), 'acceptance_required')
        bases = {'user_statement': 'user', 'reused_decision': 'reused', 'recommendation': 'proposal',
                 'inference': 'proposal', 'unresolved': 'proposal'}
        need(attr.get('basis') in bases and req.get('origin') == bases[attr['basis']], 'attribution_invalid')
        need(req.get('disposition') in ('selected', 'unresolved', 'deferred'), 'decision_state_invalid')
        if req['disposition'] == 'selected':
            need(req.get('decision_ref') in refs, 'decision_source_required')
    main = rows[meta['requirement_id']]
    if main.get('value') is not None:
        policy(main['value'])
    if main['disposition'] == 'selected':
        need(main.get('value') is not None, 'selected_policy_required')
    delegate = meta.get('delegation_requirement_id')
    if delegate:
        req = rows[delegate]
        need(req['disposition'] == 'selected' and req['product']['basis'] in ('user_statement', 'reused_decision')
             and req.get('value') == {'delegation_scope': 'app_data_refresh'}, 'scoped_delegation_required')
    for req in spec['requirements']:
        value = req.get('value')
        if type(value) is dict and value.get('kind') == 'app_data_refresh':
            need(req['id'] == meta['requirement_id'], 'unindexed_policy')


def context(spec):
    validate(spec)
    meta = metadata(spec)
    if meta is None:
        return None
    ids = {meta['requirement_id']}
    if meta.get('delegation_requirement_id'):
        ids.add(meta['delegation_requirement_id'])
    fields = ('id', 'category', 'purpose', 'value', 'surfaces', 'required', 'origin', 'disposition', 'decision_ref')
    attr = ('priority', 'basis', 'source_refs', 'acceptance', 'alternative')
    rows = []
    for req in sorted(spec['requirements'], key=lambda r: r['id']):
        if req['id'] in ids:
            row = {k: copy.deepcopy(req[k]) for k in fields if k in req}
            row['product'] = {k: copy.deepcopy(req['product'][k]) for k in attr if k in req['product']}
            rows.append(row)
    return {'metadata': copy.deepcopy(meta), 'requirements': rows}


def report(spec):
    ctx = context(spec)
    if ctx is None:
        return {'status': 'not_assessed', 'requirement_id': None, 'policy': None, 'findings': []}
    meta = metadata(spec)
    req = next(r for r in ctx['requirements'] if r['id'] == meta['requirement_id'])
    result = {'status': 'unresolved', 'requirement_id': req['id'], 'policy': None, 'findings': []}
    basis = req['product']['basis']
    if req['disposition'] != 'selected' or basis == 'unresolved':
        result['findings'].append({'code': 'data_refresh_answer_required'})
    elif basis in ('user_statement', 'reused_decision') or meta.get('delegation_requirement_id'):
        result.update(status='not_applicable' if req['value']['mode'] == 'not_applicable' else 'ready',
                      policy=policy(req['value']))
    else:
        result['findings'].append({'code': 'data_refresh_actual_answer_or_delegation_required'})
    return result


def validate_transition(previous, current):
    old = metadata(previous)
    if old is not None:
        new = metadata(current)
        need(new is not None, 'adopted_policy_removed')
        need(new['requirement_id'] == old['requirement_id'], 'adopted_requirement_replaced')
    validate(current)


def validate_handoff(design, spec):
    """Bind design to the exact interview meaning and its QA obligations."""
    ctx = context(spec)
    if ctx is None:
        return  # Historical selected designs stay readable.
    decision = report(spec)
    need(decision['status'] in ('ready', 'not_applicable'), 'handoff_policy_unresolved')
    value = design.get('data_refresh_handoff')
    need(type(value) is dict and set(value) == {'context', 'implementation', 'qa_cases'}, 'design_handoff_required')
    need(value['context'] == ctx, 'design_policy_changed')
    need(text(value['implementation']), 'implementation_behavior_required')
    need(type(value['qa_cases']) is list and value['qa_cases'] and all(text(c) for c in value['qa_cases']), 'qa_cases_required')
