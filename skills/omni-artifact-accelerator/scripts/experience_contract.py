"""Quality decisions and source-evidence contracts; no execution or craft certification.

Quality is an index over canonical requirements, never a second requirement ledger.
Discovery excludes later delivery/context scaffolding; full intent freshness still
governs those annotations. File validators read bounded local regular files only.
"""
import copy
import base64
import binascii
import importlib.util
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import zlib

_loader = importlib.util.spec_from_file_location('quality_visual', Path(__file__).with_name('visual_experience.py'))
V = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(V)
QUALITIES = {'composition', 'typography', 'imagery', 'depth', 'interaction', 'motion',
             'spatial', 'reference_qualities', 'use_cadence', 'custom'}
SOURCED = {'user_statement', 'reused_decision'}
MAX_MANIFEST = 256 * 1024
MAX_VISUAL = 10 * 1024 * 1024


def _need(ok, message):
    if not ok:
        raise ValueError('experience_contract.' + message)


def _text(value, limit=8192):
    return type(value) is str and 0 < len(value.strip()) <= limit


def _fields(value, required, optional=(), label='fields'):
    _need(type(value) is dict and set(required) <= set(value)
          and set(value) <= set(required) | set(optional), label + '_invalid')


def _ids(value, label, empty=False):
    _need(type(value) is list and (empty or value) and len(value) <= 64
          and all(_text(v, 128) for v in value) and len(set(value)) == len(value), label + '_invalid')


def _texts(obj, keys, label):
    _need(all(_text(obj.get(k)) for k in keys), label + '_text_required')


def _metadata(spec):
    product = spec.get('product', {})
    return product.get('quality_bar') if type(product) is dict else None


def _referenced(meta):
    return sorted(set(meta['requirement_ids']) | ({meta['delegation_requirement_id']}
                  if meta.get('delegation_requirement_id') else set()))


def _attribution(req, notes, sourced=False):
    item = req.get('product')
    _need(type(item) is dict, 'quality_attribution_required')
    mapping = {'user_statement': 'user', 'reused_decision': 'reused', 'recommendation': 'proposal',
               'inference': 'proposal', 'unresolved': 'proposal'}
    basis = item.get('basis')
    _need(type(basis) is str and basis in mapping and req.get('origin') == mapping[basis],
          'quality_attribution_invalid')
    _need(not sourced or basis in SOURCED, 'quality_actual_answer_or_delegation_required')
    refs = item.get('source_refs')
    _need(type(refs) is list and refs and all(_text(r) and r.split('#', 1)[0] in notes for r in refs),
          'quality_sources_required')
    _need(type(item.get('acceptance')) is list and item['acceptance']
          and all(_text(a) for a in item['acceptance']), 'observable_quality_acceptance_required')
    if req.get('disposition') in {'selected', 'explicitly_omitted'}:
        _need(req.get('decision_ref') in refs, 'quality_decision_must_reference_source')


def _omission(req, notes):
    _need(req.get('disposition') == 'explicitly_omitted', 'quality_index_removed_use_explicit_omission')
    _attribution(req, notes, sourced=True)


