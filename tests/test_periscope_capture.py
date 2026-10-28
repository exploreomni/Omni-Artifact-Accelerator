"""Original synthetic CDT capture contracts; no source runtime or real network."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/omni-artifact-translator/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('test_periscope_' + name, SCRIPTS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


C, V = load('periscope_capture'), load('periscope_visual')


def source_fixture():
    """Hand-authored producer shape, including an opaque pickle never decoded."""
    blobs = {'dashboards/d.yaml': b'display_name: Garden\n',
             'dashboards/chart.yaml': b'chart_type: bar\n',
             'dashboards/chart.sql': b'SELECT location, quantity FROM garden_rows',
             'modules/inert.py': b'raise RuntimeError("NEVER_EXECUTE")\n',
             'modules/opaque.pkl': b'\x80\x04cpickle\nNEVER_LOAD\x00'}
    files = [{'path': p, 'sha256': C.F.raw_sha(b), 'status': 'partial', 'reason': 'Synthetic source only'} for p, b in blobs.items()]
    def evidence(path, locator='$'):
        return {'path': path, 'locator': locator, 'sha256': C.F.raw_sha(blobs[path])}
    objects = [
        {'id': 'adapter-d', 'native_id': 'd' * 32, 'kind': 'dashboard', 'name': 'Garden',
         'evidence': evidence('dashboards/d.yaml'), 'details': {'native_configuration': {'display_name': 'Garden'}}},
        {'id': 'adapter-v', 'native_id': 'v' * 32, 'kind': 'chart', 'name': 'Quantity',
         'evidence': evidence('dashboards/chart.yaml'), 'details': {'native_configuration': {'chart_type': 'bar', 'position': {'x': 0, 'y': 0}}}},
        {'id': 'adapter-c', 'native_id': None, 'kind': 'filter', 'name': 'Location',
         'evidence': evidence('dashboards/d.yaml', '$.configured_filters.visible[0]'),
         'details': {'parent_id': 'adapter-d', 'native_configuration': {'name': 'Location', 'value': 'West'}}}]
    sql = blobs['dashboards/chart.sql'].decode()
    expressions = [{'id': 'expr-sql', 'object_id': 'adapter-v', 'language': 'sql', 'text': sql,
                    'content_sha256': C.F.raw_sha(sql.encode()), 'evidence': evidence('dashboards/chart.sql'), 'details': {}}]
    report = {'schema_version': 1, 'kind': 'source_adapter_result', 'source': 'periscope', 'adapter_version': 1,
              'source_files': files, 'coverage_summary': {'unit': 'supplied_source_files', 'expected': 5, 'observed': 5, 'missing': 0,
               'statuses': {'parsed': 0, 'partial': 5, 'unsupported': 0}}, 'objects': objects, 'expressions': expressions,
              'dependencies': [], 'gaps': [], 'export_completeness': 'not_established', 'native_validation': 'not_run',
              'execution_performed': False, 'limitations': ['Synthetic source; original code remains inert.']}
    for kind in ('objects', 'expressions', 'dependencies', 'gaps'):
        positions = {}
        for row in report[kind]:
            p, loc = row['evidence']['path'], row['evidence']['locator']
            ordinal = positions.get((p, loc), 0)
            row['occurrence_id'] = 'periscope:occurrence:' + hashlib.sha256(json.dumps([kind, p, loc, ordinal], ensure_ascii=True).encode()).hexdigest()[:24]
            positions[p, loc] = ordinal + 1
    def item(key, kind, sid=None, config=None):
        return {'key': key, 'kind': kind, 'name': key, 'parent_key': None if key == 'board' else 'board',
                'source_object_id': sid, 'disposition': 'include', 'disposition_reference': 'synthetic requested scope',
                'evidence_reference': 'synthetic independent source listing', 'configuration': config or {}}
    inventory = {'schema_version': 'periscope-source-enumeration.v1', 'method': 'separate_source_enumeration',
                 'reference': 'original synthetic independent manifest', 'completeness': 'selected_scope_declared',
                 'objects': [item('board', 'dashboard', 'adapter-d'), item('quantity', 'visual', 'adapter-v'),
                             item('location', 'control', 'adapter-c'), item('place-one', 'placement', None, {'visual_key': 'quantity', 'x': 0}),
                             item('place-two', 'placement', None, {'visual_key': 'quantity', 'x': 10}), item('note', 'content')]}
    crosswalk = {'schema_version': 'periscope-identity-crosswalk.v1', 'reference': 'synthetic exact ID evidence', 'rows': [
        {'key': 'board', 'git_token': 'd' * 32, 'api_id': 'api-board-uuid', 'numeric_id': 123, 'reference': 'synthetic ID tuple'},
        {'key': 'quantity', 'git_token': 'v' * 32, 'api_id': 'api-visual-uuid', 'numeric_id': 456, 'reference': 'synthetic ID tuple'}]}
    return blobs, report, inventory, crosswalk


def request(render=False, list_dashboards=False):
    return {'schema_version': C.REQUEST, 'capture_id': 'synthetic-cdt', 'product': 'sisense_cdt',
            'product_evidence_ref': 'synthetic CDT source contract', 'site_name': 'synthetic-site', 'space_id': 'space-test',
            'space_reference': 'synthetic selected Space', 'source_revision': {'kind': 'git_commit', 'value': 'a' * 40, 'reference': 'synthetic snapshot'},
            'dashboard_key': 'board', 'principal_ref': 'synthetic-principal', 'authorization_ref': 'synthetic grant',
            'credential_ref': 'host-synthetic-cdt', 'evidence_mode': 'synthetic_fixture', 'route': 'unselected', 'route_reference': None,
            'target_surface': 'both', 'state': {'filters': [{'name': 'Location', 'value': 'West'}], 'parameters': {},
              'daterange': {'start': '2025-01-01', 'end': '2025-01-31'}, 'aggregation': 'daily', 'timezone': 'UTC',
              'locale': 'en-US', 'principal': 'synthetic-principal', 'reference': 'synthetic requested state'},
            'adapter_report_path': 'adapter.json', 'producer_revision': V.DMA_REVISION, 'inventory_path': 'inventory.json',
            'crosswalk_path': 'crosswalk.json', 'list_dashboards': list_dashboards,
            'render': {'render_id': 'pdf-one', 'dashboard_ts': 1735689600, 'refresh_intent': 'allow_refresh_older_than_dashboard_ts',
                       'widget_limit': 30, 'limit_reference': 'documented default limit'} if render else None,
            'render_download_hosts': ['periscope-render-virginia.s3.amazonaws.com'] if render else []}


def prepare(root, render=False, list_dashboards=False):
    root = Path(root).resolve()
    supplied = root / 'supplied'
    supplied.mkdir()
    blobs, report, inventory, crosswalk = source_fixture()
    for p, raw in blobs.items():
        (supplied / p).parent.mkdir(parents=True, exist_ok=True)
        (supplied / p).write_bytes(raw)
    for p, val in [('adapter.json', report), ('inventory.json', inventory), ('crosswalk.json', crosswalk)]:
        (supplied / p).write_bytes(C.encoded(val))
    req = request(render, list_dashboards)
    result = C.import_local(req, supplied, root / 'capture', allow_source_read=True)
    return req, result


def evidence_spec():
    observed = request()['state']
    return {'schema_version': 'periscope-supplied-evidence.v1', 'attachments': [{
        'source_path': 'result.csv', 'attachment_id': 'quantity-result', 'object_key': 'quantity', 'format': 'csv',
        'origin': 'full', 'result_scope': 'query_result', 'observed_state': {'state': observed,
          'observed_at': '2026-10-28T12:00:00Z', 'reference': 'synthetic state observation'},
        'population': {'key': 'all-garden-rows', 'description': 'synthetic full fixture population', 'reference': 'synthetic independent count'},
        'freshness': {'data_watermark': 'fixture-v1', 'observed_at': '2026-10-28T12:00:00Z', 'reference': 'synthetic watermark'},
        'completeness': {'status': 'complete', 'reference': 'synthetic exact two-row fixture', 'row_count': 2},
        'reference': 'synthetic supplied CSV'}]}


class PeriscopeCapture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.no_network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No real network permitted'))
        self.no_network.start()

    def tearDown(self):
        self.no_network.stop()
        self.temp.cleanup()

    def test_inert_originals_separate_inventory_and_numeric_crosswalk(self):
        req, result = prepare(self.root)
        value = result['capture']
        self.assertEqual('partial', result['status'])
        self.assertFalse(value['source_execution'])
        self.assertEqual(5, len(value['source']['files']))
        for pin in C.file_pins(value):
            self.assertEqual(0o600, stat.S_IMODE((Path(result['output']).parent / pin['path']).stat().st_mode))
        self.assertEqual('verified_local_bytes', C.check_capture(Path(result['output']))['status'])
        self.assertEqual(123, value['source']['crosswalk']['rows'][0]['numeric_id'])
        self.assertEqual('api-board-uuid', value['source']['crosswalk']['rows'][0]['api_id'])
        self.assertEqual('d' * 32, value['source']['crosswalk']['rows'][0]['git_token'])
        C.load_latest(self.root / 'capture', req)

    def test_product_scope_original_hash_and_symlink_fail_closed(self):
        req, result = prepare(self.root)
        for mutate in [lambda r: r.update(product='sisense_fusion'), lambda r: r.update(space_reference=''),
                       lambda r: r.update(source_revision={'kind': 'git_commit', 'value': 'bad', 'reference': 'x'}),
                       lambda r: r.update(adapter_report_path='../secret'), lambda r: r.update(credential='dummy')]:
            bad = copy.deepcopy(req)
            mutate(bad)
            with self.assertRaises(ValueError):
                C.validate_request(bad)
        original = self.root / 'supplied/dashboards/chart.sql'
        original.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
            C.import_local(req, self.root / 'supplied', self.root / 'capture-other', allow_source_read=True)
        original.unlink()
        original.symlink_to(self.root / 'supplied/dashboards/chart.yaml')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            C.import_local(req, self.root / 'supplied', self.root / 'capture-symlink', allow_source_read=True)

    def test_inventory_omissions_cycles_and_identity_conflation_reject(self):
        blobs, report, inventory, crosswalk = source_fixture()
        req = C.validate_request(request())
        for mutate in [lambda x: x['objects'].pop(2),
                       lambda x: x['objects'][1].update(parent_key='place-one'),
                       lambda x: x['objects'][3]['configuration'].update(visual_key='missing')]:
            bad = copy.deepcopy(inventory)
            mutate(bad)
            if bad['objects'][1]['parent_key'] == 'place-one':
                bad['objects'][3]['parent_key'] = 'quantity'
            with self.assertRaises(ValueError):
                C.validate_inventory(bad, req, report)
        indexed = C.validate_inventory(inventory, req, report)
        crosswalk['rows'][0]['git_token'] = 'x' * 32
        with self.assertRaisesRegex(ValueError, 'git_mismatch'):
            C.validate_crosswalk(crosswalk, indexed, report)

    def test_supplied_csv_origin_observation_and_immutable_pin(self):
        req, result = prepare(self.root)
        (self.root / 'supplied/result.csv').write_bytes(b'place,value\nWest,1.10\nEast,2.20\n')
        imported = C.import_evidence(Path(result['output']), evidence_spec(), self.root / 'supplied')
        self.assertEqual('verified_local_bytes', C.check_capture(Path(imported['output']))['status'])
        self.assertEqual('full', imported['capture']['attachments'][0]['origin'])
        with self.assertRaises(ValueError):
            C.import_evidence(Path(result['output']), evidence_spec(), self.root / 'supplied')
        pin = imported['capture']['attachments'][0]
        (self.root / 'capture' / pin['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'evidence_bytes_changed'):
            C.check_capture(Path(imported['output']))

    def test_false_complete_unknown_origin_bad_csv_and_refresh_units_reject(self):
        req, result = prepare(self.root)
        inventory = {o['key']: o for o in result['capture']['source']['inventory']['objects']}
        for field, val in [('origin', 'unknown'), ('observed_state', None),
                           ('freshness', {'data_watermark': None, 'observed_at': None, 'reference': None})]:
            bad = evidence_spec()['attachments'][0]
            bad[field] = val
            with self.assertRaises(ValueError):
                C.validate_attachment(bad, req, inventory)
        for raw in [b'a,b\n1\n', b'\xff', b'a,b\n"unterminated']:
            with self.assertRaises(ValueError):
                C.inspect_attachment(raw, 'csv')
        bad = request(render=True)
        bad['render']['dashboard_ts'] *= 1000
        with self.assertRaisesRegex(ValueError, 'refresh_intent'):
            C.validate_request(bad)
        bad = request(render=True)
        bad['render']['data_ts'] = 123
        with self.assertRaisesRegex(ValueError, 'render_contract'):
            C.validate_request(bad)

    def test_paginated_inventory_host_authority_and_scope(self):
        req, imported = prepare(self.root, list_dashboards=True)
        calls, grants = [], []
        pages = [{'total_items': 2, 'items_this_page': 1, 'next_page_start': 'page & two',
                  'dashboards': [{'id': 'another-board', 'name': 'Another'}]},
                 {'total_items': 2, 'items_this_page': 1, 'next_page_start': None,
                  'dashboards': [{'id': 'api-board-uuid', 'name': 'Garden'}]}]
        def authority(op, fingerprint):
            grants.append((op, fingerprint))
            return 'synthetic-key'
        def transport(method, url, headers, body, maximum, timeout):
            calls.append((method, url, headers))
            return 200, {}, C.encoded(pages[len(calls) - 1])
        with self.assertRaisesRegex(ValueError, 'authority_unconfigured'):
            C.capture(req, self.root / 'capture', transport=transport)
        out = C.capture(req, self.root / 'capture', authority=authority, transport=transport)
        self.assertEqual('acquired_requested_operations', out['status'])
        self.assertEqual(2, len(calls))
        self.assertIn('next_page_start=page+%26+two', calls[1][1])
        self.assertEqual('synthetic-site:synthetic-key', calls[0][2]['HTTP-X-PARTNER-AUTH'])
        self.assertEqual(C.sha(C.validate_request(req)), grants[0][1]['request_sha256'])
        self.assertNotIn('synthetic-key', Path(out['output']).read_text())
        C.check_capture(Path(out['output']))
        forged = copy.deepcopy(out['capture'])
        forged['operations'][0]['response_sha256'] = '0' * 64
        forged['content_hash'] = C.sha({k: v for k, v in forged.items() if k != 'content_hash'})
        with self.assertRaisesRegex(ValueError, 'page_operation_binding'):
            V.validate_capture(forged)

    def test_render_pending_resume_no_auth_on_download_and_dashboard_ts(self):
        req, imported = prepare(self.root, render=True)
        calls = []
        clock = [imported['capture']['created_at_epoch'] + 1]
        url = 'https://periscope-render-virginia.s3.amazonaws.com/fixture.pdf?signature=SYNTHETIC_SIGNED'
        def transport(method, endpoint, headers, body, maximum, timeout):
            calls.append((method, endpoint, headers, body))
            if method == 'POST':
                return 200, {}, C.encoded({'url': url})
            return (200, {}, b'Screenshot not ready.') if len(calls) == 2 else (200, {}, b'%PDF-1.4\nsynthetic\n%%EOF')
        authority = lambda op, fp: True if op == 'download' else 'synthetic-key'
        out = C.capture(req, self.root / 'capture', authority=authority, transport=transport, now=lambda: clock[0])
        self.assertEqual('partial', out['status'])
        self.assertEqual(1735689600, json.loads(calls[0][3])['data']['dashboard_ts'])
        self.assertNotIn('data_ts', json.loads(calls[0][3])['data'])
        self.assertNotIn('HTTP-X-PARTNER-AUTH', calls[1][2])
        clock[0] += 61
        out = C.capture(req, self.root / 'capture', authority=authority, transport=transport, now=lambda: clock[0])
        self.assertEqual('acquired_requested_operations', out['status'])
        self.assertEqual(1, sum(c[0] == 'POST' for c in calls))
        self.assertEqual('unknown', out['capture']['attachments'][0]['completeness']['status'])
        self.assertNotIn('SYNTHETIC_SIGNED', Path(out['output']).read_text())
        C.check_capture(Path(out['output']))
        forged = copy.deepcopy(out['capture'])
        forged['operations'][-1]['fingerprint_sha256'] = '0' * 64
        forged['content_hash'] = C.sha({k: v for k, v in forged.items() if k != 'content_hash'})
        with self.assertRaisesRegex(ValueError, 'download_url_binding'):
            V.verify_capture_files(forged, self.root / 'capture')

    def test_uncertain_post_is_never_retried_and_redirect_or_foreign_url_reject(self):
        req, imported = prepare(self.root, render=True)
        calls = []
        def timeout(*args):
            calls.append(args)
            raise TimeoutError('must not echo source or secret')
        authority = lambda op, fp: True if op == 'download' else 'synthetic-key'
        for _ in range(2):
            out = C.capture(req, self.root / 'capture', authority=authority, transport=timeout)
        self.assertEqual(1, len(calls))
        self.assertEqual('uncertain', out['capture']['operations'][0]['status'])
        with self.assertRaises(ValueError):
            C.render_url('https://unapproved.example/fixture.pdf', C.validate_request(req))
        with self.assertRaises(ValueError):
            C.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://unapproved.example')

    def test_cli_new_private_evidence_counts_only(self):
        req, result = prepare(self.root)
        cmd = [sys.executable, '-I', '-S', '-B', str(SCRIPTS / 'periscope_capture.py'), 'check', '--capture', result['output']]
        completed = subprocess.run(cmd, capture_output=True, timeout=15)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual({'status': 'verified_local_bytes', 'native_validation': 'not_performed'}, json.loads(completed.stdout))
        self.assertEqual(b'', completed.stderr)
        self.assertNotIn(b'Garden', completed.stdout)
        with self.assertRaises(ValueError):
            C.import_local(req, self.root / 'supplied', self.root / 'capture', allow_source_read=True)

    def test_rate_limit_and_invocation_budget_resume_without_busy_retry(self):
        req, imported = prepare(self.root, list_dashboards=True)
        calls = []
        clock = [imported['capture']['created_at_epoch'] + 1]
        def transport(*args):
            calls.append(args)
            if len(calls) == 1:
                return 429, {}, b'not retained or echoed'
            return 200, {}, C.encoded({'total_items': 1, 'items_this_page': 1, 'next_page_start': None,
                                      'dashboards': [{'id': 'api-board-uuid', 'name': 'Garden'}]})
        kwargs = {'authority': lambda op, fp: 'synthetic-key', 'transport': transport, 'now': lambda: clock[0]}
        C.capture(req, self.root / 'capture', **kwargs)
        C.capture(req, self.root / 'capture', **kwargs)
        self.assertEqual(1, len(calls))
        clock[0] += 61
        out = C.capture(req, self.root / 'capture', **kwargs)
        self.assertEqual('acquired_requested_operations', out['status'])
        self.assertEqual(2, len(calls))

    def test_pagination_overlap_response_bound_and_redirect_stop(self):
        for mode in ('overlap', 'oversized', 'redirect'):
            run = self.root / mode
            run.mkdir()
            req, imported = prepare(run, list_dashboards=True)
            calls = []
            def transport(*args):
                calls.append(args)
                if mode == 'oversized':
                    return 200, {}, b'x' * (args[4] + 1)
                if mode == 'redirect':
                    return 302, {'Location': 'https://unapproved.example'}, b''
                return 200, {}, C.encoded({'total_items': 2, 'items_this_page': 1,
                    'next_page_start': 'same-cursor', 'dashboards': [{'id': 'api-board-uuid', 'name': 'Garden'}]})
            out = C.capture(req, run / 'capture', authority=lambda op, fp: 'synthetic-key', transport=transport)
            self.assertEqual(2 if mode == 'overlap' else 1, len(calls))
            self.assertNotEqual('acquired_requested_operations', out['status'])
            self.assertEqual('not_performed', out['capture']['native_validation'])


if __name__ == '__main__':
    unittest.main()
