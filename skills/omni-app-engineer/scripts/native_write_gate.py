"""Cooperating host write boundary over native_authoring's fixed requests.

No CLI, dynamic driver loading, secrets, default transport or implicit permission.
An operator supplies an already qualified host object in process. This cannot
intercept a separately privileged shell. Readback remains a separate requirement.
"""
import copy
import importlib.util
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location('guarded_native_authoring', Path(__file__).with_name('native_authoring.py'))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def operation_key(expected, request):
    # Review metadata may change while a network outcome remains unknown.
    # Creation identity never changes merely because a second payload is proposed.
    if expected['kind'] in {'native_app_create_request', 'native_demo_create_request'}:
        operation = {'origin': request['base_url'], 'create_document': request['body']['identifier']}
    else:
        operation = {'target': expected['target'], 'request': request,
                     'baseline': expected.get('baseline_sha256', expected.get('snapshot_sha256'))}
    return A.digest(operation)


def rebuild(project, prepared, host):
    """Ignore caller-supplied routes; reconstruct from current checked inputs."""
    A.need(type(prepared) is dict and type(prepared.get('engagement')) is dict, 'Prepared engagement required')
    e = prepared['engagement']
    kind = prepared.get('kind')
    if kind == 'native_app_create_request':
        expected = A.prepare_create(project=project, artifact=e['artifact'], spec_artifact=e['spec_artifact'])
    elif kind == 'native_demo_create_request':
        expected = A.prepare_demo(project=project, artifact=e['artifact'], spec_artifact=e['spec_artifact'],
                                  demo_artifact=e['demo_artifact'])
    elif kind in {'native_app_enhancement_request', 'native_app_publish_request'}:
        A.need(callable(getattr(host, 'read_draft', None)), 'Host must read the exact named draft immediately before writing')
        target = prepared['target']
        A.target_check(target)
        current = host.read_draft(copy.deepcopy(target))
        if prepared.get('dma_topics'):
            A.need(callable(getattr(host, 'read_semantic', None)), 'Host must read current DMA semantic bindings')
        semantic = host.read_semantic(copy.deepcopy(target)) if prepared.get('dma_topics') else None
        if kind == 'native_app_publish_request':
            expected = A.prepare_publish(project=project, artifact=e['artifact'],
                snapshot_artifact=e['snapshot_artifact'], current=current, semantic_snapshot=semantic)
        else:
            P = A.project_helper()
            root, _ = P.load_project(project)
            html = A.read_bytes(P.relative_file(root, e['artifact']), A.MAX_HTML).decode('utf-8')
            expected = A.prepare_app(target, current, current, html, project=project,
                                     artifact=e['artifact'], semantic_snapshot=semantic)
    else:
        raise ValueError('Unsupported native write kind')
    A.need(A.encoded(expected) == A.encoded(prepared), 'Prepared write drift: prepare and review current inputs')
    return expected


def execute(project, prepared, *, host):
    """Authorize exact bytes through host code, recheck, persist intent, send once.

    Required host methods are authorize(binding) and send(request); read_draft
    and read_semantic apply to their fixed routes. Creation additionally requires
    preflight_create(binding), which checks actual principal/target availability.
    Host code owns transport bounds, credential isolation and redirect rejection.
    No method is selected from JSON or loaded from an engagement path.
    """
    A.need(callable(getattr(host, 'authorize', None)) and callable(getattr(host, 'send', None)),
           'Operator-configured authorization and transport required')
    expected = rebuild(project, prepared, host)
    request = copy.deepcopy(expected['request'])
    request['base_url'] = expected.get('base_url') or expected['target']['base_url']
    kind = expected['kind']
    action = ('draft_preview' if kind == 'native_app_enhancement_request' else
              'demo_create_publication' if kind == 'native_demo_create_request' else
              'create_publication' if kind == 'native_app_create_request' else 'publish_main_draft')
    binding = {'action': action, 'request_sha256': A.digest(request),
               'prepared_sha256': A.digest(expected), 'engagement': copy.deepcopy(expected['engagement']),
               'base_url': request['base_url'], 'path': request['path'], 'method': request['method']}
    P = A.project_helper()
    root, _ = P.load_project(project)
    directory = P.no_links(root / '.native-write-gate')
    directory.mkdir(mode=0o700, exist_ok=True)
    sync_directory(root)
    key = operation_key(expected, request)
    intent = P.no_links(directory / (key + '.json'))
    A.need(not intent.exists(), 'Prior attempt exists: reconcile readback; never replay automatically')
    # The approval is obtained from the actual host, not a file/flag/reference.
    decision = host.authorize(copy.deepcopy(binding))
    A.need(type(decision) is dict and set(decision) == {'authorized', 'binding_sha256', 'reference'}
           and decision['authorized'] is True and decision['binding_sha256'] == A.digest(binding)
           and type(decision['reference']) is str and 0 < len(decision['reference'].strip()) <= 1024,
           'Actual host authorization must cover this exact action and binding')
    if action in {'create_publication', 'demo_create_publication'}:
        A.need(callable(getattr(host, 'preflight_create', None)) and
               host.preflight_create(copy.deepcopy(binding)) is True,
               'Host must verify current identity, intended audience and new destination before creation')
    # A choice/candidate/target change during approval invalidates that decision.
    rebuild(project, expected, host)
    record = {'schema_version': 1, 'kind': 'native_write_attempt', 'binding': binding,
              'operation_key': key,
              'authorization_reference': decision['reference'], 'status': 'intent_persisted',
              'host_enforcement_verified': False, 'readback_verified': False}
    fd = os.open(intent, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(A.encoded(record) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(directory)
    try:
        # Return no raw host errors or response payloads. Capture through the
        # supplied-capture verification route and preserve unknown outcomes.
        host.send(copy.deepcopy(request))
    except Exception:
        return {'status': 'outcome_unknown', 'attempt': str(intent), 'retry_allowed': False,
                'next_action': 'Read the known target and use the matching native verification operation.',
                'readback_verified': False, 'native_verified': False}
    return {'status': 'submitted_readback_required', 'attempt': str(intent), 'retry_allowed': False,
            'next_action': 'Use app-verify, app-create-verify, app-demo-verify or app-publish-verify for this action.',
            'readback_verified': False, 'native_verified': False, 'host_enforcement_verified': False}
