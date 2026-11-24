"""Project-bound, offline coordination of standalone Omni semantic work."""
from functools import lru_cache
import importlib.util
import os
from pathlib import Path
import re
import tempfile


POLICY = 'omni-modeling-v1'
FIRST = 'contracts/semantic-route-000001.json'
OPERATIONS = ('route', 'candidate', 'branch-plan', 'governance', 'verify', 'access', 'queries', 'panels', 'gap', 'delivery')
AUTHOR = {'create_topic', 'translate_semantics', 'extend_topic'}


def need(value, reason):
    if not value:
        raise ValueError('semantic_lane.' + reason)


@lru_cache(maxsize=4)
def specialist(name):
    need(name in {'semantic_modeler', 'semantic_verification', 'semantic_branch', 'semantic_governance'}, 'unknown_specialist')
    source = Path(__file__).resolve().parents[2] / 'omni-bi-engineer/scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location('oaa_' + name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def active(root, project):
    return project.get('semantic_lane') == POLICY or (root / FIRST).exists()


def routes(root):
    return sorted((root / 'contracts').glob('semantic-route-??????.json'))


def latest(root, P, D):
    versions = routes(root)
    if not versions:
        return None
    path = versions[-1].relative_to(root).as_posix()
    return D.pin(root, path, P)


def store(root, relative, value, P, D):
    """Publish complete immutable records; identical retries converge."""
    dest = P.no_links(root / D.safe_output(relative))
    need(dest.parent == root / 'contracts', 'output_must_be_in_contracts')
    P.validation_helper().before_mutation()
    raw = P.canonical(value) + b'\n'
    try:
        if os.name == 'nt':
            P.private_write(dest, raw)
        else:
            with tempfile.NamedTemporaryFile(dir=dest.parent) as new:
                new.write(raw)
                new.flush()
                os.link(new.name, dest)
    except FileExistsError:
        need(D.same(D.read(root, relative, P)[0], value, P), 'output_conflict')
    return D.pin(root, relative, P)


