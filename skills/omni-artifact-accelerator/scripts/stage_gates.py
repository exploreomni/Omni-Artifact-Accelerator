"""Bounded, offline A–F checkpoints for cooperating hosts, not an authority service.

The host supplies an already qualified in-process provider with
``verify_choice(binding, receipt_ref) -> authenticated_subject | None``. It must
authenticate an actual user's selection of these exact options in this engagement.
No provider is loaded from requests, paths, environment variables or CLI arguments.
Stored subjects/receipts are never sufficient for the strict host policy.
The explicit conversation-evidence policy records an actual user reply as
workflow evidence only. It does not authenticate a person or grant execution.

Evidence is hash pinned, not semantically authenticated. This module cannot stop
arbitrary file/code edits, qualify a host, certify real access, prove how/when work
was performed, or confer publication, native, rendered or business acceptance.
Candidate and review files must be preserved snapshots, not overwritten in place.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat

POLICY = 'data-first-v1'
HOST_SELECTION = 'host-verified-v1'
CHAT_SELECTION = 'conversation-evidence-v1'
JOURNAL = 'stage-gates.json'
LOCK = '.stage-gates.lock'
KIND = 'oaa_stage_gate_journal'
STAGES = ('access', 'analysis', 'narrative', 'brief', 'options', 'choice', 'design')
REVIEW_SCOPES = ('security', 'ui_ux', 'product_owner', 'qa')
MAX_EVENTS = 256
MAX_JOURNAL_BYTES = 2 * 1024 * 1024
SOURCE_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = {
    'selection_policy': {'policy_decision'},
    'access': {'data', 'user_access'},
    'analysis': {'profile', 'queries', 'insights', 'expectations'},
    'narrative': {'narrative', 'traceability', 'refresh'},
    'brief': {'brief'}, 'options': {'comparison'}, 'design': {'design'},
    'review': {'review'},
}
EXTRA = {
    'selection_policy': {'selection_policy', 'expected_tail_sha256'},
    'access': {'source_scope', 'user_identity'},
    'analysis': {'analyst', 'bi_engineer'},
    'narrative': {'storyteller', 'analyst'}, 'brief': set(),
    'options': {'options'}, 'choice': {'option_id', 'receipt_ref'},
    'design': {'resolved'}, 'candidate': {'iteration_id', 'builders', 'artifacts'},
    'review': {'scope', 'reviewer', 'outcome', 'basis', 'iteration_sha256', 'candidate_sha256'},
}
LIMITS = (
    'Evidence integrity and recorded order only; no semantic/access/chronology authentication.',
    'Conversation choices are agent-attested workflow evidence, not independently authenticated approval.',
    'Strict host choices require a qualified provider; no production provider ships here.',
    'Raw file/code edits outside this API are not constrained.',
    'Review readiness does not authorize publication or certify native/rendered/human acceptance.',
)


def _helpers(P):
    if P is None:
        spec = importlib.util.spec_from_file_location(
            'stage_gate_project_helpers', Path(__file__).with_name('analyst_project.py'))
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
    return P


def _need(ok, code):
    if not ok:
        raise ValueError(code)


def _text(value, limit=4096):
    return type(value) is str and 0 < len(value.strip()) <= limit and not any(ord(c) < 32 for c in value)


def _ident(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value) is not None


def _hash(value):
    return type(value) is str and re.fullmatch(r'[a-f0-9]{64}', value) is not None


def _relative(value):
    _need(_text(value, 1024), 'stage_gate_relative_path_required')
    p = Path(value)
    _need(not p.is_absolute() and '..' not in p.parts and '\\' not in value and
          p.as_posix() == value and value not in {'.', JOURNAL, LOCK} and
          not any(part.startswith('.stage-gates-') for part in p.parts),
          'stage_gate_unsafe_path')
    return value


@contextmanager
def _root_fd(root, P):
    root = P.no_links(root)
    _need(root.is_dir() and root == root.resolve() and not root.resolve().is_relative_to(SOURCE_ROOT),
          'stage_gate_private_engagement_outside_package_required')
    # Check every ancestor through openat: neither an existing symlink nor a
    # parent swapped to a symlink may redirect evidence or durable state writes.
    fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in root.parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        yield root, fd
    finally:
        os.close(fd)


def _read(fd, relative, maximum):
    parts = Path(relative).parts
    _need(parts and not Path(relative).is_absolute() and '..' not in parts and
          '\\' not in relative and Path(relative).as_posix() == relative,
          'stage_gate_unsafe_path')
    current = os.dup(fd)
    handle = None
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = new
        handle = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        before = os.fstat(handle)
        _need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
              'stage_gate_bounded_regular_file_required')
        chunks, total = [], 0
        while True:
            block = os.read(handle, min(65536, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            _need(total <= maximum, 'stage_gate_file_too_large')
        after = os.fstat(handle)
        _need((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
              (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'stage_gate_input_changed')
        return b''.join(chunks)
    finally:
        if handle is not None:
            os.close(handle)
        os.close(current)


def _json(raw, P):
    def invalid(_):
        raise ValueError('stage_gate_nonfinite_json')
    try:
        result = json.loads(raw, object_pairs_hook=P.reject_duplicate, parse_constant=invalid)
        P.canonical(result)
        return result
    except (RecursionError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('stage_gate_invalid_json') from exc


def _pin(fd, relative, P):
    _relative(relative)
    data = _read(fd, relative, P.MAX_BYTES)
    _need(bool(data), 'stage_gate_empty_evidence')
    return {'path': relative, 'sha256': P.digest(data), 'bytes': len(data)}


def _pin_shape(value, allow_empty=False):
    _need(type(value) is dict and set(value) == {'path', 'sha256', 'bytes'}, 'stage_gate_invalid_pin')
    _relative(value['path'])
    _need(_hash(value['sha256']) and type(value['bytes']) is int and
          (0 if allow_empty else 1) <= value['bytes'] <= 10 * 1024 * 1024, 'stage_gate_invalid_pin')


def _pins(payload):
    result = list(payload.get('evidence', {}).values())
    result.extend(payload.get('discovery_dependencies', []))
    result.extend(option['evidence'] for option in payload.get('options', []))
    result.extend(payload.get('artifacts', []))
    if payload.get('selected_intent') is not None:
        result.append(payload['selected_intent'])
    return result


def _fresh(fd, event, P):
    try:
        return all(_pin(fd, pin['path'], P) == pin for pin in _pins(event['payload']))
    except (ValueError, OSError):
        return False


def _context(root, fd, P):
    project = _json(_read(fd, 'project.json', P.MAX_BYTES), P)
    _need(type(project) is dict and project.get('kind') == 'omni_analyst_project' and
          type(project.get('schema_version')) is int and project['schema_version'] == 1 and
          _text(project.get('id'), 256) and project.get('mode') in {'net-new', 'migration', 'enhancement'},
          'stage_gate_invalid_project')
    policy = project.get('stage_gate_policy')
    _need('stage_gate_policy' not in project or policy == POLICY, 'stage_gate_unknown_policy')
    required = project['mode'] == 'net-new' or policy == POLICY
    selected = project.get('design_intent')
    if selected is not None:
        _pin_shape(selected)
        raw = _read(fd, selected['path'], P.MAX_BYTES)
        _need(P.digest(raw) == selected['sha256'] and len(raw) == selected['bytes'],
              'stage_gate_selected_intent_changed')
        record = _json(raw, P)
        _need(type(record) is dict and type(record.get('spec')) is dict, 'stage_gate_invalid_intent')
        # The selected record is immutable, but its referenced design, brand,
        # assets, requirements and original spec can change independently. Check
        # the exact saved dependency manifest without treating unresolved product
        # decisions or missing functional selections as an integrity failure.
        pins = record.get('pins')
        _need(type(pins) is list and len(pins) <= 256 and 'spec_file' in record,
              'stage_gate_invalid_selected_dependency_manifest')
        for expected in [*pins, record['spec_file']]:
            _pin_shape(expected, allow_empty=True)
            data = _read(fd, expected['path'], P.MAX_BYTES)
            _need(len(data) == expected['bytes'] and P.digest(data) == expected['sha256'],
                  'stage_gate_selected_dependency_changed')
        _need([pin['path'] for pin in pins] == P.intent_helper().references(record['spec']),
              'stage_gate_selected_dependency_manifest_mismatch')
        spec = record['spec']
    else:
        draft = project.get('design_intent_draft')
        spec = _json(_read(fd, _relative(draft), P.MAX_BYTES), P) if draft else {}
        _need(type(spec) is dict, 'stage_gate_invalid_intent')
    if 'product' in spec:
        product = spec['product']
        _need(type(product) is dict and product.get('scope') in
              {'new_experience', 'material_redesign', 'migration', 'focused_repair'}, 'stage_gate_invalid_product_scope')
        required = required or product['scope'] in {'new_experience', 'material_redesign'}
    try:
        journal = _json(_read(fd, JOURNAL, MAX_JOURNAL_BYTES), P)
        required = True  # deleting a scope annotation never disables an existing lifecycle
    except FileNotFoundError:
        journal = {'schema_version': 1, 'kind': KIND, 'project_id': project['id'],
                   'engagement': str(root), 'events': []}
    return project, required, journal


def _current_spec(fd, project, P):
    """Read the current canonical working spec; _context verifies selected pins."""
    selected = project.get('design_intent')
    if selected:
        return _json(_read(fd, selected['path'], P.MAX_BYTES), P)['spec']
    return _json(_read(fd, _relative(project['design_intent_draft']), P.MAX_BYTES), P)


def _discovery_snapshot(fd, project, payload, P, *, current=True):
    """Validate D's immutable spec and source dependencies, not user authenticity."""
    spec = _json(_read(fd, payload['evidence']['intent']['path'], P.MAX_BYTES), P)
    P.intent_helper().validate(spec, project)
    helper = P.routing_helper('product_intent')
    context = helper.visual_context(spec)
    _need(context is not None, 'stage_gate_visual_discovery_required')
    paths = sorted(spec['product']['note_paths'])
    inventory = spec['product'].get('source_inventory_path')
    if inventory:
        paths = sorted(set([*paths, inventory]))
    if 'discovery_dependencies' in payload:
        _need([p['path'] for p in payload['discovery_dependencies']] == paths,
              'stage_gate_discovery_dependency_manifest_mismatch')
    if current:
        live = _current_spec(fd, project, P)
        P.intent_helper().validate(live, project)
        _need(helper.visual_context(live) == context and
              live['product']['scope'] == spec['product']['scope'] and
              live['product'].get('source_inventory_path') == inventory,
              'stage_gate_visual_discovery_changed_reopen_brief')
    return helper.visual_report(spec), paths


