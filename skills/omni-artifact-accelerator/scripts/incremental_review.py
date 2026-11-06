"""Explicit review coverage reuse, never a new acceptance or execution authority.

The small manifest is a declared dependency map, not semantic code analysis.
Unknown or incomplete maps require fresh reviews. Evidence remains immutable;
timestamps describe supplied freshness evidence, not independently observed access.
"""
from datetime import datetime, timezone
import copy
import hashlib
import json

POLICY = 'incremental-review-v1'
SCOPES = ('security', 'ui_ux', 'product_owner', 'qa')
KINDS = {'artifact', 'context', 'data', 'runtime', 'access', 'product', 'ux', 'numerical', 'unknown'}
REQUIRED_KINDS = {'context', 'data', 'runtime', 'access'}


def need(ok, code):
    if not ok:
        raise ValueError('incremental_' + code)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def stamp(value):
    need(type(value) is str, 'timestamp_required')
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('incremental_invalid_timestamp') from exc
    need(result.tzinfo is not None, 'timezone_required')
    return result


def validate_dependencies(dependencies, S):
    need(type(dependencies) is list and 1 <= len(dependencies) <= 256, 'dependencies_required')
    ids = set()
    for dep in dependencies:
        need(type(dep) is dict and set(dep) == {'id', 'kind', 'scopes', 'path', 'sha256', 'bytes', 'freshness'},
             'invalid_dependency_fields')
        need(S._ident(dep['id']) and dep['id'] not in ids and dep['kind'] in KINDS, 'invalid_dependency_identity')
        ids.add(dep['id'])
        S._pin_shape({k: dep[k] for k in ('path', 'sha256', 'bytes')})
        scopes = dep['scopes']
        need(type(scopes) is list and bool(scopes) and scopes == sorted(set(scopes)) and set(scopes) <= set(SCOPES),
             'invalid_dependency_scopes')
        # No syntax classifier claims a CSS/script edit cannot affect security or QA.
        if dep['kind'] == 'artifact':
            need({'security', 'qa', 'ui_ux'} <= set(scopes), 'artifact_security_qa_ux_coverage_required')
        if dep['kind'] in REQUIRED_KINDS:
            need(set(scopes) == set(SCOPES), 'safety_context_must_cover_all_scopes')
        fresh = dep['freshness']
        need(type(fresh) is dict and set(fresh) == {'mode', 'checked_at', 'expires_at'} and
             fresh['mode'] in {'immutable', 'until'}, 'invalid_freshness')
        checked = stamp(fresh['checked_at'])
        if fresh['mode'] == 'immutable':
            need(fresh['expires_at'] is None and dep['kind'] not in {'data', 'runtime', 'access'},
                 'external_freshness_required')
        else:
            need(stamp(fresh['expires_at']) > checked, 'invalid_freshness_window')


def manifest(fd, path, artifacts, S, P):
    pin = S._pin(fd, path, P)
    value = S._json(S._read(fd, path, P.MAX_BYTES), P)
    need(type(value) is dict and set(value) == {'schema_version', 'kind', 'dependencies'} and
         type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'oaa_review_manifest', 'invalid_manifest')
    validate_dependencies(value['dependencies'], S)
    deps = value['dependencies']
    for dep in deps:
        need(S._pin(fd, dep['path'], P) == {k: dep[k] for k in ('path', 'sha256', 'bytes')}, 'dependency_changed')
    actual = {p['path']: p for p in artifacts}
    covered = {d['path']: {k: d[k] for k in ('path', 'sha256', 'bytes')} for d in deps if d['kind'] == 'artifact'}
    need(covered == actual, 'artifact_coverage_mismatch')
    need(len(covered) == sum(d['kind'] == 'artifact' for d in deps), 'duplicate_artifact_dependency')
    # Missing mandatory evidence is an unknown impact, not a false pass.
    return pin, copy.deepcopy(deps)


def freshness_findings(candidate, at=None):
    at = at or datetime.now(timezone.utc)
    findings = []
    for dep in candidate['payload'].get('review_dependencies', []):
        fresh = dep['freshness']
        if stamp(fresh['checked_at']) > at:
            findings.append('future_evidence:' + dep['id'])
        if fresh['mode'] == 'until' and stamp(fresh['expires_at']) <= at:
            findings.append('expired_evidence:' + dep['id'])
    return findings