def discovery(root, project, source, P, D):
    req = D.evidence(root, source, P)
    need(req.get('kind') == 'omni_modeling_discovery' and req.get('schema_version') == 1,
         'discovery_contract_required')
    ctx = D.context(req.get('context'))
    topic = req.get('topic_name')
    need(isinstance(topic, str) and re.fullmatch(r'[a-z_][a-z0-9_]*', topic), 'topic_name_required')
    inventory = D.evidence(root, req['inventory'], P)
    need(inventory.get('context') == ctx and inventory.get('kind') == 'omni_modeling_inventory'
         and D.text(inventory.get('connection_id')), 'inventory_scope_changed')
    names = inventory.get('topic_names')
    need(D.strings(names, 8192) and type(inventory.get('complete')) is bool, 'topic_inventory_required')
    suitability = inventory.get('suitability')
    need(isinstance(suitability, dict) and set(suitability) <= set(names)
         and all(isinstance(row, dict) and row.get('status') in ('suitable','unsuitable','unknown')
                 and D.text(row.get('reason')) for row in suitability.values()), 'invalid_suitability')
    physical = inventory.get('physical_status')
    need(physical in ('ready', 'missing', 'unknown'), 'physical_status_required')
    identity = D.evidence(root, inventory['identity'], P)
    models = D.evidence(root, inventory['models'], P)
    D.check_models(models, ctx)
    need(models[ctx['model_id']]['connectionId'] == inventory['connection_id'], 'connection_changed')
    role = identity.get('rolesByModel', {}).get(ctx['model_id'], {})
    principal_seen = (isinstance(role, dict) and identity.get('keyScope') == 'user'
                      and identity.get('user', {}).get('membershipId') == ctx['principal_id'] and bool(role))
    author_scope = 'user' if principal_seen else None
    if not principal_seen and inventory.get('branch_author'):
        authorization = D.evidence(root, inventory['branch_author'], P)
        need(authorization.get('topic_name') == topic, 'branch_author_topic_changed')
        author_scope = specialist('semantic_branch').author_scope(identity, models, ctx, authorization)
    # A successful scoped user listing alone may omit restricted Topics.
    permissions = role.get('permissions') if isinstance(role, dict) else None
    can_inspect_model = author_scope == 'organization_branch_author' or (
        principal_seen and isinstance(permissions, list) and 'USE_IDE' in permissions and 'UPDATE' in permissions)
    visible = (can_inspect_model and inventory.get('model_visibility') == 'complete'
               and inventory['complete'] and identity.get('rolesByModelTruncated') is not True)
    selected = req.get('choice')
    if selected is not None:
        choice = D.evidence(root, selected, P)
        need(choice.get('role') == 'user' and D.text(choice.get('reference')) and D.text(choice.get('response_text'))
             and choice.get('context') == ctx and choice.get('topic_name') == topic, 'choice_scope_mismatch')
        decision = choice.get('action')
        need(decision in ('create_topic', 'translate_semantics', 'extend_topic', 'reuse_existing', 'defer'), 'choice_action')
    else:
        decision = None
    source_export = req.get('source_inventory')
    if source_export is not None:
        D.evidence(root, source_export, P)
    suitable = [n for n, review in suitability.items() if review['status'] == 'suitable']
    if decision == 'defer':
        route = 'deferred'
    elif author_scope is None:
        route = 'access_pending'
    elif topic in suitable:
        route = 'reuse_existing' if principal_seen else 'access_pending'
    elif (topic in names and suitability.get(topic, {}).get('status') == 'unsuitable'
          and visible and physical == 'ready' and (decision == 'extend_topic' or not suitable)):
        route = ('extend_topic' if decision == 'extend_topic' and ctx['branch_id']
                 and not ctx['workbook_model_id'] else 'offer_extend_topic')
    elif suitable:
        route = 'select_existing'
    elif topic in names or not visible or set(suitability) != set(names) or any(
            r['status'] == 'unknown' for r in suitability.values()):
        route = 'discovery_pending'
    elif physical == 'missing':
        route = 'upstream_required'
    elif physical != 'ready':
        route = 'discovery_pending'
    else:
        proposed = 'translate_semantics' if source_export is not None else 'create_topic'
        route = proposed if decision == proposed and ctx['branch_id'] and not ctx['workbook_model_id'] else 'offer_' + proposed
    return {'kind': 'omni_modeling_route', 'schema_version': 1, 'project_id': project['id'],
            'source': source, 'previous': req.get('previous'), 'route': route, 'topic_name': topic,
            'context': ctx, 'author_scope': author_scope, 'inventory': req['inventory'], 'source_inventory': source_export,
            'owner': 'oaa' if route in AUTHOR else 'model_owner' if route == 'reuse_existing' else 'unassigned',
            'authorizes_target_write': False}


def current_route(root, project, ref, P, D):
    need(not D.bound(project, root), 'dma_owner_use_existing_handoff')
    need(ref is not None and ref == latest(root, P, D), 'current_route_required')
    saved = D.evidence(root, ref, P)
    need(saved == discovery(root, project, saved['source'], P, D), 'route_evidence_changed')
    return saved


