"""First-party synthetic boundary checks. No customer input or sandbox launch."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness import asset_checks, launcher, model_core, quarantine, worker


def local_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = local_module("source_check", "scripts/check_package.py")
P = local_module("project", "skills/omni-artifact-accelerator/scripts/analyst_project.py")


class SpatialBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / "harness/fixtures/inspection-assembly.json").read_bytes()
        self.outputs = worker.compile_bytes(self.raw, model_core.compile_scene, asset_checks.validate_glb)

    def inspect(self, outputs, raw=None):
        return quarantine.inspect_outputs(outputs, asset_checks.validate_glb, model_core.compile_scene,
                                          self.raw if raw is None else raw)

    def test_actual_bundle_reconstructs_original_input_and_never_grants_promotion(self):
        result = self.inspect(self.outputs)
        self.assertEqual(result["status"], "structurally_checked")
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(set(result["hashes"]), set(quarantine.FILES))
        manifest = json.loads(self.outputs["manifest.json"])
        self.assertEqual(manifest["input_sha256"], hashlib.sha256(self.raw).hexdigest())

    def test_worker_and_quarantine_reject_ambiguous_json_and_forged_claims(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                worker.compile_bytes(raw, model_core.compile_scene, asset_checks.validate_glb)
        for update in ({"host_isolation": "approved"}, {"input_sha256": "f" * 64}, {"approved": True}):
            outputs = dict(self.outputs)
            manifest = json.loads(outputs["manifest.json"])
            manifest.update(update)
            outputs["manifest.json"] = worker.encode(manifest)
            with self.assertRaises(ValueError): self.inspect(outputs)

    def test_substituted_scene_model_and_derived_claims_fail_even_with_resealed_hashes(self):
        outputs = dict(self.outputs)
        scene = json.loads(outputs["scene.json"])
        scene["entities"][0]["label"] = "Different original object"
        outputs["scene.json"] = worker.encode(scene)
        manifest = json.loads(outputs["manifest.json"])
        manifest["scene_sha256"] = hashlib.sha256(outputs["scene.json"]).hexdigest()
        outputs["manifest.json"] = worker.encode(manifest)
        with self.assertRaisesRegex(ValueError, "reconstruction"): self.inspect(outputs)
        changed = json.loads(self.raw)
        changed["entities"][0]["label"] = "Another input"
        other = worker.compile_bytes(worker.encode(changed), model_core.compile_scene, asset_checks.validate_glb)
        forged = json.loads(other["manifest.json"])
        forged["input_sha256"] = hashlib.sha256(self.raw).hexdigest()
        other["manifest.json"] = worker.encode(forged)
        with self.assertRaisesRegex(ValueError, "reconstruction"): self.inspect(other)
        outputs = dict(self.outputs)
        forged = json.loads(outputs["manifest.json"])
        forged["model"]["entities"][0]["id"] = "forged_identity"
        outputs["manifest.json"] = worker.encode(forged)
        with self.assertRaisesRegex(ValueError, "reconstruction"): self.inspect(outputs)

    def test_copy_is_exact_private_fresh_and_unpromoted(self):
        result = self.inspect(self.outputs)
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            dest = parent / "candidate"
            copied = quarantine.copy_exact(self.outputs, dest, result["hashes"])
            self.assertFalse(copied["promotion_authorized"])
            self.assertEqual({p.name: p.read_bytes() for p in dest.iterdir()}, self.outputs)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o700)
            with self.assertRaises(FileExistsError): quarantine.copy_exact(self.outputs, dest, result["hashes"])
            changed = dict(self.outputs); changed["model.glb"] += b"changed"
            with self.assertRaisesRegex(ValueError, "output_changed"):
                quarantine.copy_exact(changed, parent / "changed", result["hashes"])
            link = parent / "linked"; link.symlink_to(dest, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "output_path_invalid"):
                quarantine.copy_exact(self.outputs, link / "out", result["hashes"])
            self.assertFalse((parent / "changed").exists())

    def test_launcher_can_only_prepare_and_cannot_self_approve(self):
        request = launcher.prepare(ROOT / "harness/fixtures/inspection-assembly.json")
        self.assertEqual(request["profile"], model_core.PROFILE)
        self.assertEqual(request["scene_sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(request["authorization"], "not_granted")
        self.assertFalse(launcher.capabilities()["execute"])
        for forged in ({"approved": True}, {"host_gate": "approved", "runtime": "local"}, request):
            with self.assertRaisesRegex(PermissionError, "execution_blocked"):
                launcher.execute(forged, approved=True, allow_host=True)

    def test_metadata_profile_rejects_yaml_execution_syntax(self):
        self.assertEqual(CHECK.metadata_scalars('name: "Original"\ndescription: "A small skill"',
                                              {"name", "description"})["name"], "Original")
        for bad in ('name: !!python/object/apply:run', 'name: &alias something', 'name: |',
                    'name: [nested]', 'name: OK\nname: Duplicate'):
            with self.assertRaises(ValueError): CHECK.metadata_scalars(bad, {"name"})

    def test_spatial_capability_routes_only_selected_apps_and_carries_packet_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve() / "run"
            P.init(root, "Synthetic object inspection", "net-new", "app", branding="none")
            self.assertNotIn("3d-modeler", {r["role"] for r in P.plan(root)["roles"]})
            intent = json.loads((root / "contracts/design-intent.json").read_text())
            intent["requirements"] = [{"id": "inspect-object", "category": "experience",
                "purpose": "Inspect synthetic equipment", "surfaces": ["app"], "required": True,
                "origin": "user", "disposition": "selected", "value": "Task-driven object inspection",
                "asset_ids": [], "decision_ref": "synthetic request",
                "contexts": [{"id": "inspection", "appearance": "light", "state": "ready"}],
                "delivery": {"source_ref": "synthetic brief", "owner": "3d-modeler",
                    "behavior": "Select a component and return to its exact metrics",
                    "destinations": ["inspection"], "dependency_paths": [], "capabilities": ["spatial-modeling"]}}]
            (root / "contracts/design-intent.json").write_text(json.dumps(intent))
            P.intent_helper().select(root, root / "contracts/design-intent.json", "contracts/selected-intent.json")
            roles = {r["role"]: r for r in P.plan(root)["roles"]}
            self.assertIn("3d-modeler", roles)
            self.assertEqual(roles["app-engineer"]["modules"], ["references/spatial-integration.md"])
            packet = P.packet(root, "3d-modeler", ["contracts/metrics.json"], None)
            self.assertIn("Blender", json.dumps(packet["stop_conditions"]))
            router = P.routing_helper()
            self.assertIn("3d-modeler", router.STAGE_ROLES["app"])
            self.assertNotIn("3d-modeler", router.STAGE_ROLES["dashboard"])
            spec = copy.deepcopy(intent); spec["requirements"][0]["surfaces"] = ["dashboard"]
            project = P.load_project(root)[1]; project["surfaces"] = ["dashboard"]
            with self.assertRaises(ValueError): P.intent_helper().validate(spec, project)


if __name__ == "__main__":
    unittest.main()