def _payload_shape(stage, payload, saved=True):
    expected = set(EXTRA[stage]) | ({'evidence'} if stage in EVIDENCE else set())
    discovery = stage == 'brief' and 'discovery_version' in payload
    if discovery:
        expected.add('discovery_version')
        if saved:
            expected.add('discovery_dependencies')
    conversation = stage == 'choice' and payload.get('basis') == 'conversation_evidence'
    if conversation:
        expected = {'basis', 'option_id', 'expected_binding', 'evidence'}
    elif saved and stage == 'choice':
        expected.add('subject')
    if saved and stage == 'design':
        expected.add('selected_intent')
    if saved and stage == 'candidate':
        expected.update({'prior_iteration_sha256', 'prior_reviews_sha256', 'candidate_sha256'})
    _need(type(payload) is dict and set(payload) == expected, 'stage_gate_invalid_' + stage + '_fields')
    if discovery:
        _need(type(payload['discovery_version']) is int and payload['discovery_version'] == 1,
              'stage_gate_unknown_discovery_version')
        if saved:
            dependencies = payload['discovery_dependencies']
            _need(type(dependencies) is list and 0 < len(dependencies) <= 33,
                  'stage_gate_discovery_dependencies_required')
            for pin in dependencies:
                _pin_shape(pin)
            paths = [p['path'] for p in dependencies]
            _need(paths == sorted(set(paths)), 'stage_gate_duplicate_discovery_dependency')
    if stage == 'selection_policy':
        _need(payload['selection_policy'] == CHAT_SELECTION and _hash(payload['expected_tail_sha256']),
              'stage_gate_invalid_selection_policy')
    if conversation:
        _need(type(payload['evidence']) is dict and set(payload['evidence']) == {'user_response'},
              'stage_gate_user_response_required')
        value = payload['evidence']['user_response']
        _pin_shape(value) if saved else _relative(value)
        _need(type(payload['expected_binding']) is dict, 'stage_gate_expected_choice_binding_required')
    if stage in EVIDENCE:
        evidence = payload['evidence']
        expected_evidence = {'brief', 'intent'} if discovery else EVIDENCE[stage]
        _need(type(evidence) is dict and set(evidence) == expected_evidence, 'stage_gate_' + stage + '_evidence_required')
        for value in evidence.values():
            _pin_shape(value) if saved else _relative(value)
    for key in {'source_scope', 'user_identity', 'analyst', 'bi_engineer', 'storyteller',
                'receipt_ref', 'subject', 'reviewer'} & set(payload):
        _need(_text(payload[key]), 'stage_gate_invalid_' + key)
    if stage == 'options':
        options = payload['options']
        _need(type(options) is list and len(options) == 3, 'stage_gate_exactly_three_options_required')
        for option in options:
            _need(type(option) is dict and set(option) == {'id', 'thesis', 'evidence'} and
                  _ident(option['id']) and _text(option['thesis']), 'stage_gate_invalid_option')
            _pin_shape(option['evidence']) if saved else _relative(option['evidence'])
        _need(len({o['id'] for o in options}) == 3 and
              len({' '.join(o['thesis'].casefold().split()) for o in options}) == 3,
              'stage_gate_distinct_options_required')
        if saved:
            _need(len({o['evidence']['sha256'] for o in options}) == 3,
                  'stage_gate_distinct_option_evidence_required')
    if stage == 'choice':
        _need(_ident(payload['option_id']), 'stage_gate_invalid_option_id')
    if stage == 'design':
        _need(payload['resolved'] is True, 'stage_gate_detailed_design_unresolved')
        if saved and payload['selected_intent'] is not None:
            _pin_shape(payload['selected_intent'])
    if stage == 'candidate':
        _need(_ident(payload['iteration_id']) and type(payload['builders']) is list and
              0 < len(payload['builders']) <= 16 and all(_text(b, 256) for b in payload['builders']) and
              len(set(payload['builders'])) == len(payload['builders']), 'stage_gate_invalid_candidate')
        artifacts = payload['artifacts']
        _need(type(artifacts) is list and 0 < len(artifacts) <= 64, 'stage_gate_candidate_artifacts_required')
        for artifact in artifacts:
            _pin_shape(artifact) if saved else _relative(artifact)
        paths = [p['path'] for p in artifacts] if saved else artifacts
        _need(len(set(paths)) == len(paths), 'stage_gate_duplicate_artifact')
        if saved:
            _need(_hash(payload['candidate_sha256']) and all(payload[k] is None or _hash(payload[k]) for k in
                      ('prior_iteration_sha256', 'prior_reviews_sha256')), 'stage_gate_invalid_prior_iteration')
    if stage == 'review':
        _need(all(_text(payload[k], 32) for k in ('scope', 'outcome', 'basis')) and
              payload['scope'] in REVIEW_SCOPES and payload['outcome'] in
              {'resolved', 'changes_requested', 'unobserved'} and payload['basis'] in
              {'source', 'rendered', 'native', 'human'}, 'stage_gate_invalid_review')
        _need(_hash(payload['iteration_sha256']) and _hash(payload['candidate_sha256']),
              'stage_gate_review_candidate_required')


