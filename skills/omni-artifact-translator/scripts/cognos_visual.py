"""Bounded, passive Cognos report-specification XML evidence reader.

No XSD/network lookup, source execution, report rendering, query evaluation or
numeric result qualification. Original XML remains the evidence of record.
"""
import copy
import hashlib
import importlib.util
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


SCHEMA = SNAPSHOT_SCHEMA = 'cognos-report-snapshot.v1'
MAX_XML_BYTES, MAX_XML_DEPTH, MAX_XML_NODES = 2 * 1024 * 1024, 64, 20000
MAX_ITEMS, MAX_ASSETS = 2000, 5000
IDENTITY_KEYS = {'source_origin', 'product_version', 'principal_ref', 'report_id', 'content_path', 'reference'}
KINDS = {'report', 'page', 'query', 'data_item', 'visual', 'placement', 'filter', 'prompt', 'layout',
         'content', 'model', 'condition', 'drill', 'burst', 'security', 'unknown'}
TAGS = {'report': 'report', 'page': 'page', 'query': 'query', 'dataItem': 'data_item',
        'list': 'visual', 'crosstab': 'visual', 'chart': 'visual', 'visualization': 'visual',
        'repeater': 'visual', 'repeaterTable': 'visual', 'map': 'visual',
        'detailFilter': 'filter', 'summaryFilter': 'filter', 'filter': 'filter',
        'selectValue': 'prompt', 'selectDate': 'prompt', 'selectDateTime': 'prompt', 'selectTime': 'prompt',
        'selectText': 'prompt', 'selectInterval': 'prompt', 'selectWithSearch': 'prompt',
        'promptButton': 'prompt', 'prompt': 'prompt', 'parameter': 'prompt',
        'layout': 'layout', 'table': 'layout', 'block': 'layout', 'textItem': 'content',
        'image': 'content', 'HTMLItem': 'content', 'htmlItem': 'content', 'hyperlink': 'content',
        'modelPath': 'model', 'reportVariable': 'condition', 'conditionalBlock': 'condition',
        'conditionalStyle': 'condition', 'drillBehavior': 'drill', 'drillThrough': 'drill',
        'drillSets': 'drill', 'burst': 'burst', 'security': 'security', 'securityFilter': 'security'}
STRUCTURAL = set(('queries source model selection expression detailFilters summaryFilters filterExpression layouts reportPages '
    'promptPages pageBody pageHeader pageFooter contents listColumns listColumn listColumnTitle listColumnBody textSource '
    'staticValue dataItemValue style defaultStyles defaultStyle CSS classStyles classStyle reportVariables variableValues '
    'namedConditionalStyles tableRows tableRow tableCells tableCell crosstabRows crosstabColumns crosstabNode '
    'crosstabNodeMembers crosstabNodeMember crosstabFactCell chartBody chartAxes chartAxis chartNodes chartNode '
    'reportName upgradeInfo XMLAttributes appProperties sortList sortItem aggregateFunctions').split())
NORMAL_KINDS = {'report': 'workbook', 'data_item': 'definition', 'prompt': 'control', 'model': 'definition',
                'condition': 'action', 'drill': 'action', 'burst': 'action', 'security': 'definition'}


def need(ok, code):
    if not ok:
        raise ValueError('cognos.' + code)


_path = Path(__file__).with_name('powerbi_capture_files.py')
need(not any(p.is_symlink() for p in (_path, *_path.parents)), 'module_symlink')
_spec = importlib.util.spec_from_file_location('cognos_files', _path)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
encoded = F.encoded


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 2048 and all(ord(c) >= 32 for c in value)


def valid_origin(value):
    try:
        origin = urlsplit(value)
        host, port = origin.hostname, origin.port
        if not host or origin.username is not None or origin.password is not None:
            return False
        if ':' in host:
            ipaddress.IPv6Address(host)
            rendered = '[' + host + ']'
        else:
            if re.fullmatch(r'[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?', host) is None:
                return False
            rendered = host
        if port is not None:
            if not 1 <= port <= 65535:
                return False
            rendered += ':' + str(port)
        return origin.scheme == 'https' and origin.netloc == rendered and not origin.path and not origin.query and not origin.fragment
    except ValueError:
        return False


