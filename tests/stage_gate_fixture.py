"""Synthetic host and evidence for tests only; never a production approval adapter."""
import copy
from datetime import datetime, timezone
import json


def bootstrap(root, P):
    """Synthetic startup/role evidence for isolated tests, never production identity."""
    project = P.load_project(root)[1]
    if project.get('execution_start'):
        return
    brief = root / 'inputs/brief.txt'
    if not brief.exists() or not brief.read_text().strip():
        brief.write_text('Original synthetic request: compare fictional garden observations; no real user.')
    roles = {'experience': 'app-designer', 'brand': 'branding', 'semantics': 'data-analyst',
             'engineering': 'app-engineer', 'verification': 'qa-analyst',
             'design_systems': 'design-systems', 'storytelling': 'data-storyteller',
             'product_intent': 'product-owner', 'creative_review': 'design-systems'}
    responsibilities = {name: {'role': role, 'worker': 'fixture-' + name, 'mode': 'inline',
        'rationale': 'Synthetic isolated role evidence, not actual dispatch or independent work.'}
        for name, role in roles.items()}
    if project['surfaces'] == ['dashboard']:
        responsibilities['experience']['role'] = 'dashboard-designer'
        responsibilities['engineering']['role'] = 'bi-engineer'
    execution = {'responsibilities': responsibilities}
    P.write_json(root / 'contracts/execution.json', execution, replace=(root / 'contracts/execution.json').exists())
    loaded = ['skills/omni-artifact-accelerator/SKILL.md']
    loaded += ['skills/omni-' + role + '/SKILL.md' for role in P.ROLES]
    loaded += ['skills/omni-product-owner/references/visual-experience-discovery.md']
    loaded += ['skills/omni-design-systems/references/' + name + '.md' for name in
               ('experience-brief', 'visual-craft', 'experience-curriculum', 'ideation-playbook')]
    request = {'id': 'synthetic-fixture',
        'source_mode': 'repository_only', 'host': {'name': 'isolated-test-fixture',
        'execution_mode': 'inline', 'tools': ['Python standard library and first-party helpers'],
        'constraints': ['Synthetic evidence only; no real user, access, dependency or publication authority']},
        'entrypoint': 'Original synthetic fixture', 'brief': 'inputs/brief.txt',
        'execution': 'contracts/execution.json', 'loaded_guidance': loaded}
    if 'workflow_quality_policy' not in project:
        request['adopt_quality_policy'] = True
    P.routing_helper('delivery_workflow').start(root, request)
    refresh_request_review(root, P)


def refresh_request_review(root, P):
    """Update a fictional review scope after synthetic requirements are authored."""
    project = P.load_project(root)[1]
    if not project.get('execution_start'):
        return
    execution = P.read_json(root / 'contracts/execution.json')[0]
    spec = (P.intent_helper().load_selected(root)['spec'] if project.get('design_intent') else
            P.read_json(root / project['design_intent_draft'])[0])
    path = 'evidence/original-request-fixture.txt'
    (root / path).write_text('Synthetic original request coverage; not an actual independent review.')
    execution['request_review'] = {'reviewer': execution['responsibilities']['verification']['worker'],
        'brief_sha256': P.digest((root / 'inputs/brief.txt').read_bytes()),
        'requirement_ids': [r['id'] for r in spec['requirements']], 'evidence_path': path}
    P.write_json(root / 'contracts/execution.json', execution, replace=True)


