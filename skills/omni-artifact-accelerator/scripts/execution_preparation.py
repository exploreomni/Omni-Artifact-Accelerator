"""Fixed resumable work/context/preflight/reservation recipe; never launches."""
import copy
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import stat

_spec = importlib.util.spec_from_file_location('recipe_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def _binding(root, request):
    files = sorted(set(request['work']['inputs'] + [r['path'] for r in request['context']['evidence']]))
    binding = {'project': P.digest(P.read_json(root / 'project.json')[1]),
               'inputs': {p: P.digest(P.relative_file(root, p).read_bytes()) for p in files},
               'implementation': {name: P.digest(Path(__file__).with_name(name).read_bytes()) for name in
                   ('execution_preparation.py', 'execution_efficiency.py', 'context_packets.py', 'task_operations.py')}}
    journal = root / 'stage-gates.json'
    # The packet/preflight validators also check the actual journal and selected
    # context; this recorded binding is never an alternative to those checks.
    if journal.exists():
        binding['journal'] = P.digest(P.read_json(journal)[1])
    return binding


def prepare(root, request):
    root, _ = P.load_project(root)
    P.routing_helper('execution_contracts').validate('execution_prepare', 'recipe', request)
    P.need(request['schema_version'] == 1 and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', request['idempotency_key']), 'Invalid preparation identity')
    P.need(request.get('execution_mode', 'specialist') in {'inline', 'specialist'}, 'Invalid execution mode')
    P.need('packet' not in request['context'], 'Recipe computes the packet binding; do not supply one')
    P.routing_helper('execution_contracts').validate('execution_prepare', 'work', request['work'])
    P.need(type(request['context'].get('evidence')) is list, 'Context evidence required')
    directory = P.no_links(root / '.execution-preparation')
    directory.mkdir(mode=0o700, exist_ok=True)
    lock_path = P.no_links(directory / (request['idempotency_key'] + '.lock'))
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        P.need(stat.S_ISREG(os.fstat(fd).st_mode), 'Preparation lock must be regular')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'busy', 'agents_dispatched': False, 'next_action': 'Resume the same request after the active preparation finishes.'}
        binding = _binding(root, request)
        intent = {'schema_version': 1, 'kind': 'execution_preparation_intent',
                  'request_sha256': P.digest(P.canonical(request)), 'binding': binding}
        intent_path = directory / (request['idempotency_key'] + '.json')
        reused = intent_path.exists()
        if reused:
            P.need(P.read_json(intent_path)[0] == intent, 'Preparation identity or inputs changed; use a new version')
        else:
            P.routing_helper('execution_efficiency').atomic_json(intent_path, intent)
        efficiency = P.routing_helper('execution_efficiency')
        work = efficiency.prepare(root, request['work'])
        packet = P.read_json(P.relative_file(root, work['packet']))[0]
        context = copy.deepcopy(request['context'])
        context['packet'] = {'path': work['packet'], 'sha256': work['packet_sha256']}
        # Add only machine-defined restrictions; retain every caller-supplied item.
        for key, mandatory in [('stop_conditions', packet['stop_conditions']),
                               ('shared_constraint_ids', packet.get('design_context', {}).get('shared_constraint_ids', []))]:
            P.need(type(context.get(key, [])) is list and all(type(x) is str for x in context.get(key, [])), 'Invalid context restrictions')
            context[key] = list(dict.fromkeys(context.get(key, []) + mandatory))
        receipt = P.routing_helper('context_packets').build(root, context, request['context_output'])
        checked = efficiency.preflight(root, {'action': request['action'], 'packet': work['packet'], 'context_receipt': receipt['receipt_path']})
        if checked['status'] != 'ready':
            return {'status': 'blocked', 'prepared': work, 'context': receipt,
                    'preflight': checked, 'reservation_created': False, 'agents_dispatched': False,
                    'next_action': 'Resolve retained findings; resume this request only if its input bindings remain current.'}
        P.need(_binding(root, request) == binding, 'Preparation inputs changed before reservation')
        claim = P.routing_helper('task_operations').claim(root, {'attempt_id': request['attempt_id'],
            'packet': work['packet'], 'context_receipt': receipt['receipt_path'],
            'execution_mode': request.get('execution_mode', 'specialist')})
        return {'status': 'ready', 'resumed': reused, 'prepared': work, 'context': receipt, 'reservation': claim,
                'agents_dispatched': False, 'publication_authorized': False,
                'next_action': 'Reuse the recorded attempt; worker launch remains a separate guarded operation.'}
    finally:
        os.close(fd)
