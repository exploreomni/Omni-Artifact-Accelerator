"""Hex structure + maintained DMA producer composition with original bytes."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


p = load("hex_fixture_for_bridge", ROOT / "tests/test_hex_capture.py")
b, c, t = p.V, p.C, p.module("translate_artifact")


def reseal(value):
    value["content_hash"] = b.sha(
        {k: v for k, v in value.items() if k != "content_hash"}
    )
    return value


def produce_dma(generic=True, missing_ids=False):
    code = """import json,socket,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'skills/data-model-accelerator/scripts'))
def denied(*a,**k):raise AssertionError('network forbidden')
socket.socket.connect=denied
folder=root/'skills/data-model-accelerator/examples/hex-omni-e2e/input/repo'
if sys.argv[2]=='generic':
 from source_adapters.registry import parse
 files={p.relative_to(folder).as_posix():p.read_text() for p in folder.rglob('*') if p.is_file()}
 if sys.argv[3]=='missing':
  import yaml
  native=yaml.safe_load(files['revenue.hex.yaml']);native['meta'].pop('projectId');native['cells'][0].pop('cellId');files['revenue.hex.yaml']=json.dumps(native)
 result=parse('hex',files)
else:
 import hex_source
 result=hex_source.inspect_repo(folder)
print(json.dumps(result))
"""
    result = subprocess.run(
        [
            os.environ.get("OMNI_ANALYST_DMA_PYTHON", sys.executable),
            "-B",
            "-c",
            code,
            os.environ["OMNI_ANALYST_DMA_CHECKOUT"],
            "generic" if generic else "legacy",
            "missing" if missing_ids else "normal",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


class HexVisualBridge(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.result = p.capture_fixture(self.root / "capture")
        self.value = self.result["capture"]

    def parse(self, value=None):
        return t.translate(json.dumps(value or self.value).encode(), "hex-capture")

    def test_independent_tabs_placements_controls_actions_generated_inventory(self):
        result = self.parse()
        assets = result["assets"]
        self.assertEqual(len([a for a in assets if a["kind"] == "page"]), 7)
        self.assertEqual(len([a for a in assets if a["kind"] == "placement"]), 29)
        self.assertEqual(len([a for a in assets if a["kind"] == "control"]), 3)
        self.assertEqual(len([a for a in assets if a["kind"] == "action"]), 2)
        self.assertEqual(
            len([a for a in assets if a["source_identity"].get("query_visual")]), 8
        )
        self.assertTrue(
            all(
                not a["source_identity"].get("query_visual")
                for a in assets
                if a["source_identity"].get("cell_id") in (p.INPUT, p.CODE, p.NOTE)
            )
        )
        self.assertTrue(
            any(
                a["source_identity"].get("generated_interface_unobserved")
                for a in assets
            )
        )
        self.assertTrue(
            any(
                g["code"] == "hex.component_missing_or_version_mismatch"
                for g in result["gaps"]
            )
        )
        self.assertEqual(result["upstream_payload"], self.value)
        self.assertFalse(result["hex_coverage"]["denominator_authenticated"])
        self.assertEqual(result["source"]["format"], "supplied_hex_visual_capture")
        b.verify_capture_files(self.value, self.root / "capture")

    def test_expected_missing_and_unsupported_do_not_disappear(self):
        r = p.request()
        r["expected_manifest"] = {
            "reference": "fixture-independent-observer",
            "completeness": "selected_scope",
            "objects": [
                {
                    "object_id": "inventory.hex.yaml#/conditional-screen",
                    "kind": "visual",
                }
            ],
        }
        capture = p.capture_fixture(self.root / "missing", r)["capture"]
        result = self.parse(capture)
        a = next(
            a
            for a in result["assets"]
            if a["source_path"].endswith("conditional-screen")
        )
        self.assertEqual(a["kind"], "unknown")
        self.assertTrue(a["source_identity"]["query_visual"])
        self.assertEqual(
            result["hex_coverage"]["missing_expected"],
            ["inventory.hex.yaml#/conditional-screen"],
        )

    def test_resealed_identity_and_actual_file_tampering_reject(self):
        value = copy.deepcopy(self.value)
        value["source"]["projects"][0]["source_version_id"] = p.P
        with self.assertRaisesRegex(ValueError, "project_identity"):
            self.parse(reseal(value))
        path = (
            self.root / "capture" / self.value["source"]["definition_files"][0]["path"]
        )
        path.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            b.verify_capture_files(self.value, self.root / "capture")

    def test_resealed_api_run_receipt_and_incomplete_operations_reject(self):
        value = p.capture_fixture(self.root / "rest", rest=True)["capture"]
        changed = copy.deepcopy(value)
        changed["operations"] = []
        with self.assertRaisesRegex(ValueError, "operations_required"):
            self.parse(reseal(changed))
        value["source"]["runs"]["inventory-chart"]["startTime"] = "different"
        with self.assertRaisesRegex(ValueError, "run_response_mismatch"):
            b.verify_capture_files(reseal(value), self.root / "rest")

    def test_normalization_exact_decimal_null_and_binding(self):
        raw = b"site,amount\nWest,12345678901234567890.123456789\nEast,NULL\n"
        profile = {
            "schema_version": 1,
            "format": "csv",
            "encoding": "utf-8",
            "headers": ["site", "amount"],
            "subtotal_policy": "preserve",
            "columns": [
                {
                    "ordinal": 0,
                    "name": "site",
                    "type": "string",
                    "nullable": False,
                    "null_tokens": [],
                },
                {
                    "ordinal": 1,
                    "name": "amount",
                    "type": "number",
                    "nullable": True,
                    "null_tokens": ["NULL"],
                    "decimal_separator": ".",
                    "group_separator": None,
                    "percent": False,
                },
            ],
        }
        binding = {
            "capture_content_hash": self.value["content_hash"],
            "project_id": p.P,
            "source_version_id": p.VERSION,
            "cell_id": p.CELL,
            "output_id": "inventory-chart",
            "state_sha256": b.sha(self.value["request"]["state"]),
            "attachment_sha256": b.sha(raw),
        }
        result = b.normalize_results(raw, profile, binding)
        self.assertEqual(result["rows"][0]["amount"], "12345678901234567890.123456789")
        self.assertIsNone(result["rows"][1]["amount"])
        binding["cell_id"] = None
        with self.assertRaisesRegex(ValueError, "normalization_binding"):
            b.normalize_results(raw, profile, binding)

    @unittest.skipUnless(
        os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"),
        "requires explicit trusted DMA checkout",
    )
    def test_actual_dma_generic_and_native_contradiction(self):
        result = produce_dma()
        inventory = t.translate(
            json.dumps(result).encode(), "hex-adapter", b.DMA_REVISION
        )
        self.assertEqual(
            len([a for a in inventory["assets"] if a["kind"] == "page"]), 4
        )
        self.assertGreater(len(inventory["assets"]), len(result["objects"]))
        self.assertTrue(
            any(d["kind"] == "dma_candidate" for d in inventory["dependencies"])
        )
        self.assertEqual(inventory["upstream_payload"], result)
        self.assertTrue(
            all(
                not a["source_identity"]["query_visual"]
                for a in inventory["assets"]
                if a["source_identity"].get("cell_type") == "INPUT"
            )
        )
        changed = copy.deepcopy(result)
        obj = next(o for o in changed["objects"] if o["kind"] == "hex_cell")
        obj["native_id"] = p.CELL
        with self.assertRaisesRegex(ValueError, "dma_cell_contradiction"):
            t.translate(json.dumps(changed).encode(), "hex-adapter", b.DMA_REVISION)

    @unittest.skipUnless(
        os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"),
        "requires explicit trusted DMA checkout",
    )
    def test_actual_dma_missing_ids_stay_unbound(self):
        result = produce_dma(missing_ids=True)
        inventory = t.translate(
            json.dumps(result).encode(), "hex-adapter", b.DMA_REVISION
        )
        cell = next(
            a
            for a in inventory["assets"]
            if a["source_path"] == "revenue.hex.yaml#/cells/0"
        )
        self.assertIsNone(cell["source_identity"]["project_id"])
        self.assertIsNone(cell["source_identity"]["cell_id"])
        self.assertFalse(cell["source_identity"]["query_visual"])
        self.assertTrue(
            any(
                g["code"] == "hex.native_project_or_version_identity_missing"
                for g in inventory["gaps"]
            )
        )

    @unittest.skipUnless(
        os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"),
        "requires explicit trusted DMA checkout",
    )
    def test_actual_dma_legacy_inputs_not_numeric_and_capture_enrichment(self):
        legacy = produce_dma(False)
        inventory = t.translate(
            json.dumps(legacy).encode(), "dma-inventory", b.DMA_REVISION
        )
        inputs = [
            a
            for a in inventory["assets"]
            if a["source_identity"].get("cell_type") == "INPUT"
        ]
        self.assertEqual(len(inputs), 13)
        self.assertTrue(all(not a["source_identity"]["query_visual"] for a in inputs))
        source = (
            Path(os.environ["OMNI_ANALYST_DMA_CHECKOUT"])
            / "skills/data-model-accelerator/examples/hex-omni-e2e/input/repo"
        )
        r = p.request()
        r["outputs"] = []
        r["exports"] = [
            {
                "project_id": None,
                "expected_source_version_id": None,
                "version": "draft",
                "source_path": f.name,
            }
            for f in sorted(source.glob("*.hex.yaml"))
        ]
        capture = c.import_local(r, source, self.root / "dma", allow_source_read=True)[
            "capture"
        ]
        capture["source"].update(
            semantic_inventory=legacy,
            semantic_inventory_sha256=b.sha(legacy),
            dma_producer_revision=b.DMA_REVISION,
        )
        projected = self.parse(reseal(capture))
        self.assertTrue(
            any(g["code"] == "hex.dma_upstream_gap" for g in projected["gaps"])
        )


if __name__ == "__main__":
    unittest.main()