def quality_spec(spec, root):
    """Original quality choices live in existing requirements, not test flags."""
    product = spec['product']
    if product.get('quality_bar'):
        return spec
    path = 'inputs/quality-fixture.json'
    (root / path).write_text(json.dumps({'fixture_only': True,
        'response': 'Use a focal garden comparison, restrained type and useful selection/detail/return.'}))
    product['note_paths'] = sorted(set([*product['note_paths'], path]))
    ids, additions = [], []
    for name, direction in [('composition', 'A single focal comparison and subordinate evidence inspector.'),
                            ('typography', 'Readable hierarchy and aligned exact values in system type.'),
                            ('interaction', 'Select an observation, inspect its source and return retaining identity.')]:
        ident = 'quality-fixture-' + name
        ids.append(ident)
        additions.append({'id': ident, 'category': 'experience_quality',
            'purpose': 'Original synthetic quality requirement', 'surfaces': spec['surfaces'],
            'required': True, 'origin': 'user', 'disposition': 'selected',
            'value': {'quality': name, 'direction': direction}, 'asset_ids': [], 'decision_ref': path,
            'contexts': [{'id': 'comparison', 'appearance': 'light', 'state': 'ready'}],
            'product': {'priority': 'must', 'basis': 'user_statement', 'source_refs': [path],
                'acceptance': ['Preserve the stated quality in each concept and its selected handoff.'],
                'suggested_roles': ['app-designer', 'design-systems']}})
    # Preserve the longstanding fixture's first family / last treatment positions.
    spec['requirements'][-1:-1] = additions
    product['quality_bar'] = {'schema_version': 1, 'requirement_ids': ids}
    return spec


def discovery_spec(root, P):
    """Original synthetic user replies; never a runtime interview shortcut."""
    project = P.load_project(root)[1]
    draft = root / project['design_intent_draft']
    spec = json.loads(draft.read_text())
    if spec.get('product', {}).get('visual_experience'):
        spec = quality_spec(spec, root)
        draft.write_text(json.dumps(spec))
        bootstrap(root, P)
        refresh_request_review(root, P)
        return spec
    note = 'inputs/visual-fixture.json'
    (root / note).write_text(json.dumps({'fixture_only': True, 'role': 'user',
        'response': 'Compare the observations using refined 2D charts.'}))
    product = spec.setdefault('product', {'schema_version': 1, 'scope': 'new_experience',
        'discovery': 'sufficient', 'note_paths': []})
    product['note_paths'] = sorted(set([*product['note_paths'], note]))
    for ident, value in [('visual-fixture-family', {'family': 'compare_track'}),
                         ('visual-fixture-treatment', {'treatment': 'refined_2d'})]:
        spec['requirements'].append({'id': ident, 'category': 'visual_experience',
            'purpose': 'Original synthetic comparative discovery', 'surfaces': spec['surfaces'],
            'required': True, 'origin': 'user', 'disposition': 'selected', 'value': value,
            'asset_ids': [], 'decision_ref': note, 'contexts': [
                {'id': 'comparison', 'appearance': 'light', 'state': 'ready'}],
            'product': {'priority': 'must', 'basis': 'user_statement', 'source_refs': [note],
                'acceptance': ['Exact comparisons remain readable.'],
                'suggested_roles': ['product-owner', 'app-designer']}})
    product['visual_experience'] = {'schema_version': 1,
        'family_requirement_ids': ['visual-fixture-family'],
        'follow_up': {'disposition': 'answered', 'requirement_ids': ['visual-fixture-treatment']}}
    spec = quality_spec(spec, root)
    draft.write_text(json.dumps(spec))
    bootstrap(root, P)
    refresh_request_review(root, P)
    return spec


def discovery_request(root, P, brief):
    project = P.load_project(root)[1]
    if project.get('design_intent'):
        spec = P.intent_helper().load_selected(root)['spec']
        bootstrap(root, P)
        refresh_request_review(root, P)
    else:
        spec = discovery_spec(root, P)
    index = len(list((root / 'contracts').glob('visual-snapshot-*.json')))
    snapshot = 'contracts/visual-snapshot-' + str(index) + '.json'
    (root / snapshot).write_text(json.dumps(spec))
    return {'stage': 'brief', 'discovery_version': 1,
            'evidence': {'brief': brief, 'intent': snapshot}}


