#!/usr/bin/env python3
"""Fixed source-only checks; no dependency discovery, installs or native calls.

Run with python3 -I -S -B. This is a cooperating developer check, not a sandbox
for arbitrary repository code or an authenticated release/approval service.
"""
import argparse
import hashlib
import importlib.util
import importlib.machinery
import json
import os
from pathlib import Path
import re
import runpy
import stat
import sys
import sysconfig
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "source-runner": "tests/test_source_runner.py",
    "host-entry": "tests/test_host_entry.py",
    "app-experience-release": "tests/test_app_experience_release.py",
    "native-consumers": "tests/test_native_data_consumers.py",
    "native-input-handoff": "tests/test_native_input_handoff.py",
    "native-publish": "tests/test_native_publish.py",
    "dma-topic-policy": "tests/test_dma_topic_policy.py",
    "dma-native-topics": "tests/test_dma_native_topics.py",
    "experience-intent": "tests/test_experience_intent.py",
    "experience-continuity": "tests/test_experience_continuity.py",
    "experience-packet-scope": "tests/test_experience_packet_scope.py",
    "engagement-bootstrap": "tests/test_engagement_bootstrap.py",
    "execution-preparation": "tests/test_execution_preparation.py",
    "validation-snapshot": "tests/test_validation_snapshot.py",
    "selective-reads": "tests/test_selective_reads.py",
    "context-layout": "tests/test_context_layout.py",
    "execution-bridge": "tests/test_execution_bridge.py",
    "execution-runtime": "tests/test_execution_runtime.py",
    "execution-qualification": "tests/test_execution_qualification.py",
    "assembly-provenance": "tests/test_assembly_provenance.py",
    "analytical-evidence": "tests/test_analytical_evidence.py",
    "native-demo": "tests/test_native_demo.py",
    "visual-mcp": "tests/test_visual_mcp.py",
    "visual-workflow": "tests/test_visual_workflow.py",
    "context-packets": "tests/test_context_packets.py",
    "design-intent": "tests/test_design_intent.py",
    "execution-efficiency": "tests/test_execution_efficiency.py",
    "incremental-gates": "tests/test_incremental_gates.py",
    "task-operations": "tests/test_task_operations.py",
    "domo-evidence": "tests/test_domo_evidence.py",
    "domo-connected": "tests/test_domo_connected.py",
    "domo-workflow": "tests/test_domo_visual_workflow.py",
    "sigma-evidence": "tests/test_sigma_evidence.py",
    "sigma-connected": "tests/test_sigma_connected.py",
    "report-native": "tests/test_report_native.py",
    "rdl-report": "tests/test_rdl_report.py",
    "report-source-capture": "tests/test_report_source_capture.py",
    "crystal-report": "tests/test_crystal_report.py",
    "report-source-host": "tests/test_report_source_host.py",
    "report-source-integration": "tests/test_report_source_integration.py",
    "report-contract": "tests/test_report_contract.py",
    "report-routing": "tests/test_report_routing.py",
    "metadata": "scripts/check_package.py",
    "cli": "tests/test_security_cli.py",
    "app-resources": "tests/test_security_app_resources.py",
    "intake": "tests/test_security_intake.py",
    "denial": "tests/test_security_denial.py",
    "workflow": "tests/test_delivery_workflow.py",
    "native-query": "tests/test_native_query_probe.py",
    "native-authoring": "tests/test_native_authoring.py",
    "native-create": "tests/test_native_create.py",
    "assembly": "tests/test_experience_assembly.py",
    "product-intent": "tests/test_product_intent.py",
    "data-refresh": "tests/test_data_refresh_gates.py",
    "periscope-bridge": "tests/test_periscope_visual_bridge.py",
    "periscope-capture": "tests/test_periscope_capture.py",
    "periscope-projection": "tests/test_periscope_capture_projection.py",
    "periscope-integration": "tests/test_periscope_integration.py",
    "periscope-host": "tests/test_periscope_host.py",
    "metabase-capture": "tests/test_metabase_capture.py",
    "metabase-projection": "tests/test_metabase_visual.py",
    "metabase-integration": "tests/test_metabase_integration.py",
    "metabase-host": "tests/test_metabase_host.py",
    "businessobjects-projection": "tests/test_businessobjects_visual.py",
    "businessobjects-capture": "tests/test_businessobjects_capture.py",
    "businessobjects-host": "tests/test_businessobjects_host.py",
    "businessobjects-integration": "tests/test_businessobjects_integration.py",
    "cognos-projection": "tests/test_cognos_visual.py",
    "cognos-host": "tests/test_cognos_host.py",
    "cognos-integration": "tests/test_cognos_integration.py",
    "microstrategy-capture": "tests/test_microstrategy_capture.py",
    "microstrategy-projection": "tests/test_microstrategy_visual.py",
    "microstrategy-host": "tests/test_microstrategy_host.py",
    "microstrategy-integration": "tests/test_microstrategy_integration.py",
    "microstrategy-mcp": "tests/test_microstrategy_mcp.py",
    "qlik-capture": "tests/test_qlik_capture.py",
    "qlik-projection": "tests/test_qlik_visual.py",
    "qlik-host": "tests/test_qlik_host.py",
    "qlik-integration": "tests/test_qlik_integration.py",
    "qlik-mcp": "tests/test_qlik_mcp.py",
    "thoughtspot-capture": "tests/test_thoughtspot_capture.py",
    "thoughtspot-projection": "tests/test_thoughtspot_visual.py",
    "thoughtspot-host": "tests/test_thoughtspot_host.py",
    "thoughtspot-integration": "tests/test_thoughtspot_integration.py",
    "thoughtspot-mcp": "tests/test_thoughtspot_mcp.py",
    "webfocus-bridge": "tests/test_webfocus_visual.py",
    "webfocus-capture": "tests/test_webfocus_capture.py",
    "webfocus-integration": "tests/test_webfocus_integration.py",
    "webfocus-host": "tests/test_webfocus_host.py",
    "stage-gates": "tests/test_stage_gates.py",
    "stage-gate-integration": "tests/test_stage_gate_integration.py",
    "conversation-choice": "tests/test_conversation_choice.py",
    "native-stage-gates": "tests/test_native_stage_gate.py",
    "execution-readiness": "tests/test_execution_readiness.py",
    "experience-contract": "tests/test_experience_contract.py",
    "experience-enforcement": "tests/test_experience_enforcement.py",
}
# Journal integration cases revalidate retained source and candidate evidence.
# Keep them bounded without turning a larger valid fixture into a false failure.
CASE_TIMEOUTS = {name: 120 for name in ('workflow', 'product-intent', 'stage-gates',
    'stage-gate-integration', 'conversation-choice', 'native-stage-gates', 'native-create',
    'experience-enforcement', 'data-refresh', 'periscope-integration', 'metabase-integration', 'webfocus-integration', 'thoughtspot-integration', 'qlik-integration', 'microstrategy-integration', 'cognos-integration', 'businessobjects-integration', 'report-native', 'report-source-integration')}
