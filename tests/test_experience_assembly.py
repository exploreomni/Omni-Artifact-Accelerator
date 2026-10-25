"""Actual local assembly boundaries; no browser or native execution claims."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-app-engineer/scripts/assemble_experience.py"
SPEC = importlib.util.spec_from_file_location("experience_assembly", SCRIPT)
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


class ExperienceAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / 'engagement'
        spec = importlib.util.spec_from_file_location('assembly_project_fixture', SCRIPT.parents[2] /
            'omni-artifact-accelerator/scripts/analyst_project.py')
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
        P.init(self.root, 'Existing composition repair', 'enhancement', 'app', 'none')
        # Historical composition fixture. New engagements are exercised in gate integration tests.
        project = P.load_project(self.root)[1]
        project.pop('stage_gate_policy')
        project.pop('workflow_quality_policy', None)
        P.write_json(self.root / 'project.json', project, replace=True)
        self.spec = {"schema_version": 1,
                     "template": self.file("view.html", "<main>{{OAA:DATA}}</main>{{OAA:CORE}}{{OAA:VIEW}}"),
                     "slots": [self.slot("DATA", "json", "rows.json", '{"name":"Original synthetic collection","value":0}'),
                               self.slot("CORE", "script", "core.js", "globalThis.Synthetic = {count: 0};", provides=["Synthetic"]),
                               self.slot("VIEW", "script", "view.js", "Synthetic.count += 1;", requires=["CORE"])],
                     "references": [{"role": "queries", **self.file("query.json", '{"native_binding":null}')}]}

    def tearDown(self):
        self.tmp.cleanup()

    def file(self, path, content):
        raw = content.encode() if isinstance(content, str) else content
        (self.root / path).write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    def slot(self, name, kind, path, content, **extra):
        return {"name": name, "kind": kind, **self.file(path, content),
                **({"script_type": "classic"} if kind == "script" else {}), **extra}

    def manifest(self):
        (self.root / "assembly.json").write_text(json.dumps(self.spec))
        return "assembly.json"

    def test_two_independent_compositions_preserve_inputs_and_order(self):
        first = A.build(self.root, self.manifest(), "first")
        self.spec["template"] = self.file("reader.html", "<article><h1>Collection record</h1>{{OAA:DATA}}</article>\n{{OAA:CORE}}{{OAA:VIEW}}")
        second = A.build(self.root, self.manifest(), "second")
        for result in (first, second):
            self.assertEqual(result["script_order"], ["CORE", "VIEW"])
            self.assertFalse(result["source_execution"])
            self.assertEqual(result["native_verification"], "not_assessed")
            html = (Path(result["output_directory"]) / "index.html").read_text()
            self.assertIn('"value":0', html)
            self.assertNotIn("{{OAA:", html)
            self.assertEqual(hashlib.sha256(html.encode()).hexdigest(), result["output"]["sha256"])
        self.assertNotEqual(first["output"]["sha256"], second["output"]["sha256"])
        retained = json.loads((self.root / first['first_candidate_record']).read_text())
        self.assertEqual(retained['sha256'], first['output']['sha256'])
        (self.root / 'first/index.html').write_text('Changed by subsequent review')
        self.assertEqual(hashlib.sha256((self.root / retained['path']).read_bytes()).hexdigest(), retained['sha256'])

    def test_frozen_inputs_and_existing_output_are_not_overwritten(self):
        manifest = self.manifest()
        A.build(self.root, manifest, "built")
        with self.assertRaisesRegex(ValueError, "new directory"):
            A.build(self.root, manifest, "built")
        (self.root / "query.json").write_text('{"native_binding":"changed"}')
        with self.assertRaisesRegex(ValueError, "hash changed"):
            A.build(self.root, manifest, "changed")
        self.assertFalse((self.root / "changed").exists())

    def test_dependency_order_collision_and_placeholders_are_validated(self):
        self.spec["slots"][2]["provides"] = ["Synthetic"]
        with self.assertRaisesRegex(ValueError, "collision"):
            A._assemble(self.root, self.manifest())
        del self.spec["slots"][2]["provides"]
        self.spec["template"] = self.file("view.html", "{{OAA:DATA}}{{OAA:VIEW}}{{OAA:CORE}}")
        with self.assertRaisesRegex(ValueError, "script order"):
            A._assemble(self.root, self.manifest())
        self.spec["template"] = self.file("view.html", "{{OAA:DATA}}{{OAA:CORE}}{{OAA:VIEW}}{{OAA:MISSING}}")
        with self.assertRaisesRegex(ValueError, "slots differ"):
            A._assemble(self.root, self.manifest())

    def test_paths_and_symlinks_cannot_escape_selected_project(self):
        for path in ("../outside", "/tmp/outside", "./view.html", "a/../view.html", "C:/outside"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                A.local_path(self.root, path)
        (self.root / "alias.js").symlink_to(self.root / "core.js")
        self.spec["slots"][1]["path"] = "alias.js"
        with self.assertRaisesRegex(ValueError, "symlink"):
            A._assemble(self.root, self.manifest())

    def test_json_embedding_cannot_close_script_and_code_is_not_executed(self):
        self.spec["slots"][0] = self.slot("DATA", "json", "rows.json", json.dumps({"label": "</script><script>bad()</script>"}))
        html, _ = A._assemble(self.root, self.manifest())
        self.assertIn("\\u003c/script>", html)
        self.assertNotIn("<script>bad()", html)
        self.spec["slots"][1] = self.slot("CORE", "script", "core.js", "throw new Error('must never execute during assembly');")
        A.build(self.root, self.manifest(), "inert")
        self.spec["slots"][1] = self.slot("CORE", "script", "core.js", 'const text = "</script>";')
        with self.assertRaisesRegex(ValueError, "tokenizer"):
            A._assemble(self.root, self.manifest())

    def test_budgets_and_duplicate_json_keys_fail_before_output(self):
        self.spec["max_output_bytes"] = 1
        with self.assertRaisesRegex(ValueError, "output budget"):
            A.build(self.root, self.manifest(), "too-large")
        self.assertFalse((self.root / "too-large").exists())
        (self.root / "bad.json").write_text('{"schema_version":1,"schema_version":2}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            A._assemble(self.root, "bad.json")

    def test_cli_builds_new_local_artifact_only(self):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', str(SCRIPT), "--project", str(self.root),
                                 "--manifest", self.manifest(), "--output", "cli"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(Path(report["output_directory"]), self.root / "cli")
        self.assertEqual(json.loads((self.root / "cli/assembly.json").read_text())["output"], report["output"])


if __name__ == "__main__":
    unittest.main()
