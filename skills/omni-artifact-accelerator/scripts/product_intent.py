"""Readable product intent projections; no second authority, dispatch or approval."""
from datetime import datetime, timezone
import html
import importlib.util
import json
from pathlib import Path

_s = importlib.util.spec_from_file_location('product_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_s)
_s.loader.exec_module(P)
SCOPES = {'new_experience', 'material_redesign', 'migration', 'focused_repair'}
BASES = {'user_statement': 'user', 'reused_decision': 'reused', 'inference': 'proposal',
         'recommendation': 'proposal', 'unresolved': 'proposal'}


def validate(spec, need, relative, roles):
    """Additive annotations in the existing canonical intent, never a new ledger."""
    product = spec.get('product')
    if 'product' not in spec:
        need(not any('product' in r for r in spec['requirements']), 'product_context_required')
        return
    need(type(product) is dict and {'schema_version', 'scope', 'discovery', 'note_paths'} <= set(product)
         and set(product) <= {'schema_version', 'scope', 'discovery', 'note_paths', 'source_inventory_path'},
         'product_fields_invalid')
    need(type(product['schema_version']) is int and product['schema_version'] == 1, 'product_version_invalid')
    need(product['scope'] in SCOPES and product['discovery'] in
         {'sufficient', 'material_questions_open', 'reused_context', 'focused_repair'}, 'product_scope_invalid')
    notes = product['note_paths']
    need(type(notes) is list and notes and len(notes) <= 32 and all(type(n) is str for n in notes)
         and len(set(notes)) == len(notes), 'product_notes_required')
    for path in notes:
        relative(path)
        need(path.startswith(('inputs/', 'evidence/')), 'product_notes_private_engagement_path_required')
    if 'source_inventory_path' in product:
        path = relative(product['source_inventory_path'])
        need(path.startswith('evidence/'), 'source_inventory_evidence_path_required')
    for req in spec['requirements']:
        item = req.get('product')
        # Existing technical/brand requirements may remain unannotated and visible.
        if 'product' not in req:
            continue
        need(type(item) is dict and {'priority', 'basis', 'source_refs', 'acceptance', 'suggested_roles'} <= set(item)
             and set(item) <= {'priority', 'basis', 'source_refs', 'acceptance', 'suggested_roles', 'alternative'},
             'product_requirement_fields_invalid')
        need(item['priority'] in {'must', 'should', 'could'} and item['basis'] in BASES,
             'product_priority_or_basis_invalid')
        need(req['origin'] == BASES[item['basis']], 'product_attribution_conflicts_with_origin')
        need(item['priority'] != 'must' or req['required'], 'product_must_requires_required')
        for key in ('source_refs', 'acceptance', 'suggested_roles'):
            values = item[key]
            need(type(values) is list and values and len(values) <= 64 and
                 all(type(v) is str and 0 < len(v.strip()) <= 8192 for v in values)
                 and len(set(values)) == len(values), 'product_' + key + '_invalid')
        need(set(item['suggested_roles']) <= set(roles), 'product_role_unknown')
        need(all(ref.split('#', 1)[0] in notes for ref in item['source_refs']), 'product_source_must_reference_notes')
        if 'alternative' in item:
            alt = item['alternative']
            need(type(alt) is dict and set(alt) == {'unavailable_method', 'preserved_outcome', 'feasible_alternative', 'remaining_gap'}
                 and all(type(v) is str and 0 < len(v.strip()) <= 8192 for v in alt.values()),
                 'product_alternative_must_preserve_outcome_and_gap')


def clean(value):
    """Render supplied content as escaped prose, never HTML, images or active links."""
    if type(value) is not str:
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    value = ''.join(c if ord(c) >= 32 or c in '\n\t' else ' ' for c in value)
    value = html.escape(value, quote=True)
    for char in ('\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '!', '|', '>'):
        value = value.replace(char, '\\' + char)
    return value.replace('\n', ' / ').replace('\t', ' ')


def render(project, state, generated_at):
    spec = P.intent_helper().read_record(project[0], state['selected'])['spec']
    product = spec['product']
    rows = ['# Product North Star', '', clean(project[1]['name']), '',
            'Generated: ' + generated_at, 'Source version: ' + clean(state['selected']['path']),
            'Source SHA-256: ' + state['selected']['sha256'], '',
            'This is a generated view of the selected design intent. Selection records a working choice; '
            'it does not establish user approval, native verification or business acceptance.', '',
            'Edits here are proposals. Reconcile them into a new intent version and regenerate this view.', '',
            'Scope: ' + product['scope'] + ' | Discovery: ' + product['discovery'], '',
            '## Evidence notes', '']
    rows.extend('- ' + clean(path) for path in product['note_paths'])
    if product.get('source_inventory_path'):
        rows.extend(['', 'Source capability inventory: ' + clean(product['source_inventory_path']),
                     'Inventory dispositions describe usable depth and gaps; they do not approve scope or prove source completeness.'])
    rows.extend(['', '## Requirements, experience promise and success criteria', ''])
    for req in spec['requirements']:
        item = req.get('product', {})
        rows.extend(['### ' + clean(req['id']) + ': ' + clean(req['purpose']), '',
            'Category: ' + clean(req['category']) + ' | Priority: ' + item.get('priority', 'unclassified') +
            ' | State: ' + req['disposition'] + ' | Basis: ' + item.get('basis', req['origin']), '',
            'Surfaces: ' + ', '.join(req['surfaces']),
            'Intent: ' + clean(req.get('value')), 'Decision reference: ' + clean(req.get('decision_ref')), ''])
        for label, key in (('Source', 'source_refs'), ('Observable acceptance', 'acceptance'),
                           ('Suggested specialist', 'suggested_roles')):
            rows.extend('- ' + label + ': ' + clean(value) for value in item.get(key, []))
        for key, value in item.get('alternative', {}).items():
            rows.append('- ' + key.replace('_', ' ').capitalize() + ': ' + clean(value))
        rows.append('')
    rows.extend(['## Current design and brand selections', ''])
    for selected in spec['selections']:
        rows.append('- ' + selected['surface'] + ': design ' + clean(selected.get('design_path')) +
                    '; brand ' + clean(selected.get('brand_path')))
    rows.extend(['', '## Unresolved obligations', ''])
    unresolved = [r for r in spec['requirements'] if r['disposition'] in {'unresolved', 'deferred'}]
    rows.extend('- ' + clean(r['id']) + ': ' + r['disposition'] + ' — ' + clean(r['purpose']) for r in unresolved)
    if not unresolved:
        rows.append('No recorded unresolved requirements. This does not prove completeness or acceptance.')
    rows.extend(['', 'Product fit, creative craft and numerical/technical verification are separate reviews.',
                 'No fixed layout, media, chart count, 3D feature or animation is implied.', ''])
    return ('\n'.join(rows)).encode('utf-8')


def generate(root, output):
    root, project = P.load_project(root)
    state = P.intent_helper().check(root)
    P.need(state['status'] == 'consistent' and state['selected'], 'current selected intent required')
    record = P.intent_helper().load_selected(root)
    P.need('product' in record['spec'], 'product annotations required in selected intent')
    P.intent_helper().relative(output)
    P.need(output.startswith('deliverables/') and output.endswith('.md'), 'new deliverables Markdown path required')
    history = project.setdefault('product_brief_history', [])
    P.need(type(history) is list, 'product projection history must be a list')
    generated_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    raw = render((root, project), state, generated_at)
    P.need(len(raw) <= P.PACKET_BYTES, 'North Star exceeds handoff size; reduce recorded prose')
    P.private_write(root / output, raw)
    receipt = {'schema_version': 1, 'kind': 'analyst_product_projection', 'source_intent': state['selected'],
               'generated_at': generated_at, 'brief': P.intent_helper().pin(root, output)}
    history.append(receipt)
    project['product_brief'] = receipt
    P.write_json(root / 'project.json', project, replace=True)
    return check(root)


def check(root):
    root, project = P.load_project(root)
    state = P.intent_helper().check(root)
    result = {'status': 'not_assessed', 'enabled': False, 'scope': None, 'discovery': None, 'selected_intent': state['selected'],
              'brief': None, 'paths': [], 'requirements': [], 'findings': [],
              'authority': 'projection_of_selected_intent_only', 'claims_authenticated': False,
              'dispatch_authorized': False, 'business_acceptance': 'not_assessed'}
    try:
        if not state['selected']:
            P.need(state['status'] != 'inconsistent', 'current_intent_inconsistent')
            return result
        # Validate the selected record before deciding opt-in. Stale design inputs
        # in a genuine legacy engagement must not gate unrelated semantic work.
        spec = P.intent_helper().load_selected(root)['spec']
        if 'product' not in spec:
            return result
        P.need(state['status'] != 'inconsistent', 'current_intent_inconsistent')
        result.update(enabled=True, scope=spec['product']['scope'], discovery=spec['product']['discovery'], requirements=spec['requirements'])
        receipt = project.get('product_brief')
        P.need(type(receipt) is dict and set(receipt) == {'schema_version', 'kind', 'source_intent', 'generated_at', 'brief'},
               'product_projection_missing_or_invalid')
        P.need(type(receipt['schema_version']) is int and receipt['schema_version'] == 1
               and receipt['kind'] == 'analyst_product_projection', 'product_projection_version_invalid')
        P.need(receipt['source_intent'] == state['selected'], 'product_projection_stale')
        timestamp = receipt['generated_at']
        P.need(type(timestamp) is str and len(timestamp) <= 40 and
               datetime.fromisoformat(timestamp).utcoffset() is not None, 'product_projection_timestamp_invalid')
        brief = receipt['brief']
        P.need(P.intent_helper().history_pin_valid(brief) and brief['path'].startswith('deliverables/')
               and brief['path'].endswith('.md'), 'product_projection_pin_invalid')
        P.need(P.intent_helper().pin(root, brief['path']) == brief, 'product_projection_bytes_changed')
        raw = P.relative_file(root, brief['path']).read_bytes()
        P.need(raw == render((root, project), state, timestamp), 'product_projection_differs_from_intent')
        if spec['product'].get('source_inventory_path'):
            inventory = P.routing_helper('delivery_workflow').inventory_check(root, state)
            P.need(inventory['status'] == 'consistent', 'source_inventory_not_current: ' + '; '.join(inventory['findings']))
        result.update(status='consistent', brief=brief,
                      paths=[brief['path'], *spec['product']['note_paths']])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result['status'] = 'inconsistent'
        result['findings'].append(str(exc))
    return result


def packet_context(root, role):
    result = check(root)
    # Legacy projects stay usable. PO can receive current intent to repair a missing projection.
    P.need(result['status'] != 'inconsistent' or role == 'product-owner',
           'product_context_not_current: ' + '; '.join(result['findings']))
    if role != 'product-owner':
        result['paths'] = [result['brief']['path']] if result['brief'] else []
    selected = []
    for req in result.pop('requirements'):
        product = req.get('product', {})
        if role == 'product-owner' or role in product.get('suggested_roles', []) or req.get('delivery', {}).get('owner') == role:
            selected.append({'id': req['id'], 'priority': product.get('priority'), 'basis': product.get('basis', req['origin']),
                             'disposition': req['disposition'], 'source_refs': product.get('source_refs', []),
                             'acceptance': product.get('acceptance', []),
                             'alternative': product.get('alternative'), 'suggested_roles': product.get('suggested_roles', [])})
    result['role_slice'] = selected
    result['note'] = 'Suggested scope only; the orchestrator owns dispatch. Return coverage, conflicts and alternatives. '
    result['note'] += 'Read the complete current intent; unassigned requirements remain obligations.'
    return result
