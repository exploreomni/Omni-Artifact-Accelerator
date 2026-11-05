"""Experience promises over canonical intent; no approval or aesthetic certification.

Discovery preserves sourced outcomes. Creative modes may remain hypotheses until
the existing concept choice. Detailed behavior lives on the canonical journeys.
"""
import copy
import json
from pathlib import PurePosixPath

MODES = {'workspace', 'narrative', 'monitoring', 'guided_workflow', 'branded_entry', 'custom', 'hybrid'}
BASES = {'user_statement': 'user', 'reused_decision': 'reused', 'recommendation': 'proposal',
         'inference': 'proposal', 'unresolved': 'proposal'}
SOURCED = {'user_statement', 'reused_decision'}
MAX_CONTEXT_BYTES = 64 * 1024
MAX_BEHAVIOR_BYTES = 64 * 1024


def need(ok, message):
    if not ok:
        raise ValueError('experience_intent.' + message)


def text(value, limit=2048):
    return type(value) is str and 0 < len(value.strip()) <= limit


def fields(value, required, optional=(), label='fields'):
    need(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional), label + '_invalid')


def strings(value, label, *, empty=False, limit=32):
    need(type(value) is list and (empty or bool(value)) and len(value) <= limit
         and all(text(v, 128) for v in value) and len(set(value)) == len(value), label + '_invalid')


def bounded(value, maximum, label):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('experience_intent.' + label + '_invalid') from exc
    need(len(raw) <= maximum, label + '_exceeds_bound')


def relative(value):
    need(text(value) and '\\' not in value, 'path_invalid')
    path = PurePosixPath(value)
    need(not path.is_absolute() and '..' not in path.parts and path.parts
         and value != '.' and path.as_posix() == value, 'path_invalid')
    return value


def metadata(spec):
    need(type(spec) is dict, 'intent_required')
    product = spec.get('product', {})
    if type(product) is not dict or 'experience_intent' not in product:
        return None
    need(type(product['experience_intent']) is dict, 'index_invalid')
    return product['experience_intent']


def attribution(req, notes, *, sourced=False):
    attr = req.get('product')
    need(type(attr) is dict and type(attr.get('basis')) is str and attr['basis'] in BASES
         and req.get('origin') == BASES[attr['basis']], 'attribution_invalid')
    refs = attr.get('source_refs')
    need(type(refs) is list and 0 < len(refs) <= 16 and all(text(r) and r.split('#', 1)[0] in notes for r in refs)
         and len(set(refs)) == len(refs), 'source_notes_required')
    acceptance = attr.get('acceptance')
    need(type(acceptance) is list and 0 < len(acceptance) <= 16 and all(text(v) for v in acceptance),
         'observable_acceptance_required')
    need(req.get('disposition') in {'selected', 'unresolved', 'deferred', 'explicitly_omitted'}, 'disposition_invalid')
    if req['disposition'] in {'selected', 'explicitly_omitted'}:
        need(req.get('decision_ref') in refs, 'decision_source_required')
    if sourced or req['disposition'] == 'explicitly_omitted':
        need(attr['basis'] in SOURCED, 'actual_source_required')


def mode(value):
    need(type(value) is dict and value.get('kind') == 'experience_mode'
         and type(value.get('mode')) is str and value['mode'] in MODES, 'mode_invalid')
    extra = {'custom_label'} if value['mode'] == 'custom' else {'components'} if value['mode'] == 'hybrid' else set()
    fields(value, {'kind', 'mode', 'rationale'} | extra, label='mode_fields')
    need(text(value['rationale']), 'mode_rationale_required')
    if 'custom_label' in extra:
        need(text(value['custom_label'], 128), 'custom_mode_label_required')
    if 'components' in extra:
        strings(value['components'], 'hybrid_components', limit=8)
        need(len(value['components']) >= 2, 'hybrid_components_required')


def _rows(spec):
    rows = spec.get('requirements')
    need(type(rows) is list and all(type(r) is dict and text(r.get('id'), 128) for r in rows), 'requirements_invalid')
    by_id = {r['id']: r for r in rows}
    need(len(by_id) == len(rows), 'duplicate_requirement_id')
    return by_id