def validate(spec):
    """Reject malformed adoption; preserve structurally valid unanswered drafts."""
    _need(type(spec) is dict, 'intent_required')
    product = spec.get('product', {})
    if type(product) is not dict or 'quality_bar' not in product:
        return
    meta = product['quality_bar']
    _fields(meta, {'schema_version', 'requirement_ids'}, {'delegation_requirement_id'}, 'quality_bar_fields')
    _need(type(meta['schema_version']) is int and meta['schema_version'] == 1, 'quality_bar_version_invalid')
    _ids(meta['requirement_ids'], 'quality_requirement_ids', empty=True)
    if 'delegation_requirement_id' in meta:
        _need(_text(meta['delegation_requirement_id'], 128)
              and meta['delegation_requirement_id'] not in meta['requirement_ids'], 'quality_delegation_reference_invalid')
    notes = product.get('note_paths')
    _need(type(notes) is list and notes and all(_text(n) for n in notes), 'quality_notes_required')
    surfaces = spec.get('surfaces')
    _need(type(surfaces) is list and surfaces and all(type(s) is str for s in surfaces), 'intent_surfaces_required')
    rows = spec.get('requirements')
    _need(type(rows) is list and all(type(r) is dict and _text(r.get('id'), 128) for r in rows), 'requirements_invalid')
    by_id = {r['id']: r for r in rows}
    _need(len(by_id) == len(rows), 'duplicate_requirement_id')
    ids = _referenced(meta)
    _need(set(ids) <= set(by_id), 'quality_dangling_reference')
    for ident in ids:
        req = by_id[ident]
        _attribution(req, notes, sourced=req.get('disposition') == 'explicitly_omitted')
        _need(req.get('disposition') in ('selected', 'unresolved', 'deferred', 'explicitly_omitted'),
              'quality_disposition_invalid')
        _need(type(req.get('surfaces')) is list and req['surfaces']
              and all(s in surfaces for s in req['surfaces']), 'quality_surface_invalid')
    for ident in meta['requirement_ids']:
        req = by_id[ident]
        value = req.get('value')
        if value is None and req['disposition'] in ('unresolved', 'deferred'):
            continue
        _need(type(value) is dict and type(value.get('quality')) is str
              and value['quality'] in QUALITIES, 'quality_value_invalid')
        extra = {'custom_label'} if value['quality'] == 'custom' else (
            {'usage'} if value['quality'] in {'imagery', 'motion'} else set())
        _fields(value, {'quality', 'direction'} | extra, label='quality_value_fields')
        _need(_text(value['direction']), 'quality_direction_required')
        if 'custom_label' in extra:
            _need(_text(value['custom_label'], 120), 'quality_custom_label_required')
        if 'usage' in extra:
            _need(value['usage'] in ('included', 'omitted'), 'quality_usage_invalid')
    # Recognized active quality decisions cannot silently bypass the index.
    for req in rows:
        value = req.get('value')
        if (type(value) is dict and type(value.get('quality')) is str
                and value['quality'] in QUALITIES and req['id'] not in meta['requirement_ids']):
            _omission(req, notes)
    delegate = meta.get('delegation_requirement_id')
    if delegate:
        req = by_id[delegate]
        _attribution(req, notes, sourced=True)
        _need(req.get('disposition') == 'selected'
              and req.get('value') == {'delegation_scope': 'experience_quality'}, 'quality_delegation_scope_invalid')
        proposed = [by_id[i] for i in meta['requirement_ids']
                    if by_id[i]['disposition'] != 'explicitly_omitted' and by_id[i]['origin'] == 'proposal']
        _need({s for r in proposed for s in r['surfaces']} <= set(req['surfaces']), 'quality_delegation_surface_missing')


def quality_context(spec):
    """Semantic D projection, excluding delivery, assets, roles and all contexts."""
    validate(spec)
    meta = _metadata(spec)
    if meta is None:
        return None
    by_id = {r['id']: r for r in spec['requirements']}
    rows = [V._discovery_requirement(by_id[i]) for i in _referenced(meta)]
    return {'metadata': copy.deepcopy(meta), 'scope': spec['product'].get('scope'),
            'requirements': rows,
            'note_paths': sorted({ref.split('#', 1)[0] for r in rows for ref in r['product']['source_refs']})}


def quality_check(spec):
    context = quality_context(spec)
    result = {'status': 'not_assessed', 'findings': [], 'requirement_ids': []}
    if context is None:
        return result
    meta = context['metadata']
    by_id = {r['id']: r for r in context['requirements']}
    result['requirement_ids'] = sorted(by_id)
    active = [by_id[i] for i in meta['requirement_ids'] if by_id[i]['disposition'] != 'explicitly_omitted']
    if not active:
        result['findings'].append({'code': 'quality_decisions_required'})
    for req in active:
        if req['disposition'] != 'selected' or req['product']['basis'] == 'unresolved':
            result['findings'].append({'code': 'quality_decision_unresolved', 'requirement_id': req['id']})
        elif req['product']['basis'] not in SOURCED and not meta.get('delegation_requirement_id'):
            result['findings'].append({'code': 'quality_answer_or_delegation_required', 'requirement_id': req['id']})
    covered = {surface for req in active for surface in req['surfaces']}
    for surface in sorted(set(spec['surfaces']) - covered):
        result['findings'].append({'code': 'quality_surface_decisions_required', 'surface': surface})
    result['status'] = 'unresolved' if result['findings'] else 'ready'
    return result