# The three-route native authorization suite repeats complete source-bound
# lifecycles. Keep a bounded allowance separate from runtime transport deadlines.
CASE_TIMEOUTS.update({'dma-native-topics':180,'dma-topic-policy':120})
CASE_TIMEOUTS.update({'app-experience-release':240, 'native-publish':360, 'host-entry':120})
CASE_TIMEOUTS['native-stage-gates'] = 600
CASE_TIMEOUTS.update({'execution-runtime': 120, 'execution-bridge': 120, 'native-demo': 480})
CASE_TIMEOUTS.update({'execution-preparation': 120, 'validation-snapshot': 120, 'selective-reads': 120, 'context-layout': 120})
CASE_TIMEOUTS.update({'experience-continuity': 180, 'engagement-bootstrap': 120})
CASE_TIMEOUTS['experience-enforcement'] = 240
# Complete source-bound lifecycle suites outgrew the original whole-suite budgets.
# These finite test allowances do not change production transport deadlines,
# output limits, assertions, required coverage or activation/authorization gates.
CASE_TIMEOUTS.update({'incremental-gates': 360, 'report-routing': 60,
                      'native-create': 360, 'stage-gates': 360})
# These suites also exceeded their older bounds in a complete serial run.
# Focused runs pass; keep headroom for repeated source/evidence revalidation.
CASE_TIMEOUTS.update({'context-packets': 90, 'design-intent': 90,
                      'execution-efficiency': 90, 'conversation-choice': 240,
                      'experience-enforcement': 480})
