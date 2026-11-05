"""Bind governed DMA Topics to scoped workbook queries using retained, read-only evidence."""
import importlib.util
from functools import lru_cache
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path


POLICY = 'selected-topic-v1'
SURFACES = {'app', 'dashboard'}
PEER = Path(__file__).resolve().parents[2] / 'omni-backend-handoff' / 'scripts'


@lru_cache(maxsize=3)
def peer(name):
    need(name in ('continuation','standalone','cowork'), 'invalid_peer')
    path = PEER / (name + '.py')
    spec = importlib.util.spec_from_file_location('dma_topics_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def need(ok, why):
    if not ok:
        raise ValueError('dma_topics.' + why)


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048 and all(ord(c) >= 32 for c in value)


def strings(value, limit):
    return isinstance(value, list) and len(value) <= limit and all(text(v) for v in value) and len(set(value)) == len(value)


def bound(project, root=None):
    markers = ('dma_import','dma_continuation','dma_continuation_selection','dma_topic_policy')
    return bool(SURFACES.intersection(project.get('surfaces',[]))) and (
        any(k in project for k in markers) or any(r.get('id','').startswith('dma-catalog') for r in project['sources'])
        or root is not None and (Path(root)/'continuation-receipt.json').is_file())


def read(root, path, P):
    return P.read_json(P.relative_file(root, path))


def pin(root, path, P):
    return {'path':path, 'sha256':P.digest(P.read_bytes(P.relative_file(root, path)))}


def evidence(root, record, P, *, json=True):
    need(isinstance(record, dict) and set(record) == {'path','sha256'}, 'file_pin_required')
    raw = P.read_bytes(P.relative_file(root, record['path']))
    need(P.digest(raw) == record['sha256'], 'evidence_changed')
    if not json:
        need(bool(raw), 'empty_evidence')
        return None
    value, again = read(root, record['path'], P)
    need(raw == again, 'evidence_changed')
    need(isinstance(value,dict), 'structured_evidence_object_required')
    return value


def same(a, b, P):
    return P.canonical(a) == P.canonical(b)


def current(root, project, P):
    """Follow the selected exchange/catalog and validate its original producer bytes."""
    selection = peer('continuation').project_selection(root) if (
        'dma_continuation' in project or 'dma_continuation_selection' in project
        or (root/'continuation-receipt.json').is_file()) else None
    imported = project.get('dma_import')
    if not imported:
        return selection, None, None
    path = imported['catalog_path']
    if imported.get('exchange_id') is not None:
        peer('cowork').select(root,imported['exchange_id'],verify_only=True)
    else:
        need(path == 'inputs/dma-catalog.json' and not project.get('cowork_history'), 'selected_exchange_required')
        if selection and selection.get('semantic_review'):
            review = selection['semantic_review']
            need(imported['original_sha256'] == review['sha256'] and
                 (root / review['path']) == Path(imported['original_path']), 'continuation_semantic_review_changed')
    saved, raw = read(root, path, P)
    file = {'path':path,'sha256':P.digest(raw)}
    need(any(all(r.get(k) == v for k,v in file.items()) for r in project['sources']), 'catalog_registration_changed')
    rebuilt = P.validation_helper().derive(('dma_catalog_rebuild_v1',str(root),file['sha256'],imported['original_sha256']),
        lambda: P.dma_catalog(imported['original_path']))
    need(imported['original_sha256'] == rebuilt['source']['original_sha256'] and same(saved, rebuilt, P),
         'catalog_or_handoff_changed')
    return selection, file, saved


def context(value):
    fields = {'base_url','model_id','branch_id','workbook_model_id','principal_id'}
    need(isinstance(value, dict) and fields <= set(value) <= fields | {'model_version_id'}, 'context_required')
    peer('continuation')._destination({k:value[k] for k in ('base_url','model_id','branch_id')})
    need(text(value['principal_id']) and all(value.get(k) is None or text(value[k])
         for k in ('branch_id','workbook_model_id','model_version_id')), 'invalid_context')
    ids = [value[k] for k in ('model_id','branch_id','workbook_model_id') if value[k] is not None]
    need(len(set(ids)) == len(ids), 'distinct_model_identities_required')
    return value


def timestamp(value):
    need(text(value), 'observation_timestamp_required')
    try:
        result = datetime.fromisoformat(value.replace('Z','+00:00'))
        need(result.tzinfo is not None, 'observation_timezone_required')
        return result
    except (TypeError, ValueError):
        raise ValueError('dma_topics.invalid_timestamp') from None


def check_models(models,ctx,version_model_id=None):
    need(isinstance(models,dict) and all(isinstance(row,dict) for row in models.values()), 'model_records_required')
    shared = models.get(ctx['model_id'], {})
    need(shared.get('id') == ctx['model_id'] and shared.get('modelKind') in ('SHARED','SHARED_EXTENSION')
         and shared.get('deletedAt') is None and text(shared.get('connectionId')), 'shared_model_not_observed')
    for key, kind, base in [('branch_id','BRANCH',ctx['model_id']), ('workbook_model_id','WORKBOOK',ctx['branch_id'] or ctx['model_id'])]:
        if ctx[key] is None:
            continue
        row = models.get(ctx[key], {})
        need(row.get('id') == ctx[key] and row.get('modelKind') == kind and row.get('baseModelId') == base
             and row.get('deletedAt') is None and row.get('connectionId') in (None,shared['connectionId']),
             'model_ancestry_changed')
    effective = ctx['workbook_model_id'] or ctx['branch_id'] or ctx['model_id']
    if ctx.get('model_version_id') is not None:
        need(models.get(version_model_id or effective,{}).get('modelVersionId') == ctx['model_version_id'],
             'model_version_not_observed')


def check_execution_result(result, scope, query, P):
    need(result.get('kind') == 'omni_topic_trial_result' and result.get('status') == 'complete'
         and all(result.get(k) == v for k,v in scope.items())
         and result.get('query_sha256') == P.digest(P.canonical(query))
         and strings(result.get('columns'),256) and set(query['fields']) <= set(result['columns'])
         and isinstance(result.get('rows'),list) and all(isinstance(r,dict) and set(result['columns']) <= set(r)
             for r in result['rows']), 'scoped_trial_result_changed')


def check_observation(root, o, ctx, review_hash, topics, P):
    need(isinstance(o, dict) and o.get('kind') == 'dma_topic_observation' and type(o.get('schema_version')) is int and o['schema_version'] == 1
         and o.get('context') == ctx and o.get('review_sha256') == review_hash, 'observation_scope_changed')
    observed = timestamp(o.get('observed_at'))
    need(observed <= datetime.now(timezone.utc), 'observation_in_future')
    if o.get('valid_until') is not None:
        need(datetime.now(timezone.utc) < timestamp(o['valid_until']), 'observation_expired')
    identity = evidence(root, o['identity'], P)
    need(identity.get('keyScope') == 'user' and isinstance(identity.get('user'),dict) and identity['user'].get('membershipId') == ctx['principal_id']
         and isinstance(identity.get('rolesByModel'),dict) and isinstance(identity['rolesByModel'].get(ctx['model_id']),dict), 'intended_model_user_not_observed')
    models = evidence(root, o['models'], P)
    check_models(models,ctx)
    effective = ctx['workbook_model_id'] or ctx['branch_id'] or ctx['model_id']
    snapshots = {}
    need(isinstance(o.get('topics'),dict) and set(o['topics']) == set(topics), 'topic_readback_scope')
    need(isinstance(o.get('trials'),dict) and set(o['trials']) == set(topics), 'topic_access_trials_required')
    for name in topics:
        # The envelope is an attributed acquisition record, not host authentication.
        capture = evidence(root, o['topics'][name], P)
        need(capture.get('context') == ctx and capture.get('effective_model_id') == effective
             and capture.get('topic_name') == name, 'topic_capture_context_changed')
        response = capture.get('response', {})
        need(isinstance(response,dict), 'topic_response_object_required')
        peer('standalone').semantic_definitions({'topics':{name:response}},
              [{'topic':name,'field_ids':[], 'query_key':None,'query':{}}])
        trial = evidence(root, o['trials'][name], P)
        need(trial.get('context') == ctx and trial.get('effective_model_id') == effective
             and trial.get('status') == 'succeeded' and text(trial.get('query_ref'))
             and trial.get('topic') == name, 'scoped_access_trial_required')
        result = evidence(root, trial['result'], P)
        fields = semantic_fields(trial['query'], name)
        check_execution_result(result,{k:trial[k] for k in ('context','effective_model_id','topic','query_ref')},
                               trial['query'],P)
        peer('standalone').semantic_definitions({'topics':{name:response}},
              [{'topic':name,'field_ids':fields,'query_key':None,'query':trial['query']}])
        snapshots[name] = response
    return snapshots


def access_value(root, project, source, P):
    return P.validation_helper().derive(('dma_topic_access_v1',str(root),source['path'],source['sha256'],
            P.digest(P.canonical(project))), lambda: _access_value(root, project, source, P))


def _access_value(root, project, source, P):
    spec = evidence(root, source, P)
    need(type(spec.get('schema_version')) is int and spec['schema_version'] == 1 and spec.get('kind') == 'dma_topic_selection', 'selection_spec_required')
    selection, catalog_pin, catalog = current(root, project, P)
    candidates = {row['id']:row for row in catalog['topics']} if catalog else {}
    chosen = spec.get('topics', [])
    need(strings(chosen,16), 'selected_topic_names')
    inherited = selection['topic_names'] if selection else []
    ctx = context(spec['context']) if spec.get('context') is not None else None
    if inherited:
        need(not chosen or set(chosen) == set(inherited), 'continuation_topic_conflict')
        chosen = inherited
    elif chosen:
        choice = evidence(root, spec['selection_evidence'], P)
        need(choice.get('kind') == 'dma_topic_choice' and choice.get('role') == 'user' and text(choice.get('reference'))
             and text(choice.get('request_text')) and strings(choice.get('topics'),16) and set(choice['topics']) == set(chosen)
             and strings(choice.get('surfaces'),2) and set(choice['surfaces']) == set(project['surfaces'])
             and choice.get('destination') == ({k:ctx[k] for k in ('base_url','model_id','branch_id')} if ctx else None),
             'explicit_topic_choice_mismatch')
    elif len(candidates) == 1:
        chosen = list(candidates)
    if catalog:
        need(set(chosen) <= set(candidates), 'topic_outside_catalog')
    target = selection.get('destination') if selection else None
    if target and ctx:
        need(all(ctx.get(k) == v for k,v in target.items()), 'continuation_destination_conflict')
    alternatives = spec.get('alternative_topics', [])
    need(strings(alternatives,16) and not set(alternatives).intersection(chosen), 'alternate_scope_invalid')
    observation = spec.get('observation')
    snapshots = {}
    handoff = catalog['source']['original_sha256'] if catalog else None
    connection_id = None
    if observation is not None:
        need(bool(ctx and catalog and chosen), 'resolve_selection_before_observation')
        acquired = evidence(root, observation, P)
        snapshots = check_observation(root, acquired, ctx, handoff, [*chosen,*alternatives], P)
        connection_id = evidence(root,acquired['models'],P)[ctx['model_id']]['connectionId']
        for name in chosen:
            need(candidates[name].get('base_view') == snapshots[name]['topic'].get('base_view_name'),
                 'candidate_base_view_changed')
    return {'kind':'dma_topic_access','schema_version':1,'project_id':project['id'],'surfaces':project['surfaces'],
            'source':source,'catalog':catalog_pin,'review_sha256':handoff,'topics':chosen,'context':ctx,
            'continuation':selection.get('packet') if selection else None,
            'native_validation':selection.get('native_validation') if selection else None,
            'observation':observation,'connection_id':connection_id,
            'topic_versions':{k:{key:val for key,val in v['topic'].items() if key in ('id','revision','version','versionId','modelVersionId')
                                   and type(val) in (str,int)} for k,v in snapshots.items()},
            'topic_hashes':{k:P.digest(P.canonical(v)) for k,v in snapshots.items()},
            'status':'observed_from_supplied_evidence' if snapshots else 'pending',
            'needs_selection':not bool(chosen), 'origin_authenticated':False}, snapshots, catalog


def checked_access(root, project, record, P):
    saved = evidence(root, record, P)
    rebuilt, snapshots, catalog = access_value(root, project, saved['source'], P)
    need(same(saved, rebuilt, P), 'access_binding_changed')
    return rebuilt, snapshots, catalog


def semantic_fields(query, topic):
    need(isinstance(query,dict), 'semantic_query_required')
    plain = dict(query)
    need(plain.pop('join_paths_from_topic_name',topic) == topic and plain.pop('userEditedSQL','') == '',
         'query_topic_or_sql_conflict')
    need(text(plain.get('table')), 'semantic_base_required')
    fields = peer('standalone').query_fields(plain)
    for condition in plain.get('filters',{}).values():
        need(isinstance(condition,dict) and set(condition) <= {'kind','type','values','is_negative','isNegative'}
             and text(condition.get('kind')) and text(condition.get('type'))
             and all(type(condition[k]) is bool for k in ('is_negative','isNegative') if k in condition)
             and isinstance(condition.get('values',[]),list) and all(type(v) in (str,int,float,bool) or v is None
                 for v in condition.get('values',[])), 'unsupported_filter_shape')
        need(condition['kind'].upper() in {'EQUALS','NOT_EQUALS','IN','NOT_IN','GREATER_THAN','LESS_THAN','BETWEEN',
                                           'IS_NULL','IS_NOT_NULL','CONTAINS','STARTS_WITH','ENDS_WITH'}, 'unsupported_filter_kind')
    return fields


def tile_fields(tile):
    known = {'aiConfig','automaticVis','description','filterOrder','isSql','is_sql','name','prefersChart','query',
             'resultConfig','sourceQueryPresentationKey','subTitle','topicName','type','visConfig','queryType','query_type',
             'userEditedSQL'}
    need(isinstance(tile, dict) and set(tile) <= known and tile.get('type') == 'query' and tile.get('isSql',False) is False
         and tile.get('userEditedSQL','') == ''
         and tile.get('is_sql',False) is False and tile.get('sourceQueryPresentationKey') is None
         and not {'sql','rawSql','raw_sql','sourceDocumentId','modelId','branchId','model_id','branch_id'}.intersection(tile),
         'unsupported_query_source')
    need(all(isinstance(tile[k],str) and tile[k].upper() == 'TOPIC' for k in ('queryType','query_type') if k in tile),
         'unsupported_query_discriminator')
    need(text(tile.get('topicName')), 'topic_name_required')
    return semantic_fields(tile.get('query'), tile['topicName'])


def check_kinds(catalog,name,definitions):
    declared = {f['id']:f for f in catalog['dictionary'] if f.get('topic') == name}
    for field,native in definitions.items():
        original = declared.get(field)
        if original is None:
            continue  # Timeframe selectors still require explicit catalog selection and exact native membership.
        kind = original.get('kind')
        need(kind == {'dimensions':'dimension','measures':'measure','filter_only_fields':'filter_only_field'}.get(native['kind']),
             'candidate_native_field_kind_changed')
        aggregate = native['definition'].get('aggregate_type')
        if kind == 'measure' and original.get('aggregate_type') and aggregate:
            need(str(aggregate).lower() == str(original['aggregate_type']).lower(), 'candidate_native_aggregate_changed')


def candidate_fields(catalog,name):
    allowed = {f['id'] for f in catalog['dictionary'] if f.get('topic') == name and f.get('selected_for_query') is True}
    scope = next(t for t in catalog['topics'] if t['id'] == name).get('scope',{})
    allowed.update(scope.get('selections',{}).get('fields',[]) if isinstance(scope,dict) else [])
    return allowed


def query_identity(row):
    return (row['surface'],row['document_id'],row['query_key'])


def gap_spec(project, rows, route, access, source, P):
    requests = [r for r in rows if r['disposition'] == 'request']
    if not requests:
        return None
    if route is None:
        route = {'route':'reuse_existing','route_reference':'clarify_missing_binding','source_platform':'omni'}
    need(isinstance(route,dict) and {'source_platform','route','route_reference'} <= set(route) <=
         {'source_platform','route','route_reference','migration_scope_path','source_inventory_paths'}
         and text(route['route_reference']), 'backend_route_decision_required')
    stamp = P.digest(P.canonical([project['id'],access['catalog'],access['review_sha256'],source,requests,route]))[:20]
    return {'kind':'analyst_backend_request_spec','schema_version':1,'request_id':'topic-gap-'+stamp,
            **route,'requirements':[{'id':r['consumer_id'],'question':r['question'],
            'change_class':r.get('change_class','binding'),'frontend_asset_ids':[r.get('asset_id',r['consumer_id'])], 'metric_ids':r['fields'],
            'grain':r['grain'],'population':r['population'],'access_case':r['access_case'],'original_expectation':r['expectation'],
            'expected_cases':[{'case_id':r['consumer_id']+'-source','expectation':r['expectation_text']}]} for r in requests],
            'consumer_bindings':[{'asset_id':r.get('asset_id',r['consumer_id']),'topic_ids':[r['topic']], 'field_ids':r['fields'],
                                  'dependency_complete':False} for r in requests]}


def plan_value(root, project, source, P, prior=None):
    return P.validation_helper().derive(('dma_topic_plan_v1',str(root),source['path'],source['sha256'],
        P.digest(P.canonical(project)),P.digest(P.canonical(prior))), lambda: _plan_value(root,project,source,P,prior))


def _plan_value(root, project, source, P, prior):
    spec = evidence(root, source, P)
    need(spec.get('kind') == 'dma_topic_consumer_plan' and type(spec.get('schema_version')) is int and spec['schema_version'] == 1, 'queries_spec_required')
    if prior:
        need(spec.get('access') == prior, 'stage_a_binding_changed')
    access, topics, catalog = checked_access(root, project, spec['access'], P)
    consumers = spec.get('consumers')
    need(isinstance(consumers,list) and 0 < len(consumers) <= 256, 'consumer_inventory_required')
    index, entries, ids, active = {}, [], set(), []
    for row in consumers:
        need(isinstance(row,dict) and row.get('surface') in project['surfaces'] and row['surface'] in SURFACES
             and all(text(row.get(k)) for k in ('consumer_id','document_id','question','grain','population','access_case',
                                                 'expectation_text','topic')), 'consumer_scope_required')
        need(row['consumer_id'] not in ids, 'duplicate_consumer')
        ids.add(row['consumer_id'])
        evidence(root, row['expectation'], P, json=False)
        action = row.get('disposition')
        if action in ('request','defer'):
            need(row['topic'] in access['topics'] and strings(row.get('fields'),128) and text(row.get('reason'))
                 and row.get('query_key') is None and row.get('tile') is None, 'gap_must_remain_unbound')
            entries.append({k:row[k] for k in ('consumer_id','document_id','surface','disposition','reason')})
            continue
        need(action in ('new','reuse','exception') and text(row.get('query_key')) and topics,
             'observed_topic_required_before_query_binding')
        tile = row['tile']
        fields = tile_fields(tile)
        name = row['topic']
        need(tile['topicName'] == name and name in topics, 'query_outside_observed_topics')
        if action != 'reuse':
            need(tile['query'].get('join_paths_from_topic_name') == name, 'explicit_query_topic_required')
        if action == 'exception':
            decision = evidence(root, row['decision'], P)
            need(name not in access['topics'] and decision.get('kind') == 'dma_topic_exception'
                 and all(decision.get(k) == row[k] for k in ('consumer_id','surface','document_id','query_key','topic'))
                 and decision.get('access') == spec['access'] and decision.get('query_sha256') == P.digest(P.canonical(tile['query']))
                 and text(decision.get('reason')), 'exception_scope_changed')
            actual = evidence(root, decision['user_decision'], P)
            need(actual.get('role') == 'user' and text(actual.get('reference')) and text(actual.get('response_text'))
                 and all(actual.get(k) == decision[k] for k in ('consumer_id','surface','document_id','query_key','topic','access','query_sha256')),
                 'attributable_scoped_user_decision_required')
        else:
            need(name in access['topics'], 'query_outside_selected_topics')
            need(set(fields) <= candidate_fields(catalog,name), 'field_outside_dma_candidate')
        definitions = peer('standalone').semantic_definitions({'topics':{name:topics[name]}},
                [{'topic':name,'field_ids':fields,'query_key':row['query_key'],'query':tile['query']}])
        if action != 'exception':
            check_kinds(catalog,name,definitions[0]['fields'])
        if action == 'reuse':
            saved = evidence(root, row['saved_query'], P)
            need(saved.get('context') == access['context'] and saved.get('document_id') == row['document_id']
                 and saved.get('query_key') == row['query_key'] and saved.get('tile') == tile, 'existing_query_changed')
            if 'join_paths_from_topic_name' not in tile['query']:
                ctx = access['context']
                need(text(saved.get('query_ref')) and saved.get('result') is not None,
                     'saved_topic_execution_required')
                scope = {'context':ctx,'effective_model_id':ctx['workbook_model_id'] or ctx['branch_id'] or ctx['model_id'],
                         'topic':name,'query_ref':saved['query_ref'],'document_id':row['document_id'],'query_key':row['query_key']}
                check_execution_result(evidence(root,saved['result'],P),scope,tile['query'],P)
        key = query_identity(row)
        core = {'topic':name, 'query':tile['query']}
        need(key not in index or same(index[key],core,P), 'conflicting_consumers_for_saved_key')
        index[key] = core
        active.append(row)
        entries.append({k:row[k] for k in ('consumer_id','document_id','surface','query_key','topic','disposition')})
    controls = spec.get('controls',[])
    need(isinstance(controls,list) and len(controls) <= 128, 'control_inventory')
    seen = set()
    for ctrl in controls:
        need(isinstance(ctrl,dict),'control_object_required')
        key = (ctrl.get('surface'),ctrl.get('document_id'),ctrl.get('control_key'))
        need(all(text(v) for v in key) and key not in seen and strings(ctrl.get('query_keys'),48) and ctrl['query_keys'],
             'control_scope')
        seen.add(key)
        refs = ctrl.get('field_bindings')
        need(isinstance(refs,list) and 0 < len(refs) <= 128 and all(isinstance(r,dict) for r in refs), 'control_fields')
        if key[0] == 'app':
            cfg = ctrl['config']
            need(isinstance(cfg,dict) and set(cfg.get('query_keys',[])) == set(ctrl['query_keys'])
                 and set(cfg.get('field_ids',[])) == {r['field_id'] for r in refs}
                 and all(r['topic'] == cfg.get('topic') for r in refs), 'app_control_runtime_scope')
        else:
            scope = peer('standalone').pointer(ctrl['config'],ctrl['scope_pointer'])
            need(strings(scope,48) and set(scope) == set(ctrl['query_keys']), 'dashboard_control_saved_scope_changed')
        for ref in refs:
            topic, field = ref['topic'], ref['field_id']
            need(topic in topics and all(index.get((*key[:2],q),{}).get('topic') == topic for q in ctrl['query_keys'])
                 and peer('standalone').pointer(ctrl['config'], ref['pointer']) == field, 'control_binding_changed')
            if topic in access['topics']:
                need(field in candidate_fields(catalog,topic), 'control_field_outside_candidate')
            definitions = peer('standalone').semantic_definitions({'topics':{topic:topics[topic]}},
                        [{'topic':topic,'field_ids':[field],'query_key':None,'query':{}}])
            if topic in access['topics']:
                check_kinds(catalog,topic,definitions[0]['fields'])
    result = {'kind':'dma_topic_queries','schema_version':1,'source':source,'access':spec['access'],
              'consumers':entries,'backend_request':gap_spec(project, consumers, spec.get('backend'), access, source, P), 'native_verified':False}
    if result['backend_request']:
        peer('cowork').check_spec(result['backend_request'])
    return result, access, topics, active, controls


def small_pin(record):
    return {k:record[k] for k in ('path','sha256')}


def check_stage(root, project, stage, payload, P, access_event=None):
    if not bound(project, root) or stage not in ('access','analysis'):
        return
    if stage == 'access':
        a, _, _ = checked_access(root, project, small_pin(payload['evidence']['data']), P)
        if a['context']:
            need(payload['user_identity'] == a['context']['principal_id'], 'stage_a_principal_changed')
        if a['observation']:
            need(a['observation'] == small_pin(payload['evidence']['user_access']), 'stage_a_observation_changed')
    else:
        prior = small_pin(access_event['payload']['evidence']['data'])
        saved = evidence(root, small_pin(payload['evidence']['queries']), P)
        actual = plan_value(root, project, saved['source'], P, prior)[0]
        need(same(saved, actual, P), 'stage_b_plan_changed')


def prepare(root, P, request, output, analysis=False):
    root, project = P.load_project(root)
    need(bound(project, root), 'dma_engagement_required')
    with P.validation_operation(root):
        ref = pin(root, request, P)
        result = plan_value(root, project, ref, P)[0] if analysis else access_value(root, project, ref, P)[0]
    P.write_json(P.no_links(root / safe_output(output)), result)
    return pin(root, output, P)


def safe_output(path):
    p = Path(path)
    need(not p.is_absolute() and p.as_posix() == path and '..' not in p.parts and '\\' not in path,
         'private_relative_output_required')
    return p


def stage_inputs(root, project, P):
    gate = P.stage_status(root)
    bindings = gate.get('stage_bindings',{})
    need('access' in bindings and 'analysis' in bindings, 'complete_current_access_and_analysis_first')
    journal, _ = read(root,'stage-gates.json',P)
    by_hash = {e['sha256']:e for e in journal['events']}
    return (small_pin(by_hash[bindings['access']]['payload']['evidence']['data']),
            small_pin(by_hash[bindings['analysis']]['payload']['evidence']['queries']))


def guard(root, P, *, surface, document_id, context, presentations, controls=None, snapshot=None, readback=False, app_html=None):
    if root is None or not (Path(root) / 'project.json').exists():
        return None
    root, project = P.load_project(root)
    if not bound(project, root):
        return None
    if P.validation_helper().active() is None:
        with P.validation_operation(root):
            return guard(root, P, surface=surface, document_id=document_id, context=context, presentations=presentations,
                         controls=controls, snapshot=snapshot, readback=readback, app_html=app_html)
    access_pin, query_pin = stage_inputs(root, project, P)
    saved = evidence(root, query_pin, P)
    result, access, topics, active, ctrl_plan = plan_value(root, project, saved['source'], P, access_pin)
    need(same(saved, result, P) and access['status'] == 'observed_from_supplied_evidence', 'verified_topic_plan_required')
    ctx = access['context']
    need(surface in SURFACES and surface in project['surfaces'] and text(document_id), 'surface_document_mismatch')
    need(isinstance(context, dict) and {'base_url','model_id','branch_id'} <= set(context)
         and set(context) <= set(ctx), 'native_target_required')
    for key in context:
        if key == 'workbook_model_id' and ctx[key] is None:
            continue
        need(context[key] == ctx[key], 'native_context_changed_' + key)
    if readback:
        need(text(context.get('principal_id')) and text(context.get('workbook_model_id')), 'effective_readback_context_required')
    need(isinstance(presentations,dict) and isinstance(presentations.get('data'),dict)
         and strings(presentations.get('order'),128) and set(presentations['order']) == set(presentations['data']),
         'complete_saved_presentation_inventory_required')
    planned = {r['query_key']:r for r in active if r['surface'] == surface and r['document_id'] == document_id}
    need(planned, 'no_supported_queries_for_document')
    seen = set()
    for key,tile in presentations['data'].items():
        if isinstance(tile,dict) and tile.get('type') in ('text','markdown') and tile.get('query') is None:
            need(key not in planned and set(tile) <= {'type','name','description','markdown','text','query','isSql'}
                 and tile.get('isSql',False) is False, 'unexpected_inert_tile_source')
            continue
        tile_fields(tile)
        row = planned.get(key)
        need(row is not None and tile['topicName'] == row['topic'] and same(row['tile']['query'],tile['query'],P),
             'saved_query_differs_from_selected_topic_plan')
        seen.add(key)
    need(seen == set(planned), 'planned_query_missing')
    expected_controls = {c['control_key']:c['config'] for c in ctrl_plan if c['surface'] == surface and c['document_id'] == document_id}
    panel_binding = None
    if surface == 'app' and (readback or app_html is not None):
        need(isinstance(app_html,str), 'current_app_html_required')
        panel_binding, declared_controls = validate_panels(root,P,app_html,document_id,access_pin,query_pin,active,expected_controls)
        if controls is None:
            controls = declared_controls
    actual_controls = {} if controls is None else controls
    need(isinstance(actual_controls,dict), 'invalid_native_controls')
    if 'data' in actual_controls:
        need(strings(actual_controls.get('order'),128) and set(actual_controls['order']) == set(actual_controls['data']),
             'incomplete_control_inventory')
        actual_controls = actual_controls['data']
    need(same(actual_controls,expected_controls,P), 'control_scope_changed')
    wb = context.get('workbook_model_id')
    if readback or (wb and wb != ctx['workbook_model_id']):
        need(isinstance(snapshot,dict) and snapshot.get('draft_context',{}).get('workbookModelId') == wb,
             'verify_current_workbook_ancestry_and_topics')
    if snapshot is not None:
        target = snapshot.get('target',{})
        need(all(k in target and target[k] == ctx[k] for k in ('base_url','model_id','branch_id','principal_id'))
             and target.get('document_id') == document_id
             and snapshot.get('identity',{}).get('keyScope') == 'user'
             and snapshot['identity'].get('user',{}).get('membershipId') == ctx['principal_id']
             and ctx['model_id'] in snapshot['identity'].get('rolesByModel',{}), 'snapshot_identity_or_context_changed')
        original_model = ctx['workbook_model_id'] or ctx['branch_id'] or ctx['model_id']
        check_models(snapshot['models'],{**ctx,'workbook_model_id':wb},version_model_id=original_model)
        need(snapshot['models'][ctx['model_id']]['connectionId'] == access['connection_id'], 'native_connection_changed')
        current_topics = snapshot.get('topics',{})
        for name in {row['topic'] for row in planned.values()}:
            need(isinstance(current_topics,dict) and isinstance(current_topics.get(name),dict) and same(current_topics[name].get('topic'),topics[name]['topic'],P), 'live_topic_definition_changed')
    return {'policy':POLICY,'surface':surface,'document_id':document_id,
            'access_sha256':access_pin['sha256'],'queries_sha256':query_pin['sha256'],
            **({'panel_mapping_sha256':panel_binding['sha256']} if panel_binding else {})}


class AppElements(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids = []
        self.scripts = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for key,value in attrs if key == 'id')
        if tag == 'script':
            values = dict(attrs)
            if 'src' not in values and values.get('type','') in ('','module','text/javascript','application/javascript'):
                self.script = ''

    def handle_data(self, data):
        if self.script is not None:
            self.script += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            self.scripts.append(self.script)
            self.script = None


def panel_path(html_hash, document_id, P):
    return 'contracts/dma-panels-' + P.digest(P.canonical([document_id,html_hash])) + '.json'


def inspect_panels(html, spec, document, access, queries, active, expected_controls, P):
    need(isinstance(html,str) and 0 < len(html.encode()) <= 2*1024*1024, 'bounded_app_source_required')
    need(spec.get('kind') == 'dma_topic_panels' and spec.get('document_id') == document
         and spec.get('access') == access and spec.get('queries') == queries
         and spec.get('html_sha256') == P.digest(html.encode()), 'panel_candidate_or_plan_changed')
    selected = {r['consumer_id']:r for r in active if r['surface'] == 'app' and r['document_id'] == document}
    rows = spec.get('panels')
    need(selected and isinstance(rows,list) and len(rows) == len(selected), 'panel_inventory_incomplete')
    parsed = AppElements()
    parsed.feed(html)
    parsed.close()
    seen, elements = set(), set()
    for row in rows:
        cid = row['consumer_id']
        element, key, fragment = row['element_id'], row['query_key'], row['script_fragment']
        need(cid in selected and cid not in seen and selected[cid]['query_key'] == key
             and text(element) and element not in elements and parsed.ids.count(element) == 1, 'panel_query_identity_changed')
        need(isinstance(fragment,str) and 0 < len(fragment) <= 4096 and sum(code.count(fragment) for code in parsed.scripts) == 1
             and all(any(q + v + q in fragment for q in ('"',"'")) for v in (element,key)),
             'panel_runtime_fragment_missing')
        seen.add(cid)
        elements.add(element)
    controls = {}
    for row in spec.get('controls',[]):
        key, element, frag = row['control_key'], row['element_id'], row['script_fragment']
        need(key not in controls and key in expected_controls and parsed.ids.count(element) == 1
             and isinstance(frag,str) and 0 < len(frag) <= 4096 and sum(code.count(frag) for code in parsed.scripts) == 1
             and all(any(q + val + q in frag for q in ('"',"'")) for val in [element,*expected_controls[key]['query_keys']]),
             'app_control_source_mapping_changed')
        controls[key] = expected_controls[key]
    return controls


def validate_panels(root,P,html,document,access,queries,active,expected_controls):
    path = panel_path(P.digest(html.encode()),document,P)
    need((root/path).is_file(), 'panel_mapping_required_for_candidate')
    record, raw = read(root,path,P)
    controls = inspect_panels(html,record,document,access,queries,active,expected_controls,P)
    return {'path':path,'sha256':P.digest(raw)}, controls


def prepare_panels(root,P,request):
    root, project = P.load_project(root)
    with P.validation_operation(root):
        access, queries = stage_inputs(root,project,P)
        saved = evidence(root,queries,P)
        rebuilt, _, _, active, controls = plan_value(root,project,saved['source'],P,access)
        need(same(saved,rebuilt,P), 'panel_plan_changed')
        spec = read(root,request,P)[0]
        raw = P.read_bytes(P.relative_file(root,spec['html_path']))
        record = {**spec,'access':access,'queries':queries,'html_sha256':P.digest(raw)}
        expected = {c['control_key']:c['config'] for c in controls if c['surface']=='app' and c['document_id']==spec['document_id']}
        inspect_panels(raw.decode('utf-8'),record,spec['document_id'],access,queries,active,expected,P)
        path = panel_path(record['html_sha256'],spec['document_id'],P)
    if (root/path).exists():
        need(same(read(root,path,P)[0],record,P), 'panel_mapping_conflict')
    else:
        P.write_json(P.no_links(root/path),record)
    return pin(root,path,P)


def packet_context(root, project, role, stage, scope_ids, P):
    """Compact references only; no report/SQL/readback payload fan-out."""
    if not bound(project, root) or role not in ('data-analyst','bi-engineer','app-engineer','dashboard-designer',
                                          'qa-analyst','backend-handoff','product-owner','data-storyteller'):
        return None
    stages = stage.get('stage_bindings',{})
    journal = read(root,'stage-gates.json',P)[0] if (root/'stage-gates.json').is_file() else {'events':[]}
    index = {e['sha256']:e for e in journal['events']}
    refs = {}
    for stage,field in [('access','data'),('analysis','queries')]:
        if stages.get(stage) in index:
            refs[stage] = small_pin(index[stages[stage]]['payload']['evidence'][field])
    result = {'policy':POLICY,'evidence':refs,'status':'pending'}
    if 'access' in refs:
        access = evidence(root,refs['access'],P)
        if access.get('kind') == 'dma_topic_access':
            result.update(status=access['status'],topics=access['topics'],catalog=access['catalog'])
    if 'analysis' in refs:
        plan = evidence(root,refs['analysis'],P)
        if plan.get('kind') == 'dma_topic_queries':
            selected = [r for r in plan['consumers'] if role not in ('app-engineer','dashboard-designer')
                        or r['surface'] == ('app' if role == 'app-engineer' else 'dashboard')]
            if scope_ids is not None:
                selected = [r for r in selected if r['consumer_id'] in scope_ids]
            result['consumer_ids'] = [r['consumer_id'] for r in selected]
            result['blocked'] = [r['consumer_id'] for r in selected if r['disposition'] in ('request','defer')]
    return result


def prepare_gap(root, P, analysis_path, output):
    """Emit a minimal versioned request via the existing backend exchange, with safe retry."""
    root, project = P.load_project(root)
    with P.validation_operation(root):
        a, b = stage_inputs(root,project,P)
        need(pin(root,analysis_path,P) == b, 'current_stage_b_receipt_required')
        receipt = evidence(root,b,P)
        rebuilt = plan_value(root,project,receipt['source'],P,a)[0]
        need(same(receipt,rebuilt,P) and rebuilt['backend_request'], 'no_current_backend_gap')
        spec = rebuilt['backend_request']
    path = P.no_links(root / safe_output(output))
    if path.exists():
        need(same(read(root,output,P)[0],spec,P),'request_spec_changed')
    else:
        P.write_json(path,spec)
    cw = peer('cowork')
    request = 'requests/' + spec['request_id'] + '.json'
    if (root / request).exists():
        value,_ = cw.local_request(root,project,request)
        need(value['spec_path'] == output and same(value['spec'],spec,P),'request_identity_conflict')
        return {'status':'request_reused','request_id':spec['request_id'],'path':request,'dispatch_status':'not_dispatched'}
    return cw.create_request(root,output,[output])
