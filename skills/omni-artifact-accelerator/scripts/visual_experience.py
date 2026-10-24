"""Pure visual discovery index over canonical requirements; no files or authority."""
import copy

FAMILIES = {'compare_track', 'locations', 'objects_environments', 'movement_flow',
            'atmosphere_context', 'custom'}
TREATMENTS = {'dimensional_styling', 'interactive_3d', 'refined_2d'}
FOLLOW_UP = {'answered', 'reused', 'delegated', 'not_applicable', 'unresolved'}
DISCOVERY_REQUIREMENT_FIELDS = ('id', 'category', 'purpose', 'value', 'surfaces', 'required',
                                'origin', 'disposition', 'decision_ref')
DISCOVERY_PRODUCT_FIELDS = ('priority', 'basis', 'source_refs', 'acceptance', 'alternative')


def _need(ok, message):
    if not ok:
        raise ValueError('visual_experience.' + message)


def _text(value, limit=8192):
    return type(value) is str and 0 < len(value.strip()) <= limit


def _ids(value, need, label, empty=False):
    need(type(value) is list and (empty or bool(value)) and len(value) <= 64
         and all(_text(v, 128) for v in value) and len(set(value)) == len(value), label + '_invalid')


def _metadata(spec):
    product = spec.get('product', {})
    return product.get('visual_experience') if type(product) is dict else None


def _referenced(meta):
    ids = set(meta['family_requirement_ids']) | set(meta['follow_up']['requirement_ids'])
    if meta.get('family_delegation_requirement_id'):
        ids.add(meta['family_delegation_requirement_id'])
    return sorted(ids)


def _attributed(req, need, bases=None):
    item = req.get('product')
    need(type(item) is dict, 'requirement_product_attribution_required')
    mapping = {'user_statement': 'user', 'reused_decision': 'reused',
               'recommendation': 'proposal', 'inference': 'proposal', 'unresolved': 'proposal'}
    basis = item.get('basis')
    need(type(basis) is str and basis in mapping and req.get('origin') == mapping[basis], 'requirement_attribution_invalid')
    if bases is not None:
        need(basis in bases, 'decision_requires_attributable_answer_or_delegation')
    refs = item.get('source_refs')
    need(type(refs) is list and refs and all(_text(v) for v in refs), 'requirement_sources_required')
    return refs


def _decision(req, need, bases):
    refs = _attributed(req, need, bases)
    need(req.get('disposition') == 'selected' and _text(req.get('decision_ref'))
         and req['decision_ref'] in refs, 'selected_decision_must_reference_its_source')


def _comparison(req):
    value = req['value']
    return value['family'] == 'compare_track' or (
        value['family'] == 'custom' and value['includes_comparisons'])


def _index_coverage(requirements, indexed, predicate, notes, need, label):
    for req in requirements:
        value = req.get('value')
        if type(value) is not dict or not predicate(value) or req['id'] in indexed:
            continue
        need(req.get('disposition') == 'explicitly_omitted', label + '_requirement_missing_from_index')
        refs = _attributed(req, need, {'user_statement', 'reused_decision'})
        need(req.get('decision_ref') in refs and all(ref.split('#', 1)[0] in notes for ref in refs),
             'unindexed_omission_must_reference_its_source')