def _complete(reviews):
    # An unobserved lane is a recorded consultation gap, never a resolved outcome.
    return set(reviews) == set(REVIEW_SCOPES)


def _candidate_hash(artifacts, P):
    return P.digest(P.canonical({p['path']: p['sha256'] for p in artifacts}))


def _reviews_hash(reviews, P):
    return P.digest(P.canonical({s: e['sha256'] for s, e in sorted(reviews.items())}))


def _replay(root, project, journal, P):
    _need(type(journal) is dict and set(journal) ==
          {'schema_version', 'kind', 'project_id', 'engagement', 'events'} and
          type(journal['schema_version']) is int and journal['schema_version'] == 1 and
          journal['kind'] == KIND and journal['project_id'] == project['id'] and
          journal['engagement'] == str(root), 'stage_gate_invalid_journal')
    events = journal['events']
    _need(type(events) is list and len(events) <= MAX_EVENTS, 'stage_gate_history_limit')
    current, reviews, last_reviews, iterations = {}, {}, {}, set()
    iteration_dependencies = []
    candidate = last_candidate = selection_policy = None
    choice_seen = False
    previous = P.digest(P.canonical({'project_id': project['id'], 'engagement': str(root), 'policy': POLICY}))
    for sequence, event in enumerate(events, 1):
        _need(type(event) is dict and set(event) == {'sequence', 'stage', 'previous_sha256',
              'predecessor_sha256', 'recorded_at', 'payload', 'sha256'} and
              type(event['sequence']) is int and event['sequence'] == sequence and
              event['stage'] in EXTRA and event['previous_sha256'] == previous,
              'stage_gate_invalid_event_chain')
        body = {k: v for k, v in event.items() if k != 'sha256'}
        _need(event['sha256'] == P.digest(P.canonical(body)), 'stage_gate_event_digest_mismatch')
        _need(_text(event['recorded_at'], 40), 'stage_gate_invalid_timestamp')
        try:
            stamp = datetime.fromisoformat(event['recorded_at'])
            _need(stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc), 'stage_gate_future_timestamp')
        except (TypeError, ValueError) as exc:
            raise ValueError('stage_gate_invalid_timestamp') from exc
        stage, payload = event['stage'], event['payload']
        _payload_shape(stage, payload)
        if stage == 'selection_policy':
            _need(selection_policy is None and not choice_seen and last_candidate is None,
                  'stage_gate_selection_policy_already_fixed')
            _need(payload['expected_tail_sha256'] == previous, 'stage_gate_selection_policy_tail_mismatch')
            predecessor = previous
            selection_policy = event
        elif stage in STAGES:
            i = STAGES.index(stage)
            _need(all(s in current for s in STAGES[:i]), 'stage_gate_skipped_predecessor')
            _need(candidate is None or _complete(reviews), 'stage_gate_iteration_reviews_required')
            predecessor = current[STAGES[i - 1]]['sha256'] if i else None
            if stage == 'choice':
                choice_seen = True
                _need(payload['option_id'] in {o['id'] for o in current['options']['payload']['options']},
                      'stage_gate_choice_not_current_option')
                _need((payload.get('basis') == 'conversation_evidence') == (selection_policy is not None),
                      'stage_gate_choice_policy_mismatch')
                if selection_policy is not None:
                    _need(payload['expected_binding'] == _binding(root, project, current['options'],
                          payload['option_id'], selection_policy), 'stage_gate_choice_binding_mismatch')
            for later in STAGES[i:]:
                current.pop(later, None)
            current[stage] = event
            candidate, reviews = None, {}
        elif stage == 'candidate':
            _need(all(s in current for s in STAGES), 'stage_gate_skipped_predecessor')
            _need(last_candidate is None or _complete(last_reviews), 'stage_gate_iteration_reviews_required')
            _need(payload['iteration_id'] not in iterations and
                  payload['candidate_sha256'] == _candidate_hash(payload['artifacts'], P) and
                  payload['prior_iteration_sha256'] == (last_candidate['sha256'] if last_candidate else None) and
                  payload['prior_reviews_sha256'] == (_reviews_hash(last_reviews, P) if last_candidate else None),
                  'stage_gate_prior_iteration_mismatch')
            iterations.add(payload['iteration_id'])
            if last_candidate:
                iteration_dependencies.extend([last_candidate, *last_reviews.values()])
            predecessor = current['design']['sha256']
            candidate = last_candidate = event
            reviews = last_reviews = {}
        else:
            _need(candidate is not None, 'stage_gate_candidate_required')
            predecessor = candidate['sha256']
            _need(payload['iteration_sha256'] == candidate['sha256'] and
                  payload['candidate_sha256'] == candidate['payload']['candidate_sha256'],
                  'stage_gate_review_candidate_mismatch')
            _need(payload['scope'] not in {'ui_ux', 'qa'} or
                  payload['reviewer'] not in candidate['payload']['builders'], 'stage_gate_independent_reviewer_required')
            reviews[payload['scope']] = event
            last_reviews = reviews
        _need(event['predecessor_sha256'] == predecessor, 'stage_gate_predecessor_mismatch')
        previous = event['sha256']
    return {'current': current, 'candidate': candidate, 'reviews': reviews,
            'last_candidate': last_candidate, 'last_reviews': last_reviews,
            'iteration_dependencies': iteration_dependencies, 'tail': previous,
            'selection_policy': selection_policy, 'choice_seen': choice_seen}