def validate_transition(previous, current):
    before, after = quality_context(previous), quality_context(current)
    if before is None:
        return
    _need(after is not None, 'quality_context_removed_reconcile_scope_instead')
    indexed = {r['id'] for r in after['requirements']}
    current_rows = {r['id']: r for r in current['requirements']}
    for req in before['requirements']:
        if req['id'] not in indexed:
            _omission(current_rows.get(req['id'], {}), current['product']['note_paths'])


def _active(spec, surface):
    _need(quality_check(spec)['status'] == 'ready', 'quality_discovery_not_ready')
    ids = set(_metadata(spec)['requirement_ids'])
    return {r['id']: r for r in spec['requirements'] if r['id'] in ids
            and r['disposition'] != 'explicitly_omitted' and (surface is None or surface in r['surfaces'])}


def _treatments(spec, surface):
    context = V.visual_context(spec)
    if context is None:
        return {}
    _need(V.visual_report(spec)['status'] == 'ready', 'visual_discovery_not_ready')
    ids = context['metadata']['follow_up']['requirement_ids']
    return {r['id']: r for r in spec['requirements'] if r['id'] in ids
            and r['disposition'] == 'selected' and surface in r['surfaces']
            and type(r.get('value')) is dict and 'treatment' in r['value']}


def _read(root, path, P, json_file=False):
    file = P.relative_file(Path(root), path)
    if json_file:
        _need(file.stat().st_size <= MAX_MANIFEST, 'manifest_too_large')
        value, raw = P.read_json(file)
        _need(len(raw) <= MAX_MANIFEST, 'manifest_too_large')
    else:
        raw, value = file.read_bytes(), None
    _need(len(raw) <= MAX_VISUAL, 'dependency_too_large')
    return value, raw, {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}


def _css(value):
    # Reject CSS escapes/imports and active legacy constructs. Local paint-server
    # references are the only URLs; nothing here executes or resolves a resource.
    _need(not any(c in value for c in ('\\', '@')) and
          not re.search(r'expression|javascript|vbscript|behavior|binding|/\*', value, re.I), 'svg_active_css_forbidden')
    for target in re.findall(r'url\s*\((.*?)\)', value, re.I | re.S):
        _need(re.fullmatch(r'''["']?#[A-Za-z_][\w.:-]*["']?''', target.strip()) is not None,
              'svg_external_resource_forbidden')


def _svg(raw, labels):
    _need(len(raw) <= 2 * 1024 * 1024, 'svg_too_large')
    try:
        source = raw.decode('utf-8')
        _need(not re.search(r'<!|<\?(?!xml\s)', source, re.I), 'svg_declarations_forbidden')
        tree = ET.fromstring(source)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError('experience_contract.svg_invalid') from exc
    ns = '{http://www.w3.org/2000/svg}'
    _need(tree.tag in ('svg', ns + 'svg'), 'svg_root_required')
    allowed = {'svg', 'g', 'defs', 'title', 'desc', 'rect', 'circle', 'ellipse', 'path', 'line',
               'polyline', 'polygon', 'text', 'tspan', 'textPath', 'use', 'symbol', 'clipPath',
               'mask', 'linearGradient', 'radialGradient', 'stop', 'pattern', 'style', 'image'}
    marks = 0
    for element in tree.iter():
        tag = element.tag[len(ns):] if element.tag.startswith(ns) else element.tag
        _need(tag in allowed, 'svg_element_forbidden')
        marks += tag in {'rect', 'circle', 'ellipse', 'path', 'line', 'polyline', 'polygon', 'use', 'image'}
        if tag == 'style':
            _css(element.text or '')
        for key, value in element.attrib.items():
            local = key.split('}')[-1]
            _need(not local.lower().startswith('on') and local not in ('base',), 'svg_active_attribute_forbidden')
            if '}' in key:
                _need(key in ('{http://www.w3.org/1999/xlink}href', '{http://www.w3.org/XML/1998/namespace}space'),
                      'svg_attribute_namespace_forbidden')
            if local == 'href':
                embedded = re.fullmatch(r'data:image/(png|jpeg);base64,([A-Za-z0-9+/=\s]+)', value) if tag == 'image' else None
                if embedded:
                    try:
                        data = base64.b64decode(re.sub(r'\s+', '', embedded[2]), validate=True)
                    except (ValueError, binascii.Error) as exc:
                        raise ValueError('experience_contract.svg_embedded_image_invalid') from exc
                    _raster(data, '.png' if embedded[1] == 'png' else '.jpg')
                else:
                    _need(re.fullmatch(r'#[A-Za-z_][\w.:-]*', value) is not None, 'svg_external_resource_forbidden')
            _css(value)
    text = ' '.join(''.join(e.itertext()) for e in tree.iter() if e.tag in ('text', ns + 'text'))
    _need(marks > 0 and text.strip(), 'representative_graphic_and_labels_required')
    _need(all(label in text for label in labels), 'representative_labels_not_in_svg')


