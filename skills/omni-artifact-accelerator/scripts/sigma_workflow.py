"""Offline Sigma intake, compatibility and guarded converter-package handoff."""
import argparse
import importlib.util
import json
from pathlib import Path


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


HERE = Path(__file__).resolve().parent
ap = _module('sigma_workflow_project', HERE / 'analyst_project.py')
wf = _module('sigma_workflow_visual', HERE / 'visual_workflow.py')
host = _module('sigma_workflow_host', HERE / 'sigma_host.py')
ROUTES = ('reuse_existing', 'omni_semantic_reconstruction', 'warehouse_first_refactor')
COMPATIBILITY = HERE.parent / 'references/sigma-compatibility.json'


def compatibility(capabilities):
    """Version recognition is separate from runtime approval and qualification."""
    registry, _ = ap.read_json(COMPATIBILITY)
    profile = registry['connected_source']
    for key in ('schema_version', 'extension_name', 'extension_version', 'request_schema', 'result_schema'):
        ap.need(capabilities.get(key) == profile[key], 'sigma.unsupported_capability_contract')
    ap.need(capabilities.get('operations') == ['check', 'inventory', 'snapshot', 'capture'] and
            capabilities.get('target_write_authority') is False and capabilities.get('terminal_review_bypass') is False,
            'sigma.invalid_source_capabilities')
    files = capabilities.get('implementation_files')
    ap.need(type(files) is dict and files and ap.digest(ap.canonical(files)) == capabilities.get('implementation_sha256'),
            'sigma.capability_implementation_hash')
    return {'status': 'recognized_source_contract', 'distribution_status': capabilities.get('distribution_status'),
            'implementation_sha256': capabilities['implementation_sha256'],
            'live_qualification': 'not_established', 'runtime_approval': 'not_verified',
            'target_write_authority': False}


def plan(root, specification, destination):
    """Ask only missing facts, then generate source requests without executing."""
    root, project = ap.load_project(root)
    spec = wf.load(root, specification)
    ap.need(spec.get('schema_version') == 'oaa-sigma-intake.v1', 'sigma.intake_contract')
    allowed = {'schema_version', 'source', 'scope', 'route', 'route_reference', 'target', 'existing_run',
               'include_contents_beta', 'evidence_mode', 'max_requests', 'capture_requests'}
    ap.need(not set(spec) - allowed, 'sigma.unknown_intake_fields')
    source, scope, target = spec.get('source', {}), spec.get('scope', {}), spec.get('target', {})
    questions = []
    prompts = {'api_base_url': 'Which Sigma API region/origin should be used?',
               'approved_api_host': 'What exact API host is approved for source credentials?',
               'expected_organization_id': 'Which Sigma organization is in scope?',
               'expected_user_id': 'Whose Sigma access should be verified?',
               'principal_ref': 'Which retained principal evidence identifies this user?',
               'authorization_ref': 'Which actual source-read authorization should be referenced?'}
    for key, question in prompts.items():
        if not source.get(key):
            questions.append({'field': 'source.' + key, 'question': question, 'stage': 'A'})
    ap.need(not set(source) - set(prompts), 'sigma.source_fields_rejected')
    if not scope.get('workbook_ids'):
        questions.append({'field': 'scope.workbook_ids', 'question': 'Which discovered workbook IDs should be migrated?', 'stage': 'A'})
    if spec.get('route') not in ROUTES or not spec.get('route_reference'):
        questions.append({'field': 'route', 'question': 'Reuse verified Omni Topics, reconstruct Omni semantics, or refactor the warehouse first?', 'stage': 'B'})
    if not all(target.get(k) for k in ('origin', 'surface', 'destination_reference')):
        questions.append({'field': 'target', 'question': 'Which Omni instance and development destination should receive the selected dashboard or App?', 'stage': 'D'})
    requests = []
    if all(source.get(k) for k in prompts):
        common = {'schema_version': 'sigma-source-operation-request.v1', **source,
                  'evidence_mode': spec.get('evidence_mode', 'live_tenant'),
                  'max_requests': spec.get('max_requests', 100),
                  'scope': {'workbook_ids': scope.get('workbook_ids', []), 'data_model_ids': scope.get('data_model_ids', [])},
                  'options': {'include_contents_beta': False}}
        ap.need(type(spec.get('include_contents_beta', False)) is bool, 'sigma.beta_option_required')
        for operation in ('check', 'inventory', 'snapshot'):
            if operation == 'snapshot' and not common['scope']['workbook_ids']:
                continue
            request = {**common, 'operation': operation,
                       'request_id': 'sigma-' + operation + '-' + ap.digest(ap.canonical([project['id'], spec]))[:16],
                       'options': {'include_contents_beta': spec.get('include_contents_beta', False) if operation == 'snapshot' else False}}
            host.request(request)
            requests.append(request)
        captures = spec.get('capture_requests', [])
        ap.need(type(captures) is list and len(captures) <= 100, 'sigma.capture_batch_limit')
        seen = set()
        for capture in captures:
            cid = capture.get('capture_id')
            ap.need(type(cid) is str and cid not in seen, 'sigma.unique_capture_required')
            seen.add(cid)
            ap.need(capture.get('workbook_id') in common['scope']['workbook_ids'] and
                    (not capture.get('data_model_id') or capture['data_model_id'] in common['scope']['data_model_ids']),
                    'sigma.capture_outside_selected_intake')
            # Exact version/state choices come from inspected source evidence.
            # This helper never guesses tags, page IDs or effective personas.
            request = {**common, 'operation': 'capture', 'request_id': cid,
                       'scope': {'workbook_ids': [capture.get('workbook_id')],
                                 'data_model_ids': [capture['data_model_id']] if capture.get('data_model_id') else []},
                       'max_requests': capture.get('max_requests_per_invocation', 100),
                       'visual_capture_request': capture}
            for key in prompts:
                ap.need(capture.get(key) == source[key], 'sigma.capture_identity_changed')
            host.request(request)
            requests.append(request)
    return wf.output(root, destination, {'schema_version': 'oaa-sigma-plan.v1', 'engagement_id': project['id'],
        'intake': wf.pin(root, specification), 'existing_run': spec.get('existing_run'),
        'questions': questions, 'requests': requests, 'route': spec.get('route'),
        'status': 'local_preparation', 'next_action': 'resolve_source_questions' if any(q['stage'] == 'A' and q['field'] != 'scope.workbook_ids' for q in questions) else 'review_runtime_then_check_source',
        'later_requirements': ['B: qualify query semantics and effective access', 'C: traceable analytical narrative',
            'D: quality, branding, devices, visual treatments, cache/refresh interview',
            'E: three rendered concepts with equal analytical scope, actual user choice and detailed design',
            'F: guarded candidate and independent security, UX, product and QA reviews'],
        'runtime_loaded': False, 'source_access_verified': False, 'target_write_authority': False})


