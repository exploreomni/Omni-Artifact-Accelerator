"""Host-neutral worker launch coordination over the existing task ledger.

An operator supplies a driver object; requests cannot select code, commands,
credentials or tools. This cooperating process boundary does not sandbox a host
or authenticate its observations. No installed adapter is assumed.
"""
import copy
import importlib.util
from pathlib import Path
import uuid
from contextlib import contextmanager
import fcntl
import os
import stat

_spec = importlib.util.spec_from_file_location('runtime_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
TERMINAL = {'completed', 'failed', 'cancelled', 'absent'}
STATES = TERMINAL | {'active', 'unknown'}


def binding_check(binding):
    fields = {'adapter_id', 'adapter_version', 'host_version', 'configuration_sha256',
              'tool_scope', 'context_mode', 'model', 'effort'}
    P.need(type(binding) is dict and set(binding) == fields, 'Invalid host binding')
    rules = P.routing_helper()
    for key in ('adapter_id', 'adapter_version', 'host_version'):
        rules.text(binding[key])
    import re
    P.need(type(binding['configuration_sha256']) is str and
           re.fullmatch('[a-f0-9]{64}', binding['configuration_sha256']), 'Pinned host configuration required')
    rules.strings(binding['tool_scope'])
    P.need(len(binding['tool_scope']) <= 100 and len(set(binding['tool_scope'])) == len(binding['tool_scope']), 'Invalid tool scope')
    P.need(binding['context_mode'] in {'fresh', 'inherited', 'unknown'}, 'Invalid context mode')
    for key in ('model', 'effort'):
        if binding[key] is not None:
            rules.text(binding[key])
    return copy.deepcopy(binding)


class Runtime:
    """Driver protocol: launch(payload), reconcile(launch_id); no dynamic loading.

    Drivers must implement bounded calls and return observations, not permission.
    Cancellation is performed by the operator/host, then reconciled here. Unknown
    liveness retains output ownership and never permits automatic replacement.
    """
    def __init__(self, root, driver, binding):
        self.root, _ = P.load_project(root)
        P.need(callable(getattr(driver, 'launch', None)) and callable(getattr(driver, 'reconcile', None)),
               'Operator-supplied launch and reconciliation driver required')
        self.driver = driver
        self.binding = binding_check(binding)
        self.binding_sha = P.digest(P.canonical(self.binding))
        self.ops = P.routing_helper('task_operations')

    def status(self, attempt_id):
        with self.ops.locked(self.root) as (_, _, state):
            record = self.ops.attempt(state, attempt_id)
            launch = copy.deepcopy(record.get('host_launch'))
        return {'attempt_id': attempt_id, 'launch': launch, 'execution_assurance': 'host_reported',
                'host_isolation_verified': False, 'publication_authorized': False,
                'next_action': ('reconcile_existing_invocation' if launch and launch['status'] not in TERMINAL
                                else 'checkpoint_observed_result' if launch else 'launch_reserved_work')}

    @contextmanager
    def _fence(self, attempt_id):
        P.routing_helper().text(attempt_id)
        key = P.digest(attempt_id.encode('utf-8'))
        path = P.no_links(self.root / ('.host-launch-' + key + '.lock'))
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            P.need(stat.S_ISREG(os.fstat(fd).st_mode), 'Host launch fence must be a regular file')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def launch(self, attempt_id):
        try:
            with self._fence(attempt_id):
                return self._launch(attempt_id)
        except BlockingIOError:
            return {'status': 'busy', 'launched': False, 'next_action': 'wait_for_existing_host_operation'}

    def _launch(self, attempt_id):
        # Validate and persist intent under the same task lock as reservations.
        with self.ops.locked(self.root) as (root, project, state):
            record = self.ops.attempt(state, attempt_id)
            P.need(record['status'] == 'active', 'Launch requires an active reservation')
            P.need(record['execution_mode'] == 'specialist', 'Managed launch requires a specialist reservation counted against capacity')
            if record.get('host_launch'):
                P.need(record['host_launch']['binding_sha256'] == self.binding_sha, 'Host binding changed; reconcile with original adapter')
                return {'status': 'reconcile_required', 'launch_id': record['host_launch']['id'], 'launched': False}
            P.need(record.get('dispatch') is None, 'Existing dispatch must be reconciled, not relaunched')
            assignment, packet_sha = self.ops.read_packet(root, project, record['packet'])
            P.need(assignment == record['assignment'] and packet_sha == record['packet_sha256'], 'Reserved packet changed')
            context = self.ops.check_context(root, project, record)
            P.need(context is not None, 'Managed host launch requires bounded context')
            P.routing_helper('execution_efficiency').require_no_loop(root, state, record)
            task = P.relative_file(root, context['task_path']).read_bytes()
            P.need(P.digest(task) == context['task_sha256'], 'Task bytes changed before launch')
            launch_id = str(uuid.uuid4())
            record['host_launch'] = {'id': launch_id, 'status': 'pending', 'binding_sha256': self.binding_sha,
                'binding': self.binding, 'packet_sha256': packet_sha, 'task_sha256': context['task_sha256'],
                'created_at': self.ops.now(), 'observations': []}
            payload = {'launch_id': launch_id, 'attempt_id': attempt_id, 'project_id': project['id'],
                'task_utf8': task.decode('utf-8'), 'task_sha256': context['task_sha256'],
                'packet_sha256': packet_sha, 'outputs': list(assignment['outputs']), 'binding': copy.deepcopy(self.binding)}
        # Once pending intent exists, even a crash before this call is ambiguous.
        # Only reconciliation may resolve it; retrying launch never calls twice.
        try:
            observed = self.driver.launch(payload)
            return self._observe(attempt_id, launch_id, observed)
        except Exception:
            self._unknown(attempt_id, launch_id)
            return {'status': 'unknown', 'launch_id': launch_id, 'launched': None,
                    'next_action': 'reconcile_existing_invocation', 'diagnostic_code': 'host_launch_outcome_unknown'}

    def _unknown(self, attempt_id, launch_id):
        with self.ops.locked(self.root) as (_, _, state):
            launch = self.ops.attempt(state, attempt_id)['host_launch']
            P.need(launch['id'] == launch_id, 'Launch identity changed')
            if launch['status'] not in TERMINAL:
                launch['status'] = 'unknown'

    def reconcile(self, attempt_id):
        try:
            with self._fence(attempt_id):
                return self._reconcile(attempt_id)
        except BlockingIOError:
            return {'status': 'busy', 'next_action': 'wait_for_existing_host_operation'}

    def _reconcile(self, attempt_id):
        with self.ops.locked(self.root) as (_, _, state):
            launch = copy.deepcopy(self.ops.attempt(state, attempt_id).get('host_launch'))
            P.need(launch is not None and launch['binding_sha256'] == self.binding_sha, 'Original host binding required')
        try:
            return self._observe(attempt_id, launch['id'], self.driver.reconcile(launch['id']))
        except Exception:
            self._unknown(attempt_id, launch['id'])
            return {'status': 'unknown', 'launch_id': launch['id'], 'next_action': 'reconcile_existing_invocation',
                    'diagnostic_code': 'host_reconciliation_inconclusive'}

    def _observe(self, attempt_id, launch_id, observation):
        fields = {'launch_id', 'status', 'host_run_reference', 'context_mode', 'task_sha256',
                  'observed_model', 'observed_effort', 'tool_scope', 'evidence_reference'}
        P.need(type(observation) is dict and set(observation) == fields, 'Invalid host observation')
        P.need(observation['launch_id'] == launch_id and observation['status'] in STATES, 'Wrong launch observation')
        rules = P.routing_helper()
        rules.text(observation['evidence_reference'])
        rules.strings(observation['tool_scope'])
        P.need(set(observation['tool_scope']) <= set(self.binding['tool_scope']), 'Host exposed tools outside configured scope')
        P.need(observation['context_mode'] in {'fresh', 'inherited', 'unknown'}, 'Invalid observed context mode')
        if self.binding['context_mode'] == 'fresh':
            P.need(observation['context_mode'] == 'fresh' or observation['status'] in {'absent', 'unknown'},
                   'Fresh context was not observed')
        for key in ('observed_model', 'observed_effort', 'host_run_reference'):
            if observation[key] is not None:
                rules.text(observation[key])
        for expected, actual in (('model', 'observed_model'), ('effort', 'observed_effort')):
            if self.binding[expected] is not None and observation['status'] not in {'absent', 'unknown'}:
                P.need(observation[actual] == self.binding[expected], 'Configured execution settings were not observed')
        if observation['status'] not in {'absent', 'unknown'}:
            rules.text(observation['host_run_reference'])
        with self.ops.locked(self.root) as (_, _, state):
            record = self.ops.attempt(state, attempt_id)
            launch = record['host_launch']
            P.need(launch['id'] == launch_id and launch['binding_sha256'] == self.binding_sha, 'Launch binding changed')
            P.need(observation['task_sha256'] == launch['task_sha256'], 'Observed task differs')
            if launch['status'] in TERMINAL:
                P.need(launch['observations'] and launch['observations'][-1] == observation, 'Terminal observation cannot be rewritten')
                return {'status': launch['status'], 'launch_id': launch_id, 'reused': True, 'host_isolation_verified': False}
            reference = observation['host_run_reference']
            if reference is not None:
                P.need(not any(a is not record and a.get('dispatch', {}) and a['dispatch'].get('host_run_reference') == reference
                               for a in state['attempts']), 'Invocation already belongs to another attempt')
                if record['dispatch']:
                    P.need(record['dispatch']['host_run_reference'] == reference, 'Invocation identity changed')
                else:
                    record['dispatch'] = {'attempt_id': attempt_id, 'host_run_reference': reference,
                        'observed_model': observation['observed_model'], 'observed_effort': observation['observed_effort'],
                        'requested_model': self.binding['model'], 'requested_effort': self.binding['effort'],
                        'execution_mode': record['execution_mode'], 'fallback_reason': 'Operator selected inline execution' if record['execution_mode'] == 'inline' else None,
                        'assurance': 'host_reported', 'execution_verified': False}
            if not launch['observations'] or launch['observations'][-1] != observation:
                P.need(len(launch['observations']) < 100 or observation['status'] in TERMINAL,
                       'Reconciliation history limit; retain evidence until a terminal observation')
                launch['observations'].append(copy.deepcopy(observation))
            launch['status'] = observation['status']
        return {'status': observation['status'], 'launch_id': launch_id, 'host_run_reference': reference,
                'host_isolation_verified': False, 'execution_assurance': 'host_reported', 'publication_authorized': False}
