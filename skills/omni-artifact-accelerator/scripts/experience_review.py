"""Bounded, attributable experience reviews; never an aesthetic scoring engine."""

MAX_BYTES = 256 * 1024


def need(value, code):
    if not value:
        raise ValueError('experience_review.' + code)


def text(value, maximum=4096):
    return type(value) is str and 0 < len(value.strip()) <= maximum


def fields(value, required, optional=()):
    need(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional), 'fields_invalid')


def read(root, path, P):
    file = P.relative_file(root, path)
    raw = P.read_bytes(file, maximum=MAX_BYTES)
    value, checked = P.read_json(file)
    need(raw == checked, 'review_changed_during_read')
    return value, {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}


def ids(value):
    need(type(value) is list and len(value) <= 64 and all(text(v, 128) for v in value)
         and len(set(value)) == len(value), 'ids_invalid')
    return set(value)


def comparison(root, path, options, metadata, spec, P, *, expected_reviewer=None):
    """Require accountable substantive comparison of the actual three proposals."""
    helper = P.routing_helper('product_intent')
    context = helper.experience_context(spec)
    if context is None:
        return []
    review, pin = read(root, path, P)
    fields(review, {'schema_version', 'kind', 'reviewer', 'context', 'options', 'assessment', 'rationale'})
    need(type(review['schema_version']) is int and review['schema_version'] == 1
         and review['kind'] == 'analyst_experience_comparison', 'comparison_version_invalid')
    need(review['context'] == context, 'experience_context_changed')
    need(text(review['reviewer'], 256) and text(review['rationale']), 'reviewer_and_rationale_required')
    need(text(expected_reviewer, 256) and review['reviewer'] == expected_reviewer,
         'assigned_creative_reviewer_required')
    need(review['assessment'] == 'distinct_supported', 'concepts_require_revision')
    need(type(review['options']) is list and len(review['options']) == 3, 'three_reviews_required')
    expected = {o['id']: o for o in options}
    concepts = {m['option_id']: m for m in metadata}
    seen = set()
    for row in review['options']:
        fields(row, {'option_id', 'concept', 'task_relationship', 'action_outcome', 'evidence_gained',
                     'composition_difference', 'visual_locator'})
        ident = row['option_id']
        need(type(ident) is str and ident in expected and ident not in seen, 'option_identity_invalid')
        seen.add(ident)
        need(row['concept'] == expected[ident]['evidence'], 'concept_binding_changed')
        for key in ('task_relationship', 'action_outcome', 'evidence_gained', 'composition_difference', 'visual_locator'):
            need(text(row[key]), 'substantive_comparison_required')
        need(review['reviewer'] not in concepts[ident]['experience_authors'], 'independent_comparison_required')
    return [pin]


def fit(root, path, spec, candidate, review, P):
    """Review every promised outcome and canonical destination/journey separately.

    Human/agent assertions remain assertions. Source resolution cannot establish
    rendered quality; existing independent native/design QA remains authoritative
    for its separately observed lanes.
    """
    helper = P.routing_helper('product_intent')
    context = helper.experience_context(spec)
    if context is None or review['scope'] not in {'product_owner', 'ui_ux'}:
        return []
    value, pin = read(root, path, P)
    fields(value, {'schema_version', 'kind', 'reviewer', 'scope', 'basis', 'candidate_sha256',
                   'context', 'requirements', 'destinations', 'journeys', 'observations', 'rendered_quality'})
    need(type(value['schema_version']) is int and value['schema_version'] == 1
         and value['kind'] == 'analyst_experience_fit', 'fit_version_invalid')
    need(value['context'] == context, 'experience_context_changed')
    need(value['candidate_sha256'] == candidate['candidate_sha256'], 'candidate_binding_changed')
    need(all(value[k] == review[k] for k in ('reviewer', 'scope', 'basis')), 'review_identity_changed')
    need(value['reviewer'] not in candidate['builders'], 'independent_fit_review_required')
    need(value['rendered_quality'] in {'unobserved', 'recorded_observation'}, 'render_assurance_invalid')
    need(review['basis'] != 'source' or value['rendered_quality'] == 'unobserved', 'source_is_not_rendered_quality')
    need(review['basis'] != 'rendered' or review['outcome'] != 'resolved' or
         value['rendered_quality'] == 'recorded_observation', 'resolved_rendered_review_requires_observation')
    dependencies = {pin['path']: pin}
    observations = value['observations']
    need(type(observations) is list and len(observations) <= 64, 'observations_invalid')
    need(value['rendered_quality'] != 'recorded_observation' or bool(observations), 'recorded_observation_required')
    for observation in observations:
        fields(observation, {'path', 'sha256', 'bytes'})
        file = P.relative_file(root, observation['path'])
        raw = P.read_bytes(file)
        need(observation == {'path': observation['path'], 'sha256': P.digest(raw), 'bytes': len(raw)},
             'observation_changed')
        need(observation['path'] not in dependencies, 'duplicate_observation')
        dependencies[observation['path']] = observation
    required = {r['id'] for r in spec['requirements'] if r['id'] in
                spec['product']['experience_intent']['requirement_ids'] and r['disposition'] != 'explicitly_omitted'}
    destinations, journeys = set(), set()
    for path in sorted({s['design_path'] for s in spec['selections']}):
        design, design_pin = read(root, path, P)
        helper.validate_experience_handoff(design, spec)
        destinations.update(d['id'] for d in design['destinations'])
        journeys.update(j['id'] for j in design['journeys'])
        dependencies[path] = design_pin
    assessments = []
    observation_paths = {p['path'] for p in observations}
    for name, expected in (('requirements', required), ('destinations', destinations), ('journeys', journeys)):
        rows = value[name]
        need(type(rows) is list and len(rows) <= 128, 'coverage_invalid')
        seen = set()
        for row in rows:
            fields(row, {'id', 'assessment', 'candidate_locator', 'observation', 'evidence_paths'})
            need(type(row['id']) is str and row['id'] in expected and row['id'] not in seen, 'coverage_identity_invalid')
            seen.add(row['id'])
            need(row['assessment'] in {'matched', 'gap', 'unobserved'} and text(row['candidate_locator'])
                 and text(row['observation']), 'concrete_fit_finding_required')
            paths = ids(row['evidence_paths'])
            need(paths <= observation_paths, 'observation_not_bound')
            if review['basis'] != 'source' and row['assessment'] == 'matched':
                need(bool(paths), 'recorded_observation_required')
            assessments.append(row['assessment'])
        need(seen == expected, 'complete_' + name + '_coverage_required')
    if review['outcome'] == 'resolved':
        need(assessments and set(assessments) == {'matched'}, 'experience_findings_unresolved')
    return [dependencies[p] for p in sorted(dependencies)]
