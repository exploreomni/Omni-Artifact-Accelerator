"""Explicit result identity and independent comparison intake; no query execution."""
import importlib.util
import json
import math
from decimal import Decimal
from pathlib import Path

_spec = importlib.util.spec_from_file_location('analytical_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
MAX_OUTPUT_BYTES = P.MAX_BYTES


def pin(root, value):
    P.need(type(value) is dict and set(value) == {'path', 'sha256'}, 'Exact evidence pin required')
    path = P.relative_file(root, value['path'])
    P.need(path.stat().st_size <= P.MAX_BYTES, 'Analytical evidence exceeds byte budget')
    raw = path.read_bytes()
    P.need(len(raw) <= P.MAX_BYTES and P.digest(raw) == value['sha256'], 'Pinned analytical evidence changed')
    return raw


def pinned_json(root, value):
    raw = pin(root, value)
    def exact_float(token):
        number = float(token)
        P.need(math.isfinite(number) and Decimal(token) == Decimal(str(number)),
               'Numeric precision would change; supply an explicit decimal-string contract')
        return number
    def nonfinite(_):
        raise ValueError('Non-finite analytical number')
    try:
        return json.loads(raw, object_pairs_hook=P.reject_duplicate, parse_float=exact_float, parse_constant=nonfinite)
    except (RecursionError, UnicodeError, json.JSONDecodeError):
        raise ValueError('Invalid analytical JSON') from None


def normalize(root, request):
    """Map declared field IDs, never dictionary iteration order or guessed aliases."""
    root, _ = P.load_project(root)
    P.need(type(request) is dict and set(request) == {'source', 'layout', 'source_fields', 'bindings', 'output'},
           'Invalid normalization request')
    P.need(request['layout'] in {'objects', 'columnar'}, 'Unsupported result layout')
    fields = request['source_fields']
    P.routing_helper().strings(fields, nonempty=True)
    P.need(len(fields) <= 512 and len(set(fields)) == len(fields), 'Unique explicit source fields required')
    bindings = request['bindings']
    P.need(type(bindings) is list and len(bindings) == len(fields), 'Every field needs an explicit binding')
    for binding in bindings:
        P.need(type(binding) is dict and set(binding) == {'source', 'target'}, 'Explicit source and target field IDs required')
        P.routing_helper().text(binding['source']); P.routing_helper().text(binding['target'])
    P.need({b['source'] for b in bindings} == set(fields) and len({b['target'] for b in bindings}) == len(fields),
           'Ambiguous or incomplete field binding')
    original = pinned_json(root, request['source'])
    if request['layout'] == 'objects':
        P.need(type(original) is list, 'Object-row array required')
        rows = original
        P.need(all(type(row) is dict and set(row) == set(fields) for row in rows), 'Result field identity changed')
        mapped = ({b['target']: row[b['source']] for b in bindings} for row in rows)
    else:
        P.need(type(original) is dict and set(original) == {'columns', 'rows'}, 'Explicit column metadata and rows required')
        columns, rows = original['columns'], original['rows']
        P.need(type(columns) is list and all(type(c) is str for c in columns) and len(columns) == len(fields)
               and set(columns) == set(fields) and len(set(columns)) == len(columns), 'Result column identity changed')
        P.need(type(rows) is list and all(type(row) is list and len(row) == len(columns) for row in rows), 'Ragged result rows')
        positions = {column: position for position, column in enumerate(columns)}
        mapped = ({b['target']: row[positions[b['source']]] for b in bindings} for row in rows)
    chunks, size = [], 2
    for row in mapped:
        chunk = P.canonical(row)
        size += len(chunk) + (1 if chunks else 0)
        P.need(size <= MAX_OUTPUT_BYTES, 'Normalized output exceeds byte budget; split the governed result')
        chunks.append(chunk)
    payload = b'[' + b','.join(chunks) + b']'
    output = request['output']
    P.routing_helper().output_path(output)
    P.need(output.startswith(('evidence/', 'deliverables/')) and output.endswith('.json'), 'Private analytical output path required')
    destination = P.no_links(root / output)
    P.private_write(destination, payload)
    return {'status': 'normalized', 'source': request['source'], 'output': {'path': output, 'sha256': P.digest(payload)},
            'rows': len(rows), 'field_bindings': bindings, 'values_transformed': False,
            'migration_parity_verified': False, 'native_verified': False}


def compare(root, request):
    """Require original-side provenance, then reuse the established comparator.

    Supplied identity is a declaration, not authenticated source execution.
    Target-to-target comparisons remain useful but cannot use this migration lane.
    """
    root, _ = P.load_project(root)
    P.need(type(request) is dict and set(request) == {'comparison', 'provenance', 'output'}, 'Invalid comparison intake')
    spec = pinned_json(root, request['comparison'])
    P.need(spec.get('independence_provenance') == request['provenance'], 'Comparison must retain the exact provenance binding')
    validate_comparison_provenance(root, spec, request['provenance'])
    # The core retains key matching, independent context/principal/completeness,
    # source-platform evidence, tolerance and exact candidate obligations.
    return P.routing_helper('visual_workflow').compare(root, request['comparison']['path'], request['output'],
                                                       expected_spec_sha256=request['comparison']['sha256'])


def validate_comparison_provenance(root, spec, provenance_pin):
    provenance = pinned_json(root, provenance_pin)
    P.need(type(provenance) is dict and set(provenance) == {'source_basis', 'source', 'target', 'original_results', 'execution_evidence'},
           'Independent comparison provenance required')
    P.need(provenance['source_basis'] in {'original_results', 'independent_source_execution'},
           'Target self-consistency is not independent migration proof')
    for side in ('source', 'target'):
        identity = provenance[side]
        P.need(type(identity) is dict and set(identity) == {'system_ref', 'artifact_id', 'version'}, 'Versioned result identity required')
        for value in identity.values():
            P.routing_helper().text(value)
    P.need(provenance['source'] != provenance['target'], 'Source and target identity must be distinct')
    original = provenance['original_results']
    pin(root, original)
    P.need(original == spec['source'].get('raw_file', spec['source']['file']), 'Original results must bind the actual comparison source')
    P.need(spec['source']['file']['path'] != spec['target']['file']['path'], 'Source and target cannot reuse the same result file')
    evidence = provenance['execution_evidence']
    P.need(type(evidence) is list and 0 < len(evidence) <= 32, 'Retained source provenance evidence required')
    for value in evidence:
        pin(root, value)
    return {'source_basis': provenance['source_basis'], 'provenance': provenance_pin, 'source_execution_authenticated': False}