def candidate_value(root, project, source, P, D):
    spec = D.evidence(root, source, P)
    route = current_route(root, project, spec['route'], P, D)
    need(route['route'] in AUTHOR, 'standalone_branch_authoring_required')
    inventory = D.evidence(root, route['inventory'], P)
    baseline = D.evidence(root, inventory['baseline'], P)
    definition = D.evidence(root, spec['definition'], P)
    ctx, topic = route['context'], route['topic_name']
    need('baseline' not in definition and 'source_inventory' not in definition and
         baseline.get('model_id') == ctx['model_id'] and baseline.get('branch_id') == ctx['branch_id'] and
         sorted(baseline.get('topic_names', [])) == sorted(inventory['topic_names'])
         and definition.get('topic', {}).get('name') == topic, 'baseline_or_topic_changed')
    need(('update' in definition) == (route['route'] == 'extend_topic'), 'reviewed_edit_scope_required')
    model = {**definition, 'baseline': baseline}
    if route['source_inventory']:
        model['source_inventory'] = D.evidence(root, route['source_inventory'], P)
    value = specialist('semantic_modeler').build_candidate(model)
    if route['source_inventory']:
        scope = D.evidence(root, spec['source_scope'], P)
        crosswalk = {r['asset_key']: r for r in value['crosswalk']}
        required, deferred = scope.get('required'), scope.get('deferred')
        need(scope.get('inventory') == route['source_inventory'] and D.text(scope.get('reference')) and
             D.strings(required, 5000) and required and isinstance(deferred, dict) and
             all(D.text(reason) for reason in deferred.values()) and not set(required).intersection(deferred) and
             set(required) | set(deferred) == set(crosswalk), 'complete_source_dispositions_required')
        gaps = [key for key in required if crosswalk[key]['status'] != 'reviewed_mapping']
        if gaps:
            value = {**value, 'status':'blocked', 'files':{}, 'changes':[], 'rollback':[], 'candidate_sha256':None,
                     'gaps':[*value['gaps'], {'code':'required_source_mapping_missing','keys':gaps,'blocking':True}]}
    return {'kind': 'omni_modeling_candidate', 'schema_version': 1, 'source': source,
            'route': spec['route'], 'context': ctx, 'topic_name': topic, 'candidate': value,
            'authorizes_target_write': False}


def checked_candidate(root, project, ref, route_pin, P, D):
    saved = D.evidence(root, ref, P)
    value = candidate_value(root, project, saved['source'], P, D)
    need(value == saved and saved['route'] == route_pin and value['candidate']['status'] == 'candidate',
         'current_resolved_candidate_required')
    return value


class Originals(dict):
    """Read only explicitly requested, bounded engagement-local original captures."""
    def __init__(self, root, P):
        super().__init__()
        self.root, self.P = root, P

    def __contains__(self, path):
        if super().__contains__(path):
            return True
        try:
            original = self.P.relative_file(self.root, path)
        except ValueError as error:
            if str(error).startswith('missing engagement file:'):
                return False
            raise
        self[path] = self.P.read_bytes(original)
        return True


def verification(root, project, spec, P, D, *, artifact_sha256=None):
    route = current_route(root, project, spec['route'], P, D)
    topic = route['topic_name']
    target = D.context(spec.get('context', route['context']))
    need(all(target[k] == route['context'][k] for k in ('base_url','model_id','branch_id','workbook_model_id')),
         'verified_model_route_changed')
    if route['route'] in AUTHOR:
        candidate = checked_candidate(root, project, spec['candidate'], spec['route'], P, D)
        generated = candidate['candidate']
        fingerprint = generated['candidate_sha256']
        application = D.evidence(root, spec['application'], P)
        readback_context = D.context(application.get('context'))
        need(all(readback_context[k] == target[k] for k in ('base_url','model_id','branch_id','workbook_model_id'))
             and readback_context['principal_id'] in (target['principal_id'], route['context']['principal_id'])
             and readback_context.get('model_version_id') == target.get('model_version_id')
             and application.get('candidate_sha256') == fingerprint and
             application.get('kind') == 'omni_branch_file_readback' and application.get('model_id') == target['branch_id']
             and D.text(application.get('source_ref')), 'candidate_branch_readback_required')
        raw = D.evidence(root, application['yaml_response'], P)
        files = raw.get('files', {})
        checksums = raw.get('checksums', {})
        need(type(raw.get('version')) is int and all(isinstance(files.get(path), str) and D.text(checksums.get(path))
             and specialist('semantic_modeler').matches_readback(expected, files[path])
             for path, expected in generated['files'].items()), 'candidate_branch_file_changed')
    else:
        need(route['route'] == 'reuse_existing' and spec.get('candidate') is None, 'resolved_topic_required')
        fingerprint = spec.get('topic_response_sha256')
        need(type(fingerprint) is str and re.fullmatch('[0-9a-f]{64}', fingerprint), 'reuse_topic_hash_required')
    checks = D.evidence(root, spec['checks'], P)
    assessment = specialist('semantic_verification').verify_topic(checks, context=target,
        topic_name=topic, candidate_sha256=fingerprint, originals=Originals(root, P), artifact_sha256=artifact_sha256)
    return target, fingerprint, assessment


