"""Offline startup, candidate preservation and delivery assessment. No host enforcement.

Records describe supplied evidence; hashes establish bytes, not truth or authority.
Uses the existing project, intent and review contracts. No network or dependencies.
"""
import copy
import importlib.util
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlsplit

_spec = importlib.util.spec_from_file_location('delivery_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
need = P.need
ID = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
RESPONSIBILITIES = {'experience', 'brand', 'semantics', 'engineering', 'verification',
                    'design_systems', 'storytelling'}
PRODUCT_RESPONSIBILITIES = {'product_intent', 'creative_review'}
ROLE_OWNERS = {'experience': {'app-designer', 'dashboard-designer'}, 'brand': {'branding'},
               'semantics': {'data-analyst', 'bi-engineer'}, 'engineering': {'app-engineer', 'bi-engineer'},
               'verification': {'qa-analyst'}, 'design_systems': {'design-systems', 'app-designer', 'dashboard-designer'},
               'storytelling': {'data-storyteller', 'data-analyst'},
               'product_intent': {'product-owner'},
               'creative_review': {'app-designer', 'dashboard-designer', 'design-systems'}}
LANES = {'source', 'synthetic', 'numerical', 'native', 'rendered', 'access', 'publication', 'human'}
IGNORED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache'}
QUALITY_POLICY = 'experience-evidence-v1'
PHASES = ('access', 'analysis', 'narrative', 'brief', 'options', 'choice', 'design', 'candidate', 'review', 'release')


def text(value):
    need(type(value) is str and bool(value.strip()) and len(value) <= 8192, 'bounded nonempty text required')


def identity(value):
    need(type(value) is str and ID.fullmatch(value), 'lowercase run/candidate ID required')
    return value


def pins(root, paths):
    need(type(paths) is list and bool(paths) and len(paths) <= 512 and
         all(type(p) is str for p in paths) and len(set(paths)) == len(paths), 'distinct input paths required')
    return {p: P.digest(P.relative_file(root, p).read_bytes()) for p in paths}


def current(root, bindings):
    need(type(bindings) is dict and bool(bindings), 'nonempty file bindings required')
    return pins(root, list(bindings)) == bindings


def capability_rows(value, requirement_ids, input_paths):
    """Task-oriented source evidence; no domain template or automatic scope decision."""
    need(type(value) is list and bool(value) and len(value) <= 128, 'source capabilities required')
    seen = set()
    for row in value:
        required = {'id', 'requirement_ids', 'question', 'source_refs', 'population', 'grain',
                    'available_depth', 'selected_depth', 'disposition', 'rationale', 'remaining_gap'}
        need(type(row) is dict and required <= set(row) and set(row) <= required | {'alternative_id'},
             'invalid source capability fields')
        ident = identity(row['id'])
        need(ident not in seen, 'duplicate source capability')
        seen.add(ident)
        for key in ('question', 'population', 'grain', 'rationale', 'remaining_gap'):
            text(row[key])
        for key in ('requirement_ids', 'source_refs', 'available_depth', 'selected_depth'):
            values = row[key]
            need(type(values) is list and len(values) <= 128 and all(type(v) is str for v in values)
                 and len(set(values)) == len(values), 'invalid source capability list')
            for item in values:
                text(item)
        need(bool(row['requirement_ids']) and set(row['requirement_ids']) <= requirement_ids,
             'source capability requirement unknown')
        need(bool(row['source_refs']) and all(v.split('#', 1)[0] in input_paths for v in row['source_refs']),
             'source capability references must name pinned inputs')
        need(row['disposition'] in {'selected', 'unsupported', 'deferred'}, 'invalid source capability disposition')
        need(set(row['selected_depth']) <= set(row['available_depth']), 'selected depth absent from available depth')
        need(bool(row['selected_depth']) == (row['disposition'] == 'selected'), 'selected depth requires selected disposition')
    by_id = {r['id']: r for r in value}
    for row in value:
        if 'alternative_id' in row:
            alternative = by_id.get(identity(row['alternative_id']))
            need(row['disposition'] != 'selected' and alternative is not None
                 and alternative['disposition'] == 'selected'
                 and set(row['requirement_ids']) <= set(alternative['requirement_ids']),
                 'alternative must be a selected capability covering the same requirements')


def inventory(root, request):
    """Retain qualification before the next destination selection, without selecting it."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'id', 'inputs', 'capabilities', 'scope_rationale'},
         'invalid source inventory request')
    ident = identity(request['id'])
    text(request['scope_rationale'])
    state = P.intent_helper().check(root)
    need(state['status'] != 'inconsistent', 'current intent required before inventory')
    bindings = pins(root, request['inputs'])
    capability_rows(request['capabilities'], {r['id'] for r in state['requirements']}, set(bindings))
    path = 'evidence/source-capabilities-' + ident + '.json'
    need(not (root / path).exists(), 'source inventory ID already recorded; use a new ID')
    record = {'schema_version': 1, 'kind': 'analyst_source_capabilities', 'project_id': project['id'],
              'intent_at_capture': state['selected'], 'input_pins': bindings,
              'capabilities': request['capabilities'], 'scope_rationale': request['scope_rationale'],
              'claims_authenticated': False}
    P.write_json(root / path, record)
    return {'status': 'recorded', 'path': path, 'sha256': P.digest((root / path).read_bytes()),
            'next': 'Reference this evidence in product.source_inventory_path before selecting the revised destination scope.',
            'scope_selected': False, 'publication_authorized': False}


def inventory_check(root, state):
    root, project = P.load_project(root)
    result = {'status': 'not_assessed', 'findings': [], 'path': None, 'capabilities': [],
              'claims_authenticated': False, 'scope_approved': False}
    if not state['selected']:
        return result
    try:
        need(state['status'] != 'inconsistent', 'source inventory selected context inconsistent')
        spec = P.intent_helper().read_record(root, state['selected'])['spec']
        path = spec.get('product', {}).get('source_inventory_path')
        if not path:
            return result
        result['path'] = path
        record, _ = P.read_json(P.relative_file(root, path))
        need(type(record) is dict and set(record) == {'schema_version', 'kind', 'project_id', 'intent_at_capture',
             'input_pins', 'capabilities', 'scope_rationale', 'claims_authenticated'}, 'invalid source inventory record')
        need(type(record['schema_version']) is int and record['schema_version'] == 1 and
             record['kind'] == 'analyst_source_capabilities' and record['project_id'] == project['id'],
             'wrong source inventory project/version')
        need(record['claims_authenticated'] is False, 'source inventory cannot authenticate claims')
        text(record['scope_rationale'])
        prior = record['intent_at_capture']
        if prior is not None:
            need(prior != state['selected'], 'source inventory must precede destination selection')
            need(prior in project.get('design_intent_history', []), 'source inventory capture intent not in history')
            P.intent_helper().read_record(root, prior)
        need(current(root, record['input_pins']), 'source inventory inputs changed')
        capability_rows(record['capabilities'], {r['id'] for r in state['requirements']}, set(record['input_pins']))
        result.update(status='consistent', capabilities=record['capabilities'])
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result['status'] = 'inconsistent'
        result['findings'].append(str(exc))
    return result


def project_delivery(root, request):
    """Generate an unselected intent proposal, copying explicit facts only."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'output', 'annotations'}, 'invalid delivery projection request')
    state = P.intent_helper().check(root)
    need(state['selected'] and state['status'] == 'consistent', 'current selected intent required')
    spec = copy.deepcopy(P.intent_helper().read_record(root, state['selected'])['spec'])
    need(inventory_check(root, state)['status'] != 'inconsistent', 'source inventory must be reconciled before projection')
    annotations = request['annotations']
    need(type(annotations) is dict and set(annotations) <= {r['id'] for r in spec['requirements']},
         'delivery annotation requirement unknown')
    provenance = {}
    for req in spec['requirements']:
        delivery = req.setdefault('delivery', {})
        supplied = copy.deepcopy(annotations.get(req['id'], {}))
        need(type(supplied) is dict, 'delivery annotation object required')
        take_value = supplied.pop('behavior_from_value', False)
        need(type(take_value) is bool, 'behavior_from_value must be boolean')
        need(not take_value or 'behavior' not in supplied, 'choose explicit behavior or value copy')
        if take_value:
            text(req.get('value'))
            supplied['behavior'] = req['value']
        sources = {'existing': sorted(delivery), 'explicit_annotations': sorted(supplied), 'derived': []}
        if take_value:
            sources['derived'].append('behavior from value by explicit request')
        if not delivery.get('source_ref') and req.get('decision_ref'):
            delivery['source_ref'] = req['decision_ref']
            sources['derived'].append('source_ref from decision_ref')
        for key, kind in (('destinations', 'destination'), ('journeys', 'journey')):
            if key not in delivery:
                delivery[key] = sorted({a['id'] for c in req.get('contexts', []) for a in c.get('applicability', [])
                                        if a['kind'] == kind})
                sources['derived'].append(key + ' from explicit context applicability')
        delivery.update(supplied)
        provenance[req['id']] = sources
    P.intent_helper().validate(spec, project)
    output = P.intent_helper().relative(request['output'])
    need(output.startswith('contracts/') and output.endswith('.json'), 'new contracts JSON output required')
    P.write_json(root / output, spec)
    projected = dict(state, requirements=spec['requirements'], selections=spec['selections'])
    return {'status': 'proposal', 'source_intent': state['selected'], 'path': output,
            'sha256': P.digest((root / output).read_bytes()), 'provenance': provenance,
            'coverage': P.experience_helper().inspect(root, projected, P),
            'selection_required': True, 'publication_authorized': False,
            'note': 'Reconcile this proposal against current intent before selecting a new version. Owners and behavior are never inferred from suggested roles or prose.'}


def evidence_template(root, request):
    """Generate honest unobserved defaults for exact candidate recording."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'candidate', 'output'}, 'invalid evidence template request')
    candidate, raw = P.read_json(P.relative_file(root, request['candidate']))
    need(candidate.get('kind') == 'analyst_candidate' and candidate.get('project_id') == project['id'], 'wrong candidate/project')
    state = P.intent_helper().check(root)
    need(state['status'] == 'consistent' and candidate['selected_intent'] == state['selected'],
         'current candidate selection required')
    history_check(root, project['id'], {'path': request['candidate'], 'sha256': P.digest(raw)})
    need(current(root, candidate['artifacts']) and current(root, candidate['context']), 'candidate changed before evidence template')
    output = P.intent_helper().relative(request['output'])
    need(output.startswith('evidence/') and output.endswith('.json'), 'new evidence JSON output required')
    evidence = {'candidate_sha256': P.digest(raw), 'lanes': {name: {'status': 'not_run', 'method': '',
        'observer': '', 'bindings': {}, 'reason': 'No observation recorded; supply actual method, observer and evidence.'}
        for name in sorted(LANES)}}
    P.write_json(root / output, evidence)
    return {'status': 'template', 'path': output, 'candidate_sha256': P.digest(raw),
            'design_requirement_review': P.design_completion(root), 'publication_authorized': False,
            'note': 'Source critique may be recorded in source. Requirement-by-context rendered review remains separate and is not populated from that critique.'}


def source_root():
    skill_parent = Path(__file__).resolve().parents[2]
    return skill_parent.parent if skill_parent.name == 'skills' and (skill_parent.parent / 'package.json').is_file() else skill_parent


def source_manifest(root):
    """Only package-owned product trees, never adjacent projects or installed skills."""
    root = P.no_links(root)
    repo = (root / 'package.json').is_file() and (root / 'skills').is_dir()
    names = ['omni-artifact-accelerator', *('omni-' + role for role in P.ROLES)]
    trees = ([root / n for n in ('skills', 'scripts', 'tests', 'docs', 'integrations', 'harness', '.github')]
             if repo else [root / n for n in names])
    candidates = [root / n for n in ('README.md', 'AGENTS.md', 'CLAUDE.md', 'package.json')]
    for tree in trees:
        if tree.exists():
            P.no_links(tree)
            candidates.extend(p for p in tree.rglob('*') if not any(part in IGNORED for part in p.relative_to(root).parts))
    result, total = {}, 0
    for path in sorted(set(candidates)):
        need(not path.is_symlink(), 'package source contains a symlink')
        if not path.is_file():
            continue
        P.no_links(path)
        need(path.stat().st_size <= P.MAX_BYTES, 'package source file exceeds bound')
        raw = path.read_bytes()
        total += len(raw)
        need(total <= 64 * 1024 * 1024 and len(result) < 4000, 'package snapshot exceeds bound')
        result[path.relative_to(root).as_posix()] = P.digest(raw)
    need(bool(result), 'package source unavailable')
    return result


def git_identity(package):
    result = {'head': None, 'status': None}
    for key, args in (('head', ['rev-parse', 'HEAD']), ('status', ['status', '--porcelain'])):
        try:
            r = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(package), *args],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                result[key] = r.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return result


def verify_source(root, request):
    """Explicit read-only remote check; never fetch, install, reset or activate."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'id'}, 'source-check requires only id')
    path = 'evidence/source-check-' + identity(request['id']) + '.json'
    need(not (root / path).exists(), 'source check ID already exists')
    package = source_root()
    base = ['git', '-c', 'core.fsmonitor=false', '-c', 'protocol.file.allow=never',
            '-c', 'protocol.ext.allow=never', '-c', 'http.followRedirects=false', '-C', str(package)]
    try:
        remote = subprocess.run([*base, 'remote', 'get-url', 'origin'], capture_output=True,
                                text=True, timeout=10)
        need(remote.returncode == 0, 'configured origin unavailable')
        url = remote.stdout.strip()
        parsed = urlsplit(url)
        need(parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
             and not parsed.query and not parsed.fragment, 'source check needs an HTTPS origin without credentials')
        result = subprocess.run([*base, 'ls-remote', '--exit-code', 'origin', 'refs/heads/main'],
                                capture_output=True, text=True, timeout=20)
        lines = result.stdout.strip().splitlines()
        need(result.returncode == 0 and len(lines) == 1, 'remote main could not be verified')
        parts = lines[0].split()
        need(len(parts) == 2 and parts[1] == 'refs/heads/main' and
             re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', parts[0]), 'invalid remote revision response')
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError('remote main could not be verified; current checkout remains unchanged') from None
    record = {'schema_version': 1, 'kind': 'analyst_source_check', 'project_id': project['id'],
              'package_root': str(package), 'remote': url, 'ref': 'refs/heads/main', 'revision': parts[0],
              'checked_at': datetime.now(timezone.utc).isoformat(), 'git': git_identity(package),
              'claims_authenticated': False, 'source_changed': False}
    P.write_json(root / path, record)
    return {'status': 'recorded', 'path': path, 'revision': parts[0],
            'checkout_matches': record['git']['head'] == parts[0] and record['git']['status'] == '',
            'source_changed': False, 'claims_authenticated': False}


def source_expectation(root, request, git, package):
    expectation = request.get('source_expectation', {'kind': 'current_checkout'})
    need(type(expectation) is dict and expectation.get('kind') in
         {'current_checkout', 'pinned_revision', 'latest_main'}, 'invalid source expectation')
    kind = expectation['kind']
    expected = {'kind'} if kind == 'current_checkout' else {'kind', 'revision'}
    if kind == 'latest_main':
        expected.add('verification_path')
    need(set(expectation) == expected, 'source expectation fields differ')
    bindings = {}
    if kind != 'current_checkout':
        revision = expectation['revision']
        need(type(revision) is str and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision), 'exact revision required')
        need(git['head'] == revision and git['status'] == '', 'requested source revision does not match clean working checkout')
    if kind == 'latest_main':
        path = expectation['verification_path']
        receipt, _ = P.read_json(P.relative_file(root, path))
        need(receipt.get('kind') == 'analyst_source_check' and receipt.get('project_id') == P.load_project(root)[1]['id']
             and receipt.get('revision') == revision and receipt.get('package_root') == str(package)
             and receipt.get('ref') == 'refs/heads/main', 'source verification does not match run')
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(receipt['checked_at'])).total_seconds()
        except (ValueError, TypeError, KeyError):
            raise ValueError('source verification time invalid') from None
        need(0 <= age <= 600, 'latest-main check must be refreshed within ten minutes before startup')
        bindings = pins(root, [path])
    return expectation, bindings