def _binding(root, project, options, option_id, selection_policy=None):
    binding = {'policy': POLICY, 'project_id': project['id'], 'engagement': str(root),
            'options_sha256': options['sha256'], 'predecessor_sha256': options['predecessor_sha256'],
            'option_id': option_id}
    if selection_policy is not None:
        binding.update(selection_policy=CHAT_SELECTION, selection_policy_sha256=selection_policy['sha256'])
    return binding


def _conversation_response(fd, payload, P):
    """Check provenance shape and exact binding, never authenticate a transcript."""
    raw = _read(fd, payload['evidence']['user_response']['path'], 64 * 1024)
    value = _json(raw, P)
    _need(type(value) is dict and set(value) == {'schema_version', 'kind', 'source', 'response_text',
          'selected_option_id', 'expected_binding', 'recorded_by', 'assurance'}, 'stage_gate_invalid_conversation_evidence')
    _need(type(value['schema_version']) is int and value['schema_version'] == 1 and
          value['kind'] == 'oaa_conversation_choice' and
          value['assurance'] == 'agent_attested_not_independently_authenticated' and
          _text(value['recorded_by'], 256), 'stage_gate_invalid_conversation_evidence')
    source = value['source']
    _need(type(source) is dict and set(source) == {'host', 'conversation_ref', 'question_ref', 'response_ref', 'role'} and
          source['role'] == 'user' and all(_text(source[k], 1024) for k in ('host', 'conversation_ref', 'question_ref')) and
          (source['response_ref'] is None or _text(source['response_ref'], 1024)), 'stage_gate_user_response_provenance_required')
    answer = value['response_text']
    _need(type(answer) is str and 0 < len(answer.strip()) <= 16384 and
          not any(ord(c) < 32 and c not in '\n\r\t' for c in answer), 'stage_gate_user_response_text_required')
    _need(value['selected_option_id'] == payload['option_id'] and
          value['expected_binding'] == payload['expected_binding'], 'stage_gate_response_binding_mismatch')
    return value