def validate(spec):
    """Validate an additive index; historical specs without it remain readable."""
    meta = metadata(spec)
    if meta is None:
        return
    fields(meta, {'schema_version', 'requirement_ids', 'mode_requirement_ids'}, {'delegation_requirement_id'}, 'index')
    need(type(meta['schema_version']) is int and meta['schema_version'] == 1, 'version_invalid')
    strings(meta['requirement_ids'], 'promise_ids', limit=16)
    strings(meta['mode_requirement_ids'], 'mode_ids', empty=True, limit=16)
    ids = meta['requirement_ids'] + meta['mode_requirement_ids']
    if 'delegation_requirement_id' in meta:
        need(text(meta['delegation_requirement_id'], 128), 'delegation_id_invalid')
        ids.append(meta['delegation_requirement_id'])
    need(len(set(ids)) == len(ids), 'index_roles_overlap')
    rows = _rows(spec)
    need(set(ids) <= set(rows), 'dangling_requirement_reference')
    notes = spec['product'].get('note_paths')
    need(type(notes) is list and 0 < len(notes) <= 32 and all(text(p) for p in notes), 'notes_required')
    for path in notes:
        relative(path)
        need(path.startswith(('inputs/', 'evidence/')), 'private_notes_required')
    surfaces = spec.get('surfaces')
    strings(surfaces, 'surfaces', limit=3)
    need(set(surfaces) <= {'app', 'dashboard', 'report'}, 'surface_invalid')
    for ident in ids:
        req = rows[ident]
        attribution(req, notes)
        strings(req.get('surfaces'), 'requirement_surfaces', limit=3)
        need(set(req['surfaces']) <= set(surfaces) and type(req.get('required')) is bool
             and text(req.get('purpose')), 'requirement_definition_invalid')
    for ident in meta['requirement_ids']:
        req, value = rows[ident], rows[ident].get('value')
        need(req['required'], 'promise_must_remain_required')
        if value is None and req['disposition'] in {'unresolved', 'deferred', 'explicitly_omitted'}:
            continue
        keys = {'kind', 'user_task', 'promise', 'primary_action', 'success', 'first_use', 'repeat_use'}
        fields(value, keys, label='promise')
        need(value['kind'] == 'experience_promise' and all(text(value[k]) for k in keys - {'kind'}), 'promise_meaning_required')
    for ident in meta['mode_requirement_ids']:
        req = rows[ident]
        if req.get('value') is None and req['disposition'] in {'unresolved', 'deferred', 'explicitly_omitted'}:
            continue
        mode(req.get('value'))
    delegate = meta.get('delegation_requirement_id')
    if delegate:
        req = rows[delegate]
        attribution(req, notes, sourced=True)
        need(req['disposition'] == 'selected' and req.get('value') == {'delegation_scope': 'experience_direction'},
             'scoped_delegation_required')
        proposals = [rows[i] for i in meta['requirement_ids'] if rows[i]['origin'] == 'proposal'
                     and rows[i]['disposition'] != 'explicitly_omitted']
        need({s for r in proposals for s in r['surfaces']} <= set(req['surfaces']), 'delegation_surface_missing')
    # Recognized meanings cannot disappear by omitting their index entry.
    for req in rows.values():
        value = req.get('value')
        recognized = type(value) is dict and value.get('kind') in {'experience_promise', 'experience_mode'}
        if recognized and req['id'] not in ids:
            need(req.get('disposition') == 'explicitly_omitted', 'unindexed_experience_requirement')
            attribution(req, notes, sourced=True)
    bounded([meta, [rows[i] for i in ids]], MAX_CONTEXT_BYTES, 'indexed_requirements')


def _projection(req):
    result = {k: copy.deepcopy(req[k]) for k in
              ('id', 'category', 'purpose', 'value', 'surfaces', 'required', 'origin', 'disposition', 'decision_ref') if k in req}
    result['product'] = {k: copy.deepcopy(req['product'][k]) for k in
                         ('priority', 'basis', 'source_refs', 'acceptance', 'alternative') if k in req['product']}
    return result


