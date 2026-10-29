"""Passive Crystal extraction evidence. Never opens RPT, loads SDKs or runs formulas.

The extraction schema is package-owned, not a SAP serialization. Supplied SDK or
manual provenance is a declaration; every original object remains an obligation.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = 'crystal-report-snapshot.v1'
EXTRACT_SCHEMA = 'crystal-report-extract.v1'
KINDS = {'report', 'section', 'field', 'parameter', 'group', 'formula', 'running_total',
         'subreport', 'query', 'table', 'command', 'filter', 'image', 'chart', 'crosstab',
         'action', 'security', 'schedule', 'unknown'}
REVIEW_KINDS = {'formula', 'running_total', 'subreport', 'command', 'security', 'schedule', 'unknown'}
NORMAL_KINDS = {'report': 'workbook', 'section': 'layout', 'field': 'definition',
                'parameter': 'parameter', 'group': 'layout', 'formula': 'definition',
                'running_total': 'definition', 'subreport': 'placement', 'query': 'query',
                'table': 'definition', 'command': 'query', 'filter': 'filter', 'image': 'content',
                'chart': 'visual', 'crosstab': 'visual', 'action': 'action', 'security': 'definition',
                'schedule': 'action', 'unknown': 'unknown'}


def need(ok, code):
    if not ok:
        raise ValueError('crystal.' + code)


_path = Path(__file__).with_name('powerbi_capture_files.py')
need(not any(p.is_symlink() for p in (_path, *_path.parents)), 'module_symlink')
_spec = importlib.util.spec_from_file_location('crystal_report_files', _path)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
encoded = F.encoded


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 2048 and all(ord(c) >= 32 for c in value)


def origin(value):
    if not text(value):
        return False
    try:
        p = urlsplit(value)
        return (p.scheme == 'https' and p.hostname and p.hostname == p.hostname.lower()
                and not p.username and not p.password and not p.path and not p.query and not p.fragment
                and p.netloc == p.hostname + (':' + str(p.port) if p.port else '')
                and re.fullmatch(r'[a-z0-9][a-z0-9.-]*', p.hostname) is not None)
    except ValueError:
        return False


def read_extraction(raw):
    """Read an explicit supplier extraction, retaining arbitrary properties inertly."""
    need(type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024, 'extract_byte_limit')
    F.safe_text(raw)
    value = F.decode(raw)
    F.secret_check(value)
    need(type(value) is dict and set(value) == {'schema_version', 'report', 'objects', 'dependencies'}
         and value['schema_version'] == EXTRACT_SCHEMA, 'extract_contract')
    need(type(value['report']) is dict and value['report'], 'report_metadata_required')
    objects = value['objects']
    need(type(objects) is list and 0 < len(objects) <= 2000, 'objects_required')
    indexed = {}
    for row in objects:
        need(type(row) is dict and set(row) == {'id', 'parent_id', 'kind', 'name', 'properties'}
             and text(row['id']) and row['id'] not in indexed and row['kind'] in KINDS
             and (row['parent_id'] is None or text(row['parent_id']))
             and (row['name'] is None or text(row['name'])) and type(row['properties']) is dict, 'object_contract')
        indexed[row['id']] = row
    for row in objects:
        seen, item = set(), row
        while item is not None:
            need(item['id'] not in seen, 'object_parent_cycle')
            seen.add(item['id'])
            parent = item['parent_id']
            need(parent is None or parent in indexed, 'object_parent_missing')
            item = indexed.get(parent)
    need(type(value['dependencies']) is list and len(value['dependencies']) <= 2000, 'dependencies_limit')
    for dep in value['dependencies']:
        need(type(dep) is dict and set(dep) == {'from_id', 'target_id', 'kind', 'reference'}
             and dep['from_id'] in indexed and (dep['target_id'] is None or dep['target_id'] in indexed)
             and text(dep['kind']) and text(dep['reference']), 'dependency_contract')
    return value


def validate_snapshot(value):
    raw = encoded(value)
    need(len(raw) <= 8 * 1024 * 1024, 'snapshot_byte_limit')
    F.decode(raw); F.secret_check(value); F.safe_text(raw)
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'extraction', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    ident = value['identity']
    need(type(ident) is dict and set(ident) == {'source_platform', 'source_origin', 'product_version', 'engine', 'principal_ref',
         'report_id', 'cuid', 'content_path', 'reference'} and ident['engine'] in {'crystal_classic', 'crystal_enterprise', 'unknown'}
         and ident['source_platform'] == 'crystal'
         and all(text(ident[k]) for k in ('product_version', 'principal_ref', 'reference'))
         and all(ident[k] is None or text(ident[k]) for k in ('source_origin', 'report_id', 'cuid', 'content_path')),
         'identity_contract')
    need(ident['source_origin'] is None or origin(ident['source_origin']), 'source_origin')
    extract = value['extraction']
    need(type(extract) is dict and set(extract) == {'content', 'bytes', 'sha256', 'encoding', 'reference',
         'method', 'extractor_version'} and extract['encoding'] == 'utf-8' and type(extract['content']) is str
         and type(extract['bytes']) is int and extract['method'] in {'supplied_sdk_extract', 'supplied_manual_extract'}
         and text(extract['extractor_version']) and text(extract['reference']), 'extraction_contract')
    content = extract['content'].encode('utf-8')
    need(len(content) == extract['bytes'] and sha(content) == extract['sha256'], 'extraction_hash')
    parsed = read_extraction(content)
    indexed = {o['id']: o for o in parsed['objects']}
    inv = value['inventory']
    need(type(inv) is dict and set(inv) == {'reference', 'completeness', 'items'} and text(inv['reference'])
         and inv['completeness'] in {'partial', 'selected_scope_declared'}
         and type(inv['items']) is list and len(inv['items']) <= 2000, 'inventory_contract')
    keys = set()
    for row in inv['items']:
        need(type(row) is dict and set(row) == {'key', 'object_id', 'kind', 'disposition', 'reference', 'configuration'}
             and text(row['key']) and row['key'] not in keys
             and (row['object_id'] is None or row['object_id'] in indexed) and row['kind'] in KINDS
             and row['disposition'] in {'include', 'manual_review', 'defer', 'exclude', 'unavailable', 'out_of_scope'}
             and text(row['reference']) and type(row['configuration']) is dict, 'inventory_item')
        if row['object_id'] is not None:
            need(row['kind'] == indexed[row['object_id']]['kind'], 'inventory_kind_mismatch')
        keys.add(row['key'])
    need(type(value['gaps']) is list and len(value['gaps']) <= 2000, 'gaps_contract')
    return value


def make_snapshot(raw, identity, inventory, reference, method='supplied_manual_extract', extractor_version='unverified'):
    read_extraction(raw)
    value = {'schema_version': SCHEMA, 'identity': copy.deepcopy(identity),
             'extraction': {'content': raw.decode('utf-8'), 'bytes': len(raw), 'sha256': sha(raw), 'encoding': 'utf-8',
                 'reference': reference, 'method': method, 'extractor_version': extractor_version},
             'inventory': copy.deepcopy(inventory), 'gaps': []}
    validate_snapshot(value)
    return value


def scope_item(value, key):
    validate_snapshot(value)
    parsed = read_extraction(value['extraction']['content'].encode('utf-8'))
    indexed = {r['key']: r for r in value['inventory']['items']}
    return _scope_item(key, parsed, indexed)


def _scope_item(key, parsed, indexed):
    need(key in indexed, 'object_scope_missing')
    row = indexed[key]
    objects = {o['id']: o for o in parsed['objects']}
    obj = objects.get(row['object_id'])
    ancestors, current = set(), obj
    while current:
        ancestors.add(current['id']); current = objects.get(current['parent_id'])
    related = [r for r in indexed.values() if r['object_id'] in ancestors] + [row]
    restricted = any(r['disposition'] in {'exclude', 'unavailable', 'out_of_scope'} or r['configuration'].get('access') in {'denied', 'unavailable'}
                     or r['configuration'].get('private') is True and not text(r['configuration'].get('selection_reference')) for r in related)
    targets = [d['target_id'] for d in parsed['dependencies'] if d['from_id'] == row['object_id'] and d['kind'] == 'dataset_binding']
    if obj and obj['kind'] == 'query':
        targets = [obj['id']]
    dataset = targets[0] if len(targets) == 1 and targets[0] in objects and objects[targets[0]]['kind'] == 'query' else None
    dataset_rows = [r for r in indexed.values() if r['object_id'] == dataset] if dataset else []
    dataset_ancestors, current = set(), objects.get(dataset)
    while current:
        dataset_ancestors.add(current['id']); current = objects.get(current['parent_id'])
    dataset_scope = [r for r in indexed.values() if r['object_id'] in dataset_ancestors]
    dataset_restricted = any(r['disposition'] in {'exclude', 'unavailable', 'out_of_scope'}
        or r['configuration'].get('access') in {'denied', 'unavailable'}
        or r['configuration'].get('private') is True and not text(r['configuration'].get('selection_reference')) for r in dataset_scope)
    restricted = restricted or dataset_restricted
    eligible = (not restricted and row['disposition'] == 'include' and dataset is not None and len(dataset_rows) == 1
                and dataset_rows[0]['disposition'] == 'include')
    return {'item': row, 'restricted': restricted, 'query_visual': eligible, 'dataset_locator': dataset,
            'requires_source_review': restricted or obj is None or row['disposition'] != 'include' or row['kind'] in REVIEW_KINDS
                or bool(targets) and not eligible}


def translate(payload, raw, helpers):
    validate_snapshot(payload)
    need(F.decode(raw) == payload, 'raw_payload_mismatch')
    parsed = read_extraction(payload['extraction']['content'].encode('utf-8'))
    result = helpers['base'](payload, raw, 'crystal', 'supplied_crystal_report_snapshot')
    fingerprint = sha(payload)
    result['source']['definition_fingerprint'] = fingerprint
    result['source']['report_identity'] = copy.deepcopy(payload['identity'])
    result['source']['definition_sha256'] = payload['extraction']['sha256']
    result['source']['provenance_assurance'] = 'supplier_declared_not_authenticated'
    result['migration_context'] = {'route': None, 'route_reference': None, 'target_surface': 'report',
        'build_authority': False, 'target_write_authority': False, 'native_validation': 'not_run', 'business_acceptance': 'not_assessed'}
    objects = {o['id']: o for o in parsed['objects']}
    dispositions = {}
    inventory_index = {row['key']: row for row in payload['inventory']['items']}
    for row in payload['inventory']['items']:
        if row['object_id'] is not None:
            dispositions.setdefault(row['object_id'], []).append(row)

    def restricted(object_id, row):
        own = [row] if row else []
        obj = objects.get(object_id)
        while obj:
            own.extend(dispositions.get(obj['id'], []))
            obj = objects.get(obj['parent_id'])
        return any(r['disposition'] in {'exclude', 'unavailable', 'out_of_scope'} or r['configuration'].get('access') in {'denied', 'unavailable'}
                   or r['configuration'].get('private') is True and not text(r['configuration'].get('selection_reference')) for r in own)

    represented = set()
    def emit(obj, row, locator):
        kind = row['kind'] if row else obj['kind']
        review = obj is None or row is None or row['disposition'] != 'include' or kind in REVIEW_KINDS
        source = {'name': obj['name'] if obj else row['key'], 'object': copy.deepcopy(obj), 'inventory': copy.deepcopy(row)}
        facets = {k: {'status': 'needs_review', 'value': copy.deepcopy(source)} for k in
                  ('visual', 'query', 'layout', 'filters', 'interactions', 'security', 'content')}
        is_restricted = restricted(obj['id'] if obj else None, row)
        scoped = _scope_item(row['key'], parsed, inventory_index) if row else None
        is_restricted = is_restricted or bool(scoped and scoped['restricted'])
        review = review or bool(scoped and scoped['requires_source_review'])
        helpers['add_asset'](result, NORMAL_KINDS[kind], source, locator, row['key'] if row else None, fingerprint,
            facets, id_kind='independent_inventory_key' if row else 'extraction_locator_obligation',
            source_identity={'source_platform': 'crystal', 'object_key': row['key'] if row else None,
                'extractor_object_id': obj['id'] if obj else None, 'native_kind': kind,
                'report_identity': copy.deepcopy(payload['identity']), 'definition_fingerprint': fingerprint,
                'definition_sha256': payload['extraction']['sha256'], 'query_visual': bool(scoped and scoped['query_visual']),
                'dataset_locator': scoped['dataset_locator'] if scoped else None,
                'requires_source_review': review, 'restricted_private_scope': is_restricted,
                'declared_disposition': row['disposition'] if row else 'manual_review'})
        if review:
            helpers['gap'](result, 'crystal.source_semantics_require_review', locator)
        if is_restricted:
            helpers['gap'](result, 'crystal.restricted_source_scope', locator)
    for row in payload['inventory']['items']:
        obj = objects.get(row['object_id'])
        emit(obj, row, '/inventory/' + row['key'])
        represented.add(row['object_id'])
        if obj is None:
            helpers['gap'](result, 'crystal.expected_object_without_extraction', '/inventory/' + row['key'])
    for i, obj in enumerate(parsed['objects']):
        if obj['id'] not in represented:
            emit(obj, None, '/extraction/objects/' + str(i))
        if obj['kind'] in REVIEW_KINDS:
            helpers['gap'](result, 'crystal.' + obj['kind'] + '_not_compiled', '/extraction/objects/' + str(i))
    result['dependencies'] = copy.deepcopy(parsed['dependencies'])
    for dep in result['dependencies']:
        dep['status'] = 'declared_reference_only' if dep['target_id'] else 'unresolved_external_dependency'
    result['crystal_coverage'] = {'declared_objects': len(parsed['objects']), 'independent_inventory_items': len(payload['inventory']['items']),
        'additional_object_obligations': len(set(objects) - represented), 'declared_scope': payload['inventory']['completeness']}
    for detail in payload['gaps']:
        helpers['gap'](result, 'crystal.supplied_gap', detail=detail)
    for code in ('extraction_completeness_not_established', 'source_identity_not_authenticated', 'engine_version_unqualified',
                 'formula_evaluation_order_unqualified', 'saved_data_vs_refresh_unverified', 'no_binary_or_sdk_execution',
                 'source_results_and_rendering_unverified', 'schedules_and_recipient_access_unverified'):
        helpers['gap'](result, 'crystal.' + code)
    return result


parse_snapshot = translate