def materialize(root, plan_path, destination):
    root, _ = ap.load_project(root)
    value = wf.load(root, plan_path)
    ap.need(value.get('schema_version') == 'oaa-sigma-plan.v1', 'sigma.plan_required')
    wf.check_pin(root, value['intake'])
    ap.need(type(value.get('requests')) is list and value['requests'], 'sigma.resolve_source_questions_first')
    # Regenerate the requests from the pinned intake in memory by comparing the
    # saved plan's immutable content through a temporary private output.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='.sigma-plan-', dir=root) as folder:
        relative = str((Path(folder) / 'plan.json').relative_to(root))
        plan(root, value['intake']['path'], relative)
        regenerated = wf.load(root, relative)
        ap.need(regenerated == value, 'sigma.plan_changed')
    folder = Path(destination)
    ap.need(not folder.is_absolute() and folder.as_posix() == destination and '..' not in folder.parts
            and '\\' not in destination and destination not in ('', '.'), 'sigma.request_directory')
    output = ap.no_links(root / folder)
    ap.need(not output.exists(), 'sigma.request_directory_exists_resume_existing')
    output.mkdir(mode=0o700, parents=True)
    entries = []
    for request in value['requests']:
        name = str(folder / (request['request_id'] + '.json'))
        wf.output(root, name, request)
        entries.append({'id': request['request_id'], 'request': wf.pin(root, name),
                        'directory': 'inputs/sigma-source/' + request['request_id']})
    return {'schema_version': 'oaa-sigma-operation-entries.v1', 'operations': entries,
            'runtime_configuration_required': True, 'target_write_authority': False}


def package_handoff(root, specification, destination):
    """Reuse upstream converter outputs; never call Session internals or publish."""
    root, _ = ap.load_project(root)
    gates = _module('sigma_handoff_gates', HERE / 'stage_gates.py')
    gates.require_action(root, 'build')
    spec = wf.load(root, specification)
    ap.need(spec.get('schema_version') == 'oaa-sigma-package-handoff.v1', 'sigma.handoff_contract')
    package_path = wf.check_pin(root, spec['manifest'])
    value, _ = ap.read_json(package_path)
    verification = wf.sigma_module().verify_package_files(value, package_path.parent)
    _, requirements = wf.requirements(root, spec['requirements'])
    ap.need(requirements['route'] == value['route'], 'sigma.package_route_mismatch')
    # The exact source and target bindings must be separately retained. Titles,
    # a manifest or the presence of any accepted package cannot select them.
    original = wf.check_pin(root, requirements['source_files'][0])
    source_value, _ = ap.read_json(original)
    target_value = wf.load(root, spec['target_context'])
    sha = wf.sigma_module().sha
    ap.need(sha(source_value) == value['source_sha256'] and sha(target_value) == value['target_sha256'],
            'sigma.package_source_target_changed')
    files = [{**record, 'path': str((package_path.parent / record['path']).relative_to(root))}
             for record in verification['verified_files']]
    return wf.output(root, destination, {'schema_version': 'oaa-sigma-converter-handoff.v1',
        'manifest': spec['manifest'], 'requirements': wf.pin(root, spec['requirements']),
        'target_context': wf.pin(root, spec['target_context']), 'route': value['route'],
        'files': files, 'review': verification['review'], 'gaps': verification['gaps'],
        'next_action': 'inspect_converter_outputs_and_prepare_owned_native_candidate',
        'native_adapter': 'existing_named_draft_with_separate_startup_authority',
        'target_write_authority': False, 'native_validation': 'not_performed'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', required=True)
    p.add_argument('operation', choices=('plan', 'materialize', 'package-handoff', 'compatibility'))
    p.add_argument('--spec', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if args.operation == 'compatibility':
        value = compatibility(wf.load(Path(args.project), args.spec))
        wf.output(Path(args.project), args.output, value)
    elif args.operation == 'materialize':
        value = materialize(args.project, args.spec, args.output)
    else:
        value = globals()[args.operation.replace('-', '_')](args.project, args.spec, args.output)
    print(json.dumps(value))


if __name__ == '__main__':
    main()
