"""Pin a migration's source behavior and compare supplied candidate observations."""
import argparse
import importlib.util
import json
from pathlib import Path


def _module(filename):
    loader = importlib.util.spec_from_file_location(
        'oaa_fidelity_' + filename, Path(__file__).with_name(filename + '.py'))
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


G = _module('stage_gates')
P = G._helpers(None)


def need(ok, code):
    if not ok:
        raise ValueError('migration_fidelity.' + code)


def fields(value, required, optional=()):
    need(type(value) is dict and set(required) <= value.keys() <= set(required) | set(optional), 'fields')


def rows(value, key='id'):
    need(type(value) is list and len(value) <= 1024, 'rows')
    indexed = {}
    for row in value:
        need(type(row) is dict and G._ident(row.get(key)) and row[key] not in indexed, 'unique_' + key)
        indexed[row[key]] = row
    return indexed


def names(value, *, empty=False):
    need(type(value) is list and len(value) <= 1024 and (empty or value)
         and all(G._text(key, 1024) for key in value) and len(value) == len(set(value)), 'unique_names')
    return set(value)


class Evidence:
    """Use the same descriptor-relative regular-file reads as the stage journal."""
    def __init__(self, fd):
        self.fd = fd
        self.pins = {}
        self.size = 0

    def capture(self, path, *, document=False):
        G._relative(path)
        if not document and path in self.pins:
            return
        need(len(self.pins) < 512, 'file_limit')
        raw = G._read(self.fd, path, P.MAX_BYTES)
        need(bool(raw.strip()), 'empty_evidence')
        self.size += len(raw)
        need(self.size <= 32 * 1024 * 1024, 'byte_limit')
        self.pins[path] = {'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)}
        if document:
            return G._json(raw, P)

    def references(self, paths):
        for path in sorted(names(paths)):
            self.capture(path)

    def manifest(self):
        return [self.pins[path] for path in sorted(self.pins)]


def _states(value, controls):
    need(type(value) is dict and value.keys() <= controls.keys(), 'unknown_control_state')


def _baseline(fd, path):
    evidence = Evidence(fd)
    source = evidence.capture(path, document=True)
    fields(source, ('schema_version', 'source_evidence', 'views', 'controls', 'cases', 'deviations'),
           ('no_controls_evidence', 'unresolved'))
    need(type(source['schema_version']) is int and source['schema_version'] == 1, 'source_version')
    evidence.references(source['source_evidence'])
    controls = rows(source['controls'])
    views = rows(source['views'])
    cases = rows(source['cases'])
    deviations = rows(source['deviations'], 'control_id')
    unresolved = rows(source.get('unresolved', []))
    need(bool(cases) or bool(unresolved), 'source_cases_required')
    need(bool(views), 'source_views_required')
    components, visible_controls = set(), set()
    for view in views.values():
        fields(view, ('id', 'title', 'layout', 'components', 'controls', 'evidence'))
        need(G._text(view['title']) and G._text(view['layout']), 'source_view_description')
        components.update(names(view['components']))
        visible_controls.update(names(view['controls'], empty=True))
        evidence.references(view['evidence'])
    need(visible_controls == controls.keys(), 'source_view_controls')
    if not controls and not unresolved:
        evidence.references(source.get('no_controls_evidence'))
    else:
        need('no_controls_evidence' not in source, 'contradictory_control_inventory')
    for item in unresolved.values():
        fields(item, ('id', 'reason', 'evidence'))
        need(G._text(item['reason']), 'unresolved_reason')
        evidence.references(item['evidence'])
    for control in controls.values():
        fields(control, ('id', 'label', 'kind', 'default', 'affected', 'exempt', 'evidence'))
        need(G._text(control['label']) and G._text(control['kind']), 'control_label_and_kind')
        affected = names(control['affected'])
        exempt = names(control['exempt'], empty=True)
        need(not affected & exempt and (affected | exempt) <= components, 'source_control_scope')
        evidence.references(control['evidence'])
    coverage = {key: set() for key in controls}
    tested_components = set()
    for case in cases.values():
        fields(case, ('id', 'controls', 'action', 'persona', 'state', 'outputs', 'evidence'), ('context',))
        selected = names(case['controls'], empty=True)
        _states(case['state'], controls)
        need(selected <= case['state'].keys() and G._text(case['action'])
             and G._text(case['persona']), 'case_action_context')
        need('context' not in case or type(case['context']) is dict and case['context'], 'case_context')
        outputs = case['outputs']
        need(type(outputs) is dict and outputs and outputs.keys() <= components, 'source_outputs')
        tested_components.update(outputs)
        for key in selected:
            control = controls[key]
            need(set(control['affected'] + control['exempt']) <= outputs.keys(), 'source_output_scope')
            coverage[key].add(P.canonical(case['state'][key]) == P.canonical(control['default']))
        evidence.references(case['evidence'])
    need(all(states == {True, False} for states in coverage.values()), 'default_and_changed_case_required')
    for key, decision in deviations.items():
        fields(decision, ('control_id', 'disposition', 'reason', 'decision_evidence'))
        need(key in controls and decision['disposition'] in ('omit', 'adapt') and G._text(decision['reason']),
             'scope_deviation')
        evidence.references(decision['decision_evidence'])
    # A manifest cannot act as its own original source, observation or user decision.
    refs = list(source['source_evidence']) + source.get('no_controls_evidence', [])
    for record in [*views.values(), *controls.values(), *cases.values(), *unresolved.values(), *deviations.values()]:
        refs.extend(record.get('evidence', record.get('decision_evidence', [])))
    need(path not in refs, 'self_referential_evidence')
    pins = evidence.manifest()
    return {'schema_version': 1, 'baseline_path': path, 'baseline_sha256': P.digest(P.canonical(pins)),
            'pins': pins, 'control_ids': sorted(controls), 'case_ids': sorted(cases),
            'views': source['views'], 'controls': source['controls'], 'cases': source['cases'], 'deviations': source['deviations'],
            'uncovered_components': sorted(components - tested_components),
            'unresolved': source.get('unresolved', [])}


def baseline(project_root, baseline_relpath):
    """Return the reviewed denominator and an identity covering its original files."""
    with G._root_fd(project_root, P) as (_, fd):
        return _baseline(fd, baseline_relpath)


def parity(project_root, baseline_relpath, observations_relpath, candidate_sha256):
    """The integrating gate supplies the current frozen candidate's digest."""
    with G._root_fd(project_root, P) as (_, fd):
        base = _baseline(fd, baseline_relpath)
        evidence = Evidence(fd)
        observed = evidence.capture(observations_relpath, document=True)
        fields(observed, ('schema_version', 'baseline_sha256', 'candidate_sha256', 'controls', 'cases'))
        need(type(observed['schema_version']) is int and observed['schema_version'] == 1, 'observation_version')
        need(G._hash(candidate_sha256) and observed['candidate_sha256'] == candidate_sha256, 'stale_candidate')
        need(observed['baseline_sha256'] == base['baseline_sha256'], 'stale_source')
        controls = rows(observed['controls'])
        cases = rows(observed['cases'])
        need(controls.keys() <= set(base['control_ids']) and cases.keys() <= set(base['case_ids']), 'unexpected_observation')
        omitted = {d['control_id'] for d in base['deviations'] if d['disposition'] == 'omit'}
        findings = [{'kind': 'source_unresolved', 'id': row['id']} for row in base['unresolved']]
        findings.extend({'kind': 'missing_source_expectation', 'id': key} for key in base['uncovered_components'])
        for key in sorted(set(base['control_ids']) - controls.keys() - omitted):
            findings.append({'kind': 'missing_control', 'id': key})
        for control in controls.values():
            fields(control, ('id', 'target_locator', 'evidence'), ('source_views',))
            need(G._text(control['target_locator']), 'target_control_locator')
            required_views = {v['id'] for v in base['views'] if control['id'] in v['controls']}
            observed_views = (names(control['source_views'], empty=True) if 'source_views' in control
                              else required_views if len(required_views) == 1 else set())
            need(observed_views <= required_views, 'unexpected_control_view')
            for view_id in sorted(required_views - observed_views):
                findings.append({'kind': 'missing_control_in_view', 'id': control['id'], 'view_id': view_id})
            evidence.references(control['evidence'])
        need(len({c['target_locator'] for c in controls.values()}) == len(controls), 'duplicate_target_locator')
        dispositions = []
        for expected in base['cases']:
            key = expected['id']
            actual = cases.get(key)
            excepted = bool(expected['controls']) and set(expected['controls']) <= omitted
            if actual is None:
                if excepted:
                    dispositions.append({'case_id': key, 'status': 'excepted', 'control_ids': expected['controls']})
                else:
                    findings.append({'kind': 'missing_case', 'id': key})
                continue
            fields(actual, ('id', 'persona', 'state', 'outputs', 'evidence'), ('context',))
            need(G._text(actual['persona']) and type(actual['state']) is dict and type(actual['outputs']) is dict,
                 'target_case_context')
            evidence.references(actual['evidence'])
            mismatches = []
            if actual['persona'] != expected['persona']:
                mismatches.append('persona')
            if P.canonical(actual.get('context')) != P.canonical(expected.get('context')):
                mismatches.append('context')
            # The reviewed omission may remove a control from the target. A mixed
            # case still has to reproduce the source outputs for its retained task.
            expected_state = {k: v for k, v in expected['state'].items() if k not in omitted}
            observed_state = {k: v for k, v in actual['state'].items() if k not in omitted}
            if P.canonical(observed_state) != P.canonical(expected_state):
                mismatches.append('state')
            if P.canonical(actual['outputs']) != P.canonical(expected['outputs']):
                mismatches.append('outputs')
            if mismatches:
                findings.append({'kind': 'case_mismatch', 'id': key, 'fields': mismatches})
            else:
                dispositions.append({'case_id': key, 'status': 'matched'})
        if not cases and dispositions and all(row['status'] == 'excepted' for row in dispositions):
            findings.append({'kind': 'no_compared_case', 'id': 'candidate'})
        source_paths = {pin['path'] for pin in base['pins']}
        target_paths = set(evidence.pins)
        target_refs = [ref for row in [*controls.values(), *cases.values()] for ref in row['evidence']]
        need(not source_paths & target_paths and observations_relpath not in target_refs, 'independent_target_evidence')
        pins = sorted(base['pins'] + evidence.manifest(), key=lambda pin: pin['path'])
        return {'schema_version': 1, 'baseline_sha256': base['baseline_sha256'], 'candidate_sha256': candidate_sha256,
                'status': 'partial' if findings else 'matched', 'findings': findings, 'cases': dispositions,
                'deviations': base['deviations'], 'pins': pins, 'qualification': 'supplied_observations_only',
                'native_verified': False, 'acceptance_authority': False}


def frozen_candidate(project_root, baseline_relpath=None):
    """Recompute journal integrity and check the exact retained candidate bytes."""
    with G._root_fd(project_root, P) as (root, fd):
        project, _, journal = G._context(root, fd, P)
        state = G._replay(root, project, journal, P)
        candidate = state['candidate']
        need(candidate is not None and G._fresh(fd, candidate, P), 'current_frozen_candidate_required')
        if baseline_relpath is not None:
            offer = state['current']['options']['payload']
            reviewed = offer.get('evidence', {}).get('source_baseline')
            need(isinstance(reviewed, dict) and reviewed['path'] == baseline_relpath, 'candidate_baseline_required')
            base = _baseline(fd, baseline_relpath)
            need(reviewed in base['pins'] and offer.get('baseline_sha256') == base['baseline_sha256'],
                 'candidate_baseline_changed')
        return candidate['payload']['candidate_sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('baseline').add_argument('--baseline', required=True)
    compare = commands.add_parser('parity')
    compare.add_argument('--baseline', required=True)
    compare.add_argument('--observations', required=True)
    args = parser.parse_args()
    if args.command == 'baseline':
        result = baseline(args.project, args.baseline)
    else:
        result = parity(args.project, args.baseline, args.observations, frozen_candidate(args.project, args.baseline))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
