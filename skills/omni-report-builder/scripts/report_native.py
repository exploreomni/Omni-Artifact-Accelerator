#!/usr/bin/env python3
"""Gated local Report preparation and supplied observations. No native executor.

Files and hashes preserve scope and freshness, never authenticate source evidence,
permission, native execution, rendering quality or acceptance. No credentials,
network, renderer, compiler, import of supplied definitions or expression execution.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

BASE = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


P = load('report_native_project', BASE / 'omni-artifact-accelerator/scripts/analyst_project.py')
C = load('report_native_contract', BASE / 'omni-artifact-accelerator/scripts/report_contract.py')
D = P.intent_helper()
FORMATS = {'rdlx-json', 'rdl', 'rdlc', 'native_ai_handoff'}
GAPS = [{'code': 'report_native_execution_unqualified'}, {'code': 'report_observations_not_authenticated'}]


def need(ok, code):
    P.need(ok, 'report_native.' + code)


def exact(value, keys, label):
    need(type(value) is dict and set(value) == set(keys), label + '_fields')


def text(value):
    return type(value) is str and 0 < len(value.strip()) <= 8192


def screening(value):
    """Reject credential fields in metadata; not a binary/source sanitizer."""
    if type(value) is dict:
        for key, item in value.items():
            need(not re.fullmatch(r'(?:authorization|cookie|password|secret|api[_-]?key|access[_-]?token)',
                                  key, re.I), 'credential_metadata_forbidden')
            screening(item)
    elif type(value) is list:
        for item in value: screening(item)
    elif type(value) is str:
        need(not re.search(r'(?i)(?:bearer\s+[A-Za-z0-9._~-]{8,}|-----BEGIN .*PRIVATE KEY-----)', value),
             'credential_metadata_forbidden')


def raw_file(root, path):
    file = P.relative_file(root, path)
    descriptor = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        meta = os.fstat(stream.fileno())
        need(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= P.MAX_BYTES, 'evidence_file_bound')
        raw = stream.read(P.MAX_BYTES + 1)
    need(0 < len(raw) <= P.MAX_BYTES, 'evidence_byte_bound')
    return raw


def pin(root, path):
    raw = raw_file(root, path)
    return {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}


def read(root, path):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate_json_key'); result[key] = value
        return result
    def nonfinite(_):
        raise ValueError('report_native.nonfinite_json')
    try:
        value = json.loads(raw_file(root, path), object_pairs_hook=pairs, parse_constant=nonfinite)
        P.canonical(value)
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('report_native.invalid_or_nested_json') from error
    return value


def seal(value):
    return {**value, 'sha256': P.digest(P.canonical(value))}


def unseal(value, kind):
    need(type(value) is dict and type(value.get('schema_version')) is int and value['schema_version'] == 1 and value.get('kind') == kind,
         'record_kind')
    body = {k: v for k, v in value.items() if k != 'sha256'}
    need(value.get('sha256') == P.digest(P.canonical(body)), 'record_changed')
    return body


def write(root, path, value):
    D.relative(path)
    P.write_json(root / path, value)
    return value


def current(root):
    root, project = P.load_project(root)
    need('report' in project['surfaces'], 'report_surface_required')
    state = D.check(root)
    need(state['status'] == 'consistent', 'selected_intent_stale_or_unresolved')
    selected = D.load_selected(root)
    need(selected is not None, 'selected_intent_required')
    selection = next(s for s in selected['spec']['selections'] if s['surface'] == 'report')
    design_path = selection['design_path']
    design = read(root, design_path)
    result = C.validate_handoff(root, design, selected['spec'], P)
    need(design['report_contract']['schema_version'] == 2, 'upgrade_report_contract_to_v2')
    return root, project, selected['spec'], selection, design, result


def visual_requirements(root, path):
    """Use the existing original-backed validator, including its source-pin checks."""
    previous = sys.modules.get('analyst_project')
    if previous is not None:
        need(Path(getattr(previous, '__file__', '')).resolve() == Path(P.__file__).resolve(),
             'unexpected_project_helper')
    else:
        # Fixed first-party sibling; isolated source checks do not use sys.path discovery.
        sys.modules['analyst_project'] = P
    try:
        workflow = P.routing_helper('visual_workflow')
    finally:
        if previous is None:
            del sys.modules['analyst_project']
    _, requirements = workflow.requirements(root, path)
    need('report' in requirements['surface'], 'requirements_report_surface_required')
    source = workflow.source_inventory(root, *(p['path'] for p in requirements['source_files']))
    return requirements, source


def candidate_body(root, spec):
    exact(spec, {'definition_path', 'definition_format', 'requirements_path', 'builders'}, 'preparation')
    screening(spec)
    root, project, intent, selection, design, validation = current(root)
    need(selection.get('candidate_path') is None or selection['candidate_path'] == spec['definition_path'],
         'selected_candidate_path_mismatch')
    need(spec['definition_format'] in FORMATS, 'definition_format')
    builders = spec['builders']
    need(type(builders) is list and builders and len(builders) == len(set(builders)) and
         all(text(i) for i in builders), 'builders_required')
    definition = pin(root, spec['definition_path'])
    requirements = pin(root, spec['requirements_path']) if spec['requirements_path'] is not None else None
    source_files = visual_requirements(root, spec['requirements_path'])[0]['source_files'] if requirements else []
    # Definition is retained opaque. Valid JSON or an extension is not schema compilation.
    return {'schema_version': 1, 'kind': 'report_candidate', 'project_id': project['id'],
            'preparation': copy.deepcopy(spec), 'intent': copy.deepcopy(project['design_intent']),
            'baseline': pin(root, selection['design_path']), 'definition': definition,
            'requirements': requirements, 'target': selection.get('target'),
            'source_files': copy.deepcopy(source_files),
            'dependencies': validation['dependencies'], 'obligations': C.obligations(design['report_contract']),
            'capability_gaps': validation['gaps'], 'native_authoring_qualified': False,
            'compiled': False, 'rendered': False, 'external_mutations_authorized': False}


def prepare(root, spec, output):
    root, _ = P.load_project(root)
    P.stage_require(root, 'build')
    return write(root, output, seal(candidate_body(root, spec)))


def check_candidate(root, path):
    value = read(root, path)
    body = unseal(value, 'report_candidate')
    need(body == candidate_body(root, body.get('preparation')), 'candidate_or_dependencies_changed')
    return value


def qualification_body(root, spec):
    exact(spec, {'target', 'runtime_version', 'schema_version', 'definition_format',
                 'schema_evidence_path', 'capability_evidence_path', 'reference'}, 'qualification')
    screening(spec)
    exact(spec['target'], {'base_url', 'document_id'}, 'target')
    D.validate_report_target({'surface': 'report', 'state': 'published',
        'instance': spec['target']['base_url'], 'document_id': spec['target']['document_id'],
        'capability_evidence_path': spec['capability_evidence_path']})
    need(all(text(spec[k]) for k in ('runtime_version', 'schema_version', 'reference')) and
         spec['runtime_version'] != 'unverified' and spec['schema_version'] != 'unverified', 'exact_version_evidence_required')
    need(spec['definition_format'] == 'rdlx-json', 'native_observation_format_unqualified')
    return {'schema_version': 1, 'kind': 'report_runtime_evidence', 'request': copy.deepcopy(spec),
            'schema_evidence': pin(root, spec['schema_evidence_path']),
            'capability_evidence': pin(root, spec['capability_evidence_path']),
            'native_execution_qualified': False, 'authority': 'none',
            'gaps': copy.deepcopy(GAPS)}


def qualify(root, spec, output):
    root, _ = P.load_project(root)
    return write(root, output, seal(qualification_body(root, spec)))


def check_qualification(root, path):
    value = read(root, path); body = unseal(value, 'report_runtime_evidence')
    need(body == qualification_body(root, body.get('request')), 'runtime_evidence_changed')
    return value


def context_pins(root, path, contract, intent):
    value = read(root, path)
    exact(value, {'principal_ref', 'locale', 'timezone', 'as_of', 'parameter_values', 'query_results', 'asset_paths'}, 'context')
    screening(value)
    need(all(text(value[k]) for k in ('principal_ref', 'locale', 'timezone', 'as_of')), 'context_text')
    need(value['locale'] == contract['data_policy']['locale'] and value['timezone'] == contract['data_policy']['timezone'],
         'context_locale_or_timezone_mismatch')
    need(type(value['parameter_values']) is dict and set(value['parameter_values']) ==
         {p['id'] for p in contract['parameters']}, 'parameter_values_incomplete')
    results = value['query_results']
    need(type(results) is list and len(results) <= 128, 'query_results')
    result_ids = []
    pins = [pin(root, path)]
    for result in results:
        exact(result, {'dataset_id', 'path', 'population_reference'}, 'query_result')
        need(text(result['dataset_id']) and text(result['population_reference']), 'query_result_identity')
        result_ids.append(result['dataset_id']); pins.append(pin(root, result['path']))
    need(len(set(result_ids)) == len(result_ids) and set(result_ids) == {d['id'] for d in contract['datasets']},
         'query_result_dataset_scope')
    assets = value['asset_paths']
    need(type(assets) is list and len(assets) <= 128 and all(type(p) is str for p in assets)
         and len(set(assets)) == len(assets), 'context_asset_paths')
    selected_assets = [a for a in intent['assets'] if a['id'] in contract['asset_ids']]
    need(all(a.get('local_path') for a in selected_assets) and
         set(assets) == {a['local_path'] for a in selected_assets}, 'selected_asset_bytes_required')
    pins.extend(pin(root, p) for p in assets)
    return value, pins


def observation_body(root, spec):
    exact(spec, {'candidate_path', 'qualification_path', 'operation', 'status', 'definition_path',
                 'output_format', 'export_path', 'context_path', 'evidence_path', 'reference'}, 'observation')
    screening(spec)
    candidate = check_candidate(root, spec['candidate_path'])
    runtime = check_qualification(root, spec['qualification_path'])
    target = candidate['target']
    need(type(target) is dict and target.get('state') == 'published' and
         {'base_url': target['instance'], 'document_id': target['document_id']} == runtime['request']['target'],
         'published_selected_target_required')
    need(pin(root, target['capability_evidence_path']) == runtime['capability_evidence'], 'target_capability_mismatch')
    need(runtime['request']['definition_format'] == candidate['preparation']['definition_format'], 'schema_format_mismatch')
    need(spec['operation'] in {'readback', 'export'} and spec['status'] in {'completed', 'failed', 'uncertain', 'conflict'},
         'observation_operation_or_status')
    need(text(spec['reference']), 'observation_reference')
    _, _, intent, _, design, _ = current(root)
    context, pins = context_pins(root, spec['context_path'], design['report_contract'], intent)
    pins.append(pin(root, spec['evidence_path']))
    definition = pin(root, spec['definition_path']) if spec['definition_path'] is not None else None
    exported = pin(root, spec['export_path']) if spec['export_path'] is not None else None
    matched = False
    if spec['operation'] == 'readback':
        need(spec['output_format'] is None and exported is None, 'readback_export_fields')
        need(spec['status'] != 'completed' or definition is not None, 'readback_definition_required')
        matched = definition is not None and definition['sha256'] == candidate['definition']['sha256']
    else:
        need(spec['output_format'] in {o['format'] for o in design['report_contract']['outputs']} and
             definition is None, 'export_scope')
        need(spec['status'] != 'completed' or exported is not None, 'export_bytes_required')
        if exported and spec['status'] == 'completed':
            raw = raw_file(root, exported['path'])
            need((raw.startswith(b'%PDF-') if spec['output_format'] in {'pdf', 'print'} else raw.startswith(b'PK\x03\x04')),
                 'export_signature_mismatch')
    return {'schema_version': 1, 'kind': 'report_observation', 'request': copy.deepcopy(spec),
            'candidate': pin(root, spec['candidate_path']), 'qualification': pin(root, spec['qualification_path']),
            'target': runtime['request']['target'], 'context': copy.deepcopy(context), 'context_evidence': pins,
            'definition': definition, 'export': exported,
            'status': ('readback_matched' if matched else 'readback_conflict') if spec['status'] == 'completed' and
                      spec['operation'] == 'readback' else spec['status'],
            'native_execution_qualified': False, 'claims_authenticated': False, 'native_verified': False,
            'business_accepted': False, 'external_mutations_authorized': False,
            'replay_allowed': False, 'gaps': copy.deepcopy(GAPS)}


def observe(root, spec, output):
    root, _ = P.load_project(root)
    return write(root, output, seal(observation_body(root, spec)))


def check_observation(root, path):
    value = read(root, path); body = unseal(value, 'report_observation')
    need(body == observation_body(root, body.get('request')), 'observation_or_context_changed')
    return value


def coverage_body(root, candidate_path, observations, cases):
    candidate = check_candidate(root, candidate_path)
    need(type(observations) is list and len(observations) <= 128 and all(type(p) is str for p in observations)
         and len(set(observations)) == len(observations), 'observation_paths')
    evidence = {p: check_observation(root, p) for p in observations}
    candidate_pin = pin(root, candidate_path)
    need(all(o['candidate'] == candidate_pin for o in evidence.values()), 'coverage_candidate_mismatch')
    obligations = {c['id']: c for c in candidate['obligations']}
    need(type(cases) is list and len(cases) <= 128, 'qa_cases')
    seen, passed, records = set(), set(), []
    for case in cases:
        exact(case, {'id', 'outcome', 'basis', 'observation_path', 'evidence_paths', 'reviewer', 'notes'}, 'qa_case')
        screening(case)
        need(case['id'] in obligations and case['id'] not in seen, 'qa_case_identity'); seen.add(case['id'])
        need(case['outcome'] in {'pass', 'fail', 'not_run'} and case['basis'] in {'source', 'rendered', 'native_behavior', 'access'}, 'qa_case_outcome')
        need(text(case['reviewer']) and case['reviewer'] not in candidate['preparation']['builders'] and text(case['notes']),
             'independent_reviewer_required')
        paths = case['evidence_paths']
        need(type(paths) is list and len(paths) <= 128 and all(type(p) is str for p in paths)
             and len(set(paths)) == len(paths), 'qa_evidence_paths')
        pins = [pin(root, p) for p in paths]
        observation = evidence.get(case['observation_path']) if case['observation_path'] is not None else None
        if case['outcome'] == 'pass':
            need(pins and observation is not None and observation['request']['operation'] == 'export' and
                 observation['status'] == 'completed' and observation['request']['output_format'] ==
                 obligations[case['id']]['output_format'], 'case_export_observation_required')
            lane = obligations[case['id']]['lane']
            required_basis = {'pagination': 'rendered', 'typography': 'rendered', 'accessibility': 'rendered',
                              'access': 'access', 'performance': 'native_behavior'}
            need(lane not in required_basis or case['basis'] == required_basis[lane], 'qa_basis_insufficient')
            passed.add(case['id'])
        records.append({'case': copy.deepcopy(case), 'evidence': pins})
    return {'schema_version': 1, 'kind': 'report_coverage', 'candidate': candidate_pin,
            'observation_paths': observations, 'observations': [pin(root, p) for p in observations],
            'cases': records, 'obligations': list(obligations.values()), 'passed_recorded_cases': sorted(passed),
            'pending_cases': sorted(set(obligations) - passed), 'native_verified': False,
            'human_accepted': False, 'claims_authenticated': False, 'gaps': copy.deepcopy(GAPS)}


def coverage(root, candidate_path, observation_paths, qa_cases, output):
    root, _ = P.load_project(root)
    return write(root, output, seal(coverage_body(root, candidate_path, observation_paths, qa_cases)))


def check_coverage(root, path):
    value = read(root, path); body = unseal(value, 'report_coverage')
    need(body == coverage_body(root, body.get('candidate', {}).get('path'), body.get('observation_paths'),
                               [r['case'] for r in body.get('cases', [])]), 'coverage_changed')
    return value


def verify_delivery(root, delivery):
    """Read-only proof for DMA returns; unresolved native authority always remains a gap."""
    exact(delivery, {'candidate_path', 'execution_receipt_path', 'coverage_path'}, 'delivery')
    root, _ = P.load_project(root)
    candidate = check_candidate(root, delivery['candidate_path'])
    receipt = check_observation(root, delivery['execution_receipt_path'])
    covered = check_coverage(root, delivery['coverage_path'])
    candidate_pin = pin(root, delivery['candidate_path'])
    need(candidate['requirements'] is not None, 'delivery_visual_requirements_required')
    need(receipt['candidate'] == candidate_pin == covered['candidate'] and
         receipt['status'] == 'readback_matched' and receipt['request']['operation'] == 'readback',
         'delivery_matched_readback_required')
    need(pin(root, delivery['execution_receipt_path']) in covered['observations'], 'delivery_readback_not_in_coverage')
    requirements, source = visual_requirements(root, candidate['requirements']['path'])
    gaps = copy.deepcopy(GAPS) + [{'code': 'report_capability_gap', 'capability': copy.deepcopy(gap)}
                                 for gap in candidate['capability_gaps']]
    gaps.extend({'code': 'pending_report_case', 'case_id': i} for i in covered['pending_cases'])
    # Report-format QA never clears source migration cases or proves a semantic binding.
    gaps.extend({'code': 'report_source_gap', 'source_gap': copy.deepcopy(gap)} for gap in source['gaps'])
    for item in requirements['items']:
        if 'report' not in item.get('target_surfaces', requirements['surface']):
            continue
        if item['disposition'] != 'migrate':
            gaps.append({'code': 'report_source_' + item['disposition'], 'asset_key': item['asset_key'],
                         'scope_decision': copy.deepcopy(item['scope_decision'])})
            continue
        gaps.append({'code': 'report_source_binding_unqualified', 'asset_key': item['asset_key']})
        gaps.extend({'code': 'pending_report_source_parity', 'asset_key': item['asset_key'],
                     'case_id': case['case_id'], 'lane': case['lane']} for case in item['required_cases'])
    return {'surface': 'report', 'target': receipt['target'], 'candidate_sha256': candidate['sha256'],
            'requirements': candidate['requirements'], 'baseline': candidate['baseline'], 'candidate': candidate_pin,
            'execution_receipt': pin(root, delivery['execution_receipt_path']), 'coverage': pin(root, delivery['coverage_path']),
            'gaps': gaps, 'native_verification': 'supplied_observation_only', 'native_verified': False,
            'migration_accepted': False, 'native_execution_qualified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'qualify', 'observe'):
        command = sub.add_parser(name); command.add_argument('--spec', required=True); command.add_argument('--output', required=True)
    check = sub.add_parser('check'); check.add_argument('--kind', choices=['candidate', 'qualification', 'observation', 'coverage'], required=True); check.add_argument('--path', required=True)
    cover = sub.add_parser('coverage'); cover.add_argument('--candidate', required=True); cover.add_argument('--observations', nargs='*', default=[]); cover.add_argument('--cases', required=True); cover.add_argument('--output', required=True)
    delivery = sub.add_parser('verify-delivery'); delivery.add_argument('--spec', required=True)
    args = parser.parse_args(); root, _ = P.load_project(args.project)
    if args.command in {'prepare', 'qualify', 'observe'}:
        result = globals()[args.command](root, read(root, args.spec), args.output)
    elif args.command == 'check':
        result = globals()['check_' + args.kind](root, args.path)
    elif args.command == 'coverage':
        result = coverage(root, args.candidate, args.observations, read(root, args.cases), args.output)
    else:
        result = verify_delivery(root, read(root, args.spec))
    print(json.dumps({'status': 'local_evidence_checked', 'kind': result.get('kind', result.get('surface')),
                      'native_execution_qualified': False, 'native_verified': False}, sort_keys=True))


if __name__ == '__main__': main()