def local(tag):
    return tag.rsplit('}', 1)[-1] if type(tag) is str else None


def namespace(tag):
    return tag[1:].split('}', 1)[0] if type(tag) is str and tag.startswith('{') else ''


def _credential_name(name):
    return re.sub('[^a-z]', '', local(name).lower()) in {
        'password', 'passwd', 'pwd', 'authorization', 'credential', 'credentials', 'apikey',
        'accesstoken', 'refreshtoken', 'clientsecret', 'privatekey', 'cam_passport', 'campassport'}


class _BoundedTree:
    def __init__(self):
        self.tree = ET.TreeBuilder(insert_comments=True, insert_pis=True)
        self.depth = self.nodes = self.characters = 0
        self.namespaces = []
        self.instructions = []

    def start(self, tag, attrs):
        self.depth += 1; self.nodes += 1
        need(self.depth <= MAX_XML_DEPTH and self.nodes <= MAX_XML_NODES and len(attrs) <= 256, 'xml_structure_limit')
        return self.tree.start(tag, attrs)

    def end(self, tag):
        value = self.tree.end(tag); self.depth -= 1
        return value

    def data(self, data):
        self.characters += len(data)
        need(self.characters <= MAX_XML_BYTES, 'xml_text_limit')
        return self.tree.data(data)

    def comment(self, data):
        self.nodes += 1; need(self.nodes <= MAX_XML_NODES, 'xml_structure_limit')
        return self.tree.comment(data)

    def pi(self, target, data):
        self.nodes += 1; need(self.nodes <= MAX_XML_NODES, 'xml_structure_limit')
        self.instructions.append({'target': target, 'text': data, 'depth': self.depth})
        return self.tree.pi(target, data)

    def start_ns(self, prefix, uri):
        need(len(self.namespaces) < MAX_XML_NODES and len(uri) <= 2048, 'xml_namespace_limit')
        self.namespaces.append({'prefix': prefix or '', 'uri': uri, 'depth': self.depth})

    def end_ns(self, prefix):
        pass

    def doctype(self, *args):
        raise ValueError('cognos.xml_declaration_rejected')

    def close(self):
        return self.tree.close()


