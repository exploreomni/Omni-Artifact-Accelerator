"""Offline Domo intake, retained capture and gated frontend handoff.

This module prepares evidence and assignments. It never loads the source engine,
fetches source URLs, chooses a design, mutates a target or authenticates approval.
"""
import importlib.util
import hashlib
import json
from pathlib import Path


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


HERE = Path(__file__).resolve().parent
ap = module('domo_workflow_project', HERE / 'analyst_project.py')
wf = module('domo_workflow_visual', HERE / 'visual_workflow.py')
host = module('domo_workflow_host', HERE / 'domo_host.py')
contract = host.contract
ROUTES = ('reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')


def plan_value(root, specification):
    root, project = ap.load_project(root)
    spec = wf.load(root, specification)
    allowed = {'schema_version', 'source', 'scope', 'route', 'route_reference', 'target',
               'existing_run', 'observed_at', 'evidence_mode', 'limits', 'completeness', 'experience'}
    ap.need(type(spec) is dict and spec.get('schema_version') == 'oaa-domo-intake.v1'
            and not set(spec) - allowed, 'domo.intake_contract')
    source, scope, target = (spec.get(k, {}) for k in ('source', 'scope', 'target'))
    ap.need(all(type(v) is dict for v in (source, scope, target)), 'domo.intake_objects')
    ap.need(not set(source) - contract.SOURCE_FIELDS, 'domo.source_fields_rejected')
    ap.need(not set(scope) - set(contract.SCOPE_FIELDS) - {'include_portfolio', 'include_dataflows',
            'max_dependency_dataflows', 'max_dependency_datasets'}, 'domo.scope_fields_rejected')
    ap.need(not set(target) - {'origin', 'surface', 'destination_reference'}, 'domo.target_fields_rejected')
    questions = []
    prompts = {'origin': 'What exact HTTPS Domo tenant origin is authorized?',
        'tenant_ref': 'Which retained tenant evidence identifies the source organization?',
        'principal_ref': 'Whose effective Domo access should this migration verify?',
        'permission_context_ref': 'Which permission or PDP context applies to this person?',
        'authorization_ref': 'Which actual source-read authorization should be retained?'}
    for key, prompt in prompts.items():
        if not source.get(key):
            questions.append({'field': 'source.' + key, 'stage': 'A', 'question': prompt})
    selected = any(scope.get(k) for k in contract.SCOPE_FIELDS)
    if not selected:
        questions.append({'field': 'scope', 'stage': 'A', 'question':
            'Which discovered Pages, Cards, DataSets, Apps or workflows should be migrated?'})
    if 'include_portfolio' not in scope:
        questions.append({'field': 'scope.include_portfolio', 'stage': 'A', 'question':
            'May discovery enumerate the visible portfolio, or only inspect selected IDs?'})
    if not spec.get('observed_at'):
        questions.append({'field': 'observed_at', 'stage': 'A', 'question':
            'What timezone-aware acquisition timestamp should be recorded?'})
    if spec.get('route') not in ROUTES or not spec.get('route_reference'):
        questions.append({'field': 'route', 'stage': 'B', 'question':
            'Reuse verified Omni Topics, reconstruct Omni semantics, or refactor the warehouse first?'})
    if not all(target.get(k) for k in ('origin', 'surface', 'destination_reference')):
        questions.append({'field': 'target', 'stage': 'D', 'question':
            'Which Omni instance, dashboard/App surface and development destination should receive the selected design?'})
    else:
        contract.origin(target['origin'])
        ap.need(target['surface'] in ('dashboard', 'app', 'both'), 'domo.target_surface')
        contract.reference(target['destination_reference'])
    experience = spec.get('experience', {})
    ap.need(type(experience) is dict and not set(experience) - {'audience', 'quality_bar', 'branding',
        'devices', 'visual_preferences', 'cache_refresh_policy', 'migration_fidelity'}, 'domo.experience_fields')
    for field, question in {
        'audience': 'Who uses the product and what decisions must it support?',
        'quality_bar': 'What should premium or polished mean here, and which reference qualities matter?',
        'branding': 'Which official website, approved logo, imagery, fonts and theme should guide the design?',
        'devices': 'Which screen sizes, navigation and accessibility needs should be designed for?',
        'visual_preferences': 'Compare, track, explain or explore spatially; are futuristic 3D treatments useful?',
        'cache_refresh_policy': 'Keep existing caching, use manual refresh, or request another freshness policy?',
        'migration_fidelity': 'Which source layouts and behaviors must remain exact, and which may be redesigned?'
    }.items():
        if not experience.get(field):
            questions.append({'field': 'experience.' + field, 'stage': 'D', 'question': question})
    existing = spec.get('existing_run')
    ap.need(existing is None or type(existing) is dict and set(existing) == {'run_id', 'unit_id', 'cycle_id', 'reference'}
            and all(contract.text(v) for v in existing.values()), 'domo.existing_run_identity')
    requests = []
    if all(source.get(k) for k in prompts) and spec.get('observed_at') and 'include_portfolio' in scope:
        full_scope = {k: scope.get(k, []) for k in contract.SCOPE_FIELDS}
        full_scope.update({k: scope.get(k, default) for k, default in (
            ('include_portfolio', False), ('include_dataflows', False),
            ('max_dependency_dataflows', 0), ('max_dependency_datasets', 100))})
        operation = 'capture' if selected else 'discover'
        value = {'schema_version': contract.SCHEMA, 'operation': operation,
            'request_id': 'domo-' + operation + '-' + ap.digest(ap.canonical([project['id'], spec]))[:16],
            'source': source, 'scope': full_scope, 'observed_at': spec['observed_at'],
            'evidence_mode': spec.get('evidence_mode', 'live_tenant'),
            'completeness': spec.get('completeness', {}), 'limits': spec.get('limits', {
                'max_requests': 100, 'max_response_bytes': 2 * 1024 * 1024,
                'max_total_bytes': 10 * 1024 * 1024, 'max_elapsed_seconds': 120})}
        if selected or full_scope['include_portfolio']:
            contract.request(value)
            requests.append(value)
    return {'schema_version': 'oaa-domo-plan.v1', 'engagement_id': project['id'],
        'intake': wf.pin(root, specification), 'existing_run': existing, 'route': spec.get('route'),
        'questions': questions, 'requests': requests, 'status': 'local_preparation',
        'next_action': 'review_runtime_and_capture' if requests else 'resolve_source_questions',
        'later_requirements': ['B: verified semantics and access', 'C: traceable narrative',
            'D: experience, fidelity, brand and freshness interview',
            'E: exactly three rendered concepts, actual user choice, detailed design',
            'F: guarded candidate plus independent security, UX, product and QA reviews'],
        'runtime_loaded': False, 'source_access_verified': False, 'target_write_authority': False}