def start(root, request):
    root, project = P.load_project(root)
    required = {'id', 'source_mode', 'host', 'entrypoint', 'brief', 'loaded_guidance'}
    need(type(request) is dict and required <= set(request) and
         set(request) <= required | {'execution', 'source_expectation', 'adopt_quality_policy'},
         'invalid run-start fields')
    if 'adopt_quality_policy' in request:
        need(request['adopt_quality_policy'] is True, 'explicit quality policy adoption required')
        need('workflow_quality_policy' not in project, 'quality policy adoption applies only to historical engagements')
    quality = project.get('workflow_quality_policy') == QUALITY_POLICY or request.get('adopt_quality_policy') is True
    if quality:
        need('execution' in request, 'quality startup requires an execution contract path')
        P.read_json(P.relative_file(root, request['execution']))
    ident = identity(request['id'])
    path = 'evidence/run-' + ident + '.json'
    need(not (root / path).exists(), 'run ID already recorded; use a new ID')
    need(request['source_mode'] in {'repository_only', 'installed', 'connected_reference'}, 'invalid source mode')
    host = request['host']
    need(type(host) is dict and set(host) == {'name', 'execution_mode', 'tools', 'constraints'}, 'invalid host fields')
    for key in ('name', 'execution_mode'):
        text(host[key])
    need(host['execution_mode'] in {'inline', 'delegated', 'instruction_guided'}, 'invalid host execution mode')
    for key in ('tools', 'constraints'):
        need(type(host[key]) is list and len(host[key]) <= 128, 'host list required')
        for value in host[key]:
            text(value)
    text(request['entrypoint'])
    package = source_root()
    manifest = source_manifest(package)
    loaded = request['loaded_guidance']
    need(type(loaded) is list and loaded and all(type(p) is str and p in manifest for p in loaded)
         and len(set(loaded)) == len(loaded), 'loaded guidance must name package files actually read')
    prefix = 'skills/' if 'skills/omni-artifact-accelerator/SKILL.md' in manifest else ''
    need(prefix + 'omni-artifact-accelerator/SKILL.md' in loaded, 'orchestrator entrypoint must be read')
    if request['source_mode'] == 'repository_only':
        need(prefix == 'skills/', 'repository-only execution requires a source checkout')
    if request['source_mode'] == 'installed':
        need(prefix == '', 'installed mode must use the installed helper')
    git = git_identity(package) if prefix else {'head': None, 'status': None}
    expectation, source_pins = source_expectation(root, request, git, package)
    events = P.read_json(root / 'stage-gates.json')[0]['events'] if (root / 'stage-gates.json').exists() else []
    work_events = [e for e in events if e.get('stage') != 'selection_policy']
    previous = project.get('execution_start')
    if previous:
        # Check the retained chain without comparing old package bytes to the new
        # checkout: a legitimate upgrade is allowed, laundering late startup is not.
        visited, pointer = set(), previous
        while pointer is not None:
            need(type(pointer) is dict and set(pointer) == {'path', 'sha256'} and
                 pointer['path'] not in visited and len(visited) < 64, 'invalid prior startup chain')
            prior, prior_raw = P.read_json(P.relative_file(root, pointer['path']))
            need(P.digest(prior_raw) == pointer['sha256'] and prior.get('project_id') == project['id'] and
                 prior.get('kind') == 'analyst_execution_start', 'prior startup changed')
            need(prior.get('startup_timing') in {'before_access', 'resumed'}, 'late startup cannot be converted to a resume')
            visited.add(pointer['path'])
            pointer = prior.get('previous_start')
    timing = ('before_access' if not work_events else 'resumed' if previous or request.get('adopt_quality_policy') else 'late')
    brief_pins = pins(root, [request['brief']])
    brief_raw = P.relative_file(root, request['brief']).read_bytes()
    need(P.digest(brief_raw) == brief_pins[request['brief']], 'brief changed during capture')
    retained = 'evidence/brief-' + ident + '.txt'
    P.private_write(root / retained, brief_raw)
    record = {'schema_version': 1, 'kind': 'analyst_execution_start', 'project_id': project['id'],
              **request, 'package_root': str(package), 'package_files': manifest, 'git': git,
              'loaded_guidance_pins': {p: manifest[p] for p in loaded}, 'brief_pins': brief_pins, 'brief_retained': retained,
              'source_expectation': expectation, 'source_verification_pins': source_pins,
              'execution_path': request.get('execution'), 'startup_timing': timing,
              'stage_tail_at_start': events[-1]['sha256'] if events else None,
              'previous_start': previous,
              'claims_authenticated': False, 'agents_dispatched': False,
              'host_qualification': 'unobserved', 'publication_authorized': False}
    P.write_json(root / path, record)
    if quality:
        project['workflow_quality_policy'] = QUALITY_POLICY
        project['execution_start'] = {'path': path, 'sha256': P.digest((root / path).read_bytes())}
        project['execution_guidance'] = []
        P.write_json(root / 'project.json', project, replace=True)
    return {'status': 'recorded', 'path': path, 'agents_dispatched': False, 'claims_authenticated': False}


