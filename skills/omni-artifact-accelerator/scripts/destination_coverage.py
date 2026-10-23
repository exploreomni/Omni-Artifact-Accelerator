"""Derived review obligations, not another ledger or authentication of observations."""
from urllib.parse import quote
from pathlib import Path

VISUAL = {'craft', 'native_behavior', 'responsive', 'accessibility'}
JOURNEY_FIELDS = ('path', 'action', 'start_state', 'end_state', 'retained_context', 'return_behavior')


def text(value):
    return type(value) is str and bool(value.strip())


def obligation_id(requirement, surface, kind, target, context, lane):
    return '/'.join(quote(value, safe='') for value in (requirement, surface, kind, target, context, lane))


def execution_note(root, path, api):
    """Only retained UTF-8 notes/structured logs count here; still media never does."""
    if Path(path).suffix.lower() not in {'.txt', '.md', '.json'}:
        return False
    raw = api.relative_file(root, path).read_bytes()
    if raw.startswith((b'GIF87a', b'GIF89a', b'\x89PNG', b'\xff\xd8')) or b'<svg' in raw.lower():
        return False
    try:
        return bool(raw.decode('utf-8').strip()) and b'\x00' not in raw
    except UnicodeDecodeError:
        return False


def derive(root, spec, state, api):
    """Derive the denominator before looking at cases, including unresolved declarations."""
    gaps, inventory, obligations = [], [], []
    scope = spec['scope']
    coverage = scope.get('coverage', {})
    mode = coverage.get('mode')
    if mode not in {'whole_experience', 'focused'}:
        gaps.append({'code': 'destination_review_scope_missing'})
    selected = state.get('selected')
    if (not selected or state['status'] != 'consistent' or not spec.get('intent') or
            any(spec['intent'].get(k) != selected.get(k) for k in ('path', 'sha256'))):
        gaps.append({'code': 'destination_intent_missing_or_stale'})
    gaps.extend({'code': 'intent_choice_unresolved', 'question': q} for q in state.get('open_questions', []))
    gaps.extend(f for f in state.get('findings', []) if f['code'] in {
        'selection_missing', 'design_brand_reference_mismatch', 'invalid_current_selection'})
    targets = {}
    for selection in state.get('selections', []):
        surface = selection['surface']
        try:
            design, _ = api.read_json(api.relative_file(root, selection['design_path']))
            for kind, key in (('destination', 'destinations'), ('journey', 'journeys')):
                items = design.get(key, [])
                api.need(type(items) is list, key + ' must be a list')
                ids = set()
                for item in items:
                    api.need(type(item) is dict and text(item.get('id')) and item['id'] not in ids,
                             key + ' require unique nonempty IDs')
                    ids.add(item['id'])
                    targets[(surface, kind, item['id'])] = item
                    inventory.append({'surface': surface, 'kind': kind, 'id': item['id'], 'requirement_ids': []})
            api.need(any(k[:2] == (surface, 'destination') for k in targets), 'selected destinations missing')
            for (s, kind, ident), item in targets.items():
                if s == surface and kind == 'journey':
                    path = item.get('path')
                    api.need(type(path) is list and len(path) >= 2 and all(type(p) is str and
                             (surface, 'destination', p) in targets for p in path), 'journey path must name selected destinations')
                    api.need(all(text(item.get(k)) for k in JOURNEY_FIELDS if k != 'path'),
                             'journey action, states, retained_context and return_behavior required')
        except (ValueError, OSError, KeyError, TypeError) as exc:
            gaps.append({'code': 'destination_inventory_invalid', 'surface': surface, 'detail': str(exc)})
    if not inventory:
        gaps.append({'code': 'destination_inventory_missing'})
    requirements = state.get('requirements', [])
    for req in requirements:
        if not (req['required'] or req['disposition'] == 'selected'):
            continue
        delivery = req.get('delivery', {})
        links = [('destination', ident) for ident in delivery.get('destinations', [])]
        links += [('journey', ident) for ident in delivery.get('journeys', [])]
        if not links and req['disposition'] != 'explicitly_omitted':
            gaps.append({'code': 'requirement_destinations_missing', 'requirement_id': req['id']})
        for surface in req['surfaces']:
            # Surface-specific applicability permits shared requirements with distinct screen IDs.
            applications = [(context, item) for context in req.get('contexts', [])
                            for item in context.get('applicability', [])
                            if item.get('surface', surface) == surface]
            for context, item in applications:
                if (item['kind'], item['id']) not in links or (surface, item['kind'], item['id']) not in targets:
                    gaps.append({'code': 'applicability_target_unknown', 'requirement_id': req['id'],
                                 'surface': surface, 'context_id': context['id'], 'target_id': item['id']})
            # delivery links may be the union of IDs across surfaces. Require each ID on at least
            # one requirement surface; inventory below independently detects unlinked destinations.
            for kind, ident in links:
                if not any((s, kind, ident) in targets for s in req['surfaces']):
                    gaps.append({'code': 'delivery_target_unknown', 'requirement_id': req['id'], 'target_id': ident})
                if (surface, kind, ident) not in targets:
                    continue
                item = next(i for i in inventory if (i['surface'], i['kind'], i['id']) == (surface, kind, ident))
                item['requirement_ids'].append(req['id'])
                if req['disposition'] == 'explicitly_omitted':
                    item.setdefault('omissions', []).append({'requirement_id': req['id'], 'decision_ref': req['decision_ref']})
                    continue
                if req['disposition'] != 'selected':
                    gaps.append({'code': 'destination_requirement_' + req['disposition'], 'requirement_id': req['id'],
                                 'surface': surface, 'target_id': ident})
                applicable = [(c, a) for c, a in applications if (a['kind'], a['id']) == (kind, ident)]
                if not applicable:
                    gaps.append({'code': 'destination_context_missing', 'requirement_id': req['id'],
                                 'surface': surface, 'target_id': ident})
                for context, application in applicable:
                    for lane in scope['required_lanes']:
                        rule = application['lanes'].get(lane, {})
                        status = rule.get('status', 'missing')
                        oid = obligation_id(req['id'], surface, kind, ident, context['id'], lane)
                        if status == 'missing':
                            gaps.append({'code': 'lane_applicability_missing', 'obligation_id': oid})
                        obligations.append({'id': oid, 'requirement_id': req['id'], 'surface': surface,
                            'kind': kind, 'target_id': ident, 'context_id': context['id'], 'lane': lane,
                            'context': {k: v for k, v in context.items() if k != 'applicability'},
                            'applicability': rule, 'disposition': req['disposition'],
                            'expectation': targets[(surface, kind, ident)] if kind == 'journey' else req['purpose']})
    for item in inventory:
        if not item['requirement_ids']:
            gaps.append({'code': 'destination_without_requirement', 'surface': item['surface'],
                         'kind': item['kind'], 'target_id': item['id']})
    affected = coverage.get('affected_obligation_ids', [])
    known = {o['id'] for o in obligations}
    if mode == 'focused' and (not affected or not set(affected) <= known):
        gaps.append({'code': 'focused_obligations_missing_or_unknown'})
    if mode == 'whole_experience' and (affected or set(scope['surfaces']) != {i['surface'] for i in inventory}):
        gaps.append({'code': 'whole_experience_scope_mismatch'})
    for obligation in obligations:
        obligation['in_scope'] = mode != 'focused' or obligation['id'] in affected
        if obligation['in_scope'] and obligation['surface'] not in scope['surfaces']:
            gaps.append({'code': 'obligation_surface_outside_scope', 'obligation_id': obligation['id']})
    return {'status': 'incomplete', 'mode': mode, 'inventory': inventory, 'obligations': obligations,
            'gaps': gaps, 'claims_authenticated': False}