def _subject(provider, binding, receipt_ref):
    if provider is None:
        return None
    try:
        subject = provider.verify_choice(dict(binding), receipt_ref)
    except Exception:
        return None  # provider failures never leak host secrets or turn into approval
    return subject if _text(subject, 256) else None


def _report(root, fd, project, required, state, P, provider):
    report = {'required': required, 'policy': POLICY if required else None,
              'status': 'not_applicable', 'next_stage': None, 'completed_stages': [], 'stage_bindings': {},
              'findings': [], 'choice_bindings': {}, 'candidate': None, 'candidate_sha256': None, 'reviews': {},
              'release_ready': False, 'claims_authenticated': False,
              'selection_policy': CHAT_SELECTION if state['selection_policy'] else HOST_SELECTION,
              'selection_policy_event_sha256': state['selection_policy']['sha256'] if state['selection_policy'] else None,
              'tail_sha256': state['tail'], 'choice_assurance': None, 'choice_authenticated': False,
              'external_mutations_authorized': False, 'limits': list(LIMITS),
              'visual_discovery': {'status': 'not_assessed', 'version': None}}
    if not required:
        return report
    if state['selection_policy'] is not None and not _fresh(fd, state['selection_policy'], P):
        report.update(status='blocked', next_stage='repair_selection_policy')
        report['findings'].append('stale_evidence:selection_policy')
        return report
    current = state['current']
    for stage in STAGES:
        event = current.get(stage)
        if event is None:
            report['findings'].append('missing_stage:' + stage)
            report['next_stage'] = stage
            break
        if not _fresh(fd, event, P):
            report['findings'].append('stale_evidence:' + stage)
            report['next_stage'] = stage
            break
        if stage == 'brief':
            if event['payload'].get('discovery_version') == 1:
                try:
                    discovery, _ = _discovery_snapshot(fd, project, event['payload'], P)
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    report['findings'].append(str(exc) if isinstance(exc, ValueError) else 'stage_gate_invalid_discovery')
                    report['next_stage'] = 'brief'
                    break
                report['visual_discovery'] = dict(discovery, version=1)
                if discovery['status'] != 'ready':
                    report['completed_stages'].append(stage)
                    report['stage_bindings'][stage] = event['sha256']
                    report['findings'].append('visual_discovery_unresolved')
                    report['next_stage'] = 'brief'
                    break
            elif P.routing_helper('product_intent').visual_context(_current_spec(fd, project, P)) is not None:
                report['findings'].append('visual_discovery_checkpoint_required')
                report['next_stage'] = 'brief'
                break
        if stage == 'design' and event['payload']['selected_intent'] != project.get('design_intent'):
            report['findings'].append('selected_intent_changed')
            report['next_stage'] = stage
            break
        if stage == 'choice':
            if state['selection_policy'] is not None:
                _conversation_response(fd, event['payload'], P)
                report['choice_assurance'] = 'conversation_evidence'
            else:
                subject = _subject(provider, _binding(root, project, current['options'],
                                   event['payload']['option_id']), event['payload']['receipt_ref'])
                if subject is None or subject != event['payload']['subject']:
                    report['findings'].append('trusted_choice_unverified')
                    report['next_stage'] = 'choice'
                    break
                report.update(choice_assurance='host_verified', choice_authenticated=True)
        report['completed_stages'].append(stage)
        report['stage_bindings'][stage] = event['sha256']
    if 'options' in report['completed_stages']:
        report['choice_bindings'] = {o['id']: _binding(root, project, current['options'], o['id'], state['selection_policy'])
                                    for o in current['options']['payload']['options']}
    last = state['last_candidate']
    if last:
        dependencies = [last, *state['last_reviews'].values(), *state['iteration_dependencies']]
        if any(not _fresh(fd, e, P) for e in dependencies):
            report['findings'].append('stale_iteration_evidence')
        report['prior_reviews_complete'] = _complete(state['last_reviews'])
    else:
        report['prior_reviews_complete'] = True
    if len(report['completed_stages']) == len(STAGES):
        candidate = state['candidate']
        if candidate is None:
            report['next_stage'] = 'candidate'
        else:
            report['candidate'] = dict(candidate['payload'], event_sha256=candidate['sha256'])
            report['candidate_sha256'] = candidate['payload']['candidate_sha256']
            report['reviews'] = {scope: dict(e['payload'], event_sha256=e['sha256'])
                                 for scope, e in state['reviews'].items()}
            report['next_stage'] = 'review'
            if _complete(state['reviews']):
                report['next_stage'] = 'candidate'
                if all(e['payload']['outcome'] == 'resolved' for e in state['reviews'].values()):
                    report['next_stage'] = None
                    report['release_ready'] = not report['findings']
    report['status'] = ('ready_for_release' if report['release_ready'] else
                        'blocked' if any(not x.startswith('missing_stage:') for x in report['findings']) else 'incomplete')
    return report


