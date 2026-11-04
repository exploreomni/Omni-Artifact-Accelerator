"""Fixed, startup-selected Domo acquisition through the existing source engine.

Pins establish integrity, not permission. A qualified local host must separately
authorize the reviewed runtime/dependency closure. No target or model-call tools.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ap = module('domo_host_project', HERE / 'analyst_project.py')
process = module('domo_host_process', HERE.parents[1] / 'omni-bi-engineer/scripts/cli_process.py')
contract = module('domo_host_contract', HERE.parents[1] / 'omni-artifact-translator/scripts/domo_source_contract.py')


def need(ok, code):
    ap.need(ok, 'domo.host.' + code)


def pin(root, record):
    need(type(record) is dict and set(record) == {'path', 'sha256'}, 'file_pin_required')
    path = ap.relative_file(root, record['path'])
    need(ap.digest(path.read_bytes()) == record['sha256'], 'file_changed')
    return path


def capabilities(value):
    need(type(value) is dict and value.get('schema_version') == 'domo-source-capabilities.v1'
         and value.get('extension_name') == 'domo-source-operations'
         and value.get('extension_version') == '0.1.0'
         and value.get('target_write_authority') is False, 'capability_profile')
    need(set(('domo-acquire', 'domo-inventory', 'domo-source-evidence')) <= set(value.get('supported_commands', [])),
         'source_commands_required')
    files = value.get('implementation_files')
    need(type(files) is list and 0 < len(files) <= 10000, 'implementation_manifest_required')
    seen = set()
    for item in files:
        need(type(item) is dict and set(item) == {'path', 'sha256', 'bytes'}, 'implementation_file')
        path = Path(item['path'])
        need(not path.is_absolute() and '..' not in path.parts and path.as_posix() == item['path']
             and '\\' not in item['path'] and path.suffix == '.py' and item['path'] not in seen
             and re.fullmatch(r'[a-f0-9]{64}', item['sha256']) and type(item['bytes']) is int
             and 0 <= item['bytes'] <= 10 * 1024 * 1024, 'implementation_file')
        seen.add(item['path'])
    return {'status': 'recognized_source_contract', 'runtime_loaded': False,
            'source_access_verified': False, 'live_qualification': 'not_established',
            'native_write_authority': False, 'dependency_approval_verified': False}


class DomoOperations:
    def __init__(self, project, configuration, *, allow_read=False, allow_dataflows=False, runner=None):
        need(allow_read is True and type(allow_dataflows) is bool, 'startup_read_grant_required')
        self.root, _ = ap.load_project(project)
        path = ap.relative_file(self.root, configuration)
        self.configuration = {'path': configuration, 'sha256': ap.digest(path.read_bytes())}
        self.config, _ = ap.read_json(path)
        c = self.config
        need(set(c) == {'schema_version', 'runtime', 'capabilities', 'operations', 'credential_environment',
             'max_invocations', 'max_total_requests', 'timeout_seconds'} and
             c['schema_version'] == 'oaa-domo-host.v1', 'configuration_contract')
        self.allow_dataflows = allow_dataflows
        self.runner = runner or process.run
        self.expected, _ = ap.read_json(pin(self.root, c['capabilities']))
        capabilities(self.expected)
        for key, maximum in (('max_invocations', 200), ('max_total_requests', 20000), ('timeout_seconds', 300)):
            need(type(c[key]) is int and 1 <= c[key] <= maximum, 'finite_budget_required')
        self.credentials = c['credential_environment']
        need(type(self.credentials) is dict and set(self.credentials) <= {
            'client_id', 'client_secret', 'bearer_token', 'product_token', 'dataflow_token'}, 'credential_channels')
        need(all(type(v) is str and re.fullmatch(r'DOMO_[A-Z0-9_]{1,80}', v) for v in self.credentials.values())
             and len(set(self.credentials.values())) == len(self.credentials), 'source_environment_names_only')
        need(('client_id' in self.credentials) == ('client_secret' in self.credentials)
             and not ('client_id' in self.credentials and 'bearer_token' in self.credentials)
             and any(k in self.credentials for k in ('client_id', 'bearer_token', 'product_token')),
             'explicit_auth_route_required')
        self.entries = {}
        folders = []
        need(type(c['operations']) is list and 0 < len(c['operations']) <= 100, 'operations_required')
        for entry in c['operations']:
            need(type(entry) is dict and set(entry) == {'id', 'request', 'directory'}, 'operation_entry')
            value, _ = ap.read_json(pin(self.root, entry['request']))
            contract.request(value)
            need(entry['id'] == value['request_id'] and entry['id'] not in self.entries, 'unique_operation_identity')
            rel = Path(entry['directory'])
            need(not rel.is_absolute() and rel.as_posix() == entry['directory'] and
                 '..' not in rel.parts and '\\' not in entry['directory'] and str(rel) != '.', 'output_scope')
            folder = ap.no_links(self.root / rel)
            need(not any(folder == p or folder.is_relative_to(p) or p.is_relative_to(folder) for p in folders),
                 'overlapping_outputs')
            folders.append(folder)
            need(not value['scope']['include_dataflows'] or (allow_dataflows and 'dataflow_token' in self.credentials),
                 'separate_dataflow_grant_required')
            need(value['limits']['max_elapsed_seconds'] <= c['timeout_seconds'], 'child_timeout_exceeds_host')
            self.entries[entry['id']] = (entry, value, folder)
        self.check_runtime()

    def check_runtime(self):
        pin(self.root, self.configuration)
        pin(self.root, self.config['capabilities'])
        runtime = self.config['runtime']
        need(type(runtime) is dict and set(runtime) <= {'executable', 'interpreter', 'source_root', 'closure'}
             and {'executable', 'source_root', 'closure'} <= set(runtime), 'runtime_contract')
        exe = runtime['executable']
        env = {'OAA_OMNI_CLI_PATH': exe.get('path'), 'OAA_OMNI_CLI_SHA256': exe.get('sha256')}
        if runtime.get('interpreter'):
            env.update(OAA_OMNI_RUNTIME_PATH=runtime['interpreter'].get('path'),
                       OAA_OMNI_RUNTIME_SHA256=runtime['interpreter'].get('sha256'))
        argv = process.command(env)
        if runtime.get('interpreter'):
            argv.insert(1, '-I')
        closure = runtime['closure']
        need(type(closure) is list and 0 < len(closure) <= 10000, 'reviewed_dependency_closure_required')
        hashes = {}
        for item in closure:
            need(type(item) is dict and set(item) == {'path', 'sha256'} and item['path'] not in hashes, 'closure_pin')
            process.pinned_file(item['path'], item['sha256'])
            hashes[item['path']] = item['sha256']
        source_root = ap.no_links(Path(runtime['source_root']))
        need(Path(runtime['source_root']).is_absolute() and source_root.is_dir(), 'source_root')
        for item in self.expected['implementation_files']:
            path = source_root / item['path']
            need(hashes.get(str(path)) == item['sha256'] and path.stat().st_size == item['bytes'],
                 'implementation_closure_incomplete')
        for entry, _, _ in self.entries.values():
            pin(self.root, entry['request'])
        return argv

    def describe(self):
        self.check_runtime()
        return {**capabilities(self.expected), 'operations': list(self.entries),
                'visual_export': 'requires_qualified_capture_or_supplied_export',
                'query_capture': 'requires_qualified_capture_or_supplied_export'}

    def _invoke(self, argv, env, home):
        result = self.runner(argv, env=env, cwd=home, timeout=self.config['timeout_seconds'], max_stdout=512 * 1024)
        need(result.returncode == 0, 'source_requires_review_no_automatic_retry')
        try:
            value = json.loads(result.stdout, object_pairs_hook=ap.reject_duplicate,
                               parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
            need(type(value) is dict, 'source_response_object_required')
            return value
        except (ValueError, UnicodeError):
            raise ValueError('domo.host.invalid_source_response') from None

    def run(self, operation_id, resume=False):
        need(operation_id in self.entries and type(resume) is bool, 'operation_not_selected')
        argv = self.check_runtime()
        entry, value, folder = self.entries[operation_id]
        host_state = ap.no_links(self.root / 'evidence' / 'domo-host')
        host_state.mkdir(mode=0o700, parents=True, exist_ok=True)
        key = self.configuration['sha256']
        fd = os.open(ap.no_links(host_state / (key + '.lock')), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ledger = host_state / (key + '.json')
            state = ap.read_json(ledger)[0] if ledger.exists() else {'invocations': 0, 'reserved_requests': 0, 'receipts': {}}
            receipt_path = folder / 'operation.json'
            if resume:
                need(folder.is_dir() and receipt_path.is_file(), 'resume_requires_recorded_outcome')
                need(state.get('receipts', {}).get(operation_id) == ap.digest(receipt_path.read_bytes()), 'resume_receipt_changed')
                receipt, _ = ap.read_json(receipt_path)
                need(receipt.get('request') == value and receipt.get('configuration') == self.configuration,
                     'resume_context_changed')
                for item in receipt['files']:
                    pin(self.root, item)
                return receipt
            need(not folder.exists(), 'existing_operation_requires_reconcile')
            need(state['invocations'] < self.config['max_invocations'] and state['reserved_requests'] +
                 value['limits']['max_requests'] <= self.config['max_total_requests'], 'budget_exhausted')
            state['invocations'] += 1
            state['reserved_requests'] += value['limits']['max_requests']
            ap.write_json(ledger, state, replace=ledger.exists())
            ap.no_links(folder.parent).mkdir(mode=0o700, parents=True, exist_ok=True)
            folder.mkdir(mode=0o700, parents=False, exist_ok=False)
            bridge = folder / 'source-request.json'
            ap.write_json(bridge, contract.bridge_request(value))
            ap.write_json(folder / 'intent.json', {'request': value, 'configuration': self.configuration,
                'state': 'reserved', 'target_write_authority': False})
            with tempfile.TemporaryDirectory(prefix='domo-source-', dir=host_state) as home:
                env = process.environment(home)
                env.update(PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1')
                observed = self._invoke(argv + ['domo-capabilities'], env, home)
                need(observed == self.expected, 'capabilities_changed')
                self.check_runtime()
                source_env = dict(env)
                command = argv + ['domo-acquire', '--request', str(bridge), '--output', str(folder / 'acquired.json'),
                                  '--trusted-domo-host', contract.origin(value['source']['origin'])]
                for field, name in self.credentials.items():
                    if field == 'dataflow_token' and not value['scope']['include_dataflows']:
                        continue
                    token = os.environ.get(name, '')
                    need(0 < len(token) <= 8192 and not any(c.isspace() for c in token), 'source_credentials_missing')
                    source_env[name] = token
                    command.extend(['--' + field.replace('_', '-') + '-env', name])
                if value['scope']['include_dataflows']:
                    command += ['--enable-dataflow-api', '--dataflow-evidence-dir', str(folder / 'private-dataflows')]
                command += ['--max-dependency-dataflows', str(value['scope']['max_dependency_dataflows']),
                            '--max-dependency-datasets', str(value['scope']['max_dependency_datasets'])]
                acquired = self._invoke(command, source_env, home)
                need(acquired.get('output') == str(folder / 'acquired.json') and
                     acquired.get('target_write_authority') is False, 'acquisition_receipt')
                # The typed accessor, not a guessed generic bundle path, exports evidence.
                exported = self._invoke(argv + ['domo-source-evidence', '--bundle', str(folder / 'acquired.json'),
                    '--output', str(folder / 'source-evidence.json')], env, home)
                need(exported.get('output') == str(folder / 'source-evidence.json') and
                     exported.get('target_write_authority') is False, 'evidence_receipt')
            evidence, _ = ap.read_json(folder / 'source-evidence.json')
            need(type(evidence) is dict and evidence.get('contract_version') == 'omnikit.domo.evidence.v1'
                 and type(evidence.get('objects')) is list, 'typed_evidence_contract')
            need(all(row.get('tenant_ref') == value['source']['tenant_ref'] and
                     row.get('visibility_principal_ref') == value['source']['principal_ref']
                     for row in evidence['objects']), 'evidence_identity_changed')
            files = [{'path': str(p.relative_to(self.root)), 'sha256': ap.digest(p.read_bytes())}
                     for p in (bridge, folder / 'acquired.json', folder / 'source-evidence.json')]
            receipt = {'schema_version': 'oaa-domo-source-operation.v1', 'operation_id': operation_id,
                'request': value, 'configuration': self.configuration, 'files': files,
                'evidence': files[-1], 'import_state': 'review_redaction_before_frontend_import', 'state': 'source_captured_requires_review',
                'effective_access': 'not_established', 'native_validation': 'not_run',
                'target_write_authority': False, 'acceptance_authority': False}
            ap.write_json(receipt_path, receipt)
            state['receipts'][operation_id] = ap.digest(receipt_path.read_bytes())
            ap.write_json(ledger, state, replace=True)
            return receipt