# The explicit existing-Node lane verifies its large native binary before use.
CASE_TIMEOUTS['native-input-handoff'] = 60
NODE_CASE = 'native-input-handoff'
NODE_PATH_ENV = 'OAA_SOURCE_NODE_PATH'
NODE_SHA_ENV = 'OAA_SOURCE_NODE_SHA256'
MAX_SOURCE_RUNTIME = 256 * 1024 * 1024
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
STDLIB_ROOTS = {Path(sysconfig.get_path(name)).resolve() for name in ("stdlib", "platstdlib")}
FIRST_PARTY_IMPORTS = {
    "visual_mcp": ROOT / "skills/omni-artifact-accelerator/scripts/visual_mcp.py",
    "visual_workflow": ROOT / "skills/omni-artifact-accelerator/scripts/visual_workflow.py",
    "cowork": ROOT / "skills/omni-backend-handoff/scripts/cowork.py",
    "analyst_project": ROOT / "skills/omni-artifact-accelerator/scripts/analyst_project.py",
    "test_experience_quality": ROOT / "tests/test_experience_quality.py",
    "test_design_intent": ROOT / "tests/test_design_intent.py",
    "test_design_review": ROOT / "tests/test_design_review.py",
}


class StandardLibraryOnly:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in sys.builtin_module_names or importlib.machinery.FrozenImporter.find_spec(fullname):
            return None
        if fullname in FIRST_PARTY_IMPORTS:
            return importlib.util.spec_from_file_location(fullname, FIRST_PARTY_IMPORTS[fullname])
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is not None and spec.origin:
            origin = Path(spec.origin).resolve()
            if origin == FIRST_PARTY_IMPORTS.get(fullname):
                return None
            if (not {"site-packages", "dist-packages"}.intersection(origin.parts)
                    and any(origin.is_relative_to(root) for root in STDLIB_ROOTS)):
                return None
        if (fullname == "harness" or fullname.startswith("harness.")) and spec is not None:
            locations = ([spec.origin] if spec.origin else list(spec.submodule_search_locations or []))
            if locations and all(Path(p).resolve().is_relative_to(ROOT / "harness") for p in locations):
                return None
        raise ModuleNotFoundError("Dependency import outside source-only check scope")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_pins():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob("*")) if not any(part in IGNORED for part in p.relative_to(ROOT).parts)
            and p.is_file() and not p.is_symlink()}


class SourceRuntimeError(ValueError):
    """An invalid existing-runtime selection; never an acquisition request."""