def context(spec):
    """Stable D meaning, excluding creative hypotheses and later delivery details."""
    validate(spec)
    meta = metadata(spec)
    if meta is None:
        return None
    rows = _rows(spec)
    constraints = [i for i in meta['mode_requirement_ids'] if rows[i]['product']['basis'] in SOURCED]
    ids = list(meta['requirement_ids']) + constraints
    delegate = meta.get('delegation_requirement_id')
    if delegate:
        ids.append(delegate)
    index = {'schema_version': 1, 'requirement_ids': sorted(meta['requirement_ids']), 'mode_constraint_ids': sorted(constraints)}
    if delegate:
        index['delegation_requirement_id'] = delegate
    return {'metadata': index, 'surfaces': sorted(spec['surfaces']),
            'requirements': [_projection(rows[i]) for i in sorted(ids)]}


def report(spec):
    ctx = context(spec)
    result = {'status': 'not_assessed', 'requirement_ids': [], 'mode_constraint_ids': [],
              'creative_hypothesis_ids': [], 'findings': [], 'concept_selected': False,
              'claims_authenticated': False, 'execution_authorized': False}
    if ctx is None:
        return result
    meta, rows = metadata(spec), _rows(spec)
    result.update(requirement_ids=sorted(meta['requirement_ids']), mode_constraint_ids=ctx['metadata']['mode_constraint_ids'],
                  creative_hypothesis_ids=sorted(set(meta['mode_requirement_ids']) - set(ctx['metadata']['mode_constraint_ids'])))
    covered = set()
    for ident in meta['requirement_ids']:
        req = rows[ident]
        if req['disposition'] == 'explicitly_omitted':
            continue
        if req['disposition'] != 'selected' or req['product']['basis'] == 'unresolved':
            result['findings'].append({'code': 'experience_promise_unresolved', 'requirement_id': ident})
        elif req['product']['basis'] not in SOURCED and not meta.get('delegation_requirement_id'):
            result['findings'].append({'code': 'experience_promise_source_or_delegation_required', 'requirement_id': ident})
        else:
            covered.update(req['surfaces'])
    for ident in result['mode_constraint_ids']:
        if rows[ident]['disposition'] in {'unresolved', 'deferred'}:
            result['findings'].append({'code': 'sourced_mode_constraint_unresolved', 'requirement_id': ident})
    for surface in spec['surfaces']:
        constraints = [i for i in result['mode_constraint_ids']
                       if rows[i]['disposition'] == 'selected' and surface in rows[i]['surfaces']]
        if len(constraints) > 1:
            result['findings'].append({'code': 'experience_mode_constraints_conflict', 'surface': surface})
    for surface in sorted(set(spec['surfaces']) - covered):
        result['findings'].append({'code': 'experience_surface_promise_missing', 'surface': surface})
    result['status'] = 'unresolved' if result['findings'] else 'ready'
    return result


def validate_transition(previous, current):
    validate(previous)
    validate(current)
    old = metadata(previous)
    if old is None:
        return
    new = metadata(current)
    need(new is not None, 'adopted_context_removed')
    old_rows, rows = _rows(previous), _rows(current)
    for key in ('requirement_ids', 'mode_requirement_ids'):
        for ident in old[key]:
            need(ident in rows, 'adopted_requirement_removed')
            if ident not in new[key]:
                need(rows[ident]['disposition'] == 'explicitly_omitted', 'index_removed_use_explicit_omission')
                attribution(rows[ident], current['product']['note_paths'], sourced=True)
            if old_rows[ident]['product']['basis'] in SOURCED and old_rows[ident]['disposition'] == 'selected':
                need(rows[ident]['product']['basis'] in SOURCED, 'sourced_promise_replaced_by_proposal')
    delegate = old.get('delegation_requirement_id')
    if delegate and new.get('delegation_requirement_id') != delegate:
        need(delegate in rows and rows[delegate]['disposition'] == 'explicitly_omitted', 'delegation_removed_use_explicit_omission')
        attribution(rows[delegate], current['product']['note_paths'], sourced=True)


def _state(value, destinations, evidence_ids):
    fields(value, {'destination_id', 'state', 'evidence_ids'}, label='state')
    need(type(value['destination_id']) is str and value['destination_id'] in destinations and text(value['state']),
         'state_destination_invalid')
    strings(value['evidence_ids'], 'state_evidence_ids', empty=True)
    need(set(value['evidence_ids']) <= evidence_ids, 'state_evidence_unknown')
    return value['destination_id'], value['state'], frozenset(value['evidence_ids'])


