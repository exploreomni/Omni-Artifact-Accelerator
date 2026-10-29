"""Bounded design requirements and file selection; no execution, network or approval."""
import copy
import importlib.util
from pathlib import Path
import re
from urllib.parse import urlsplit

_s = importlib.util.spec_from_file_location('_intent_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P)
SPEC = 'analyst_design_intent_spec'
KIND = 'analyst_design_intent'
BRANDING = {'requested', 'none', 'unknown'}
VISUAL = {'craft', 'native_behavior', 'responsive', 'accessibility', 'human_usability'}
ROLES = {'product-owner', 'branding', 'design-systems', 'app-designer', 'dashboard-designer', 'report-designer', 'report-builder', 'app-engineer', 'bi-engineer', '3d-modeler',
         'qa-analyst', 'motion-designer', 'data-storyteller'}


def text(value):
    return type(value) is str and bool(value.strip())


def need(condition, message):
    P.need(condition, 'design_intent.' + message)


def relative(path):
    need(text(path), 'path_required')
    p = Path(path)
    need(not p.is_absolute() and '..' not in p.parts and '\\' not in path and p.as_posix() == path
         and path != 'project.json', 'canonical_engagement_path_required')
    return path


def pin(root, path):
    raw = P.relative_file(root, relative(path)).read_bytes()
    return {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}


def url(value):
    need(text(value), 'url_required')
    p = urlsplit(value)
    need(p.scheme == 'https' and p.hostname and not p.username and not p.password and not p.fragment,
         'https_url_without_credentials_required')


def rows(value, label, key='id'):
    need(type(value) is list, label + '_list_required')
    ids = set()
    for row in value:
        need(type(row) is dict and text(row.get(key)), label + '_identity_required')
        need(row[key] not in ids, label + '_duplicate_identity')
        ids.add(row[key])
    return value


def validate_surfaces(value, allowed):
    need(type(value) is list and value and all(type(s) is str for s in value)
         and len(set(value)) == len(value) and set(value) <= set(allowed), 'surfaces_invalid')


def validate_report_target(value):
    """Local candidates or pinned published observations; never native write authority."""
    need(type(value) is dict and {'surface', 'state'} <= set(value) <=
         {'surface', 'state', 'document_id', 'draft_id', 'instance', 'capability_evidence_path'}
         and value['surface'] == 'report', 'report_target_invalid')
    need(value['state'] in {'local', 'published'}, 'report_draft_lifecycle_unqualified')
    need(value.get('draft_id') is None, 'report_draft_lifecycle_unqualified')
    if value['state'] == 'local':
        need(all(value.get(k) is None for k in ('document_id', 'instance', 'capability_evidence_path')),
             'local_report_cannot_claim_native_identity')
        return
    url(value.get('instance'))
    origin = urlsplit(value['instance'])
    need(origin.path in {'', '/'} and not origin.query and not origin.fragment, 'report_origin_required')
    ident = value.get('document_id')
    need(text(ident) and len(ident) <= 256 and all(32 <= ord(c) < 127 for c in ident)
         and not any(c in ident for c in '/\\?#'), 'report_document_required')
    relative(value.get('capability_evidence_path'))


def starter(surfaces, branding='unknown', website=None):
    validate_surfaces(surfaces, {'app', 'dashboard', 'report'})
    need(branding in BRANDING, 'branding_invalid')
    if website is not None:
        url(website)
    return {'schema_version': 1, 'kind': SPEC, 'branding': branding, 'website': website,
            'surfaces': list(surfaces),
            'logo_sourcing': {'mode': 'unresolved', 'authorization_ref': None, 'source': None},
            'selections': [{'surface': s, 'design_path': None, 'brand_path': None,
                            'candidate_path': None, 'target': None} for s in surfaces],
            'assets': [], 'requirements': ([{'id': 'brand-logo', 'category': 'logo',
                'purpose': 'Retain the requested brand identity on the selected surfaces.',
                'surfaces': list(surfaces), 'required': True, 'origin': 'proposal',
                'disposition': 'unresolved', 'value': None, 'asset_ids': [], 'decision_ref': None,
                'contexts': []}] if branding == 'requested' else [])}


def validate(spec, project):
    need(type(spec) is dict and type(spec.get('schema_version')) is int and spec['schema_version'] == 1
         and spec.get('kind') == SPEC, 'unsupported_spec')
    need(spec.get('branding') in BRANDING, 'branding_invalid')
    validate_surfaces(spec.get('surfaces'), project['surfaces'])
    need(set(spec['surfaces']) == set(project['surfaces']), 'project_surfaces_must_be_accounted')
    if spec.get('website') is not None:
        url(spec['website'])
    sourcing = spec.get('logo_sourcing', {})
    need(type(sourcing) is dict and sourcing.get('mode', 'unresolved') in {'unresolved', 'supplied', 'official_site'},
         'logo_sourcing_invalid')
    if sourcing.get('mode') == 'official_site':
        need(text(sourcing.get('authorization_ref')), 'official_site_authorization_required')
    selections = rows(spec.get('selections'), 'selections', 'surface')
    need({s['surface'] for s in selections} == set(spec['surfaces']), 'selection_surfaces_must_be_accounted')
    for selection in selections:
        for key in ('design_path', 'brand_path', 'candidate_path'):
            if selection.get(key) is not None:
                relative(selection[key])
        target = selection.get('target')
        if selection.get('candidate_path') is not None:
            need(type(target) is dict and target.get('surface') == selection['surface']
                 and target.get('state') in {'local', 'draft', 'published'}, 'candidate_target_required')
            if selection['surface'] == 'report':
                validate_report_target(target)
            if target['state'] != 'local':
                url(target.get('instance'))
                parsed = urlsplit(target['instance'])
                need(parsed.path in {'', '/'} and not parsed.query, 'target_origin_required')
                need(text(target.get('document_id')), 'target_document_required')
            if target['state'] == 'draft':
                need(text(target.get('draft_id')), 'target_draft_required')
            else:
                need(target.get('draft_id') is None, 'unexpected_draft_id')
        else:
            need(target is None, 'target_without_candidate')
    assets = rows(spec.get('assets'), 'assets')
    for asset in assets:
        local, remote = asset.get('local_path'), asset.get('remote_url')
        need(bool(local) != bool(remote), 'asset_requires_one_local_or_remote_source')
        if local:
            relative(local)
        if remote:
            url(remote)
        need(text(asset.get('source')) and text(asset.get('authorization_ref')) and
             asset.get('sourcing_mode') in {'supplied', 'official_site', 'original'}, 'asset_provenance_required')
        for field in ('variant', 'placement', 'appearance', 'loading_method'):
            need(text(asset.get(field)), 'asset_' + field + '_required')
    asset_ids = {a['id'] for a in assets}
    assets_by_id = {a['id']: a for a in assets}
    requirements = rows(spec.get('requirements'), 'requirements')
    for req in requirements:
        need(text(req.get('category')) and text(req.get('purpose')) and type(req.get('required')) is bool,
             'requirement_definition_required')
        validate_surfaces(req.get('surfaces'), spec['surfaces'])
        need(req.get('origin') in {'user', 'reused', 'proposal'} and req.get('disposition') in
             {'unresolved', 'selected', 'explicitly_omitted', 'deferred'}, 'requirement_decision_invalid')
        ids = req.get('asset_ids', [])
        need(type(ids) is list and all(type(i) is str for i in ids) and len(set(ids)) == len(ids)
             and set(ids) <= asset_ids, 'requirement_asset_ids_invalid')
        contexts = rows(req.get('contexts', []), 'contexts')
        for context in contexts:
            need(text(context.get('appearance')) and text(context.get('state')), 'context_definition_required')
            if 'viewport' in context:
                vp = context['viewport']
                need(type(vp) is list and len(vp) == 2 and all(type(n) is int and 0 < n <= 32768 for n in vp),
                     'context_viewport_invalid')
        if req['disposition'] == 'explicitly_omitted':
            need(req['origin'] in {'user', 'reused'} and text(req.get('decision_ref')), 'omission_needs_user_decision')
        if req['disposition'] == 'selected':
            need(text(req.get('decision_ref')) and (ids or req.get('value') is not None), 'selection_value_required')
            need(contexts, 'selected_requirement_context_required')
            if req['category'] == 'logo':
                need(ids, 'selected_logo_asset_required')
                for asset_id in ids:
                    for field in ('size', 'accessible_name', 'fallback'):
                        need(text(assets_by_id[asset_id].get(field)), 'logo_asset_' + field + '_required')
    P.experience_helper().validate(spec, need, relative, P.ROLES)
    P.routing_helper('product_intent').validate(spec, need, relative, P.ROLES)
    if spec['branding'] == 'requested':
        covered = {s for req in requirements if req['category'] == 'logo' and req['required'] for s in req['surfaces']}
        need(covered == set(spec['surfaces']), 'required_logo_surfaces_missing')
    return spec


def references(spec):
    paths = set()
    paths.update(spec.get('product', {}).get('note_paths', []))
    if spec.get('product', {}).get('source_inventory_path'):
        paths.add(spec['product']['source_inventory_path'])
    for selection in spec['selections']:
        paths.update(selection[k] for k in ('design_path', 'brand_path', 'candidate_path') if selection.get(k))
        target = selection.get('target') or {}
        if selection['surface'] == 'report' and target.get('capability_evidence_path'):
            paths.add(relative(target['capability_evidence_path']))
    paths.update(a['local_path'] for a in spec['assets'] if a.get('local_path'))
    paths.update(path for req in spec['requirements'] for path in req.get('delivery', {}).get('dependency_paths', []))
    return sorted(paths)


def links(root, spec):
    findings = []
    for selection in spec['selections']:
        surface = selection['surface']
        for key in ('design_path', 'brand_path', 'candidate_path'):
            if not selection.get(key):
                findings.append({'code': 'selection_missing', 'surface': surface, 'field': key})
        if selection.get('design_path') and selection.get('brand_path'):
            design, _ = P.read_json(P.relative_file(root, selection['design_path']))
            need(type(design) is dict, 'design_object_required')
            if design.get('brand_contract') != selection['brand_path']:
                findings.append({'code': 'design_brand_reference_mismatch', 'surface': surface,
                                 'design_path': selection['design_path'], 'selected_brand': selection['brand_path']})
        if selection.get('brand_path'):
            brand, _ = P.read_json(P.relative_file(root, selection['brand_path']))
            need(type(brand) is dict, 'brand_object_required')
    return findings


def assembled(project, spec, spec_file, pins):
    body = {'schema_version': 1, 'kind': KIND, 'project_id': project['id'],
            'project_surfaces': project['surfaces'], 'spec': spec, 'spec_file': spec_file,
            'pins': pins, 'authority': 'recorded_selection_only'}
    body['content_sha256'] = P.digest(P.canonical(body))
    return body


def select(root, spec_path, output_relative):
    root, project = P.load_project(root)
    path = P.no_links(spec_path)
    need(path.is_relative_to(root), 'spec_inside_engagement_required')
    spec, raw = P.read_json(path)
    validate(spec, project)
    previous = None
    if project.get('design_intent'):
        previous = read_record(root, project['design_intent'])
        need('product' not in previous['spec'] or 'product' in spec,
             'product_context_removed_reconcile_scope_instead')
        need(not previous['spec'].get('product', {}).get('source_inventory_path') or
             spec.get('product', {}).get('source_inventory_path'), 'source_inventory_removed_reconcile_instead')
        P.routing_helper('product_intent').V.validate_transition(
            previous['spec'], spec, lambda ok, message: need(ok, 'visual_experience.' + message))
        P.routing_helper('product_intent').validate_quality_transition(previous['spec'], spec)
        P.routing_helper('product_intent').validate_refresh_transition(previous['spec'], spec)
        current = {r['id']: r for r in spec['requirements']}
        for req in previous['spec']['requirements']:
            if req['required']:
                replacement = current.get(req['id'], {})
                need(replacement.get('required') is True and set(req['surfaces']) <= set(replacement.get('surfaces', [])),
                     'required_requirement_removed_use_explicit_disposition')
                need('product' not in req or 'product' in replacement,
                     'required_product_attribution_removed')
    findings = links(root, spec)
    need(not any(f['code'] == 'design_brand_reference_mismatch' for f in findings), 'design_brand_reference_mismatch')
    relative(output_relative)
    paths = references(spec)
    spec_relative = path.relative_to(root).as_posix()
    need(output_relative not in paths + [spec_relative], 'output_replaces_input')
    need(type(project.get('design_intent_history', [])) is list, 'history_list_required')
    # Validate and read every input before writing. Unresolved choices can still be selected honestly.
    value = assembled(project, spec, {'path': spec_relative, 'sha256': P.digest(raw), 'bytes': len(raw)},
                      [pin(root, p) for p in paths])
    P.write_json(root / output_relative, value)
    selected = pin(root, output_relative)
    project.setdefault('design_intent_history', []).append(selected)
    project['design_intent'] = selected
    # Retire only known starter prompts. Current intent supplies derived questions;
    # separately recorded questions survive subsequent selections.
    questions = project['open_questions']
    if project.get('open_questions_kind') == 'starter_prompts' or questions == P.STARTER_QUESTIONS:
        retained = [q for q in questions if q not in P.STARTER_QUESTIONS]
        project['open_questions'] = list(dict.fromkeys([*choice_report(spec)[0], *retained]))
        project['open_questions_kind'] = 'current_intent_projection'
    elif project.get('open_questions_kind') == 'current_intent_projection':
        prior_questions = choice_report(previous['spec'])[0] if previous else []
        retained = [q for q in questions if q not in prior_questions]
        project['open_questions'] = list(dict.fromkeys([*choice_report(spec)[0], *retained]))
    # One atomic index replacement; a crash before this step leaves an unselected recoverable snapshot.
    P.write_json(root / 'project.json', project, replace=True)
    return {'path': str(root / output_relative), 'selection': selected, 'report': check(root)}


def read_record(root, record_pin):
    need(type(record_pin) is dict and text(record_pin.get('path')) and
         type(record_pin.get('sha256')) is str and re.fullmatch('[a-f0-9]{64}', record_pin['sha256']),
         'selection_pin_required')
    value, raw = P.read_json(P.relative_file(root, record_pin['path']))
    need(P.digest(raw) == record_pin['sha256'], 'selected_record_changed')
    _, project = P.load_project(root)
    need(value.get('kind') == KIND and value.get('schema_version') == 1 and
         value.get('project_id') == project['id'] and value.get('project_surfaces') == project['surfaces'],
         'record_project_mismatch')
    validate(value.get('spec'), project)
    pins = value.get('pins')
    need(type(pins) is list and [p.get('path') for p in pins] == references(value['spec']), 'pin_manifest_mismatch')
    need(value == assembled(project, value['spec'], value.get('spec_file'), pins), 'record_content_mismatch')
    original, original_raw = P.read_json(P.relative_file(root, value['spec_file']['path']))
    if P.digest(original_raw) == value['spec_file']['sha256']:
        need(original == value['spec'], 'embedded_spec_mismatch')
    return value


def load_selected(root):
    root, project = P.load_project(root)
    return read_record(root, project['design_intent']) if project.get('design_intent') else None


def choice_report(spec):
    questions, findings = [], []
    website_omitted = {surface for req in spec['requirements']
                       if req.get('category') == 'website' and req.get('disposition') == 'explicitly_omitted'
                       and req.get('origin') in {'user', 'reused'} and text(req.get('decision_ref'))
                       for surface in req.get('surfaces', [])}
    if (spec['branding'] == 'requested' and not spec.get('website')
            and not set(spec['surfaces']) <= website_omitted):
        questions.append('What is the official company website?')
    for req in spec['requirements']:
        if req['required'] and req['disposition'] in {'unresolved', 'deferred'}:
            findings.append({'code': 'requirement_' + req['disposition'], 'requirement_id': req['id'], 'surfaces': req['surfaces']})
            if req['category'] == 'logo':
                sourcing = spec.get('logo_sourcing', {})
                if sourcing.get('mode') in {'supplied', 'official_site'}:
                    findings.append({'code': 'logo_asset_pending', 'requirement_id': req['id']})
                else:
                    questions.append('Which approved logo file/URL or official-site sourcing authorization should be used, or is no logo intended?')
            else:
                questions.append('Resolve: ' + req['purpose'])
    for asset in spec['assets']:
        if asset.get('remote_url'):
            findings.append({'code': 'remote_asset_bytes_unverified', 'asset_id': asset['id'], 'url': asset['remote_url']})
    visual = P.routing_helper('product_intent').visual_report(spec)
    findings.extend(visual['findings'])
    refresh = P.routing_helper('product_intent').refresh_report(spec)
    findings.extend(refresh['findings'])
    if refresh['status'] == 'unresolved':
        questions.append('How should this App cache, refresh and age its data, or should it use no custom policy?')
    if any(f['code'].startswith('visual_family_') for f in visual['findings']):
        questions.append('Which visual experiences should be used, or has the user explicitly delegated the family recommendation?')
    if any(f['code'] == 'visual_treatment_follow_up_unresolved' for f in visual['findings']):
        questions.append('Resolve the comparison treatment with an attributable answer, reused decision, scoped delegation, or valid not-applicable rationale.')
    return list(dict.fromkeys(questions)), findings


def context_index(project, state):
    """Derived orientation only; historical files are neither loaded nor rewritten."""
    history = project.get('design_intent_history', [])
    history = history if type(history) is list else []
    result = {'authority': 'index_of_recorded_selection_only', 'integrity': state['status'],
            'selected_intent': copy.deepcopy(state['selected']),
            'historical_intents': [{k: p.get(k) for k in ('path', 'sha256', 'bytes')} for p in history
                                   if history_pin_valid(p) and p != state['selected']],
            'unresolved_requirement_ids': [r['id'] for r in state['requirements']
                                           if r['required'] and r['disposition'] in {'unresolved', 'deferred'}],
            'note': 'Use current requirements and selections below. Historical records are comparison evidence; '
                    'new user decisions require a new selection. Descriptive links are not pinned dependencies.'}
    if state.get('visual_context') is not None:
        result['visual_context'] = copy.deepcopy(state['visual_context'])
        result['visual_experience'] = copy.deepcopy(state['visual_experience'])
    if state.get('data_refresh_context') is not None:
        result['data_refresh_context'] = copy.deepcopy(state['data_refresh_context'])
        result['data_refresh'] = copy.deepcopy(state['data_refresh'])
    return result


def history_pin_valid(value):
    if type(value) is not dict or set(value) != {'path', 'sha256', 'bytes'}:
        return False
    try:
        relative(value['path'])
        return (type(value['sha256']) is str and re.fullmatch('[a-f0-9]{64}', value['sha256']) is not None
                and type(value['bytes']) is int and 0 <= value['bytes'] <= P.MAX_BYTES)
    except ValueError:
        return False


def check(root):
    root, project = P.load_project(root)
    selected = project.get('design_intent')
    base = {'status': 'not_assessed', 'selected': selected, 'requirements': [], 'assets': [], 'selections': [],
            'branding': 'unknown', 'website': None, 'logo_sourcing': {}, 'open_questions': [], 'findings': [],
            'paths': [], 'files': [], 'stale_paths': [], 'publication_authorized': False, 'claims_authenticated': False}
    try:
        need(type(project.get('design_intent_history', [])) is list, 'history_list_required')
        need(all(history_pin_valid(p) for p in project.get('design_intent_history', [])), 'history_pin_metadata_invalid')
        if selected:
            record = read_record(root, selected)
            spec = record['spec']
            base['files'] = record['pins']
            for expected in record['pins'] + [record['spec_file']]:
                try:
                    need(pin(root, expected['path']) == expected, 'changed_or_missing_file')
                except (ValueError, OSError):
                    base['stale_paths'].append(expected['path'])
            base['status'] = 'inconsistent' if base['stale_paths'] else 'consistent'
            base['paths'] = [selected['path'], record['spec_file']['path'], *references(spec)]
        elif project.get('design_intent_draft'):
            draft = project['design_intent_draft']
            spec, _ = P.read_json(P.relative_file(root, draft))
            # An untouched discovery starter is not a saved surface decision. Existing
            # migration setup can still choose App/both before defining any design.
            # Never reproject a selected record or a draft containing customer choices.
            if (type(spec) is dict and spec.get('surfaces') != project['surfaces']
                    and not project.get('design_intent_history')
                    and spec == starter(spec.get('surfaces'))):
                spec = starter(project['surfaces'])
                base['findings'].append({'code': 'unselected_starter_scope_refreshed',
                                         'surfaces': project['surfaces']})
            validate(spec, project)
            base['paths'] = [draft, *references(spec)]
            base['findings'].append({'code': 'missing_current_selection'})
        else:
            base['findings'].append({'code': 'missing_current_selection'})
            base['current_context'] = context_index(project, base)
            return base
        base.update({k: copy.deepcopy(spec.get(k)) for k in ('requirements', 'assets', 'selections', 'branding', 'website', 'logo_sourcing')})
        visual = P.routing_helper('product_intent')
        base['visual_experience'] = visual.visual_report(spec)
        base['visual_context'] = visual.visual_context(spec)
        base['data_refresh'] = visual.refresh_report(spec)
        base['data_refresh_context'] = visual.refresh_context(spec)
        questions, findings = choice_report(spec)
        base['open_questions'] = questions
        base['findings'].extend(findings)
        base['findings'].extend(links(root, spec))
        base['findings'].extend({'code': 'changed_or_missing_file', 'path': path} for path in base['stale_paths'])
        if any(f['code'] == 'design_brand_reference_mismatch' for f in base['findings']):
            base['status'] = 'inconsistent'
    except (ValueError, OSError, KeyError, TypeError) as exc:
        base['status'] = 'inconsistent'
        base['findings'].append({'code': 'invalid_current_selection', 'detail': str(exc)})
    base['current_context'] = context_index(project, base)
    return base


def packet_context(root, role):
    state = check(root)
    relevant = role in ROLES or any(
        req.get('delivery', {}).get('owner') == role or role in req.get('product', {}).get('suggested_roles', []) or any(
            role in P.experience_helper().CAPABILITIES.get(tag, ())
            for tag in req.get('delivery', {}).get('capabilities', []))
        for req in state['requirements'] if req['disposition'] not in {'deferred', 'explicitly_omitted'})
    if not relevant:
        return {'selected_intent': None, 'paths': [], 'requirements': [], 'findings': [], 'open_questions': []}
    if state['status'] == 'inconsistent':
        details = []
        for finding in state['findings']:
            if finding['code'] in {'changed_or_missing_file', 'design_brand_reference_mismatch', 'invalid_current_selection'}:
                affected = finding.get('path') or finding.get('design_path') or finding.get('detail')
                details.append(finding['code'] + (': ' + str(affected) if affected else ''))
        need(False, 'stale_or_invalid_packet_selection; ' + '; '.join(details[:8]))
    paths = state['paths'] if relevant else []
    if role != 'product-owner':
        # Notes remain pinned for freshness, but are not blanket specialist disclosure.
        root, project = P.load_project(root)
        spec = load_selected(root)['spec'] if state['selected'] else (
            P.read_json(P.relative_file(root, project['design_intent_draft']))[0]
            if project.get('design_intent_draft') else {})
        note_paths = set(spec.get('product', {}).get('note_paths', []))
        explicit = {p for req in spec.get('requirements', [])
                    for p in req.get('delivery', {}).get('dependency_paths', [])}
        paths = [p for p in paths if p not in note_paths - explicit]
    if relevant and not state['selected']:
        root, _ = P.load_project(root)
        for name in ('design', 'brand'):
            path = 'contracts/' + name + '.json'
            if (root / path).is_file():
                P.relative_file(root, path)
                paths.append(path)
    result = {'selected_intent': copy.deepcopy(state['selected']),
            'current_context': copy.deepcopy(state['current_context']),
            'paths': sorted(set(paths)), 'requirements': state['requirements'] if relevant else [],
            'findings': state['findings'] if relevant else [], 'open_questions': state['open_questions'] if relevant else []}
    if state.get('visual_context') is not None:
        result['visual_context'] = copy.deepcopy(state['visual_context'])
        result['visual_experience'] = copy.deepcopy(state['visual_experience'])
    if state.get('data_refresh_context') is not None:
        result['data_refresh_context'] = copy.deepcopy(state['data_refresh_context'])
        result['data_refresh'] = copy.deepcopy(state['data_refresh'])
    return result


def case_templates(root, review_spec=None):
    root, project = P.load_project(root)
    state = check(root)
    need(state['status'] != 'inconsistent', 'stale_or_invalid_case_selection')
    review = P.design_helper()
    if review_spec is not None:
        spec, _ = P.read_json(P.relative_file(root, relative(review_spec)))
        review.validate(spec, project)
    else:
        spec = {'intent': state['selected'], 'scope': {'surfaces': project['surfaces'],
                'required_lanes': ['craft'], 'coverage': {'mode': 'whole_experience'}}}
    coverage = review.destination_helper().derive(root, spec, state, P)
    selections = {s['surface']: s for s in state['selections']}
    requirements = {r['id']: r for r in state['requirements']}
    templates = []
    for obligation in coverage['obligations']:
        if not obligation['in_scope'] or obligation['applicability'].get('status') != 'required':
            continue
        req = requirements[obligation['requirement_id']]
        row = {'id': obligation['id'], 'surface': obligation['surface'], 'lane': obligation['lane'],
               'obligation_ids': [obligation['id']], 'asset_ids': req.get('asset_ids', []),
               'expected': req['purpose'], 'status': 'not_run', 'executed': False, 'capture_ids': [],
               'evidence_paths': [], 'candidate_id': None, 'reviewed_dependencies': {},
               'target': selections.get(obligation['surface'], {}).get('target')}
        if obligation['kind'] == 'journey':
            row['journey_observations'] = []
        templates.append(row)
    return {'intent': state['selected'], 'cases': templates, 'destination_coverage': coverage,
            'required_lanes': spec['scope']['required_lanes'], 'status': 'not_run',
            'note': ('Templates only; actual scope and lanes come from --review-spec. Without it only craft is generated. '
                     'No review, execution or native observation has occurred.')}


def review_coverage(root, spec, results, destination_coverage=None):
    """Reconcile named visual requirements with already validated review cases, in place."""
    state = check(root)
    binding = spec.get('intent')
    if not binding:
        return {'status': 'not_assessed', 'requirements': [], 'gaps': [{'code': 'intent_review_binding_missing'}]}
    good = state['status'] == 'consistent' and state['selected'] and all(binding.get(k) == state['selected'].get(k) for k in ('path', 'sha256'))
    gaps = [] if good else [{'code': 'intent_selection_stale_or_changed'}]
    gaps.extend({'code': 'intent_choice_unresolved', 'question': q} for q in state['open_questions'])
    gaps.extend(f for f in state['findings'] if f['code'] in {
        'selection_missing', 'design_brand_reference_mismatch', 'invalid_current_selection'})
    selection = {s['surface']: s for s in state['selections']}
    indexed = {r['id']: r for r in results}
    deps = {d['id']: d for d in spec['dependencies']}
    captures = {c['id']: c for c in spec.get('captures', [])}
    requirements = {r['id']: r for r in state['requirements']}
    for case in spec.get('cases', []):
        result = indexed[case['id']]
        reasons = []
        if destination_coverage is None and case['lane'] in VISUAL and not good:
            reasons.append('intent_selection_stale_or_changed')
        req_id = case.get('requirement_id')
        if req_id is not None and destination_coverage is None:
            req = requirements.get(req_id)
            selected = selection.get(case['surface'], {})
            candidate = deps.get(case.get('candidate_id'), {})
            contexts = {c['id']: c for c in req.get('contexts', [])} if req else {}
            context = contexts.get(case.get('requirement_context'))
            if not req or req['disposition'] != 'selected' or case['surface'] not in req['surfaces'] or not context:
                reasons.append('requirement_binding_mismatch')
            else:
                if case['lane'] not in {'craft', 'native_behavior', 'responsive', 'accessibility'}:
                    reasons.append('requirement_visual_review_missing')
                if not text(case.get('expected')) or case.get('asset_ids', []) != req.get('asset_ids', []):
                    reasons.append('requirement_asset_expectation_missing')
                if candidate.get('path') != selected.get('candidate_path') or candidate.get('target') != selected.get('target'):
                    reasons.append('intent_candidate_mismatch')
                for kind in ('design', 'brand'):
                    if not any(d['kind'] == kind and d['surface'] in {case['surface'], 'shared'} and
                               d['path'] == selected.get(kind + '_path') for d in deps.values()):
                        reasons.append('intent_' + kind + '_dependency_missing')
                linked = [captures.get(i) for i in case.get('capture_ids', [])]
                if (selected.get('target') or {}).get('state') not in {'draft', 'published'} or not linked or any(
                        c is None or c.get('kind') != 'native' for c in linked):
                    reasons.append('requirement_native_observation_missing')
                if not linked or any(c is None or any(c['context'].get(k) != context[k] for k in ('appearance', 'state'))
                                     or ('viewport' in context and c['context'].get('viewport') != context['viewport']) for c in linked):
                    reasons.append('requirement_capture_context_mismatch')
        if reasons:
            result['recorded_status'] = 'not_run'
            result['reasons'].extend(reason for reason in reasons if reason not in result['reasons'])
        result.update({k: case[k] for k in ('requirement_id', 'requirement_context', 'asset_ids') if k in case})
    report = []
    for req in state['requirements']:
        for surface in req['surfaces']:
            contexts = req['contexts'] if req['disposition'] == 'selected' else [{'id': None}]
            for context in contexts:
                if destination_coverage is not None and context.get('applicability') and not any(
                        a.get('surface', surface) == surface for a in context['applicability']):
                    continue
                matches = [r for r in results if r.get('requirement_id') == req['id'] and r['surface'] == surface
                           and r.get('requirement_context') == context['id']]
                fulfilled = good and matches and all(r['recorded_status'] == 'pass' for r in matches)
                observed = []
                if destination_coverage is not None:
                    observed = [o for o in destination_coverage['obligations'] if o['requirement_id'] == req['id']
                                and o['surface'] == surface and o['context_id'] == context['id']]
                    case_ids = {ident for o in observed for ident in o.get('case_ids', [])}
                    matches = [r for r in results if r['id'] in case_ids]
                    fulfilled = (good and destination_coverage['status'] == 'complete' and bool(observed) and
                                 all(o['status'] in {'pass', 'not_applicable'} for o in observed) and
                                 all(o.get('native_recorded') for o in observed if o['lane'] in
                                     {'craft', 'native_behavior', 'responsive', 'accessibility'} and o['status'] == 'pass'))
                status = 'explicitly_omitted' if req['disposition'] == 'explicitly_omitted' else (
                    'recorded_fulfilled' if fulfilled
                    else req['disposition'] if req['disposition'] in {'unresolved', 'deferred'} else 'not_assessed')
                row = {'requirement_id': req['id'], 'surface': surface, 'context_id': context['id'],
                       'required': req['required'], 'status': status, 'case_ids': [r['id'] for r in matches],
                       'purpose': req['purpose'], 'category': req['category'], 'origin': req['origin'],
                       'disposition': req['disposition'], 'decision_ref': req.get('decision_ref'),
                       'value': req.get('value'), 'asset_ids': req.get('asset_ids', []),
                       'selection': selection.get(surface),
                       'assets': [{**a, 'file': next((p for p in state['files'] if p['path'] == a.get('local_path')), None)}
                                  for a in state['assets'] if a['id'] in req.get('asset_ids', [])],
                       'observations': [{**{k: c.get(k) for k in ('id', 'expected', 'observation', 'method', 'reviewer',
                            'executed', 'evidence_paths', 'capture_ids')},
                            'recorded_status': indexed[c['id']]['recorded_status'],
                            'captures': [captures[i] for i in c.get('capture_ids', []) if i in captures]}
                            for c in spec.get('cases', []) if c['id'] in {r['id'] for r in matches}]}
                if destination_coverage is not None:
                    row['obligation_ids'] = [o['id'] for o in observed]
                    row['destination_status'] = ('recorded_complete' if observed and
                        all(o['status'] in {'pass', 'not_applicable'} for o in observed) else 'incomplete')
                report.append(row)
                if req['required'] and status not in {'recorded_fulfilled', 'explicitly_omitted'}:
                    gaps.append({'code': 'design_requirement_unfulfilled', **row})
    return {'status': 'incomplete' if gaps else 'recorded_complete', 'requirements': report, 'gaps': gaps,
            'intent': state['selected'], 'claims_authenticated': False}


def summary(root, design_report):
    state = check(root)
    coverage = design_report.get('intent_coverage', {}) if type(design_report) is dict else {}
    matching = state['selected'] and coverage.get('intent') == state['selected'] and state['status'] == 'consistent'
    return {'status': coverage.get('status', 'not_assessed') if matching else 'not_assessed',
            'selected': state['selected'],
            'integrity': state['status'], 'requirements': coverage.get('requirements', []) if matching else state['requirements'],
            'open_questions': state['open_questions'], 'findings': state['findings'],
            'gaps': coverage.get('gaps', []) if matching else [{'code': 'current_requirement_review_missing'}],
            'native_verification': 'not_assessed', 'business_acceptance': 'not_assessed',
            'publication_authorized': False, 'claims_authenticated': False}
