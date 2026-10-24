#!/usr/bin/env python3
"""Offline consistency checks for supplied query captures, never a native execution gate.

No network, credentials, imports from captures, writes, SQL execution or vendor SDK.
JSON pointers select retained values; this helper never guesses keys or repairs rows.
"""
import argparse
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
import sys

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100000
LANES = {'query_export', 'native_callback', 'constructed_fixture', 'source_contract'}
TYPES = {'string', 'integer', 'number', 'boolean', 'decimal_string'}
IDENTITY = {'connection_id', 'database', 'schema', 'model_id', 'query_name'}
SELECTORS = {'binding', 'query', 'status', 'columns', 'rows', 'limit', 'truncated', 'exhaustive', 'total_rows'}
DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')
MISSING = object()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return type(value) is str and bool(value.strip()) and len(value) <= 4096


def decimal(value):
    need(type(value) in (int, float, Decimal, str) and type(value) is not bool, 'Expected finite number')
    need(not isinstance(value, str) or bool(DECIMAL.fullmatch(value)), 'Invalid decimal string')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal') from exc
    need(result.is_finite() and abs(result.adjusted()) <= 1000 and len(result.as_tuple().digits) <= 100, 'Number outside finite bounds')
    return result


def pointer(document, path):
    """Exact RFC 6901 traversal; missing paths remain missing, never an empty result."""
    need(type(path) is str and len(path) <= 4096 and path.count('/') <= 64 and (path == '' or path.startswith('/')), 'Invalid JSON pointer')
    need(not re.search(r'~(?![01])', path), 'Invalid JSON pointer escape')
    value = document
    for token in path.split('/')[1:] if path else []:
        need(not re.search(r'~(?![01])', token), 'Invalid JSON pointer escape')
        token = token.replace('~1', '/').replace('~0', '~')
        if type(value) is dict:
            value = value.get(token, MISSING)
        elif type(value) is list and re.fullmatch(r'0|[1-9][0-9]*', token):
            index = int(token)
            value = value[index] if index < len(value) else MISSING
        else:
            return MISSING
    return value


