"""Passive planning over explicitly supplied Domo Pro Code source files."""
from html.parser import HTMLParser
from pathlib import Path


GUIDE = 'skills/omni-domo-migrator/references/pro-code-apps.md'
KINDS = {'manifest', 'source', 'instance_wiring', 'source_observation'}
CODE = {'.html', '.htm', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.css', '.sql', '.json', '.vue', '.svelte'}
FORMATS = {'source': CODE, 'manifest': {'.json'}, 'instance_wiring': {'.json', '.txt', '.csv'},
           'source_observation': {'.json', '.txt', '.csv'}}
SUMMARY_BYTES = 48 * 1024


class ControlHints(HTMLParser):
    """Static HTML declarations only; JS, CSS visibility and events stay unobserved."""
    def __init__(self):
        super().__init__()
        self.items = []
        self.truncated = False

    def handle_starttag(self, tag, attrs):
        if tag not in {'input', 'select', 'button', 'textarea'}:
            return
        if len(self.items) == 256:
            self.truncated = True
            return
        attrs = dict(attrs)
        self.items.append({'line': self.getpos()[0], 'tag': tag, **{
            key: attrs[key][:256] for key in ('id', 'name', 'type', 'aria-label') if attrs.get(key)}})


def manifest_summary(value, domo):
    domo.need(isinstance(value, dict), 'pro_code_manifest_object')
    summary = {'design_id': value.get('id') if isinstance(value.get('id'), str) else None,
               'version': value.get('version') if isinstance(value.get('version'), str) else None,
               'mapping_declared': 'datasetsMapping' in value}
    mappings = value.get('datasetsMapping', [])
    if not isinstance(mappings, list):
        return {**summary, 'dataset_mappings': None, 'findings': ['dataset_mappings_uninterpreted']}
    result, findings = [], []
    for mapping in mappings:
        if not isinstance(mapping, dict):
            findings.append('dataset_mapping_uninterpreted')
            continue
        fields = mapping.get('fields', [])
        field_rows = None
        if isinstance(fields, list) and all(isinstance(f, dict) for f in fields):
            field_rows = [{k: f[k] for k in ('alias', 'columnName') if isinstance(f.get(k), str)} for f in fields]
        if field_rows is None or any(set(f) != {'alias', 'columnName'} for f in field_rows):
            findings.append('field_mapping_needs_review')
        if not isinstance(mapping.get('alias'), str) or not isinstance(mapping.get('dataSetId'), str):
            findings.append('dataset_mapping_needs_review')
        result.append({'alias': mapping.get('alias') if isinstance(mapping.get('alias'), str) else None,
                       'design_dataset_id': mapping.get('dataSetId') if isinstance(mapping.get('dataSetId'), str) else None,
                       'fields': field_rows})
    return {**summary, 'dataset_mappings': result, 'findings': sorted(set(findings))}


def inspect(root, spec, ap, domo):
    selected = spec.get('scope', {}).get('app_ids', [])
    assets = spec.get('pro_code_assets', [])
    domo.need(isinstance(assets, list) and len(assets) <= 128, 'pro_code_asset_limit')
    gates = ap.routing_helper('stage_gates')
    reviewed, seen, total = [], set(), 0
    remaining_summary = SUMMARY_BYTES
    with gates._root_fd(root, ap) as (_, fd):
        for item in assets:
            domo.need(isinstance(item, dict) and {'kind', 'path'} <= item.keys() <= {'kind', 'path', 'app_id'}
                      and isinstance(item['kind'], str) and item['kind'] in KINDS, 'pro_code_asset')
            ident = item.get('app_id')
            domo.need(ident is None or domo.text(ident) and ident in selected, 'pro_code_asset_scope')
            domo.need(len(selected) <= 1 or ident is not None, 'pro_code_asset_needs_app_scope')
            path = gates._relative(item['path'])
            key = (ident, item['kind'], path)
            domo.need(key not in seen, 'pro_code_duplicate_asset')
            seen.add(key)
            suffix = Path(path).suffix.lower()
            domo.need(suffix in FORMATS[item['kind']], 'pro_code_asset_format')
            raw = gates._read(fd, path, domo.MAX_BYTES)
            total += len(raw)
            domo.need(raw.strip() and b'\0' not in raw and total <= domo.MAX_TOTAL, 'pro_code_asset_bytes')
            row = {'kind': item['kind'], 'app_id': ident, 'file': {'path': path, 'bytes': len(raw), 'sha256': ap.digest(raw)}}
            details = {}
            if suffix == '.json':
                value = domo.decode(raw)
                domo._screen(value)
                if item['kind'] == 'manifest':
                    details['declarations'] = manifest_summary(value, domo)
            else:
                try:
                    value = raw.decode('utf-8-sig')
                except UnicodeError:
                    raise ValueError('domo.pro_code_text_utf8_required') from None
                domo._screen(value)
                if suffix in {'.htm', '.html'}:
                    hints = ControlHints()
                    try:
                        hints.feed(value)
                        hints.close()
                    except AssertionError:  # HTMLParser rejects unknown marked sections.
                        hints.truncated = True
                    details.update(html_control_hints=hints.items, hints_truncated=hints.truncated)
            if details:
                size = len(ap.canonical(details))
                if size <= min(16 * 1024, remaining_summary):
                    row.update(details)
                    remaining_summary -= size
                else:
                    row.update(summary_status='read_pinned_source_for_details', omitted_sections=sorted(details))
            reviewed.append(row)
    coverage = []
    for ident in selected or [None]:
        supplied = {row['kind'] for row in reviewed if row['app_id'] == ident or len(selected) == 1 and row['app_id'] is None}
        coverage.append({'app_id': ident, 'missing_evidence_kinds': sorted(KINDS - supplied)})
    return {'app_family': 'pro_code', 'guide': GUIDE, 'assets': reviewed, 'coverage': coverage,
            'qualification': 'supplied_source_planning_only', 'source_execution': False,
            'unverified': ['design_to_instance_wiring', 'effective_persona_access', 'control_propagation_and_reset',
                           'operational_dependencies', 'native_candidate_parity']}


def handoff(root, source, project, gate, ap):
    records = [{key: asset[key] for key in ('app_id', 'kind', 'file')} for asset in source['assets']]
    result = {'assets': records, 'coverage': source['coverage'], 'unverified': source['unverified'],
              'qualification': source['qualification']}
    if records and project.get('migration_treatment') in ap.TREATMENTS:
        selected = gate.get('migration_baseline')
        ap.need(isinstance(selected, dict), 'domo.pro_code_selected_baseline_required')
        baseline = ap.routing_helper('migration_fidelity').baseline(root, selected['path'])
        ap.need(baseline['baseline_sha256'] == selected['baseline_sha256'], 'domo.pro_code_source_baseline_changed')
        pins = {pin['path']: pin for pin in baseline['pins']}
        ap.need(all(pins.get(row['file']['path']) == row['file'] for row in records),
                'domo.pro_code_include_current_files_in_source_baseline')
        result['baseline_sha256'] = baseline['baseline_sha256']
    return result