def active_run(root, project):
    pointer = project.get('execution_start')
    need(type(pointer) is dict and set(pointer) == {'path', 'sha256'}, 'workflow_startup_missing')
    run, raw = P.read_json(P.relative_file(root, pointer['path']))
    need(P.digest(raw) == pointer['sha256'] and run.get('project_id') == project['id']
         and run.get('kind') == 'analyst_execution_start', 'workflow_startup_changed')
    need(run.get('startup_timing') != 'late', 'workflow_startup_recorded_late')
    need(str(source_root()) == run['package_root'] and source_manifest(source_root()) == run['package_files'],
         'package_changed_since_start')
    need(current(root, run['brief_pins']) and P.digest(P.relative_file(root, run['brief_retained']).read_bytes()) ==
         run['brief_pins'][run['brief']], 'original_request_changed')
    if run.get('source_verification_pins'):
        need(current(root, run['source_verification_pins']), 'source_verification_changed')
    return run, pointer


def guidance_state(root, project, run, pointer):
    loaded = dict(run['loaded_guidance_pins'])
    paths = [pointer['path']]
    previous = pointer
    chain = project.get('execution_guidance', [])
    need(type(chain) is list and len(chain) <= 64, 'invalid guidance chain')
    for receipt in chain:
        need(type(receipt) is dict and set(receipt) == {'path', 'sha256'}, 'invalid guidance pointer')
        value, raw = P.read_json(P.relative_file(root, receipt['path']))
        need(P.digest(raw) == receipt['sha256'] and value.get('kind') == 'analyst_guidance_read'
             and value.get('run') == pointer and value.get('previous') == previous,
             'guidance receipt changed or reordered')
        additions = value.get('loaded_guidance_pins')
        need(type(additions) is dict and additions and all(run['package_files'].get(p) == h for p, h in additions.items()),
             'guidance source differs')
        loaded.update(additions)
        paths.append(receipt['path'])
        previous = receipt
    return loaded, paths


