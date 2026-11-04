"""Bounded work preparation, preflight and host-reported usage. Standard library only.

These helpers do not dispatch workers, authenticate observations, select a model,
cache live data or authorize publication. Historical engagements remain opt-in.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile

_spec = importlib.util.spec_from_file_location('efficiency_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
POLICIES = {'legacy-index-v1', 'bounded-context-v1'}
USAGE_FIELDS = {'input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens'}


def operations():
    return P.routing_helper('task_operations')


def atomic_json(path, value):
    path = P.no_links(path)
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    P.need(len(raw) <= P.MAX_BYTES, 'Efficiency record exceeds project size limit')
    fd, temporary = tempfile.mkstemp(prefix='.efficiency-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(root, request):
    P.need(type(request) is dict and set(request) == {'policy', 'reason'}, 'Expected policy and reason')
    P.need(request['policy'] in POLICIES, 'Unknown context policy')
    P.routing_helper().text(request['reason'])
    ops = operations()
    with ops.locked(root) as (root, project, state):
        previous = project.get('context_policy', 'legacy-index-v1')
        if previous == request['policy']:
            return {'status': 'unchanged', 'policy': previous, 'authority_changed': False}
        P.need(not any(r['status'] == 'active' for r in state['attempts']),
               'Checkpoint active workers before changing context policy')
        history = project.setdefault('context_policy_history', [])
        history.append({'previous': previous, 'policy': request['policy'], 'reason': request['reason'],
                        'recorded_at': ops.now(), 'prior_project_sha256': P.digest(P.canonical(project))})
        project['context_policy'] = request['policy']
        atomic_json(root / 'project.json', project)
        return {'status': 'configured', 'policy': request['policy'], 'previous': previous,
                'authority_changed': False, 'history_count': len(history)}


def prepare(root, request):
    """Compute packet bindings from explicit task fields; never guess scope or approval."""
    required = {'role', 'inputs', 'assignment', 'output'}
    P.need(type(request) is dict and set(request) == required, 'Expected role, inputs, assignment and output')
    root, _ = P.load_project(root)
    assignment = copy.deepcopy(request['assignment'])
    P.need(type(assignment) is dict and 'input_bindings' not in assignment and 'dependencies' not in assignment,
           'Supply dependency_paths; bindings are generated from current evidence')
    dependencies = assignment.pop('dependency_paths', [])
    P.routing_helper().strings(dependencies)
    index = P.packet_data(root, request['role'], request['inputs'])
    bindings = {r['path']: r['sha256'] for r in index['inputs']}
    P.need(set(dependencies) <= set(bindings), 'Dependency paths must be included in packet inputs')
    assignment.update(input_bindings=bindings, dependencies={p: bindings[p] for p in dependencies})
    value = P.packet_data(root, request['role'], request['inputs'], assignment)
    # No random identity participates in semantic no-op detection.
    P.routing_helper().output_path(request['output'])
    P.need(request['output'].startswith('tasks/') and request['output'].endswith('.json'),
           'Prepared packet belongs in tasks as a new JSON file')
    destination = P.no_links(root / request['output'])
    if destination.exists():
        saved = P.read_json(destination)[0]
        P.need(saved == value, 'Packet path already contains different work; use a new version')
        status = 'reused'
    else:
        P.write_json(destination, value)
        status = 'prepared'
    return {'status': status, 'packet': request['output'], 'packet_sha256': P.digest(destination.read_bytes()),
            'assignment_sha256': value['assignment_sha256'], 'input_bytes': value['input_bytes'],
            'task_id': value['task_id'], 'agents_dispatched': False}


def preflight(root, request):
    P.need(type(request) is dict and set(request) <= {'action', 'packet', 'attempt_id', 'context_receipt'} and
           bool(request), 'Unknown preflight fields')
    root, project = P.load_project(root)
    blockers, observations = [], {}
    if 'action' in request:
        action = request['action']
        P.need(action in {'access', 'analysis', 'narrative', 'brief', 'options', 'choose', 'design', 'build', 'review', 'release'},
               'Unknown preflight action')
        try:
            phase = P.routing_helper('delivery_workflow').phase_check(root, action)
            blockers.extend({'area': 'phase', 'detail': f} for f in phase.get('findings', []))
            observations['phase'] = phase['status']
        except (ValueError, OSError, KeyError) as exc:
            # Review/release have stage gates but are not execution-guidance phases.
            if action not in {'review', 'release'}:
                blockers.append({'area': 'phase', 'detail': str(exc)})
        try:
            P.stage_require(root, action)
            observations['stage'] = 'ready'
        except (ValueError, OSError, KeyError) as exc:
            blockers.append({'area': 'stage', 'detail': str(exc)})
    ops = operations()
    if 'packet' in request:
        try:
            assignment, pin = ops.read_packet(root, project, request['packet'])
            observations['packet'] = {'sha256': pin, 'task_id': assignment['task_id']}
        except (ValueError, OSError, KeyError) as exc:
            blockers.append({'area': 'packet', 'detail': str(exc)})
    if 'attempt_id' in request:
        try:
            observations['dispatch'] = ops.prepare_dispatch(root, {'attempt_id': request['attempt_id']})
        except (ValueError, OSError, KeyError) as exc:
            blockers.append({'area': 'dispatch', 'detail': str(exc)})
    if 'context_receipt' in request:
        try:
            report = P.routing_helper('context_packets').check(root, request['context_receipt'], request.get('packet'))
            observations['context'] = report
            if report['status'] != 'consistent':
                blockers.extend({'area': 'context', 'detail': str(f)} for f in report.get('findings', ['Context invalid']))
        except (ValueError, OSError, KeyError) as exc:
            blockers.append({'area': 'context', 'detail': str(exc)})
    elif project.get('context_policy') == 'bounded-context-v1' and 'packet' in request and 'attempt_id' not in request:
        blockers.append({'area': 'context', 'detail': 'Build a bounded context receipt before managed dispatch'})
    unique = {P.digest(P.canonical(b)): b for b in blockers}
    return {'status': 'blocked' if unique else 'ready', 'blockers': list(unique.values()),
            'observations': observations, 'agents_dispatched': False, 'publication_authorized': False,
            'next_action': 'Resolve the listed areas together; unchanged checks need no new model pass' if unique
                           else 'Continue through the guarded action using current evidence'}


def record_usage(root, request):
    required = {'attempt_id', 'observation_id', 'host_run_reference', 'context_mode', 'evidence'}
    P.need(type(request) is dict and required <= set(request) <= required | {'usage', 'elapsed_ms', 'host_instruction_bytes'},
           'Invalid usage observation fields')
    for key in ('attempt_id', 'observation_id', 'host_run_reference'):
        P.routing_helper().text(request[key])
    P.need(request['context_mode'] in {'fresh', 'inherited', 'unknown'}, 'Unknown context mode')
    usage = request.get('usage')
    P.need(usage is None or (type(usage) is dict and bool(usage) and set(usage) <= USAGE_FIELDS), 'Unknown usage fields')
    for value in [*(usage or {}).values(), request.get('elapsed_ms'), request.get('host_instruction_bytes')]:
        P.need(value is None or (type(value) is int and 0 <= value < 2**63), 'Usage values must be observed nonnegative integers or null')
    ops = operations()
    with ops.locked(root) as (root, project, state):
        record = ops.attempt(state, request['attempt_id'])
        P.need(record.get('dispatch') and record['dispatch']['host_run_reference'] == request['host_run_reference'],
               'Usage must name the recorded host invocation')
        evidence = request['evidence']
        P.need(type(evidence) is dict and set(evidence) == {'path', 'sha256'}, 'Pinned host evidence required')
        P.need(P.digest(P.relative_file(root, evidence['path']).read_bytes()) == evidence['sha256'], 'Usage evidence changed')
        item = dict(copy.deepcopy(request), assurance='host_reported', billing_verified=False)
        existing = record.get('usage_observation')
        P.need(existing is None or existing == item, 'Invocation already has an immutable usage observation; do not double count')
        P.need(not any(a is not record and a.get('usage_observation', {}).get('host_run_reference') == request['host_run_reference']
                       for a in state['attempts']), 'Host invocation usage already recorded on another attempt; do not double count')
        record['usage_observation'] = item
        return item


def retry_key(root, record, error_family):
    assignment = record['assignment']
    existing_outputs = {p: P.digest(P.relative_file(root, p).read_bytes()) for p in assignment['outputs'] if (root / p).exists()}
    inputs = {p: P.digest(P.relative_file(root, p).read_bytes()) for p in assignment['input_bindings']}
    # Task/attempt names and narrative wording cannot reset an unchanged-state loop.
    state = {'inputs': inputs, 'outputs': existing_outputs, 'output_paths': sorted(assignment['outputs']),
             'scope_ids': sorted(assignment['scope_ids']), 'stage': assignment['stage'], 'error_family': error_family}
    packet = P.read_json(P.relative_file(root, record['packet']))[0]
    state['intent'] = {k: packet.get('design_context', {}).get(k) for k in ('selected_intent', 'requirements', 'shared_constraint_ids')}
    if record.get('context'):
        context = P.read_json(P.relative_file(root, record['context']['receipt_path']))[0]
        # An actual evidence expansion can resolve a blocker; rewording a summary cannot.
        evidence = []
        for item in context['request']['evidence']:
            ranges = []
            for start, end in sorted(item['ranges']):
                if ranges and start <= ranges[-1][1] + 1:
                    ranges[-1][1] = max(ranges[-1][1], end)
                else:
                    ranges.append([start, end])
            evidence.append({'path': item['path'], 'sha256': item['sha256'], 'ranges': ranges})
        state['context_evidence'] = sorted(evidence, key=lambda e: (e['path'], e['sha256']))
    return P.digest(P.canonical(state))


def record_blocker(root, request):
    P.need(type(request) is dict and set(request) == {'attempt_id', 'event_id', 'error_family', 'detail'}, 'Invalid blocker event')
    for value in request.values():
        P.routing_helper().text(value)
        P.need(len(value) <= 2048, 'Blocker event too large; retain detailed evidence separately')
    ops = operations()
    with ops.locked(root) as (root, project, state):
        record = ops.attempt(state, request['attempt_id'])
        key = retry_key(root, record, request['error_family'])
        events = state.setdefault('blocker_events', [])
        old = next((e for e in events if e['event_id'] == request['event_id']), None)
        value = dict(request, state_sha256=key)
        P.need(old is None or old == value, 'Blocker event identity already used for another state')
        if old is None:
            events.append(value)
        count = sum(e['state_sha256'] == key for e in events)
        return {'status': 'stop' if count >= 2 else 'correction_available', 'state_sha256': key, 'attempts': count,
                'next_action': 'Resolve the missing evidence or decision; continue unrelated work' if count >= 2
                               else 'Apply one targeted correction; retain the finding'}


def require_no_loop(root, state, record):
    families = {e['error_family'] for e in state.get('blocker_events', [])}
    for family in families:
        key = retry_key(root, record, family)
        P.need(sum(e['state_sha256'] == key for e in state.get('blocker_events', [])) < 2,
               'Repeated unchanged blocker; resolve evidence or decision before redispatch: ' + family)


def report(root):
    ops = operations()
    with ops.locked(root) as (root, project, state):
        observations = [a['usage_observation'] for a in state['attempts'] if a.get('usage_observation')]
        totals = {k: None for k in USAGE_FIELDS}
        counts = {k: 0 for k in USAGE_FIELDS}
        stale = []
        for o in observations:
            evidence = o['evidence']
            try:
                P.need(P.digest(P.relative_file(root, evidence['path']).read_bytes()) == evidence['sha256'], 'stale')
            except (ValueError, OSError):
                stale.append(o['observation_id'])
                continue
            for key, value in (o.get('usage') or {}).items():
                if value is not None:
                    totals[key] = (totals[key] or 0) + value
                    counts[key] += 1
        return {'schema_version': 1, 'kind': 'oaa_efficiency_report', 'policy': project.get('context_policy', 'legacy-index-v1'),
                'task_count': len({a['task_id'] for a in state['attempts']}), 'attempt_count': len(state['attempts']),
                'dispatch_count': sum(bool(a.get('dispatch')) for a in state['attempts']), 'reuse_count': state['reuse_count'],
                'context_packet_bytes': sum(a.get('context', {}).get('task_bytes', 0) for a in state['attempts']),
                'context_expansions': sum(a.get('context', {}).get('mode') == 'delta' for a in state['attempts']),
                'blocker_event_count': len(state.get('blocker_events', [])), 'observed_usage': totals,
                'usage_coverage': counts, 'stale_usage_observations': stale, 'dollars': None,
                'qualification': 'Local operations and host-reported observations. Byte counts are not tokens, costs or proof of isolation.'}
