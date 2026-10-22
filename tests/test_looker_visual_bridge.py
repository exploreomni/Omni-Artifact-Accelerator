"""Actual maintained Looker acquisition and DMA producers; no tenant calls."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/omni-artifact-translator/scripts"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


b = module("looker_bridge", SCRIPTS / "looker_visual.py")
t = module("looker_translation", SCRIPTS / "translate_artifact.py")
p = module("looker_producer_fixture", ROOT / "tests/test_looker_capture.py")
c = p.C
# Independent denominator authored from source contract, not projected output.
EXPECTED = [("", "dashboard"), *[("/dashboard_elements/" + str(i), "content" if i == 3 else "visual") for i in range(5)],
    ("/dashboard_filters/0", "control"), ("/dashboard_layouts/0", "layout"),
    ("/tabs/0", "page"), ("/tabs/1", "page"),
    ("/dashboard_layouts/0/dashboard_layout_components/0", "placement"),
    ("/dashboard_layouts/0/dashboard_layout_components/1", "placement"),
    ("/source/dependencies/0/payload/query", "definition"), ("/source/dependencies/2/payload", "definition"),
    ("/source/dependencies/3/payload", "definition"), ("/source/dependencies/5/payload", "definition"),
    ("/source/dependencies/0/payload", "definition"), ("/merged_dependencies/merge-1", "definition")]


def dashboard():
    return p.dashboard()


def request():
    value = p.request()
    value["expected_manifest"]["objects"] = [{"object_id": loc or "/", "kind": kind} for loc, kind in EXPECTED]
    return value


def capture_fixture(directory, supplied_request=None):
    with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
        result = c.capture(supplied_request or request(), directory, token=p.TOKEN, transport=p.Transport(),
            allow_source_read=True, allow_source_query=True, now=p.NOW)
    result["inventory"] = t.translate(Path(result["output"]).read_bytes(), "looker-capture")
    return result


def reseal(value):
    value["request_sha256"] = b.sha(value["request"])
    value["content_hash"] = b.sha({k: v for k, v in value.items() if k != "content_hash"})
    return value


def produce_dma(payload, generic=False, files=None):
    checkout = Path(os.environ["OMNI_ANALYST_DMA_CHECKOUT"]).resolve()
    code = '''import json,socket,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'skills/data-model-accelerator/scripts'))
def denied(*a,**k): raise AssertionError('network forbidden')
socket.socket.connect=denied
value=json.loads(sys.stdin.read())
if sys.argv[2]=='generic':
 from source_adapters.registry import parse
 result=parse('looker',value)
else:
 import looker_source
 result=looker_source.parse_dashboard(json.dumps(value,ensure_ascii=False).encode())
print(json.dumps(result))
'''
    supplied = files if files is not None else {"dashboard.json": json.dumps(payload, ensure_ascii=False)} if generic else payload
    result = subprocess.run([os.environ.get("OMNI_ANALYST_DMA_PYTHON", sys.executable), "-c", code,
        str(checkout), "generic" if generic else "canonical"], input=json.dumps(supplied), text=True,
        capture_output=True, check=True)
    return json.loads(result.stdout)


class LookerVisualBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.result = capture_fixture(self.root / "capture")
        self.value = self.result["capture"]

    def parse(self, value):
        return t.translate(json.dumps(value).encode(), "looker-capture")

    def test_actual_rest_producer_complete_denominator_and_exact_original(self):
        inventory = self.result["inventory"]
        self.assertEqual(self.value["status"], "complete")
        self.assertEqual(inventory["source"]["projection_version"], "1.2.0")
        self.assertEqual({(a["source_path"], a["kind"]) for a in inventory["assets"]}, set(EXPECTED))
        self.assertEqual(inventory["upstream_payload"], self.value)
        self.assertEqual(len([a for a in inventory["assets"] if a["kind"] == "placement"]), 2)
        self.assertEqual(next(a for a in inventory["assets"] if a["source_id"] == "tile-note")["kind"], "content")
        self.assertTrue(all(a["source_identity"]["element_id"] == "tile-kpi" for a in inventory["assets"] if a["kind"] == "placement"))
        self.assertEqual(b.verify_capture_files(self.value, self.root / "capture")["status"], "verified_local_bytes")
        self.assertEqual(inventory["native_validation"], "not_run")

    def test_wrong_query_dashboard_and_resealed_attachment_hash_reject(self):
        for mutation, code in ((lambda x: x["attachments"][-1].update(query_id="q-table"), "attachment_query"),
                (lambda x: x["source"]["identity"].update(dashboard_id="other"), "identity_mismatch"),
                (lambda x: x["attachments"][-1].update(query_fingerprint="0" * 64), "attachment_query")):
            value = copy.deepcopy(self.value)
            mutation(value)
            reseal(value)
            with self.assertRaisesRegex(ValueError, code):
                self.parse(value)

    def test_changed_raw_bytes_and_symlink_reject(self):
        attachment = self.value["attachments"][-1]
        path = self.root / "capture" / attachment["path"]
        path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "actual_file_mismatch"):
            b.verify_capture_files(self.value, self.root / "capture")
        path.unlink()
        target = self.root / "outside"
        target.write_bytes(b"{}")
        path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            b.verify_capture_files(self.value, self.root / "capture")

    def test_missing_expected_object_remains_obligation(self):
        value = copy.deepcopy(self.value)
        value["request"]["expected_manifest"]["objects"].append({"object_id": "/missing-page", "kind": "page"})
        value["request_sha256"] = b.sha(value["request"])
        for a in value["attachments"]:
            a["request_sha256"] = value["request_sha256"]
        result = self.parse(reseal(value))
        self.assertIn("/missing-page", result["looker_coverage"]["missing_expected"])
        self.assertTrue(any(a["kind"] == "unknown" and a["source_payload"].get("missing_from_capture") for a in result["assets"]))

    def test_legacy_api_content_actions_and_nonquery_placement(self):
        value = dashboard()
        value["dashboard_elements"][3]["links"] = [{"url": "https://example.invalid/action"}]
        value["dashboard_layouts"][0]["dashboard_layout_components"].append({"id": "note-placement", "dashboard_element_id": "tile-note"})
        result = t.translate(json.dumps(value).encode(), "looker-api")
        self.assertEqual(next(a for a in result["assets"] if a["source_id"] == "tile-note")["kind"], "content")
        self.assertFalse(next(a for a in result["assets"] if a["source_id"] == "note-placement")["source_identity"]["query_visual"])
        self.assertTrue(any(a["kind"] == "action" for a in result["assets"]))

    def test_supplied_yaml_original_names_geometry_controls_and_unsupported(self):
        request_value = request()
        request_value.update(source_instance=None, dashboard_id=None, views=[], renders=[], queries=[])
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp).resolve()
            yaml = b'- dashboard: inventory\n  title: Inventory\n  elements:\n  - name: chart\n    model: inventory\n    explore: stock\n    fields: [stock.available]\n    row: 0\n    col: 0\n    width: 12\n    height: 4\n    listen: {Site: stock.site}\n  - name: text\n    type: text\n    body_text: Inert\n  filters:\n  - name: Site\n    default_value: West\n  extends: [unresolved]\n'
            (src / "inventory.dashboard.lookml").write_bytes(yaml)
            result = c.import_local(request_value, src, self.root / "yaml", allow_source_read=True)
        projected = self.parse(result["capture"])
        self.assertEqual([(a["kind"], a["source_id"]) for a in projected["assets"] if a["kind"] != "unknown"],
                         [("dashboard", "inventory"), ("visual", "chart"), ("placement", None), ("content", "text"), ("control", "Site")])
        self.assertEqual(result["capture"]["source"]["supplied_files"][0]["content_utf8"].encode(), yaml)
        self.assertIn("looker.lookml_effective_inheritance_liquid_access_unresolved", {g["code"] for g in projected["gaps"]})

    def test_yaml_alias_duplicate_tags_and_depth_are_rejected(self):
        for raw in (b'- dashboard: a\n  dashboard: b', b'- dashboard: a\n  x: &a [1]\n  y: *a',
                    b'- dashboard: a\n  x: !!python/object:evil {}', b'- dashboard: a\n  x: ' + b'[' * 40 + b'0' + b']' * 40):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                b.safe_yaml(raw)

    def test_declared_tab_layout_and_effective_query_contradictions_reject(self):
        for field, wrong in (("tab_id", "not-a-tab"), ("layout_id", "not-a-layout")):
            value = copy.deepcopy(self.value)
            value["request"]["views"][0][field] = wrong
            value["request_sha256"] = b.sha(value["request"])
            for attachment in value["attachments"]:
                attachment["request_sha256"] = value["request_sha256"]
            with self.assertRaisesRegex(ValueError, "view_.*_mismatch|selected_(tab|layout)_missing"):
                self.parse(reseal(value))
        value = copy.deepcopy(self.value)
        attachment = next(a for a in value["attachments"] if a.get("binding_id"))
        attachment["effective_query"]["fields"] = ["stock.other"]
        attachment["effective_query_sha256"] = b.sha(attachment["effective_query"])
        with self.assertRaisesRegex(ValueError, "saved_effective_query_mismatch"):
            self.parse(reseal(value))

    def test_effective_query_removal_and_principal_render_contradictions_reject(self):
        for change, code in ((lambda x: next(a for a in x["attachments"] if a.get("binding_id")).pop("effective_query"), "effective_query_required"),
                (lambda x: x["request"].update(expected_user_id="other-user"), "observed_user_mismatch"),
                (lambda x: next(a for a in x["attachments"] if a.get("render_id")).update(render_request_sha256="0" * 64), "render_request_hash"),
                (lambda x: next(a for a in x["attachments"] if a.get("render_id")).update(render_task_id="other-job"), "render_job_mismatch")):
            value = copy.deepcopy(self.value)
            change(value)
            value["request_sha256"] = b.sha(value["request"])
            for a in value["attachments"]:
                a["request_sha256"] = value["request_sha256"]
            with self.assertRaisesRegex(ValueError, code):
                self.parse(reseal(value))

    def test_truncated_result_cannot_be_resealed_as_complete(self):
        value = copy.deepcopy(self.value)
        attachment = next(a for a in value["attachments"] if a.get("binding_id"))
        raw = b'{"metadata":{"columns_truncated":true},"rows":[]}'
        (self.root / "capture" / attachment["path"]).write_bytes(raw)
        attachment.update(sha256=b.sha(raw), bytes=len(raw), result_completeness={"status": "complete", "reference": "claim", "flags": []})
        # A new derivative may pin new data, but cannot contradict the data's
        # explicit truncation flag. The operation response remains independently pinned.
        with self.assertRaisesRegex(ValueError, "result_quality_contradiction"):
            b.verify_capture_files(reseal(value), self.root / "capture")

    def test_early_budget_preserves_frozen_missing_denominator(self):
        supplied = request()
        supplied["max_requests_per_invocation"] = 1
        result = c.capture(supplied, self.root / "early", token=p.TOKEN, transport=p.Transport(),
            allow_source_read=True, allow_source_query=True, now=p.NOW)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["capture"]["budget"]["requests"], 1)
        projected = self.parse(result["capture"])
        self.assertEqual(len(projected["assets"]), len(EXPECTED))
        self.assertTrue(all(a["kind"] == "unknown" for a in projected["assets"]))
        self.assertTrue(all(a["source_payload"]["missing_from_capture"] for a in projected["assets"]))
        b.verify_capture_files(result["capture"], self.root / "early")

    def test_wrong_producer_revision_rejects_before_contract_import(self):
        with self.assertRaisesRegex(ValueError, "producer_revision"):
            t.translate(b'{"kind":"canonical_dashboard"}', "looker-canonical", "0" * 40)
        with self.assertRaisesRegex(ValueError, "producer_revision"):
            t.translate(b'{"kind":"source_adapter_result"}', "looker-adapter", "0" * 40)

    @unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "trusted DMA checkout optional")
    def test_actual_dma_canonical_and_generic_not_kind_spoof(self):
        original = dashboard()
        original["title"] = "Inventário"
        canonical = produce_dma(original)
        result = t.translate(json.dumps(canonical).encode(), "looker-canonical", t.DMA_REVISION)
        self.assertEqual(result["upstream_payload"], canonical)
        self.assertEqual(len([a for a in result["assets"] if a["kind"] == "placement"]), 2)
        generic = produce_dma(original, generic=True, files={"dashboard.json": json.dumps(original),
            "model.model.lkml": 'connection: "warehouse"\ninclude: "*.view.lkml"\nexplore: stock {}',
            "dashboard.dashboard.lookml": '- dashboard: unsupported\n  elements: []'})
        result = t.translate(json.dumps(generic).encode(), "looker-adapter", t.DMA_REVISION)
        self.assertEqual(result["upstream_payload"], generic)
        self.assertTrue(any(a["kind"] == "content" for a in result["assets"]))
        self.assertTrue(any(a["kind"] == "unknown" and a["source_id"] == "dashboard.dashboard.lookml" for a in result["assets"]))
        with self.assertRaises(ValueError):
            t.translate(json.dumps(generic).encode(), "looker-canonical", t.DMA_REVISION)
        canonical["tiles"].pop()
        with self.assertRaisesRegex(ValueError, "denominator"):
            t.translate(json.dumps(canonical).encode(), "looker-canonical", t.DMA_REVISION)


if __name__ == "__main__":
    unittest.main()