def plan(root, specification, destination):
    return wf.output(Path(root), destination, plan_value(root, specification))


def materialize(root, plan_path, destination):
    root, _ = ap.load_project(root)
    value = wf.load(root, plan_path)
    ap.need(value.get('schema_version') == 'oaa-domo-plan.v1', 'domo.plan_required')
    wf.check_pin(root, value['intake'])
    ap.need(value == plan_value(root, value['intake']['path']), 'domo.plan_changed')
    ap.need(value['requests'], 'domo.resolve_source_questions_first')
    folder = Path(destination)
    ap.need(not folder.is_absolute() and folder.as_posix() == destination and '..' not in folder.parts
            and '\\' not in destination and destination not in ('', '.'), 'domo.request_directory')
    output = ap.no_links(root / folder)
    ap.need(not output.exists(), 'domo.request_directory_exists_resume_existing')
    output.mkdir(mode=0o700, parents=True)
    entries = []
    for value in value['requests']:
        name = str(folder / (value['request_id'] + '.json'))
        wf.output(root, name, value)
        entries.append({'id': value['request_id'], 'request': wf.pin(root, name),
                        'directory': 'inputs/domo-source/' + value['request_id']})
    return {'schema_version': 'oaa-domo-operation-entries.v1', 'operations': entries,
            'runtime_configuration_required': True, 'target_write_authority': False}


