"""Passive BusinessObjects response interpreter. No source execution or transport.

Native Web Intelligence JSON/XML shapes establish structural obligations, not
formula equivalence, numeric completeness, effective access or write authority.
Crystal definitions and unfamiliar shapes remain original, reviewable evidence.
"""
import copy
import hashlib
import importlib.util
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

SCHEMA = SNAPSHOT_SCHEMA = 'businessobjects-api-snapshot.v1'
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
MAX_XML_DEPTH, MAX_XML_NODES, MAX_ITEMS, MAX_ASSETS = 64, 20000, 2000, 5000
KINDS = {'document', 'report', 'visual', 'placement', 'provider', 'query', 'variable', 'filter', 'prompt',
         'input_control', 'merged_dimension', 'layout', 'security', 'drill', 'alert', 'content', 'unknown'}
RESPONSE_KINDS = {'document', 'reports', 'report', 'elements', 'element', 'dataproviders', 'dataprovider',
                  'query', 'specification', 'map', 'variables', 'variable', 'filters', 'prompts',
                  'input_controls', 'merged_dimensions', 'layout', 'security', 'unknown'}
DISPOSITIONS = {'include', 'manual_review', 'unsupported', 'unavailable', 'out_of_scope'}
NORMAL = {'document': 'workbook', 'report': 'page', 'provider': 'query', 'variable': 'definition',
          'prompt': 'parameter', 'input_control': 'control', 'merged_dimension': 'definition',
          'security': 'definition', 'drill': 'action', 'alert': 'action'}
SPEC_TAGS = {'REPORT': 'report', 'PAGE_HEADER': 'layout', 'PAGE_BODY': 'layout', 'PAGE_FOOTER': 'layout',
             'VTABLE': 'visual', 'HTABLE': 'visual', 'XTABLE': 'visual', 'TABLE': 'visual',
             'TDCELL': 'visual', 'CELL': 'visual', 'CONTENT': 'content'}
PLAIN_TAGS = {'document': 'document', 'report': 'report', 'element': 'visual', 'dataprovider': 'provider',
              'variable': 'variable', 'parameter': 'prompt', 'inputcontrol': 'input_control',
              'filter': 'filter', 'datafilter': 'filter', 'link': 'merged_dimension',
              'drill': 'drill', 'alerter': 'alert', 'security': 'security', 'node': 'placement'}
WRAPPERS = {'document', 'reports', 'report', 'elements', 'element', 'dataproviders', 'dataprovider',
            'variables', 'variable', 'parameters', 'parameter', 'inputcontrols', 'inputcontrol',
            'datafilter', 'filters', 'links', 'link', 'security', 'map', 'REPORT'}
STRUCTURAL = set(('id name reference parentId dataSourceId dataSourceType dataSourcePrefix updated isPartial rowCount flowCount '
    'showDataChanges style hyperLinkColors pageSettings margins format records scaling paginationMode size position hide '
    'padding border background content expression formula template alerters definition formulaLanguageId description '
    'groups group values value dimensionId datapath queryParameters maxRowsRetrievedProperty queriesTree queryOperator '
    'ROWGROUP TR display status type documentId reportId linkedExpressions linkedExpression').split()) | WRAPPERS


def need(ok, code):
    if not ok:
        raise ValueError('businessobjects.' + code)


_file = Path(__file__).with_name('powerbi_capture_files.py')
need(not any(p.is_symlink() for p in (_file, *_file.parents)), 'module_symlink')
_spec = importlib.util.spec_from_file_location('businessobjects_files', _file)
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
encoded = F.encoded


def sha(value):
    return hashlib.sha256(value if type(value) is bytes else encoded(value)).hexdigest()


def text(value):
    return type(value) is str and 0 < len(value) <= 2048 and all(ord(c) >= 32 for c in value)


def native_id(value):
    if type(value) is int and value >= 0:
        return str(value)
    return value if text(value) else None


def valid_origin(value):
    try:
        u = urlsplit(value); host, port = u.hostname, u.port
        if not host or u.username is not None or u.password is not None:
            return False
        if ':' in host:
            ipaddress.IPv6Address(host); rendered = '[' + host + ']'
        else:
            if re.fullmatch(r'[a-z0-9]+(?:[a-z0-9.-]*[a-z0-9])?', host) is None:
                return False
            rendered = host
        if port is not None:
            if not 1 <= port <= 65535:
                return False
            rendered += ':' + str(port)
        return u.scheme == 'https' and u.netloc == rendered and not u.path and not u.query and not u.fragment
    except (ValueError, TypeError):
        return False


def local(tag):
    return tag.rsplit('}', 1)[-1] if type(tag) is str else ''


def namespace(tag):
    return tag[1:].split('}', 1)[0] if type(tag) is str and tag.startswith('{') else ''