def _raster(raw, suffix):
    """Check bounded file structure, not pixels, visual quality or authenticity."""
    if suffix == '.png':
        _need(raw.startswith(b'\x89PNG\r\n\x1a\n'), 'png_signature_invalid')
        pos, kinds = 8, []
        while pos < len(raw):
            _need(pos + 12 <= len(raw), 'png_chunk_invalid')
            size = int.from_bytes(raw[pos:pos + 4], 'big')
            kind, data = raw[pos + 4:pos + 8], raw[pos + 8:pos + 8 + size]
            _need(pos + size + 12 <= len(raw), 'png_chunk_invalid')
            _need(zlib.crc32(kind + data) & 0xffffffff == int.from_bytes(raw[pos + size + 8:pos + size + 12], 'big'),
                  'png_crc_invalid')
            if not kinds:
                _need(kind == b'IHDR' and size == 13, 'png_header_invalid')
                width, height = struct.unpack('>II', data[:8])
                _need(0 < width <= 20000 and 0 < height <= 20000, 'raster_dimensions_invalid')
            _need(kind not in (b'acTL', b'fcTL', b'fdAT'), 'animated_visual_not_supported')
            kinds.append(kind)
            pos += size + 12
            if kind == b'IEND':
                _need(size == 0 and pos == len(raw), 'png_trailing_bytes')
                break
        _need(kinds and kinds[-1] == b'IEND' and b'IDAT' in kinds, 'png_incomplete')
    else:
        _need(suffix in ('.jpg', '.jpeg') and raw.startswith(b'\xff\xd8') and raw.endswith(b'\xff\xd9'),
              'jpeg_signature_invalid')
        pos, dimensions = 2, False
        while pos < len(raw) - 2:
            _need(raw[pos] == 255, 'jpeg_marker_invalid')
            while pos < len(raw) and raw[pos] == 255:
                pos += 1
            _need(pos < len(raw), 'jpeg_marker_invalid')
            marker = raw[pos]
            pos += 1
            if marker == 0xda:
                break
            _need(pos + 2 <= len(raw), 'jpeg_segment_invalid')
            size = int.from_bytes(raw[pos:pos + 2], 'big')
            _need(size >= 2 and pos + size <= len(raw), 'jpeg_segment_invalid')
            if marker in (0xc0, 0xc1, 0xc2):
                _need(size >= 8, 'jpeg_frame_invalid')
                height, width = struct.unpack('>HH', raw[pos + 3:pos + 7])
                _need(0 < width <= 20000 and 0 < height <= 20000, 'raster_dimensions_invalid')
                dimensions = True
            pos += size
        _need(dimensions, 'jpeg_dimensions_missing')


def _coverage(value, active, handoff=False, destination_ids=()):
    _need(type(value) is list and len(value) <= 64, 'quality_coverage_invalid')
    seen = set()
    for row in value:
        _fields(row, {'requirement_id', 'implementation', 'destination_ids' if handoff else 'visual_locator'},
                label='quality_coverage_fields')
        ident = row['requirement_id']
        _need(type(ident) is str and ident in active and ident not in seen, 'quality_coverage_unknown_or_duplicate')
        seen.add(ident)
        _need(_text(row['implementation']), 'quality_implementation_required')
        if handoff:
            _ids(row['destination_ids'], 'quality_destination_ids')
            _need(set(row['destination_ids']) <= set(destination_ids), 'quality_destination_unknown')
        else:
            _need(_text(row['visual_locator']), 'quality_visual_locator_required')
    _need(seen == set(active), 'same_active_quality_coverage_required')