def access_value(root, project, source, P, D):
    spec = D.evidence(root, source, P)
    need(spec.get('kind') == 'omni_modeling_access', 'standalone_access_spec_required')
    ctx, fingerprint, check = verification(root, project, spec, P, D)
    route = current_route(root, project, spec['route'], P, D)
    need(check.get('model_ready') is True, 'topic_model_verification_pending')
    name = route['topic_name']
    observation = D.evidence(root, spec['observation'], P)
    snapshots = D.check_observation(root, observation, ctx, fingerprint, [name], P, kind='omni_topic_observation')
    actual = P.digest(P.canonical(snapshots[name]))
    need(actual == check['topic_response_sha256'], 'different_topic_readbacks')
    if route['route'] == 'reuse_existing':
        need(actual == fingerprint, 'existing_topic_changed')
    fields = spec.get('fields')
    need(D.strings(fields, 2048) and bool(fields), 'selected_fields_required')
    D.peer('standalone').semantic_definitions({'topics': snapshots}, [{'topic': name, 'field_ids': fields,
                                              'query_key': None, 'query': {}}])
    connection = D.evidence(root, observation['models'], P)[ctx['model_id']]['connectionId']
    need(connection == D.evidence(root, route['inventory'], P)['connection_id'], 'connection_changed')
    return {'kind':'omni_topic_access', 'schema_version':1, 'project_id':project['id'], 'source':source,
            'route_pin':spec['route'], 'context':ctx, 'topics':[name], 'catalog':None,
            'review_sha256':fingerprint, 'fields':fields, 'topic_hashes':{name:actual},
            'observation':spec['observation'], 'connection_id':connection,
            'status':'observed_from_supplied_evidence','origin_authenticated':False}, snapshots, None


def delivery_value(root, project, req, access, queries, artifact, P, D):
    need(req.get('access') == access and req.get('queries') == queries and req.get('artifact_sha256') == artifact,
         'delivery_context_changed')
    a = D.checked_access(root, project, access, P)[0]
    original = D.evidence(root, a['source'], P)
    checks = dict(original, checks=req['checks'])
    phase_a = D.evidence(root, original['checks'], P)
    phase_f = D.evidence(root, checks['checks'], P)
    need(phase_f.get('policy') == phase_a.get('policy'), 'changed_access_policy')
    _, _, assessment = verification(root, project, checks, P, D, artifact_sha256=artifact)
    need(assessment.get('delivery_ready') is True and assessment['topic_response_sha256'] == a['topic_hashes'][a['topics'][0]],
         'delivery_observations_pending')
    query_receipt = D.evidence(root, queries, P)
    query_spec = D.evidence(root, query_receipt['source'], P)
    policy = D.evidence(root, phase_f.get('delivery_policy', phase_f['policy']), P)
    planned_controls = {(c['document_id'], c['control_key']) for c in query_spec['controls']}
    probed_controls = {(p['request']['document_id'], p['request']['resource'])
                       for persona in policy['personas'].values()
                       for p in (persona if isinstance(persona, list) else persona.get('probes', []))
                       if p.get('kind') == 'control'}
    need(planned_controls == probed_controls, 'delivery_control_scope_changed')
    rows = query_receipt['consumers']
    documents = {r['document_id'] for r in rows if r['disposition'] in ('reuse','new')}
    need(documents and set(assessment['documents']) == documents, 'delivery_document_scope_changed')


def release_check(root, project, access, queries, artifact, P, D):
    path = 'contracts/semantic-delivery-' + artifact + '.json'
    record = D.read(root, path, P)[0]
    req = D.evidence(root, record['source'], P)
    delivery_value(root, project, req, access, queries, artifact, P, D)