def evaluate(root, spec, state, results, api, image_file, stale):
    report = derive(root, spec, state, api)
    obligations = {o['id']: o for o in report['obligations']}
    deps = {d['id']: d for d in spec['dependencies']}
    selections = {s['surface']: s for s in state.get('selections', [])}
    captures = {c['id']: c for c in spec.get('captures', [])}
    indexed = {r['id']: r for r in results}
    requirements = {r['id']: r for r in state.get('requirements', [])}
    for capture in captures.values():
        candidate = deps.get(capture.get('candidate_id'), {})
        req = requirements.get(capture.get('requirement_id'), {})
        contexts = {c['id']: c for c in req.get('contexts', [])}
        context = contexts.get(capture.get('requirement_context'))
        if (not context or not any(i['kind'] == 'destination' and i['id'] == capture.get('destination_id') and
                i['surface'] == candidate.get('surface') for i in report['inventory']) or
                capture.get('destination_id') not in req.get('delivery', {}).get('destinations', []) or
                candidate.get('surface') not in req.get('surfaces', [])):
            report['gaps'].append({'code': 'capture_destination_binding_invalid', 'capture_id': capture['id']})
    for case in spec.get('cases', []):
        result = indexed[case['id']]
        ids = case.get('obligation_ids', [])
        reasons = []
        if case['lane'] in VISUAL and any(g['code'] == 'destination_intent_missing_or_stale' for g in report['gaps']):
            reasons.append('intent_selection_stale_or_changed')
        bound = [obligations[i] for i in ids if i in obligations]
        if not ids or len(bound) != len(ids):
            reasons.append('obligation_binding_missing_or_unknown')
        if any(o['surface'] != case['surface'] or o['lane'] != case['lane'] or not o['in_scope'] for o in bound):
            reasons.append('obligation_scope_mismatch')
        candidate = deps.get(case.get('candidate_id'), {})
        selection = selections.get(case['surface'], {})
        if candidate.get('path') != selection.get('candidate_path') or candidate.get('target') != selection.get('target'):
            reasons.append('intent_candidate_mismatch')
        for kind in ('design', 'brand'):
            if selection.get(kind + '_path') and not any(d['kind'] == kind and d['surface'] in {case['surface'], 'shared'}
                    and d['path'] == selection[kind + '_path'] for d in deps.values()):
                reasons.append('intent_' + kind + '_dependency_missing')
        if case['status'] == 'pass' and not text(case.get('expected')):
            reasons.append('obligation_expectation_missing')
        if case['lane'] in VISUAL:
            assets = {a for o in bound for a in requirements[o['requirement_id']].get('asset_ids', [])}
            if set(case.get('asset_ids', [])) != assets:
                reasons.append('requirement_asset_expectation_missing')
        for obligation in bound:
            req = requirements[obligation['requirement_id']]
            if case['lane'] in VISUAL and req.get('asset_ids') and (not text(case.get('expected')) or
                    not set(req['asset_ids']) <= set(case.get('asset_ids', []))):
                reasons.append('requirement_asset_expectation_missing')
            if case.get('requirement_id') is not None and (case['requirement_id'] != obligation['requirement_id'] or
                    case.get('requirement_context') != obligation['context_id']):
                reasons.append('requirement_binding_mismatch')
            rule = obligation['applicability']
            if case['status'] == 'not_applicable' and rule.get('status') != 'not_applicable':
                reasons.append('required_obligation_cannot_be_excluded_by_case')
            if case['status'] == 'pass' and rule.get('status') != 'required':
                reasons.append('obligation_applicability_unresolved_or_excluded')
            if case['status'] != 'pass':
                continue
            if obligation['kind'] == 'destination' and case['lane'] in VISUAL:
                context = obligation['context']
                linked = [captures[i] for i in case.get('capture_ids', []) if i in captures]
                if not any(c.get('destination_id') == obligation['target_id'] and
                        c.get('requirement_id') == obligation['requirement_id'] and
                        c.get('requirement_context') == obligation['context_id'] and
                        all(c['context'].get(k) == context[k] for k in ('appearance', 'state')) and
                        ('viewport' not in context or c['context'].get('viewport') == context['viewport']) for c in linked):
                    reasons.append('destination_capture_context_mismatch:' + obligation['id'])
            if obligation['kind'] == 'journey':
                if case['lane'] in VISUAL:
                    context = obligation['context']
                    expectation = obligation['expectation']
                    endpoints = [(expectation['path'][0], expectation['start_state']),
                                 (expectation['path'][-1], expectation['end_state'])]
                    linked = [captures[i] for i in case.get('capture_ids', []) if i in captures]
                    if not all(any(c.get('destination_id') == dest and
                            c.get('requirement_id') == obligation['requirement_id'] and
                            c.get('requirement_context') == obligation['context_id'] and
                            c['context'].get('appearance') == context['appearance'] and
                            c['context'].get('state') == endpoint_state and
                            ('viewport' not in context or c['context'].get('viewport') == context['viewport'])
                            for c in linked) for dest, endpoint_state in endpoints):
                        reasons.append('journey_endpoint_capture_mismatch:' + obligation['id'])
                observations = [o for o in case.get('journey_observations', []) if o['obligation_id'] == obligation['id']]
                expected_method = ('participant_observation' if case['lane'] == 'human_usability' else
                                   'native_execution' if candidate.get('target', {}).get('state') != 'local' else 'local_execution')
                if not any(all(o.get(k) == obligation['expectation'].get(k) for k in JOURNEY_FIELDS) and
                        o.get('method') == expected_method and text(o.get('observation')) and o.get('evidence_paths') and
                        all(p not in stale for p in o['evidence_paths']) and
                        any(execution_note(root, p, api) for p in o['evidence_paths']) for o in observations):
                    reasons.append('journey_execution_missing_or_mismatched:' + obligation['id'])
        if any(o['obligation_id'] not in ids or o['obligation_id'] not in obligations or
               obligations[o['obligation_id']]['kind'] != 'journey' for o in case.get('journey_observations', [])):
            reasons.append('journey_observation_binding_mismatch')
        if reasons:
            result['recorded_status'] = 'not_run'
            result['reasons'].extend(r for r in reasons if r not in result['reasons'])
        result['obligation_ids'] = ids
        if result['recorded_status'] not in {'pass', 'not_applicable'}:
            report['gaps'].append({'code': 'bound_case_incomplete', 'case_id': case['id'],
                                   'status': result['recorded_status']})
    for obligation in obligations.values():
        matches = [r for r in results if obligation['id'] in r.get('obligation_ids', [])]
        rule = obligation['applicability'].get('status')
        statuses = {r['recorded_status'] for r in matches}
        status = ('out_of_scope' if not obligation['in_scope'] else
                  'not_applicable' if rule == 'not_applicable' and
                  (not matches or statuses == {'not_applicable'}) else
                  obligation['disposition'] if obligation['disposition'] != 'selected' else
                  'not_assessed' if rule not in {'required', 'not_applicable'} else
                  'missing' if not matches else
                  next((s for s in ('fail', 'blocked', 'not_run') if s in statuses),
                       'pass' if statuses == {'pass'} else 'not_applicable' if statuses == {'not_applicable'} else 'not_run'))
        obligation.update(status=status, case_ids=[r['id'] for r in matches], native_recorded=False)
        # Native fulfillment is explicitly separate from successful local evidence.
        if status == 'pass' and obligation['lane'] in VISUAL:
            obligation['native_recorded'] = all(deps.get(next(c for c in spec['cases'] if c['id'] == r['id']).get('candidate_id'),
                {}).get('target', {}).get('state') in {'draft', 'published'} for r in matches)
        if status not in {'pass', 'not_applicable', 'out_of_scope'}:
            report['gaps'].append({'code': 'destination_obligation_incomplete', 'obligation_id': obligation['id'], 'status': status})
    for collection in ('findings', 'deviations'):
        for finding in spec.get(collection, []):
            ids = finding.get('obligation_ids', [])
            valid = bool(ids) and all(i in obligations and obligations[i]['in_scope'] and
                    obligations[i]['surface'] == finding['surface'] for i in ids)
            original = indexed.get(finding.get('case_id'), {})
            if collection == 'findings':
                valid = valid and set(ids) <= set(original.get('obligation_ids', []))
            if finding.get('disposition') == 'corrected':
                retest = indexed.get(finding.get('retest_case_id'), {})
                valid = valid and retest.get('recorded_status') == 'pass' and set(ids) <= set(retest.get('obligation_ids', []))
            if not valid:
                report['gaps'].append({'code': 'correction_obligation_mismatch', 'collection': collection, 'id': finding['id']})
    report['status'] = ('incomplete' if report['gaps'] else
                        'scoped_complete' if report['mode'] == 'focused' else 'complete')
    return report