def import_capture(root, source, destination):
    root, _ = ap.load_project(root)
    path = ap.relative_file(root, source)
    value, raw = ap.read_json(path)
    wf.domo_module().verify_capture_files(value, path.parent)
    translator = module('domo_workflow_translator', HERE.parents[1] / 'omni-artifact-translator/scripts/translate_artifact.py')
    return wf.output(root, destination, translator.translate(raw, 'domo-agent', 'oaa-domo-evidence@1'))


def check_selected_scope(intake, capture):
    """Only selected artifacts and their retained dependencies may enter design."""
    index = {row['key']: row for row in capture['inventory']['items']}
    mapping = {'page_ids': 'page', 'card_ids': 'card', 'app_ids': 'app',
               'dataset_ids': 'dataset', 'workflow_ids': 'operation'}
    selected = set()
    for field, kind in mapping.items():
        for native in intake['scope'].get(field, []):
            matches = {key for key, row in index.items() if row['kind'] == kind and row['native_id'] == native}
            ap.need(matches, 'domo.selected_source_missing_from_capture')
            selected.update(matches)
    ap.need(selected, 'domo.selected_visual_scope_required')
    # Children of selected pages/apps, and explicit Card references from their
    # placements, are dependencies. Their parent containers remain context.
    allowed = set(selected)
    for key, row in index.items():
        cursor = row
        while cursor['parent_key']:
            if cursor['parent_key'] in selected:
                allowed.add(key)
                break
            cursor = index[cursor['parent_key']]
    allowed.update(key for key, row in index.items() if row['kind'] == 'placement' and row['configuration'].get('target_key') in selected)
    allowed.update(key for key, row in index.items() if row['kind'] == 'card' and any(
        r['kind'] == 'placement' and r.get('card_id') == row['native_id'] and k in allowed for k, r in index.items()))
    for key in list(allowed):
        cursor = index[key]
        while cursor['parent_key']:
            allowed.add(cursor['parent_key'])
            cursor = index[cursor['parent_key']]
    ap.need(all(key in allowed or row['kind'] not in {'page', 'app', 'app_page', 'component', 'card', 'placement'}
                or row['disposition'] != 'include' for key, row in index.items()), 'domo.capture_contains_unselected_artifact')


