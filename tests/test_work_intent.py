"""First-run and continuation behavior at the public project entry point."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-accelerator/scripts/analyst_project.py"
spec = importlib.util.spec_from_file_location("project_intake_test", SCRIPT)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class WorkIntentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "engagement"

    def cli(self, *args, expect_ok=True):
        command = [sys.executable, "-I", "-S", "-B", str(SCRIPT), *map(str, args)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if expect_ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def test_questions_precede_initialization(self):
        fields = ("--output", self.root, "--name", "Service", "--surface", "app")
        self.assertEqual(self.cli("init", *fields)["choices"], ["migration", "net-new"])
        self.assertEqual(self.cli("init", *fields, "--mode", "migration")["choices"], ["preserve", "redesign"])
        self.assertFalse(self.root.exists())
        self.cli("init", *fields, "--mode", "migration", "--migration-treatment", "preserve")
        result = self.cli("plan", "--project", self.root)
        self.assertIsNone(result["intake_question"])
        self.assertEqual(result["migration_treatment"], "preserve")

    def test_pending_handoff_and_conflicting_replies(self):
        P.init(self.root, "Handoff", "migration", "both")
        self.assertEqual(P.load_project(self.root)[1]["migration_treatment"], "pending")
        args = ("migration-select", "--project", self.root, "--migration-treatment")
        self.assertEqual(self.cli(*args, "redesign"), self.cli(*args, "redesign"))
        self.cli(*args, "preserve", expect_ok=False)
        self.assertEqual(P.load_project(self.root)[1]["migration_treatment"], "redesign")
        with self.assertRaisesRegex(ValueError, "recorded migration treatment changed"):
            project = json.loads((self.root / "project.json").read_text())
            project.pop("migration_treatment")
            P.write_json(self.root / "project.json", project, replace=True)
            P.load_project(self.root)

    def test_connected_host_can_record_a_pending_treatment_and_preflight_redesign(self):
        P.init(self.root, "Source handoff", "migration", "app")
        bridge = P.routing_helper("execution_bridge")
        contracts = P.routing_helper("execution_contracts")
        request = "requests/route.json"
        P.write_json(self.root / request, {"migration_treatment": "redesign"})
        args = {"operation": "migration_select", "request": request}
        self.assertEqual(bridge.call(self.root, "execution_lifecycle", args)["migration_treatment"], "redesign")
        self.assertEqual(bridge.call(self.root, "execution_lifecycle", args)["status"], "selected")
        contracts.validate("execution_lifecycle", "concept_preflight",
                           {"options": [], "source_baseline": "contracts/source-baseline.json"})
        self.assertIn("source_baseline", bridge.contract("execution_lifecycle", "concept_preflight")["optional_request_fields"])

    def test_net_new_and_existing_repairs_keep_their_modes(self):
        for mode in ("net-new", "enhancement"):
            root = self.root.parent / mode
            result = self.cli("init", "--output", root, "--name", "Use existing Topic", "--surface", "app", "--mode", mode)
            self.assertEqual(result["mode"], mode)
            self.assertNotIn("migration_treatment", P.load_project(root)[1])
        self.cli("init", "--mode", "net-new", "--migration-treatment", "redesign", expect_ok=False)
        self.assertFalse(self.root.exists())

    def test_older_engagement_resumes_its_saved_policy(self):
        P.init(self.root, "Historical", "migration", "dashboard")
        project = P.load_project(self.root)[1]
        project.pop("migration_treatment")
        P.write_json(self.root / "project.json", project, replace=True)
        self.assertNotIn("migration_treatment", self.cli("plan", "--project", self.root))
        self.cli("migration-select", "--project", self.root, "--migration-treatment", "preserve", expect_ok=False)