def record_guidance(root, request):
    """Append reported reads; neither file hashes nor this record prove comprehension."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'id', 'loaded_guidance'}, 'invalid run-guidance request')
    run, pointer = active_run(root, project)
    guidance_state(root, project, run, pointer)
    items = request['loaded_guidance']
    need(type(items) is list and items and len(items) == len(set(items)) and
         all(type(p) is str and p in run['package_files'] for p in items), 'guidance must name actual package files read')
    path = 'evidence/guidance-' + identity(request['id']) + '.json'
    chain = project.get('execution_guidance', [])
    P.write_json(root / path, {'schema_version': 1, 'kind': 'analyst_guidance_read', 'run': pointer,
        'previous': chain[-1] if chain else pointer,
        'loaded_guidance_pins': {p: run['package_files'][p] for p in items}, 'claims_authenticated': False})
    project['execution_guidance'] = [*chain, {'path': path, 'sha256': P.digest((root / path).read_bytes())}]
    P.write_json(root / 'project.json', project, replace=True)
    return {'status': 'recorded', 'path': path, 'claims_authenticated': False}


def phase_snapshot(root):
    """One read snapshot for a single journal inspection, never a persisted cache.

    Mutation entrypoints still call require_phase afresh. Callers must not retain
    this value between inspections or use it to authorize a later write.
    """
    root, project = P.load_project(root)
    run, pointer = active_run(root, project)
    loaded, paths = guidance_state(root, project, run, pointer)
    execution, _ = P.read_json(P.relative_file(root, run.get('execution_path')))
    return {'root': root, 'run': run, 'pointer': pointer, 'loaded': loaded, 'paths': paths,
            'execution': execution, 'state': P.intent_helper().check(root)}


def phase_check(root, action, _snapshot=None):
    """Phase-local structural check; deliberately never calls stage-status/run-check."""
    root, project = P.load_project(root)
    action = {'choose': 'choice', 'build': 'candidate'}.get(action, action)
    need(action in {*PHASES, 'selection_policy'}, 'unknown execution phase')
    result = {'status': 'not_assessed', 'findings': [], 'context': {}, 'paths': [],
              'claims_authenticated': False, 'publication_authorized': False}
    if project.get('workflow_quality_policy') != QUALITY_POLICY or action == 'selection_policy':
        return result
    findings = result['findings']
    try:
        snapshot = phase_snapshot(root) if _snapshot is None else _snapshot
        need(snapshot['root'] == root, 'phase_snapshot_project_differs')
        run, pointer = snapshot['run'], snapshot['pointer']
        loaded, paths = snapshot['loaded'], list(snapshot['paths'])
        execution_path = run.get('execution_path')
        execution = snapshot['execution']
        need(type(execution) is dict and 'responsibilities' in execution and
             set(execution) <= {'responsibilities', 'request_review', 'specialists'}, 'invalid execution contract')
        owners = execution['responsibilities']
        need(type(owners) is dict and set(owners) <= RESPONSIBILITIES | PRODUCT_RESPONSIBILITIES,
             'invalid responsibility inventory')
        phase = PHASES.index(action)
        required = {'semantics'}
        if phase >= PHASES.index('narrative'):
            required.add('storytelling')
        if phase >= PHASES.index('brief'):
            required.update({'product_intent', 'experience', 'brand'})
        if phase >= PHASES.index('options'):
            required.update({'design_systems', 'creative_review', 'verification'})
        if phase >= PHASES.index('candidate'):
            required.add('engineering')
        used = {}
        prefix = 'skills/' if 'skills/omni-artifact-accelerator/SKILL.md' in run['package_files'] else ''
        guidance = {prefix + 'omni-artifact-accelerator/SKILL.md'}
        for name in sorted(required):
            value = owners.get(name)
            if value is None:
                findings.append('responsibility_missing:' + name)
                continue
            need(type(value) is dict and set(value) == {'role', 'worker', 'mode', 'rationale'}
                 and value['role'] in ROLE_OWNERS[name] and
                 value['mode'] in {'inline', 'delegated', 'not_required'}, 'invalid responsibility:' + name)
            text(value['rationale'])
            if value['mode'] == 'not_required':
                findings.append('required_responsibility_omitted:' + name)
            else:
                text(value['worker'])
            used[name] = value
            guidance.add(prefix + 'omni-' + value['role'] + '/SKILL.md')
        if phase >= PHASES.index('analysis'):
            guidance.update(prefix + 'omni-' + r + '/SKILL.md' for r in ('data-analyst', 'bi-engineer'))
        if phase >= PHASES.index('brief'):
            guidance.add(prefix + 'omni-product-owner/references/visual-experience-discovery.md')
        if phase >= PHASES.index('options'):
            guidance.update(prefix + 'omni-design-systems/references/' + p + '.md'
                            for p in ('experience-brief', 'visual-craft', 'experience-curriculum', 'ideation-playbook'))
            guidance.add(prefix + 'omni-design-systems/SKILL.md')
            creative = owners.get('creative_review', {}).get('worker')
            if creative and creative in {owners.get('experience', {}).get('worker'), owners.get('engineering', {}).get('worker')}:
                findings.append('independent_creative_review_not_assigned')
        if phase >= PHASES.index('candidate'):
            if owners.get('verification', {}).get('worker') == owners.get('engineering', {}).get('worker'):
                findings.append('independent_verification_not_assigned')
        # Read draft/selected requirements without stage-status recursion. A later
        # specialization cannot be erased by the generic stage role projection.
        state = snapshot['state']
        if phase >= PHASES.index('brief') and state.get('data_refresh_context') is not None:
            guidance.add(prefix + 'omni-product-owner/references/data-refresh-policy.md')
        if phase >= PHASES.index('brief') and state.get('status') == 'inconsistent':
            findings.append('selected_intent_inconsistent')
        active = [r for r in state.get('requirements', []) if r.get('disposition') not in {'deferred', 'explicitly_omitted'}]
        capabilities = set(c for r in active for c in r.get('delivery', {}).get('capabilities', []))
        specialist_records = {}
        if phase >= PHASES.index('options'):
            conditional = {'motion': 'motion-designer', 'spatial-modeling': '3d-modeler'}
            specialists = execution.get('specialists', {})
            need(type(specialists) is dict, 'invalid specialist inventory')
            for capability, role in conditional.items():
                ids = {r['id'] for r in active if capability in r.get('delivery', {}).get('capabilities', [])}
                # Canonical discovery choices already carry an obligation; a
                # missing later delivery annotation must not erase it.
                for row in active:
                    value = row.get('value')
                    if type(value) is dict and (
                        capability == 'motion' and value.get('quality') == 'motion' and value.get('usage') == 'included'
                        or capability == 'spatial-modeling' and value.get('treatment') == 'interactive_3d'
                    ):
                        ids.add(row['id'])
                if not ids:
                    continue
                matches = {k: v for k, v in specialists.items() if type(v) is dict and v.get('role') == role
                           and v.get('mode') in {'inline', 'delegated'}}
                covered = set()
                for key, value in matches.items():
                    need(set(value) == {'role', 'worker', 'mode', 'rationale', 'requirement_ids'}, 'invalid specialist assignment')
                    text(value['worker']); text(value['rationale'])
                    need(type(value['requirement_ids']) is list and all(type(v) is str for v in value['requirement_ids']),
                         'invalid specialist requirement IDs')
                    covered.update(value['requirement_ids'])
                    specialist_records[key] = value
                if not ids <= covered:
                    findings.append('specialist_scope_missing:' + role)
                guidance.add(prefix + 'omni-' + role + '/SKILL.md')
            if 'custom-visualization' in capabilities:
                guidance.add(prefix + 'omni-app-engineer/references/advanced-visualization.md')
        for name in sorted(guidance - loaded.keys()):
            findings.append('guidance_not_recorded:' + name)
        context = {'run': pointer, 'package_sha256': P.digest(P.canonical(run['package_files'])),
                   'responsibilities': used, 'specialists': specialist_records,
                   'guidance': {p: loaded[p] for p in sorted(guidance & loaded.keys())}}
        paths.extend([execution_path, run['brief_retained'], *run['brief_pins'], *run.get('source_verification_pins', {})])
        if phase >= PHASES.index('candidate'):
            review = execution.get('request_review')
            need(type(review) is dict and set(review) == {'reviewer', 'brief_sha256', 'requirement_ids', 'evidence_path'},
                 'original_request_review_missing')
            need(type(review['requirement_ids']) is list and len(review['requirement_ids']) == len(set(review['requirement_ids'])),
                 'invalid original request review scope')
            if set(review['requirement_ids']) != {r['id'] for r in state.get('requirements', [])}:
                findings.append('original_request_review_scope_differs')
            if review['reviewer'] != owners.get('verification', {}).get('worker'):
                findings.append('original_request_review_not_independent')
            if review['brief_sha256'] != run['brief_pins'][run['brief']]:
                findings.append('original_request_review_stale')
            context['request_review'] = dict(review, evidence_sha256=pins(root, [review['evidence_path']])[review['evidence_path']])
            paths.append(review['evidence_path'])
        result.update(context=context, paths=sorted(set(paths)))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        findings.append(str(exc))
    result['status'] = 'blocked' if findings else 'ready'
    return result


def require_phase(root, action):
    result = phase_check(root, action)
    need(result['status'] != 'blocked', 'execution_phase_blocked:' + ';'.join(result['findings']))
    return result


def requalify_context(root, previous_context, action):
    """Re-derive an A–E context after an explicit startup; never carry F passes.

    The journal owns evidence, choice and ordering validation. This helper only
    checks the immutable startup lineage and unchanged phase responsibilities.
    """
    need(action in PHASES[:PHASES.index('candidate')], 'requalification_applies_only_to_A_E')
    root, project = P.load_project(root)
    check = require_phase(root, action)
    need(check['status'] == 'ready', 'requalification_requires_quality_policy')
    now = check['context']
    need(type(previous_context) is dict and set(previous_context) == set(now), 'requalification_context_fields_differ')
    old_pointer = previous_context.get('run')
    need(old_pointer != now['run'], 'requalification_requires_new_startup')
    run, pointer = active_run(root, project)
    brief_pins = run['brief_pins']
    visited, found = set(), None
    while pointer is not None:
        need(type(pointer) is dict and set(pointer) == {'path', 'sha256'} and
             pointer['path'] not in visited and len(visited) < 64, 'invalid_requalification_startup_chain')
        record, raw = P.read_json(P.relative_file(root, pointer['path']))
        need(P.digest(raw) == pointer['sha256'] and record.get('kind') == 'analyst_execution_start' and
             record.get('project_id') == project['id'] and record.get('startup_timing') in {'before_access', 'resumed'},
             'requalification_startup_changed')
        need(record['brief_pins'] == brief_pins and
             P.digest(P.relative_file(root, record['brief_retained']).read_bytes()) == brief_pins[record['brief']],
             'requalification_original_request_changed')
        visited.add(pointer['path'])
        if pointer == old_pointer:
            found = record
            break
        pointer = record.get('previous_start')
    need(found is not None, 'requalification_prior_startup_not_in_chain')
    need(previous_context['package_sha256'] == P.digest(P.canonical(found['package_files'])),
         'requalification_prior_package_differs')
    old_guidance = previous_context['guidance']
    need(type(old_guidance) is dict and all(found['package_files'].get(p) == h for p, h in old_guidance.items()),
         'requalification_prior_guidance_differs')
    # Required guidance may change with the package. Owners and selected
    # specialist scope must not silently change while preserving old choices.
    for name in set(now) - {'run', 'package_sha256', 'guidance'}:
        need(now[name] == previous_context[name], 'requalification_' + name + '_changed')
    return now


def inspect_run(root, request):
    """Check structural readiness; provisional discovery/authoring remain possible."""
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'run', 'execution'}, 'run and execution paths required')
    run, _ = P.read_json(P.relative_file(root, request['run']))
    execution, _ = P.read_json(P.relative_file(root, request['execution']))
    need(run.get('kind') == 'analyst_execution_start' and run.get('project_id') == project['id'], 'wrong run/project')
    need(type(execution) is dict and {'responsibilities', 'request_review'} <= set(execution)
         and set(execution) <= {'responsibilities', 'request_review', 'specialists'}, 'invalid execution contract')
    findings = []
    loaded_guidance = run['loaded_guidance_pins']
    if project.get('workflow_quality_policy') == QUALITY_POLICY:
        phase = phase_check(root, 'candidate')
        findings.extend(phase['findings'])
        if project.get('execution_start', {}).get('path') != request['run'] or run.get('execution_path') != request['execution']:
            findings.append('assessment_startup_differs')
        else:
            try:
                loaded_guidance, _ = guidance_state(root, project, run, project['execution_start'])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                findings.append(str(exc))
    need(P.digest(P.relative_file(root, run['brief_retained']).read_bytes()) == run['brief_pins'][run['brief']],
         'retained original request changed')
    if not current(root, run['brief_pins']):
        findings.append('original_request_changed')
    if source_manifest(source_root()) != run['package_files'] or str(source_root()) != run['package_root']:
        findings.append('package_changed_since_start')
    responsibilities = execution['responsibilities']
    need(type(responsibilities) is dict and RESPONSIBILITIES <= set(responsibilities)
         and set(responsibilities) <= RESPONSIBILITIES | PRODUCT_RESPONSIBILITIES, 'named responsibilities required')
    for name, value in responsibilities.items():
        need(type(value) is dict and set(value) == {'role', 'worker', 'mode', 'rationale'}, 'invalid responsibility')
        need(value['role'] in ROLE_OWNERS[name], 'role does not own this responsibility')
        need(value['mode'] in {'inline', 'delegated', 'not_required'}, 'invalid responsibility mode')
        text(value['rationale'])
        if value['mode'] == 'not_required':
            need(name in {'design_systems', 'storytelling'}, 'core responsibility cannot be omitted')
        else:
            text(value['worker'])
            prefix = 'skills/' if 'skills/omni-artifact-accelerator/SKILL.md' in run['package_files'] else ''
            if prefix + 'omni-' + value['role'] + '/SKILL.md' not in loaded_guidance:
                findings.append('role_guidance_not_recorded:' + value['role'])
    if responsibilities['verification']['worker'] == responsibilities['engineering']['worker']:
        findings.append('independent_verification_not_assigned')
    state = P.intent_helper().check(root)
    specialists = execution.get('specialists', {})
    need(type(specialists) is dict and len(specialists) <= 32, 'invalid optional specialists')
    for ident, value in specialists.items():
        identity(ident)
        need(type(value) is dict and set(value) == {'role', 'worker', 'mode', 'rationale', 'requirement_ids'},
             'invalid specialist assignment')
        need(value['role'] in P.ROLES and value['mode'] in {'inline', 'delegated', 'not_required'},
             'unknown specialist role or mode')
        text(value['rationale'])
        ids = value['requirement_ids']
        need(type(ids) is list and ids and all(type(v) is str for v in ids) and len(set(ids)) == len(ids)
             and set(ids) <= {r['id'] for r in state['requirements']}, 'specialist requirement scope invalid')
        if value['mode'] != 'not_required':
            text(value['worker'])
            prefix = 'skills/' if 'skills/omni-artifact-accelerator/SKILL.md' in run['package_files'] else ''
            if prefix + 'omni-' + value['role'] + '/SKILL.md' not in loaded_guidance:
                findings.append('role_guidance_not_recorded:' + value['role'])
    product = P.routing_helper('product_intent').check(root)
    source_inventory = inventory_check(root, state)
    if source_inventory['status'] == 'inconsistent':
        findings.append('source_capability_inventory_not_current')
    active_ids = {r['id'] for r in state['requirements'] if r['disposition'] not in {'explicitly_omitted', 'deferred'}
                  and (r['required'] or r['disposition'] == 'selected')}
    for capability in source_inventory['capabilities']:
        if (capability['disposition'] != 'selected' and not capability.get('alternative_id')
                and active_ids.intersection(capability['requirement_ids'])):
            findings.append('source_capability_' + capability['disposition'] + ':' + capability['id'])
    if product['status'] == 'inconsistent':
        findings.append('product_context_not_current')
    if product['discovery'] == 'material_questions_open':
        findings.append('product_material_questions_open')
    if product['enabled'] and product['scope'] != 'focused_repair':
        if source_inventory['status'] == 'not_assessed':
            findings.append('source_capability_inventory_missing')
        for name in PRODUCT_RESPONSIBILITIES - set(responsibilities):
            findings.append('product_responsibility_missing:' + name)
        creative = responsibilities.get('creative_review', {})
        if creative.get('worker') in {responsibilities['experience']['worker'], responsibilities['engineering']['worker']}:
            findings.append('independent_creative_review_not_assigned')
    coverage = P.experience_check(root)
    if coverage['status'] != 'ready_for_review':
        findings.append('declared_delivery_' + coverage['status'])
    if ('data-storyteller' in coverage['role_requirements'] and
            responsibilities['storytelling']['mode'] == 'not_required'):
        findings.append('required_storytelling_unassigned')
    review = execution['request_review']
    need(type(review) is dict and set(review) == {'reviewer', 'brief_sha256', 'requirement_ids', 'evidence_path'},
         'invalid original-request review')
    text(review['reviewer'])
    if review['reviewer'] != responsibilities['verification']['worker']:
        findings.append('original_request_review_not_independent')
    need(type(review['requirement_ids']) is list and all(type(v) is str for v in review['requirement_ids']), 'invalid requirement IDs')
    if (set(review['requirement_ids']) != {r['id'] for r in state['requirements']}
            or len(review['requirement_ids']) != len(set(review['requirement_ids']))):
        findings.append('original_request_review_scope_differs')
    if review['brief_sha256'] != run['brief_pins'][run['brief']]:
        findings.append('original_request_review_stale')
    try:
        P.relative_file(root, review['evidence_path'])
    except (ValueError, OSError):
        findings.append('original_request_review_missing')
    gates = P.stage_status(root)
    if gates['required']:
        if responsibilities['storytelling']['mode'] == 'not_required':
            findings.append('stage_gate_storytelling_required')
        try:
            P.stage_require(root, 'build')
        except ValueError as exc:
            findings.append(str(exc))
    return {'status': 'incomplete' if findings else 'ready_for_review', 'findings': findings,
            'stage_gates': gates,
            'coverage': coverage, 'selected_intent': state['selected'], 'responsibilities': responsibilities,
            'product_context': product, 'source_inventory': source_inventory, 'specialists': specialists,
            'claims_authenticated': False, 'agents_dispatched': False, 'publication_authorized': False,
            'limitation': 'Declared ownership and supplied review only; does not discover omitted requirements or prove dispatch.'}


def history_check(root, project_id, pointer):
    """Verify the declared chain's records and retained bytes, not historical working files."""
    first, _ = P.read_json(P.relative_file(root, 'evidence/candidate-history/first.json'))
    visited, final = set(), None
    while pointer is not None:
        need(type(pointer) is dict and set(pointer) == {'path', 'sha256'}, 'invalid history pointer')
        need(pointer['path'] not in visited and len(visited) < 512, 'cyclic or oversized candidate history')
        visited.add(pointer['path'])
        record, raw = P.read_json(P.relative_file(root, pointer['path']))
        need(P.digest(raw) == pointer['sha256'], 'candidate history record changed')
        need(record.get('kind') == 'analyst_candidate' and record.get('project_id') == project_id,
             'candidate history belongs to another project')
        need(pointer['path'] == 'evidence/candidate-history/' + identity(record['id']) + '/candidate.json',
             'candidate history path differs')
        need(type(record['retained']) is dict and set(record['retained']) == set(record['artifacts'])
             and bool(record['artifacts']), 'retained artifact inventory differs')
        for original, saved in record['retained'].items():
            need(P.digest(P.relative_file(root, saved).read_bytes()) == record['artifacts'][original], 'retained historical bytes changed')
        final, pointer = pointer, record.get('previous')
    need(final == first, 'candidate history does not reach the preserved first candidate')
    return len(visited)


