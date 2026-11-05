"""Bounded local structural measurements. No payload logging or billing inference."""
import importlib.util
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

_spec = importlib.util.spec_from_file_location('observed_project', Path(__file__).with_name('analyst_project.py'))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)
MAX_EVENTS = 2048
MAX_EVENT_BYTES = 8192
COUNTERS = {'file_reads', 'file_bytes', 'read_reuses', 'derivation_reuses', 'verification_reads', 'verification_bytes', 'validation_ms', 'lock_wait_ms'}
OPERATIONS = P.routing_helper('execution_contracts').OPERATIONS
TOOLS = {*OPERATIONS, 'execution_status', 'execution_contract'}


def package_identity():
    source = Path(__file__).resolve().parents[3]
    metadata = source / 'package.json'
    if not metadata.is_file():
        return {'version': None, 'metadata_sha256': None}
    value, raw = P.read_json(metadata)
    return {'version': value.get('version'), 'metadata_sha256': P.digest(raw)}


def report(root):
    root, _ = P.load_project(root)
    directory = P.no_links(root / '.execution-observations')
    totals = {k: 0 for k in ('argument_bytes', 'result_json_bytes', 'elapsed_ms', *COUNTERS)}
    coverage = {k: 0 for k in totals}
    operations, configurations, implementations = {}, set(), set()
    count = rejected = invalid = 0
    paths = sorted(directory.glob('*.json')) if directory.is_dir() else []
    for path in paths[:MAX_EVENTS]:
        try:
            P.need(path.stat().st_size <= MAX_EVENT_BYTES, 'oversized observation')
            item = P.read_json(path)[0]
            P.need(item.get('kind') == 'execution_local_observation' and item.get('schema_version') == 1, 'invalid observation')
            P.need(item['tool'] in TOOLS and
                   (item['operation'] is None or item['operation'] in OPERATIONS.get(item['tool'], ())), 'invalid operation')
            P.need(item['outcome'] in {'returned', 'rejected'}, 'invalid outcome')
            for key in totals:
                value = item.get(key)
                P.need(value is None or (type(value) is int and 0 <= value < 2**63), 'invalid metric')
            P.need(all(type(item[k]) is str and re.fullmatch('[a-f0-9]{64}', item[k])
                       for k in ('configuration_sha256', 'implementation_sha256')), 'invalid identity')
            count += 1
            rejected += item['outcome'] == 'rejected'
            key = item['tool'] + '/' + (item['operation'] or 'unspecified')
            operations[key] = operations.get(key, 0) + 1
            configurations.add(item['configuration_sha256'])
            implementations.add(item['implementation_sha256'])
            for key in totals:
                if item.get(key) is not None:
                    totals[key] += item[key]
                    coverage[key] += 1
        except (ValueError, OSError, KeyError, TypeError):
            invalid += 1
    return {'kind': 'execution_local_measurement_report', 'schema_version': 1,
            'observed_calls': count, 'rejected_calls': rejected, 'operations': operations,
            'totals': {k: totals[k] if coverage[k] else None for k in totals}, 'coverage': coverage,
            'configuration_count': len(configurations), 'implementation_count': len(implementations),
            'invalid_observations': invalid, 'collection_limit_reached': len(paths) >= MAX_EVENTS,
            'unread_observations': max(0, len(paths) - MAX_EVENTS), 'dollars': None,
            'qualification': 'Local structural observations only; no raw prompts, source data, billing or model-quality claims.'}


def record(root, *, tool, operation, arguments, result, started_ns, outcome, configuration, counters=None):
    """Failure to measure cannot turn an otherwise valid workflow into a failure."""
    try:
        root, _ = P.load_project(root)
        P.need(tool in TOOLS and
               (operation is None or operation in OPERATIONS.get(tool, ())), 'fixed operation required')
        directory = P.no_links(root / '.execution-observations')
        directory.mkdir(mode=0o700, exist_ok=True)
        item = {'schema_version': 1, 'kind': 'execution_local_observation', 'event_id': uuid.uuid4().hex,
                'tool': tool, 'operation': operation, 'outcome': outcome,
                'argument_bytes': len(P.canonical(arguments)),
                'result_json_bytes': len(json.dumps(result, allow_nan=False).encode('utf-8')) if outcome == 'returned' else None,
                'elapsed_ms': max(0, (time.monotonic_ns() - started_ns) // 1000000),
                'configuration_sha256': P.digest(P.canonical(configuration)),
                'package': package_identity(),
                'implementation_sha256': P.digest(P.canonical({name: P.digest(Path(__file__).with_name(name).read_bytes())
                    for name in ('execution_observability.py', 'execution_bridge.py', 'execution_efficiency.py')})),
                'source_payload_recorded': False, 'host_usage': None, 'billing_verified': False}
        for key in COUNTERS:
            value = (counters or {}).get(key)
            item[key] = int(value) if type(value) in (int, float) and 0 <= value < 2**63 else None
        raw = P.canonical(item) + b'\n'
        P.need(len(raw) <= MAX_EVENT_BYTES, 'observation exceeds bound')
        # Do not delay execution for metrics. A short nonblocking collector lock
        # keeps the event cap exact even when several workers finish together.
        lock = os.open(P.no_links(directory / '.collector.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(lock)
            P.need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'unsafe collector lock')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return 'collector_busy'
            if sum(1 for _ in directory.glob('*.json')) >= MAX_EVENTS:
                return 'limit_reached'
            fd = os.open(P.no_links(directory / (item['event_id'] + '.json')),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
        finally:
            os.close(lock)
        return 'recorded'
    except (ValueError, OSError, TypeError, OverflowError):
        return 'unavailable'