def build_handoff(root, specification, destination):
    root, project = ap.load_project(root)
    gates = module('domo_build_gates', HERE / 'stage_gates.py')
    gates.require_action(root, 'build')
    spec = wf.load(root, specification)
    ap.need(type(spec) is dict and set(spec) == {'schema_version', 'intake', 'requirements', 'target_context',
            'backend_evidence', 'app_handoff'} and spec['schema_version'] == 'oaa-domo-build-handoff-spec.v1',
            'domo.build_handoff_contract')
    intake_path = wf.check_pin(root, spec['intake'])
    prepared = plan_value(root, spec['intake']['path'])
    ap.need(not prepared['questions'], 'domo.interview_incomplete')
    intake, _ = ap.read_json(intake_path)
    _, requirements = wf.requirements(root, spec['requirements'])
    ap.need(requirements['route'] == intake['route'] in ROUTES, 'domo.route_mismatch')
    original_pin, inventory_pin = requirements['source_files'][:2]
    original = wf.load(root, original_pin['path'])
    inventory = wf.load(root, inventory_pin['path'])
    ap.need(inventory['source']['platform'] == 'domo' and
            original.get('schema_version') == 'oaa-domo-visual-capture.v1', 'domo.reviewed_capture_required')
    wf.domo_module().verify_capture_files(original, wf.check_pin(root, original_pin).parent)
    ap.need(original['identity'] == {'source_origin': intake['source']['origin'],
        'tenant_ref': intake['source']['tenant_ref'], 'principal_ref': intake['source']['principal_ref']},
        'domo.capture_identity_changed')
    check_selected_scope(intake, original)
    target = wf.load(root, spec['target_context'])
    ap.need(target == intake['target'], 'domo.target_context_changed')
    expected_surfaces = {'app', 'dashboard'} if target['surface'] == 'both' else {target['surface']}
    ap.need(expected_surfaces == set(project['surfaces']) == set(requirements['surface']), 'domo.selected_surfaces_changed')
    backend = spec['backend_evidence']
    ap.need(type(backend) is list and backend, 'domo.reviewed_backend_evidence_required')
    for item in backend:
        wf.check_pin(root, item)
    if target['surface'] in ('app', 'both'):
        app_path = wf.check_pin(root, spec['app_handoff'])
        app, _ = ap.read_json(app_path)
        wf.domo_module().validate_app_handoff(app, original['inventory'])
        ap.need(app == original.get('app_handoff'), 'domo.app_handoff_changed')
    else:
        ap.need(spec['app_handoff'] is None, 'domo.unselected_app_handoff')
    return wf.output(root, destination, {'schema_version': 'oaa-domo-build-handoff.v1',
        'intake': spec['intake'], 'requirements': wf.pin(root, spec['requirements']),
        'target_context': wf.pin(root, spec['target_context']), 'route': intake['route'],
        'existing_run': intake.get('existing_run'), 'source_files': requirements['source_files'],
        'semantic_qualification': 'retained_references_only_candidate_adapter_must_validate',
        'build_authority': False,
        'backend_evidence': backend, 'app_handoff': spec['app_handoff'],
        'next_action': 'prepare_owned_native_candidate_from_selected_design',
        'native_adapter': 'existing_candidate_bound_omni_adapter',
        'source_access_verified': False, 'native_validation': 'not_performed',
        'target_write_authority': False, 'acceptance_authority': False})