def inspect(root, *, P=None, provider=None):
    """Read current integrity/readiness; invalid or missing state never means ready."""
    P = _helpers(P)
    try:
        with _root_fd(root, P) as (root, fd):
            project, required, journal = _context(root, fd, P)
            state = _replay(root, project, journal, P)
            return _report(root, fd, project, required, state, P, provider)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError):
        return {'required': True, 'policy': POLICY, 'status': 'invalid', 'next_stage': 'repair_state',
                'completed_stages': [], 'stage_bindings': {}, 'findings': ['stage_gate_invalid_state'], 'choice_bindings': {},
                'candidate': None, 'candidate_sha256': None, 'reviews': {}, 'release_ready': False, 'claims_authenticated': False,
                'selection_policy': None, 'selection_policy_event_sha256': None, 'tail_sha256': None,
                'choice_assurance': None, 'choice_authenticated': False,
                'external_mutations_authorized': False, 'limits': list(LIMITS)}


def candidate_commit_status(root, iteration_id, *, P=None):
    """Recovery observation only: True committed, False absent, None uncertain.

    Does not consult choice providers, confer readiness or authorize any action.
    A caller must preserve bytes when commit status cannot be established.
    """
    P = _helpers(P)
    try:
        _need(_ident(iteration_id), 'stage_gate_invalid_iteration')
        with _root_fd(root, P) as (root, fd):
            project, _, journal = _context(root, fd, P)
            _replay(root, project, journal, P)
            return any(e['stage'] == 'candidate' and e['payload']['iteration_id'] == iteration_id
                       for e in journal['events'])
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError):
        return None


