"""Local OAA task reservations, evidence checkpoints and offline status.

No worker launch, liveness inference, billing, native validation or publication.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import html
import importlib.util
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location('operations_project', Path(__file__).with_name('analyst_project.py'))
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)
rules = ap.routing_helper()


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def locked(root):
    import fcntl
    root, project = ap.load_project(root)
    lock = ap.no_links(root / '.task-operations.lock')
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        path = ap.no_links(root / 'task-operations.json')
        state = ap.read_json(path)[0] if path.exists() else {
            'schema_version': 1, 'project_id': project['id'], 'max_workers': 2, 'attempts': [], 'reuse_count': 0}
        ap.need(state.get('schema_version') == 1 and state.get('project_id') == project['id'], 'Invalid task ledger')
        before = copy.deepcopy(state)
        yield root, project, state
        if state != before:
            state['updated_at'] = now()
            # The first ledger write must also be atomic while holding the lock.
            import tempfile
            import json
            payload = json.dumps(state, indent=2, allow_nan=False).encode()
            ap.need(len(payload) <= ap.MAX_BYTES, 'Task ledger exceeds the readable size limit; retain it and start a linked scope')
            fd_tmp, temp = tempfile.mkstemp(prefix='.operations-', dir=root)
            try:
                with os.fdopen(fd_tmp, 'wb') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    finally:
        os.close(fd)


def capture(root, paths):
    rules.strings(paths, nonempty=True)
    return {path: ap.digest(ap.relative_file(root, path).read_bytes()) for path in paths}


def read_packet(root, project, path):
    packet, raw = ap.read_json(ap.relative_file(root, path))
    ap.need(packet.get('kind') == 'analyst_task_packet' and packet.get('project_id') == project['id'], 'Wrong project packet')
    assignment = rules.bind_assignment(packet.get('assignment'), task_id=packet['task_id'], role=packet['role'])
    ap.need(packet.get('assignment_sha256') == rules.fingerprint(assignment), 'Assignment fingerprint differs')
    inputs = {r['path']: r['sha256'] for r in packet['inputs']}
    ap.need(len(inputs) == len(packet['inputs']) and assignment['input_bindings'] == inputs, 'Packet input bindings differ')
    size = 0
    for record in packet['inputs']:
        source = ap.relative_file(root, record['path'])
        size += source.stat().st_size
        ap.need(size <= ap.PACKET_BYTES, 'Packet input budget exceeded')
        raw_input = source.read_bytes()
        ap.need(ap.digest(raw_input) == record['sha256'], 'Packet inputs changed; prepare a revised assignment')
        ap.need(type(record['bytes']) is int and record['bytes'] == len(raw_input), 'Packet input size differs')
    ap.need(packet.get('input_bytes') == size, 'Packet total input size differs')
    for record in project['sources'] + project['artifacts']:
        if record['path'] in inputs:
            ap.need(record['sha256'] == inputs[record['path']], 'Registered source changed')
    if project.get('dma_import') and project['dma_import'].get('catalog_path') in inputs:
        upstream = project['dma_import']
        _, original = ap.read_json(upstream['original_path'])
        ap.need(ap.digest(original) == upstream['original_sha256'], 'Selected DMA handoff changed')
    ap.need(set(assignment['dependencies'].values()) <= set(inputs.values()), 'Unbound dependency version')
    ap.need(not rules.outputs_overlap(assignment['outputs'], list(inputs)) and
            not any(p.casefold().startswith(('inputs/', 'contracts/', 'tasks/', 'evidence/')) for p in assignment['outputs']), 'Outputs overlap retained evidence')
    ap.need(not rules.outputs_overlap(assignment['outputs'], [r['path'] for r in project['sources']]), 'Outputs overlap registered source evidence')
    return assignment, ap.digest(raw)


def attempt(state, identity):
    rules.text(identity)
    result = next((a for a in state['attempts'] if a['attempt_id'] == identity), None)
    ap.need(result is not None, 'Unknown task attempt')
    return result


def current(root, record):
    try:
        return bool(record['outputs']) and capture(root, list(record['outputs'])) == record['outputs']
    except (ValueError, OSError):
        return False


def claim(root, request):
    ap.need(set(request) <= {'attempt_id', 'packet', 'execution_mode'} and {'attempt_id', 'packet'} <= set(request), 'Invalid claim fields')
    rules.text(request['attempt_id'])
    mode = request.get('execution_mode', 'specialist')
    ap.need(mode in {'inline', 'specialist'}, 'Invalid execution mode')
    with locked(root) as (root, project, state):
        assignment, packet_sha = read_packet(root, project, request['packet'])
        revision = rules.fingerprint(assignment)
        active = [a for a in state['attempts'] if a['status'] == 'active']
        for record in active:
            if record['task_id'] == assignment['task_id']:
                ap.need(record['revision'] == revision, 'Checkpoint the active attempt before revising scope')
                return {'action': 'already_active', 'attempt_id': record['attempt_id'],
                        'qualification': 'Reuse the known host worker; unknown liveness is not permission to replace it'}
            ap.need(not rules.outputs_overlap(assignment['outputs'], record['assignment']['outputs']), 'Output already owned by active work')
        for record in reversed(state['attempts']):
            if record['task_id'] == assignment['task_id'] and record['revision'] == revision and record['status'] == 'outputs_recorded' and current(root, record):
                state['reuse_count'] += 1
                return {'action': 'reuse', 'attempt_id': record['attempt_id'], 'outputs': record['outputs'],
                        'qualification': 'Current files reused; prior validation status is unchanged'}
        ap.need(mode == 'inline' or sum(a['execution_mode'] == 'specialist' for a in active) < state['max_workers'], 'Specialist concurrency limit reached')
        ap.need(all(a['attempt_id'] != request['attempt_id'] for a in state['attempts']), 'Attempt ID already used')
        ap.need(len(state['attempts']) < 20000, 'Task history limit reached')
        previous = next((a['attempt_id'] for a in reversed(state['attempts']) if a['task_id'] == assignment['task_id'] and a['revision'] == revision and a['status'] == 'interrupted'), None)
        record = {'attempt_id': request['attempt_id'], 'task_id': assignment['task_id'], 'revision': revision,
                  'assignment': assignment, 'packet': request['packet'], 'packet_sha256': packet_sha,
                  'status': 'active', 'execution_mode': mode, 'started_at': now(), 'outputs': {},
                  'resumes_attempt_id': previous, 'dispatch': None}
        state['attempts'].append(record)
        return {'action': 'dispatch', 'attempt_id': record['attempt_id'], 'revision': revision,
                'resumes_attempt_id': previous, 'qualification': 'Reservation only; the host must invoke a bounded worker'}


def prepare_dispatch(root, request):
    ap.need(set(request) == {'attempt_id'}, 'Invalid dispatch preflight fields')
    with locked(root) as (root, project, state):
        record = attempt(state, request['attempt_id'])
        ap.need(record['status'] == 'active', 'Dispatch needs an active reservation')
        assignment, pin = read_packet(root, project, record['packet'])
        ap.need(assignment == record['assignment'] and pin == record['packet_sha256'], 'Reserved packet changed')
        return {'status': 'ready', 'attempt_id': record['attempt_id'], 'agents_dispatched': False}


def record_dispatch(root, request):
    ap.need(set(request) == {'attempt_id', 'host_run_reference', 'observed_model', 'observed_effort', 'requested_model',
                            'requested_effort', 'execution_mode', 'fallback_reason'}, 'Invalid dispatch fields')
    with locked(root) as (root, project, state):
        record = attempt(state, request['attempt_id'])
        ap.need(record['status'] == 'active', 'Dispatch needs an active reservation')
        assignment, packet_sha = read_packet(root, project, record['packet'])
        ap.need(assignment == record['assignment'] and packet_sha == record['packet_sha256'], 'Reserved packet changed')
        ap.need(request['execution_mode'] == record['execution_mode'], 'Execution mode differs')
        rules.text(request['host_run_reference'])
        for key in ('observed_model', 'observed_effort', 'requested_model', 'requested_effort', 'fallback_reason'):
            if request[key] is not None:
                rules.text(request[key])
        if request['execution_mode'] == 'inline':
            rules.text(request['fallback_reason'])
        receipt = {**copy.deepcopy(request), 'assurance': 'host_reported', 'execution_verified': False}
        ap.need(record['dispatch'] is None or record['dispatch'] == receipt, 'Dispatch receipt is immutable')
        record['dispatch'] = receipt
        return receipt


def checkpoint(root, request):
    ap.need(set(request) == {'attempt_id', 'status', 'reason', 'outputs'}, 'Invalid checkpoint fields')
    ap.need(request['status'] in {'interrupted', 'outputs_recorded'}, 'Invalid checkpoint status')
    rules.text(request['reason']); rules.strings(request['outputs'])
    with locked(root) as (root, project, state):
        record = attempt(state, request['attempt_id'])
        ap.need(record['status'] == 'active', 'Checkpoint requires active work')
        ap.need(set(request['outputs']) <= set(record['assignment']['outputs']), 'Unassigned checkpoint output')
        outputs = capture(root, request['outputs']) if request['outputs'] else {}
        if request['status'] == 'outputs_recorded':
            assignment, pin = read_packet(root, project, record['packet'])
            ap.need(assignment == record['assignment'] and pin == record['packet_sha256'], 'Assignment changed during work')
            ap.need(set(outputs) == set(assignment['outputs']), 'Completed work requires every assigned output')
        record.update(status=request['status'], reason=request['reason'], outputs=outputs, checkpoint_at=now())
        return {'status': record['status'], 'outputs': outputs, 'native_verified': False}


def review_work(root, request):
    ap.need(type(request) is dict and {'attempt_id', 'action'} <= set(request)
            <= {'attempt_id', 'action', 'changes', 'dependency_state', 'result', 'correction_attempt_id'}, 'Invalid review request')
    with locked(root) as (root, project, state):
        record = attempt(state, request['attempt_id'])
        ap.need(record.get('assignment'), 'Review requires an explicit assignment')
        action = request['action']
        paths = record['assignment']['outputs']
        artifacts = capture(root, paths)
        assignment, pin = read_packet(root, project, record['packet'])
        ap.need(assignment == record['assignment'] and pin == record['packet_sha256'], 'Review assignment changed')
        if action == 'start':
            ap.need(record['status'] != 'outputs_recorded' or artifacts == record['outputs'], 'Review candidate differs from recorded checkpoint')
            ap.need('review' not in record, 'Review already started; use its existing result or revise')
            record['review'] = rules.start_review(assignment, artifacts, request.get('changes'), request.get('dependency_state', 'known'),
                                                 (record['dispatch'] or {}).get('host_run_reference'))
        elif action == 'record':
            ap.need(artifacts == record['review']['artifacts'], 'Candidate changed before review recording')
            record['review'] = rules.record_review(record['review'], request['result'])
        elif action == 'revise':
            ap.need(record['status'] == 'active' and record.get('corrects_attempt_id'), 'Reserve the correction attempt before revising')
            builder = (record['dispatch'] or {}).get('host_run_reference')
            ap.need(builder, 'Record the correction worker before revising the review')
            record['review'] = rules.revise_review(record['review'], artifacts, builder)
        elif action == 'correct':
            identity = request.get('correction_attempt_id')
            rules.text(identity)
            decision = rules.review_decision(record['review'], artifacts)
            ap.need(decision['action'] == 'correct', 'Collect all reviews before reserving correction')
            ap.need(not record.get('corrected_by_attempt_id'), 'Correction already reserved; reuse its recorded attempt')
            ap.need(not any(a['attempt_id'] == identity for a in state['attempts']), 'Correction attempt ID already used')
            active = [a for a in state['attempts'] if a['status'] == 'active' and a is not record]
            ap.need(all(not rules.outputs_overlap(assignment['outputs'], a['assignment']['outputs']) for a in active), 'Correction outputs already owned')
            ap.need(record['execution_mode'] == 'inline' or sum(a['execution_mode'] == 'specialist' for a in active) < state['max_workers'], 'Specialist concurrency limit reached')
            ap.need(len(state['attempts']) < 20000, 'Task history limit reached')
            successor = copy.deepcopy(record)
            successor.update(attempt_id=identity, status='active', outputs={}, started_at=now(), dispatch=None,
                             corrects_attempt_id=record['attempt_id'])
            for key in ('checkpoint_at', 'reason', 'review_decision', 'corrected_by_attempt_id'):
                successor.pop(key, None)
            if record['status'] == 'active':
                record.update(status='interrupted', reason='Correction moved to a separately reserved attempt', checkpoint_at=now())
            record['corrected_by_attempt_id'] = identity
            state['attempts'].append(successor)
            return {'action': 'dispatch', 'attempt_id': identity, 'findings': decision['findings'], 'agents_dispatched': False}
        else:
            ap.need(action == 'status', 'Unknown review action')
        decision = rules.review_decision(record['review'], artifacts)
        record['review_decision'] = decision
        return {'review': record['review'], 'decision': decision}


def status(root, output=None):
    with locked(root) as (root, project, state):
        latest = {a['task_id']: a for a in state['attempts']}
        rows = []
        for record in latest.values():
            assignment = record['assignment']
            stale = False
            try:
                value, pin = read_packet(root, project, record['packet'])
                stale = value != assignment or pin != record['packet_sha256']
            except (ValueError, OSError):
                stale = True
            if record['status'] == 'outputs_recorded' and not current(root, record):
                stale = True
            state_label = 'stale' if stale else ('reserved' if record['status'] == 'active' and not record['dispatch'] else record['status'])
            review = {'action': 'unverified'}
            if record.get('review') and not stale:
                try:
                    review = rules.review_decision(record['review'], capture(root, assignment['outputs']))
                except (ValueError, OSError):
                    review = {'action': 'stale'}
            rows.append({'task_id': record['task_id'], 'domain_id': assignment['domain_id'], 'stage': assignment['stage'],
                         'role': assignment['role'], 'status': state_label, 'authoring_mode': assignment['authoring_mode'],
                         'outputs': list(record['outputs']), 'unknowns': assignment['unknowns'], 'review_status': review['action'],
                         'next_action': 'Refresh changed evidence' if stale else review.get('reason') or
                            ('Invoke or locate the reserved host worker' if state_label == 'reserved' else
                             'Resume from checkpoint' if state_label == 'interrupted' else 'Review candidate outputs and outstanding decisions')})
        result = {'snapshot_at': now(), 'tasks': rows, 'reuse_count': state['reuse_count'], 'execution_verified': False,
                  'qualification': 'Offline snapshot. Reserved work is not execution; recorded outputs are not native validation or approval.'}
        if output:
            rules.output_path(output)
            destination = ap.no_links(root / output)
            ap.need(destination.parent.is_dir() and destination.suffix == '.html', 'Existing status directory and HTML path required')
            if destination.exists():
                ap.need(destination.read_text().startswith('<!doctype html><!-- oaa-task-status-v1 -->'), 'Do not overwrite unrelated HTML')
            esc = lambda value: html.escape(str(value), quote=True)
            from urllib.parse import quote
            def extras(row):
                links = []
                for path in row['outputs']:
                    href = quote(os.path.relpath(root / path, destination.parent), safe='/')
                    links.append('<a href="' + esc(href) + '">' + esc(path) + '</a>')
                return '<td>' + '<br>'.join(links) + '</td><td>' + '<br>'.join(esc(v) for v in row['unknowns']) + '</td>'
            body = ''.join('<tr>' + ''.join('<td>' + esc(row[key]) + '</td>' for key in ('domain_id', 'task_id', 'stage', 'role', 'status', 'authoring_mode', 'review_status', 'next_action')) + extras(row) + '</tr>' for row in rows)
            page = '<!doctype html><!-- oaa-task-status-v1 --><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'"><title>Task progress</title><style>body{font:18px system-ui;margin:2rem;line-height:1.5}main{max-width:1200px;margin:auto}table{border-collapse:collapse;min-width:800px}th,td{padding:12px;border:1px solid #ccd;text-align:left;vertical-align:top}.scroll{overflow:auto}small{color:#555}</style><main><h1>Task progress</h1><p>' + esc(result['qualification']) + '</p><small>Snapshot ' + esc(result['snapshot_at']) + '</small><div class="scroll"><table><tr>' + ''.join('<th>' + title + '</th>' for title in ('Domain', 'Task', 'Stage', 'Specialist', 'Progress', 'Candidate', 'Review', 'Next action', 'Recorded outputs', 'Open questions')) + '</tr>' + body + '</table></div></main></html>'
            ap.private_write(destination, page.encode(), replace=destination.exists())
            entry = ap.relative_file(root, 'START_HERE.md')
            link = '\n- [Task progress and recorded outputs](<' + quote(output, safe='/') + '>)\n'
            content = entry.read_text()
            if link not in content:
                ap.private_write(entry, (content + link).encode(), replace=True)
            result['html'] = output
        return result