def source_bindings(context, evidence, portfolio, profile):
    """Preserve the source planner's stable IDs and its distinct native hashes."""
    def vendor_hash(value):
        return 'sha256:' + hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    ap.need(profile in ('native_content_hash', 'portfolio_object_hash'), 'domo.source_revision_profile')
    required = {'tenant_ref', 'run_id', 'migration_unit_id', 'validation_cycle_id', 'source_scope',
        'source_object_refs', 'created_at', 'inventory_snapshot_ref', 'source_object_graph_ref',
        'coverage_ledger_ref', 'evidence_bundle_ref'}
    ap.need(type(context) is dict and required <= set(context) and
        all(contract.text(context[k]) for k in required - {'source_scope', 'source_object_refs'}) and
        type(context['source_scope']) is list and context['source_scope'] and
        type(context['source_object_refs']) is list and context['source_object_refs'] and
        all(contract.text(x) for x in context['source_object_refs']), 'domo.original_planning_context_required')
    mapping = {}
    if profile == 'portfolio_object_hash':
        ap.need(type(portfolio) is dict and portfolio.get('contract_version') == 'domo-to-omni.portfolio-inventory.v1'
            and portfolio.get('immutable') is True and portfolio.get('source_tenant_ref') == context['tenant_ref']
            and portfolio.get('run_id') == context['run_id'], 'domo.original_portfolio_required')
        ap.need(all(portfolio.get(k) == context[k] for k in ('source_object_graph_ref', 'evidence_bundle_ref',
            'coverage_ledger_ref', 'inventory_snapshot_ref')), 'domo.portfolio_context_changed')
        ap.need(portfolio.get('portfolio_hash') == vendor_hash({k: v for k, v in portfolio.items() if k != 'portfolio_hash'}),
            'domo.portfolio_hash_changed')
        ap.need(type(portfolio.get('objects')) is list and portfolio['objects'], 'domo.portfolio_objects')
        for row in portfolio['objects']:
            identity = row.get('identity', {})
            ap.need(all(contract.text(identity.get(k)) for k in ('object_type', 'object_id', 'native_id')),
                'domo.portfolio_identity')
            key = (identity['object_type'], identity['object_id'])
            ap.need(key not in mapping and row.get('object_hash') == vendor_hash({k: v for k, v in row.items() if k != 'object_hash'}),
                'domo.portfolio_object_changed')
            mapping[key] = row
    else:
        ap.need(portfolio is None, 'domo.unselected_portfolio')
    rows = {row['object_type'] + ':' + row['object_id']: row for row in evidence['objects']}
    bindings, seen, native_seen = [], set(), set()
    for item in context['source_scope']:
        ap.need(type(item) is dict and set(item) == {'system', 'object_type', 'object_id', 'fingerprint'} and
            item['system'] in ('domo', 'dbt', 'snowflake', 'omni'), 'domo.return_source_scope')
        if item['system'] != 'domo':
            continue
        stable = (item['object_type'], item['object_id'])
        ap.need(stable not in seen, 'domo.return_duplicate_scope')
        seen.add(stable)
        native = item['object_id']
        if profile == 'portfolio_object_hash':
            mapped = mapping.get(stable)
            ap.need(mapped and mapped['object_hash'] == 'sha256:' + item['fingerprint'], 'domo.portfolio_revision_changed')
            native = mapped['identity']['native_id']
        key = item['object_type'] + ':' + native
        row = rows.get(key)
        ap.need(row and row.get('tenant_ref') == context['tenant_ref'] and contract.text(row.get('content_hash')),
                'domo.return_source_membership_changed')
        if profile == 'portfolio_object_hash':
            ap.need(mapped.get('definition', {}).get('content_hash') == row['content_hash'], 'domo.native_definition_changed')
        else:
            ap.need(row['content_hash'] == 'sha256:' + item['fingerprint'], 'domo.native_revision_changed')
        ap.need(key not in native_seen, 'domo.duplicate_native_binding')
        native_seen.add(key)
        bindings.append({k: item[k] for k in ('system', 'object_type', 'object_id', 'fingerprint')} |
                        {'object_key': key, 'content_hash': row['content_hash']})
    ap.need(bindings, 'domo.return_missing_scope')
    return bindings


