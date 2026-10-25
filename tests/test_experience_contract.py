"""Original source-only quality contracts; no real user or rendered observations."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location('quality_product_tests', ROOT / 'skills/omni-artifact-accelerator/scripts/product_intent.py')
N = importlib.util.module_from_spec(loader)
loader.loader.exec_module(N)
P, E = N.P, N.E


def requirement(ident='quality', value=None, basis='user_statement', disposition='selected', surfaces=None):
    source = 'inputs/quality.json#' + ident
    return {'id': ident, 'category': 'experience_quality', 'purpose': 'Inspect original garden observations.',
        'surfaces': surfaces or ['app'], 'required': True,
        'origin': {'user_statement': 'user', 'reused_decision': 'reused', 'recommendation': 'proposal',
                   'inference': 'proposal', 'unresolved': 'proposal'}[basis],
        'disposition': disposition, 'value': value or {'quality': 'composition', 'direction': 'One focal comparison and useful evidence inspection.'},
        'asset_ids': [], 'decision_ref': source if disposition in ('selected', 'explicitly_omitted') else None,
        'contexts': [{'id': 'ready', 'appearance': 'light', 'state': 'ready'}],
        'product': {'priority': 'must', 'basis': basis, 'source_refs': [source],
                    'acceptance': ['The garden comparison stays focal when the evidence inspector opens.'],
                    'suggested_roles': ['app-designer']}}


def specimen(surfaces=None):
    surfaces = surfaces or ['app']
    spec = P.intent_helper().starter(surfaces, 'none')
    spec['product'] = {'schema_version': 1, 'scope': 'new_experience', 'discovery': 'sufficient',
        'note_paths': ['inputs/quality.json'], 'quality_bar': {'schema_version': 1, 'requirement_ids': ['quality']}}
    spec['requirements'] = [requirement(surfaces=surfaces)]
    return spec


def coverage(ident='quality'):
    return {'requirement_id': ident, 'implementation': 'Focal plot retains space during inspection.', 'visual_locator': 'focal-chart'}


def concept(surface='app'):
    return {'schema_version': 1, 'kind': 'analyst_concept_manifest', 'option_id': 'a', 'surface': surface,
        'analytical_scope': 'Original fictional garden measurements in 2025',
        'structure': 'Focal comparison with an evidence inspector', 'primary_interaction': 'Select a mark and inspect exact evidence',
        'quality_coverage': [coverage()], 'treatment_coverage': [],
        'representative': {'path': 'concepts/a.svg', 'evidence_kind': 'static_source',
                           'state': 'Comparison with an unavailable measurement', 'labels': ['2025', 'Unavailable']},
        'responsive': 'Inspection becomes a focused destination, retaining selected identity.',
        'constraints': {'feasibility': 'First-party SVG', 'assets': 'No imagery selected',
                        'dependencies': 'No runtime library required', 'observation_limits': 'Source only, not rendered.'}}


SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="240"><rect id="focal-chart" x="10" y="50" width="170" height="90"/><text x="10" y="180">2025 garden observations · Unavailable</text></svg>'


def design():
    return {'destinations': [{'id': 'main', 'purpose': 'Inspect garden observations', 'focal_content': 'Garden comparison',
        'primary_action': 'Select a mark', 'evidence': 'Exact value and source key', 'drill': 'Inspect source evidence',
        'return': 'Restore selected mark focus', 'composition': 'Comparison anchors the reading order; inspector is subordinate',
        'typography': 'System type with aligned values and distinct labels',
        'chart_anatomy': {'applicable': True, 'details': 'Common baseline, named units, exact values and visible unknowns'},
        'controls': 'Named mark selection and return', 'responsive': 'Separate inspection destination on narrow space',
        'state_ownership': 'Parent owns selection; failed refresh leaves no stale claim', 'journey_id': 'inspect'}],
        'journeys': [{'id': 'inspect', 'destination_ids': ['main'], 'entry': 'Open comparison', 'action': 'Select a mark',
            'detail': 'Read exact source evidence', 'return': 'Restore mark focus', 'retained_state': 'Stable key and period',
            'recovery': 'Unknown state remains explicit; retry keeps scope'}],
        'experience_handoff': {'schema_version': 1, 'concept_manifest_path': 'concepts/a.json',
            'quality_coverage': [{'requirement_id': 'quality', 'implementation': 'Focal comparison remains visible',
                                  'destination_ids': ['main']}]}}


def png():
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00')) + chunk(b'IEND', b'')


class QualityIntentTests(unittest.TestCase):
    def test_legacy_and_unresolved_are_readable_not_ready(self):
        self.assertEqual(N.quality_check({'requirements': []})['status'], 'not_assessed')
        spec = specimen()
        spec['requirements'][0]['disposition'] = 'unresolved'
        spec['requirements'][0]['decision_ref'] = None
        spec['requirements'][0]['value'] = None
        P.intent_helper().validate(spec, {'surfaces': ['app']})
        self.assertEqual(N.quality_check(spec)['status'], 'unresolved')
        spec['requirements'] = []
        spec['product']['quality_bar']['requirement_ids'] = []
        self.assertEqual(N.quality_check(spec)['status'], 'unresolved')

    def test_user_reuse_and_scoped_delegation_keep_provenance(self):
        for basis in ('user_statement', 'reused_decision'):
            spec = specimen()
            spec['requirements'][0] = requirement(basis=basis)
            P.intent_helper().validate(spec, {'surfaces': ['app']})
            self.assertEqual(N.quality_check(spec)['status'], 'ready')
        spec['requirements'][0] = requirement(basis='recommendation')
        self.assertEqual(N.quality_check(spec)['status'], 'unresolved')
        spec['product']['quality_bar']['delegation_requirement_id'] = 'delegate'
        spec['requirements'].append(requirement('delegate', {'delegation_scope': 'experience_quality'}))
        self.assertEqual(N.quality_check(spec)['status'], 'ready')
        self.assertEqual(N.quality_context(spec)['requirements'][1]['origin'], 'proposal')
        spec['requirements'][1] = requirement('delegate', {'delegation_scope': 'experience_quality'}, 'inference')
        with self.assertRaisesRegex(ValueError, 'actual_answer_or_delegation'):
            N.quality_check(spec)

    def test_delegation_and_quality_must_cover_each_surface(self):
        spec = specimen(['app', 'dashboard'])
        spec['requirements'][0] = requirement(basis='recommendation', surfaces=['app', 'dashboard'])
        spec['product']['quality_bar']['delegation_requirement_id'] = 'delegate'
        spec['requirements'].append(requirement('delegate', {'delegation_scope': 'experience_quality'}))
        with self.assertRaisesRegex(ValueError, 'delegation_surface_missing'):
            N.quality_check(spec)
        spec['requirements'][0]['surfaces'] = ['app']
        self.assertEqual(N.quality_check(spec)['status'], 'unresolved')

    def test_strict_version_references_and_active_index(self):
        mutations = [lambda s: s['product']['quality_bar'].update(schema_version=True),
                     lambda s: s['product']['quality_bar'].update(hidden_answer=True),
                     lambda s: s['product']['quality_bar'].update(requirement_ids=['missing']),
                     lambda s: s['requirements'].append(requirement('unindexed', {'quality': 'depth', 'direction': 'Layered inspection'})),
                     lambda s: s['requirements'][0]['product'].update(acceptance=[])]
        for change in mutations:
            spec = specimen()
            change(spec)
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                N.quality_check(spec)
        spec = specimen()
        spec['requirements'].append(requirement('unrelated', {'quality': 'water_grade'}))
        self.assertEqual(N.quality_check(spec)['status'], 'ready')

    def test_context_retains_decisions_but_not_later_implementation(self):
        spec = specimen()
        before = N.quality_context(spec)
        row = spec['requirements'][0]
        row['delivery'] = {'owner': 'app-engineer', 'destinations': ['main']}
        row['contexts'].append({'id': 'error', 'appearance': 'light', 'state': 'error', 'viewport': [640, 480]})
        row['product']['suggested_roles'] = ['qa-analyst']
        self.assertEqual(N.quality_context(spec), before)
        for change in (lambda r: r['value'].update(direction='Different composition'),
                       lambda r: r.update(required=False),
                       lambda r: r['product'].update(acceptance=['Different observable behavior']),
                       lambda r: r.update(purpose='Different job')):
            changed = copy.deepcopy(spec)
            change(changed['requirements'][0])
            self.assertNotEqual(N.quality_context(changed), before)

    def test_adoption_cannot_strip_even_optional_rows_but_sourced_omission_works(self):
        before = specimen()
        after = copy.deepcopy(before)
        del after['product']['quality_bar']
        with self.assertRaisesRegex(ValueError, 'context_removed'):
            N.validate_quality_transition(before, after)
        after = specimen()
        after['requirements'][0]['required'] = False
        after['requirements'][0]['product']['priority'] = 'could'
        before = copy.deepcopy(after)
        after['product']['quality_bar']['requirement_ids'] = []
        after['requirements'] = []
        with self.assertRaisesRegex(ValueError, 'explicit_omission'):
            N.validate_quality_transition(before, after)
        after['requirements'] = [requirement(disposition='explicitly_omitted')]
        N.validate_quality_transition(before, after)


class ExperienceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'concepts').mkdir()
        (self.root / 'contracts').mkdir()
        (self.root / 'concepts/a.svg').write_text(SVG)
        self.spec = specimen()
        self.write('concepts/a.json', concept())
        self.write('contracts/design.json', design())

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value))

    def test_static_concept_and_handoff_pin_actual_bytes_without_render_claims(self):
        result = N.validate_concept(self.root, 'concepts/a.json', self.spec, P)
        self.assertEqual([p['path'] for p in result['dependencies']], ['concepts/a.json', 'concepts/a.svg'])
        self.assertIn('unassessed', result['metadata']['observation_limit'])
        handoff = N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
        self.assertEqual(handoff['metadata']['destination_ids'], ['main'])
        old = result['dependencies'][-1]['sha256']
        (self.root / 'concepts/a.svg').write_text(SVG.replace('170', '171'))
        self.assertNotEqual(N.validate_concept(self.root, 'concepts/a.json', self.spec, P)['dependencies'][-1]['sha256'], old)

    def test_svg_active_content_external_resources_and_prose_only_rejected(self):
        examples = [SVG.replace('</svg>', '<script>bad()</script></svg>'),
            SVG.replace('<rect ', '<rect onload="bad()" '),
            SVG.replace('</svg>', '<use href="https://invalid.example/x.svg#x"/></svg>'),
            SVG.replace('</svg>', '<style>@import "remote.css";</style></svg>'),
            SVG.replace('</svg>', '<style>rect{fill:url(https://invalid.example)}</style></svg>'),
            '<!DOCTYPE svg [<!ENTITY x "value">]>' + SVG,
            '<svg><text>2025 Unavailable</text></svg>',
            '<svg><rect width="20" height="20"/></svg>',
            SVG.replace('2025', '2099')]
        for value in examples:
            (self.root / 'concepts/a.svg').write_text(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                N.validate_concept(self.root, 'concepts/a.json', self.spec, P)

    def test_unknown_fields_incomplete_coverage_and_escape_paths_fail(self):
        for change in (lambda c: c.update(extra=True), lambda c: c.update(quality_coverage=[]),
                       lambda c: c['representative'].update(path='../outside.svg'),
                       lambda c: c['constraints'].update(dependencies='')):
            c = concept()
            change(c)
            self.write('concepts/a.json', c)
            with self.assertRaises(ValueError):
                N.validate_concept(self.root, 'concepts/a.json', self.spec, P)

    def test_selected_comparison_treatment_requires_demonstration(self):
        self.spec['product']['visual_experience'] = {'schema_version': 1, 'family_requirement_ids': ['family'],
            'follow_up': {'disposition': 'answered', 'requirement_ids': ['treatment']}}
        self.spec['requirements'] += [requirement('family', {'family': 'compare_track'}),
                                     requirement('treatment', {'treatment': 'refined_2d'})]
        with self.assertRaisesRegex(ValueError, 'same_active_quality_coverage'):
            N.validate_concept(self.root, 'concepts/a.json', self.spec, P)
        c = concept()
        c['treatment_coverage'] = [coverage('treatment')]
        self.write('concepts/a.json', c)
        self.assertEqual(N.validate_concept(self.root, 'concepts/a.json', self.spec, P)['metadata']['treatment_requirement_ids'], ['treatment'])

    def test_render_capture_requires_pinned_observation_but_does_not_authenticate_it(self):
        c = concept()
        c['representative'].update(path='concepts/a.png', evidence_kind='rendered_capture')
        (self.root / 'concepts/a.png').write_bytes(png())
        self.write('concepts/a.json', c)
        with self.assertRaisesRegex(ValueError, 'rendered_capture_evidence_required'):
            N.validate_concept(self.root, 'concepts/a.json', self.spec, P)
        c['representative']['observation_path'] = 'concepts/observation.md'
        (self.root / 'concepts/observation.md').write_text('Original synthetic fixture; not a real render observation.')
        self.write('concepts/a.json', c)
        result = N.validate_concept(self.root, 'concepts/a.json', self.spec, P)
        self.assertEqual(len(result['dependencies']), 3)
        self.assertIn('not authenticated', result['metadata']['observation_limit'])
        (self.root / 'concepts/a.png').write_bytes(png()[:-1])
        with self.assertRaises(ValueError):
            N.validate_concept(self.root, 'concepts/a.json', self.spec, P)

    def test_handoff_uses_canonical_rows_and_requires_detail_state_and_return(self):
        for field in ('composition', 'typography', 'controls', 'responsive', 'state_ownership', 'drill', 'return'):
            d = design()
            del d['destinations'][0][field]
            self.write('contracts/design.json', d)
            with self.subTest(field=field), self.assertRaises(ValueError):
                N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
        d = design()
        d['journeys'][0]['destination_ids'] = ['unknown']
        self.write('contracts/design.json', d)
        with self.assertRaisesRegex(ValueError, 'journey_destination_unknown'):
            N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
        d = design()
        d['destinations'][0]['chart_anatomy'] = {'applicable': False, 'rationale': 'This destination uses a source evidence list.'}
        self.write('contracts/design.json', d)
        N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)

    def test_motion_and_imagery_only_required_when_selected(self):
        for quality, block in [('motion', {'trigger': 'Inspection opens', 'purpose': 'Orient the same selected identity',
            'continuity': 'Keep identity stable', 'interruption': 'Latest choice wins', 'reduced_motion': 'Immediate update'}),
            ('imagery', {'role': 'Atmosphere', 'placement': 'Supporting region', 'crop': 'Retain focal subject',
             'alternative_text': 'Decorative', 'fallback': 'Retain readable background', 'narrow': 'Omit without evidence loss'})]:
            self.spec = specimen()
            self.spec['requirements'].append(requirement(quality, {'quality': quality, 'direction': 'Selected task support', 'usage': 'included'}))
            self.spec['product']['quality_bar']['requirement_ids'].append(quality)
            c, d = concept(), design()
            c['quality_coverage'].append(coverage(quality))
            d['experience_handoff']['quality_coverage'].append({'requirement_id': quality, 'implementation': 'Task support', 'destination_ids': ['main']})
            self.write('concepts/a.json', c)
            self.write('contracts/design.json', d)
            with self.assertRaisesRegex(ValueError, 'selected_' + quality):
                N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
            d['destinations'][0][quality] = block
            self.write('contracts/design.json', d)
            N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
            self.spec['requirements'][-1]['value']['usage'] = 'omitted'
            with self.assertRaisesRegex(ValueError, 'omitted_' + quality):
                N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)

    def test_both_surfaces_need_two_concrete_children_and_canonical_destination_coverage(self):
        self.spec = specimen(['app', 'dashboard'])
        with self.assertRaisesRegex(ValueError, 'all_product_surfaces'):
            N.validate_concept(self.root, 'concepts/a.json', self.spec, P)
        dashboard = concept('dashboard')
        dashboard['representative']['path'] = 'concepts/dashboard.svg'
        (self.root / 'concepts/dashboard.svg').write_text(SVG.replace('170', '240'))
        self.write('concepts/dashboard.json', dashboard)
        wrapper = {'schema_version': 1, 'kind': 'analyst_concept_set', 'option_id': 'a',
            'analytical_scope': concept()['analytical_scope'], 'structure': 'Companion monitoring and investigation',
            'primary_interaction': 'Monitor dashboard, inspect in App',
            'surface_manifests': ['concepts/a.json', 'concepts/dashboard.json']}
        self.write('concepts/set.json', wrapper)
        result = N.validate_concept(self.root, 'concepts/set.json', self.spec, P)
        self.assertEqual(result['metadata']['surfaces'], ['app', 'dashboard'])
        self.assertEqual(len(result['metadata']['representative_artifacts']), 2)
        self.assertEqual(len(result['dependencies']), 5)
        d = design()
        d['experience_handoff']['concept_manifest_path'] = 'concepts/set.json'
        d['destinations'][0]['surface'] = 'app'
        second = copy.deepcopy(d['destinations'][0])
        second.update(id='monitor', surface='dashboard')
        d['destinations'].append(second)
        d['journeys'][0]['destination_ids'].append('monitor')
        self.write('contracts/design.json', d)
        with self.assertRaisesRegex(ValueError, 'quality_destination_surface_coverage'):
            N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)
        d['experience_handoff']['quality_coverage'][0]['destination_ids'].append('monitor')
        self.write('contracts/design.json', d)
        N.validate_handoff(self.root, 'contracts/design.json', self.spec, P)


if __name__ == '__main__':
    unittest.main()
