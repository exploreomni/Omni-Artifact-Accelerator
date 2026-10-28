"""Passive Metabase projection and state-bound comparison. No source execution.

The supported query subset yields analytical requirements, not compiled Omni SQL.
Original definitions remain authoritative evidence even when interpretation fails.
"""
import copy
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def module(name):
    need(name in ('metabase_capture', 'powerbi_capture_files', 'powerbi_visual'), 'module_not_allowed')
    spec = importlib.util.spec_from_file_location('metabase_visual_' + name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def need(value, code):
    if not value:
        raise ValueError('metabase.' + code)


def validate_snapshot(value):
    return module('metabase_capture').validate_snapshot(value)


def validate_capture(value):
    return module('metabase_capture').validate_envelope(value)


def verify_capture_files(value, root):
    return module('metabase_capture').verify_capture_files(value, root)


def positive(value):
    return type(value) is int and value > 0


def question_analysis(query):
    """Conservative single-stage MBQL interpretation; never drop a clause."""
    output = {'status': 'needs_review', 'language': 'unknown', 'original': copy.deepcopy(query),
              'reasons': [], 'dependencies': [], 'execution_performed': False, 'target_compiled': False}
    if type(query) is not dict:
        output['reasons'] = ['missing_query_definition']
        return output
    output['dependencies'] = [{'kind': 'card', 'id': item, 'status': 'declared'} for item in
                              sorted(module('metabase_capture').card_references({}, [{'dataset_query': query}]))]
    if query.get('type') == 'native' or 'native' in query:
        output.update(language='native', reasons=['native_query_requires_semantic_review'])
        native = query.get('native', {})
        if type(native) is dict:
            output['template_tags'] = copy.deepcopy(native.get('template-tags', {}))
        return output
    output['language'] = 'mbql'
    if 'stages' in query:
        stages = query['stages']
        # Modern MBQL is retained without claiming legacy-clause equivalence.
        output['reasons'] = ['modern_mbql_requires_review' if type(stages) is list and len(stages) == 1
                             else 'multistage_query_requires_review']
        return output
    stage = query.get('query')
    if query.get('type') != 'query' or type(stage) is not dict:
        output['reasons'] = ['unrecognized_query_shape']
        return output
    source = stage.get('source-table')
    if type(source) is str and re.fullmatch(r'card__[1-9][0-9]*', source):
        pass  # Shared dependency scan includes nested stages and saved questions.
    elif positive(source):
        output['dependencies'].append({'kind': 'table', 'id': source, 'status': 'declared'})
    else:
        output['reasons'].append('source_table_unresolved')
    if not positive(source):
        output['reasons'].append('nested_or_saved_question_source_requires_review')
    allowed = {'source-table', 'aggregation', 'breakout', 'filter', 'order-by', 'limit', 'fields'}
    if set(stage) - allowed:
        output['reasons'].append('unsupported_query_clauses')
    if set(query) - {'database', 'type', 'query', 'parameters'}:
        output['reasons'].append('unsupported_query_envelope_fields')
    if not positive(query.get('database')):
        output['reasons'].append('database_unresolved')
    if query.get('parameters'):
        output['reasons'].append('query_parameters_require_review')

    def field(item):
        return type(item) is list and len(item) in (2, 3) and item[0] == 'field' and positive(item[1]) and (
            len(item) == 2 or item[2] is None or (type(item[2]) is dict and set(item[2]) <= {'base-type'}))

    def literal(value):
        return value is None or type(value) in (str, int, float, bool)

    def predicate(item):
        if type(item) is not list or not item or type(item[0]) is not str:
            return False
        if item[0] in ('and', 'or'):
            return len(item) >= 3 and all(predicate(x) for x in item[1:])
        if item[0] == 'not':
            return len(item) == 2 and predicate(item[1])
        if item[0] in ('is-null', 'not-null'):
            return len(item) == 2 and field(item[1])
        arity = {'=': 3, '!=': 3, '>': 3, '>=': 3, '<': 3, '<=': 3, 'between': 4}.get(item[0])
        return arity is not None and len(item) == arity and field(item[1]) and all(literal(x) for x in item[2:])

    for key in ('breakout', 'fields'):
        if key in stage and not (type(stage[key]) is list and all(field(x) for x in stage[key])):
            output['reasons'].append('unsupported_' + key)
    if 'aggregation' in stage:
        aggs = stage['aggregation']
        valid = type(aggs) is list and bool(aggs)
        if valid:
            for agg in aggs:
                valid = valid and (agg == ['count'] or (type(agg) is list and len(agg) == 2 and
                    agg[0] in ('sum', 'avg', 'min', 'max', 'distinct', 'count') and field(agg[1])))
        if not valid:
            output['reasons'].append('unsupported_aggregation')
    if 'filter' in stage and not predicate(stage['filter']):
        output['reasons'].append('unsupported_filter')
    if 'order-by' in stage and not (type(stage['order-by']) is list and all(
        type(x) is list and len(x) == 2 and x[0] in ('asc', 'desc') and field(x[1]) for x in stage['order-by'])):
        output['reasons'].append('unsupported_sort')
    if 'limit' in stage and not positive(stage['limit']):
        output['reasons'].append('invalid_limit')
    if not output['reasons']:
        output['status'] = 'interpreted_subset'
        output['analytical_contract'] = {'database_id': query['database'], 'source_table_id': source,
                                         'clauses': copy.deepcopy(stage), 'physical_binding': 'unverified'}
    return output


def card_id(row):
    value = row.get('card_id')
    if value is None and type(row.get('card')) is dict:
        value = row['card'].get('id')
    return value if positive(value) else None


def series_ids(row):
    return [r.get('id') for r in row.get('series', []) if type(r) is dict and positive(r.get('id'))]


def parse_snapshot(payload, raw, helpers):
    validate_snapshot(payload)
    result = helpers['base'](payload, raw, 'metabase', 'supplied_metabase_api_snapshot')
    identity, dashboard = payload['identity'], payload['dashboard']
    namespace = identity['source_origin'] + '/dashboard/' + str(dashboard['id'])
    fingerprint = sha(payload)
    result['source'].update(source_identity=copy.deepcopy(identity), namespace=namespace,
                            definition_fingerprint=fingerprint)
    result['build_authority'] = False
    result['migration_context'] = {'route': None, 'build_authority': False, 'target_write_authority': False,
                                   'native_validation': 'not_established', 'business_acceptance': 'not_assessed'}
    facet = helpers['facet']

    def add(kind, row, path, key, *, query_visual=False, visual_key=None, extra=None):
        facets = {'visual': facet(row, ('display', 'visualization_settings'), 'declared'),
                  'layout': facet(row, ('row', 'col', 'size_x', 'size_y', 'dashboard_tab_id', 'tabs', 'width'), 'declared'),
                  'query': facet(row, ('dataset_query', 'result_metadata'), 'declared'),
                  'filters': facet(row, ('parameters', 'parameter_mappings', 'auto_apply_filters'), 'declared'),
                  'interactions': facet(row, ('visualization_settings', 'action_id', 'action', 'series'), 'declared'),
                  'content': facet(row, ('name', 'description', 'visualization_settings'), 'declared'),
                  'security': {'status': 'unobserved', 'value': None}}
        return helpers['add_asset'](result, kind, row, path, key, namespace, facets,
            id_kind='scoped_native_id', source_identity={**copy.deepcopy(identity), 'source_platform': 'metabase',
                'namespace': namespace, 'dashboard_id': dashboard['id'], 'object_key': key,
                'native_id': row.get('id'), 'entity_id': row.get('entity_id'), 'definition_fingerprint': fingerprint,
                'query_visual': query_visual, 'visual_key': visual_key, **(extra or {})})

    add('dashboard', dashboard, '/dashboard', 'dashboard:' + str(dashboard['id']))
    tabs = dashboard.get('tabs', [])
    for i, tab in enumerate(tabs):
        add('page', tab, '/dashboard/tabs/' + str(i), 'tab:' + str(tab['id']))
    for i, parameter in enumerate(dashboard.get('parameters', [])):
        add('control', parameter, '/dashboard/parameters/' + str(i), 'parameter:' + str(parameter['id']))
    placements = dashboard.get('dashcards', [])
    used = {x for row in placements for x in [card_id(row), *series_ids(row)] if x is not None}
    cards = {row['id']: row for row in payload['cards']}
    known_displays = {'bar', 'line', 'area', 'row', 'table', 'scalar', 'smartscalar', 'combo', 'pie',
                      'scatter', 'pivot', 'gauge', 'progress', 'funnel', 'map', 'waterfall', 'sankey'}
    analyses = {}
    for i, row in enumerate(payload['cards']):
        key = 'card:' + str(row['id'])
        analysis = question_analysis(row.get('dataset_query'))
        analyses[key] = analysis
        asset = add('visual' if row['id'] in used else 'definition', row, '/cards/' + str(i), key,
                    query_visual=row['id'] in used, visual_key=key, extra={'card_id': row['id']})
        asset['facets']['query']['value']['interpretation'] = analysis
        if analysis['status'] != 'interpreted_subset':
            asset['facets']['query']['status'] = 'needs_review'
            helpers['gap'](result, 'metabase.query_requires_review', asset['source_path'], analysis['reasons'])
        for dep in analysis['dependencies']:
            dependency = {'source_asset': asset['asset_key'], **dep}
            if dep['kind'] == 'card' and dep['id'] not in cards:
                dependency['status'] = 'unresolved'
                helpers['gap'](result, 'metabase.missing_card_definition', asset['source_path'], dep['id'])
            result['dependencies'].append(dependency)
        if row.get('display') not in known_displays:
            helpers['gap'](result, 'metabase.visual_type_requires_review', asset['source_path'])
        for j, parameter in enumerate(row.get('parameters', [])):
            add('parameter', parameter, '/cards/' + str(i) + '/parameters/' + str(j),
                key + '/parameter:' + str(parameter.get('id', j)), extra={'card_id': row['id']})
    for i, row in enumerate(placements):
        cid, series = card_id(row), series_ids(row)
        key = 'dashcard:' + str(row['id'])
        visual = 'card:' + str(cid) if cid else None
        settings = row.get('visualization_settings', {})
        virtual = settings.get('virtual_card', {}) if type(settings) is dict else {}
        action = row.get('action_id') is not None or row.get('action') is not None or virtual.get('display') == 'action'
        asset = add('placement', row, '/dashboard/dashcards/' + str(i), key,
            query_visual=cid is not None or bool(series), visual_key=visual,
            extra={'card_id': cid, 'dashcard_id': row['id'], 'tab_id': row.get('dashboard_tab_id'),
                   'series_card_ids': series, 'content_kind': 'action' if action else virtual.get('display'),
                   'placement_overrides': copy.deepcopy(settings)})
        for dependency in ([cid] if cid else []) + series:
            result['dependencies'].append({'source_asset': asset['asset_key'], 'kind': 'card', 'id': dependency,
                                           'status': 'declared' if dependency in cards else 'unresolved'})
            if dependency not in cards:
                helpers['gap'](result, 'metabase.missing_card_definition', asset['source_path'], dependency)
        if cid in cards:
            asset['facets']['query'] = {'status': 'declared' if analyses[visual]['status'] == 'interpreted_subset' else 'needs_review',
                'value': {'card_id': cid, 'interpretation': copy.deepcopy(analyses[visual])}, 'interpretation': 'preserved_only'}
        if row.get('dashboard_tab_id') is not None and row['dashboard_tab_id'] not in {t['id'] for t in tabs}:
            helpers['gap'](result, 'metabase.missing_tab', asset['source_path'])
        if not cid and not series and virtual.get('display') not in ('text', 'heading', 'link', 'image') and not action:
            helpers['gap'](result, 'metabase.unknown_placement', asset['source_path'])
        if action:
            helpers['gap'](result, 'metabase.action_requires_separate_design_and_authority', asset['source_path'])
    for i, row in enumerate(payload['metadata']):
        add('definition', row, '/metadata/' + str(i), row['kind'] + ':' + str(row['id']),
            extra={'metadata_kind': row['kind'], 'metadata_id': row['id']})
    result['metabase_coverage'] = {'dashboards': 1, 'tabs': len(tabs), 'placements': len(placements),
        'questions': len(cards), 'query_placements': sum(card_id(r) is not None or bool(series_ids(r)) for r in placements),
        'controls': len(dashboard.get('parameters', [])), 'declared_coverage': copy.deepcopy(payload['coverage']),
        'export_completeness': 'not_established', 'behavior_coverage': 'not_verified'}
    for gap in payload['gaps']:
        helpers['gap'](result, 'metabase.supplied_gap', detail=gap)
    for code in ('effective_access_not_verified', 'render_and_behavior_not_verified',
                 'query_interpretation_is_not_target_compilation', 'scope_completeness_not_authenticated'):
        helpers['gap'](result, 'metabase.' + code)
    return result


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    snapshot = payload['source']['snapshot']
    result = parse_snapshot(snapshot, encoded(snapshot), helpers)
    source = helpers['base'](payload, raw, 'metabase', 'supplied_metabase_visual_capture')['source']
    result['source'].update(source)
    result['source']['capture_content_hash'] = payload['content_hash']
    need(result['source']['definition_fingerprint'] == payload['source']['definition_fingerprint'], 'definition_fingerprint')
    result['upstream_payload'] = copy.deepcopy(payload)
    request = payload['request']
    result['migration_context'].update(route=None if request['route'] == 'unselected' else request['route'],
                                       route_reference=request['route_reference'], target_surface=request['target_surface'])
    for gap in payload['gaps']:
        helpers['gap'](result, 'metabase.capture_gap', detail=gap)
    helpers['gap'](result, 'metabase.actual_files_require_verification')
    return result


def case_binding(asset, case, capture):
    validate_capture(capture)
    identity, snapshot = asset['source_identity'], capture['source']['snapshot']
    need(identity.get('definition_fingerprint') == capture['source']['definition_fingerprint'] and
         identity.get('dashboard_id') == snapshot['dashboard']['id'] and
         all(identity.get(k) == snapshot['identity'][k] for k in ('source_origin', 'version', 'principal_ref')),
         'case_identity_mismatch')
    binding = case.get('source_binding')
    need(type(binding) is dict, 'case_binding_required')
    expected = {'object_key': identity['object_key'], 'state_sha256': sha(capture['request']['state']),
                'definition_fingerprint': capture['source']['definition_fingerprint']}
    need(all(binding.get(k) == v for k, v in expected.items()), 'case_object_or_state_mismatch')
    attachment_id = binding.get('attachment_id')
    if attachment_id is not None:
        matches = [a for a in capture['attachments'] if a['attachment_id'] == attachment_id and
                   a['object_key'] == identity['object_key']]
        need(len(matches) == 1, 'case_attachment_mismatch')
        a = matches[0]
        for field in ('card_id', 'dashcard_id', 'tab_id'):
            need(a.get(field) == identity.get(field), 'case_attachment_identity_mismatch')
    if case.get('lane') == 'numeric':
        need(attachment_id is not None and matches[0]['format'] in ('csv', 'json'), 'case_numeric_result_required')
    return binding


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id',
              'state_sha256', 'attachment_sha256'}
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(type(binding[k]) is str and re.fullmatch('[a-f0-9]{64}', binding[k]) for k in (
             'capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and all(type(binding[k]) is str and binding[k] for k in ('object_key', 'attachment_id')), 'normalization_binding')
    need(type(profile) is dict, 'normalization_profile')
    parse_raw, parse_profile = raw, copy.deepcopy(profile)
    if profile.get('format') == 'metabase-json':
        module('powerbi_capture_files').decode(raw)  # duplicate keys/depth/size/nonfinite checks
        value = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal)
        need(type(value) is dict and value.get('status') == 'completed' and not value.get('error')
             and not value.get('errors'), 'query_result_not_completed')
        data = value.get('data')
        need(type(data) is dict and type(data.get('cols')) is list and type(data.get('rows')) is list,
             'query_result_columns_required')
        headers = profile.get('headers')
        need(headers == [x.get('name') for x in data['cols']] and len(set(headers)) == len(headers),
             'query_result_header_mismatch_or_duplicate')
        converted = []
        for row in data['rows']:
            need(type(row) is list and len(row) == len(headers), 'query_result_ragged_rows')
            converted.append({k: str(v) if type(v) is Decimal else v for k, v in zip(headers, row)})
        parse_raw = encoded({'rows': converted})
        parse_profile.update(format='json', rows_pointer='/rows')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'],
              'state_sha256': binding['state_sha256'], 'attachment_sha256': sha(parse_raw)}
    result = module('powerbi_visual').normalize_results(parse_raw, parse_profile, mapped)
    result.update(kind='metabase_normalized_results', binding=copy.deepcopy(binding), raw_sha256=sha(raw),
                  parser_profile=copy.deepcopy(profile))
    return result


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps = []
    pin = source.get('raw_file') if source.get('format') == 'metabase-normalized' else source.get('file')
    need(type(pin) is dict, 'comparison_raw_pin_required')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding.get('attachment_id')
               and a['sha256'] == pin.get('sha256')]
    if len(matches) != 1:
        return ['source.metabase_result_not_bound']
    a = matches[0]
    if capture.get('status') == 'blocked':
        gaps.append('source.metabase_capture_blocked')
    complete = a['completeness']
    if complete.get('status') != 'complete' or not complete.get('reference') or complete.get('flags'):
        gaps.append('source.metabase_completeness_unverified')
    if a.get('origin') == 'unknown' or a.get('result_scope') == 'unknown':
        gaps.append('source.metabase_result_origin_unverified')
    state = capture['request']['state']
    observed = a.get('observed_state')
    if not observed:
        gaps.append('source.metabase_observed_state_missing')
    else:
        for key in ('filters', 'parameters', 'timezone', 'locale', 'principal'):
            wanted = state.get(key)
            if (wanted is None or observed['state'].get(key) != wanted or source['context'].get(key) != wanted):
                gaps.append('source.metabase_observed.' + key)
            if key != 'principal' and target['context'].get(key) != wanted:
                gaps.append('context.' + key)
    expected = {'population': a['population'].get('key'), 'data_watermark': a['freshness'].get('data_watermark'),
                'freshness_reference': a['freshness'].get('reference'), 'result_scope': a.get('result_scope')}
    for key, wanted in expected.items():
        if wanted is None or not a['freshness'].get('observed_at') or source['context'].get(key) != wanted:
            gaps.append('source.metabase_context.' + key)
        if key == 'freshness_reference':
            if not target['context'].get(key):
                gaps.append('target.metabase_freshness_reference')
        elif target['context'].get(key) != wanted:
            gaps.append('context.' + key)
    # A standalone card query does not establish dashboard-parameter equivalence.
    if asset['kind'] == 'placement' and not (observed or {}).get('placement_reference'):
        gaps.append('source.metabase_placement_parameter_evidence_required')
    if asset['source_identity'].get('series_card_ids'):
        # Retain each series card independently; current evidence cannot prove
        # that a combined placement applies every series mapping correctly.
        gaps.append('source.metabase_combined_series_parity_not_supported')
    if source.get('format') == 'metabase-normalized':
        expected_binding = {'capture_content_hash': capture['content_hash'],
            'definition_fingerprint': capture['source']['definition_fingerprint'], 'object_key': binding['object_key'],
            'attachment_id': binding['attachment_id'], 'state_sha256': binding['state_sha256'], 'attachment_sha256': pin['sha256']}
        if type(normalized) is not dict or normalized.get('binding') != expected_binding:
            gaps.append('source.metabase_normalization_binding_mismatch')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                        target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    return gaps