def inspect_xml(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_XML_BYTES and b'\x00' not in raw, 'xml_bytes_or_encoding')
    try:
        source = raw.decode('utf-8')
    except UnicodeError:
        raise ValueError('cognos.xml_utf8_required') from None
    need(not re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', source, re.I), 'xml_declaration_rejected')
    declaration = re.search(r'<\?xml\s[^>]*encoding\s*=\s*[\'"]([^\'"]+)', source, re.I)
    need(not declaration or declaration[1].lower().replace('-', '') == 'utf8', 'xml_utf8_required')
    F.safe_text(raw)
    builder = _BoundedTree()
    try:
        parser = ET.XMLParser(target=builder)
        parser.feed(raw); root = parser.close()
    except (ET.ParseError, RecursionError, OverflowError):
        raise ValueError('cognos.invalid_xml') from None
    need(local(root.tag) == 'report', 'report_root_required')
    ns = namespace(root.tag)
    need(re.fullmatch(r'https?://developer\.cognos\.com/schemas/report/[0-9]+(?:\.[0-9]+)*/', ns) is not None,
         'report_namespace_required')
    records, pending, comments = {}, [(root, '/', None)], []
    while pending:
        node, path, parent = pending.pop()
        children = [c for c in node if type(c.tag) is str]
        for attr, value in node.attrib.items():
            need(not _credential_name(attr) or not value, 'credential_bearing_xml')
        need(not _credential_name(node.tag) or not (''.join(node.itertext()).strip() or any(node.attrib.values())),
             'credential_bearing_xml')
        records[path] = {'locator': path, 'parent_locator': parent, 'qname': node.tag, 'local_name': local(node.tag),
            'namespace': namespace(node.tag), 'attributes': dict(node.attrib), 'text': node.text,
            'tail': node.tail, 'children': [(path.rstrip('/') + '/' + str(i)) for i in range(len(children))]}
        for c in node:
            if type(c.tag) is not str:
                comments.append({'parent_locator': path, 'kind': 'comment' if c.tag is ET.Comment else 'processing_instruction',
                                 'text': c.text, 'tail': c.tail})
        pending.extend((c, path.rstrip('/') + '/' + str(i), path) for i, c in reversed(list(enumerate(children))))
    return {'xml_sha256': sha(raw), 'namespace': ns, 'namespaces': builder.namespaces, 'records': records,
            'comments_and_processing_instructions': comments, 'processing_instructions': builder.instructions,
            'node_count': builder.nodes}


def _kind(record, ns):
    return TAGS.get(record['local_name'], 'unknown') if record['namespace'] == ns else 'unknown'


def _restricted(row, indexed):
    while row is not None:
        config = row['configuration']
        if row['disposition'] in ('unavailable', 'out_of_scope') or config.get('access') in ('denied', 'unavailable'):
            return True
        if config.get('private') is True and not text(config.get('selection_reference')):
            return True
        row = indexed.get(row['parent_key'])
    return False


def _validate(value):
    try:
        raw = encoded(value)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('cognos.invalid_json') from None
    need(len(raw) <= 8 * 1024 * 1024, 'snapshot_byte_limit')
    F.decode(raw); F.secret_check(value); F.safe_text(raw)
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'report_xml', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    identity = value['identity']
    need(type(identity) is dict and set(identity) == IDENTITY_KEYS
         and all(text(identity[k]) for k in ('product_version', 'principal_ref', 'reference'))
         and all(identity[k] is None or text(identity[k]) for k in ('source_origin', 'report_id', 'content_path')), 'identity_contract')
    if identity['source_origin'] is not None:
        need(valid_origin(identity['source_origin']), 'source_origin')
    xml = value['report_xml']
    need(type(xml) is dict and set(xml) == {'encoding', 'sha256', 'bytes', 'content', 'reference'}
         and xml['encoding'] == 'utf-8' and type(xml['content']) is str and type(xml['bytes']) is int
         and text(xml['reference']), 'report_xml_contract')
    try:
        original = xml['content'].encode('utf-8')
    except UnicodeError:
        raise ValueError('cognos.xml_utf8_required') from None
    need(len(original) == xml['bytes'] and sha(original) == xml['sha256'], 'xml_pin_mismatch')
    parsed = inspect_xml(original)
    inventory = value['inventory']
    need(type(inventory) is dict and set(inventory) == {'reference', 'completeness', 'items'} and text(inventory['reference'])
         and inventory['completeness'] in ('partial', 'selected_scope_declared') and type(inventory['items']) is list
         and 1 <= len(inventory['items']) <= MAX_ITEMS, 'inventory_contract')
    indexed, locators = {}, set()
    for row in inventory['items']:
        need(type(row) is dict and set(row) == {'key', 'kind', 'parent_key', 'native_id', 'locator', 'disposition', 'reference', 'configuration'}
             and text(row['key']) and row['key'] not in indexed and row['kind'] in KINDS and text(row['reference'])
             and row['disposition'] in ('include', 'manual_review', 'unsupported', 'unavailable', 'out_of_scope')
             and type(row['configuration']) is dict
             and all(row[k] is None or text(row[k]) for k in ('parent_key', 'native_id', 'locator')), 'inventory_item')
        locator, config = row['locator'], row['configuration']
        if locator is not None:
            need(locator in parsed['records'] and locator not in locators, 'locator_missing_or_duplicate')
            locators.add(locator); record = parsed['records'][locator]
            native = record['attributes'].get('id')
            need(native is None or row['native_id'] == native, 'native_identity_contradiction')
            actual = _kind(record, parsed['namespace'])
            need(row['kind'] in ('unknown', actual) or row['kind'] == 'placement' and actual in ('visual', 'content'), 'native_kind_contradiction')
        if 'private' in config:
            need(type(config['private']) is bool, 'private_flag')
        if 'access' in config:
            need(config['access'] in ('allowed', 'denied', 'unavailable', 'unknown'), 'access_declaration')
        if 'selection_reference' in config:
            need(text(config['selection_reference']), 'selection_reference')
        indexed[row['key']] = row
    roots = [r for r in indexed.values() if r['parent_key'] is None]
    need(len(roots) == 1 and roots[0]['kind'] == 'report' and roots[0]['locator'] == '/', 'inventory_root_binding')
    need(identity['report_id'] is None or roots[0]['native_id'] == identity['report_id'], 'report_identity_contradiction')
    for row in indexed.values():
        parent, seen = row['parent_key'], {row['key']}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'inventory_parent_or_cycle')
            seen.add(parent); parent = indexed[parent]['parent_key']
    need(type(value['gaps']) is list and len(value['gaps']) <= 1000 and all(text(x) for x in value['gaps']), 'gaps_contract')
    return parsed, indexed