def validate_concept(root, option_manifest_path, spec, P):
    """Pin one concrete option. Stage E owns count, comparability and selection."""
    return _concept(root, option_manifest_path, spec, P, component=False)


def _concept(root, option_manifest_path, spec, P, component):
    obj, _, manifest_pin = _read(root, option_manifest_path, P, True)
    if type(obj) is dict and obj.get('kind') == 'analyst_concept_set':
        _need(not component, 'nested_concept_sets_forbidden')
        _fields(obj, {'schema_version', 'kind', 'option_id', 'analytical_scope', 'structure',
                      'primary_interaction', 'surface_manifests'}, label='concept_set_fields')
        _need(type(obj['schema_version']) is int and obj['schema_version'] == 1, 'concept_set_version_invalid')
        _texts(obj, ('option_id', 'analytical_scope', 'structure', 'primary_interaction'), 'concept_set')
        _ids(obj['surface_manifests'], 'surface_manifests')
        _need(len(obj['surface_manifests']) == len(spec['surfaces']), 'concept_set_surface_count_invalid')
        children = [_concept(root, path, spec, P, component=True) for path in obj['surface_manifests']]
        _need(sorted(c['metadata']['surface'] for c in children) == sorted(spec['surfaces']),
              'concept_set_surface_coverage_invalid')
        normalize = lambda value: ' '.join(value.split()).casefold()
        _need(all(c['metadata']['option_id'] == obj['option_id'] and
                  normalize(c['metadata']['analytical_scope']) == normalize(obj['analytical_scope']) for c in children),
              'concept_set_identity_or_scope_mismatch')
        hashes = sorted(c['metadata']['representative_sha256'] for c in children)
        _need(len(set(hashes)) == len(hashes), 'concept_set_requires_surface_specific_visuals')
        pins = {p['path']: p for p in [manifest_pin, *(p for c in children for p in c['dependencies'])]}
        return {'schema_version': 1, 'kind': 'analyst_concept_validation', 'metadata': {
            'option_id': obj['option_id'], 'surface': 'both' if len(children) > 1 else children[0]['metadata']['surface'],
            'surfaces': sorted(spec['surfaces']), 'analytical_scope': obj['analytical_scope'],
            'structure': obj['structure'], 'primary_interaction': obj['primary_interaction'],
            'quality_requirement_ids': sorted({i for c in children for i in c['metadata']['quality_requirement_ids']}),
            'treatment_requirement_ids': sorted({i for c in children for i in c['metadata']['treatment_requirement_ids']}),
            'evidence_kind': 'surface_evidence_set', 'representative_sha256': P.digest(P.canonical(hashes)),
            'representative_sha256s': hashes, 'representative_artifact_sha256s': hashes,
            'representative_artifacts': sorted([p for c in children for p in c['metadata']['representative_artifacts']], key=lambda p: p['path']),
            'surface_metadata': sorted([c['metadata'] for c in children], key=lambda m: m['surface']),
            'observation_limit': 'Each surface has pinned visual evidence; source completeness does not certify rendered craft or native behavior.'},
            'dependencies': [pins[path] for path in sorted(pins)]}
    _fields(obj, {'schema_version', 'kind', 'option_id', 'surface', 'analytical_scope', 'structure',
                  'primary_interaction', 'quality_coverage', 'treatment_coverage', 'representative', 'responsive', 'constraints'},
            label='concept_fields')
    _need(type(obj['schema_version']) is int and obj['schema_version'] == 1
          and obj['kind'] == 'analyst_concept_manifest', 'concept_version_invalid')
    _texts(obj, ('option_id', 'analytical_scope', 'structure', 'primary_interaction', 'responsive'), 'concept')
    _need(type(obj['surface']) is str and obj['surface'] in spec['surfaces'], 'concept_surface_invalid')
    _need(component or spec['surfaces'] == [obj['surface']], 'all_product_surfaces_need_concept_evidence')
    active = _active(spec, obj['surface'])
    _coverage(obj['quality_coverage'], active)
    treatments = _treatments(spec, obj['surface'])
    _coverage(obj['treatment_coverage'], treatments)
    constraints = obj['constraints']
    _fields(constraints, {'feasibility', 'assets', 'dependencies', 'observation_limits'}, label='concept_constraints')
    _texts(constraints, tuple(constraints), 'concept_constraints')
    representative = obj['representative']
    _fields(representative, {'path', 'evidence_kind', 'state', 'labels'}, {'observation_path'}, 'representative_fields')
    _need(_text(representative['state']), 'representative_state_required')
    labels = representative['labels']
    _need(type(labels) is list and 0 < len(labels) <= 64
          and all(_text(label, 512) for label in labels), 'representative_labels_required')
    _, raw, visual_pin = _read(root, representative['path'], P)
    suffix = Path(representative['path']).suffix.lower()
    kind = representative['evidence_kind']
    dependencies = [manifest_pin, visual_pin]
    if kind == 'static_source':
        _need(suffix == '.svg' and 'observation_path' not in representative, 'static_source_requires_original_svg')
        _svg(raw, labels)
    else:
        _need(kind == 'rendered_capture' and suffix in ('.png', '.jpg', '.jpeg')
              and 'observation_path' in representative, 'rendered_capture_evidence_required')
        _raster(raw, suffix)
        path = representative['observation_path']
        _need(type(path) is str and path.endswith(('.json', '.md')), 'render_observation_path_invalid')
        _, observation, pin = _read(root, path, P, path.endswith('.json'))
        _need(observation.strip() and len(observation) <= MAX_MANIFEST, 'render_observation_required')
        dependencies.append(pin)
    return {'schema_version': 1, 'kind': 'analyst_concept_validation',
            'metadata': {'option_id': obj['option_id'], 'surface': obj['surface'], 'surfaces': [obj['surface']],
                         'analytical_scope': obj['analytical_scope'], 'structure': obj['structure'],
                         'primary_interaction': obj['primary_interaction'],
                         'quality_requirement_ids': sorted(active), 'evidence_kind': kind,
                         'treatment_requirement_ids': sorted(treatments),
                         'representative_sha256': visual_pin['sha256'],
                         'representative_sha256s': [visual_pin['sha256']],
                         'representative_artifact_sha256s': [visual_pin['sha256']],
                         'representative_artifacts': [visual_pin],
                         'observation_limit': 'Source/structure validation only; supplied render claims are not authenticated; craft and native behavior unassessed.'},
            'dependencies': sorted(dependencies, key=lambda p: p['path'])}