def freeze(root, request):
    root, project = P.load_project(root)
    need(type(request) is dict and {'id', 'artifacts', 'context'} <= set(request)
         and set(request) <= {'id', 'artifacts', 'context', 'builders', 'supporting_artifacts'}, 'invalid candidate request')
    gates = P.stage_require(root, 'build')
    if gates['required']:
        builders = request.get('builders')
        need(type(builders) is list and builders and len(builders) <= 16 and
             all(type(b) is str and b.strip() and len(b) <= 256 and
                 all(ord(c) >= 32 and ord(c) != 127 for c in b) for b in builders)
             and len(set(builders)) == len(builders), 'stage_gate_candidate_builders_required')
    ident = identity(request['id'])
    artifacts = pins(root, request['artifacts'])
    readiness = require_phase(root, 'candidate')
    context = pins(root, sorted(set([*request['context'], *readiness['paths']])))
    state = P.intent_helper().check(root)
    supporting = request.get('supporting_artifacts', [])
    need(type(supporting) is list and all(type(p) is str for p in supporting) and
         len(supporting) == len(set(supporting)) and set(supporting) < set(artifacts),
         'supporting_artifacts_must_be_a_distinct_proper_subset')
    selected_paths = {s['candidate_path'] for s in state['selections'] if s.get('candidate_path')}
    need(not selected_paths.intersection(supporting), 'selected_candidate_cannot_be_supporting_artifact')
    artifact_roles = {p: 'supporting' if p in supporting else 'primary' for p in artifacts}
    if project.get('workflow_quality_policy') == QUALITY_POLICY and selected_paths:
        need(set(artifacts) - set(supporting) == selected_paths,
             'candidate_primary_artifacts_must_match_selected_surfaces')
    # The first assembly can precede binding its actual bytes into selected
    # intent. It stays a provisional candidate: assess rejects missing selected
    # artifact coverage and native create independently requires that binding.
    if state['selected']:
        context.update(pins(root, state['paths']))
    directory = P.no_links(root / 'evidence' / 'candidate-history')
    directory.mkdir(mode=0o700, exist_ok=True)
    first, head = directory / 'first.json', directory / 'head.json'
    if gates['required']:
        need(not any(directory.glob('*/candidate.json')) or (first.is_file() and head.is_file()),
             'stage_gate_history_reconciliation_required')
        if gates.get('candidate') is not None and head.is_file():
            latest = P.read_json(head)[0]
            expected = 'evidence/candidate-history/' + gates['candidate']['iteration_id'] + '/candidate.json'
            need(latest.get('path') == expected, 'stage_gate_history_reconciliation_required')
    previous = P.read_json(head)[0] if head.exists() else P.read_json(first)[0] if first.exists() else None
    if previous is not None:
        history_check(root, project['id'], previous)
    need(sum(P.relative_file(root, p).stat().st_size for p in artifacts) <= 64 * 1024 * 1024,
         'candidate snapshot exceeds 64 MiB')
    path = P.no_links(directory / ident)
    need(not path.exists(), 'candidate ID already recorded; create a revision')
    path.mkdir(mode=0o700)
    retained = {}
    for i, name in enumerate(artifacts):
        raw = P.relative_file(root, name).read_bytes()
        need(P.digest(raw) == artifacts[name], 'candidate changed while freezing')
        copy = path / ('artifact-' + str(i) + '.bin')
        P.private_write(copy, raw)
        retained[name] = copy.relative_to(root).as_posix()
    record = {'schema_version': 1, 'kind': 'analyst_candidate', 'project_id': project['id'], 'id': ident,
              'artifacts': artifacts, 'artifact_roles': artifact_roles,
              'context': context, 'retained': retained, 'selected_intent': state['selected'],
              'previous': previous}
    if readiness['status'] == 'ready':
        record['workflow_context'] = readiness['context']
    saved = path / 'candidate.json'
    P.write_json(saved, record)
    pointer = {'path': saved.relative_to(root).as_posix(), 'sha256': P.digest(saved.read_bytes())}
    if gates['required']:
        try:
            P.stage_record(root, {'stage': 'candidate', 'iteration_id': ident,
                'builders': request['builders'],
                'artifacts': [saved.relative_to(root).as_posix(), *retained.values()]})
        except Exception as exc:
            # A failure after atomic replacement can still mean committed. Choice
            # provider availability must not determine whether bytes are retained.
            committed = P.routing_helper('stage_gates').candidate_commit_status(root, ident)
            if committed is False:
                for created in [saved, *(root / p for p in retained.values())]:
                    created.unlink()
                path.rmdir()
                raise
            raise ValueError('stage_gate_candidate_commit_requires_reconciliation; preserved candidate bytes') from exc
    if not first.exists():
        P.write_json(first, pointer)
    P.write_json(head, pointer, replace=head.exists())
    return {'status': 'frozen', 'path': saved.relative_to(root).as_posix(),
            'first': P.read_json(first)[0], 'publication_authorized': False}