def validate(spec, need=_need):
    """Malformed metadata raises; unanswered but structurally valid drafts survive."""
    need(type(spec) is dict, 'intent_object_required')
    product = spec.get('product', {})
    if type(product) is not dict or 'visual_experience' not in product:
        return
    need(_text(product.get('scope'), 128) and type(product.get('note_paths')) is list
         and all(_text(p) for p in product['note_paths']), 'product_context_required')
    need(type(spec.get('surfaces')) is list and spec['surfaces']
         and all(type(s) is str for s in spec['surfaces']), 'intent_surfaces_required')
    meta = product['visual_experience']
    need(type(meta) is dict and {'schema_version', 'family_requirement_ids', 'follow_up'} <= set(meta)
         and set(meta) <= {'schema_version', 'family_requirement_ids', 'follow_up',
                           'family_delegation_requirement_id'}, 'fields_invalid')
    need(type(meta['schema_version']) is int and meta['schema_version'] == 1, 'version_invalid')
    _ids(meta['family_requirement_ids'], need, 'family_requirement_ids')
    follow = meta['follow_up']
    need(type(follow) is dict and set(follow) == {'disposition', 'requirement_ids'}, 'follow_up_fields_invalid')
    need(type(follow['disposition']) is str and follow['disposition'] in FOLLOW_UP, 'follow_up_disposition_invalid')
    _ids(follow['requirement_ids'], need, 'follow_up_requirement_ids', empty=follow['disposition'] == 'unresolved')
    if 'family_delegation_requirement_id' in meta:
        need(_text(meta['family_delegation_requirement_id'], 128), 'family_delegation_requirement_id_invalid')
    requirements = spec.get('requirements')
    need(type(requirements) is list and all(type(r) is dict and _text(r.get('id'), 128) for r in requirements),
         'requirements_invalid')
    by_id = {r['id']: r for r in requirements}
    need(len(by_id) == len(requirements), 'duplicate_requirement_id')
    ids = _referenced(meta)
    need(set(ids) <= set(by_id), 'dangling_requirement_reference')
    need(not set(meta['family_requirement_ids']) & set(follow['requirement_ids']), 'family_and_follow_up_refs_overlap')
    delegate = meta.get('family_delegation_requirement_id')
    need(delegate not in meta['family_requirement_ids'] + follow['requirement_ids'], 'delegation_refs_overlap')
    notes = product.get('note_paths', [])
    for ident in ids:
        req = by_id[ident]
        refs = _attributed(req, need)
        need(all(ref.split('#', 1)[0] in notes for ref in refs), 'source_must_reference_product_notes')
        need(type(req.get('disposition')) is str and req['disposition'] in
             {'selected', 'unresolved', 'deferred', 'explicitly_omitted'},
             'requirement_disposition_invalid')
        need(type(req.get('surfaces')) is list and req['surfaces'] and
             all(s in spec.get('surfaces', []) for s in req['surfaces']), 'requirement_surfaces_invalid')
        if req['disposition'] in {'selected', 'explicitly_omitted'}:
            need(req.get('decision_ref') in refs, 'decision_must_reference_its_source')
        if req['disposition'] == 'explicitly_omitted':
            _attributed(req, need, {'user_statement', 'reused_decision'})
    for ident in meta['family_requirement_ids']:
        value = by_id[ident].get('value')
        need(type(value) is dict and type(value.get('family')) is str and value['family'] in FAMILIES,
             'family_value_invalid')
        if value['family'] == 'custom':
            need(set(value) == {'family', 'custom_label', 'includes_comparisons'}
                 and _text(value['custom_label'], 120) and type(value['includes_comparisons']) is bool,
                 'custom_family_requires_label_and_comparison_applicability')
        else:
            need(set(value) == {'family'}, 'family_fields_invalid')
    # Active structured preferences cannot disappear merely by excluding their IDs.
    # Generic unrelated values (for example a font family) are not reinterpreted.
    _index_coverage(requirements, set(meta['family_requirement_ids']),
                    lambda value: type(value.get('family')) is str and value['family'] in FAMILIES,
                    notes, need, 'family')
    _index_coverage(requirements, set(follow['requirement_ids']),
                    lambda value: type(value.get('treatment')) is str and (
                        value['treatment'] in TREATMENTS or (value['treatment'] == 'delegated'
                            and value.get('delegation_scope') == 'comparison_treatment')),
                    notes, need, 'treatment')
    if delegate:
        req = by_id[delegate]
        _decision(req, need, {'user_statement', 'reused_decision'})
        need(req.get('value') == {'delegation_scope': 'visual_families'}, 'family_delegation_scope_invalid')
        proposed = [by_id[i] for i in meta['family_requirement_ids']
                    if by_id[i]['disposition'] != 'explicitly_omitted' and by_id[i]['origin'] == 'proposal']
        need({s for r in proposed for s in r['surfaces']} <= set(req['surfaces']),
             'family_delegation_surface_missing')
    comparisons = [by_id[i] for i in meta['family_requirement_ids']
                   if by_id[i]['disposition'] != 'explicitly_omitted' and _comparison(by_id[i])]
    disposition = follow['disposition']
    need(not (disposition == 'not_applicable' and comparisons), 'comparison_follow_up_cannot_be_not_applicable')
    for ident in follow['requirement_ids']:
        req, value = by_id[ident], by_id[ident].get('value')
        if disposition == 'unresolved':
            need(req['disposition'] in {'unresolved', 'deferred'}, 'unresolved_follow_up_requires_open_requirement')
            need(value is None or (type(value) is dict and set(value) == {'treatment'}
                 and type(value['treatment']) is str and value['treatment'] in TREATMENTS), 'treatment_value_invalid')
        elif disposition == 'not_applicable':
            _decision(req, need, {'user_statement', 'reused_decision', 'recommendation', 'inference'})
            need(type(value) is dict and set(value) == {'rationale'} and _text(value['rationale']),
                 'not_applicable_requires_sourced_rationale')
        elif disposition == 'delegated':
            _decision(req, need, {'user_statement', 'reused_decision'})
            need(value == {'treatment': 'delegated', 'delegation_scope': 'comparison_treatment'},
                 'treatment_delegation_scope_invalid')
        else:
            _decision(req, need, {'user_statement'} if disposition == 'answered' else {'reused_decision'})
            need(type(value) is dict and set(value) == {'treatment'} and
                 type(value['treatment']) is str and value['treatment'] in TREATMENTS, 'treatment_value_invalid')
    # A choice on one surface cannot silently answer comparisons on another.
    if comparisons and disposition != 'unresolved':
        covered = {s for i in follow['requirement_ids'] for s in by_id[i]['surfaces']}
        need({s for r in comparisons for s in r['surfaces']} <= covered, 'comparison_treatment_surface_missing')