def validate_modes(spec, selected_mode_ids):
    """Use the same viable mode set before presentation and after actual choice."""
    ctx = context(spec)
    need(ctx is not None, 'mode_context_required')
    strings(selected_mode_ids, 'selected_mode_ids', limit=16)
    meta, rows = metadata(spec), _rows(spec)
    chosen = set(selected_mode_ids)
    need(chosen <= set(meta['mode_requirement_ids']), 'chosen_mode_unknown')
    sourced = {i for i in ctx['metadata']['mode_constraint_ids'] if rows[i]['disposition'] == 'selected'}
    need(sourced <= chosen, 'sourced_mode_constraint_dropped')
    for ident in chosen:
        req = rows[ident]
        need(req['disposition'] in {'selected', 'unresolved'} and req.get('value') is not None,
             'chosen_mode_unavailable')
        need(req['product']['basis'] != 'unresolved', 'chosen_mode_meaning_unresolved')
        mode(req['value'])
    for surface in spec['surfaces']:
        need(sum(surface in rows[i]['surfaces'] for i in chosen) == 1, 'one_chosen_mode_per_surface_required')
    return chosen


def validate_handoff(design, spec):
    """Check promised behavior bindings; the caller binds actual E choice and pins."""
    ctx = context(spec)
    if ctx is None:
        return {'status': 'not_assessed', 'claims_authenticated': False}
    need(report(spec)['status'] == 'ready', 'handoff_promise_unresolved')
    need(type(design) is dict, 'design_required')
    handoff = design.get('experience_intent_handoff')
    fields(handoff, {'schema_version', 'context', 'selected_mode_ids', 'journey_ids'}, label='handoff')
    need(type(handoff['schema_version']) is int and handoff['schema_version'] == 1, 'handoff_version_invalid')
    need(handoff['context'] == ctx, 'handoff_context_changed')
    strings(handoff['selected_mode_ids'], 'selected_mode_ids', limit=16)
    strings(handoff['journey_ids'], 'handoff_journey_ids', limit=32)
    meta, rows = metadata(spec), _rows(spec)
    chosen = validate_modes(spec, handoff['selected_mode_ids'])
    destinations = design.get('destinations')
    journeys = design.get('journeys')
    need(type(destinations) is list and 0 < len(destinations) <= 32 and
         all(type(d) is dict and text(d.get('id'), 128) for d in destinations), 'destinations_required')
    need(type(journeys) is list and 0 < len(journeys) <= 64 and
         all(type(j) is dict and text(j.get('id'), 128) for j in journeys), 'journeys_required')
    dests, by_journey = {d['id']: d for d in destinations}, {j['id']: j for j in journeys}
    need(len(dests) == len(destinations) and len(by_journey) == len(journeys), 'duplicate_design_identity')
    need(set(handoff['journey_ids']) <= set(by_journey), 'handoff_journey_unknown')
    promises = [rows[i] for i in meta['requirement_ids'] if rows[i]['disposition'] != 'explicitly_omitted']
    covered_surfaces = {r['id']: set() for r in promises}
    linked = {}
    for req in promises:
        delivery = req.get('delivery', {})
        strings(delivery.get('journeys'), 'promise_journeys')
        need(set(delivery['journeys']) <= set(handoff['journey_ids']), 'promise_journey_not_in_handoff')
        for ident in delivery['journeys']:
            linked.setdefault(ident, []).append(req)
    need(set(linked) == set(handoff['journey_ids']), 'handoff_journey_without_promise')
    for ident in handoff['journey_ids']:
        journey, requirements = by_journey[ident], linked[ident]
        behavior = journey.get('experience_behavior')
        keys = {'kind', 'trigger', 'before', 'after', 'useful_change', 'evidence', 'governed_bindings',
                'context_preservation', 'return', 'recovery'}
        fields(behavior, keys, {'single_view_rationale'}, 'behavior')
        bounded(behavior, MAX_BEHAVIOR_BYTES, 'behavior')
        need(behavior['kind'] in {'transition', 'single_view'}, 'behavior_kind_invalid')
        fields(behavior['trigger'], {'control_id', 'action'}, label='trigger')
        trigger = behavior['trigger']
        need(text(trigger['action']) and all(trigger['action'] == r['value']['primary_action'] for r in requirements),
             'trigger_must_match_promised_action')
        need(journey.get('action') == trigger['action'], 'canonical_journey_action_mismatch')
        for key in ('useful_change', 'context_preservation'):
            need(text(behavior[key]), 'behavior_' + key + '_required')
        evidence, bindings = behavior['evidence'], behavior['governed_bindings']
        need(type(evidence) is list and 0 < len(evidence) <= 32 and type(bindings) is list and 0 < len(bindings) <= 32,
             'evidence_and_governed_bindings_required')
        binding_ids, evidence_ids = set(), set()
        dependencies = {p for r in requirements for p in r.get('delivery', {}).get('dependency_paths', [])}
        for binding in bindings:
            fields(binding, {'id', 'path', 'reference'}, label='governed_binding')
            need(text(binding['id'], 128) and binding['id'] not in binding_ids and text(binding['reference']), 'binding_identity_invalid')
            need(relative(binding['path']) in dependencies, 'binding_path_must_be_explicit_dependency')
            binding_ids.add(binding['id'])
        used = set()
        for item in evidence:
            fields(item, {'id', 'binding_ids', 'meaning'}, label='evidence')
            need(text(item['id'], 128) and item['id'] not in evidence_ids and text(item['meaning']), 'evidence_identity_invalid')
            strings(item['binding_ids'], 'evidence_binding_ids')
            need(set(item['binding_ids']) <= binding_ids, 'evidence_binding_unknown')
            used.update(item['binding_ids'])
            evidence_ids.add(item['id'])
        need(used == binding_ids, 'unused_governed_binding')
        before = _state(behavior['before'], dests, evidence_ids)
        after = _state(behavior['after'], dests, evidence_ids)
        need(behavior['after']['evidence_ids'], 'after_evidence_required')
        destinations_used = {behavior['before']['destination_id'], behavior['after']['destination_id']}
        declared_destinations = journey.get('destination_ids')
        strings(declared_destinations, 'journey_destination_ids')
        need(destinations_used <= set(declared_destinations) <= set(dests), 'journey_destination_binding_invalid')
        for dest in declared_destinations:
            surface = dests[dest].get('surface', spec['surfaces'][0] if len(spec['surfaces']) == 1 else None)
            need(surface in spec['surfaces'] and all(surface in r['surfaces'] for r in requirements), 'journey_surface_binding_invalid')
            for req in requirements:
                covered_surfaces[req['id']].add(surface)
        fields(behavior['return'], {'destination_id', 'control_id', 'state'}, label='return')
        returning = behavior['return']
        need(returning['destination_id'] in declared_destinations and text(returning['state']) and
             (returning['control_id'] is None or text(returning['control_id'], 128)), 'return_binding_invalid')
        fields(behavior['recovery'], {'empty', 'error'}, label='recovery')
        need(all(text(v) for v in behavior['recovery'].values()), 'recovery_behavior_required')
        if behavior['kind'] == 'transition':
            need(text(trigger['control_id'], 128) and before != after
                 and 'single_view_rationale' not in behavior, 'transition_must_change_state')
            if returning['destination_id'] != behavior['after']['destination_id']:
                need(text(returning['control_id'], 128), 'return_control_required')
        else:
            need(trigger['control_id'] is None and before == after and
                 text(behavior.get('single_view_rationale')) and returning['control_id'] is None
                 and returning['destination_id'] == behavior['before']['destination_id']
                 and returning['state'] == behavior['before']['state'], 'single_view_case_invalid')
    need(all(covered_surfaces[r['id']] == set(r['surfaces']) for r in promises), 'promise_journey_surface_missing')
    return {'status': 'consistent', 'requirement_ids': sorted(r['id'] for r in promises),
            'selected_mode_ids': sorted(chosen), 'journey_ids': sorted(linked),
            'claims_authenticated': False, 'behavior_observed': False, 'execution_authorized': False,
            'qualification': 'Declared promised behavior and bindings only; product fit and actual operation require independent evidence.'}