def same(left, right):
    """Strict structure/type equality prevents JSON true from matching numeric 1."""
    if type(left) is dict and type(right) is dict:
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if type(left) is list and type(right) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def validate_contract(contract, expectations):
    need(type(contract) is dict and type(contract.get('schema_version')) is int and contract['schema_version'] == 1
         and contract.get('kind') == 'native_query_probe_contract', 'Unsupported contract')
    requested = contract.get('requested')
    need(type(requested) is dict and IDENTITY <= requested.keys()
         and set(requested) <= IDENTITY | {'document_id', 'draft_id'}
         and all(text(v) or (k == 'draft_id' and v is None) for k, v in requested.items()), 'Exact requested identity required')
    fields = contract.get('fields')
    need(type(fields) is list and 0 < len(fields) <= 1024, 'Fields required')
    keys = []
    for field in fields:
        need(type(field) is dict and text(field.get('key')) and field.get('type') in TYPES
             and type(field.get('nullable')) is bool and text(field.get('metadata_type')), 'Invalid field contract')
        keys.append(field['key'])
    need(len(set(keys)) == len(keys), 'Duplicate contracted field')
    query = contract.get('query')
    need(type(query) is dict and {'fields', 'filters', 'limit'} <= query.keys()
         and query['fields'] == keys and type(query['filters']) is dict
         and type(query['limit']) is int and 0 < query['limit'] <= MAX_ROWS, 'Exact query fields, filters and bounded limit required')
    grain = contract.get('grain')
    need(type(grain) is list and grain and len(set(grain)) == len(grain)
         and all(k in keys for k in grain), 'Nonempty unique grain required')
    selectors = contract.get('selectors')
    need(type(selectors) is dict and set(selectors) == SELECTORS, 'Exact observation selectors required')
    for value in selectors.values():
        pointer({}, value)
    metadata = contract.get('metadata')
    need(type(metadata) is dict and metadata.get('layout') in {'list', 'object'}
         and text(metadata.get('type_key'))
         and (metadata['layout'] == 'object' or text(metadata.get('name_key'))), 'Metadata layout and keys required')
    need(text(contract.get('complete_status')), 'Exact complete status required')
    concurrency = contract.get('concurrency')
    need(type(concurrency) is dict and concurrency.get('mode') in {'serialized', 'correlated'}
         and type(concurrency.get('max_in_flight')) is int and concurrency['max_in_flight'] > 0
         and concurrency.get('qualification') in {'unavailable', 'source_only', 'native_observed'}, 'Concurrency policy required')
    if concurrency['mode'] == 'serialized':
        need(concurrency['max_in_flight'] == 1, 'Serialized mode allows one in-flight request')
    else:
        need(concurrency['qualification'] == 'native_observed' and text(concurrency.get('evidence_ref'))
             and type(concurrency.get('evidence_sha256')) is str
             and re.fullmatch(r'[a-f0-9]{64}', concurrency['evidence_sha256']),
             'Correlated mode needs retained native correlation evidence; otherwise serialize')
    need(type(expectations) is dict and type(expectations.get('schema_version')) is int and expectations['schema_version'] == 1
         and expectations.get('kind') == 'native_query_probe_expectations', 'Independent expectations required')
    provenance = expectations.get('provenance', {})
    need(type(provenance) is dict and provenance.get('method') in {'independent_query', 'independent_calculation'}
         and text(provenance.get('reference')) and type(provenance.get('sha256')) is str
         and re.fullmatch(r'[a-f0-9]{64}', provenance['sha256']), 'Pinned independent expectation provenance required')
    pointer({}, expectations.get('rows_pointer'))
    need(same(expectations.get('requested'), requested) and same(expectations.get('filters'), query['filters']),
         'Expected population must match the requested source and filters')
    need(type(expectations.get('rows')) is int and 0 <= expectations['rows'] <= MAX_ROWS, 'Independent full population row count required')
    aggregates = expectations.get('aggregates')
    need(type(aggregates) is list and 0 < len(aggregates) <= 128, 'Independent aggregates required')
    ids = set()
    for item in aggregates:
        need(type(item) is dict and text(item.get('id')) and item['id'] not in ids
             and item.get('op') in {'sum', 'mean', 'count_non_null', 'count_true'}, 'Invalid aggregate expectation')
        ids.add(item['id'])
        pointer({}, item.get('expected_pointer'))
        pointer({}, item.get('non_null_pointer'))
        field = next((f for f in fields if f['key'] == item.get('field')), None)
        need(field is not None, 'Aggregate field not contracted')
        if item['op'] in {'sum', 'mean'}:
            need(field['type'] in {'number', 'integer', 'decimal_string'}, 'Numeric aggregate requires numeric field')
        if item['op'] == 'count_true':
            need(field['type'] == 'boolean', 'Count true requires boolean field')
        need('expected' in item and type(item.get('non_null_rows')) is int
             and 0 <= item['non_null_rows'] <= expectations['rows'], 'Aggregate expected value and denominator required')
        if item['expected'] is not None:
            decimal(item['expected'])
        need(decimal(item.get('absolute_tolerance', '0')) >= 0, 'Negative tolerance')
    return fields


def valid_value(value, field):
    if value is None:
        return field['nullable']
    kind = field['type']
    if kind == 'string':
        return type(value) is str
    if kind == 'boolean':
        return type(value) is bool
    if kind == 'integer':
        # JSON numbers must survive the native JavaScript boundary without precision loss.
        # Larger exact values need an explicitly contracted decimal_string field.
        return type(value) is int and abs(value) <= 2 ** 53 - 1
    if kind == 'number':
        return type(value) in (int, float, Decimal) and (not isinstance(value, float) or math.isfinite(value)) and decimal(value).is_finite()
    return type(value) is str and bool(DECIMAL.fullmatch(value)) and decimal(value).is_finite()


