"""Source checks for the file-free Cursor Agent entry and its shared references."""
import importlib.util
from pathlib import Path
import tempfile
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RULE = ROOT / ".cursor/rules/omni-artifact-entry.mdc"


class CursorEntryTests(unittest.TestCase):
    def test_entry_applies_without_a_matching_file_or_rule_mention(self):
        lines = RULE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "---")
        frontmatter = lines[1:lines.index("---", 1)]
        self.assertEqual([line for line in frontmatter if line.startswith("alwaysApply:")],
                         ["alwaysApply: true"])

    def test_repo_snapshot_pins_the_shipped_rule_and_ignores_personal_settings(self):
        script = ROOT / 'skills/omni-artifact-accelerator/scripts/delivery_workflow.py'
        spec = importlib.util.spec_from_file_location('cursor_snapshot_workflow', script)
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        with tempfile.TemporaryDirectory() as temp:
            checkout = Path(temp).resolve()
            (checkout / 'package.json').write_text('{}')
            (checkout / 'skills').mkdir()
            relative = RULE.relative_to(ROOT)
            rule = checkout / relative
            rule.parent.mkdir(parents=True)
            rule.write_bytes(RULE.read_bytes())
            original = workflow.source_manifest(checkout)
            self.assertIn(relative.as_posix(), original)
            (checkout / '.cursor/local.json').write_text('{}')
            self.assertEqual(original, workflow.source_manifest(checkout))
            rule.write_bytes(rule.read_bytes() + b'\n')
            self.assertNotEqual(original, workflow.source_manifest(checkout))

    def test_entry_points_to_the_shared_checkout_guidance(self):
        references = set(re.findall(r"`@([^`]+)`", RULE.read_text(encoding="utf-8")))
        expected = {
            "AGENTS.md",
            "skills/omni-artifact-accelerator/SKILL.md",
            "skills/omni-artifact-accelerator/references/work-intent.md",
            "skills/omni-domo-migrator/SKILL.md",
        }
        self.assertTrue(expected.issubset(references), expected - references)
        for path in references:
            with self.subTest(path=path):
                target = (ROOT / path).resolve(strict=True)
                self.assertIn(ROOT, target.parents)
                self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
