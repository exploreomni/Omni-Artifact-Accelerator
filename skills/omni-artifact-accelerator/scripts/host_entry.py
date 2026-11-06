"""Read-only host entry inspection from the explicitly trusted package.

The reported loaded directory is read as bytes. No code is imported from it.
Only a programmatically supplied, independently qualified host provider can
corroborate tool mediation. Stored records and request fields grant no authority.
"""
import argparse
import copy
import importlib.util
from pathlib import Path
import re
import secrets

_spec = importlib.util.spec_from_file_location('host_entry_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
W = P.routing_helper('delivery_workflow')
ROUTES = ('package_helper', 'cli', 'api', 'mcp', 'shell', 'file_write', 'other')
SHA = re.compile(r'[a-f0-9]{64}\Z')
ENTRY = 'omni-artifact-accelerator/SKILL.md'
HELPER = 'omni-artifact-accelerator/scripts/analyst_project.py'


def need(ok, code):
    if not ok:
        raise ValueError('host_entry.' + code)


def fields(value, required, optional=()):
    need(type(value) is dict and set(required) <= set(value) <= set(required) | set(optional), 'invalid_fields')


def text(value, maximum=2048):
    return type(value) is str and 0 < len(value.encode('utf-8')) <= maximum and value.strip() == value and all(ord(c) >= 32 for c in value)


def validate(request):
    fields(request, ('schema_version', 'id', 'host', 'loaded_package_path', 'source_expectation', 'routes'))
    need(type(request['schema_version']) is int and request['schema_version'] == 1, 'unsupported_request')
    W.identity(request['id'])
    fields(request['host'], ('name', 'execution_mode', 'tools', 'constraints'))
    need(text(request['host']['name'], 256) and request['host']['execution_mode'] in
         ('inline', 'delegated', 'instruction_guided'), 'invalid_host')
    for key in ('tools', 'constraints'):
        rows = request['host'][key]
        need(type(rows) is list and len(rows) <= 128 and all(text(v, 512) for v in rows)
             and len(set(rows)) == len(rows), 'invalid_host_list')
    path = request['loaded_package_path']
    need(text(path, 4096) and Path(path).is_absolute() and '..' not in Path(path).parts, 'absolute_loaded_package_required')
    need(type(request['source_expectation']) is dict, 'source_expectation_required')
    routes = request['routes']
    need(type(routes) is list and len(ROUTES) <= len(routes) <= 128, 'route_inventory_required')
    seen = set()
    for row in routes:
        fields(row, ('kind', 'name', 'availability'))
        need(type(row['kind']) is str and row['kind'] in ROUTES and text(row['name'], 256)
             and row['availability'] in ('available', 'unavailable', 'unknown'), 'invalid_route')
        key = (row['kind'], row['name'])
        need(key not in seen, 'duplicate_route')
        seen.add(key)
    need({r['kind'] for r in routes} == set(ROUTES), 'all_route_kinds_required')
    P.routing_helper('context_packets').scan(P.canonical(request))


def package_state(path):
    path = P.no_links(path).resolve()
    need(path.is_dir(), 'loaded_package_unavailable')
    manifest = W.source_manifest(path)
    prefix = 'skills/' if 'skills/' + ENTRY in manifest else ''
    skills = {key[len(prefix):]: val for key, val in manifest.items()
              if key.startswith(prefix + 'omni-')}
    need({ENTRY, HELPER} <= set(skills), 'package_entry_missing')
    # Installed skill roots have no source revision. Their exact bytes can still
    # be compared with the verified checkout, without inventing Git provenance.
    git = W.git_identity(path) if prefix else {'head': None, 'status': None}
    return {'path': str(path), 'revision': git['head'],
            'tree_status': 'unknown' if git['status'] is None else 'clean' if git['status'] == '' else 'dirty',
            'manifest_sha256': P.digest(P.canonical(manifest)),
            'skill_sha256': P.digest(P.canonical(skills)), 'layout': 'repository' if prefix else 'installed'}, git


def _boundary(request, binding, provider):
    result = {'mode': 'advisory', 'inventory_assurance': 'host_reported', 'loading': 'host_reported',
              'routes': copy.deepcopy(request['routes']), 'qualification_reference': None,
              'findings': ['host_boundary_not_verified']}
    if provider is None:
        return result
    try:
        binding = dict(binding, challenge=secrets.token_hex(24))
        # The operator constructs this provider outside request/artifact data.
        # It must authenticate the inventory and actual denied-write probes at
        # the credential/capability boundary before returning this observation.
        observed = provider.verify_entry(copy.deepcopy(binding))
        fields(observed, ('binding_sha256', 'loaded_package_path', 'routes', 'denied_probes', 'qualification_reference'))
        need(observed['binding_sha256'] == P.digest(P.canonical(binding))
             and observed['loaded_package_path'] == binding['loaded_package']['path']
             and observed['routes'] == request['routes'] and text(observed['qualification_reference']), 'host_observation_mismatch')
        probes = observed['denied_probes']
        need(type(probes) is list and len(probes) <= 128, 'invalid_host_probes')
        verified = set()
        for probe in probes:
            fields(probe, ('kind', 'name', 'outcome', 'evidence_reference'))
            key = (probe['kind'], probe['name'])
            need(all(text(v, 256) for v in key) and key not in verified and probe['outcome'] == 'denied'
                 and text(probe['evidence_reference']), 'invalid_host_probe')
            verified.add(key)
        available = {(r['kind'], r['name']) for r in request['routes'] if r['availability'] == 'available'}
        need(verified == available and all(r['availability'] != 'unknown' for r in request['routes']),
             'host_route_coverage_incomplete')
        result.update(mode='enforced', inventory_assurance='qualified_host_provider', loading='qualified_host_provider',
                      qualification_reference=observed['qualification_reference'], findings=[])
    except (ValueError, OSError, AttributeError, KeyError, TypeError):
        result['findings'] = ['host_observation_unavailable_or_incomplete']
    return result


def check(root, request, *, provider=None, _resume=False):
    """Inspect an explicit loaded path before authoring. Never install or load it."""
    validate(request)
    root, project = P.load_project(root)
    with P.validation_operation(root):
        expected, git = package_state(W.source_root())
        findings = []
        try:
            loaded, _ = package_state(request['loaded_package_path'])
        except (ValueError, OSError, KeyError, TypeError):
            loaded = {'path': request['loaded_package_path'], 'revision': None, 'tree_status': 'unknown',
                      'manifest_sha256': None, 'skill_sha256': None, 'layout': 'unknown'}
            findings.append('loaded_package_unavailable_or_invalid')
        expectation = request['source_expectation']
        verification = {}
        try:
            _, verification = W.source_expectation(root, request, git, Path(expected['path']), resume=_resume)
            release = {'current_checkout': 'checkout_recorded_latest_unverified',
                       'offline_snapshot': 'offline_bytes_verified', 'pinned_revision': 'pinned_revision_verified',
                       'latest_main': 'latest_main_verified_at_recorded_entry' if _resume else 'latest_main_verified_at_entry'}[expectation['kind']]
        except (ValueError, OSError, KeyError, TypeError):
            release = 'unverified'
            findings.append('requested_release_unverified')
        if loaded['skill_sha256'] != expected['skill_sha256']:
            findings.append('loaded_package_differs_from_verifier')
        if loaded['revision'] is not None and expectation.get('revision') is not None and loaded['revision'] != expectation['revision']:
            findings.append('loaded_revision_differs_from_requested')
        if expectation.get('kind') in ('pinned_revision', 'latest_main') and loaded['tree_status'] == 'dirty':
            findings.append('loaded_package_has_local_changes')
        binding = {'project_id': project['id'], 'host': request['host'], 'loaded_package': loaded,
                   'verifier_package': expected, 'source_expectation': expectation, 'routes': request['routes']}
        boundary = _boundary(request, binding, provider)
        report = {'schema_version': 1, 'kind': 'analyst_host_entry_check', 'project_id': project['id'],
                  'status': 'source_mismatch' if findings else 'source_ready', 'host': request['host'],
                  'loaded_package': loaded, 'verifier_package': expected, 'requested_release': expectation,
                  'release_status': release, 'verification_pins': verification,
                  'host_boundary': boundary, 'findings': findings,
                  'current_release_test': not _resume and not findings and expectation.get('kind') == 'latest_main'
                                          and boundary['loading'] == 'qualified_host_provider',
                  'execution_authorized': False, 'publication_authorized': False,
                  'next_action': 'Reconcile the reported loaded path and requested source through the approved update procedure.'
                                 if findings else 'Continue the engagement through its existing phase and candidate gates.'}
    return report


def prepare(root, request, *, provider=None):
    """Retain a source/host observation once, including an actionable mismatch."""
    validate(request)
    root, project = P.load_project(root)
    path = 'evidence/host-entry-' + request['id'] + '.json'
    if (root / path).exists():
        record, raw = P.read_json(P.relative_file(root, path))
        need(type(record) is dict and record.get('kind') == 'analyst_host_entry' and record.get('project_id') == project['id']
             and record.get('request') == request, 'immutable_record_conflict')
        need(record.get('sha256') == P.digest(P.canonical({k:v for k,v in record.items() if k != 'sha256'})), 'record_changed')
        report = check(root, request, provider=provider, _resume=True)
        if any(record['entry'].get(key) != report[key] for key in ('loaded_package', 'verifier_package', 'verification_pins')):
            report['status'] = 'source_mismatch'
            report['findings'].append('recorded_package_changed')
            report['current_release_test'] = False
            report['next_action'] = 'Preserve this entry and record a new ID after reconciling the source change.'
        return {'status': 'reused', 'record': {'path': path, 'sha256': P.digest(raw)}, 'entry': report}
    report = check(root, request, provider=provider)
    record = {'schema_version': 1, 'kind': 'analyst_host_entry', 'project_id': project['id'],
              'request': copy.deepcopy(request), 'entry': report}
    record['sha256'] = P.digest(P.canonical(record))
    P.write_json(root / path, record)
    return {'status': 'recorded', 'record': {'path': path, 'sha256': P.digest(P.read_bytes(P.relative_file(root, path)))}, 'entry': report}


def verify_record(root, pointer, host, expectation, *, resume=False):
    """Recheck exact local source bytes. Retained host claims are historical only."""
    fields(pointer, ('path', 'sha256'))
    need(type(pointer['path']) is str and re.fullmatch(r'evidence/host-entry-[a-z][a-z0-9-]{0,63}\.json', pointer['path'])
         and type(pointer['sha256']) is str and SHA.fullmatch(pointer['sha256']), 'record_pin_required')
    value, raw = P.read_json(P.relative_file(root, pointer['path']))
    need(type(value) is dict, 'record_changed')
    need(P.digest(raw) == pointer['sha256'] and value.get('kind') == 'analyst_host_entry'
         and value.get('project_id') == P.load_project(root)[1]['id'], 'record_changed')
    request = value['request']
    need(request['host'] == host and request['source_expectation'] == expectation, 'startup_binding_mismatch')
    report = check(root, request, _resume=resume)
    need(value['entry']['status'] == 'source_ready' and report['status'] == 'source_ready', 'source_not_ready')
    for key in ('loaded_package', 'verifier_package', 'verification_pins'):
        need(value['entry'][key] == report[key], 'source_changed')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('check', 'prepare'))
    parser.add_argument('--project', required=True)
    parser.add_argument('--request', required=True, help='Engagement-relative JSON request')
    args = parser.parse_args()
    try:
        root, _ = P.load_project(args.project)
        request, _ = P.read_json(P.relative_file(root, args.request))
        result = {'check': check, 'prepare': prepare}[args.operation](root, request)
        print(P.canonical(result).decode())
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        parser.exit(1, 'host_entry.invalid_request_or_unavailable_source\n')


if __name__ == '__main__':
    raise SystemExit(main())