def probe(contract, evidence, expectations, evidence_root=None):
    """Return bounded findings; consistency never authenticates captures or observations."""
    fields = validate_contract(contract, expectations)
    need(type(evidence) is dict and evidence.get('lane') in LANES, 'Evidence lane required')
    need(type(evidence.get('provenance')) is dict and text(evidence['provenance'].get('reference')),
         'Capture provenance reference required')
    lane = evidence['lane']
    findings = []
    def finding(code, field=None):
        item = {'code': code}
        if field is not None:
            item['field'] = field
        if item not in findings:
            findings.append(item)
    source_pin = None
    if evidence_root is None:
        finding('expectation_source_not_loaded')
    else:
        try:
            reference = expectations['provenance']['reference']
            rel = Path(reference)
            need(not rel.is_absolute() and '..' not in rel.parts and rel.as_posix() == reference
                 and '\\' not in reference, 'Independent source must be an engagement-relative path')
            source, source_pin = read(Path(evidence_root) / rel)
            if source_pin['sha256'] != expectations['provenance']['sha256']:
                finding('expectation_source_hash_mismatch')
            else:
                pairs = [(expectations['rows_pointer'], expectations['rows'])]
                for item in expectations['aggregates']:
                    pairs.extend([(item['expected_pointer'], item['expected']),
                                  (item['non_null_pointer'], item['non_null_rows'])])
                for path, expected in pairs:
                    observed_value = pointer(source, path)
                    matched = observed_value is None if expected is None else (
                        observed_value is not MISSING and decimal(observed_value) == decimal(expected))
                    if not matched:
                        finding('expectation_source_value_mismatch', path)
        except (ValueError, OSError, TypeError, KeyError):
            finding('expectation_source_unavailable_or_invalid')
    if contract['concurrency']['mode'] == 'correlated':
        try:
            concurrency = contract['concurrency']
            ref = concurrency['evidence_ref']
            rel = Path(ref)
            need(evidence_root is not None and not rel.is_absolute() and '..' not in rel.parts
                 and rel.as_posix() == ref and '\\' not in ref, 'Correlation evidence path required')
            _, correlation_pin = read(Path(evidence_root) / rel)
            if correlation_pin['sha256'] != concurrency['evidence_sha256']:
                finding('correlation_evidence_hash_mismatch')
        except (ValueError, OSError, TypeError, KeyError):
            finding('correlation_evidence_unavailable_or_invalid')
    observed = {key: pointer(evidence, path) for key, path in contract['selectors'].items()}
    for key, value in observed.items():
        if value is MISSING:
            finding('observation_missing', key)
    binding = observed['binding']
    for key, expected in contract['requested'].items():
        if type(binding) is not dict or key not in binding or not same(binding[key], expected):
            finding('binding_mismatch', key)
    query = observed['query']
    if type(query) is not dict or not same(query, contract['query']):
        finding('query_or_population_mismatch')
    if observed['status'] != contract['complete_status']:
        finding('query_not_complete')
    if not same(observed['limit'], contract['query']['limit']):
        finding('limit_mismatch')
    if observed['truncated'] is not False:
        finding('truncation_not_excluded')
    if observed['exhaustive'] is not True:
        finding('population_not_exhausted')
    if not same(observed['total_rows'], expectations['rows']):
        finding('independent_population_mismatch')
    if contract['concurrency']['mode'] == 'correlated' and lane != 'native_callback':
        finding('correlation_requires_native_evidence')
    columns = observed['columns']
    metadata = contract['metadata']
    by_name = {}
    if metadata['layout'] == 'object' and type(columns) is dict:
        by_name = columns
    elif metadata['layout'] == 'list' and type(columns) is list:
        for column in columns:
            name = column.get(metadata['name_key']) if type(column) is dict else None
            if not text(name) or name in by_name:
                finding('invalid_or_duplicate_metadata')
            else:
                by_name[name] = column
    else:
        finding('metadata_shape_mismatch')
    for field in fields:
        meta = by_name.get(field['key'])
        if type(meta) is not dict or not meta:
            finding('field_metadata_missing', field['key'])
        elif meta.get(metadata['type_key']) != field['metadata_type']:
            finding('field_metadata_type_mismatch', field['key'])
    rows = observed['rows']
    if type(rows) is not list or len(rows) > MAX_ROWS:
        finding('rows_shape_or_bound_mismatch')
        rows = []
    if len(rows) != expectations['rows']:
        finding('row_count_mismatch')
    # At the limit, even an asserted total can be a capped total. Require a larger probe.
    if len(rows) >= contract['query']['limit']:
        finding('cap_reached_increase_limit_or_qualify_pagination')
    keys = {f['key'] for f in fields}
    field_types = {f['key']: f['type'] for f in fields}
    seen = set()
    rows_valid = True
    for row in rows:
        if type(row) is not dict or set(row) != keys:
            finding('row_field_set_mismatch')
            rows_valid = False
            continue
        for field in fields:
            try:
                valid = valid_value(row[field['key']], field)
            except ValueError:
                valid = False
            if not valid:
                finding('row_type_or_null_mismatch', field['key'])
                rows_valid = False
        grain = [row[k] for k in contract['grain']]
        if any(v is None or type(v) in (dict, list) or (type(v) is str and not v.strip()) for v in grain):
            finding('grain_missing_or_invalid')
            rows_valid = False
        else:
            try:
                identity = tuple(('numeric', decimal(row[k])) if field_types[k] in {'number', 'integer', 'decimal_string'}
                                 else (type(row[k]).__name__, row[k]) for k in contract['grain'])
            except ValueError:
                finding('grain_missing_or_invalid')
                rows_valid = False
                continue
            if identity in seen:
                finding('grain_duplicate')
            seen.add(identity)
    comparisons = []
    if rows_valid:
        with localcontext() as ctx:
            # Bounded 100-significant-digit inputs / exponents <= 1000; sums stay exact.
            ctx.prec = 4096
            for item in expectations['aggregates']:
                values = [r[item['field']] for r in rows if r[item['field']] is not None]
                op = item['op']
                if op == 'count_non_null':
                    actual = Decimal(len(values))
                elif op == 'count_true':
                    actual = Decimal(sum(v is True for v in values))
                else:
                    actual = sum((decimal(v) for v in values), Decimal(0)) if values else None
                    if op == 'mean' and values:
                        actual /= len(values)
                expected = None if item['expected'] is None else decimal(item['expected'])
                matched = actual is expected if actual is None or expected is None else abs(actual - expected) <= decimal(item.get('absolute_tolerance', '0'))
                denominator_ok = len(values) == item['non_null_rows']
                if not matched or not denominator_ok:
                    finding('aggregate_or_denominator_mismatch', item['id'])
                comparisons.append({'id': item['id'], 'actual': None if actual is None else str(actual),
                                    'non_null_rows': len(values), 'matches': matched and denominator_ok})
    return {'schema_version': 1, 'kind': 'native_query_probe_report',
            'status': 'consistent' if not findings else 'incomplete', 'evidence_lane': lane,
            'row_count': len(rows), 'independent_source_pin': source_pin, 'findings': findings, 'aggregate_comparisons': comparisons,
            'claims_authenticated': False, 'native_execution_verified': False,
            'native_callback': 'supplied_capture_only' if lane == 'native_callback' else 'not_observed',
            'rendering': 'not_assessed', 'access': 'not_assessed', 'recovery': 'not_executed',
            'boundary': 'Offline consistency of declared scope and supplied captures only; independent provenance and original-request completeness require review.'}


