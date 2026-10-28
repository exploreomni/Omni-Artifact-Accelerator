#!/usr/bin/env python3
"""Bounded CDT source evidence. Code/SQL/pickle remain bytes; no target writes.

Connected execution requires a host-injected callable; request files and CLI
flags cannot authorize it. Public API contracts: dtdocs.sisense.com/article/
user-and-role-management-api-rbac and /render-api. No Fusion API is accepted.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


def module(name):
    spec = importlib.util.spec_from_file_location('periscope_' + name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F = module('powerbi_capture_files')
need, sha, encoded = F.need, F.sha, F.encoded
REQUEST = 'periscope-visual-capture-request.v1'
ENVELOPE = 'periscope-visual-capture.v1'
PRODUCT = 'sisense_cdt'
API_ORIGIN = 'https://app.periscopedata.com'
RENDER_ORIGIN = 'https://api.periscopedata.com'
MAX_JOURNAL_BYTES = 128000000
BASE_GAPS = ['product_and_identity_evidence_supplied_not_authenticated',
             'export_completeness_not_established', 'effective_access_not_verified',
             'source_code_not_executed', 'requested_state_is_not_observed_state',
             'rendered_quality_and_business_acceptance_not_assessed',
             'global_vendor_rate_limits_require_host_coordination']


def text(value, maximum=1000):
    return type(value) is str and 0 < len(value) <= maximum and all(ord(c) >= 32 for c in value)


def local_id(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) is not None


def digest(value):
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def utcnow():
    return datetime.now(timezone.utc).timestamp()


def revision(value):
    need(type(value) is dict and set(value) == {'kind', 'value', 'reference'}
         and value['kind'] in ('git_commit', 'supplied_snapshot', 'unknown')
         and text(value['reference']), 'periscope.source_revision_required')
    if value['kind'] == 'git_commit':
        need(type(value['value']) is str and re.fullmatch(r'[a-f0-9]{40}', value['value']), 'periscope.git_revision')
    elif value['kind'] == 'unknown':
        need(value['value'] is None, 'periscope.unknown_revision')
    else:
        need(text(value['value']), 'periscope.snapshot_revision')


def state(value):
    need(type(value) is dict and set(value) == {'filters', 'parameters', 'daterange', 'aggregation',
        'timezone', 'locale', 'principal', 'reference'}, 'periscope.state_contract')
    need(type(value['filters']) is list and len(value['filters']) <= 100
         and type(value['parameters']) is dict and len(value['parameters']) <= 100,
         'periscope.state_values')
    for row in value['filters']:
        need(type(row) is dict and {'name', 'value'} <= set(row) <= {'name', 'value', 'group', 'display'}
             and text(row['name']), 'periscope.filter_shape')
        for val in row.values():
            vals = val if type(val) is list else [val]
            need(len(vals) <= 100 and all(type(v) in (str, int, float, bool) or v is None for v in vals),
                 'periscope.filter_scalar_values')
    d = value['daterange']
    need(d is None or (type(d) is dict and (
        (set(d) == {'days'} and type(d['days']) is int and 1 <= d['days'] <= 36600) or
        (set(d) == {'start', 'end'} and all(type(d[k]) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', d[k]) for k in d))
    )), 'periscope.daterange')
    for key in ('aggregation', 'timezone', 'locale', 'principal'):
        need(value[key] is None or text(value[key]), 'periscope.state_context')
    need(text(value['reference']), 'periscope.state_reference')
    F.decode(encoded(value))
    F.secret_check(value)


def validate_request(value, *, require_service=False):
    required = {'schema_version', 'capture_id', 'product', 'product_evidence_ref', 'site_name', 'space_id',
                'space_reference', 'source_revision', 'dashboard_key', 'principal_ref', 'authorization_ref',
                'credential_ref', 'evidence_mode', 'route', 'route_reference', 'target_surface', 'state',
                'adapter_report_path', 'producer_revision', 'inventory_path', 'crosswalk_path'}
    defaults = {'list_dashboards': False, 'render': None, 'render_download_hosts': [],
                'max_requests_per_invocation': 20, 'max_total_requests': 200, 'max_total_bytes': 64000000,
                'max_response_bytes': 8000000, 'max_elapsed_seconds': 21600, 'max_attempts_per_operation': 3}
    need(type(value) is dict and required <= set(value) <= required | set(defaults)
         and value.get('schema_version') == REQUEST and value.get('product') == PRODUCT,
         'periscope.cdt_request_required')
    r = {**defaults, **copy.deepcopy(value)}
    need(local_id(r['capture_id']) and local_id(r['dashboard_key']) and
         type(r['site_name']) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', r['site_name']),
         'periscope.request_identity')
    need(r['space_id'] is None or text(r['space_id'], 200), 'periscope.space_identity')
    for key in ('space_reference', 'product_evidence_ref', 'principal_ref', 'authorization_ref'):
        need(text(r[key]), 'periscope.evidence_reference')
    need(r['credential_ref'] is None or text(r['credential_ref'], 200), 'periscope.credential_reference')
    need(not require_service or r['credential_ref'] is not None, 'periscope.host_credential_reference_required')
    revision(r['source_revision'])
    need(r['producer_revision'] == module('periscope_visual').DMA_REVISION, 'periscope.producer_revision')
    for key in ('adapter_report_path', 'inventory_path', 'crosswalk_path'):
        F.source_path(r[key])
    need(len({r[k] for k in ('adapter_report_path', 'inventory_path', 'crosswalk_path')}) == 3,
         'periscope.distinct_source_records')
    need(r['evidence_mode'] in ('synthetic_fixture', 'manual_transfer', 'live_tenant'), 'periscope.evidence_mode')
    need(r['target_surface'] in ('app', 'dashboard', 'both'), 'periscope.target_surface')
    need(r['route'] in ('unselected', 'reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
         and (r['route'] == 'unselected' or text(r['route_reference'])), 'periscope.route')
    state(r['state'])
    need(type(r['list_dashboards']) is bool, 'periscope.inventory_operation')
    bounds = {'max_requests_per_invocation': (1, 60), 'max_total_requests': (1, 1000),
              'max_total_bytes': (1, 128000000), 'max_response_bytes': (1, F.MAX_FILE),
              'max_elapsed_seconds': (1, 86400), 'max_attempts_per_operation': (1, 5)}
    for key, (lo, hi) in bounds.items():
        need(type(r[key]) is int and lo <= r[key] <= hi, 'periscope.budget')
    hosts = r['render_download_hosts']
    need(type(hosts) is list and len(hosts) <= 10 and len(set(hosts)) == len(hosts) and
         all(type(h) is str and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,250})', h)
             and h.endswith('.s3.amazonaws.com') and h.startswith('periscope-render-') for h in hosts),
         'periscope.reviewed_render_hosts_required')
    render = r['render']
    if render is not None:
        need(type(render) is dict and set(render) == {'render_id', 'dashboard_ts', 'refresh_intent', 'widget_limit', 'limit_reference'}
             and local_id(render['render_id']) and type(render['widget_limit']) is int
             and 1 <= render['widget_limit'] <= 500 and text(render['limit_reference']) and hosts,
             'periscope.render_contract')
        ts = render['dashboard_ts']
        need((ts is None and render['refresh_intent'] == 'no_freshness_refresh_requested') or
             (type(ts) is int and 0 <= ts <= 4102444800 and render['refresh_intent'] == 'allow_refresh_older_than_dashboard_ts'),
             'periscope.render_refresh_intent')
        need(not r['state']['parameters'], 'periscope.render_parameters_unsupported')
    F.secret_check(r)
    return r


def validate_inventory(value, request, report):
    need(type(value) is dict and set(value) == {'schema_version', 'method', 'reference', 'completeness', 'objects'}
         and value['schema_version'] == 'periscope-source-enumeration.v1'
         and value['method'] == 'separate_source_enumeration' and text(value['reference'])
         and value['completeness'] in ('partial', 'selected_scope_declared'), 'periscope.independent_enumeration_required')
    rows = value['objects']
    need(type(rows) is list and 1 <= len(rows) <= 2000, 'periscope.inventory_bound')
    indexed, adapter = {}, {o['id']: o for o in report['objects']}
    for row in rows:
        need(type(row) is dict and set(row) == {'key', 'kind', 'name', 'parent_key', 'source_object_id',
             'disposition', 'disposition_reference', 'evidence_reference', 'configuration'}
             and local_id(row['key']) and row['key'] not in indexed
             and row['kind'] in ('dashboard', 'visual', 'control', 'placement', 'content', 'unknown')
             and type(row['name']) is str and type(row['configuration']) is dict
             and row['disposition'] in ('include', 'manual_review', 'unsupported', 'out_of_scope')
             and text(row['disposition_reference']) and text(row['evidence_reference']), 'periscope.inventory_record')
        sid = row['source_object_id']
        need(sid is None or (text(sid) and sid in adapter), 'periscope.inventory_adapter_binding')
        if sid is not None:
            expected = {'dashboard': 'dashboard', 'chart': 'visual', 'filter': 'control', 'parameter': 'control'}.get(adapter[sid]['kind'])
            need(expected is None or row['kind'] == expected or row['kind'] == 'placement', 'periscope.inventory_kind_mismatch')
        indexed[row['key']] = row
    need(request['dashboard_key'] in indexed and indexed[request['dashboard_key']]['kind'] == 'dashboard',
         'periscope.selected_dashboard_missing')
    primary = [row['source_object_id'] for row in rows if row['kind'] != 'placement' and row['source_object_id'] is not None]
    need(len(primary) == len(set(primary)), 'periscope.duplicate_primary_object')
    required = {o['id'] for o in report['objects'] if o['kind'] in ('dashboard', 'chart', 'filter', 'parameter')}
    need(required <= set(primary), 'periscope.adapter_object_omitted_from_enumeration')
    for row in rows:
        parent = row['parent_key']
        need(parent is None or (parent in indexed and parent != row['key']), 'periscope.inventory_parent')
        if row['key'] != request['dashboard_key']:
            seen = {row['key']}
            while parent is not None:
                need(parent not in seen, 'periscope.inventory_cycle')
                seen.add(parent)
                parent = indexed[parent]['parent_key']
            need(request['dashboard_key'] in seen, 'periscope.inventory_scope')
        if row['kind'] == 'placement':
            target = row['configuration'].get('visual_key')
            need(target in indexed and indexed[target]['kind'] in ('visual', 'content', 'unknown'),
                 'periscope.placement_target')
    F.secret_check(value)
    return indexed


def validate_crosswalk(value, inventory, report):
    need(type(value) is dict and set(value) == {'schema_version', 'reference', 'rows'}
         and value['schema_version'] == 'periscope-identity-crosswalk.v1' and text(value['reference'])
         and type(value['rows']) is list and len(value['rows']) <= 2000, 'periscope.crosswalk_contract')
    indexed, seen = {}, set()
    adapter = {o['id']: o for o in report['objects']}
    for row in value['rows']:
        need(type(row) is dict and set(row) == {'key', 'git_token', 'api_id', 'numeric_id', 'reference'}
             and row['key'] in inventory and row['key'] not in indexed and text(row['reference']), 'periscope.crosswalk_record')
        need(row['git_token'] is None or (type(row['git_token']) is str and re.fullmatch(r'[A-Za-z0-9]{32}', row['git_token'])),
             'periscope.git_token')
        need(row['api_id'] is None or text(row['api_id'], 256), 'periscope.api_identity')
        need(row['numeric_id'] is None or (type(row['numeric_id']) is int and row['numeric_id'] > 0),
             'periscope.numeric_identity')
        sid = inventory[row['key']]['source_object_id']
        if sid is not None:
            need(row['git_token'] == adapter[sid]['native_id'], 'periscope.crosswalk_git_mismatch')
        for kind in ('git_token', 'api_id', 'numeric_id'):
            if row[kind] is not None:
                identity = (inventory[row['key']]['kind'], kind, row[kind])
                need(identity not in seen, 'periscope.crosswalk_ambiguity')
                seen.add(identity)
        indexed[row['key']] = row
    need(set(indexed) == {k for k, row in inventory.items() if row['kind'] in ('dashboard', 'visual')},
         'periscope.crosswalk_visual_denominator')
    return indexed


def source_fingerprint(source):
    return sha({k: source[k] for k in ('adapter_report_sha256', 'inventory_sha256', 'crosswalk_sha256', 'files')})


def file_pins(value):
    source = value['source']
    return ([source[k] for k in ('adapter_report_file', 'inventory_file', 'crosswalk_file')]
            + source['files'] + value['attachments'] + [p['file'] for p in value['api_pages']]
            + ([value['render_job']['response_file']] if value.get('render_job') else []))


def save(root, value):
    value['journal_revision'] += 1
    value.pop('content_hash', None)
    value['content_hash'] = sha(value)
    raw = encoded(value)
    snapshots = list(root.glob('capture-*.json'))
    need(len(snapshots) < 5000 and len(raw) + sum(F.no_links(p).stat().st_size for p in snapshots) <= MAX_JOURNAL_BYTES,
         'periscope.journal_budget')
    path = F.write_once(root, 'capture-%06d.json' % value['journal_revision'], raw)
    return root / path['path']


def import_local(request, source_root, directory, *, allow_source_read=False):
    need(allow_source_read, 'periscope.source_read_grant_required')
    r = validate_request(request)
    source_root, root = F.no_links(source_root), F.private_directory(directory)
    need(source_root.is_dir() and not list(root.iterdir()), 'periscope.new_directory_required')
    blobs = {k: F.read_file(source_root / r[k], F.MAX_FILE) for k in ('adapter_report_path', 'inventory_path', 'crosswalk_path')}
    report, inventory, crosswalk = (F.decode(blobs[k]) for k in ('adapter_report_path', 'inventory_path', 'crosswalk_path'))
    module('periscope_visual').validate(report, r['producer_revision'])
    indexed = validate_inventory(inventory, r, report)
    identities = validate_crosswalk(crosswalk, indexed, report)
    need(not r['render'] or identities[r['dashboard_key']]['numeric_id'] is not None, 'periscope.render_numeric_id_required')
    need(not r['list_dashboards'] or identities[r['dashboard_key']]['api_id'] is not None, 'periscope.inventory_api_id_required')
    originals, total, seen = [], sum(map(len, blobs.values())), set()
    need(len(report['source_files']) <= F.MAX_FILES, 'periscope.source_file_limit')
    for item in report['source_files']:
        path = F.source_path(item['path'])
        folded = unicodedata.normalize('NFC', path).casefold()
        need(folded not in seen and not any(folded.startswith(p + '/') or p.startswith(folded + '/') for p in seen),
             'periscope.source_path_collision')
        seen.add(folded)
        raw = F.read_file(source_root / path, F.MAX_FILE)
        need(F.raw_sha(raw) == item['sha256'], 'periscope.original_source_hash_mismatch')
        total += len(raw)
        need(total <= min(r['max_total_bytes'], F.MAX_TOTAL), 'periscope.source_byte_limit')
        originals.append((path, raw))
    source = {'adapter_report': report, 'adapter_report_sha256': sha(report),
              'inventory': inventory, 'inventory_sha256': sha(inventory),
              'crosswalk': crosswalk, 'crosswalk_sha256': sha(crosswalk), 'files': []}
    for key, path_key in (('adapter_report', 'adapter_report_path'), ('inventory', 'inventory_path'), ('crosswalk', 'crosswalk_path')):
        source[key + '_file'] = F.write_once(root, key + '.json', blobs[path_key])
    for i, (path, raw) in enumerate(originals):
        source['files'].append({**F.write_once(root, 'source-%04d.bin' % i, raw), 'source_path': path, 'interpretation': 'inert_bytes'})
    source['definition_fingerprint'] = source_fingerprint(source)
    value = {'schema_version': ENVELOPE, 'capture_id': r['capture_id'], 'request': r,
             'request_sha256': sha(r), 'source': source, 'attachments': [], 'api_pages': [],
             'render_job': None, 'operations': [], 'status': 'partial', 'journal_revision': 0,
             'previous_capture': None, 'created_at_epoch': utcnow(), 'request_count': 0,
             'network_bytes': 0, 'retry_not_before_epoch': 0, 'gaps': list(BASE_GAPS),
             'target_write_authority': False, 'source_execution': False,
             'native_validation': 'not_performed', 'business_acceptance': 'not_assessed'}
    output = save(root, value)
    return {'status': value['status'], 'output': str(output), 'capture': value}


def check_capture(path):
    path = F.no_links(path)
    value = F.decode(F.read_file(path, F.MAX_JSON))
    visual = module('periscope_visual')
    visual.validate_capture(value)
    return visual.verify_capture_files(value, path.parent)


def load_latest(directory, request=None):
    root = F.private_directory(directory)
    paths = sorted(root.glob('capture-*.json'))
    need(paths and len(paths) <= 5000, 'periscope.capture_journal_missing_or_limit')
    need(sum(F.no_links(p).stat().st_size for p in paths) <= MAX_JOURNAL_BYTES, 'periscope.journal_budget')
    previous = None
    for i, path in enumerate(paths, 1):
        need(path.name == 'capture-%06d.json' % i, 'periscope.journal_sequence')
        value = F.decode(F.read_file(path, F.MAX_JSON))
        need(value.get('journal_revision') == i and value.get('previous_capture') == previous,
             'periscope.journal_chain')
        module('periscope_visual').validate_capture(value)
        previous = {'path': path.name, 'sha256': F.raw_sha(F.read_file(path, F.MAX_JSON))}
    module('periscope_visual').verify_capture_files(value, root)
    need(request is None or value['request'] == validate_request(request), 'periscope.resume_request_changed')
    value['previous_capture'] = previous
    return value, paths[-1]


def advance(root, value):
    output = save(root, value)
    value['previous_capture'] = {'path': output.name, 'sha256': F.raw_sha(F.read_file(output, F.MAX_JSON))}
    return output


def validate_attachment(row, request, inventory):
    required = {'attachment_id', 'object_key', 'format', 'origin', 'result_scope', 'observed_state',
                'population', 'freshness', 'completeness', 'reference'}
    derived = {'source_path', 'path', 'sha256', 'bytes', 'request_sha256', 'definition_fingerprint',
               'requested_state_sha256', 'inspection', 'acquisition'}
    need(type(row) is dict and required <= set(row) <= required | derived and local_id(row['attachment_id'])
         and row['object_key'] in inventory and row['format'] in ('csv', 'png', 'pdf')
         and text(row['reference']), 'periscope.attachment_contract')
    need(row['origin'] in ('full', 'displayed', 'transformed', 'unknown')
         and row['result_scope'] in ('query_result', 'transformed', 'displayed', 'unknown'), 'periscope.result_origin')
    need(not (row['origin'] == 'displayed' and row['result_scope'] != 'displayed') and
         not (row['origin'] == 'transformed' and row['result_scope'] != 'transformed'), 'periscope.result_origin_conflict')
    observed = row['observed_state']
    need(observed is None or (type(observed) is dict and set(observed) == {'state', 'observed_at', 'reference'}
         and text(observed['observed_at']) and text(observed['reference'])), 'periscope.observed_state')
    if observed is not None:
        state(observed['state'])
    population, freshness, completeness = row['population'], row['freshness'], row['completeness']
    need(type(population) is dict and set(population) == {'key', 'description', 'reference'} and
         all(population[k] is None or text(population[k]) for k in population), 'periscope.population')
    need(type(freshness) is dict and set(freshness) == {'data_watermark', 'observed_at', 'reference'} and
         all(freshness[k] is None or text(freshness[k]) for k in freshness), 'periscope.freshness')
    need(type(completeness) is dict and set(completeness) == {'status', 'reference', 'row_count'} and
         completeness['status'] in ('complete', 'partial', 'unknown')
         and (completeness['reference'] is None or text(completeness['reference']))
         and (completeness['row_count'] is None or (type(completeness['row_count']) is int and 0 <= completeness['row_count'] <= 100000)),
         'periscope.result_completeness')
    if completeness['status'] == 'complete':
        need(row['format'] == 'csv' and row['origin'] != 'unknown' and row['result_scope'] != 'unknown'
             and observed is not None and all(population.values()) and all(freshness.values())
             and text(completeness['reference']) and type(completeness['row_count']) is int,
             'periscope.complete_result_evidence_required')
    F.secret_check(row)


def inspect_attachment(raw, format):
    need(type(raw) is bytes and len(raw) <= F.MAX_FILE, 'periscope.attachment_byte_limit')
    if format == 'csv':
        import csv
        import io
        try:
            value = raw.decode('utf-8-sig')
            need('\x00' not in value, 'periscope.invalid_csv')
            reader = csv.reader(io.StringIO(value), strict=True)
            headers = next(reader)
            need(1 <= len(headers) <= 1000 and all(type(h) is str for h in headers), 'periscope.csv_headers')
            count = 0
            for row in reader:
                count += 1
                need(count <= 100000 and len(row) == len(headers), 'periscope.csv_row_bound_or_shape')
            return {'row_count': count, 'headers': headers}
        except (ValueError, UnicodeError, csv.Error, StopIteration):
            raise F.CaptureError('periscope.invalid_csv') from None
    if format == 'png':
        return F.png_info(raw)
    need(format == 'pdf' and raw.startswith(b'%PDF-') and b'%%EOF' in raw[-1024:], 'periscope.invalid_pdf')
    return {'validation': 'signature_only_no_pdf_decoder_or_render'}


def _import_evidence(capture_path, spec, source_root):
    path = F.no_links(capture_path)
    value, latest = load_latest(path.parent)
    need(path == latest and type(spec) is dict and set(spec) == {'schema_version', 'attachments'}
         and spec['schema_version'] == 'periscope-supplied-evidence.v1'
         and type(spec['attachments']) is list and len(spec['attachments']) <= 100, 'periscope.evidence_import')
    root, source_root = path.parent, F.no_links(source_root)
    inventory = {o['key']: o for o in value['source']['inventory']['objects']}
    seen = {a['attachment_id'] for a in value['attachments']}
    need(len(seen) + len(spec['attachments']) <= 500, 'periscope.attachment_count_limit')
    pending = []
    total = sum(p['bytes'] for p in file_pins(value))
    for row in spec['attachments']:
        need(type(row) is dict and 'source_path' in row, 'periscope.evidence_source_path')
        validate_attachment(row, value['request'], inventory)
        need(row['attachment_id'] not in seen, 'periscope.duplicate_attachment')
        seen.add(row['attachment_id'])
        raw = F.read_file(source_root / F.source_path(row['source_path']))
        info = inspect_attachment(raw, row['format'])
        need(row['format'] != 'csv' or row['completeness']['row_count'] in (None, info['row_count']),
             'periscope.csv_count_contradiction')
        total += len(raw)
        need(total <= value['request']['max_total_bytes'], 'periscope.capture_byte_limit')
        pending.append((row, raw, info))
    for row, raw, info in pending:
        record = {k: copy.deepcopy(v) for k, v in row.items() if k != 'source_path'}
        record.update(F.write_once(root, 'attachment-' + row['attachment_id'] + '.' + row['format'], raw))
        record.update(request_sha256=value['request_sha256'], definition_fingerprint=value['source']['definition_fingerprint'],
                      requested_state_sha256=sha(value['request']['state']), inspection=info, acquisition='supplied')
        value['attachments'].append(record)
    output = advance(root, value)
    return {'status': value['status'], 'output': str(output), 'capture': F.decode(F.read_file(output, F.MAX_JSON))}


def import_evidence(capture_path, spec, source_root):
    path = F.no_links(capture_path)
    root = F.private_directory(path.parent)
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _import_evidence(path, spec, source_root)
    finally:
        os.close(fd)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise F.CaptureError('periscope.redirect_rejected')


def default_transport(method, url, headers, body, maximum, timeout):
    """Fixed URLs are checked by Session; no environment proxy or redirects."""
    opener = build_opener(ProxyHandler({}), NoRedirect())
    request = Request(url, data=body, headers=headers, method=method)
    started = time.monotonic()
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        status = response.code
        need(response.geturl() == url and not 300 <= status < 400, 'periscope.redirect_rejected')
        chunks, total = [], 0
        while True:
            need(time.monotonic() - started < timeout, 'periscope.response_deadline')
            raw = response.read1(min(65536, maximum + 1 - total))
            if not raw:
                break
            total += len(raw)
            need(total <= maximum, 'periscope.response_byte_limit')
            chunks.append(raw)
        return status, dict(response.headers), b''.join(chunks)


def render_url(url, request):
    need(type(url) is str and len(url) <= 8192, 'periscope.render_url')
    p = urlsplit(url)
    need(p.scheme == 'https' and p.hostname in request['render_download_hosts'] and p.netloc == p.hostname
         and not p.username and not p.password and not p.fragment and p.path.endswith('.pdf')
         and not any(c in url for c in ('\r', '\n', '\\')), 'periscope.render_url_scope')
    return url


class StopCapture(Exception):
    pass


class Session:
    def __init__(self, root, value, authority, transport, now):
        self.root, self.value, self.authority, self.transport, self.now = root, value, authority, transport, now
        self.invocation_count = 0

    def call(self, operation, method, url, body=None, *, key):
        value, r = self.value, self.value['request']
        now = self.now()
        need(callable(self.authority), 'periscope.host_authority_unconfigured')
        if (value['request_count'] >= r['max_total_requests'] or self.invocation_count >= r['max_requests_per_invocation']
            or value['network_bytes'] >= r['max_total_bytes'] or now - value['created_at_epoch'] >= r['max_elapsed_seconds']
            or now < value['retry_not_before_epoch']):
            raise StopCapture()
        previous = [o for o in value['operations'] if o['key'] == key]
        if len(previous) >= r['max_attempts_per_operation']:
            raise StopCapture()
        if method == 'POST' and any(o['status'] in ('pending', 'uncertain', 'success') for o in previous):
            if 'render_submission_uncertain_no_blind_retry' not in value['gaps']:
                value['gaps'].append('render_submission_uncertain_no_blind_retry')
                advance(self.root, value)
            raise StopCapture()
        if sum(o['started_at_epoch'] > now - 60 for o in value['operations']) >= 60:
            value['retry_not_before_epoch'] = now + 60
            advance(self.root, value)
            raise StopCapture()
        if operation == 'inventory':
            need(method == 'GET' and url.startswith(API_ORIGIN + '/api/v1/dashboards') and
                 urlsplit(url).path == '/api/v1/dashboards', 'periscope.inventory_route')
        elif operation == 'render':
            need(method == 'POST' and url == RENDER_ORIGIN + '/api/v1/screenshot_requests', 'periscope.render_route')
        else:
            need(operation == 'download' and method == 'GET', 'periscope.operation_rejected')
            render_url(url, r)
        raw_body = None if body is None else encoded(body)
        fingerprint = {'request_sha256': value['request_sha256'], 'method': method, 'url': url,
                       'body_sha256': None if raw_body is None else F.raw_sha(raw_body)}
        grant = self.authority(operation, fingerprint)
        headers = {'Accept': 'application/pdf' if operation == 'download' else 'application/json'}
        if operation == 'download':
            need(grant is True, 'periscope.download_authority_required')
        else:
            need(type(grant) is str and 0 < len(grant) <= 4096 and not any(c in grant for c in '\r\n:'),
                 'periscope.host_credential_required')
            headers['HTTP-X-PARTNER-AUTH'] = r['site_name'] + ':' + grant
        if raw_body is not None:
            headers['Content-Type'] = 'application/json'
        record = {'key': key, 'operation': operation, 'method': method, 'fingerprint_sha256': sha(fingerprint),
                  'started_at_epoch': now, 'status': 'pending'}
        value['operations'].append(record)
        value['request_count'] += 1
        self.invocation_count += 1
        advance(self.root, value)  # POST uncertainty survives interruption before any response.
        try:
            base_bytes = sum(p['bytes'] for p in [value['source'][k] for k in
                ('adapter_report_file', 'inventory_file', 'crosswalk_file')] + value['source']['files'])
            base_bytes += sum(p['bytes'] for p in value['attachments'] if p['acquisition'] == 'supplied')
            maximum = min(r['max_response_bytes'], r['max_total_bytes'] - base_bytes - value['network_bytes'])
            need(maximum > 0, 'periscope.total_byte_limit')
            timeout = min(20, r['max_elapsed_seconds'] - (now - value['created_at_epoch']))
            status, response_headers, raw = self.transport(method, url, headers, raw_body, maximum, timeout)
            need(type(status) is int and type(raw) is bytes and len(raw) <= maximum, 'periscope.transport_contract')
            value['network_bytes'] += len(raw)
            need(not 300 <= status < 400, 'periscope.redirect_rejected')
        except Exception:
            record['status'] = 'uncertain' if method == 'POST' else 'failed'
            value['gaps'].append('source_request_failed_redacted')
            advance(self.root, value)
            raise StopCapture() from None
        record['http_status'] = status
        record['response_sha256'] = F.raw_sha(raw)
        record['response_bytes'] = len(raw)
        record['status'] = 'success' if status == 200 else ('uncertain' if method == 'POST' and status >= 500 else 'rejected')
        if status == 429:
            value['retry_not_before_epoch'] = now + 60
        advance(self.root, value)
        if status != 200:
            raise StopCapture()
        return raw


def dashboard_page(raw):
    data = F.decode(raw)
    need(type(data) is dict and {'next_page_start', 'total_items', 'items_this_page', 'dashboards'} <= set(data)
         and type(data['dashboards']) is list and len(data['dashboards']) <= 1000
         and type(data['total_items']) is int and 0 <= data['total_items'] <= 100000
         and type(data['items_this_page']) is int and data['items_this_page'] == len(data['dashboards'])
         and (data['next_page_start'] is None or text(data['next_page_start'], 1000)), 'periscope.dashboard_page_contract')
    ids = []
    for row in data['dashboards']:
        need(type(row) is dict and text(row.get('id'), 256) and type(row.get('name')) is str, 'periscope.dashboard_identity')
        ids.append(row['id'])
    need(len(set(ids)) == len(ids), 'periscope.duplicate_dashboard_id')
    F.secret_check(data)
    return data


def capture(request, directory, *, authority=None, transport=None, resume=True, now=None):
    """Extend imported immutable source; host grants fixed read/render/download routes.

