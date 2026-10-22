"""Synthetic visual structure plus real maintained DMA producer; no network."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/omni-artifact-translator/scripts"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


t = module("tableau_bridge_translator", SCRIPTS / "translate_artifact.py")
b = module("tableau_bridge_visual", SCRIPTS / "tableau_visual.py")
c = module("tableau_bridge_capture", SCRIPTS / "tableau_capture.py")
W = "/workbook[1]"
S = W + "/worksheets[1]/worksheet[1]"
D = W + "/dashboards[1]/dashboard[1]"
L = D + "/zones[1]/zone[1]"
P1 = L + "/zone[1]"
P2 = L + "/zone[2]"
DEVICE = D + "/devicelayouts[1]/devicelayout[1]"
MOBILE = DEVICE + "/zones[1]/zone[1]"

# Deliberately synthetic structural evidence, not an assertion Tableau opens it.
XML = b'''<workbook><repository-location id="native-book"/>
<worksheets><worksheet name="Revenue"><simple-id uuid="uuid-one"/><table/></worksheet></worksheets>
<dashboards><dashboard name="Overview"><zones><zone id="1" type-v2="layout-flow">
<zone id="2" name="Revenue" type-v2="viz"/><zone id="3" name="Revenue" type-v2="viz"/>
<zone id="4" type-v2="filter" field="[Region]"/><zone id="5" type-v2="text"><formatted-text>Read me</formatted-text></zone>
<zone id="6" type-v2="extension-widget"/></zone></zones>
<devicelayouts><devicelayout name="Phone"><zones><zone id="2" name="Revenue" type-v2="viz"/></zones></devicelayout></devicelayouts>
<actions><action name="Select"><source worksheet="Revenue"/><target worksheet="Unknown"/></action></actions>
</dashboard></dashboards></workbook>'''

EXPECTED = [(W, "workbook"), (S, "worksheet"), (D, "dashboard"), (L, "layout"),
            (P1, "placement"), (P2, "placement"), (L + "/zone[3]", "control"),
            (L + "/zone[4]", "content"), (L + "/zone[5]", "unknown"),
            (DEVICE, "device_layout"), (MOBILE, "placement"), (D + "/actions[1]/action[1]", "action")]

RICH_XML = XML.replace(b"<worksheets>", b'''<datasources><datasource name="Parameters"><column name="[Region]"
    datatype="string" param-domain-type="list" value="&quot;ALL&quot;"/></datasource></datasources><worksheets>''').replace(
    b'<table/>', b'<table><panes><pane><mark class="Bar"/></pane></panes></table>').replace(
    b'</worksheets>', b'''<worksheet name="Trend"><simple-id uuid="uuid-two"/><table><panes><pane><mark class="Line"/></pane></panes></table></worksheet>
    <worksheet name="KPI Table"><simple-id uuid="uuid-three"/><table><panes><pane><mark class="Text"/></pane></panes></table></worksheet></worksheets>''').replace(
    b'<zone id="6" type-v2="extension-widget"/>', b'''<zone id="6" type-v2="extension-widget"/>
    <zone id="7" name="Trend" type-v2="viz"/><zone id="8" name="KPI Table" type-v2="viz"/>
    <zone id="9" type-v2="paramctrl" param="[Region]"/>''')
RICH_SHEETS = [W + "/worksheets[1]/worksheet[" + str(i) + "]" for i in (1, 2, 3)]
RICH_EXPECTED = EXPECTED + [(RICH_SHEETS[1], "worksheet"), (RICH_SHEETS[2], "worksheet"),
    (W + "/datasources[1]/datasource[1]/column[1]", "parameter"),
    (L + "/zone[6]", "placement"), (L + "/zone[7]", "placement"), (L + "/zone[8]", "control")]


def png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\xff\xff")) + chunk(b"IEND", b""))


def request(xml=XML, expected=EXPECTED, sheets=None):
    sheets = sheets or [S]
    views = [{"view_id": "dashboard-1", "role": "dashboard", "worksheet_id": None}]
    views += [{"view_id": "sheet-" + str(i), "role": "worksheet", "worksheet_id": sheet}
              for i, sheet in enumerate(sheets)]
    mappings = [{"view_id": "dashboard-1", "object_id": D, "status": "matched", "evidence_reference": "synthetic-review:dashboard-id"}]
    mappings += [{"view_id": "sheet-" + str(i), "object_id": sheet, "status": "matched", "evidence_reference": "synthetic-review:uuid-" + str(i)}
                 for i, sheet in enumerate(sheets)]
    return {"schema_version": "tableau-visual-capture-request.v1", "capture_id": "synthetic-tableau",
            "origin": "https://tableau.invalid", "api_version": "3.29", "site_id": "site-1", "expected_user_id": "user-1",
            "workbook_id": "workbook-1", "dashboard_view_id": "dashboard-1", "dashboard_id": D,
            "principal_ref": "synthetic-viewer", "authorization_ref": "synthetic-offline-only", "evidence_mode": "synthetic_fixture",
            "views": views, "state": {"state_id": "default", "filters": {}, "parameters": {}, "locale": "en-US",
                                      "timezone": "UTC", "data_time_policy": "fixed synthetic rows"},
            "definition_sha256": b.sha(xml), "expected_manifest": {"schema_version": 1, "reference": "independent-synthetic-manifest",
                "completeness": "selected_dashboard", "objects": [{"object_id": k, "kind": v} for k, v in expected]},
            "identity_map": {"schema_version": 1, "mappings": mappings}}


class Source:
    def __init__(self, xml=XML, selected=None, csv=b"Team,Value\nA,10\nB,20\n"):
        self.xml, self.csv = xml, csv
        self.selected = selected or request(xml)
        self.calls = []

    def transport(self, url, token, maximum, timeout):
        self.calls.append(url)
        path = urlsplit(url).path
        if path.endswith("/sessions/current"):
            value = {"session": {"site": {"id": "site-1"}, "user": {"id": "user-1"}}}
        elif path.endswith("/workbooks/workbook-1/views"):
            value = {"views": {"view": [{"id": v["view_id"], "name": "Same caption"} for v in self.selected["views"]]}}
        elif path.endswith("/workbooks/workbook-1"):
            value = {"workbook": {"id": "workbook-1", "updatedAt": "2026-10-21T00:00:00Z"}}
        elif path.endswith("/content"):
            return 200, {"content-type": "application/xml"}, self.xml
        elif path.endswith("/image"):
            return 200, {"content-type": "image/png"}, png()
        elif path.endswith("/data"):
            return 200, {"content-type": "text/csv"}, self.csv
        else:
            raise AssertionError("Unexpected source operation")
        return 200, {"content-type": "application/json"}, json.dumps(value).encode()

    def capture(self, path):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")):
            result = c.capture_rest(self.selected, directory=path, session_token="synthetic-token", transport=self.transport,
                                    allow_source_read=True, allow_source_query=True)
        if result["status"] != "complete":
            raise AssertionError(result["capture"]["gaps"])
        return result


def reseal(value):
    value["request_sha256"] = b.sha(value["request"])
    for attachment in value["attachments"]:
        attachment["request_sha256"] = value["request_sha256"]
    value["content_hash"] = b.sha({k: v for k, v in value.items() if k != "content_hash"})
    return value


def capture_fixture(directory, dma_checkout=None, python=None, rich=False):
    """Small complete synthetic dashboard through actual source + optional DMA producers.

    Return {capture, output, inventory}; no sockets or customer pipelines. The
    enriched copy names its source journal instead of rewriting that journal.
    """
    directory = Path(directory).resolve()
    xml = RICH_XML if rich else XML
    selected = request(xml, RICH_EXPECTED, RICH_SHEETS) if rich else request()
    result = Source(xml, selected).capture(directory)
    if dma_checkout is not None:
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp)
            (source_dir / "synthetic.twb").write_bytes(xml)
            code = '''import json, socket, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "skills/data-model-accelerator/scripts"))
def denied(*a, **k): raise AssertionError("network forbidden")
socket.socket.connect = denied
import tableau_source
print(json.dumps(tableau_source.inspect_repo(sys.argv[2])))
'''
            produced = subprocess.run([python or sys.executable, "-c", code, str(dma_checkout), str(source_dir)],
                                      capture_output=True, text=True, check=True)
        value = copy.deepcopy(result["capture"])
        value["source"]["semantic_inventory"] = json.loads(produced.stdout)
        value["source"]["semantic_inventory_sha256"] = b.sha(value["source"]["semantic_inventory"])
        value["derivation"] = {"kind": "trusted_local_semantic_enrichment", "source_content_hash": result["capture"]["content_hash"],
                               "source_journal": Path(result["output"]).name}
        reseal(value)
        output = directory / "semantic-enriched.json"
        output.write_bytes(b.encoded(value))
        result = {**result, "capture": value, "output": str(output)}
    result["inventory"] = t.translate(Path(result["output"]).read_bytes(), "tableau-capture")
    return result


class TableauVisualBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.result = Source().capture(self.root / "capture")
        self.value = self.result["capture"]

    def parse(self, value=None):
        return t.translate(json.dumps(value or self.value).encode(), "tableau-capture")

    def test_actual_capture_producer_and_independent_denominator(self):
        report = b.verify_capture_files(self.value, self.root / "capture")
        self.assertEqual(report["status"], "verified_local_bytes")
        inventory = self.parse()
        self.assertEqual({(a["source_id"], a["kind"]) for a in inventory["assets"]}, set(EXPECTED))
        placements = [a for a in inventory["assets"] if a["kind"] == "placement"]
        self.assertEqual(len(placements), 3)
        self.assertEqual(len({a["asset_key"] for a in placements}), 3)
        self.assertEqual({a["source_identity"]["worksheet_id"] for a in placements}, {S})
        mobile = next(a for a in placements if a["source_id"] == MOBILE)
        self.assertEqual(mobile["source_identity"]["device_id"], DEVICE)
        self.assertEqual(mobile["source_identity"]["parent_id"], DEVICE)
        self.assertEqual(inventory["tableau_coverage"]["definition_coverage"], "reconciled_supplied_manifest")
        self.assertEqual(inventory["tableau_coverage"]["behavior_coverage"], "not_verified")
        self.assertEqual(inventory["upstream_payload"], self.value)

    def test_three_distinct_chart_definitions_repeated_placements_and_parameter(self):
        result = capture_fixture(self.root / "rich", rich=True)
        inventory = result["inventory"]
        self.assertEqual({(a["source_id"], a["kind"]) for a in inventory["assets"]}, set(RICH_EXPECTED))
        sheets = [a for a in inventory["assets"] if a["kind"] == "worksheet"]
        self.assertEqual(len(sheets), 3)
        self.assertEqual(len([a for a in inventory["assets"] if a["kind"] == "placement"]), 5)
        self.assertEqual(len([a for a in inventory["assets"] if a["kind"] == "parameter"]), 1)
        self.assertEqual(len([a for a in result["capture"]["attachments"] if a["format"] == "csv"]), 3)
        self.assertTrue(all(any(mark in a["source_payload"]["raw_xml"] for mark in ("Bar", "Line", "Text")) for a in sheets))

    def test_missing_and_extra_expected_objects_remain_visible(self):
        value = copy.deepcopy(self.value)
        value["request"]["expected_manifest"]["objects"].pop()
        value["request"]["expected_manifest"]["objects"].append({"object_id": D + "/missing[1]", "kind": "control"})
        inventory = self.parse(reseal(value))
        self.assertTrue(any(a["source_payload"].get("missing_from_definition") for a in inventory["assets"]))
        self.assertTrue(inventory["tableau_coverage"]["missing_expected"])
        self.assertTrue(inventory["tableau_coverage"]["unexpected_objects"])
        self.assertEqual(inventory["tableau_coverage"]["definition_coverage"], "partial")

    def test_hash_and_wrong_view_crosswalk_reject(self):
        value = copy.deepcopy(self.value)
        value["source"]["definition"]["content_utf8"] += " "
        with self.assertRaisesRegex(ValueError, "definition_hash"):
            self.parse(reseal(value))
        value = copy.deepcopy(self.value)
        value["request"]["identity_map"]["mappings"][1]["object_id"] = D
        with self.assertRaisesRegex(ValueError, "kind_mismatch"):
            self.parse(reseal(value))

    def test_unresolved_identity_is_gap_not_caption_join(self):
        value = copy.deepcopy(self.value)
        value["request"]["identity_map"]["mappings"][1].update(status="unresolved", object_id=None, evidence_reference=None)
        value["request"]["views"][1]["worksheet_id"] = None
        value["captures"][1]["worksheet_id"] = None
        for attachment in value["attachments"]:
            if attachment.get("view_id") == "sheet-0":
                attachment["worksheet_id"] = None
        inventory = self.parse(reseal(value))
        self.assertTrue(any(g["code"] == "tableau.api_xml_identity_unresolved" for g in inventory["gaps"]))
        sheet = next(a for a in inventory["assets"] if a["kind"] == "worksheet")
        self.assertEqual(sheet["source_identity"]["view_ids"], [])

    def test_attachment_edit_symlink_and_path_alias_reject(self):
        file = self.root / "capture/view-001.csv"
        file.write_text("Team,Value\nA,999\n")
        with self.assertRaisesRegex(ValueError, "bytes_mismatch"):
            b.verify_capture_files(self.value, file.parent)
        file.unlink()
        file.symlink_to(self.root / "outside.csv")
        with self.assertRaises(OSError):
            b.verify_capture_files(self.value, file.parent)
        value = copy.deepcopy(self.value)
        value["attachments"][0]["path"] = "./definition.twb"
        with self.assertRaisesRegex(ValueError, "unsafe_path"):
            self.parse(reseal(value))

    def test_xml_boundary_and_unresolved_duplicate_worksheet(self):
        for raw in (b'<!DOCTYPE workbook [<!ENTITY x "bad">]><workbook/>',
                    b'<workbook><connection password="sensitive"/></workbook>',
                    b'<workbook><property name="password"><value>sensitive</value></property></workbook>',
                    b'<workbook>' + b'<x>' * 33 + b'</x>' * 33 + b'</workbook>',
                    b'x' * (b.MAX_XML_BYTES + 1)):
            with self.assertRaises(ValueError):
                b.inspect_workbook(raw)
        raw = XML.replace(b'</worksheets>', b'<worksheet name="Revenue"/></worksheets>')
        parsed = b.inspect_workbook(raw)
        self.assertTrue(all(o["worksheet_id"] is None for o in parsed["objects"] if o["kind"] == "placement"))
        self.assertEqual(len([g for g in parsed["gaps"] if g["code"] == "tableau.unresolved_worksheet_reference"]), 3)

    def test_action_reference_is_not_a_new_definition_and_orphan_is_visible(self):
        raw = XML.replace(b'<target worksheet="Unknown"/>', b'<target><worksheet name="Unknown"/></target>')
        structure = b.inspect_workbook(raw)
        sheets = [o for o in structure["objects"] if o["kind"] == "worksheet"]
        self.assertEqual(len(sheets), 1)
        action = next(o for o in structure["objects"] if o["kind"] == "action")
        self.assertEqual(action["references"][0]["object_id"], S)
        self.assertEqual(action["references"][1]["status"], "unresolved")
        self.assertTrue(any(g["code"] == "tableau.action_reference_unresolved" for g in structure["gaps"]))


@unittest.skipUnless(os.environ.get("OMNI_ANALYST_DMA_CHECKOUT"), "optional trusted DMA checkout not selected")
class ActualDMAProducer(unittest.TestCase):
    def test_dma_semantics_capture_projection_and_requirements(self):
        checkout = Path(os.environ["OMNI_ANALYST_DMA_CHECKOUT"]).resolve()
        fixture = checkout / "skills/data-model-accelerator/examples/tableau-omni-e2e/input/repo"
        code = '''import json, socket, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "skills/data-model-accelerator/scripts"))
def denied(*a, **k): raise AssertionError("network forbidden")
socket.socket.connect = denied
import tableau_source
print(json.dumps(tableau_source.inspect_repo(sys.argv[2])))
'''
        result = subprocess.run([os.environ.get("OMNI_ANALYST_DMA_PYTHON", sys.executable), "-c", code, str(checkout), str(fixture)],
                                capture_output=True, text=True, check=True)
        inventory = json.loads(result.stdout)
        self.assertEqual(inventory["kind"], "tableau_source_inventory")
        self.assertEqual(len(inventory["worksheets"]), 3)
        self.assertEqual(len(inventory["dashboards"]), 1)
        xml = (fixture / "billing.twb").read_bytes()
        sheets = [W + "/worksheets[1]/worksheet[" + str(i) + "]" for i in (1, 2, 3)]
        # Authored independently of the visual reader: root + 3 definitions + dashboard
        # + 3 placements + all 5 published parameter definitions and worksheet filters.
        expected = [(W, "workbook"), (D, "dashboard")]
        expected += [(s, "worksheet") for s in sheets]
        expected += [(D + "/zones[1]/zone[" + str(i) + "]", "placement") for i in (1, 2, 3)]
        expected += [(W + "/datasources[1]/datasource[1]/column[" + str(i) + "]", "parameter") for i in range(1, 6)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve()
            value = Source(xml, request(xml, expected, sheets)).capture(path / "capture")["capture"]
            value["source"]["semantic_inventory"] = inventory
            value["source"]["semantic_inventory_sha256"] = b.sha(inventory)
            reseal(value)
            projection = t.translate(json.dumps(value).encode(), "tableau-capture")
            self.assertEqual(len([a for a in projection["assets"] if a["kind"] == "worksheet"]), 3)
            self.assertEqual(len([a for a in projection["assets"] if a["kind"] == "placement"]), 3)
            self.assertEqual(projection["upstream_payload"]["source"]["semantic_inventory"], inventory)
            self.assertFalse(any(g["code"] == "tableau.semantic_inventory_not_supplied" for g in projection["gaps"]))
            b.verify_capture_files(value, path / "capture")
            # Requirements composition exercises exact-byte reprojection, not just fixture equality.
            sys.path.insert(0, str(ROOT / "skills/omni-artifact-accelerator/scripts"))
            import visual_workflow as workflow
            project = path / "project"
            workflow.ap.init(project, "Actual DMA Tableau composition", "migration", "dashboard")
            import shutil
            shutil.copytree(path / "capture", project / "inputs/capture")
            (project / "inputs/capture/original.json").write_text(json.dumps(value))
            (project / "inputs/inventory.json").write_text(json.dumps(projection))
            workflow.prepare(project, "inputs/capture/original.json", "inputs/inventory.json", "contracts/visual.json")
            _, req = workflow.requirements(project, "contracts/visual.json")
            self.assertEqual(len(req["items"]), len(projection["assets"]))
            self.assertEqual(req["route"], "unselected")


if __name__ == "__main__":
    unittest.main()
