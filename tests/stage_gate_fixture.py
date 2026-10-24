"""Synthetic host and evidence for tests only; never a production approval adapter."""
import json


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