def _discovery_requirement(req):
    """Project decisions, not implementation/review annotations.

    Delivery, suggested roles, assets, runtime metadata and all contexts are
    excluded. Detailed design routinely adds loading/error/reduced-motion and
    viewport review cases after concept choice. Full intent/design/candidate
    freshness still governs those annotations; substantive user constraints
    belong in canonical requirement values, purpose or acceptance criteria.
    """
    result = {key: copy.deepcopy(req[key]) for key in DISCOVERY_REQUIREMENT_FIELDS if key in req}
    result['product'] = {key: copy.deepcopy(req['product'][key]) for key in DISCOVERY_PRODUCT_FIELDS
                         if key in req['product']}
    return result


def visual_context(spec):
    """Return discovery semantics without later implementation or review bindings."""
    validate(spec)
    meta = _metadata(spec)
    if meta is None:
        return None
    ids = _referenced(meta)
    by_id = {r['id']: r for r in spec['requirements']}
    requirements = [_discovery_requirement(by_id[i]) for i in ids]
    notes = sorted({ref.split('#', 1)[0] for r in requirements for ref in r['product']['source_refs']})
    return {'metadata': copy.deepcopy(meta), 'scope': spec['product']['scope'],
            'requirements': requirements, 'note_paths': notes}


def visual_report(spec):
    context = visual_context(spec)
    report = {'status': 'not_assessed', 'families': [], 'follow_up': None,
              'requirement_ids': [], 'findings': []}
    if context is None:
        return report
    meta = context['metadata']
    by_id = {r['id']: r for r in context['requirements']}
    active = [by_id[i] for i in meta['family_requirement_ids'] if by_id[i]['disposition'] != 'explicitly_omitted']
    report.update(families=sorted({r['value']['family'] for r in active}),
                  follow_up=copy.deepcopy(meta['follow_up']), requirement_ids=sorted(by_id))
    for req in active:
        basis = req['product']['basis']
        if req['disposition'] != 'selected' or basis == 'unresolved':
            report['findings'].append({'code': 'visual_family_unresolved', 'requirement_id': req['id']})
        elif basis in {'recommendation', 'inference'} and not meta.get('family_delegation_requirement_id'):
            report['findings'].append({'code': 'visual_family_answer_or_delegation_required', 'requirement_id': req['id']})
    if meta['follow_up']['disposition'] == 'unresolved':
        report['findings'].append({'code': 'visual_treatment_follow_up_unresolved',
                                   'comparison_in_scope': any(_comparison(r) for r in active)})
    report['status'] = 'unresolved' if report['findings'] else 'ready'
    return report


def validate_transition(previous, current, need=_need):
    """Adopted decisions stay indexed; explicit scope removal uses requirement disposition."""
    before, after = visual_context(previous), visual_context(current)
    if before is not None:
        need(after is not None, 'context_removed_reconcile_scope_instead')
        indexed = {r['id'] for r in after['requirements']}
        current_rows = {r['id']: r for r in current['requirements']}
        for req in before['requirements']:
            if req['id'] in indexed:
                continue
            replacement = current_rows.get(req['id'], {})
            need(replacement.get('disposition') == 'explicitly_omitted',
                 'requirement_index_removed_use_explicit_disposition')
            refs = _attributed(replacement, need, {'user_statement', 'reused_decision'})
            need(replacement.get('decision_ref') in refs and
                 all(ref.split('#', 1)[0] in current['product']['note_paths'] for ref in refs),
                 'omission_must_reference_its_source')
