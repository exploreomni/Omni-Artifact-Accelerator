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
import runpy
import sys
import sysconfig
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = {
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
    'experience-enforcement')}
IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
STDLIB_ROOTS = {Path(sysconfig.get_path(name)).resolve() for name in ("stdlib", "platstdlib")}
FIRST_PARTY_IMPORTS = {
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, help=argparse.SUPPRESS)
    parser.add_argument("--report", help="New output JSON outside repository; never overwrites")
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode:
        parser.error("use the existing interpreter with -I -S -B")
    # Normal imports are restricted as defense against accidental optional use.
    # Explicit first-party file loading still trusts reviewed repository source.
    sys.meta_path.insert(0, StandardLibraryOnly())
    if args.case:
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
    checks = []
    for name in CASES:
        with tempfile.TemporaryDirectory(prefix="oaa-source-check-") as folder:
            try:
                result = transport.run([sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()),
                                        "--case", name], env=transport.environment(folder), cwd=folder,
                                       timeout=CASE_TIMEOUTS.get(name, 30), max_stdout=128 * 1024, max_stderr=128 * 1024)
                checks.append({"case": name, "passed": result.returncode == 0,
                               "exit_code": result.returncode, "output": result.stdout.decode("utf-8", "replace")})
            except (OSError, transport.ProcessError):
                checks.append({"case": name, "passed": False, "reason": "bounded_check_failed"})
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
