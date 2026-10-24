"""Verify public activation/job denial without compiling models or installing."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DenialTests(unittest.TestCase):
    def test_model_request_is_bound_and_cannot_authorize_execution(self):
        launcher = load("blocked_launcher", "harness/launcher.py")
        request = launcher.prepare(ROOT / "harness/fixtures/inspection-assembly.json")
        self.assertEqual(request["authorization"], "not_granted")
        self.assertFalse(launcher.capabilities()["execute"])
        self.assertFalse(launcher.capabilities()["promote"])
        with self.assertRaises(PermissionError):
            launcher.execute({**request, "approved": True}, approved=True, host_fallback=True)

    def test_public_installer_rejects_before_creating_destination(self):
        installer = load("blocked_installer", "scripts/install_skills.py")
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder).resolve() / "skills"
            with self.assertRaisesRegex(ValueError, "host|approval|disabled"):
                installer.install(destination, apply=True, source=ROOT)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