def concept_options(root, P, ids, theses=None):
    project = P.load_project(root)[1]
    spec = (P.intent_helper().load_selected(root)['spec'] if project.get('design_intent') else
            P.read_json(root / project['design_intent_draft'])[0])
    options = []
    for index, ident in enumerate(ids):
        visual = 'evidence/concept-' + ident + '.svg'
        (root / visual).write_text('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200">'
            '<rect id="focal-chart" x="20" y="20" width="' + str(40 + index * 30) +
            '" height="80" fill="#426c73"/><text x="20" y="145">Garden ' + str(index + 1) +
            ' · 2025 · Unavailable</text></svg>')
        path = 'evidence/concept-' + ident + '.json'
        (root / path).write_text(json.dumps({'schema_version': 1, 'kind': 'analyst_concept_manifest',
            'option_id': ident, 'surface': spec['surfaces'][0],
            'analytical_scope': 'Same synthetic garden observations and missing values',
            'structure': ['Observation-first list and inspector', 'Period-first investigation', 'Coverage-first evidence notebook'][index],
            'primary_interaction': ['Select observation and inspect detail', 'Choose period then inspect its observations', 'Choose missing evidence issue then open its record'][index],
            'quality_coverage': [{'requirement_id': i, 'implementation': 'Retain source quality direction ' + i,
                                  'visual_locator': 'SVG focal-chart'} for i in spec['product']['quality_bar']['requirement_ids']],
            'treatment_coverage': [{'requirement_id': i, 'implementation': 'Use the selected comparison treatment',
                                   'visual_locator': 'SVG focal-chart'} for i in
                                  spec['product']['visual_experience']['follow_up']['requirement_ids']
                                  if spec['product']['visual_experience']['follow_up']['disposition'] != 'not_applicable'],
            'representative': {'path': visual, 'evidence_kind': 'static_source',
                'state': 'Populated synthetic observation and missing-value example', 'labels': ['2025', 'Unavailable']},
            'responsive': 'Stage the index and inspector while preserving selected identity.',
            'constraints': {'feasibility': 'Original first-party static SVG is feasible',
                'assets': 'No imagery selected', 'dependencies': 'No external runtime dependency selected',
                'observation_limits': 'Static source only; render and native unobserved'}}))
        if len(spec['surfaces']) > 1:
            original = json.loads((root / path).read_text())
            children = []
            for surface in spec['surfaces']:
                child = copy.deepcopy(original)
                child['surface'] = surface
                child_visual = visual.replace('.svg', '-' + surface + '.svg')
                (root / child_visual).write_text((root / visual).read_text().replace('Garden ', surface + ' Garden '))
                child['representative']['path'] = child_visual
                child_path = path.replace('.json', '-' + surface + '.json')
                (root / child_path).write_text(json.dumps(child))
                children.append(child_path)
            (root / path).write_text(json.dumps({'schema_version': 1, 'kind': 'analyst_concept_set',
                'option_id': ident, 'analytical_scope': original['analytical_scope'],
                'structure': original['structure'], 'primary_interaction': original['primary_interaction'],
                'surface_manifests': children}))
        options.append({'id': ident, 'thesis': theses[index] if theses else 'Distinct synthetic garden structure ' + str(index),
                        'evidence': path})
    return options


