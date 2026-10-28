"""Distinct CDT adapter/capture projections, passive byte checks and typed CSV.

No vendor/DMA imports or source execution. Connected acquisition lives in the
separate host-gated capture module; these projections confer no authority.
"""
import copy
import hashlib
import json
from pathlib import PurePosixPath
import re
import unicodedata


def module(name):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('periscope_visual_' + name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def validate_capture(value):
    C = module('periscope_capture')
    need(type(value) is dict and value.get('schema_version') == C.ENVELOPE, 'capture_contract')
    need(value.get('content_hash') == sha({k: v for k, v in value.items() if k != 'content_hash'}), 'capture_hash')
    need(value.get('target_write_authority') is False and value.get('source_execution') is False
         and value.get('native_validation') == 'not_performed' and value.get('business_acceptance') == 'not_assessed',
         'capture_authority')
    request = C.validate_request(value.get('request'))
    need(request == value['request'] and value.get('request_sha256') == sha(request)
         and value.get('capture_id') == request['capture_id'], 'capture_request_binding')
    source = value.get('source')
    need(type(source) is dict, 'capture_source')
    report = source.get('adapter_report')
    validate(report, request['producer_revision'])
    inventory = C.validate_inventory(source.get('inventory'), request, report)
    identities = C.validate_crosswalk(source.get('crosswalk'), inventory, report)
    for key in ('adapter_report', 'inventory', 'crosswalk'):
        need(source.get(key + '_sha256') == sha(source[key]), 'capture_payload_hash')
    need(type(source.get('files')) is list and len(source['files']) == len(report['source_files']), 'capture_original_files')
    need({f.get('source_path'): f.get('sha256') for f in source['files']} ==
         {f['path']: f['sha256'] for f in report['source_files']}, 'capture_source_file_hashes')
    need(source.get('definition_fingerprint') == C.source_fingerprint(source), 'capture_definition_fingerprint')
    attachments = value.get('attachments')
    need(type(attachments) is list and len(attachments) <= 500, 'capture_attachments')
    seen = set()
    for row in attachments:
        C.validate_attachment(row, request, inventory)
        need(row['attachment_id'] not in seen and row.get('request_sha256') == value['request_sha256']
             and row.get('definition_fingerprint') == source['definition_fingerprint']
             and row.get('requested_state_sha256') == sha(request['state'])
             and row.get('acquisition') in ('supplied', 'render_api'), 'capture_attachment_binding')
        seen.add(row['attachment_id'])
        if row['acquisition'] == 'render_api':
            need(request['render'] is not None and row['attachment_id'] == request['render']['render_id']
                 and row['format'] == 'pdf' and row['object_key'] == request['dashboard_key']
                 and row['completeness']['status'] == 'unknown' and row['observed_state'] is None
                 and value.get('render_job', {}).get('status') == 'pdf_bytes_received', 'render_attachment_claim')
    pages = value.get('api_pages')
    need(type(pages) is list and len(pages) <= 1000 and (request['list_dashboards'] or not pages), 'capture_api_pages')
    ids, tokens = set(), set()
    for page in pages:
        need(type(page) is dict and set(page) == {'file', 'dashboard_ids', 'total_items', 'next_page_start'}
             and type(page['dashboard_ids']) is list and all(text(x) for x in page['dashboard_ids'])
             and len(set(page['dashboard_ids'])) == len(page['dashboard_ids'])
             and not ids.intersection(page['dashboard_ids']) and type(page['total_items']) is int
             and page['total_items'] == pages[0]['total_items'], 'capture_pagination')
        ids.update(page['dashboard_ids'])
        token = page['next_page_start']
        need(token is None or (text(token) and token not in tokens), 'capture_pagination_token')
        need(None not in tokens, 'capture_page_after_terminal')
        tokens.add(token)
        need(len(ids) <= page['total_items'], 'capture_pagination_total')
    if pages and pages[-1]['next_page_start'] is None:
        need(len(ids) == pages[-1]['total_items'], 'capture_pagination_terminal_total')
    job = value.get('render_job')
    if job is not None:
        need(request['render'] is not None and type(job) is dict and set(job) ==
             {'response_file', 'created_at_epoch', 'body_sha256', 'status', 'expires_after_seconds'}
             and job['status'] in ('awaiting_pdf', 'pdf_bytes_received') and job['expires_after_seconds'] == 259200
             and type(job['created_at_epoch']) in (int, float) and C.digest(job['body_sha256']), 'capture_render_job')
        body = {'dashboard_id': identities[request['dashboard_key']]['numeric_id'], 'filters': request['state']['filters']}
        for key in ('aggregation', 'daterange'):
            if request['state'][key] is not None:
                body[key] = request['state'][key]
        if request['render']['dashboard_ts'] is not None:
            body['dashboard_ts'] = request['render']['dashboard_ts']
        need(body['dashboard_id'] is not None and job['body_sha256'] == sha({'data': body}), 'capture_render_body')
    operations = value.get('operations')
    need(type(operations) is list and len(operations) <= request['max_total_requests']
         and value.get('request_count') == len(operations) and type(value.get('request_count')) is int,
         'capture_request_budget')
    for op in operations:
        need(type(op) is dict and text(op.get('key')) and op.get('operation') in ('inventory', 'render', 'download')
             and op.get('method') == ('POST' if op['operation'] == 'render' else 'GET')
             and C.digest(op.get('fingerprint_sha256')) and type(op.get('started_at_epoch')) in (int, float)
             and op.get('status') in ('pending', 'success', 'rejected', 'uncertain', 'failed'), 'capture_operation')
        if 'http_status' in op:
            need(type(op['http_status']) is int and C.digest(op.get('response_sha256'))
                 and type(op.get('response_bytes')) is int and 0 <= op['response_bytes'] <= request['max_response_bytes'],
                 'capture_operation_response')
        if op['status'] == 'success':
            need(op.get('http_status') == 200, 'capture_success_without_response')
    def successful(key, pin, fingerprint=None):
        return any(op['key'] == key and op['status'] == 'success' and op.get('response_sha256') == pin['sha256']
                   and op.get('response_bytes') == pin['bytes'] and
                   (fingerprint is None or op['fingerprint_sha256'] == fingerprint) for op in operations)
    from urllib.parse import urlencode
    for i, page in enumerate(pages):
        token = pages[i - 1]['next_page_start'] if i else None
        url = C.API_ORIGIN + '/api/v1/dashboards' + ('?' + urlencode({'next_page_start': token}) if token is not None else '')
        fingerprint = sha({'request_sha256': value['request_sha256'], 'method': 'GET', 'url': url, 'body_sha256': None})
        need(successful('inventory.%d' % i, page['file'], fingerprint), 'capture_page_operation_binding')
    if job is not None:
        fingerprint = sha({'request_sha256': value['request_sha256'], 'method': 'POST',
            'url': C.RENDER_ORIGIN + '/api/v1/screenshot_requests', 'body_sha256': job['body_sha256']})
        need(successful('render.' + request['render']['render_id'], job['response_file'], fingerprint),
             'capture_render_operation_binding')
    for row in attachments:
        if row['acquisition'] == 'render_api':
            need(successful('render-download.' + row['attachment_id'], row), 'capture_download_operation_binding')
    need(type(value.get('network_bytes')) is int and 0 <= value['network_bytes'] <= request['max_total_bytes']
         and type(value.get('journal_revision')) is int and 1 <= value['journal_revision'] <= 5000
         and type(value.get('created_at_epoch')) in (int, float) and type(value.get('retry_not_before_epoch')) in (int, float),
         'capture_budget_or_journal')
    need(value.get('status') in ('partial', 'blocked', 'acquired_requested_operations')
         and type(value.get('gaps')) is list and set(C.BASE_GAPS) <= set(value['gaps']), 'capture_status')
    if value['status'] == 'acquired_requested_operations':
        need(not request['list_dashboards'] or (pages and pages[-1]['next_page_start'] is None
             and identities[request['dashboard_key']]['api_id'] in ids), 'capture_inventory_incomplete')
        need(request['render'] is None or (job and job['status'] == 'pdf_bytes_received'), 'capture_render_incomplete')
    files = C.file_pins(value)
    indexed = {}
    for pin in files:
        need(type(pin) is dict and type(pin.get('path')) is str
             and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', pin['path'])
             and C.digest(pin.get('sha256')) and type(pin.get('bytes')) is int and 0 <= pin['bytes'] <= C.F.MAX_FILE,
             'capture_file_pin')
        need(pin['path'] not in indexed, 'capture_pin_collision')
        indexed[pin['path']] = pin
    need(sum(p['bytes'] for p in files) <= request['max_total_bytes'], 'capture_file_budget')
    return value


def verify_capture_files(value, root):
    validate_capture(value)
    C = module('periscope_capture')
    from pathlib import Path
    root = Path(root)
    verified = {}
    for pin in C.file_pins(value):
        raw = C.F.read_pin(root, pin)
        verified[pin['path']] = pin['sha256']
    for key in ('adapter_report', 'inventory', 'crosswalk'):
        need(C.F.decode(C.F.read_pin(root, value['source'][key + '_file'])) == value['source'][key],
             'capture_original_payload_mismatch')
    for row in value['attachments']:
        info = C.inspect_attachment(C.F.read_pin(root, row), row['format'])
        need(info == row.get('inspection'), 'capture_attachment_inspection_mismatch')
        if row['format'] == 'csv':
            need(row['completeness']['row_count'] in (None, info['row_count']), 'capture_csv_count_mismatch')
    for page in value['api_pages']:
        raw = C.F.read_pin(root, page['file'])
        data = C.dashboard_page(raw)
        need(page['dashboard_ids'] == [d['id'] for d in data['dashboards']] and
             all(page[k] == data[k] for k in ('total_items', 'next_page_start')), 'capture_page_original_mismatch')
    if value['render_job']:
        data = C.F.decode(C.F.read_pin(root, value['render_job']['response_file']))
        need(type(data) is dict and set(data) == {'url'}, 'capture_render_original')
        C.render_url(data['url'], value['request'])
        fingerprint = sha({'request_sha256': value['request_sha256'], 'method': 'GET',
                           'url': data['url'], 'body_sha256': None})
        for a in value['attachments']:
            if a['acquisition'] == 'render_api':
                need(any(op['key'] == 'render-download.' + a['attachment_id'] and op['status'] == 'success'
                     and op['fingerprint_sha256'] == fingerprint and op['response_sha256'] == a['sha256']
                     for op in value['operations']), 'capture_download_url_binding')
    return {'status': 'verified_local_bytes', 'files': verified, 'native_validation': 'not_performed'}


def parse_capture(payload, raw, helpers):
    validate_capture(payload)
    source, request = payload['source'], payload['request']
    result = parse_adapter(source['adapter_report'], encoded(source['adapter_report']), helpers, request['producer_revision'])
    base = helpers['base'](payload, raw, 'periscope', 'supplied_periscope_visual_capture')
    result.update(source=base['source'], upstream_payload=copy.deepcopy(payload))
    identity = {k: copy.deepcopy(request[k]) for k in ('product', 'site_name', 'space_id', 'source_revision', 'dashboard_key')}
    namespace = request['site_name'] + '/space/' + str(request['space_id']) + '/' + request['dashboard_key']
    result['source'].update(source_identity=identity, definition_fingerprint=source['definition_fingerprint'],
                            capture_content_hash=payload['content_hash'], namespace=namespace)
    # Semantic parser output remains preserved evidence, not a second visual count.
    for asset in result['assets']:
        asset['kind'] = 'definition'
        asset['source_identity'].update(adapter_evidence_only=True, query_visual=False,
                                       definition_fingerprint=source['definition_fingerprint'], namespace=namespace)
    obsolete = {'periscope.visual_denominator_not_established', 'periscope.render_and_result_capture_not_implemented'}
    result['gaps'] = [g for g in result['gaps'] if g.get('code') not in obsolete]
    crosswalk = {r['key']: r for r in source['crosswalk']['rows']}
    objects = {r['id']: r for r in source['adapter_report']['objects']}
    rows = source['inventory']['objects']
    inventory_index = {r['key']: r for r in rows}
    for index, row in enumerate(rows):
        path = '/source/inventory/objects/' + str(index)
        semantic = objects.get(row['source_object_id'])
        config = semantic['details'].get('native_configuration', {}) if semantic else {}
        facets = {'visual': {'status': 'declared', 'value': copy.deepcopy(config)},
                  'layout': {'status': 'declared', 'value': copy.deepcopy(row['configuration'])},
                  'filters': {'status': 'declared' if row['kind'] == 'control' else 'needs_review', 'value': copy.deepcopy(row['configuration'])},
                  'query': {'status': 'declared' if semantic else 'unobserved', 'value': copy.deepcopy([
                      e for e in source['adapter_report']['expressions'] if e['object_id'] == row['source_object_id'] and semantic])},
                  'interactions': {'status': 'needs_review', 'value': None},
                  'security': {'status': 'needs_review', 'value': None}}
        key = row['key']
        si = {**identity, 'source_platform': 'periscope', 'object_key': key,
              'definition_fingerprint': source['definition_fingerprint'], 'namespace': namespace,
              'source_object_id': row['source_object_id'], 'identity_crosswalk': copy.deepcopy(crosswalk.get(key)),
              'visual_key': row['configuration'].get('visual_key') if row['kind'] == 'placement' else (key if row['kind'] == 'visual' else None),
              'query_visual': row['kind'] == 'visual' or (row['kind'] == 'placement' and
                  inventory_index[row['configuration']['visual_key']]['kind'] == 'visual'),
              'declared_disposition': row['disposition']}
        helpers['add_asset'](result, row['kind'], row, path, key, namespace, facets,
                             id_kind='independently_enumerated_source_key', source_identity=si)
        if row['source_object_id'] is None or row['disposition'] in ('manual_review', 'unsupported'):
            helpers['gap'](result, 'periscope.independent_object_requires_review', path)
    result.setdefault('migration_context', {}).update(
        route=None if request['route'] == 'unselected' else request['route'],
        route_reference=request['route_reference'], target_surface=request['target_surface'],
        build_authority=False, target_write_authority=False,
        native_validation='not_established', business_acceptance='not_assessed')
    result['periscope_coverage'] = {'enumerated_objects': len(rows),
        'visuals': sum(r['kind'] == 'visual' for r in rows), 'controls': sum(r['kind'] == 'control' for r in rows),
        'placements': sum(r['kind'] == 'placement' for r in rows),
        'manifest_completeness': source['inventory']['completeness'], 'source_export_completeness': 'not_established',
        'enumeration_provenance': 'supplied_separate_source_enumeration_not_authenticated', 'behavior_coverage': 'not_verified'}
    for gap in payload['gaps']:
        helpers['gap'](result, 'periscope.capture_gap', detail=gap)
    helpers['gap'](result, 'periscope.actual_files_require_verification')
    return result


def case_binding(asset, case, capture):
    validate_capture(capture)
    request, identity = capture['request'], asset.get('source_identity', {})
    need(identity.get('definition_fingerprint') == capture['source']['definition_fingerprint'] and
         all(identity.get(k) == request[k] for k in ('product', 'site_name', 'space_id', 'source_revision', 'dashboard_key')),
         'case_source_identity_mismatch')
    binding = case.get('source_binding')
    need(type(binding) is dict, 'case_binding_required')
    key = identity.get('visual_key') if asset['kind'] == 'placement' else identity.get('object_key')
    expected = {'object_key': key, 'placement_key': identity.get('object_key') if asset['kind'] == 'placement' else None,
                'state_sha256': sha(request['state']), 'definition_fingerprint': capture['source']['definition_fingerprint']}
    need(all(binding.get(k) == v for k, v in expected.items()), 'case_object_or_state_mismatch')
    inventory = {o['key']: o for o in capture['source']['inventory']['objects']}
    need(key in inventory and inventory[key]['disposition'] != 'out_of_scope', 'case_object_scope')
    aid = binding.get('attachment_id')
    if aid is not None:
        matches = [a for a in capture['attachments'] if a['attachment_id'] == aid and a['object_key'] == key]
        need(len(matches) == 1, 'case_attachment_mismatch')
    if case.get('lane') == 'numeric':
        need(aid is not None and matches[0]['format'] == 'csv', 'case_numeric_csv_required')
    return binding


def validate_case(value, capture):
    """Lightweight case schema; asset identity matching belongs to case_binding."""
    need(type(value) is dict and type(value.get('source_binding')) is dict, 'case_binding_required')
    binding = value['source_binding']
    need(binding.get('state_sha256') == sha(capture['request']['state']) and
         binding.get('definition_fingerprint') == capture['source']['definition_fingerprint'], 'case_capture_binding')
    return binding


def normalize_results(raw, profile, binding):
    fields = {'capture_content_hash', 'definition_fingerprint', 'object_key', 'attachment_id',
              'state_sha256', 'attachment_sha256'}
    C = module('periscope_capture')
    need(type(binding) is dict and set(binding) == fields and binding['attachment_sha256'] == sha(raw)
         and all(C.digest(binding[k]) for k in ('capture_content_hash', 'definition_fingerprint', 'state_sha256', 'attachment_sha256'))
         and C.local_id(binding['object_key']) and C.local_id(binding['attachment_id']), 'normalization_binding')
    need(type(profile) is dict and profile.get('format') == 'csv', 'csv_only_normalization')
    mapped = {'capture_content_hash': binding['capture_content_hash'], 'page_id': binding['definition_fingerprint'],
              'visual_id': binding['object_key'], 'query_id': binding['attachment_id'],
              'state_sha256': binding['state_sha256'], 'attachment_sha256': binding['attachment_sha256']}
    result = module('powerbi_visual').normalize_results(raw, profile, mapped)
    result.update(kind='periscope_normalized_results', binding=copy.deepcopy(binding))
    return result


def comparison_gaps(capture, asset, case, source, target, normalized=None, columns=None):
    binding = case_binding(asset, case, capture)
    gaps, request = [], capture['request']
    if case.get('source_capture') is None:
        gaps.append('source.periscope_case_capture_required')
    if capture['status'] == 'blocked':
        gaps.append('source.periscope_capture_blocked')
    if request['space_id'] is None or request['source_revision']['kind'] == 'unknown':
        gaps.append('source.periscope_scope_or_revision_unverified')
    raw_pin = source.get('raw_file') if source.get('format') == 'periscope-normalized' else source.get('file')
    need(type(raw_pin) is dict, 'comparison_raw_file_required')
    matches = [a for a in capture['attachments'] if a['attachment_id'] == binding.get('attachment_id')
               and a['format'] == 'csv' and a['sha256'] == raw_pin.get('sha256')]
    if len(matches) != 1:
        return gaps + ['source.periscope_result_not_bound']
    a = matches[0]
    if a['completeness']['status'] != 'complete' or not a['completeness']['reference']:
        gaps.append('source.periscope_completeness_unverified')
    if a['origin'] == 'unknown' or a['result_scope'] == 'unknown':
        gaps.append('source.periscope_result_origin_unverified')
    # A chart's Python/R output is a different result population from its SQL
    # input. Resolve placements through the retained inventory, not filenames or
    # unrelated module dependencies, and never execute the source to infer it.
    inventory = {row['key']: row for row in capture['source']['inventory']['objects']}
    selected = inventory[asset['source_identity']['object_key']]
    if selected['kind'] == 'placement':
        selected = inventory[selected['configuration']['visual_key']]
    need(binding['object_key'] == selected['key'], 'comparison_selected_visual_mismatch')
    adapter = capture['source']['adapter_report']
    chart = next((row for row in adapter['objects'] if row['id'] == selected['source_object_id']), None)
    if selected['kind'] == 'visual' and chart is not None:
        def post_query_language(value):
            return type(value) is str and re.fullmatch(r'(?:python|r)(?:[ _-]?\d+(?:\.\d+)*)?', value.strip().lower()) is not None
        config = chart['details'].get('native_configuration')
        configured = post_query_language(config.get('code_language')) if type(config) is dict else False
        attached = any(row['object_id'] == chart['id'] and post_query_language(row['language'])
                       for row in adapter['expressions'])
        if (configured or attached) and (a['origin'] != 'transformed' or a['result_scope'] != 'transformed'):
            gaps.append('source.periscope_chart_transformed_results_required')
    observed = a['observed_state']
    if observed is None:
        gaps.append('source.periscope_observed_state_missing')
    else:
        obs = observed['state']
        for key in ('filters', 'parameters', 'daterange', 'aggregation', 'timezone', 'locale'):
            wanted = request['state'][key]
            if (key in ('timezone', 'locale') and wanted is None) or obs[key] != wanted or source['context'].get(key) != wanted:
                gaps.append('source.periscope_observed.' + key)
            if target['context'].get(key) != wanted:
                gaps.append('context.' + key)
        principal = request['state']['principal']
        if not principal or obs['principal'] != principal or source['context'].get('principal') != principal:
            gaps.append('source.periscope_principal_unverified')
    expected_context = {'population': a['population']['key'], 'data_watermark': a['freshness']['data_watermark'],
                        'freshness_reference': a['freshness']['reference'], 'result_scope': a['result_scope']}
    for key, wanted in expected_context.items():
        if wanted is None or not a['freshness']['observed_at'] or source['context'].get(key) != wanted:
            gaps.append('source.periscope_context.' + key)
        # Target freshness evidence is independently attributable, not identical source reference text.
        if key == 'freshness_reference':
            if not target['context'].get(key):
                gaps.append('target.periscope_freshness_reference')
        elif target['context'].get(key) != wanted:
            gaps.append('context.' + key)
    if source.get('format') == 'periscope-normalized':
        expected = {'capture_content_hash': capture['content_hash'], 'definition_fingerprint': capture['source']['definition_fingerprint'],
                    'object_key': binding['object_key'], 'attachment_id': binding['attachment_id'],
                    'state_sha256': binding['state_sha256'], 'attachment_sha256': raw_pin['sha256']}
        if type(normalized) is not dict or normalized.get('binding') != expected:
            gaps.append('source.periscope_normalization_binding_mismatch')
        for field in (normalized or {}).get('parser_profile', {}).get('columns', []):
            currency = field.get('currency')
            if currency is not None:
                mapped = [c for c in (columns or []) if c.get('source') == field['name']]
                if len(mapped) != 1 or source['context'].get('currencies', {}).get(field['name']) != currency['code'] or \
                        target['context'].get('currencies', {}).get(mapped[0]['target']) != currency['code']:
                    gaps.append('context.currency.' + field['name'])
    return gaps


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

DMA_REVISION = 'a88f2a3b4dd0cfa596766f938961f37d673cf9b9'
SHA = re.compile(r'[a-f0-9]{64}\Z')


def need(ok, code):
    if not ok:
        raise ValueError('periscope.' + code)


def text(value):
    return type(value) is str and bool(value) and len(value) <= 8192 and not any(ord(c) < 32 for c in value)


def file_path(value):
    need(text(value), 'source_path_invalid')
    path = PurePosixPath(value)
    need(bool(path.parts) and not path.is_absolute() and '..' not in path.parts and '\\' not in value
         and ':' not in value and str(path) == value, 'source_path_invalid')
    return value


def validate(value, revision):
    need(revision == DMA_REVISION, 'unsupported_or_missing_producer_revision')
    need(type(value) is dict and type(value.get('schema_version')) is int and value['schema_version'] == 1
         and value.get('kind') == 'source_adapter_result' and value.get('source') == 'periscope'
         and type(value.get('adapter_version')) is int and value['adapter_version'] == 1, 'adapter_contract')
    need(value.get('execution_performed') is False and value.get('native_validation') == 'not_run'
         and value.get('export_completeness') == 'not_established', 'unsupported_execution_or_acceptance_claim')
    # Reject structured credential fields; source expressions still need the
    # caller's privacy review. This is not a general secret scanner.
    stack = [value]
    secret_keys = {'authorization', 'password', 'clientsecret', 'accesstoken', 'refreshtoken',
                   'apikey', 'apitoken', 'privatekey', 'credentials', 'httpxpartnerauth'}
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, child in item.items():
                if key.lower().replace('_', '').replace('-', '') in secret_keys:
                    need(child in (None, '', '[REDACTED]') or child == {'redacted': 'secret'}, 'credential_bearing_input')
                stack.append(child)
        elif type(item) is list:
            stack.extend(item)
    for category in ('source_files', 'objects', 'expressions', 'dependencies', 'gaps', 'limitations'):
        need(type(value.get(category)) is list and len(value[category]) <= 5000, 'collection_required')
    need(all(type(x) is str for x in value['limitations']), 'limitations_invalid')
    if 'component_sha256' in value:
        need(type(value['component_sha256']) is str and SHA.fullmatch(value['component_sha256']), 'component_hash_invalid')
    files, normalized = {}, set()
    for row in value['source_files']:
        need(type(row) is dict, 'file_record_invalid')
        path = file_path(row.get('path'))
        key = unicodedata.normalize('NFC', path).casefold()
        need(key not in normalized, 'duplicate_source_path')
        normalized.add(key)
        need(type(row.get('sha256')) is str and SHA.fullmatch(row['sha256'])
             and row.get('status') in ('parsed', 'partial', 'unsupported')
             and type(row.get('reason')) is str, 'file_record_invalid')
        files[path] = row
    summary = value.get('coverage_summary')
    expected = {'unit': 'supplied_source_files', 'expected': len(files), 'observed': len(files), 'missing': 0,
        'statuses': {status: sum(f['status'] == status for f in files.values())
                     for status in ('parsed', 'partial', 'unsupported')}}
    need(type(summary) is dict and summary == expected
         and all(type(summary.get(k)) is int for k in ('expected', 'observed', 'missing'))
         and all(type(n) is int for n in summary.get('statuses', {}).values()), 'coverage_mismatch')
    ids = set()
    for category in ('objects', 'expressions', 'dependencies', 'gaps'):
        occurrences = set()
        ordinals = {}
        for row in value[category]:
            need(type(row) is dict, 'record_invalid')
            evidence = row.get('evidence')
            need(type(evidence) is dict and type(evidence.get('path')) is str
                 and evidence['path'] in files and text(evidence.get('locator'))
                 and evidence.get('sha256') == files[evidence['path']]['sha256'], 'evidence_mismatch')
            occurrence = row.get('occurrence_id')
            need(text(occurrence) and occurrence not in occurrences, 'occurrence_invalid_or_duplicate')
            position = (evidence['path'], evidence['locator'])
            ordinal = ordinals.get(position, 0)
            material = json.dumps([category, *position, ordinal], ensure_ascii=True).encode()
            expected_occurrence = 'periscope:occurrence:' + hashlib.sha256(material).hexdigest()[:24]
            need(occurrence == expected_occurrence, 'occurrence_binding_mismatch')
            ordinals[position] = ordinal + 1
            occurrences.add(occurrence)
            if category in ('objects', 'expressions'):
                need(text(row.get('id')) and row['id'] not in ids, 'identity_invalid_or_duplicate')
                ids.add(row['id'])
            if category == 'objects':
                need(text(row.get('kind')) and type(row.get('name')) is str and type(row.get('details')) is dict and 'native_id' in row
                     and (row.get('native_id') is None or text(row['native_id'])), 'object_invalid')
            elif category == 'expressions':
                need(type(row.get('text')) is str and text(row.get('language')) and type(row.get('details')) is dict
                     and row.get('content_sha256') == hashlib.sha256(row['text'].encode()).hexdigest(), 'expression_hash_or_shape')
            elif category == 'dependencies':
                need(text(row.get('source_id')) and text(row.get('target')) and type(row.get('details')) is dict,
                     'dependency_invalid')
            else:
                need(text(row.get('code')) and type(row.get('message')) is str, 'gap_invalid')
                need(files[evidence['path']]['status'] != 'parsed', 'hidden_coverage_gap')
    objects = {row['id']: row for row in value['objects']}
    for row in value['expressions']:
        need(row.get('object_id') is None or (text(row['object_id']) and row['object_id'] in objects), 'expression_owner_missing')
    for row in value['dependencies']:
        need(row['source_id'] in objects, 'dependency_owner_missing')
    return files, objects


def parse_adapter(payload, raw, helpers, revision):
    files, objects = validate(payload, revision)
    result = helpers['base'](payload, raw, 'periscope', 'supplied_periscope_source_adapter_result')
    result['source']['projection_version'] = '1.0.0'
    result['source']['producer'] = {'name': 'DataModelAccelerator', 'revision': revision,
        'revision_evidence': 'operator_declared_not_authenticated',
        'component_sha256': payload.get('component_sha256')}
    result['source']['upstream_files'] = copy.deepcopy(payload['source_files'])
    result['upstream_coverage'] = copy.deepcopy(payload['coverage_summary'])
    result['upstream_gaps'] = copy.deepcopy(payload['gaps'])
    result['upstream_expressions'] = copy.deepcopy(payload['expressions'])
    result['build_authority'] = False
    add, gap, facet = helpers['add_asset'], helpers['gap'], helpers['facet']
    expressions = {}
    for row in payload['expressions']:
        expressions.setdefault(row.get('object_id'), []).append(row)
    native = set()
    for index, row in enumerate(payload['objects']):
        details, source_kind = row['details'], row['kind']
        config = details.get('native_configuration')
        config = config if type(config) is dict else {}
        kind = {'dashboard': 'dashboard', 'chart': 'visual', 'filter': 'filter', 'parameter': 'parameter'}.get(source_kind, 'definition')
        path = '/objects/' + str(index)
        facets = {'visual': facet(config, ('chart_type', 'color_theme', 'encrypted_definition'), 'declared'),
            'layout': facet(config, ('position', 'size'), 'declared'),
            'filters': facet(config, ('configured_filters', 'disable_filters'), 'declared'),
            'query': {'status': 'declared' if expressions.get(row['id']) else 'unobserved',
                      'value': copy.deepcopy(expressions.get(row['id'], []))},
            'content': facet(row, ('name',), 'declared'),
            'interactions': {'status': 'needs_review', 'value': None},
            'security': {'status': 'needs_review', 'value': None}}
        if source_kind in ('filter', 'parameter'):
            facets['filters'] = {'status': 'declared', 'value': copy.deepcopy(details)}
        add(result, kind, row, path, row['id'], row['evidence']['path'], facets,
            id_kind='adapter_generated_id', source_identity={'source_platform': 'periscope',
                'native_id': row['native_id'], 'adapter_kind': source_kind,
                'adapter_occurrence_id': row['occurrence_id'], 'evidence': copy.deepcopy(row['evidence']),
                'parent_id': details.get('parent_id'), 'query_visual': source_kind == 'chart'})
        if source_kind in ('dashboard', 'chart'):
            if row['native_id'] is None:
                gap(result, 'periscope.native_id_unavailable', path)
            elif (source_kind, row['native_id']) in native:
                gap(result, 'periscope.duplicate_native_token', path)
            native.add((source_kind, row['native_id']))
        if source_kind == 'chart':
            gap(result, 'periscope.render_results_and_behavior_required', path)
            if config.get('encrypted_definition'):
                gap(result, 'periscope.encrypted_settings_opaque', path)
        if source_kind == 'dashboard':
            gap(result, 'periscope.inherited_filters_unverified', path)
        if details.get('parent_id') is not None and (not text(details['parent_id']) or details['parent_id'] not in objects):
            gap(result, 'periscope.parent_unresolved', path)
    # Every supplied file stays an obligation, including files the upstream
    # parser could not turn into an analytics object. A parsed file is not a render.
    for index, row in enumerate(payload['source_files']):
        path = '/source_files/' + str(index)
        add(result, 'definition', row, path, None, row['path'],
            {'content': {'status': 'declared', 'value': copy.deepcopy(row)}},
            id_kind='source_file', source_identity={'source_platform': 'periscope',
                'source_file': row['path'], 'definition_sha256': row['sha256']})
        if row['status'] != 'parsed':
            gap(result, 'periscope.file_coverage_gap', path, row)
    result['dependencies'] = copy.deepcopy(payload['dependencies'])
    for index, row in enumerate(payload['dependencies']):
        if row['target'] not in objects or row['details'].get('resolution') != 'declared':
            gap(result, 'periscope.dependency_requires_review', '/dependencies/' + str(index), row)
    for index, row in enumerate(payload['gaps']):
        gap(result, 'periscope.upstream_gap', '/gaps/' + str(index), row)
    for code in ('source_files_not_reverified', 'visual_denominator_not_established',
                 'effective_access_not_exported', 'render_and_result_capture_not_implemented',
                 'source_code_and_templates_not_executed'):
        gap(result, 'periscope.' + code)
    return result
