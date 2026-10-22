"""Power BI bridge tests against actual source producers, never a tenant."""
import base64
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
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


t = module("powerbi_translator_test", SCRIPTS / "translate_artifact.py")
b = module("powerbi_bridge_test", SCRIPTS / "powerbi_visual.py")
c = module("powerbi_capture_test", SCRIPTS / "powerbi_capture.py")
REPORT = "11111111-1111-1111-1111-111111111111"
WORKSPACE = "22222222-2222-2222-2222-222222222222"
DATASET = "33333333-3333-3333-3333-333333333333"
PREFIX = "Report.Report/definition/"


def visual_path(name, page="Main"):
    return PREFIX + "pages/" + page + "/visuals/" + name + "/visual.json"


def visual(name, visual_type="clusteredColumnChart", **extra):
    return {"name": name, "position": {"x": 0, "y": 0, "width": 300, "height": 200, "z": 1},
            "visual": {"visualType": visual_type, "query": {"queryState": {"Category": {"projections": [
                {"queryRef": "Sales.Region", "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "Region"}}}]},
                "Y": {"projections": [{"queryRef": "Sales.Revenue", "field": {"Measure": {
                    "Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": "Revenue"}}}]}}}}, **extra}


def definitions():
    # Synthetic modern PBIR layout. Deliberately no model.bim; DAX is inert.
    values = {
        "Report.pbip": {"version": "1.0", "artifacts": [{"report": {"path": "Report.Report"}}]},
        "Report.Report/definition.pbir": {"version": "4.0", "datasetReference": {"byPath": {"path": "../Model.SemanticModel"}}},
        PREFIX + "report.json": {"themeCollection": {"customTheme": {"name": "Brand"}}, "filterConfig": {"filters": []}},
        PREFIX + "pages/pages.json": {"pageOrder": ["Main", "Hidden"]},
        PREFIX + "pages/Main/page.json": {"name": "Main", "displayName": "Sales", "width": 1280, "height": 720,
            "visualInteractions": [{"source": "Slicer", "target": "A", "type": "DataFilter"}], "mobileLayout": {"order": ["A", "B"]}},
        PREFIX + "pages/Hidden/page.json": {"name": "Hidden", "displayName": "Sales", "visibility": "Hidden"},
        visual_path("A"): visual("A", parentGroupName="Group", isHidden=True, unsupportedProperty={"retained": True}),
        visual_path("B"): visual("B", "lineChart"),
        visual_path("Slicer"): visual("Slicer", "slicer"),
        visual_path("Group"): {"name": "Group", "visualGroup": {"displayName": "KPIs"}},
        visual_path("C", "Hidden"): visual("C", "card"),
        PREFIX + "bookmarks/bookmarks.json": {"items": [{"name": "Saved", "state": {"sections": {"Main": {}}}}]},
        "Report.Report/StaticResources/RegisteredResources/BrandTheme.json": {"name": "Brand", "dataColors": ["#123456"]},
    }
    output = {path: json.dumps(value, ensure_ascii=False).encode() for path, value in values.items()}
    output["Model.SemanticModel/definition/tables/Sales.tmdl"] = b"table Sales\n\tcolumn Region\n\t\tdataType: string\n\tmeasure Revenue = SUM(Sales[Amount])\n"
    output["Report.Report/StaticResources/RegisteredResources/logo.svg"] = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    return output


EXPECTED = [("Report.pbip#/", "definition"), ("Report.Report/definition.pbir#/", "definition"),
    (PREFIX + "report.json#/", "dashboard"), (PREFIX + "report.json#/filterConfig", "filter"),
    (PREFIX + "pages/pages.json#/", "definition"), (PREFIX + "pages/Main/page.json#/", "page"),
    (PREFIX + "pages/Main/page.json#/visualInteractions", "action"), (PREFIX + "pages/Main/page.json#/mobileLayout", "device_layout"),
    (PREFIX + "pages/Hidden/page.json#/", "page"), (visual_path("A") + "#/", "visual"),
    (visual_path("B") + "#/", "visual"), (visual_path("Slicer") + "#/", "visual"),
    (visual_path("Slicer") + "#/visual", "control"), (visual_path("Group") + "#/", "layout"),
    (visual_path("C", "Hidden") + "#/", "visual"), (PREFIX + "bookmarks/bookmarks.json#/", "action"),
    ("Report.Report/StaticResources/RegisteredResources/BrandTheme.json#/", "definition"),
    ("Model.SemanticModel/definition/tables/Sales.tmdl#/", "definition"),
    ("Report.Report/StaticResources/RegisteredResources/logo.svg#/", "content")]


def request():
    return {"schema_version": "powerbi-visual-capture-request.v1", "capture_id": "synthetic-pbir",
        "workspace_id": WORKSPACE, "report_id": REPORT, "dataset_id": DATASET,
        "principal_ref": "synthetic-viewer", "authorization_ref": "synthetic-offline-only", "evidence_mode": "synthetic_fixture",
        "route": "unselected", "route_reference": None,
        "views": [{"page_id": "Main", "visual_id": None, "export_png": False},
                  {"page_id": "Main", "visual_id": "A", "export_png": False}],
        "state": {"state_id": "default", "filters": [], "bookmark": None, "locale": "en-US", "timezone": "UTC",
                  "principal": "synthetic-viewer", "data_time_policy": "fixed synthetic fixture"},
        "queries": [{"query_id": "q1", "query": "EVALUATE ROW(\"Value\", 0)", "page_id": "Main", "visual_id": "A",
                     "context_reference": "synthetic query definition"}],
        "expected_manifest": {"reference": "independently-authored-synthetic-manifest", "completeness": "selected_report",
                              "objects": [{"object_id": oid, "kind": kind} for oid, kind in EXPECTED]}}


def reseal(value):
    value["request_sha256"] = b.sha(value["request"])
    for attachment in value["attachments"]:
        attachment["request_sha256"] = value["request_sha256"]
    value["content_hash"] = b.sha({k: v for k, v in value.items() if k != "content_hash"})
    return value


def capture_fixture(directory, files=None, supplied_request=None):
    files = definitions() if files is None else files
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp).resolve()
        for path, raw in files.items():
            target = source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
            result = c.import_local(supplied_request or request(), source, directory, allow_source_read=True)
    result["inventory"] = t.translate(Path(result["output"]).read_bytes(), "powerbi-capture")
    return result


def produce_dma(files, generic=True):
    checkout = Path(os.environ["OMNI_ANALYST_DMA_CHECKOUT"]).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp).resolve()
        for name, raw in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        code = '''import json, socket, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'skills/data-model-accelerator/scripts'))
def denied(*a, **k): raise AssertionError('network forbidden')
socket.socket.connect = denied
root=Path(sys.argv[2])
if sys.argv[3]=='generic':
    from source_adapters.registry import parse
    files={p.relative_to(root).as_posix():p.read_text() for p in root.rglob('*') if p.is_file()}
    result=parse('powerbi',files)
else:
    import powerbi_source
    result=powerbi_source.inspect_repo(root)
print(json.dumps(result))
'''
        completed = subprocess.run([os.environ.get("OMNI_ANALYST_DMA_PYTHON", sys.executable), "-c", code,
            str(checkout), str(folder), "generic" if generic else "legacy"], text=True, capture_output=True, check=True)
    return json.loads(completed.stdout)


class PowerBIVisualBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name).resolve()
        self.result = capture_fixture(self.folder / "capture")
        self.value = self.result["capture"]

    def parse(self, value):
        return t.translate(json.dumps(value).encode(), "powerbi-capture")

    def test_actual_import_producer_preserves_all_query_visuals_without_model_bim(self):
        inventory = self.result["inventory"]
        self.assertEqual({(a["source_path"], a["kind"]) for a in inventory["assets"]}, set(EXPECTED))
        visuals = [a for a in inventory["assets"] if a["kind"] == "visual"]
        self.assertEqual({a["source_id"] for a in visuals}, {"A", "B", "C", "Slicer"})
        self.assertTrue(all(a["source_identity"]["query_visual"] for a in visuals))
        a = next(a for a in visuals if a["source_id"] == "A")
        self.assertEqual(a["source_payload"]["query_roles"], ["Category", "Y"])
        self.assertEqual(a["source_payload"]["native"]["unsupportedProperty"], {"retained": True})
        self.assertTrue(a["facets"]["layout"]["value"]["isHidden"])
        self.assertEqual(inventory["powerbi_coverage"]["definition_coverage"], "reconciled_supplied_manifest")
        self.assertEqual(b.verify_capture_files(self.value, self.folder / "capture")["status"], "verified_local_bytes")
        self.assertEqual(inventory["upstream_payload"], self.value)
        self.assertEqual(inventory["migration_context"]["route"], None)

    def test_actual_fabric_definition_producer_same_structure(self):
        payload = {"definition": {"parts": [{"path": name, "payload": base64.b64encode(raw).decode(), "payloadType": "InlineBase64"}
                                             for name, raw in definitions().items()]}}
        result = c.import_fabric_definition(request(), payload, self.folder / "fabric", allow_source_read=True)
        inventory = self.parse(result["capture"])
        self.assertEqual({(a["source_path"], a["kind"]) for a in inventory["assets"]}, set(EXPECTED))
        self.assertEqual(result["capture"]["source"]["definition_fingerprint"], self.value["source"]["definition_fingerprint"])

    def test_actual_rest_producer_keeps_cross_page_names_and_unknown_state(self):
        producer = module("powerbi_actual_capture_fixture", ROOT / "tests/test_powerbi_capture.py")
        transport = producer.Transport()
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
            result = producer.C.capture(producer.request(), self.folder / "rest",
                fabric_token="fabric-synthetic-token", powerbi_token="powerbi-synthetic-token",
                transport=transport, allow_source_read=True, allow_source_query=True, now=producer.NOW)
        capture = result["capture"]
        b.verify_capture_files(capture, Path(result["output"]).parent)
        inventory = self.parse(capture)
        visuals = [a for a in inventory["assets"] if a["kind"] == "visual"]
        self.assertEqual({(a["source_identity"]["page_id"], a["source_identity"]["visual_id"]) for a in visuals}, {
            ("ReportSectionOps", "available_by_site"), ("ReportSectionOps", "site_selector"),
            ("ReportSectionDetail", "available_by_site")})
        self.assertEqual(len({a["asset_key"] for a in visuals}), 3)
        self.assertEqual(inventory["upstream_payload"], capture)
        self.assertEqual(capture["source"]["state_observation"]["status"], "unknown")
        query = next(a for a in capture["attachments"] if a.get("query_id"))
        self.assertEqual(query["result_completeness"]["status"], "unknown")
        changed = copy.deepcopy(capture)
        next(a for a in changed["attachments"] if a.get("query_id"))["query_id"] = "another-query"
        with self.assertRaisesRegex(ValueError, "attachment_query_mismatch"):
            b.validate_capture(reseal(changed))
        mutations = [(lambda v: v["request"]["queries"][0].update(query="EVALUATE ROW(\"Different\", 1)"), "query_hash_mismatch"),
            (lambda v: v["source"].update(definition_after_fingerprint="0" * 64), "complete_definition_drift"),
            (lambda v: v["source"]["identity"].update(report_id=REPORT), "source_identity_mismatch"),
            (lambda v: next(a for a in v["attachments"] if a.get("query_id")).update(dataset_id=DATASET), "attachment_dataset_mismatch")]
        for change, code in mutations:
            changed = copy.deepcopy(capture)
            change(changed)
            with self.assertRaisesRegex(ValueError, code):
                b.validate_capture(reseal(changed))

    def test_unsupported_query_shape_does_not_drop_visual_or_subsequent_files(self):
        files = definitions()
        first = json.loads(files[visual_path("A")])
        first["visual"]["query"]["queryState"] = None
        files[visual_path("A")] = json.dumps(first).encode()
        result = capture_fixture(self.folder / "unsupported", files)
        visuals = [a for a in result["inventory"]["assets"] if a["kind"] == "visual"]
        self.assertEqual({a["source_id"] for a in visuals}, {"A", "B", "C", "Slicer"})
        self.assertTrue(any(g["code"] == "powerbi.query_roles_uninterpreted" for g in result["inventory"]["gaps"]))

    def test_actual_query_raw_decimal_survives_capture_and_normalization(self):
        producer = module("powerbi_decimal_capture_fixture", ROOT / "tests/test_powerbi_capture.py")
        transport = producer.Transport()
        raw = b'{"results":[{"tables":[{"rows":[{"[Available]":12345678901234567890.123456789}]}]}]}'
        def precise(*args):
            if args[1].endswith("/executeQueries"):
                return 200, {"content-type": "application/json"}, raw
            return transport(*args)
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
            result = producer.C.capture(producer.request(), self.folder / "decimal",
                fabric_token="fabric-synthetic-token", powerbi_token="powerbi-synthetic-token", transport=precise,
                allow_source_read=True, allow_source_query=True, now=producer.NOW)
        capture = result["capture"]
        attachment = next(a for a in capture["attachments"] if a.get("query_id"))
        actual = (Path(result["output"]).parent / attachment["path"]).read_bytes()
        self.assertEqual(actual, raw)
        normalized = b.normalize_results(actual, {"schema_version": 1, "format": "json", "subtotal_policy": "preserve",
            "rows_pointer": "/results/0/tables/0/rows", "headers": ["[Available]"], "columns": [
                {"ordinal": 0, "name": "available", "type": "number", "nullable": False, "null_tokens": [],
                 "decimal_separator": ".", "group_separator": None, "percent": False}]},
            {"capture_content_hash": capture["content_hash"], "attachment_sha256": attachment["sha256"],
             **{k: attachment[k] for k in ("page_id", "visual_id", "state_sha256", "query_id")}})
        self.assertEqual(normalized["rows"], [{"available": "12345678901234567890.123456789"}])

    def test_page_scoped_query_is_retained_without_becoming_visual_evidence(self):
        selected = request()
        selected["queries"][0]["visual_id"] = None
        result = capture_fixture(self.folder / "page-query", supplied_request=selected)
        self.assertIsNone(result["inventory"]["upstream_payload"]["request"]["queries"][0]["visual_id"])
        self.assertEqual(len([a for a in result["inventory"]["assets"] if a["kind"] == "visual"]), 4)

    def test_nonquery_content_keeps_denominator_without_fake_numeric_obligations(self):
        files, selected = definitions(), request()
        expected = set(EXPECTED)
        for name, visual_type, expected_kind in (("Text", "textbox", "content"), ("Shape", "shape", "content"),
                ("Button", "actionButton", "content"), ("Image", "image", "content"), ("Custom", "unrecognizedCustom", "unknown")):
            path = visual_path(name)
            files[path] = json.dumps({"name": name, "visual": {"visualType": visual_type}}).encode()
            selected["expected_manifest"]["objects"].append({"object_id": path + "#/", "kind": expected_kind})
            expected.add((path + "#/", expected_kind))
        result = capture_fixture(self.folder / "content", files, selected)
        assets = result["inventory"]["assets"]
        self.assertEqual({(a["source_path"], a["kind"]) for a in assets}, expected)
        self.assertEqual(len([a for a in assets if a["kind"] == "visual"]), 4)
        with patch.object(sys, "path", [str(ROOT / "skills/omni-artifact-accelerator/scripts"), *sys.path]):
            workflow = module("powerbi_content_workflow", ROOT / "skills/omni-artifact-accelerator/scripts/visual_workflow.py")
        for asset in assets:
            if asset["source_id"] in ("Text", "Shape", "Button", "Image", "Custom"):
                self.assertFalse(any(c["lane"] == "numeric" for c in workflow.cases(asset)))
        query = json.loads(files[visual_path("Text")])
        query["visual"]["query"] = None
        files[visual_path("Text")] = json.dumps(query).encode()
        changed = capture_fixture(self.folder / "query-content", files)
        self.assertTrue(any(a["kind"] == "visual" and a["source_id"] == "Text" for a in changed["inventory"]["assets"]))

    def test_local_definition_identity_needs_no_invented_service_ids(self):
        selected = request()
        selected.update(workspace_id=None, report_id=None, dataset_id=None, queries=[])
        result = capture_fixture(self.folder / "local-only", supplied_request=selected)
        fingerprint = result["capture"]["source"]["definition_fingerprint"]
        for asset in result["inventory"]["assets"]:
            self.assertIsNone(asset["source_identity"]["report_id"])
            self.assertEqual(asset["source_identity"]["namespace"], "definition:" + fingerprint)
        wrong = copy.deepcopy(result["capture"])
        wrong["source"]["identity"]["namespace"] = "definition:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "definition_only_identity_required"):
            self.parse(reseal(wrong))

    def test_lost_expected_visual_stays_obligation(self):
        files = definitions()
        files.pop(visual_path("B"))
        result = capture_fixture(self.folder / "partial", files)
        inventory = result["inventory"]
        self.assertTrue(any(a["source_payload"].get("missing_from_definition") for a in inventory["assets"]))
        self.assertEqual(inventory["powerbi_coverage"]["missing_expected"], [visual_path("B") + "#/"])
        self.assertEqual(len([a for a in inventory["assets"] if a["kind"] == "visual"]), 3)

    def test_same_caption_does_not_collapse_pages_or_visuals(self):
        inventory = self.result["inventory"]
        pages = [a for a in inventory["assets"] if a["kind"] == "page"]
        self.assertEqual({a["source_id"] for a in pages}, {"Main", "Hidden"})
        self.assertEqual({a["source_payload"]["native"]["displayName"] for a in pages}, {"Sales"})

    def test_actual_bytes_and_embedded_hash_mismatch_reject(self):
        record = self.value["source"]["definition_files"][0]
        (self.folder / "capture" / record["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "actual_file_mismatch"):
            b.verify_capture_files(self.value, self.folder / "capture")
        value = copy.deepcopy(self.value)
        value["source"]["definition_files"][0]["content_utf8"] = "changed"
        with self.assertRaisesRegex(ValueError, "hash_or_size"):
            self.parse(reseal(value))

    def test_path_alias_and_wrong_requested_visual_reject(self):
        value = copy.deepcopy(self.value)
        value["source"]["definition_files"][0]["source_path"] = "../escaped.json"
        with self.assertRaises(ValueError):
            self.parse(reseal(value))
        value = copy.deepcopy(self.value)
        value["request"]["views"][1]["visual_id"] = "not-observed"
        with self.assertRaisesRegex(ValueError, "view_definition_mismatch"):
            self.parse(reseal(value))


@unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "optional trusted DMA runtime not selected")
class ActualDMAProfiles(unittest.TestCase):
    def test_generic_tmdl_result_is_not_spoofed_as_legacy_inventory(self):
        generic = produce_dma(definitions())
        self.assertEqual(generic["kind"], "source_adapter_result")
        self.assertTrue(any(o["kind"] == "measure" for o in generic["objects"]))
        result = t.translate(json.dumps(generic).encode(), "powerbi-adapter", t.DMA_REVISION)
        self.assertEqual(result["source"]["format"], "supplied_powerbi_source_adapter_result")
        self.assertEqual(result["upstream_payload"], generic)
        self.assertTrue(any(a["source_identity"]["adapter_kind"] == "measure" for a in result["assets"]))
        with self.assertRaisesRegex(ValueError, "unsupported_inventory"):
            t.translate(json.dumps(generic).encode(), "dma-inventory", t.DMA_REVISION)
        altered = copy.deepcopy(generic)
        altered["objects"][0]["evidence"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "evidence_mismatch"):
            t.translate(json.dumps(altered).encode(), "powerbi-adapter", t.DMA_REVISION)

    def test_real_legacy_billing_inventory_preserved_and_unsupported_role_cannot_drop_visuals(self):
        checkout = Path(os.environ["OMNI_ANALYST_DMA_CHECKOUT"])
        root = checkout / "skills/data-model-accelerator/examples/powerbi-omni-e2e/input/repo"
        files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        legacy = produce_dma(files, generic=False)
        self.assertEqual(len(legacy["visuals"]), 3)
        imported = t.translate(json.dumps(legacy).encode(), "dma-inventory", t.DMA_REVISION)
        self.assertEqual(len([a for a in imported["assets"] if a["kind"] == "visual"]), 3)
        first = sorted(p for p in files if p.endswith("visual.json"))[0]
        changed = json.loads(files[first])
        changed["visual"]["query"]["queryState"]["Category"] = changed["visual"]["query"]["queryState"].pop("Values")
        files[first] = json.dumps(changed).encode()
        narrowed = produce_dma(files, generic=False)
        self.assertLess(len(narrowed["visuals"]), 3)
        with tempfile.TemporaryDirectory() as tmp:
            selected = request()
            selected["views"] = []
            selected["queries"] = []
            selected["expected_manifest"] = {"reference": "maintained-billing-source", "completeness": "partial", "objects": []}
            capture = capture_fixture(Path(tmp).resolve() / "capture", files, selected)
            visuals = [a for a in capture["inventory"]["assets"] if a["kind"] == "visual"]
            self.assertEqual(len(visuals), 3)
            value = capture["capture"]
            value["source"].update(semantic_inventory=narrowed, semantic_inventory_sha256=b.sha(narrowed))
            projected = t.translate(json.dumps(reseal(value)).encode(), "powerbi-capture")
            self.assertEqual(len([a for a in projected["assets"] if a["kind"] == "visual"]), 3)
            self.assertEqual(projected["upstream_payload"]["source"]["semantic_inventory"], narrowed)


if __name__ == "__main__":
    unittest.main()