def selected_handoff(root, P, option, version=None):
    project = P.load_project(root)[1]
    spec = (P.intent_helper().load_selected(root)['spec'] if project.get('design_intent') else
            P.read_json(root / project['design_intent_draft'])[0])
    version = version or 'fixture-' + str(len(list((root / 'contracts').glob('quality-design-*.json'))))
    design_path = 'contracts/quality-design-' + version + '.json'
    destination = {'id': 'main', 'purpose': 'Inspect synthetic garden observations',
        'focal_content': 'The selected garden comparison', 'primary_action': 'Select a mark and inspect evidence',
        'evidence': 'Exact fixture value with source key and unknown state', 'return': 'Restore the selected mark',
        'drill': 'Open the selected source record in a useful inspector',
        'composition': 'Focal plot and subordinate inspector', 'typography': 'System type and aligned values',
        'controls': 'Named selection and return controls', 'responsive': 'Stage plot and detail at narrow width',
        'state_ownership': 'Parent owns selection and query state; detail reflects current key',
        'journey_id': 'inspect-observation',
        'chart_anatomy': {'applicable': True, 'details': 'Shared zero and scale, visible units and exact values, explicit unknowns'}}
    journey = {'id': 'inspect-observation', 'destination_ids': ['main'],
        'entry': 'Open comparison', 'action': 'Select a mark', 'detail': 'Read exact source evidence',
        'return': 'Return to the original mark', 'retained_state': 'Selected stable key and period',
        'recovery': 'Clear unavailable data and allow retry; no silent replacement'}
    design = {'brand_contract': None, 'destinations': [destination], 'journeys': [journey],
        'experience_handoff': {'schema_version': 1,
        'concept_manifest_path': option['evidence'] if isinstance(option['evidence'], str) else option['evidence']['path'],
        'quality_coverage': [{'requirement_id': i, 'implementation': 'Carry the original direction into main',
                             'destination_ids': ['main']} for i in spec['product']['quality_bar']['requirement_ids']]}}
    if len(spec['surfaces']) > 1:
        design['destinations'], design['journeys'] = [], []
        for surface in spec['surfaces']:
            dest, flow = copy.deepcopy(destination), copy.deepcopy(journey)
            dest.update(id='main-' + surface, surface=surface, journey_id='inspect-' + surface)
            flow.update(id='inspect-' + surface, destination_ids=[dest['id']])
            design['destinations'].append(dest)
            design['journeys'].append(flow)
        for row in design['experience_handoff']['quality_coverage']:
            row['destination_ids'] = [d['id'] for d in design['destinations']]
    (root / design_path).write_text(json.dumps(design))
    for selected in spec['selections']:
        selected['design_path'] = design_path
        selected['brand_path'] = None
    spec_path = 'contracts/quality-selected-spec-' + version + '.json'
    (root / spec_path).write_text(json.dumps(spec))
    P.intent_helper().select(root, root / spec_path, 'contracts/quality-selected-intent-' + version + '.json')
    refresh_request_review(root, P)
    return design_path


class Host:
    def __init__(self, P):
        self.P, self.grants = P, {}

    def verify_choice(self, binding, receipt_ref):
        return self.grants.get((self.P.canonical(binding), receipt_ref))