def verify_node_runtime(selection):
    """Check selected existing native bytes; not approval or hostile-host isolation."""
    path, expected = selection.get('path'), selection.get('sha256')
    if not isinstance(path, str) or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise SourceRuntimeError('source_runtime_path_and_sha256_required')
    p = Path(path)
    if (not p.is_absolute() or str(p) != path or '..' in p.parts
            or any(part.is_symlink() for part in (p, *p.parents))):
        raise SourceRuntimeError('source_runtime_requires_canonical_path_without_links')
    try:
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise SourceRuntimeError('source_runtime_file_unavailable') from None
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_SOURCE_RUNTIME
                or before.st_mode & 0o022 or not os.access(p, os.X_OK)):
            raise SourceRuntimeError('source_runtime_requires_bounded_regular_protected_executable')
        digest, size, prefix = hashlib.sha256(), 0, b''
        while True:
            block = os.read(fd, min(1024 * 1024, MAX_SOURCE_RUNTIME + 1 - size))
            if not block:
                break
            if not prefix:
                prefix = block[:4]
            size += len(block)
            if size > MAX_SOURCE_RUNTIME:
                raise SourceRuntimeError('source_runtime_byte_limit')
            digest.update(block)
        after, current = os.fstat(fd), os.stat(p, follow_symlinks=False)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                                  value.st_mtime_ns, value.st_ctime_ns)
        if (identity(before) != identity(after) or identity(after) != identity(current)
                or size != before.st_size or digest.hexdigest() != expected):
            raise SourceRuntimeError('source_runtime_pin_mismatch_or_changed')
        # ELF and Mach-O native executables, including universal Mach-O. No shebang.
        if prefix not in (b'\x7fELF', b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
                          b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
                          b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                          b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'):
            raise SourceRuntimeError('source_runtime_native_executable_required')
        return {'path': path, 'sha256': expected}
    except OSError:
        raise SourceRuntimeError('source_runtime_file_unavailable_or_changed') from None
    finally:
        os.close(fd)


def run_case(name, transport, node=None):
    timeout = CASE_TIMEOUTS.get(name, 30)
    started = time.monotonic()
    check = {'case': name, 'passed': False}
    print(f"source check: {name} (limit {timeout}s)", file=sys.stderr, flush=True)
    with tempfile.TemporaryDirectory(prefix="oaa-source-check-") as folder:
        try:
            argv = [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '--case', name]
            if name == NODE_CASE:
                if node is None:
                    raise SourceRuntimeError('existing_node_runtime_not_selected')
                check['runtime'] = verify_node_runtime(node)
                argv.extend(['--node-runtime', node['path'], '--node-sha256', node['sha256']])
            result = transport.run(argv, env=transport.environment(folder), cwd=folder,
                                   timeout=timeout, max_stdout=128 * 1024, max_stderr=128 * 1024)
            if name == NODE_CASE:
                verify_node_runtime(node)
                check['runtime']['bytes_verified_before_and_after'] = True
            check.update(passed=result.returncode == 0, exit_code=result.returncode,
                         output=result.stdout.decode('utf-8', 'replace'))
        except SourceRuntimeError as error:
            check.update(reason='source_runtime_unavailable', detail=str(error))
        except (OSError, transport.ProcessError):
            check.update(reason='bounded_check_failed')
    check.update(elapsed_seconds=round(time.monotonic() - started, 3), timeout_seconds=timeout)
    print(f"source check: {name} {'passed' if check['passed'] else 'FAILED'} "
          f"in {check['elapsed_seconds']}s", file=sys.stderr, flush=True)
    return check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--report", help="New output JSON outside repository; never overwrites")
    parser.add_argument('--node-runtime', help='Explicit existing native Node path for its original-source lane only')
    parser.add_argument('--node-sha256', help='SHA-256 of that existing runtime; integrity is not approval')
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode:
        parser.error("use the existing interpreter with -I -S -B")
    if bool(args.node_runtime) != bool(args.node_sha256):
        parser.error('provide both --node-runtime and --node-sha256')
    node = {'path': args.node_runtime, 'sha256': args.node_sha256} if args.node_runtime else None
    # Ambient variables never select a runtime for this maintained runner.
    os.environ.pop(NODE_PATH_ENV, None)
    os.environ.pop(NODE_SHA_ENV, None)
    # Normal imports are restricted as defense against accidental optional use.
    # Explicit first-party file loading still trusts reviewed repository source.
    sys.meta_path.insert(0, StandardLibraryOnly())
    if args.case:
        if args.case == NODE_CASE:
            if node is None:
                parser.error('this required case needs explicit --node-runtime and --node-sha256')
            try:
                verify_node_runtime(node)
            except (OSError, SourceRuntimeError):
                parser.error('selected existing Node runtime did not pass byte/path checks')
            os.environ[NODE_PATH_ENV], os.environ[NODE_SHA_ENV] = node['path'], node['sha256']
        if args.case == "metadata":
            sys.argv = [str(ROOT / CASES[args.case])]
            runpy.run_path(sys.argv[0], run_name="__main__")
        else:
            module = load("source_case", CASES[args.case])
            result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromModule(module))
            print(json.dumps({"tests_run": result.testsRun, "skipped": len(result.skipped),
                              "required_coverage": result.testsRun > 0 and not result.skipped}))
            return int(not result.wasSuccessful() or result.testsRun == 0 or bool(result.skipped))
        return 0
    output = None
    if args.report:
        output = Path(args.report).absolute()
        if (output.resolve().is_relative_to(ROOT) or output.exists() or not output.parent.is_dir()
                or any(p.is_symlink() for p in (output, *output.parents))):
            parser.error("report must be a new file in an existing canonical directory outside repository")
    before = source_pins()
    transport = load("source_process", "skills/omni-bi-engineer/scripts/cli_process.py")
    checks = [run_case(name, transport, node) for name in CASES]
    after = source_pins()
    report = {"kind": "oaa_source_security_validation", "passed": all(c["passed"] for c in checks) and before == after,
              "checks": checks, "source_unchanged_during_checks": before == after,
              "source_sha256": before, "interpreter": {"path": sys.executable, "version": sys.version.split()[0]},
              "qualification": {"source_local": True, "dependency_approval": False, "host_isolation": False,
                                "native_tenant": False, "rendered": False, "release_authorized": False}}
    if output:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(report, stream, indent=2); stream.write("\n")
    print(json.dumps({"passed": report["passed"], "checks": [{"case": c["case"], "passed": c["passed"]} for c in checks],
                      "source_unchanged": before == after, "report": str(output) if output else None}, indent=2))
    if not report["passed"]:
        for check in checks:
            if not check["passed"]:
                print(check.get("output", check.get("reason")), file=sys.stderr)
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
