"""Offline coverage of supplied execution observations; never grants authority.

Pins establish byte integrity, not origin, authenticity, isolation or acceptance.
No worker, source code, query, native operation or external dependency is executed.
"""
import importlib.util
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

_spec = importlib.util.spec_from_file_location('qualification_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
VERSION = 'execution-scenarios-v1'
SHA = re.compile(r'[a-f0-9]{64}')
CAPABILITIES = ('bounded_context', 'restricted_tools', 'atomic_launch_reservation', 'durable_resume',
                'exact_candidate_authority', 'native_readback', 'render_observation',
                'principal_observation', 'human_observation')
CORE_CAPABILITIES = set(CAPABILITIES[:5])
PROVENANCE = {'host_observation', 'native_observation', 'human_observation',
              'source_execution', 'local_synthetic', 'imported_assertion'}
LANES = {
    'host': ('bounded_dispatch', 'tool_profile_denial', 'source_instruction_containment',
             'stage_a_source_and_access', 'stage_b_qualified_analysis', 'stage_c_traceable_narrative', 'stage_d_artifact_discovery',
             'stage_e_three_options_actual_selection_and_design', 'stage_f_candidate_review', 'missing_gate_denial',
             'duplicate_claim', 'output_overlap_denial', 'concurrency_limit',
             'uncertain_launch_reconciliation', 'unchanged_blocker_stop', 'checkpoint_resume',
             'changed_context_revalidation', 'completed_result_reuse', 'independent_review_identity',
             'end_to_end_local_candidate'),
    'native': ('exact_candidate_denial', 'target_principal_drift_denial',
               'uncertain_write_reconciliation', 'candidate_readback', 'demo_release_separation',
               'end_to_end_native_candidate', 'dynamic_data_and_control_binding'),
    'visual': ('rendered_default_and_narrow', 'empty_sparse_error_states'),
    'access': ('allowed_principal', 'denied_principal', 'export_access'),
    'human': ('nonleading_task_observation', 'explicit_acceptance'),
    'migration': ('original_execution_provenance', 'independent_source_target_comparison',
                  'filters_calendar_population_equivalence', 'skewed_and_changing_categories'),
    'semantic': ('adaptation_owner_decision', 'zero_null_negative_and_sparse', 'affected_consumer_review'),
}
KINDS = {'host': {'host_observation'}, 'native': {'native_observation'},
         'visual': {'native_observation', 'human_observation'},
         'access': {'native_observation', 'human_observation'}, 'human': {'human_observation'},
         'migration': {'source_execution', 'native_observation'},
         'semantic': {'source_execution', 'human_observation', 'native_observation'}}
ASSURANCE = ('Coverage of supplied observations only. Provenance labels and hashes do not authenticate '
             'execution, isolation, access, human acceptance or permissions. No data file grants authority.')


def need(condition, code):
    if not condition:
        raise ValueError('qualification.' + code)


def fields(value, expected):
    need(type(value) is dict and set(value) == set(expected), 'invalid_fields')


def text(value, limit=2048):
    need(type(value) is str and bool(value.strip()) and len(value.encode('utf-8')) <= limit,
         'invalid_text')


def verified_pin(root, value):
    fields(value, ('path', 'sha256'))
    text(value['path'])
    need(type(value['sha256']) is str and SHA.fullmatch(value['sha256']), 'invalid_pin')
    path = P.relative_file(root, value['path'])
    with path.open('rb') as stream:
        raw = stream.read(P.MAX_BYTES + 1)
    need(len(raw) <= P.MAX_BYTES and P.digest(raw) == value['sha256'], 'pinned_bytes_changed')
    return path, raw


def pin(root, value):
    """Validate evidence bytes while preserving the path-returning helper API."""
    return verified_pin(root, value)[0]


def pinned_json(root, value):
    """Parse the exact buffer whose digest matched; never reopen a verified path."""
    _, raw = verified_pin(root, value)
    try:
        def nonfinite(_):
            raise ValueError('Nonfinite JSON')
        result = json.loads(raw, object_pairs_hook=P.reject_duplicate, parse_constant=nonfinite)
        # Also rejects numeric exponent overflow and excessive nesting, matching
        # the existing project JSON reader without re-reading mutable bytes.
        P.canonical(result)
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('qualification.invalid_pinned_json') from None


def pins(root, values, nonempty=False):
    need(type(values) is list and len(values) <= 64 and (values or not nonempty), 'invalid_pin_list')
    seen = set()
    for value in values:
        pin(root, value)
        need(value['path'] not in seen, 'duplicate_pin')
        seen.add(value['path'])


def catalog():
    return {'schema_version': 1, 'catalog_version': VERSION,
            'capabilities': list(CAPABILITIES), 'core_capabilities': sorted(CORE_CAPABILITIES),
            'scenarios': [{'scenario_id': name, 'lane': lane,
                           'required_when': lane if lane in {'migration', 'semantic'} else 'always',
                           'eligible_provenance': sorted(KINDS[lane])}
                          for lane, names in LANES.items() for name in names],
            'execution_authorized': False, 'publication_authorized': False, 'assurance': ASSURANCE}


def timestamp(value):
    text(value)
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(result.tzinfo is not None, 'timestamp_requires_offset')
        return result
    except ValueError:
        raise ValueError('qualification.invalid_observation_timestamp') from None


def freshness(value):
    fields(value, ('observed_at', 'valid_until', 'basis'))
    text(value['basis'])
    observed, until = timestamp(value['observed_at']), timestamp(value['valid_until'])
    need(observed < until and observed <= datetime.now(timezone.utc), 'invalid_freshness_window')
    return 'current' if datetime.now(timezone.utc) < until else 'expired'


def target(root, binding):
    if binding is None:
        return None
    value = pinned_json(root, binding)
    fields(value, ('schema_version', 'kind', 'origin', 'principal', 'model_id', 'document_id',
                   'draft_id', 'operation', 'audience', 'freshness', 'evidence'))
    need(type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'execution_qualification_target', 'unsupported_target')
    text(value['origin'])
    origin = urlsplit(value['origin'])
    need(origin.scheme == 'https' and origin.hostname and not origin.username and not origin.password
         and not origin.path and not origin.query and not origin.fragment and origin.port in (None, 443)
         and not any(c.isspace() for c in value['origin']), 'invalid_target_origin')
    for key in ('principal', 'model_id', 'document_id'):
        text(value[key])
    need(value['operation'] in {'draft_edit', 'initial_create', 'publish', 'readback', 'demo_create'},
         'invalid_target_operation')
    if value['draft_id'] is not None:
        text(value['draft_id'])
    need(value['operation'] not in {'draft_edit', 'publish'} or value['draft_id'] is not None,
         'named_draft_required')
    fields(value['audience'], ('visibility', 'principal_refs'))
    need(value['audience']['visibility'] in {'private', 'restricted', 'shared'}, 'invalid_audience')
    people = value['audience']['principal_refs']
    need(type(people) is list and 0 < len(people) <= 128, 'explicit_audience_required')
    for item in people:
        text(item)
    need(len(set(people)) == len(people), 'duplicate_audience')
    pins(root, value['evidence'], True)
    return {'binding': binding, 'freshness': freshness(value['freshness'])}


def profile(root, binding):
    value = pinned_json(root, binding)
    fields(value, ('schema_version', 'kind', 'profile_id', 'profile_version', 'host', 'runtime',
                   'implementation', 'tool_profile', 'capabilities', 'freshness'))
    need(type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'execution_host_profile', 'unsupported_profile')
    for key in ('profile_id', 'profile_version'):
        text(value[key])
    for key in ('host', 'runtime'):
        fields(value[key], ('name', 'version'))
        for item in value[key].values():
            text(item)
    pins(root, value['implementation'], True)
    pin(root, value['tool_profile'])
    freshness(value['freshness'])
    fields(value['capabilities'], CAPABILITIES)
    for row in value['capabilities'].values():
        fields(row, ('status', 'reason', 'evidence'))
        need(row['status'] in {'reported_supported', 'reported_unsupported', 'unknown'}, 'invalid_capability_status')
        text(row['reason'])
        pins(root, row['evidence'], row['status'] != 'unknown')
    return value


def observation(root, binding, spec, cases):
    value = pinned_json(root, binding)
    fields(value, ('schema_version', 'kind', 'observation_id', 'scenario_id', 'profile', 'candidate', 'target',
                   'outcome', 'provenance', 'evidence', 'summary'))
    need(type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'execution_observation', 'unsupported_observation')
    text(value['observation_id']); text(value['summary'])
    need(value['scenario_id'] in cases, 'unknown_or_out_of_scope_scenario')
    need(all(value[key] == spec[key] for key in ('profile', 'candidate', 'target')), 'observation_binding_differs')
    need(value['outcome'] in {'pass', 'fail', 'pending'}, 'invalid_outcome')
    pins(root, value['evidence'], value['outcome'] != 'pending')
    provenance = value['provenance']
    if value['outcome'] == 'pending':
        need(provenance is None, 'pending_has_no_execution_provenance')
    else:
        fields(provenance, ('kind', 'observer', 'run_reference', 'recorded_at', 'valid_until', 'method'))
        need(provenance['kind'] in PROVENANCE, 'invalid_provenance')
        for key, item in provenance.items():
            if key != 'valid_until':
                text(item)
        observed_at = timestamp(provenance['recorded_at'])
        need(observed_at <= datetime.now(timezone.utc), 'future_observation')
        required = cases[value['scenario_id']] in {'host', 'native', 'access'} or provenance['kind'] == 'native_observation'
        need(provenance['valid_until'] is not None or not required, 'observation_freshness_required')
        if provenance['valid_until'] is not None:
            need(timestamp(provenance['valid_until']) > observed_at, 'invalid_freshness_window')
    return value


def assess(root, spec):
    """Recompute coverage without trusting a precomputed pass or running evidence."""
    root, project = P.load_project(root)
    fields(spec, ('schema_version', 'kind', 'catalog_version', 'profile', 'candidate', 'target', 'scope', 'observations'))
    need(type(spec['schema_version']) is int and spec['schema_version'] == 1 and
         spec['kind'] == 'execution_qualification_spec' and spec['catalog_version'] == VERSION,
         'unsupported_spec')
    fields(spec['scope'], ('migration', 'semantic_adaptation'))
    need(all(type(x) is bool for x in spec['scope'].values()), 'invalid_scope')
    host = profile(root, spec['profile'])
    pin(root, spec['candidate'])
    destination = target(root, spec['target'])
    selected = {name: lane for lane, names in LANES.items()
                if lane not in {'migration', 'semantic'} or spec['scope']['migration' if lane == 'migration' else 'semantic_adaptation']
                for name in names}
    need(type(spec['observations']) is list and len(spec['observations']) <= len(selected), 'invalid_observations')
    observed, identities = {}, set()
    for binding in spec['observations']:
        value = observation(root, binding, spec, selected)
        name = value['scenario_id']
        need(name not in observed and value['observation_id'] not in identities, 'duplicate_observation')
        identities.add(value['observation_id'])
        observed[name] = (binding, value)
    rows = []
    for name, lane in selected.items():
        binding, item = observed.get(name, (None, None))
        kind = item['provenance']['kind'] if item and item['provenance'] else None
        status = 'pending'
        if item and item['outcome'] != 'pending':
            status = ('reported_pass' if item['outcome'] == 'pass' else 'reported_fail') if kind in KINDS[lane] else (
                'synthetic_only' if kind == 'local_synthetic' else 'assertion_only' if kind == 'imported_assertion'
                else 'incompatible_provenance')
            if status in {'reported_pass', 'reported_fail'}:
                until = item['provenance']['valid_until']
                if until is not None and timestamp(until) <= datetime.now(timezone.utc):
                    status = 'expired_observation'
                elif lane == 'host' and freshness(host['freshness']) != 'current':
                    status = 'expired_profile'
                elif lane in {'native', 'access'} or kind == 'native_observation':
                    if destination is None:
                        status = 'target_unbound'
                    elif destination['freshness'] != 'current':
                        status = 'expired_target'
        rows.append({'scenario_id': name, 'lane': lane, 'status': status, 'observation': binding,
                     'provenance_kind': kind, 'reported_outcome': item['outcome'] if item else None})
    lanes = {}
    for lane in LANES:
        items = [r for r in rows if r['lane'] == lane]
        pending = [r['scenario_id'] for r in items if r['status'] != 'reported_pass']
        lanes[lane] = {'status': 'not_selected' if not items else 'reported_fail' if any(r['status'] == 'reported_fail' for r in items)
                       else 'incomplete' if pending else 'supplied_evidence_complete',
                       'required': len(items), 'reported_pass': len(items) - len(pending), 'unresolved': pending}
    unknown = [key for key, row in host['capabilities'].items() if row['status'] == 'unknown']
    unsupported = [key for key, row in host['capabilities'].items() if row['status'] == 'reported_unsupported']
    incomplete = (any(r['status'] != 'reported_pass' for r in rows) or
                  bool(CORE_CAPABILITIES & set(unknown + unsupported)) or freshness(host['freshness']) != 'current')
    failed = any(r['status'] == 'reported_fail' for r in rows)
    return {'schema_version': 1, 'kind': 'execution_qualification_assessment', 'project_id': project['id'],
            'catalog_version': VERSION, 'catalog_sha256': P.digest(P.canonical(catalog())),
            'implementation_sha256': P.digest(Path(__file__).read_bytes()),
            'profile': spec['profile'], 'candidate': spec['candidate'], 'target': spec['target'], 'scope': spec['scope'],
            'profile_freshness': freshness(host['freshness']), 'target_freshness': destination['freshness'] if destination else 'unbound',
            'host': host['host'], 'runtime': host['runtime'], 'profile_id': host['profile_id'],
            'profile_version': host['profile_version'], 'capabilities': host['capabilities'],
            'unknown_capabilities': unknown, 'unsupported_capabilities': unsupported,
            'status': 'reported_fail' if failed else 'incomplete' if incomplete else 'supplied_evidence_complete',
            'lanes': lanes, 'scenarios': rows, 'execution_authorized': False, 'publication_authorized': False,
            'host_isolation_verified': False, 'provenance_authenticated': False,
            'native_verified': False, 'effective_access_verified': False, 'human_acceptance_verified': False,
            'tokens': None, 'cost': None, 'assurance': ASSURANCE}


def summary(value, output, digest):
    result = value['assessment']
    return {'status': 'consistent', 'report': {'path': output, 'sha256': digest},
            'coverage_status': result['status'], 'lanes': result['lanes'],
            'unknown_capabilities': result['unknown_capabilities'],
            'execution_authorized': False, 'publication_authorized': False, 'assurance': ASSURANCE}


def record(root, spec_path, output):
    """Write an immutable local coverage report; existing identical reports are reused."""
    root, _ = P.load_project(root)
    source = P.relative_file(root, spec_path)
    spec, raw = P.read_json(source)
    result = {'schema_version': 1, 'kind': 'execution_qualification_report',
              'spec': {'path': spec_path, 'sha256': P.digest(raw)}, 'assessment': assess(root, spec)}
    relative = Path(output)
    need(type(output) is str and relative.as_posix() == output and not relative.is_absolute()
         and '..' not in relative.parts and '\\' not in output and output.startswith('evidence/')
         and output.endswith('.json'), 'report_requires_evidence_json_path')
    target = P.no_links(root / relative)
    need(target.resolve().is_relative_to(root.resolve()), 'output_escape')
    need(len(P.canonical(result)) <= P.MAX_BYTES, 'report_too_large')
    if target.exists():
        need(P.read_json(target)[0] == result, 'immutable_report_exists_use_new_version')
    else:
        P.write_json(target, result)
    return summary(result, output, P.digest(target.read_bytes()))


def check(root, report_path):
    """Check all exact pins again; modified summaries cannot establish coverage."""
    try:
        root, _ = P.load_project(root)
        path = P.relative_file(root, report_path)
        saved, raw = P.read_json(path)
        fields(saved, ('schema_version', 'kind', 'spec', 'assessment'))
        need(type(saved['schema_version']) is int and saved['schema_version'] == 1 and
             saved['kind'] == 'execution_qualification_report', 'unsupported_report')
        spec = pinned_json(root, saved['spec'])
        need(saved['assessment'] == assess(root, spec), 'report_changed_or_stale')
        return summary(saved, report_path, P.digest(raw))
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        return {'status': 'inconsistent', 'findings': ['qualification_pins_or_coverage_changed'],
                'execution_authorized': False, 'publication_authorized': False}