def _require(report, action, provider):
    _need(action in {*STAGES, 'selection_policy', 'choose', 'build', 'candidate', 'review', 'release'}, 'stage_gate_unknown_action')
    if not report['required']:
        return
    _need(report['status'] != 'invalid', 'stage_gate_invalid_state')
    _need('stale_evidence:selection_policy' not in report['findings'], 'stage_gate_stale_selection_policy')
    if action == 'selection_policy':
        _need(report['selection_policy'] == HOST_SELECTION, 'stage_gate_selection_policy_already_fixed')
        return
    stage = {'choose': 'choice', 'build': 'candidate'}.get(action, action)
    needed = STAGES[:STAGES.index(stage)] if stage in STAGES else STAGES
    _need(set(needed) <= set(report['completed_stages']), 'stage_gate_predecessor_incomplete:' + action)
    if stage in {'options', 'choice'}:
        discovery = report.get('visual_discovery', {})
        _need(discovery.get('version') == 1, 'stage_gate_upgrade_visual_discovery_before_options')
        _need(discovery.get('status') == 'ready', 'stage_gate_visual_discovery_unresolved')
    if stage in {'choice', 'design', 'candidate', 'review', 'release'} and report['selection_policy'] == HOST_SELECTION:
        _need(provider is not None and callable(getattr(provider, 'verify_choice', None)),
              'stage_gate_trusted_provider_required')
    if stage not in {'review', 'release'}:
        _need(report.get('prior_reviews_complete', True), 'stage_gate_iteration_reviews_required')
    _need('stale_iteration_evidence' not in report['findings'], 'stage_gate_stale_iteration_evidence')
    if stage in {'review', 'release'}:
        _need(report['candidate'] is not None, 'stage_gate_candidate_required')
    if stage == 'release':
        _need(report['release_ready'], 'stage_gate_resolved_reviews_required')


def require_action(root, action, *, P=None, provider=None):
    """Cooperating host guard. It does not execute or authorize the action."""
    report = inspect(root, P=P, provider=provider)
    _require(report, action, provider)
    return report


@contextmanager
def _locked(fd):
    handle = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
    try:
        _need(stat.S_ISREG(os.fstat(handle).st_mode), 'stage_gate_invalid_lock')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('stage_gate_busy') from exc
        yield
    finally:
        os.close(handle)


def _atomic(fd, value, P):
    data = P.canonical(value) + b'\n'
    _need(len(data) <= MAX_JOURNAL_BYTES, 'stage_gate_journal_too_large')
    temporary = '.stage-gates-' + secrets.token_hex(16)
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, JOURNAL, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=fd)
        except FileNotFoundError:
            pass