def execute(root, P, operation, request, output=None):
    root, project = P.load_project(root)
    D = P.routing_helper('dma_topics')
    need(not set(project['surfaces']) - D.SURFACES, 'app_or_dashboard_required')
    if operation == 'route' and D.bound(project, root):
        selection, _, catalog = D.current(root, project, P)
        return {'route':'dma_handoff', 'owner':'dma', 'authorizes_target_write':False,
                'topics':selection['topic_names'] if selection else [t['id'] for t in (catalog or {}).get('topics',[])]}
    need(not D.bound(project, root), 'dma_owner_use_existing_handoff')
    if operation not in ('route', 'delivery') and output:
        need(not Path(output).name.startswith(('semantic-route-', 'semantic-delivery-')), 'reserved_output_name')
    if operation == 'panels':
        need(active(root, project), 'select_route_first')
        return D.prepare_panels(root, P, request)
    with P.validation_operation(root):
        source = D.pin(root, request, P)
        req = D.evidence(root, source, P)
        if operation == 'route':
            value = discovery(root, project, source, P, D)
            prior = latest(root, P, D)
            if prior and D.evidence(root, prior, P) == value:
                return prior
            need(value['previous'] == prior, 'route_changed_supply_previous')
            seq = 1 if prior is None else int(Path(prior['path']).stem.split('-')[-1]) + 1
            need(seq < 1000000, 'route_history_limit')
            name = 'contracts/semantic-route-%06d.json' % seq
        elif operation in ('access','queries'):
            need(active(root, project), 'select_route_first')
            value = (D.access_value(root,project,source,P) if operation == 'access'
                     else D.plan_value(root,project,source,P))[0]
            name = output
        elif operation == 'candidate':
            value = candidate_value(root, project, source, P, D)
            name = output
        elif operation == 'branch-plan':
            wrapper = checked_candidate(root, project, req['candidate'], req['route'], P, D)
            value = specialist('semantic_branch').prepare_branch(wrapper, D.evidence(root, req['snapshot'], P))
            name = output
        elif operation == 'governance':
            route = current_route(root, project, req['route'], P, D)
            value = specialist('semantic_governance').plan_access(D.evidence(root, req['policy_request'], P),
                context=route['context'], topic_name=route['topic_name'])
            name = output
        elif operation == 'verify':
            _, _, value = verification(root, project, req, P, D)
            name = output
        elif operation == 'gap':
            route = current_route(root, project, req['route'], P, D)
            need(route['route'] == 'upstream_required', 'upstream_requirement_not_established')
            value = D.evidence(root, req['requirements'], P)
            D.peer('cowork').check_spec(value)
            need(value['route'] == 'warehouse_first_refactor', 'upstream_request_route')
            name = output
        elif operation == 'delivery':
            access, queries = D.stage_inputs(root, project, P)
            artifact = P.stage_status(root).get('candidate_sha256')
            need(isinstance(artifact, str), 'frozen_artifact_required')
            delivery_value(root, project, req, access, queries, artifact, P, D)
            value = {'kind':'omni_modeling_delivery', 'source':source}
            name = 'contracts/semantic-delivery-' + artifact + '.json'
        else:
            raise ValueError('semantic_lane.unknown_operation')
    need(isinstance(name, str) and (output is None or output == name), 'output_required_or_fixed')
    return store(root, name, value, P, D)


def check_adoption(root, project, catalog, decision, P):
    """A direct DMA handoff can arrive after standalone discovery. Retain both baselines."""
    D = P.routing_helper('dma_topics')
    prior = latest(root, P, D)
    if prior is None:
        return
    route = current_route(root, project, prior, P, D)
    # A semantic review alone cannot prove the live branch; record the owner's comparison.
    need(decision, 'record_late_dma_reconciliation')
    record = D.read(root, decision, P)[0]
    D.context(record.get('destination'))
    need(record.get('role') == 'user' and D.text(record.get('reference')) and D.text(record.get('response_text'))
         and record.get('route') == prior and record.get('handoff_sha256') == catalog['source']['original_sha256']
         and record.get('prior_context') == route['context'] and record.get('action') == 'adopt_dma'
         and D.strings(record.get('topics'), 16) and record['topics']
         and set(record['topics']) <= {row['id'] for row in catalog['topics']}, 'late_dma_decision_mismatch')
    return D.pin(root, decision, P)