class Lifecycle:
    def __init__(self, root, P, *, historical=False):
        self.root, self.P, self.host = root, P, Host(P)
        self.historical = historical
        self.S = P.routing_helper('stage_gates')
        self.counter = 0
        if historical:
            project = P.load_project(root)[1]
            assert 'workflow_quality_policy' not in project and project.get('design_intent')
        else:
            bootstrap(root, P)

    def evidence(self, name, content=None):
        path = 'evidence/gate-fixture-' + name + '.txt'
        (self.root / path).write_text(content or 'Original synthetic evidence for ' + name)
        return path

    def stage(self, stage):
        request = {'stage': stage, 'evidence': {k: self.evidence(stage + '-' + k)
                   for k in self.S.EVIDENCE[stage]}}
        if stage == 'access':
            request.update(source_scope='Synthetic observations', user_identity='fixture-user')
        elif stage == 'analysis':
            request.update(analyst='analyst', bi_engineer='bi-engineer')
        elif stage == 'narrative':
            request.update(storyteller='storyteller', analyst='analyst')
        elif stage == 'brief':
            request = discovery_request(self.root, self.P, request['evidence']['brief'])
        elif stage == 'options':
            self.P.stage_require(self.root, 'options')
            request['options'] = concept_options(self.root, self.P, ['option-' + str(i) for i in range(3)])
        elif stage == 'design' and self.historical:
            request['resolved'] = True
        elif stage == 'design':
            self.P.stage_require(self.root, 'design')
            request['resolved'] = True
            ident = next(e['payload']['option_id'] for e in
                         reversed(self.P.read_json(self.root / self.S.JOURNAL)[0]['events']) if e['stage'] == 'choice')
            request['evidence']['design'] = selected_handoff(self.root, self.P,
                {'id': ident, 'evidence': 'evidence/concept-' + ident + '.json'})
        return self.P.stage_record(self.root, request)

    def through(self, end='design'):
        if self.historical:
            return self.historical_journal(end)
        for stage in self.S.STAGES:
            if stage == 'choice':
                binding = self.P.stage_status(self.root)['choice_bindings']['option-1']
                receipt = 'synthetic-user-choice-event'
                self.host.grants[(self.P.canonical(binding), receipt)] = 'fixture-user'
                self.P.stage_record(self.root, {'stage': stage, 'option_id': 'option-1', 'receipt_ref': receipt})
            else:
                self.stage(stage)
            if stage == end:
                break

    def historical_journal(self, end):
        """Original pre-policy test bytes, not a production legacy-record route."""
        P, S, root = self.P, self.S, self.root
        project = P.load_project(root)[1]
        assert not (root / S.JOURNAL).exists()
        journal = {'schema_version': 1, 'kind': S.KIND, 'project_id': project['id'],
                   'engagement': str(root), 'events': []}
        previous = P.digest(P.canonical({'project_id': project['id'], 'engagement': str(root), 'policy': S.POLICY}))
        current = {}
        def pin(path):
            data = (root / path).read_bytes()
            return {'path': path, 'sha256': P.digest(data), 'bytes': len(data)}
        for stage in S.STAGES:
            payload = {'evidence': {k: pin(self.evidence(stage + '-' + k)) for k in S.EVIDENCE.get(stage, {})}}
            if stage == 'access':
                payload.update(source_scope='Historical synthetic scope', user_identity='fixture-user')
            elif stage == 'analysis':
                payload.update(analyst='analyst', bi_engineer='bi-engineer')
            elif stage == 'narrative':
                payload.update(storyteller='storyteller', analyst='analyst')
            elif stage == 'options':
                payload['options'] = [{'id': 'option-' + str(i), 'thesis': 'Original historical synthetic option ' + str(i),
                    'evidence': pin(self.evidence('old-option-' + str(i)))} for i in range(3)]
            elif stage == 'choice':
                receipt = 'synthetic-user-choice-event'
                binding = S._binding(root, project, current['options'], 'option-1')
                self.host.grants[(P.canonical(binding), receipt)] = 'fixture-user'
                payload = {'option_id': 'option-1', 'receipt_ref': receipt, 'subject': 'fixture-user'}
            elif stage == 'design':
                payload.update(resolved=True, selected_intent=project['design_intent'])
            index = S.STAGES.index(stage)
            event = {'sequence': len(journal['events']) + 1, 'stage': stage, 'previous_sha256': previous,
                'predecessor_sha256': current[S.STAGES[index - 1]]['sha256'] if index else None,
                'recorded_at': datetime.now(timezone.utc).isoformat(), 'payload': payload}
            event['sha256'] = P.digest(P.canonical(event))
            journal['events'].append(event)
            current[stage], previous = event, event['sha256']
            if stage == end:
                break
        P.write_json(root / S.JOURNAL, journal)

    def reviews(self, outcome='resolved'):
        self.counter += 1
        current = self.P.stage_status(self.root)['candidate']
        for scope in self.S.REVIEW_SCOPES:
            self.P.stage_record(self.root, {'stage': 'review', 'scope': scope, 'reviewer': scope + '-reviewer',
                'iteration_sha256': current['event_sha256'], 'candidate_sha256': current['candidate_sha256'],
                'outcome': outcome, 'basis': 'source', 'evidence': {
                    'review': self.evidence('review-' + str(self.counter) + '-' + scope)}})


def pre_policy_project(root, P):
    """Represent a historical engagement in compatibility tests, never a user option."""
    project = P.load_project(root)[1]
    project.pop('stage_gate_policy', None)
    project.pop('workflow_quality_policy', None)
    P.write_json(root / 'project.json', project, replace=True)