def record(root, request, *, P=None, provider=None):
    """Append one observed checkpoint; reject unbounded fields and skipped stages.

    Common requests: {stage, evidence: {required_name: relative_path}, ...}.
    EXTRA/EVIDENCE document the complete schema. review.basis defaults to source.
    Strict choice uses option_id and receipt_ref authenticated by the provider.
    Explicit conversational choice uses a pinned response and caller-supplied
    exact binding; it is not an approval grant. Review requests name iteration_sha256
    and candidate_sha256; they are checked, never silently restamped. Generated
    event/subject fields cannot be supplied. No host adapter or approval-minting
    command is included.
    """
    P = _helpers(P)
    _need(type(request) is dict and _text(request.get('stage'), 32) and request['stage'] in EXTRA,
          'stage_gate_invalid_request')
    _need(len(P.canonical(request)) <= 64 * 1024, 'stage_gate_request_too_large')
    stage = request['stage']
    payload = {k: v for k, v in request.items() if k != 'stage'}
    if stage == 'candidate' and 'artifact' in payload and 'artifacts' not in payload:
        payload['artifacts'] = [payload.pop('artifact')]
    if stage == 'review':
        payload.setdefault('basis', 'source')
    _payload_shape(stage, payload, saved=False)
    with _root_fd(root, P) as (root, fd), _locked(fd):
        project, required, journal = _context(root, fd, P)
        _need(required, 'stage_gate_not_new_product')
        state = _replay(root, project, journal, P)
        before = _report(root, fd, project, required, state, P, provider)
        _require(before, stage, provider)
        if stage == 'brief':
            _need(payload.get('discovery_version') == 1, 'stage_gate_visual_discovery_required')
        if stage == 'selection_policy':
            _need(not state['choice_seen'] and state['last_candidate'] is None,
                  'stage_gate_selection_policy_already_fixed')
            _need(payload['expected_tail_sha256'] == before['tail_sha256'],
                  'stage_gate_selection_policy_tail_mismatch')
        if stage == 'review':
            _need(payload['iteration_sha256'] == state['candidate']['sha256'] and
                  payload['candidate_sha256'] == state['candidate']['payload']['candidate_sha256'],
                  'stage_gate_review_candidate_mismatch')
        if stage in EVIDENCE:
            payload['evidence'] = {k: _pin(fd, v, P) for k, v in payload['evidence'].items()}
        if stage == 'brief':
            _, paths = _discovery_snapshot(fd, project, payload, P)
            payload['discovery_dependencies'] = [_pin(fd, p, P) for p in paths]
            # Adoption can precede a selected intent. Keep prior D requirements
            # accountable even after an upstream checkpoint invalidates current D.
            prior = next((e for e in reversed(journal['events']) if e['stage'] == 'brief'
                          and e['payload'].get('discovery_version') == 1), None)
            if prior:
                pin = prior['payload']['evidence']['intent']
                _need(_pin(fd, pin['path'], P) == pin, 'stage_gate_prior_discovery_snapshot_changed')
                old_spec = _json(_read(fd, pin['path'], P.MAX_BYTES), P)
                new_spec = _json(_read(fd, payload['evidence']['intent']['path'], P.MAX_BYTES), P)
                P.routing_helper('product_intent').validate_visual_transition(old_spec, new_spec)
        if stage == 'options':
            payload['options'] = [dict(o, evidence=_pin(fd, o['evidence'], P)) for o in payload['options']]
        if stage == 'choice':
            _need(payload['option_id'] in before['choice_bindings'], 'stage_gate_choice_not_current_option')
            if before['selection_policy'] == CHAT_SELECTION:
                _need(payload.get('basis') == 'conversation_evidence', 'stage_gate_conversation_evidence_required')
                _need(payload['expected_binding'] == before['choice_bindings'][payload['option_id']],
                      'stage_gate_choice_binding_mismatch')
                payload['evidence'] = {k: _pin(fd, v, P) for k, v in payload['evidence'].items()}
                _conversation_response(fd, payload, P)
            else:
                _need('basis' not in payload, 'stage_gate_choice_policy_mismatch')
                payload['subject'] = _subject(provider, before['choice_bindings'][payload['option_id']], payload['receipt_ref'])
                _need(payload['subject'] is not None, 'stage_gate_trusted_choice_unverified')
        if stage == 'design':
            payload['selected_intent'] = project.get('design_intent')
        if stage == 'candidate':
            payload['artifacts'] = [_pin(fd, p, P) for p in payload['artifacts']]
            payload['candidate_sha256'] = _candidate_hash(payload['artifacts'], P)
            last = state['last_candidate']
            payload['prior_iteration_sha256'] = last['sha256'] if last else None
            payload['prior_reviews_sha256'] = _reviews_hash(state['last_reviews'], P) if last else None
        _payload_shape(stage, payload)
        _need(len(journal['events']) < MAX_EVENTS, 'stage_gate_history_limit')
        predecessor = (state['tail'] if stage == 'selection_policy' else
                       state['current'][STAGES[STAGES.index(stage) - 1]]['sha256']
                       if stage in STAGES and stage != 'access' else
                       state['current']['design']['sha256'] if stage == 'candidate' else
                       state['candidate']['sha256'] if stage == 'review' else None)
        event = {'sequence': len(journal['events']) + 1, 'stage': stage,
                 'previous_sha256': state['tail'], 'predecessor_sha256': predecessor,
                 'recorded_at': datetime.now(timezone.utc).isoformat(), 'payload': payload}
        event['sha256'] = P.digest(P.canonical(event))
        journal['events'].append(event)
        updated = _replay(root, project, journal, P)
        report = _report(root, fd, project, True, updated, P, provider)
        _need(report['selection_policy_event_sha256'] == event['sha256'] if stage == 'selection_policy' else
              stage in report['completed_stages'] if stage in STAGES else
              report['candidate'] is not None, 'stage_gate_evidence_changed_during_record')
        _need('stale_iteration_evidence' not in report['findings'], 'stage_gate_evidence_changed_during_record')
        _need('stale_evidence:selection_policy' not in report['findings'], 'stage_gate_evidence_changed_during_record')
        _atomic(fd, journal, P)
        report['recorded'] = {'stage': stage, 'sequence': event['sequence'], 'sha256': event['sha256']}
        return report