def _secret_name(key):
    return re.sub('[^a-z]', '', local(key).lower()) in {
        'password', 'passwd', 'pwd', 'authorization', 'credential', 'credentials', 'apikey', 'accesstoken',
        'refreshtoken', 'clientsecret', 'privatekey', 'xsaplogontoken', 'logontoken', 'sessiontoken',
        'cookie', 'setcookie', 'serializedsession'}


def secret_check(value):
    F.secret_check(value)
    pending = [value]
    while pending:
        row = pending.pop()
        if type(row) is dict:
            declared = row.get('@name', row.get('name'))
            if type(declared) is str and _secret_name(declared):
                need(not any(row.get(k) for k in ('$', 'value', '#text')), 'credential_bearing_json')
            for key, val in row.items():
                need(not _secret_name(key) or not val, 'credential_bearing_json')
                pending.append(val)
        elif type(row) is list:
            pending.extend(row)


class _Tree:
    def __init__(self):
        self.tree = ET.TreeBuilder(insert_comments=True, insert_pis=True)
        self.depth = self.nodes = self.characters = 0
        self.namespaces, self.instructions = [], []

    def start(self, tag, attrs):
        self.depth += 1; self.nodes += 1
        need(self.depth <= MAX_XML_DEPTH and self.nodes <= MAX_XML_NODES and len(attrs) <= 256, 'xml_structure_limit')
        return self.tree.start(tag, attrs)

    def end(self, tag):
        result = self.tree.end(tag); self.depth -= 1
        return result

    def data(self, value):
        self.characters += len(value)
        need(self.characters <= MAX_RESPONSE_BYTES, 'xml_text_limit')
        return self.tree.data(value)

    def comment(self, value):
        self.nodes += 1; need(self.nodes <= MAX_XML_NODES, 'xml_structure_limit')
        return self.tree.comment(value)

    def pi(self, target, value):
        self.nodes += 1; need(self.nodes <= MAX_XML_NODES, 'xml_structure_limit')
        self.instructions.append({'target': target, 'text': value})
        return self.tree.pi(target, value)

    def start_ns(self, prefix, uri):
        need(len(self.namespaces) < MAX_XML_NODES and len(uri) <= 2048, 'xml_namespace_limit')
        self.namespaces.append({'prefix': prefix or '', 'uri': uri})

    def end_ns(self, prefix):
        pass

    def doctype(self, *args):
        raise ValueError('businessobjects.xml_declaration_rejected')

    def close(self):
        return self.tree.close()


