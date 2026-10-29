"""Original report design checks; no renderer, query execution or native writes.

The selected design remains the contract. These checks do not compile RDL,
RDLX-JSON or Crystal definitions and cannot certify pixel-perfect output.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError('report_contract.' + message)


def text(value):
    return type(value) is str and 0 < len(value.strip()) <= 8192


def fields(value, required, label):
    need(type(value) is dict and set(value) == set(required), label + '_fields')


def words(value, keys, label):
    need(all(text(value.get(key)) for key in keys), label + '_text_required')


def rows(value, label, empty=False):
    need(type(value) is list and len(value) <= 128 and (empty or value), label + '_rows')
    ids = set()
    for row in value:
        need(type(row) is dict and text(row.get('id')) and row['id'] not in ids, label + '_identity')
        ids.add(row['id'])
    return value


def number(value, zero=False):
    return type(value) in (int, float) and math.isfinite(value) and (value >= 0 if zero else value > 0)


def validate(value, spec, destinations):
    """Check declared geometry/bindings and retain unknown native capabilities."""
    need(type(value) is dict, 'contract_fields')
    need(type(value.get('schema_version')) is int and
         value['schema_version'] in {1, 2}, 'version')
    version = value['schema_version']
    fields(value, {'schema_version', 'profile', 'paper', 'datasets', 'parameters', 'sections',
                   'outputs', 'data_policy', 'asset_ids', 'capabilities', 'acceptance'} |
                   ({'requirement_bindings'} if version == 2 else set()), 'contract')
    profile = value['profile']
    fields(profile, {'release_label', 'runtime_version', 'authoring_route', 'evidence_path'}, 'profile')
    need(profile['release_label'] == 'Beta', 'beta_label_required')
    need(profile['authoring_route'] in {'unverified', 'native_editor', 'native_ai', 'qualified_api'}, 'authoring_route')
    words(profile, ('runtime_version',), 'profile')
    need(profile['evidence_path'] is None or text(profile['evidence_path']), 'profile_evidence_path')
    need(profile['authoring_route'] == 'unverified' or profile['evidence_path'] is not None,
         'observed_route_evidence_required')
    paper = value['paper']
    fields(paper, {'unit', 'width', 'height', 'orientation', 'margins', 'header_height',
                   'footer_height', 'page_numbering', 'layout_mode'}, 'paper')
    need(paper['unit'] in {'mm', 'in', 'pt'}, 'explicit_paper_unit')
    need(paper['orientation'] in {'portrait', 'landscape'}, 'orientation')
    need(paper['layout_mode'] in {'fixed', 'flow'}, 'paginated_layout_mode')
    need(number(paper['width']) and number(paper['height']), 'paper_dimensions')
    need((paper['width'] <= paper['height']) if paper['orientation'] == 'portrait'
         else (paper['width'] >= paper['height']), 'orientation_dimensions_conflict')
    fields(paper['margins'], {'top', 'right', 'bottom', 'left'}, 'margins')
    need(all(number(v, True) for v in paper['margins'].values()) and
         all(number(paper[k], True) for k in ('header_height', 'footer_height')), 'paper_reserved_space')
    width = paper['width'] - paper['margins']['left'] - paper['margins']['right']
    height = paper['height'] - paper['margins']['top'] - paper['margins']['bottom'] - paper['header_height'] - paper['footer_height']
    need(width > 0 and height > 0, 'no_printable_body')
    words(paper, ('page_numbering',), 'paper')
    datasets = rows(value['datasets'], 'datasets', True)
    for dataset in datasets:
        fields(dataset, {'id', 'query_path', 'grain', 'sort', 'filter_scope', 'totals', 'fields'}, 'dataset')
        words(dataset, ('query_path', 'grain', 'sort', 'filter_scope', 'totals'), 'dataset')
        columns = rows(dataset['fields'], 'fields')
        names = set()
        for column in columns:
            fields(column, {'id', 'report_name', 'type'}, 'field')
            words(column, ('report_name', 'type'), 'field')
            need(column['report_name'] not in names, 'duplicate_report_field_name')
            names.add(column['report_name'])
    by_dataset = {d['id']: d for d in datasets}
    for parameter in rows(value['parameters'], 'parameters', True):
        fields(parameter, {'id', 'dataset_ids', 'value_policy', 'query_binding', 'required', 'multi_value'}, 'parameter')
        need(type(parameter['required']) is bool and type(parameter['multi_value']) is bool, 'parameter_flags')
        ids = parameter['dataset_ids']
        need(type(ids) is list and ids and all(type(i) is str for i in ids) and
             len(ids) == len(set(ids)) and set(ids) <= set(by_dataset), 'parameter_dataset_scope')
        words(parameter, ('value_policy', 'query_binding'), 'parameter')
    destination_ids = {d['id'] for d in destinations if d.get('surface', 'report') == 'report'}
    sections = rows(value['sections'], 'sections')
    for section in sections:
        fields(section, {'id', 'destination_id', 'dataset_id', 'width', 'columns', 'grouping',
                          'repeat_headers', 'keep_together', 'page_breaks', 'overflow', 'empty_state'}, 'section')
        need(section['destination_id'] in destination_ids and (section['dataset_id'] is None or
             section['dataset_id'] in by_dataset), 'section_binding')
        need(number(section['width']) and section['width'] <= width, 'section_exceeds_printable_width')
        words(section, ('grouping', 'repeat_headers', 'keep_together', 'page_breaks', 'overflow', 'empty_state'), 'section')
        columns = rows(section['columns'], 'section_columns', section['dataset_id'] is None)
        need(section['dataset_id'] is not None or not columns, 'static_section_cannot_claim_data_columns')
        source_fields = ({f['id'] for f in by_dataset[section['dataset_id']]['fields']}
                         if section['dataset_id'] is not None else set())
        for column in columns:
            fields(column, {'id', 'field_id', 'width', 'format', 'long_text'}, 'column')
            need(column['field_id'] in source_fields and number(column['width']), 'column_binding')
            words(column, ('format', 'long_text'), 'column')
        need(sum(c['width'] for c in columns) <= section['width'] + 1e-9, 'columns_exceed_section_width')
    need({s['destination_id'] for s in sections} == destination_ids, 'report_destinations_uncovered')
    requirements = {r['id'] for r in spec['requirements'] if 'report' in r['surfaces']}
    capabilities = rows(value['capabilities'], 'capabilities')
    gaps = []
    covered_requirements = set()
    for capability in capabilities:
        fields(capability, {'id', 'requirement_ids', 'behavior', 'status', 'evidence_path',
                            'disposition', 'decision_ref'}, 'capability')
        ids = capability['requirement_ids']
        need(type(ids) is list and ids and all(type(i) is str for i in ids) and
             len(ids) == len(set(ids)) and set(ids) <= requirements, 'capability_requirement_scope')
        covered_requirements.update(ids)
        words(capability, ('behavior',), 'capability')
        need(capability['status'] in {'observed', 'documented', 'unverified', 'unsupported'}, 'capability_status')
        need(capability['disposition'] in {'native', 'approved_alternative', 'deferred'}, 'capability_disposition')
        need(capability['evidence_path'] is None or text(capability['evidence_path']), 'capability_evidence_path')
        need(capability['status'] not in {'observed', 'documented'} or capability['evidence_path'] is not None,
             'capability_evidence_required')
        need(capability['decision_ref'] is None or text(capability['decision_ref']), 'capability_decision')
        need(capability['disposition'] == 'native' or capability['decision_ref'] is not None, 'alternative_needs_actual_decision')
        if capability['status'] != 'observed' or capability['disposition'] != 'native':
            gaps.append({'capability': capability['id'], 'status': capability['status'],
                         'disposition': capability['disposition']})
    required = {r['id'] for r in spec['requirements'] if 'report' in r['surfaces']
                and r.get('required') is True and r.get('disposition') not in {'explicitly_omitted', 'deferred'}}
    need(required <= covered_requirements, 'required_report_capabilities_uncovered')
    formats, capability_ids = set(), {c['id'] for c in capabilities}
    for output in rows(value['outputs'], 'outputs'):
        fields(output, {'id', 'format', 'capability_id', 'pagination', 'sheet_policy', 'filename_policy'}, 'output')
        need(output['format'] in {'pdf', 'print', 'xlsx'} and output['format'] not in formats, 'output_format')
        formats.add(output['format'])
        need(output['capability_id'] in capability_ids, 'output_capability_missing')
        words(output, ('pagination', 'sheet_policy', 'filename_policy'), 'output')
    policy = value['data_policy']
    fields(policy, {'locale', 'timezone', 'as_of', 'caching', 'refresh', 'distribution', 'decision_ref'}, 'data_policy')
    words(policy, tuple(policy), 'data_policy')
    ids = value['asset_ids']
    need(type(ids) is list and all(type(i) is str for i in ids) and len(ids) == len(set(ids))
         and set(ids) <= {a['id'] for a in spec['assets']}, 'asset_scope')
    covered, lanes_by_format = set(), {name: set() for name in formats}
    for case in rows(value['acceptance'], 'acceptance'):
        fields(case, {'id', 'output_format', 'lane', 'scenario', 'expected'} |
               ({'section_ids', 'parameter_ids'} if version == 2 else set()), 'acceptance')
        need(case['output_format'] in formats and case['lane'] in
             {'numerical', 'pagination', 'typography', 'export', 'access', 'performance', 'accessibility'}, 'acceptance_scope')
        words(case, ('scenario', 'expected'), 'acceptance')
        covered.add(case['output_format']); lanes_by_format[case['output_format']].add(case['lane'])
    need(covered == formats and all({'numerical', 'export'} <= lanes_by_format[name]
         and (name == 'xlsx' or 'pagination' in lanes_by_format[name]) for name in formats), 'acceptance_coverage')
    if version == 2:
        validate_bindings(value, spec)
    else:
        gaps.append({'code': 'legacy_report_contract_mapping_unqualified', 'schema_version': 1})
    return {'gaps': gaps, 'printable_width': width, 'printable_height': height,
            'schema_version': version, 'requirement_mapping_qualified': version == 2,
            'native_authoring_qualified': False, 'rendered_quality': 'not_assessed'}


def identifiers(value, allowed, label, empty=True):
    need(type(value) is list and (empty or value) and all(type(i) is str for i in value)
         and len(value) == len(set(value)) and set(value) <= set(allowed), label)
    return set(value)


def validate_bindings(value, spec):
    """Bind the requirement denominator to actual report parts, never capability prose alone."""
    requirements = {r['id']: r for r in spec['requirements'] if 'report' in r['surfaces']}
    sections = {r['id'] for r in value['sections']}
    parameters = {r['id'] for r in value['parameters']}
    outputs = {r['id']: r for r in value['outputs']}
    acceptance = {r['id']: r for r in value['acceptance']}
    for case in acceptance.values():
        identifiers(case['section_ids'], sections, 'acceptance_section_scope')
        identifiers(case['parameter_ids'], parameters, 'acceptance_parameter_scope')
    covered_requirements, covered_sections, covered_parameters, covered_outputs, covered_cases = set(), set(), set(), set(), set()
    for binding in rows(value['requirement_bindings'], 'requirement_bindings'):
        fields(binding, {'id', 'requirement_id', 'section_ids', 'parameter_ids', 'output_ids',
                         'acceptance_ids', 'disposition', 'decision_ref'}, 'requirement_binding')
        ident = binding['requirement_id']
        need(ident in requirements and ident not in covered_requirements, 'requirement_binding_identity')
        covered_requirements.add(ident)
        section_ids = identifiers(binding['section_ids'], sections, 'requirement_section_scope')
        parameter_ids = identifiers(binding['parameter_ids'], parameters, 'requirement_parameter_scope')
        output_ids = identifiers(binding['output_ids'], outputs, 'requirement_output_scope')
        case_ids = identifiers(binding['acceptance_ids'], acceptance, 'requirement_acceptance_scope')
        need(binding['disposition'] in {'implemented', 'deferred', 'explicitly_omitted'}, 'requirement_binding_disposition')
        need(binding['decision_ref'] is None or text(binding['decision_ref']), 'requirement_binding_decision')
        original = requirements[ident]
        if binding['disposition'] != 'implemented':
            need(original.get('disposition') == binding['disposition'] and
                 original.get('origin') in {'user', 'reused'} and text(original.get('decision_ref')) and
                 binding['decision_ref'] == original['decision_ref'], 'omission_requires_matching_actual_decision')
            need(not (section_ids or parameter_ids or output_ids or case_ids), 'omitted_requirement_has_implementation')
            continue
        need(original.get('disposition') == 'selected' and (section_ids or parameter_ids or output_ids)
             and output_ids and case_ids, 'requirement_actual_implementation_required')
        cases = [acceptance[i] for i in case_ids]
        need({c['output_format'] for c in cases} == {outputs[i]['format'] for i in output_ids},
             'requirement_acceptance_output_mismatch')
        need(section_ids <= {s for c in cases for s in c['section_ids']} and
             parameter_ids <= {p for c in cases for p in c['parameter_ids']}, 'requirement_acceptance_part_mismatch')
        covered_sections.update(section_ids); covered_parameters.update(parameter_ids); covered_outputs.update(output_ids)
        covered_cases.update(case_ids)
    need({i for i, r in requirements.items() if r.get('required') is True} <= covered_requirements,
         'required_report_mapping_uncovered')
    need(covered_sections == sections and covered_parameters == parameters and covered_outputs == set(outputs),
         'actual_report_parts_unmapped')
    need(covered_cases == set(acceptance), 'acceptance_without_requirement')
    for output in outputs.values():
        cases = [c for c in acceptance.values() if c['output_format'] == output['format']]
        need({s for c in cases for s in c['section_ids']} == sections and
             {p for c in cases for p in c['parameter_ids']} == parameters, 'per_format_part_acceptance_uncovered')


def obligations(value):
    """Stable per-format scenario denominator; no declaration is a QA pass."""
    need(value.get('schema_version') == 2, 'version_2_required_for_candidate_qa')
    return [{**case, 'requirement_ids': sorted(b['requirement_id'] for b in value['requirement_bindings']
             if case['id'] in b['acceptance_ids'])} for case in value['acceptance']]


def validate_handoff(root, design, spec, P):
    value = design.get('report_contract')
    result = validate(value, spec, design.get('destinations', []))
    paths = {d['query_path'] for d in value['datasets']}
    paths.update(c['evidence_path'] for c in value['capabilities'] if c['evidence_path'])
    paths.update(c['decision_ref'].split('#', 1)[0] for c in value['capabilities'] if c['decision_ref'])
    paths.update(b['decision_ref'].split('#', 1)[0] for b in value.get('requirement_bindings', []) if b['decision_ref'])
    paths.add(value['data_policy']['decision_ref'].split('#', 1)[0])
    if value['profile']['evidence_path']:
        paths.add(value['profile']['evidence_path'])
    dependencies = []
    for path in sorted(paths):
        raw = P.relative_file(root, path).read_bytes()
        need(raw.strip(), 'empty_evidence')
        dependencies.append({'path': path, 'sha256': P.digest(raw), 'bytes': len(raw)})
    result['dependencies'] = dependencies
    result['qualification'] = 'Declared design and retained evidence only; no schema compilation, native execution, authority or pixel-perfect certification.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--design', required=True)
    parser.add_argument('--intent', required=True)
    args = parser.parse_args()
    loader = importlib.util.spec_from_file_location('report_project', Path(__file__).with_name('analyst_project.py'))
    P = importlib.util.module_from_spec(loader); loader.loader.exec_module(P)
    root, project = P.load_project(args.project)
    need('report' in project['surfaces'], 'report_surface_required')
    spec = P.read_json(P.relative_file(root, args.intent))[0]
    P.intent_helper().validate(spec, project)
    design = P.read_json(P.relative_file(root, args.design))[0]
    print(json.dumps(validate_handoff(root, design, spec, P), indent=2))


if __name__ == '__main__':
    main()