def impact_state(state, at=None):
    policy = state.get('incremental_policies', [])
    now, old = state.get('candidate'), state.get('previous_candidate')
    prior = state.get('previous_reviews', {})
    mode = policy[-1]['payload']['mode'] if policy else None
    result = {'policy': POLICY if policy else None, 'mode': mode, 'scopes': {},
              'claims_authenticated': False, 'publication_authorized': False}
    broad = []
    if not policy:
        broad.append('policy_not_adopted')
    if now is None or old is None or set(prior) != set(SCOPES):
        broad.append('four_review_baseline_required')
    newer = {d['id']: d for d in (now or {}).get('payload', {}).get('review_dependencies', [])}
    older = {d['id']: d for d in (old or {}).get('payload', {}).get('review_dependencies', [])}
    if not newer or not older:
        broad.append('manifest_missing')
    if set(newer) != set(older):
        broad.append('dependency_inventory_changed')
    for rows in (newer, older):
        if not REQUIRED_KINDS <= {d['kind'] for d in rows.values()}:
            broad.append('mandatory_safety_context_missing')
        if any(d['kind'] == 'unknown' for d in rows.values()):
            broad.append('unknown_impact')
    for key in set(newer) & set(older):
        if any(newer[key][field] != older[key][field] for field in ('kind', 'scopes')):
            broad.append('dependency_contract_changed:' + key)
    if now:
        broad.extend(freshness_findings(now, at))
    if old:
        # New timestamps cannot rejuvenate the prior observation or acceptance.
        broad.extend('prior_' + reason for reason in freshness_findings(old, at))
    if now and old and now['payload'].get('review_context') != old['payload'].get('review_context'):
        broad.append('stage_or_workflow_context_changed')
    changed = sorted(key for key in set(newer) & set(older)
                     if any(newer[key][field] != older[key][field] for field in ('sha256', 'bytes', 'freshness')) or
                     newer[key]['kind'] != 'artifact' and newer[key]['path'] != older[key]['path'])
    for scope in SCOPES:
        reasons = list(dict.fromkeys(broad))
        reasons.extend('dependency_changed:' + key for key in changed
                       if scope in newer[key]['scopes'] or scope in older[key]['scopes'])
        source = prior.get(scope)
        if source and now:
            independent = scope in {'qa', 'ui_ux'} or (scope == 'product_owner' and
                                                      'experience_dependencies' in source['payload'])
            if independent and source['payload']['reviewer'] in now['payload']['builders']:
                reasons.append('reviewer_is_current_builder')
            if source['payload']['basis'] != 'source':
                reasons.append('observed_acceptance_requires_fresh_review')
        proof = {'current': now['sha256'] if now else None, 'previous': old['sha256'] if old else None,
                 'source_review': source['sha256'] if source else None, 'scope': scope,
                 'current_dependencies': list(newer.values()), 'previous_dependencies': list(older.values())}
        result['scopes'][scope] = {'eligible': not reasons, 'action': 'carry_forward' if not reasons and mode == 'enforce'
                                  else 'observe_reuse' if not reasons else 'fresh_review',
                                  'reasons': reasons, 'source_review_sha256': source['sha256'] if source else None,
                                  'proof_sha256': digest(proof)}
    return result


def carry_payload(state, request):
    scope = request['scope']
    assessment = impact_state(state)
    need(assessment['mode'] == 'enforce', 'enforcement_not_adopted')
    row = assessment['scopes'][scope]
    need(row['eligible'], 'fresh_review_required:' + ';'.join(row['reasons']))
    source = state['previous_reviews'][scope]
    need(source['sha256'] == request['source_review_sha256'], 'source_review_mismatch')
    original = source['payload']
    return {**request, **{k: copy.deepcopy(original[k]) for k in ('reviewer', 'outcome', 'basis', 'evidence', 'experience_dependencies', 'app_release_policy') if k in original},
            'origin_review_sha256': original.get('origin_review_sha256', source['sha256']),
            'proof_sha256': row['proof_sha256']}


def validate_carry(state, payload, at):
    assessment = impact_state(state, at)
    need(assessment['mode'] == 'enforce', 'enforcement_not_adopted')
    row = assessment['scopes'][payload['scope']]
    need(row['eligible'] and row['proof_sha256'] == payload['proof_sha256'], 'carry_proof_invalid')
    source = state['previous_reviews'][payload['scope']]
    need(source['sha256'] == payload['source_review_sha256'], 'source_review_mismatch')
    original = source['payload']
    need(all(payload[k] == original[k] for k in ('reviewer', 'outcome', 'basis', 'evidence')) and
         payload.get('experience_dependencies') == original.get('experience_dependencies') and
         payload.get('app_release_policy') == original.get('app_release_policy') and
         payload['origin_review_sha256'] == original.get('origin_review_sha256', source['sha256']),
         'original_review_changed')


def _stage(P):
    if P is None:
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location('incremental_stage', Path(__file__).with_name('stage_gates.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, module._helpers(None)
    return P.routing_helper('stage_gates'), P


def adopt(root, request, *, P=None, provider=None):
    S, P = _stage(P)
    return S.record(root, {'policy': POLICY, 'mode': 'observe', **request, 'stage': 'incremental_policy'}, P=P, provider=provider)


def carry_forward(root, request, *, P=None, provider=None):
    S, P = _stage(P)
    return S.record(root, {**request, 'stage': 'review_carry_forward'}, P=P, provider=provider)


def impact(root, *, P=None, provider=None):
    S, P = _stage(P)
    status = S.inspect(root, P=P, provider=provider)
    need(status['status'] != 'invalid', 'invalid_stage_state')
    return status.get('incremental_review', {'policy': None, 'mode': None, 'scopes': {}})


def manifest_template(root, request, *, P=None):
    """Pin supplied evidence; caller supplies scopes and freshness, never inferred."""
    S, P = _stage(P)
    need(type(request) is dict and set(request) == {'dependencies'} and type(request['dependencies']) is list,
         'invalid_manifest_request')
    deps = []
    with S._root_fd(root, P) as (_, fd):
        for row in request['dependencies']:
            need(type(row) is dict and set(row) == {'id', 'kind', 'scopes', 'path', 'freshness'},
                 'invalid_manifest_dependency_request')
            deps.append({**copy.deepcopy(row), **S._pin(fd, row['path'], P)})
    validate_dependencies(deps, S)
    return {'schema_version': 1, 'kind': 'oaa_review_manifest', 'dependencies': deps}