def frontend_return_value(root, specification):
    """Prepare the source engine's passive return contract from verified delivery.

    The source engine must independently validate this proposal against its real
    retained planning context. It is never an attach/accept/complete command.
    """
    root, _ = ap.load_project(root)
    spec = wf.load(root, specification)
    ap.need(type(spec) is dict and set(spec) == {'schema_version', 'source_context', 'source_evidence',
            'frontend_receipt', 'producer_revision', 'source_revision_profile', 'source_portfolio'} and
            spec['schema_version'] == 'oaa-domo-frontend-return-spec.v1', 'domo.return_spec')
    context_path = wf.check_pin(root, spec['source_context'])
    evidence_path = wf.check_pin(root, spec['source_evidence'])
    receipt_path = wf.check_pin(root, spec['frontend_receipt'])
    context, _ = ap.read_json(context_path)
    evidence, raw = ap.read_json(evidence_path)
    translator = module('domo_return_translator', HERE.parents[1] / 'omni-artifact-translator/scripts/translate_artifact.py')
    translator.translate(raw, 'domo-agent', spec['producer_revision'])
    ap.need(evidence.get('contract_version') == 'omnikit.domo.evidence.v1', 'domo.return_full_evidence_required')
    migration = module('domo_return_migration', HERE.parents[1] / 'omni-backend-handoff/scripts/migration.py')
    verification = migration.verify_return(root, spec['frontend_receipt']['path'])
    receipt, _ = ap.read_json(receipt_path)
    scope = wf.load(root, receipt['scope']['path'])
    source_file_records = receipt.get('source_files', [])
    original_match = False
    source_assets = {}
    for inventory in scope['inventories']:
        inventory_value = wf.load(root, inventory['path'])
        ap.need(inventory_value['source']['platform'] == 'domo', 'domo.return_mixed_source')
        source_assets.update({a['asset_key']: a for a in inventory_value['assets']})
        if inventory_value['source'].get('input_sha256') == spec['source_evidence']['sha256']:
            original_match = True
        for record in source_file_records:
            path = wf.check_pin(root, {k: record[k] for k in ('path', 'sha256')})
            if 'bytes' in record:
                ap.need(path.stat().st_size == record['bytes'], 'domo.source_file_size_changed')
            if path.suffix == '.json':
                value, _ = ap.read_json(path)
                if type(value) is dict and value.get('schema_version') == 'oaa-domo-visual-capture.v1':
                    wf.domo_module().verify_capture_files(value, path.parent)
                    original_match = original_match or value['producer']['file']['sha256'] == spec['source_evidence']['sha256']
    ap.need(original_match, 'domo.return_source_evidence_not_in_frontend_scope')
    identity_fields = ('tenant_ref', 'run_id', 'migration_unit_id', 'validation_cycle_id')
    portfolio = ap.read_json(wf.check_pin(root, spec['source_portfolio']))[0] if spec['source_portfolio'] else None
    bindings = source_bindings(context, evidence, portfolio, spec['source_revision_profile'])
    covered = {key for unit in scope['units'] for key in unit['asset_keys']}
    for binding in bindings:
        native_id = binding['object_key'].split(':', 1)[1]
        source_kind = {'card': 'visual', 'app_studio_app': 'app', 'custom_app': 'app', 'subpage': 'page'}.get(binding['object_type'], binding['object_type'])
        if source_kind in ('app', 'page', 'visual'):
            matching = {key for key, asset in source_assets.items() if asset['source_id'] == native_id and asset['kind'] == source_kind}
            ap.need(matching and matching <= covered, 'domo.return_visual_not_in_frozen_scope')
    surfaces = sorted({surface for unit in scope['units'] if unit['disposition'] == 'migrate' for surface in unit['surfaces']})
    ap.need(surfaces and set(surfaces) <= {'app', 'dashboard'}, 'domo.return_surface')
    # One combined delivery receipt can cover both surfaces; its existing verifier
    # checks each candidate, readback and retained QA rather than copying statuses.
    artifacts = [{**spec['frontend_receipt'], 'bytes': receipt_path.stat().st_size,
                  'surface': 'both' if len(surfaces) > 1 else surfaces[0], 'kind': 'verified_frontend_receipt'}]
    result = {'schema_version': 'domo-frontend-return.v1',
        'source_context_file_sha256': spec['source_context']['sha256'],
        'source_evidence_file_sha256': spec['source_evidence']['sha256'],
        'source_revision_profile': spec['source_revision_profile'],
        'source_portfolio_file_sha256': spec['source_portfolio']['sha256'] if spec['source_portfolio'] else None,
        'source_context': {k: context[k] for k in identity_fields}, 'source_bindings': bindings,
        'target_artifacts': artifacts, 'gaps': [ap.canonical(gap).decode() if type(gap) is dict else gap
            for gap in receipt.get('gaps', [])] + ['business_acceptance_not_assessed',
            'canonical_run_identity_not_authenticated', 'recorded_frontend_verification:' + verification['status']],
        'outcome': 'proposal_only', 'acceptance_authority': False, 'target_write_authority': False,
        'release_authority': False}
    result['content_hash'] = ap.digest(ap.canonical(result))
    return result


def frontend_return(root, specification, destination):
    return wf.output(Path(root), destination, frontend_return_value(root, specification))


def check_frontend_return(root, specification, receipt):
    root, _ = ap.load_project(root)
    value = wf.load(root, receipt)
    ap.need(value == frontend_return_value(root, specification), 'domo.frontend_return_changed')
    return {'status': 'consistent', 'source_registry_validation': 'not_performed',
            'business_acceptance': 'not_assessed', 'target_write_authority': False}
