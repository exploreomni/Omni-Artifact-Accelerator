"""Synthetic host and evidence for tests only; never a production approval adapter."""
import json


def discovery_spec(root, P):
    """Original synthetic user replies; never a runtime interview shortcut."""
    project = P.load_project(root)[1]
    draft = root / project['design_intent_draft']
    spec = json.loads(draft.read_text())
    if spec.get('product', {}).get('visual_experience'):
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
    draft.write_text(json.dumps(spec))
    return spec


def discovery_request(root, P, brief):
    project = P.load_project(root)[1]
    if project.get('design_intent'):
        spec = P.intent_helper().load_selected(root)['spec']
    else:
        spec = discovery_spec(root, P)
    index = len(list((root / 'contracts').glob('visual-snapshot-*.json')))
    snapshot = 'contracts/visual-snapshot-' + str(index) + '.json'
    (root / snapshot).write_text(json.dumps(spec))
    return {'stage': 'brief', 'discovery_version': 1,
            'evidence': {'brief': brief, 'intent': snapshot}}


class Host:
    def __init__(self, P):
        self.P, self.grants = P, {}

    def verify_choice(self, binding, receipt_ref):
        return self.grants.get((self.P.canonical(binding), receipt_ref))


class Lifecycle:
    def __init__(self, root, P):
        self.root, self.P, self.host = root, P, Host(P)
        self.S = P.routing_helper('stage_gates')
        self.counter = 0

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
            request['options'] = [{'id': 'option-' + str(i), 'thesis': 'Distinct original concept ' + str(i),
                                   'evidence': self.evidence('option-' + str(i))} for i in range(3)]
        elif stage == 'design':
            request['resolved'] = True
        return self.P.stage_record(self.root, request)

    def through(self, end='design'):
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
    P.write_json(root / 'project.json', project, replace=True)