def assess(root, request):
    root, project = P.load_project(root)
    need(type(request) is dict and set(request) == {'run', 'execution', 'candidate', 'evidence'}, 'invalid delivery request')
    result = inspect_run(root, {k: request[k] for k in ('run', 'execution')})
    findings = list(result['findings'])
    candidate, raw = P.read_json(P.relative_file(root, request['candidate']))
    need(candidate.get('kind') == 'analyst_candidate' and candidate.get('project_id') == project['id'], 'wrong candidate/project')
    candidate_pin = P.digest(raw)
    state = P.intent_helper().check(root)
    selected_artifacts = {s['candidate_path'] for s in state['selections'] if s.get('candidate_path')}
    roles = candidate.get('artifact_roles')
    if roles is None:  # Historical candidates used the exact primary set only.
        primary = set(candidate['artifacts'])
    elif (type(roles) is dict and set(roles) == set(candidate['artifacts']) and
          all(role in {'primary', 'supporting'} for role in roles.values())):
        primary = {p for p, role in roles.items() if role == 'primary'}
    else:
        primary = set()
        findings.append('candidate_artifact_roles_invalid')
    if not selected_artifacts or primary != selected_artifacts:
        findings.append('delivery_artifacts_differ_from_selected_candidates')
    try:
        history_check(root, project['id'], {'path': request['candidate'], 'sha256': candidate_pin})
    except (ValueError, OSError, KeyError, TypeError):
        findings.append('candidate_history_invalid')
    if candidate['selected_intent'] != result['selected_intent']:
        findings.append('candidate_selection_superseded')
    for name in ('artifacts', 'context'):
        try:
            if not current(root, candidate[name]):
                findings.append('candidate_' + name + '_changed')
        except (ValueError, OSError):
            findings.append('candidate_' + name + '_unavailable')
    for original, saved in candidate['retained'].items():
        need(P.digest(P.relative_file(root, saved).read_bytes()) == candidate['artifacts'][original], 'retained bytes changed')
    # The assessment context itself must be frozen, not a mutable after-the-fact declaration.
    execution, _ = P.read_json(P.relative_file(root, request['execution']))
    required = {request['run'], request['execution'], execution['request_review']['evidence_path']}
    if not required <= candidate['context'].keys():
        findings.append('candidate_missing_execution_context')
    evidence, _ = P.read_json(P.relative_file(root, request['evidence']))
    need(type(evidence) is dict and set(evidence) == {'candidate_sha256', 'lanes'}, 'invalid delivery evidence')
    if evidence['candidate_sha256'] != candidate_pin:
        findings.append('evidence_candidate_differs')
    need(type(evidence['lanes']) is dict and set(evidence['lanes']) == LANES, 'all evidence lanes must be accounted for')
    lanes = {}
    for name, entry in evidence['lanes'].items():
        need(type(entry) is dict and set(entry) == {'status', 'method', 'observer', 'bindings', 'reason'}, 'invalid lane evidence')
        need(entry['status'] in {'reported_pass', 'failed', 'not_run', 'not_applicable'}, 'invalid lane status')
        text(entry['reason'])
        outcome = entry['status']
        if outcome == 'reported_pass':
            text(entry['method']); text(entry['observer'])
            try:
                if not current(root, entry['bindings']):
                    outcome = 'stale'
            except (ValueError, OSError):
                outcome = 'unavailable'
            allowed = {'source': {'source_review'}, 'synthetic': {'constructed_fixture'},
                       'numerical': {'independent_reconciliation'}, 'native': {'native_observation'},
                       'rendered': {'rendered_observation'}, 'access': {'principal_observation'},
                       'publication': {'exact_readback'}, 'human': {'attributable_acceptance'}}
            need(entry['method'] in allowed[name], 'evidence method does not establish this lane')
        if name == 'rendered' and outcome == 'not_applicable':
            findings.append('rendered_quality_cannot_be_excluded')
        if outcome not in {'reported_pass', 'not_applicable'}:
            findings.append('lane_' + name + '_' + outcome)
        lanes[name] = outcome
    # Existing case-based review remains the authority for declared design coverage.
    design = P.design_completion(root)
    if design['status'] != 'recorded_complete':
        findings.append('design_requirement_review_' + design['status'])
    gates = P.stage_status(root)
    if gates['required']:
        try:
            P.stage_require(root, 'release')
            recorded_paths = {r['path'] for r in gates['candidate']['artifacts']}
            need(request['candidate'] in recorded_paths, 'stage_gate_reviewed_candidate_differs')
        except (ValueError, KeyError, TypeError) as exc:
            findings.append(str(exc))
    claims = assessment_claims(findings, result['findings'], lanes, design, gates)
    return {'status': 'candidate_with_gaps' if findings else 'ready_for_review', 'findings': findings,
            'stage_gates': gates,
            'candidate_sha256': candidate_pin, 'lanes': lanes, 'design': design,
            'review_assessments': {'source_critique': lanes['source'], 'requirement_context_design': design['status']},
            'claims': claims,
            'claims_authenticated': False, 'publication_authorized': False,
            'note': 'Assessment of supplied evidence, not approval, beauty certification, native execution or a universal write gate.'}