def _capability(value, fields, label):
    if type(value) is dict and value.get('applicable') is False:
        _fields(value, {'applicable', 'rationale'}, label=label)
        _need(_text(value['rationale']), label + '_rationale_required')
        return False
    _fields(value, set(fields), label=label)
    _texts(value, fields, label)
    return True


def validate_handoff(root, design_path, spec, P):
    """Validate selected design detail; caller binds its concept to actual choice."""
    design, _, design_pin = _read(root, design_path, P, True)
    _need(type(design) is dict, 'design_object_required')
    handoff = design.get('experience_handoff')
    _fields(handoff, {'schema_version', 'concept_manifest_path', 'quality_coverage'}, label='handoff_fields')
    _need(type(handoff['schema_version']) is int and handoff['schema_version'] == 1, 'handoff_version_invalid')
    concept = validate_concept(root, handoff['concept_manifest_path'], spec, P)
    surface = concept['metadata']['surface']
    active = _active(spec, None)
    destinations = design.get('destinations')
    _need(type(destinations) is list and 0 < len(destinations) <= 32, 'handoff_destinations_required')
    required = {'id', 'purpose', 'focal_content', 'primary_action', 'evidence', 'drill', 'return',
                'composition', 'typography', 'chart_anatomy', 'controls', 'responsive', 'state_ownership', 'journey_id'}
    ids, capabilities, surface_by_id = [], {'imagery': set(), 'motion': set()}, {}
    for destination in destinations:
        # Existing destination rows remain canonical and may retain additional
        # app/dashboard-specific design fields. No parallel destination ledger.
        _need(type(destination) is dict and required <= set(destination), 'destination_fields_invalid')
        _texts(destination, tuple(required - {'chart_anatomy'}), 'destination')
        _need(destination['id'] not in ids, 'destination_duplicate')
        ids.append(destination['id'])
        destination_surface = destination.get('surface', surface)
        _need(type(destination_surface) is str and destination_surface in spec['surfaces'], 'destination_surface_required')
        surface_by_id[destination['id']] = destination_surface
        chart = destination['chart_anatomy']
        if type(chart) is dict and chart.get('applicable') is True:
            _fields(chart, {'applicable', 'details'}, label='chart_anatomy')
            _need(_text(chart['details']), 'chart_anatomy_details_required')
        else:
            _need(type(chart) is dict and chart.get('applicable') is False, 'chart_applicability_required')
            _capability(chart, (), 'chart_anatomy')
        for name, fields in {'imagery': ('role', 'placement', 'crop', 'alternative_text', 'fallback', 'narrow'),
                             'motion': ('trigger', 'purpose', 'continuity', 'interruption', 'reduced_motion')}.items():
            if name in destination:
                if _capability(destination[name], fields, name):
                    capabilities[name].add(destination_surface)
    _need(set(surface_by_id.values()) == set(spec['surfaces']), 'handoff_surface_coverage_required')
    journeys = design.get('journeys')
    _need(type(journeys) is list and 0 < len(journeys) <= 64, 'canonical_journeys_required')
    journey_ids = set()
    for journey in journeys:
        fields = {'id', 'destination_ids', 'entry', 'action', 'detail', 'return', 'retained_state', 'recovery'}
        _need(type(journey) is dict and fields <= set(journey), 'journey_fields_invalid')
        _texts(journey, tuple(fields - {'destination_ids'}), 'journey')
        _need(journey['id'] not in journey_ids, 'journey_duplicate')
        journey_ids.add(journey['id'])
        _ids(journey['destination_ids'], 'journey_destination_ids')
        _need(set(journey['destination_ids']) <= set(ids), 'journey_destination_unknown')
    journeys_by_id = {j['id']: j for j in journeys}
    _need(all(d['journey_id'] in journey_ids and d['id'] in journeys_by_id[d['journey_id']]['destination_ids']
              for d in destinations), 'destination_journey_reference_invalid')
    _coverage(handoff['quality_coverage'], active, True, ids)
    for coverage in handoff['quality_coverage']:
        _need({surface_by_id[i] for i in coverage['destination_ids']} == set(active[coverage['requirement_id']]['surfaces']),
              'quality_destination_surface_coverage_required')
    for name in capabilities:
        for destination_surface in spec['surfaces']:
            choices = {r['value']['usage'] for r in active.values() if r['value']['quality'] == name
                       and destination_surface in r['surfaces']}
            _need(len(choices) <= 1, 'quality_capability_choices_conflict')
            if choices == {'included'}:
                _need(destination_surface in capabilities[name], 'selected_' + name + '_handoff_required')
                _need(all(name in d for d in destinations if surface_by_id[d['id']] == destination_surface),
                      name + '_destination_applicability_required')
            if choices == {'omitted'}:
                _need(destination_surface not in capabilities[name], 'omitted_' + name + '_cannot_be_implemented')
    report = None
    if 'report' in spec['surfaces']:
        report = P.routing_helper('report_contract').validate_handoff(root, design, spec, P)
    pins = {p['path']: p for p in [design_pin, *concept['dependencies'],
                                 *(report['dependencies'] if report else [])]}
    return {'schema_version': 1, 'kind': 'analyst_handoff_validation',
            'metadata': {'option_id': concept['metadata']['option_id'], 'surface': surface, 'surfaces': sorted(spec['surfaces']),
                         'concept_manifest_path': handoff['concept_manifest_path'],
                         'quality_requirement_ids': sorted(active), 'destination_ids': sorted(ids),
                         **({'report_capability_gaps': report['gaps'],
                             'report_native_authoring_qualified': False} if report else {}),
                         'observation_limit': 'Declared design completeness only; no rendered, interaction, native or acceptance certification.'},
            'dependencies': [pins[path] for path in sorted(pins)]}
