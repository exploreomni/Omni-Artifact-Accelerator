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
ROLES = {'branding', 'design-systems', 'app-designer', 'dashboard-designer', 'app-engineer', 'bi-engineer', 'qa-analyst'}


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


def starter(surfaces, branding='unknown', website=None):
    validate_surfaces(surfaces, {'app', 'dashboard'})
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
    if spec['branding'] == 'requested':
        covered = {s for req in requirements if req['category'] == 'logo' and req['required'] for s in req['surfaces']}
        need(covered == set(spec['surfaces']), 'required_logo_surfaces_missing')
    return spec


def references(spec):
    paths = set()
    for selection in spec['selections']:
        paths.update(selection[k] for k in ('design_path', 'brand_path', 'candidate_path') if selection.get(k))
    paths.update(a['local_path'] for a in spec['assets'] if a.get('local_path'))
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
    if project.get('design_intent'):
        previous = read_record(root, project['design_intent'])
        current = {r['id']: r for r in spec['requirements']}
        for req in previous['spec']['requirements']:
            if req['required']:
                replacement = current.get(req['id'], {})
                need(replacement.get('required') is True and set(req['surfaces']) <= set(replacement.get('surfaces', [])),
                     'required_requirement_removed_use_explicit_disposition')
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
    if spec['branding'] == 'requested' and not spec.get('website'):
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
    return list(dict.fromkeys(questions)), findings


def check(root):
    root, project = P.load_project(root)
    selected = project.get('design_intent')
    base = {'status': 'not_assessed', 'selected': selected, 'requirements': [], 'assets': [], 'selections': [],
            'branding': 'unknown', 'website': None, 'logo_sourcing': {}, 'open_questions': [], 'findings': [],
            'paths': [], 'files': [], 'stale_paths': [], 'publication_authorized': False, 'claims_authenticated': False}
    try:
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
            return base
        base.update({k: copy.deepcopy(spec.get(k)) for k in ('requirements', 'assets', 'selections', 'branding', 'website', 'logo_sourcing')})
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
    return base


def packet_context(root, role):
    if role not in ROLES:
        return {'paths': [], 'requirements': [], 'findings': [], 'open_questions': []}
    state = check(root)
    if state['status'] == 'inconsistent':
        details = []
        for finding in state['findings']:
            if finding['code'] in {'changed_or_missing_file', 'design_brand_reference_mismatch', 'invalid_current_selection'}:
                affected = finding.get('path') or finding.get('design_path') or finding.get('detail')
                details.append(finding['code'] + (': ' + str(affected) if affected else ''))
        need(False, 'stale_or_invalid_packet_selection; ' + '; '.join(details[:8]))
    paths = state['paths'] if role in ROLES else []
    if role in ROLES and not state['selected']:
        root, _ = P.load_project(root)
        for name in ('design', 'brand'):
            path = 'contracts/' + name + '.json'
            if (root / path).is_file():
                P.relative_file(root, path)
                paths.append(path)
    return {'paths': sorted(set(paths)), 'requirements': state['requirements'] if role in ROLES else [],
            'findings': state['findings'] if role in ROLES else [], 'open_questions': state['open_questions'] if role in ROLES else []}


def case_templates(root):
    state = check(root)
    need(state['status'] != 'inconsistent', 'stale_or_invalid_case_selection')
    templates = []
    for req in state['requirements']:
        if req['required'] and req['disposition'] == 'selected':
            for surface in req['surfaces']:
                for context in req['contexts']:
                    templates.append({'id': req['id'] + '/' + surface + '/' + context['id'], 'surface': surface,
                        'lane': 'craft', 'requirement_id': req['id'], 'requirement_context': context['id'],
                        'asset_ids': req.get('asset_ids', []), 'status': 'not_run', 'executed': False,
                        'expected': req['purpose'], 'capture_ids': [], 'evidence_paths': [],
                        'candidate_id': None, 'reviewed_dependencies': {},
                        'target': next(s['target'] for s in state['selections'] if s['surface'] == surface)})
    return {'intent': state['selected'], 'cases': templates, 'status': state['status'],
            'note': 'Draft templates; fill the actual candidate ID, dependency pins, reviewer and observed evidence.'}


def review_coverage(root, spec, results):
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
        if case['lane'] in VISUAL and not good:
            reasons.append('intent_selection_stale_or_changed')
        req_id = case.get('requirement_id')
        if req_id is not None:
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
                matches = [r for r in results if r.get('requirement_id') == req['id'] and r['surface'] == surface
                           and r.get('requirement_context') == context['id']]
                status = 'explicitly_omitted' if req['disposition'] == 'explicitly_omitted' else (
                    'recorded_fulfilled' if good and matches and all(r['recorded_status'] == 'pass' for r in matches)
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