def inspect_xml(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_RESPONSE_BYTES and b'\x00' not in raw, 'xml_byte_limit_or_encoding')
    source = F.safe_text(raw)
    need(not re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', source, re.I), 'xml_declaration_rejected')
    declaration = re.search(r'<\?xml\s[^>]*encoding\s*=\s*[\'"]([^\'"]+)', source, re.I)
    need(not declaration or declaration[1].lower().replace('-', '') == 'utf8', 'utf8_required')
    builder = _Tree()
    try:
        parser = ET.XMLParser(target=builder); parser.feed(raw); root = parser.close()
    except (ET.ParseError, RecursionError, OverflowError):
        raise ValueError('businessobjects.invalid_xml') from None
    records, pending, comments = {}, [(root, '/', None)], []
    while pending:
        node, path, parent = pending.pop()
        for key, value in node.attrib.items():
            need(not _secret_name(key) or not value, 'credential_bearing_xml')
        need(not _secret_name(node.tag) or not (''.join(node.itertext()).strip() or any(node.attrib.values())), 'credential_bearing_xml')
        if local(node.tag) == 'attr' and _secret_name(node.attrib.get('name', '')):
            need(not ''.join(node.itertext()).strip() and not node.attrib.get('value'), 'credential_bearing_xml')
        children = [c for c in node if type(c.tag) is str]
        records[path] = {'locator': path, 'parent_locator': parent, 'label': local(node.tag), 'qname': node.tag,
            'namespace': namespace(node.tag), 'attributes': dict(node.attrib), 'text': node.text, 'tail': node.tail,
            'children': [path.rstrip('/') + '/' + str(i) for i in range(len(children))]}
        for child in node:
            if type(child.tag) is not str:
                comments.append({'parent_locator': path, 'text': child.text, 'tail': child.tail,
                    'kind': 'comment' if child.tag is ET.Comment else 'processing_instruction'})
        pending.extend((c, path.rstrip('/') + '/' + str(i), path) for i, c in reversed(list(enumerate(children))))
    return {'format': 'xml', 'records': records, 'namespaces': builder.namespaces,
            'comments_and_processing_instructions': comments, 'processing_instructions': builder.instructions}


def _pointer(value):
    return value.replace('~', '~0').replace('/', '~1')


def decode_response(response):
    raw = response['content'].encode('utf-8')
    if response['format'] == 'xml':
        return inspect_xml(raw)
    payload = F.decode(raw); secret_check(payload)
    need(type(payload) is dict, 'json_response_object_required')
    records, pending = {}, [(payload, '', None, None)]
    while pending:
        row, path, parent, label = pending.pop()
        if type(row) is dict:
            records[path] = {'locator': path, 'parent_locator': parent, 'label': label, 'namespace': '', 'payload': row}
            pending.extend((v, path + '/' + _pointer(k), path, k) for k, v in reversed(list(row.items())) if type(v) in (dict, list))
        elif type(row) is list:
            pending.extend((v, path + '/' + str(i), parent, label) for i, v in reversed(list(enumerate(row))) if type(v) in (dict, list))
    return {'format': 'json', 'records': records}


def _field(record, name, parsed):
    if 'payload' in record:
        return record['payload'].get(name, record['payload'].get('@' + name))
    if name in record['attributes']:
        return record['attributes'][name]
    found = [parsed['records'][p] for p in record['children']
             if parsed['records'][p]['label'] == name and not parsed['records'][p]['namespace']]
    return found[0]['text'] if len(found) == 1 else None


def _route(response, identity):
    provenance = response['provenance']; path = provenance['resource_path']
    if provenance['mode'] != 'supplied_rest' or provenance['method'] != 'GET' or provenance['status'] != 200 or path is None:
        return None
    u = urlsplit(path)
    need(not u.scheme and not u.netloc and not u.fragment and path.startswith('/') and '\\' not in path,
         'resource_path_invalid')
    parts = [unquote(p) for p in u.path.split('/') if p]
    need(not any(p in ('.', '..') or '/' in p or '\\' in p for p in parts), 'resource_path_invalid')
    if 'documents' not in parts:
        return None
    pos = parts.index('documents'); tail = parts[pos:]
    need(len(tail) >= 2 and tail[1] == identity['document_id'], 'route_document_mismatch')
    for label, declared in (('reports', response['report_id']), ('dataproviders', response['provider_id'])):
        if label in tail and tail.index(label) + 1 < len(tail):
            actual = tail[tail.index(label) + 1]
            need(declared == actual, 'route_' + label + '_mismatch')
    return tail


def _profile(identity):
    version, engine = identity['product_version'], identity['report_engine']
    gaps = []
    if version not in ('4.3', '2025'):
        gaps.append('unqualified_product_version')
    if engine == 'crystal_classic' and (version == '4.3' and (identity['service_pack'] is None or identity['service_pack'] < 5)):
        gaps.append('crystal_classic_requires_4_3_SP05_or_later')
    if engine == 'crystal_enterprise' and version == '2025':
        gaps.append('crystal_enterprise_not_supported_2025')
    if engine != 'webi':
        gaps.append('crystal_native_shapes_not_qualified')
    return gaps


def _shape_root(parsed, response):
    expected = {'document': {'document'}, 'reports': {'reports'}, 'report': {'report'}, 'elements': {'elements'},
        'element': {'element'}, 'dataproviders': {'dataproviders'}, 'dataprovider': {'dataprovider'},
        'variable': {'variable'}, 'variables': {'variables'}, 'prompts': {'parameters'},
        'input_controls': {'inputcontrols', 'inputcontrol'}, 'filters': {'datafilter', 'filters'},
        'merged_dimensions': {'links', 'link'},
        'map': {'map'}, 'specification': {'REPORT', 'QuerySpec'}, 'query': {'QuerySpec'}}.get(response['kind'], set())
    if parsed['format'] == 'xml':
        root = parsed['records']['/']
        return (root['label'] in expected and (not root['namespace'] or
                root['label'] == 'QuerySpec' and root['namespace'] == 'http://com.sap.sl.queryspec'))
    payload = parsed['records']['']['payload']
    return len(payload) == 1 and next(iter(payload)) in expected and type(next(iter(payload.values()))) is dict


def _native(record, parsed, response, identity, route):
    label, ns = record['label'], record['namespace']
    kind, query = 'unknown', False
    identifier = native_id(_field(record, 'id', parsed))
    provider_ids = []
    known_route = route is not None and identity['report_engine'] == 'webi' and not _profile(identity) and _shape_root(parsed, response)
    # A namespace-spoofed element cannot impersonate an unqualified Raylight element.
    if not ns:
        kind = PLAIN_TAGS.get(label, 'unknown')
        if response['kind'] == 'specification' and label in SPEC_TAGS:
            kind = SPEC_TAGS[label]
            identifier = native_id(_field(record, 'rId' if label == 'REPORT' else 'bId', parsed))
        if label == 'element':
            typ = _field(record, 'type', parsed)
            kind = 'layout' if typ == 'PageZone' else 'unknown' if typ == 'Custom' else 'visual'
            query = typ in ('VTable', 'HTable', 'XTable', 'Form', 'Visualization')
            if typ == 'Cell':
                query = any(r['label'] == 'formula' for p, r in parsed['records'].items()
                            if p.startswith(record['locator'].rstrip('/') + '/'))
            if typ not in ('PageZone', 'Cell', 'VTable', 'HTable', 'XTable', 'Form', 'Visualization', 'Custom'):
                kind = 'unknown'; query = False
        elif response['kind'] == 'specification' and label in ('VTABLE', 'HTABLE', 'XTABLE', 'TABLE', 'TDCELL', 'CELL'):
            query = True
        elif label == 'dataprovider':
            query = _field(record, 'dataSourceType', parsed) in ('unv', 'unx', 'bex', 'excel', 'fhsql', 'webi')
            if identifier:
                provider_ids.append(identifier)
        elif label == 'node' and response['kind'] != 'map':
            kind = 'unknown'
    elif label == 'QuerySpec' and ns == 'http://com.sap.sl.queryspec' and response['kind'] in ('query', 'specification'):
        kind, query = 'query', True
        identifier = native_id(_field(record, 'dataProviderId', parsed))
    if label == 'QuerySpec' and ns == 'http://com.sap.sl.queryspec' and identifier:
        provider_ids.append(identifier)
    # Raylight formula dataObjectId attributes carry the provider prefix. Keep
    # formulas inert and never infer provider lineage from display names/text.
    formulas = [record] if label == 'formula' else []
    if kind == 'visual':
        formulas.extend(r for p, r in parsed['records'].items() if p.startswith(record['locator'].rstrip('/') + '/')
                        and r['label'] == 'formula' and not r['namespace'])
    for formula in formulas:
        data_object = _field(formula, 'dataObjectId', parsed)
        if type(data_object) is str and re.fullmatch(r'DP[^.\s]+\..+', data_object):
            provider_ids.append(data_object.split('.', 1)[0])
    if label == 'link' and not ns and response['kind'] == 'merged_dimensions':
        for linked in parsed['records'].values():
            parent = parsed['records'].get(linked['parent_locator'])
            if (linked['label'] == 'linkedExpression' and not linked['namespace'] and parent is not None
                    and parent['label'] == 'linkedExpressions' and not parent['namespace']
                    and parent['parent_locator'] == record['locator']):
                linked_id = _field(linked, 'id', parsed)
                if type(linked_id) is str and re.fullmatch(r'DP[^.\s]+\..+', linked_id):
                    provider_ids.append(linked_id.split('.', 1)[0])
    if response['provider_id'] is not None and route and 'dataproviders' in route:
        provider_ids.append(response['provider_id'])
    if kind == 'report' and identifier is not None:
        need(response['report_id'] is None or identifier == response['report_id'], 'native_report_identity_mismatch')
    if kind == 'document' and identifier is not None:
        need(identifier == identity['document_id'], 'native_document_identity_mismatch')
        cuid = _field(record, 'cuid', parsed)
        need(cuid is None or identity['cuid'] is None or cuid == identity['cuid'], 'native_cuid_mismatch')
    if kind in ('provider', 'query') and identifier is not None and response['provider_id'] is not None:
        need(identifier == response['provider_id'], 'native_provider_identity_mismatch')
    unv = _field(record, 'dataSourceType', parsed) == 'unv' and identity['product_version'] == '2025'
    # Source-native eligibility also requires an actual endpoint family, not merely
    # a familiar field name in a modeled/unknown payload or an unrelated endpoint.
    family = False
    if route:
        suffix = route[2:]
        family = ((kind == 'document' and not suffix) or
                  (kind == 'report' and suffix and suffix[0] == 'reports') or
                  (kind in ('visual', 'layout', 'content', 'placement') and len(suffix) >= 3 and suffix[0] == 'reports'
                   and suffix[2] in ('elements', 'specification', 'map')) or
                  (kind in ('provider', 'query') and suffix and suffix[0] == 'dataproviders') or
                  (kind == 'variable' and suffix and suffix[0] == 'variables') or
                  (kind == 'merged_dimension' and label == 'link' and suffix and suffix[0] == 'links') or
                  (kind in ('filter', 'prompt', 'input_control', 'drill', 'alert') and any(
                      part in ('parameters', 'datafilter', 'filters', 'inputcontrols', 'driller', 'alerters') for part in suffix)))
        if kind in ('visual', 'layout') and label == 'element' and 'elements' in suffix:
            pos = suffix.index('elements')
            if pos + 1 < len(suffix):
                need(identifier is None or identifier == suffix[pos + 1], 'native_element_route_mismatch')
        if kind == 'variable' and len(suffix) >= 2 and suffix[0] == 'variables':
            need(identifier is None or identifier == suffix[1], 'native_variable_route_mismatch')
        if kind == 'merged_dimension' and len(suffix) >= 2 and suffix[0] == 'links':
            need(identifier is None or identifier == suffix[1], 'native_link_route_mismatch')
    # Only documented container ancestry is eligible. An unfamiliar embedded
    # object is retained but cannot promote a familiar child label to native proof.
    parent = parsed['records'].get(record['parent_locator'])
    while parent is not None:
        label_parent = parent['label']
        allowed = (label_parent is None or label_parent in WRAPPERS or label_parent in SPEC_TAGS
                   or label_parent in ('ROWGROUP', 'TR'))
        if not allowed or parent['namespace']:
            family = False
        parent = parsed['records'].get(parent['parent_locator'])
    native = bool(known_route and family)
    return {'kind': kind, 'native_id': identifier, 'query_native': bool(native and query and identifier is not None and not unv),
        'native_shape': native, 'provider_ids': sorted(set(provider_ids)),
        'report_id': identifier if kind == 'report' else response['report_id'],
        'unv_2025': unv, 'instance_reference': _field(record, 'reference', parsed),
        'name': _field(record, 'name', parsed)}


def _validate(value):
    try:
        raw = encoded(value)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('businessobjects.invalid_json') from None
    need(len(raw) <= MAX_SNAPSHOT_BYTES, 'snapshot_byte_limit'); F.decode(raw); F.safe_text(raw); secret_check(value)
    need(type(value) is dict and set(value) == {'schema_version', 'identity', 'responses', 'inventory', 'gaps'}
         and value['schema_version'] == SCHEMA, 'snapshot_contract')
    ident = value['identity']
    need(type(ident) is dict and set(ident) == {'source_origin', 'product_version', 'service_pack', 'principal_ref',
         'document_id', 'cuid', 'report_engine', 'reference'} and valid_origin(ident['source_origin'])
         and all(text(ident[k]) for k in ('product_version', 'principal_ref', 'document_id', 'reference'))
         and (ident['cuid'] is None or text(ident['cuid'])) and (ident['service_pack'] is None or
         type(ident['service_pack']) is int and 0 <= ident['service_pack'] <= 99)
         and ident['report_engine'] in ('webi', 'crystal_classic', 'crystal_enterprise'), 'identity_contract')
    need(type(value['responses']) is list and 1 <= len(value['responses']) <= 512, 'responses_contract')
    responses, total = {}, 0
    for response in value['responses']:
        need(type(response) is dict and set(response) == {'key', 'kind', 'report_id', 'provider_id', 'format', 'encoding',
             'content', 'sha256', 'bytes', 'reference', 'provenance'} and text(response['key']) and response['key'] not in responses
             and response['kind'] in RESPONSE_KINDS and response['format'] in ('json', 'xml') and response['encoding'] == 'utf-8'
             and type(response['content']) is str and type(response['bytes']) is int and text(response['reference'])
             and all(response[k] is None or text(response[k]) for k in ('report_id', 'provider_id')), 'response_contract')
        try:
            body = response['content'].encode('utf-8')
        except UnicodeError:
            raise ValueError('businessobjects.utf8_required') from None
        total += len(body)
        need(0 < len(body) <= MAX_RESPONSE_BYTES and total <= MAX_SNAPSHOT_BYTES and len(body) == response['bytes']
             and sha(body) == response['sha256'], 'response_pin_or_size')
        F.safe_text(body)
        p = response['provenance']
        need(type(p) is dict and set(p) == {'mode', 'method', 'resource_path', 'status'}
             and p['mode'] in ('supplied_rest', 'supplied_modeled', 'unknown') and p['method'] in ('GET', None)
             and (p['resource_path'] is None or text(p['resource_path']))
             and (p['status'] is None or type(p['status']) is int and 100 <= p['status'] <= 599), 'provenance_contract')
        parsed = decode_response(response); route = _route(response, ident)
        for record in parsed['records'].values():
            record['native'] = _native(record, parsed, response, ident, route)
        responses[response['key']] = {'response': response, 'parsed': parsed, 'route': route}
    inv = value['inventory']
    need(type(inv) is dict and set(inv) == {'reference', 'completeness', 'items'} and text(inv['reference'])
         and inv['completeness'] in ('partial', 'selected_scope_declared') and type(inv['items']) is list
         and 1 <= len(inv['items']) <= MAX_ITEMS, 'inventory_contract')
    indexed, mappings = {}, {}
    for row in inv['items']:
        need(type(row) is dict and set(row) == {'key', 'kind', 'parent_key', 'native_id', 'report_id', 'disposition',
             'reference', 'configuration', 'source_mapping'} and text(row['key']) and row['key'] not in indexed
             and row['kind'] in KINDS and row['disposition'] in DISPOSITIONS and text(row['reference'])
             and type(row['configuration']) is dict and all(row[k] is None or text(row[k])
             for k in ('parent_key', 'native_id', 'report_id')), 'inventory_item')
        config, mapping = row['configuration'], row['source_mapping']
        if 'private' in config:
            need(type(config['private']) is bool, 'private_flag')
        if 'access' in config:
            need(config['access'] in ('allowed', 'denied', 'unavailable', 'unknown'), 'access_declaration')
        if 'selection_reference' in config:
            need(text(config['selection_reference']), 'selection_reference')
        if mapping is not None:
            need(type(mapping) is dict and set(mapping) == {'response_key', 'locator'} and mapping['response_key'] in responses
                 and type(mapping['locator']) is str, 'source_mapping')
            parsed = responses[mapping['response_key']]['parsed']
            need(mapping['locator'] in parsed['records'], 'source_locator_missing')
            record = parsed['records'][mapping['locator']]; native = record['native']
            need(native['native_id'] is None or native['native_id'] == row['native_id'], 'native_identity_contradiction')
            need(native['report_id'] is None or native['report_id'] == row['report_id'], 'report_identity_contradiction')
            need(row['kind'] in ('unknown', native['kind']) or row['kind'] == 'placement'
                 and native['kind'] in ('visual', 'content'), 'native_kind_contradiction')
            pair = (mapping['response_key'], mapping['locator'])
            if pair in mappings:
                prior = mappings[pair]
                need(row['kind'] == prior['kind'] == 'placement' and text(config.get('instance_reference'))
                     and text(prior['configuration'].get('instance_reference')) and
                     config['instance_reference'] != prior['configuration']['instance_reference'], 'duplicate_mapping')
            mappings[pair] = row
        indexed[row['key']] = row
    roots = [r for r in indexed.values() if r['parent_key'] is None]
    need(len(roots) == 1 and roots[0]['kind'] == 'document' and roots[0]['native_id'] == ident['document_id'], 'document_root_binding')
    for row in indexed.values():
        parent, seen = row['parent_key'], {row['key']}
        while parent is not None:
            need(parent in indexed and parent not in seen, 'inventory_parent_or_cycle')
            seen.add(parent); parent = indexed[parent]['parent_key']
    need(type(value['gaps']) is list and len(value['gaps']) <= 1000 and all(text(x) for x in value['gaps']), 'gaps_contract')
    return responses, indexed


def validate_snapshot(value):
    _validate(value)
    return value


def _restricted(row, indexed):
    while row is not None:
        config = row['configuration']
        if row['disposition'] in ('unavailable', 'out_of_scope') or config.get('access') in ('denied', 'unavailable'):
            return True
        if config.get('private') is True and not text(config.get('selection_reference')):
            return True
        row = indexed.get(row['parent_key'])
    return False


def _native_restriction(record, parsed):
    """Negative source flags restrict; positive flags never establish access."""
    while record is not None:
        for key in ('private', 'isPrivate'):
            if _field(record, key, parsed) in (True, 'true'):
                return True
        if _field(record, 'access', parsed) in ('denied', 'unavailable'):
            return True
        record = parsed['records'].get(record['parent_locator'])
    return False


def _source_policy(responses, indexed):
    policy = {'document_restricted': False, 'restricted_reports': set(), 'unsupported_providers': set(),
              'qualified_providers': set(), 'restricted_providers': set()}
    for data in responses.values():
        for candidate in data['parsed']['records'].values():
            native = candidate['native']
            if native['kind'] == 'provider' and native['unv_2025']:
                policy['unsupported_providers'].add(native['native_id'])
            if native['kind'] == 'provider' and _native_restriction(candidate, data['parsed']):
                policy['restricted_providers'].add(native['native_id'])
            if native['kind'] in ('document', 'report') and _native_restriction(candidate, data['parsed']):
                if native['kind'] == 'document':
                    policy['document_restricted'] = True
                else:
                    policy['restricted_reports'].add(native['native_id'])
    for row in indexed.values():
        mapping = row['source_mapping']
        if row['kind'] != 'provider' or mapping is None:
            continue
        parsed = responses[mapping['response_key']]['parsed']
        record = parsed['records'][mapping['locator']]; native = record['native']
        if native['kind'] != 'provider':
            continue
        restricted = _restricted(row, indexed) or _native_restriction(record, parsed)
        if restricted:
            policy['restricted_providers'].add(native['native_id'])
        # Direct evidence/scope check only: a provider does not recursively
        # qualify itself through the consumer dependency evaluator.
        if row['disposition'] == 'include' and not restricted and native['query_native']:
            policy['qualified_providers'].add(native['native_id'])
    policy['qualified_providers'] -= policy['restricted_providers'] | policy['unsupported_providers']
    return policy


def _scope(row, responses, indexed, policy=None):
    mapping = row['source_mapping']; record, response = None, None
    if mapping:
        response = responses[mapping['response_key']]['response']
        record = responses[mapping['response_key']]['parsed']['records'][mapping['locator']]
    restricted = _restricted(row, indexed)
    if record:
        restricted |= _native_restriction(record, responses[mapping['response_key']]['parsed'])
    # A caller cannot evade a native report/document restriction by reparenting its
    # independent item or omitting a native child from the selected denominator.
    for other in indexed.values():
        if not _restricted(other, indexed):
            continue
        if other['kind'] == 'document' or other['kind'] == 'report' and row['report_id'] == other['native_id']:
            restricted = True
        m = other['source_mapping']
        if mapping and m and m['response_key'] == mapping['response_key']:
            path, ancestor = mapping['locator'], m['locator']
            if path == ancestor or ancestor in ('', '/') or path.startswith(ancestor + '/'):
                restricted = True
    native = record['native'] if record else {}
    # Unsupported source providers remain obligations, including consumers.
    policy = _source_policy(responses, indexed) if policy is None else policy
    providers = set(native.get('provider_ids', []))
    unsupported_provider = bool(providers & policy['unsupported_providers'])
    missing_providers = sorted(providers - policy['qualified_providers'] - policy['restricted_providers'])
    restricted_providers = sorted(providers & policy['restricted_providers'])
    unresolved_providers = bool(missing_providers or restricted_providers or native.get('query_native') and not providers)
    restricted |= policy['document_restricted'] or row['report_id'] in policy['restricted_reports']
    restricted |= bool(restricted_providers)
    return {'item': row, 'node': record, 'response': response, 'native_kind': native.get('kind', 'unknown'),
        'restricted': restricted, 'report_id': native.get('report_id', row['report_id']),
        'provider_ids': native.get('provider_ids', []), 'query_visual': bool(row['kind'] in ('visual', 'placement', 'provider', 'query')
        and row['disposition'] == 'include' and not restricted and not unsupported_provider and not unresolved_providers
        and native.get('query_native')), 'unsupported_provider': unsupported_provider,
        'provider_dependencies_unqualified': unresolved_providers, 'missing_provider_ids': missing_providers,
        'restricted_provider_ids': restricted_providers}


def scope_item(value, key):
    responses, indexed = _validate(value)
    need(key in indexed, 'object_key_missing')
    return copy.deepcopy(_scope(indexed[key], responses, indexed))


def translate(payload, raw, helpers):
    responses, indexed = _validate(payload)
    need(type(raw) is bytes and F.decode(raw) == payload, 'raw_payload_mismatch')
    result = helpers['base'](payload, raw, 'businessobjects', 'supplied_businessobjects_api_snapshot')
    fingerprint, ident = sha(payload), payload['identity']
    result['source'].update(source_identity=copy.deepcopy(ident), definition_fingerprint=fingerprint,
                            definition_sha256=fingerprint)
    result.update(build_authority=False, migration_context={'route': None, 'route_reference': None, 'build_authority': False,
        'target_write_authority': False, 'native_validation': 'not_run', 'business_acceptance': 'not_assessed'})
    represented = {(r['source_mapping']['response_key'], r['source_mapping']['locator'])
                   for r in indexed.values() if r['source_mapping']}
    policy = _source_policy(responses, indexed)
    def emit(row, declared):
        scope = _scope(row, responses, indexed, policy); record, response = scope['node'], scope['response']
        mapping = row['source_mapping']; native = record['native'] if record else {}
        summary = copy.deepcopy({k: v for k, v in record.items() if k != 'payload'}) if record else None
        if record and 'payload' in record:
            summary['original_object_keys'] = list(record['payload'])
            summary['scalar_fields'] = {k: v for k, v in record['payload'].items() if type(v) not in (dict, list)}
        source = {'name': native.get('name') or row['key'] or native.get('kind'),
                  'inventory': copy.deepcopy(row), 'native_node': summary}
        evidence = {'source_mapping': copy.deepcopy(mapping), 'response_sha256': response['sha256'] if response else None,
                    'interpretation': 'inert_source_evidence'}
        facets = {k: {'status': 'needs_review', 'value': copy.deepcopy(evidence)}
                  for k in ('visual', 'query', 'layout', 'filters', 'interactions', 'security', 'content')}
        path = '/inventory/' + row['key'] if declared else '/responses/' + mapping['response_key'] + '#' + mapping['locator']
        helpers['add_asset'](result, NORMAL.get(row['kind'], row['kind']) if declared else 'unknown', source, path,
            row['key'] if declared else None, fingerprint, facets,
            id_kind='independent_inventory_key' if declared else 'native_locator_obligation', source_identity={
                'source_platform': 'businessobjects', 'object_key': row['key'] if declared else None,
                'native_kind': row['kind'], 'native_id': row['native_id'], 'source_mapping': copy.deepcopy(mapping),
                'document_id': ident['document_id'], 'document_cuid': ident['cuid'], 'report_engine': ident['report_engine'],
                'report_id': scope['report_id'], 'provider_ids': scope['provider_ids'],
                'definition_fingerprint': fingerprint, 'definition_sha256': response['sha256'] if response else fingerprint,
                'query_visual': scope['query_visual'] if declared else False, 'native_shape': native.get('native_shape', False),
                'requires_source_review': record is None or not native.get('native_shape', False)
                    or scope['unsupported_provider'] or scope['provider_dependencies_unqualified'] or native.get('kind') == 'unknown',
                'restricted_private_scope': scope['restricted'], 'declared_disposition': row['disposition'],
                'provenance': copy.deepcopy(response['provenance']) if response else None})
        if scope['restricted']:
            helpers['gap'](result, 'businessobjects.restricted_source_scope', path)
        if record is None:
            helpers['gap'](result, 'businessobjects.expected_object_without_native_evidence', path)
        elif not native['native_shape']:
            helpers['gap'](result, 'businessobjects.unqualified_native_shape_or_provenance', path)
        if native.get('unv_2025'):
            helpers['gap'](result, 'businessobjects.UNV_unavailable_2025', path)
        if scope['unsupported_provider']:
            helpers['gap'](result, 'businessobjects.unsupported_provider_dependency', path)
        if scope['provider_dependencies_unqualified']:
            helpers['gap'](result, 'businessobjects.provider_dependency_unqualified', path,
                {'missing_or_unqualified': scope['missing_provider_ids'], 'restricted': scope['restricted_provider_ids']})
        if row['kind'] in ('variable', 'merged_dimension', 'security', 'drill', 'alert', 'filter', 'prompt', 'input_control'):
            helpers['gap'](result, 'businessobjects.' + row['kind'] + '_semantics_require_review', path)
        for provider in scope['provider_ids']:
            result['dependencies'].append({'source_object_key': row['key'], 'source_mapping': copy.deepcopy(mapping),
                'reference_kind': 'data_provider_id', 'reference': provider, 'status': 'source_reference_not_target_binding'})
    for row in indexed.values():
        emit(row, True)
    omitted = unknown = 0
    for key, data in responses.items():
        response, parsed = data['response'], data['parsed']
        for path, record in parsed['records'].items():
            native = record['native']; kind = native['kind']
            substantive = (kind != 'unknown' or record['namespace'] or record['label'] not in STRUCTURAL)
            # JSON's root container is retained once as evidence rather than a fake object.
            if path == '' and len(record.get('payload', {})) == 1 and next(iter(record['payload']), None) in WRAPPERS:
                substantive = False
            if (key, path) not in represented and substantive:
                need(len(result['assets']) < MAX_ASSETS, 'projection_asset_limit')
                omitted += 1; unknown += kind == 'unknown'
                emit({'key': None, 'kind': kind, 'parent_key': None, 'native_id': native['native_id'],
                    'report_id': native['report_id'], 'disposition': 'manual_review', 'reference': response['reference'],
                    'configuration': {}, 'source_mapping': {'response_key': key, 'locator': path}}, False)
                helpers['gap'](result, 'businessobjects.native_object_not_independently_dispositioned', '/responses/' + key + '#' + path)
            if 'attributes' in record and any(local(k) in ('href', 'src', 'schemaLocation') or '://' in v
                                                for k, v in record['attributes'].items()):
                helpers['gap'](result, 'businessobjects.external_reference_not_followed', '/responses/' + key + '#' + path)
        if parsed.get('processing_instructions'):
            helpers['gap'](result, 'businessobjects.processing_instruction_not_executed', '/responses/' + key)
    result['businessobjects_coverage'] = {'independently_enumerated': len(indexed), 'original_responses': len(responses),
        'additional_native_obligations': omitted, 'unknown_native_obligations': unknown,
        'declared_scope': payload['inventory']['completeness'], 'export_completeness': 'not_established'}
    for code in _profile(ident):
        helpers['gap'](result, 'businessobjects.' + code)
    for detail in payload['gaps']:
        helpers['gap'](result, 'businessobjects.supplied_gap', detail=detail)
    for code in ('originals_are_not_execution_or_render_evidence', 'no_formula_or_query_compiler',
                 'source_identity_and_inventory_not_authenticated', 'effective_access_unverified',
                 'unqualified_source_results', 'external_universe_and_security_incomplete', 'no_DMA_producer'):
        helpers['gap'](result, 'businessobjects.' + code)
    return result


parse_snapshot = translate