No credential may be placed in request/envelope. Render URLs are bearer-like
capabilities: retained only in private original response bytes, never stdout.
"""
    need(callable(authority), 'periscope.host_authority_unconfigured')
    r = validate_request(request, require_service=True)
    need(resume is True, 'periscope.import_snapshot_before_connected_capture')
    root = F.private_directory(directory)
    fd = os.open(F.no_links(root / '.capture.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        value, output = load_latest(root, r)
        if value['status'] == 'blocked':
            return {'status': 'blocked', 'output': str(output), 'capture': F.decode(F.read_file(output, F.MAX_JSON))}
        session = Session(root, value, authority, transport or default_transport, now or utcnow)
        try:
            if r['list_dashboards']:
                while not value['api_pages'] or value['api_pages'][-1]['next_page_start'] is not None:
                    token = value['api_pages'][-1]['next_page_start'] if value['api_pages'] else None
                    url = API_ORIGIN + '/api/v1/dashboards' + ('?' + urlencode({'next_page_start': token}) if token is not None else '')
                    raw = session.call('inventory', 'GET', url, key='inventory.%d' % len(value['api_pages']))
                    data = dashboard_page(raw)
                    need(not value['api_pages'] or data['total_items'] == value['api_pages'][0]['total_items'], 'periscope.pagination_total_changed')
                    known = {did for p in value['api_pages'] for did in p['dashboard_ids']}
                    ids = [d['id'] for d in data['dashboards']]
                    need(not known.intersection(ids) and len(known) + len(ids) <= data['total_items'], 'periscope.pagination_overlap')
                    need(data['next_page_start'] is None or (ids and data['next_page_start'] not in
                         [p['next_page_start'] for p in value['api_pages']]), 'periscope.pagination_cycle')
                    if data['next_page_start'] is None:
                        need(len(known) + len(ids) == data['total_items'], 'periscope.pagination_incomplete')
                    pin = F.write_once(root, 'dashboard-page-%04d.json' % len(value['api_pages']), raw)
                    value['api_pages'].append({'file': pin, 'dashboard_ids': ids, 'total_items': data['total_items'],
                                              'next_page_start': data['next_page_start']})
                    output = advance(root, value)
                api_id = next(i['api_id'] for i in value['source']['crosswalk']['rows'] if i['key'] == r['dashboard_key'])
                need(api_id in {i for p in value['api_pages'] for i in p['dashboard_ids']}, 'periscope.selected_api_dashboard_unobserved')
                if 'api_listing_not_visual_inventory_or_effective_access' not in value['gaps']:
                    value['gaps'].append('api_listing_not_visual_inventory_or_effective_access')
            if r['render']:
                render = r['render']
                if value['render_job'] is None:
                    numeric = next(i['numeric_id'] for i in value['source']['crosswalk']['rows'] if i['key'] == r['dashboard_key'])
                    body = {'dashboard_id': numeric, 'filters': r['state']['filters']}
                    for key in ('aggregation', 'daterange'):
                        if r['state'][key] is not None:
                            body[key] = r['state'][key]
                    if render['dashboard_ts'] is not None:
                        body['dashboard_ts'] = render['dashboard_ts']
                    raw = session.call('render', 'POST', RENDER_ORIGIN + '/api/v1/screenshot_requests',
                                       {'data': body}, key='render.' + render['render_id'])
                    response = F.decode(raw)
                    need(type(response) is dict and set(response) == {'url'}, 'periscope.render_response')
                    render_url(response['url'], r)
                    value['render_job'] = {'response_file': F.write_once(root, 'render-response.json', raw),
                                           'created_at_epoch': session.now(), 'body_sha256': sha({'data': body}),
                                           'status': 'awaiting_pdf', 'expires_after_seconds': 259200}
                    output = advance(root, value)
                job = value['render_job']
                if job['status'] == 'awaiting_pdf':
                    need(session.now() - job['created_at_epoch'] < 259200, 'periscope.render_url_expired')
                    url = F.decode(F.read_pin(root, job['response_file']))['url']
                    raw = session.call('download', 'GET', url, key='render-download.' + render['render_id'])
                    if raw.strip() == b'Screenshot not ready.':
                        value['retry_not_before_epoch'] = session.now() + 60
                        output = advance(root, value)
                        raise StopCapture()
                    info = inspect_attachment(raw, 'pdf')
                    a = {'attachment_id': render['render_id'], 'object_key': r['dashboard_key'], 'format': 'pdf',
                         'origin': 'displayed', 'result_scope': 'displayed', 'observed_state': None,
                         'population': {'key': None, 'description': None, 'reference': None},
                         'freshness': {'data_watermark': None, 'observed_at': None, 'reference': None},
                         'completeness': {'status': 'unknown', 'reference': None, 'row_count': None},
                         'reference': 'render_api_response', 'request_sha256': value['request_sha256'],
                         'definition_fingerprint': value['source']['definition_fingerprint'],
                         'requested_state_sha256': sha(r['state']), 'inspection': info, 'acquisition': 'render_api'}
                    a.update(F.write_once(root, 'render-' + render['render_id'] + '.pdf', raw))
                    value['attachments'].append(a)
                    job['status'] = 'pdf_bytes_received'
                    value['gaps'].append('pdf_bytes_not_visual_inspection_or_widget_completeness')
            value['status'] = 'acquired_requested_operations'
            output = advance(root, value)
        except StopCapture:
            pass
        except (ValueError, TypeError, KeyError, OSError):
            value['status'] = 'blocked'
            value['gaps'].append('source_contract_or_scope_rejected')
            output = advance(root, value)
        output = sorted(root.glob('capture-*.json'))[-1]
        return {'status': value['status'], 'output': str(output), 'capture': F.decode(F.read_file(output, F.MAX_JSON))}
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    local = sub.add_parser('import-local')
    local.add_argument('--request', required=True, type=Path)
    local.add_argument('--source-root', required=True, type=Path)
    local.add_argument('--directory', required=True, type=Path)
    local.add_argument('--allow-source-read', action='store_true')
    evidence = sub.add_parser('import-evidence')
    evidence.add_argument('--capture', required=True, type=Path)
    evidence.add_argument('--spec', required=True, type=Path)
    evidence.add_argument('--source-root', required=True, type=Path)
    check = sub.add_parser('check')
    check.add_argument('--capture', required=True, type=Path)
    # Deliberately no CLI secret/grant flags. The host calls capture in process.
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-local':
            result = import_local(F.decode(F.read_file(args.request)), args.source_root, args.directory,
                                  allow_source_read=args.allow_source_read)
        elif args.command == 'import-evidence':
            result = import_evidence(args.capture, F.decode(F.read_file(args.spec)), args.source_root)
        else:
            result = check_capture(args.capture)
        print(encoded({'status': result['status'], 'native_validation': 'not_performed'}).decode())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        print('Periscope source capture rejected; review the scoped contract and local evidence.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