def assessment_claims(findings, structural_findings, lanes, design, gates):
    """Describe only recorded lanes. Publication/readback never upgrades quality."""
    pending = sorted(set(findings))
    identity_findings = [f for f in pending if f.startswith(('candidate_', 'evidence_candidate_',
        'delivery_artifacts_', 'stage_gate_reviewed_candidate_', 'stale_candidate_', 'assessment_startup_'))]
    current_candidate = not identity_findings
    source_reviewed = current_candidate and lanes.get('source') == 'reported_pass'
    rendered = current_candidate and lanes.get('rendered') == 'reported_pass' and design.get('status') == 'recorded_complete'
    native = current_candidate and lanes.get('native') == 'reported_pass'
    published = current_candidate and lanes.get('publication') == 'reported_pass'
    accepted = current_candidate and lanes.get('human') == 'reported_pass'
    return {'source_reviewed': source_reviewed, 'rendered_verified': rendered,
            'native_verified': native, 'effective_access_verified': current_candidate and lanes.get('access') == 'reported_pass',
            'published_readback_verified': published, 'user_acceptance_recorded': accepted,
            'preview_structurally_ready': current_candidate and not structural_findings and bool(gates.get('release_ready')),
            'current_candidate_evidence_bound': current_candidate,
            'delivery_evidence_complete': not pending, 'remaining_findings': pending,
            'summary': ('Delivery evidence recorded; human judgment remains explicit.' if not pending else
                        'Published candidate with unresolved evidence.' if published else
                        'Source-reviewed candidate with unresolved evidence.' if source_reviewed else
                        'Candidate with unresolved evidence.'),
            'publication_authorized': False, 'beauty_certified': False,
            'limitation': 'Supplied observations are not independently authenticated. Preview readiness is not permission to publish.'}