def read(path):
    p = Path(path)
    need(not any(part.is_symlink() for part in (p, *p.absolute().parents)) and p.is_file() and p.stat().st_size <= MAX_BYTES, 'Input must be a bounded regular JSON file')
    raw = p.read_bytes()
    need(len(raw) <= MAX_BYTES, 'Input exceeds byte bound')
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON number')
    data = json.loads(raw, object_pairs_hook=pairs, parse_float=Decimal, parse_constant=invalid)
    return data, {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contract', 'evidence', 'expectations'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--evidence-root', help='Private engagement root for pinned independent evidence; defaults to expectations parent')
    args = parser.parse_args()
    try:
        loaded = {name: read(getattr(args, name)) for name in ('contract', 'evidence', 'expectations')}
        result = probe(*(loaded[name][0] for name in ('contract', 'evidence', 'expectations')),
                       evidence_root=args.evidence_root or Path(args.expectations).absolute().parent)
        result['input_pins'] = {name: loaded[name][1] for name in loaded}
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'consistent' else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError, OverflowError) as exc:
        # Never echo data-bearing JSON decode errors, captured payloads or row values.
        print(json.dumps({'status': 'invalid_input', 'error_type': type(exc).__name__,
                          'detail': 'Check the documented contract, pointers and bounded JSON input.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