def validate_snapshot(value):
    _validate(value)
    return value


def import_report_xml(raw, identity, inventory, reference):
    inspect_xml(raw)
    value = {'schema_version': SCHEMA, 'identity': copy.deepcopy(identity), 'report_xml': {
        'encoding': 'utf-8', 'sha256': sha(raw), 'bytes': len(raw), 'content': raw.decode('utf-8'), 'reference': reference},
        'inventory': copy.deepcopy(inventory), 'gaps': []}
    return validate_snapshot(value)


def translate(payload, raw, helpers):
    parsed, indexed = _validate(payload)
    need(type(raw) is bytes and F.decode(raw) == payload, 'raw_payload_mismatch')
    result = helpers['base'](payload, raw, 'cognos', 'supplied_cognos_report_snapshot')
    fingerprint, xml_hash, ns = sha(payload), payload['report_xml']['sha256'], parsed['namespace']
    result['source'].update(source_identity=copy.deepcopy(payload['identity']), definition_fingerprint=fingerprint,
                            definition_sha256=xml_hash, report_namespace=ns)
    result.update(build_authority=False, migration_context={'route': None, 'build_authority': False,
        'target_write_authority': False, 'native_validation': 'not_run', 'business_acceptance': 'not_assessed'})
    records, represented = parsed['records'], {r['locator'] for r in indexed.values() if r['locator'] is not None}
    result['cognos_xml'] = parsed
    queries = {}
    for path, record in records.items():
        if _kind(record, ns) == 'query' and text(record['attributes'].get('name')):
            queries.setdefault(record['attributes']['name'], []).append(path)
    def query_binding(record):
        if record is None or record['namespace'] != ns:
            return None
        if record['local_name'] == 'query' and text(record['attributes'].get('name')):
            return record['locator']
        ref = record['attributes'].get('refQuery')
        return queries[ref][0] if ref in queries and len(queries[ref]) == 1 else None
    def emit(row, record, path, declared):
        restricted = (declared and _restricted(row, indexed)) or any(_restricted(r, indexed) for r in indexed.values()
            if path is not None and r['locator'] is not None and
            (r['locator'] == '/' or path == r['locator'] or path.startswith(r['locator'] + '/')))
        query = query_binding(record) if record and row['kind'] in ('query', 'visual', 'placement') else None
        eligible = declared and row['disposition'] == 'include' and not restricted and query is not None
        source = {'inventory': copy.deepcopy(row), 'xml_node': copy.deepcopy(record)}
        attrs = record['attributes'] if record else {}
        source['name'] = attrs.get('name') or row['key']
        facets = {k: {'status': 'needs_review', 'value': {'xml_locator': path, 'original_xml_sha256': xml_hash,
                  'node': copy.deepcopy(record)}} for k in ('visual', 'query', 'layout', 'filters', 'interactions', 'security', 'content')}
        helpers['add_asset'](result, NORMAL_KINDS.get(row['kind'], row['kind']) if declared else 'unknown', source,
            '/inventory/' + row['key'] if declared else '/xml' + path, row['key'] if declared else None, fingerprint,
            facets, id_kind='independent_inventory_key' if declared else 'xml_locator_obligation', source_identity={
                'source_platform': 'cognos', 'object_key': row['key'] if declared else None, 'native_kind': row['kind'],
                'native_id': row.get('native_id'), 'xml_locator': path, 'xml_qname': record['qname'] if record else None,
                'xml_name': attrs.get('name'), 'report_identity': copy.deepcopy(payload['identity']),
                'definition_fingerprint': fingerprint, 'definition_sha256': xml_hash, 'query_visual': eligible,
                'query_locator': query, 'restricted_private_scope': restricted, 'declared_disposition': row['disposition']})
        if record and 'refQuery' in attrs:
            result['dependencies'].append({'source_locator': path, 'reference_kind': 'query_name', 'reference': attrs['refQuery'],
                'target_locators': queries.get(attrs['refQuery'], []), 'status': 'resolved_xml_reference' if query else 'unresolved'})
            if query is None:
                helpers['gap'](result, 'cognos.query_reference_unresolved_or_ambiguous', path)
        if restricted:
            helpers['gap'](result, 'cognos.restricted_source_scope', path)
    for row in indexed.values():
        path = row['locator']; emit(row, records.get(path), path, True)
        if path is None:
            helpers['gap'](result, 'cognos.expected_object_without_xml', '/inventory/' + row['key'])
    omitted = unknown = 0
    for path, record in records.items():
        kind = _kind(record, ns)
        if path not in represented and (kind != 'unknown' or record['namespace'] != ns or record['local_name'] not in STRUCTURAL):
            need(len(result['assets']) < MAX_ASSETS, 'projection_asset_limit')
            omitted += 1; unknown += kind == 'unknown'
            emit({'key': None, 'kind': kind, 'disposition': 'manual_review'}, record, path, False)
            helpers['gap'](result, 'cognos.native_element_not_independently_dispositioned', path)
        if kind in ('model', 'condition', 'drill', 'burst', 'security') or record['local_name'] in ('appProperties', 'HTMLItem', 'htmlItem'):
            helpers['gap'](result, 'cognos.' + kind + '_semantics_require_review', path)
        if any(local(k) in ('href', 'src', 'schemaLocation') or '://' in v for k, v in record['attributes'].items()):
            helpers['gap'](result, 'cognos.external_reference_not_followed', path)
        if kind == 'model':
            result['dependencies'].append({'source_locator': path, 'reference_kind': 'model_search_path',
                'reference': record['text'], 'status': 'external_definition_unverified'})
        if record['namespace'] == ns and 'refDataItem' in record['attributes']:
            ancestor, query = record, None
            while ancestor is not None and query is None:
                query = query_binding(ancestor)
                ancestor = records.get(ancestor['parent_locator'])
            name = record['attributes']['refDataItem']
            matches = [p for p, r in records.items() if query and p.startswith(query + '/') and
                       _kind(r, ns) == 'data_item' and r['attributes'].get('name') == name]
            result['dependencies'].append({'source_locator': path, 'reference_kind': 'data_item_name', 'reference': name,
                'query_locator': query, 'target_locators': matches,
                'status': 'resolved_xml_reference' if len(matches) == 1 else 'unresolved'})
            if len(matches) != 1:
                helpers['gap'](result, 'cognos.data_item_reference_unresolved_or_ambiguous', path)
    if parsed['processing_instructions']:
        helpers['gap'](result, 'cognos.processing_instruction_not_executed', '/')
    for required in ('modelPath', 'queries', 'layouts'):
        if not any(r['namespace'] == ns and r['local_name'] == required and r['parent_locator'] == '/' for r in records.values()):
            helpers['gap'](result, 'cognos.required_report_element_missing', detail=required)
    if 'expressionLocale' not in records['/']['attributes']:
        helpers['gap'](result, 'cognos.expression_locale_missing', '/')
    result['cognos_coverage'] = {'independently_enumerated': len(indexed), 'xml_elements': len(records),
        'additional_xml_obligations': omitted, 'unknown_xml_obligations': unknown,
        'declared_scope': payload['inventory']['completeness'], 'export_completeness': 'not_established'}
    for detail in payload['gaps']:
        helpers['gap'](result, 'cognos.supplied_gap', detail=detail)
    for code in ('xml_is_not_render_or_execution_evidence', 'no_schema_validation_or_formula_compiler',
                 'source_identity_and_inventory_not_authenticated', 'effective_access_unverified',
                 'unqualified_source_results', 'external_semantic_model_and_security_not_complete',
                 'no_connected_transport_or_DMA_producer'):
        helpers['gap'](result, 'cognos.' + code)
    return result


parse_snapshot = translate
