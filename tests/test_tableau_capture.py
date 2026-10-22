"""Real Tableau capture producer against synthetic transport; no tenant or source writes."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
import zipfile
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-translator/scripts/tableau_capture.py"
spec = importlib.util.spec_from_file_location("test_tableau_capture_module", SCRIPT)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

TWB = b'''<?xml version="1.0" encoding="utf-8"?>
<workbook version="2026.1"><datasources><datasource name="Parameters"><column name="[Threshold]" datatype="integer" value="10" /></datasource></datasources>
<worksheets><worksheet name="Sales"><table><view><filter column="[Region]" /></view></table></worksheet><worksheet name="Trend"><table /></worksheet><worksheet name="KPI"><table /></worksheet></worksheets>
<dashboards><dashboard name="Overview"><zones><zone id="1" name="Sales" type-v2="viz"/><zone id="2" name="Trend" type-v2="viz"/><zone id="3" name="KPI" type-v2="viz"/><zone id="4" name="Sales" type-v2="viz"/><zone id="5" type-v2="text"><formatted-text><run>Inventory overview</run></formatted-text></zone><zone id="6" type-v2="color" /></zones></dashboard></dashboards><actions><action name="Filter related items" /></actions></workbook>'''


def png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\x00\xff\x00")) + chunk(b"IEND", b"")


def request():
    dashboard = "/workbook[1]/dashboards[1]/dashboard[1]"
    worksheets = [f"/workbook[1]/worksheets[1]/worksheet[{i}]" for i in (1, 2, 3)]
    objects = [{"object_id": dashboard, "kind": "dashboard"}, *[{"object_id": item, "kind": "worksheet"} for item in worksheets]]
    objects.extend({"object_id": dashboard + f"/zones[1]/zone[{i}]", "kind": "placement"} for i in range(1, 7))
    return {"schema_version": capture.REQUEST, "capture_id": "inventory-default", "origin": "https://tableau.example.test",
            "api_version": "3.29", "site_id": "site-1", "expected_user_id": "user-1", "workbook_id": "workbook-1",
            "dashboard_view_id": "dashboard-1", "dashboard_id": dashboard,
            "principal_ref": "principal-ref://fixture/viewer", "authorization_ref": "human-authorization-ref://fixture/source-read",
            "evidence_mode": "synthetic_fixture", "views": [{"view_id": "dashboard-1", "role": "dashboard", "worksheet_id": None},
                *[{"view_id": f"sheet-{i}", "role": "worksheet", "worksheet_id": worksheets[i - 1]} for i in (1, 2, 3)]],
            "state": {"state_id": "default", "filters": {"Region & Site": "East / é"}, "parameters": {},
                      "locale": "en-US", "timezone": "America/Chicago", "data_time_policy": "inconclusive until paired watermark"},
            "expected_manifest": {"schema_version": 1, "reference": "independent synthetic fixture manifest",
                                  "completeness": "selected_dashboard", "objects": objects},
            "identity_map": {"schema_version": 1, "mappings": [{"view_id": "dashboard-1", "object_id": dashboard,
                                  "status": "matched", "evidence_reference": "fixture identity"},
                *[{"view_id": f"sheet-{i}", "object_id": worksheets[i - 1], "status": "matched", "evidence_reference": "fixture identity"} for i in (1, 2, 3)]]},
            "image_options": {"width": 1600, "height": 900, "max_age_minutes": 1}}


class Source:
    def __init__(self):
        self.calls = []
        self.workbook = {"workbook": {"id": "workbook-1", "updatedAt": "2026-10-21T00:00:00Z"}}
        self.views = {"views": {"view": [{"id": name} for name in ("dashboard-1", "sheet-1", "sheet-2", "sheet-3")]}}
        self.session = {"session": {"site": {"id": "site-1"}, "user": {"id": "user-1"}}}
        self.override = None
        self.definition_calls = 0
        self.drift = False

    def __call__(self, url, token, maximum, timeout):
        assert token == "source-session-fixture"
        assert url.startswith("https://tableau.example.test/api/3.29/")
        assert maximum <= capture.F.MAX_FILE and timeout <= 45
        self.calls.append(url)
        if self.override:
            result = self.override(url)
            if result is not None:
                return result
        parsed = urlsplit(url)
        if parsed.path.endswith("/sessions/current"):
            return 200, {"content-type": "application/json"}, capture.encoded(self.session)
        if parsed.path.endswith("/workbooks/workbook-1"):
            return 200, {"content-type": "application/json"}, capture.encoded(self.workbook)
        if parsed.path.endswith("/workbooks/workbook-1/views"):
            return 200, {"content-type": "application/json"}, capture.encoded(self.views)
        if parsed.path.endswith("/content"):
            self.definition_calls += 1
            assert parse_qs(parsed.query) == {"includeExtract": ["False"]}
            raw = TWB.replace(b"Inventory overview", b"Changed source") if self.drift and self.definition_calls > 1 else TWB
            return 200, {"content-type": "application/xml"}, raw
        assert parse_qs(parsed.query)["vf_Region & Site"] == ["East / é"]
        if parsed.path.endswith("/image"):
            assert parse_qs(parsed.query)["vizWidth"] == ["1600"]
            return 200, {"content-type": "image/png"}, png()
        assert parsed.path.endswith("/data") and "/dashboard-1/" not in parsed.path
        return 200, {"content-type": "text/csv; charset=utf-8"}, b"Site,Units\nEast,21\nWest,4\n"


def run(source, directory, value=None, **kwargs):
    return capture.capture_rest(value or request(), directory=directory, session_token="source-session-fixture",
                                transport=source, allow_source_read=True, allow_source_query=True, **kwargs)


def text_response(value):
    return {"content": [{"type": "text", "text": json.dumps(value)}]}


class TableauCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root / "capture"
        self.denied = patch.object(socket, "socket", side_effect=AssertionError("tenant networking forbidden"))
        self.denied.start()
        self.addCleanup(self.denied.stop)

    def test_real_producer_three_worksheets_repeated_placement_and_persisted_bytes(self):
        source = Source()
        result = run(source, self.directory)
        value = result["capture"]
        self.assertEqual(value["status"], "complete")
        self.assertEqual(len(value["captures"]), 4)
        self.assertEqual(len([a for a in value["attachments"] if a["format"] == "csv"]), 3)
        self.assertEqual(value["source"]["definition"]["sha256"], hashlib.sha256(TWB).hexdigest())
        self.assertEqual((self.directory / "definition.twb").read_bytes(), TWB)
        self.assertEqual((self.directory / "view-000.png").read_bytes(), png())
        self.assertEqual(value["source"]["identity"]["verification"], "source_session_observed")
        self.assertEqual(len(value["request"]["expected_manifest"]["objects"]), 10)
        self.assertIn("configuration_bracket_is_not_atomic_data_snapshot", value["gaps"])
        self.assertFalse(value["target_write_authority"])
        self.assertEqual(value["native_validation"], "not_performed")
        for path in self.directory.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        previous = len(source.calls)
        self.assertEqual(run(source, self.directory, resume=True)["status"], "complete")
        self.assertEqual(len(source.calls), previous)

    def test_session_wrong_site_or_user_stops_before_content(self):
        for key in ("site", "user"):
            source = Source()
            source.session["session"][key]["id"] = "wrong"
            result = run(source, self.root / key)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(source.calls), 1)

    def test_definition_drift_does_not_report_complete(self):
        source = Source()
        source.drift = True
        result = run(source, self.directory)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual((self.directory / "definition.twb").read_bytes(), TWB)

    def test_wrong_workbook_missing_view_and_partial_listing_stop(self):
        for kind in ("workbook", "missing", "pagination"):
            source = Source()
            if kind == "workbook":
                source.workbook["workbook"]["id"] = "wrong"
            elif kind == "missing":
                source.views["views"]["view"].pop()
            else:
                source.views["pagination"] = {"totalAvailable": "99", "pageNumber": "1"}
            self.assertEqual(run(source, self.root / kind)["status"], "blocked")
            self.assertFalse(any("/content" in url for url in source.calls))

    def test_transport_timeout_never_replays_uncertain_export(self):
        source = Source()
        def timeout(url):
            if "/dashboard-1/image" in url:
                raise TimeoutError("sensitive details must never be copied")
        source.override = timeout
        result = run(source, self.directory)
        self.assertEqual(result["status"], "partial")
        source.override = None
        result = run(source, self.directory, resume=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(sum("/dashboard-1/image" in url for url in source.calls), 1)
        self.assertNotIn("sensitive details", Path(result["output"]).read_text())

    def test_throttle_retry_after_and_total_attempt_bound(self):
        source = Source()
        source.override = lambda url: (429, {"retry-after": "60"}, b"throttle") if "/dashboard-1/image" in url else None
        value = request()
        value["max_attempts_per_operation"] = 1
        start = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.assertEqual(run(source, self.directory, value, now=lambda: start)["status"], "partial")
        self.assertEqual(run(source, self.directory, value, resume=True, now=lambda: start + timedelta(seconds=30))["status"], "partial")
        self.assertEqual(sum("/dashboard-1/image" in url for url in source.calls), 1)
        self.assertEqual(run(source, self.directory, value, resume=True, now=lambda: start + timedelta(seconds=61))["status"], "blocked")

    def test_finite_per_invocation_budget_can_resume_to_complete(self):
        source = Source()
        value = request()
        value["max_requests_per_invocation"] = 5
        result = run(source, self.directory, value)
        for _ in range(20):
            if result["status"] != "partial":
                break
            before = len(source.calls)
            result = run(source, self.directory, value, resume=True)
            self.assertLessEqual(len(source.calls) - before, 5)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(sum("/dashboard-1/image" in url for url in source.calls), 1)

    def test_capture_request_byte_and_age_budgets(self):
        for key, limit in (("max_total_requests", 2), ("max_total_bytes", 10)):
            value = request()
            value[key] = limit
            result = run(Source(), self.root / key, value)
            self.assertIn(result["status"], ("blocked", "partial"))
            self.assertLessEqual(result["capture"]["budget"]["requests"], limit if key == "max_total_requests" else 100)
        value = request()
        value["max_requests_per_invocation"] = 5
        value["max_elapsed_seconds"] = 10
        start = datetime(2026, 10, 21, tzinfo=timezone.utc)
        source = Source()
        run(source, self.directory, value, now=lambda: start)
        self.assertEqual(run(source, self.directory, value, resume=True, now=lambda: start + timedelta(seconds=11))["status"], "blocked")

    def test_changed_state_and_attachment_tampering_reject_resume(self):
        source = Source()
        run(source, self.directory)
        value = request()
        value["state"]["filters"]["Region & Site"] = "Other"
        with self.assertRaises(capture.CaptureError):
            run(source, self.directory, value, resume=True)
        (self.directory / "view-000.png").write_bytes(b"changed")
        with self.assertRaises(capture.CaptureError):
            run(source, self.directory, resume=True)

    def test_changed_runtime_requires_review_instead_of_old_journal_resume(self):
        run(Source(), self.directory)
        replacement = self.root / "changed-runtime.py"
        replacement.write_text("# different runtime, never executed")
        with patch.object(capture, "__file__", str(replacement)):
            with self.assertRaisesRegex(capture.CaptureError, "runtime_changed"):
                run(Source(), self.directory, resume=True)

    def test_invalid_media_csv_and_auth_status_do_not_persist_payload(self):
        for status, media, raw in ((200, "text/html", b"<html>private error</html>"),
                                   (200, "image/png", b"invalid png"), (401, "text/html", b"credential-private-error")):
            source = Source()
            source.override = lambda url, s=status, m=media, r=raw: (s, {"content-type": m}, r) if "/dashboard-1/image" in url else None
            folder = self.root / str(status + len(raw))
            result = run(source, folder)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse((folder / "view-000.png").exists())
            self.assertNotIn(raw.decode(), Path(result["output"]).read_text())
        with self.assertRaises(capture.CaptureError):
            capture.F.csv_info(b'a,b\n"unfinished,2\n')
        with self.assertRaises(capture.CaptureError):
            capture.F.csv_info(b"a,b\n1,2,3\n")
        self.assertEqual(capture.F.csv_info(b"a,b\n")["observed_rows"], 0)

    def test_unknown_parameter_state_fails_before_network(self):
        value = request()
        value["state"]["parameters"] = {"Threshold": "20"}
        source = Source()
        self.assertEqual(run(source, self.directory, value)["status"], "blocked")
        self.assertEqual(source.calls, [])

    def test_url_token_symlink_and_redirect_boundaries(self):
        for origin in ("http://tableau.example.test", "https://u:p@tableau.example.test", "https://tableau.example.test/api", "https://tableau.example.test?x=1"):
            value = request()
            value["origin"] = origin
            with self.assertRaises(capture.CaptureError):
                run(Source(), self.directory, value)
        with self.assertRaises(capture.CaptureError):
            capture.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example")
        (self.root / "link").symlink_to(self.root)
        with self.assertRaises(capture.CaptureError):
            run(Source(), self.root / "link" / "capture")
        with self.assertRaises(capture.CaptureError):
            capture.capture_rest(request(), directory=self.directory, session_token="token\nheader")

    def test_no_extract_zip_path_collision_entity_and_png_inflate_guards(self):
        for names in (["../bad.twb"], ["a.twb", "A.twb"], ["a.twb", "data.hyper"]):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as archive:
                for name in names:
                    archive.writestr(name, TWB)
            with self.assertRaises(capture.CaptureError):
                capture.F.definition(stream.getvalue())
        with self.assertRaises(capture.CaptureError):
            capture.F.definition(b'<!DOCTYPE workbook [<!ENTITY x "bad">]><workbook>&x;</workbook>')
        with self.assertRaises(capture.CaptureError):
            capture.F.definition(b'<workbook><connection password="private-value" /></workbook>')
        with self.assertRaises(capture.CaptureError):
            capture.F.png_info(png()[:-5])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("workbook.twb", TWB)
        parsed = capture.F.definition(stream.getvalue())
        self.assertEqual(parsed["xml"], TWB)

    def test_default_transport_http_error_and_truncated_response(self):
        class Response(io.BytesIO):
            status = 429
            headers = {"Content-Type": "text/html", "Retry-After": "10"}
        from urllib.error import HTTPError
        error = HTTPError("https://tableau.example.test/fixed", 429, "Throttle", Response.headers, Response(b"body"))
        with patch.object(capture, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            status, headers, raw = capture.default_transport("https://tableau.example.test/fixed", "token", 10, 1)
        self.assertEqual((status, headers["retry-after"], raw), (429, "10", b"body"))
        response = Response(b"short")
        response.headers = {"Content-Type": "text/csv", "Content-Length": "999"}
        with patch.object(capture, "build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(capture.CaptureError):
                capture.default_transport("https://tableau.example.test/fixed", "token", 100, 1)

    def test_mcp_inline_image_and_legacy_json_encoded_csv(self):
        records = [{"record_id": "image", "tool": "get-view-image", "arguments": {"viewId": "sheet-1", "width": 1600, "height": 900, "viewFilters": request()["state"]["filters"]},
                    "response": {"content": [{"type": "image", "mimeType": "image/png", "data": base64.b64encode(png()).decode()}]}},
                   {"record_id": "data", "tool": "get-view-data", "arguments": {"viewId": "sheet-1", "viewFilters": request()["state"]["filters"]},
                    "response": text_response("Site,Units\nEast,21\n") }]
        result = capture.import_mcp(request(), {"schema_version": "tableau-mcp-intake.v1", "records": records}, directory=self.directory, allow_source_read=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["capture"]["captures"][1]["status"], "complete")
        self.assertEqual((self.directory / "mcp-001.csv").read_bytes(), b"Site,Units\nEast,21\n")

    def test_mcp_all_data_preserves_duplicate_parts_errors_and_no_caption_join(self):
        value = request()
        value["api_version"] = "3.30"
        parts = [{"sheetName": "Same", "columns": ["Units"], "rows": [["21"]], "sheetStatus": "OK"},
                 {"sheetName": "Same", "columns": ["Units"], "rows": [["4"]], "sheetStatus": "OK"},
                 {"sheetName": "Denied", "columns": [], "rows": [], "sheetStatus": "ERROR", "errorDetail": "Denied"}]
        record = {"record_id": "all-data", "tool": "get-view-data", "arguments": {"viewId": "dashboard-1", "viewFilters": value["state"]["filters"]}, "response": text_response(parts)}
        result = capture.import_mcp(value, {"schema_version": "tableau-mcp-intake.v1", "records": [record]}, directory=self.directory, allow_source_read=True)
        retained = result["capture"]["operations"][0]["parts"]
        self.assertEqual([p["source_part"] for p in retained], parts)
        self.assertNotEqual(retained[0]["attachment"], retained[1]["attachment"])
        self.assertTrue(all(p["identity_status"] == "unresolved_no_caption_join" for p in retained))
        self.assertEqual(result["status"], "partial")

    def test_mcp_resource_unavailable_until_pinned_local_transfer_no_signed_url_retained(self):
        remote = "https://bucket.example.test/workbook.twb?X-Amz-Signature=private-query-secret"
        record = {"record_id": "definition", "tool": "download-workbook", "arguments": {"workbookId": "workbook-1", "includeExtract": False},
                  "response": {"content": [{"type": "resource_link", "uri": remote, "mimeType": "application/xml", "name": "workbook.twb"}]}}
        intake = {"schema_version": "tableau-mcp-intake.v1", "records": [record]}
        result = capture.import_mcp(request(), intake, directory=self.directory, allow_source_read=True)
        self.assertNotIn("definition", result["capture"]["source"])
        self.assertNotIn("private-query-secret", "".join(p.read_text() for p in self.directory.glob("*.json")))
        transfers = self.root / "transfers"
        transfers.mkdir(mode=0o700)
        (transfers / "authority.twb").write_bytes(TWB)
        record["transfer"] = {"path": "authority.twb", "sha256": hashlib.sha256(TWB).hexdigest(), "bytes": len(TWB),
                              "reference_sha256": hashlib.sha256(remote.encode()).hexdigest(), "provenance_reference": "approved host transfer receipt"}
        result = capture.import_mcp(request(), intake, directory=self.root / "transferred", transfer_directory=transfers, allow_source_read=True)
        self.assertEqual(result["capture"]["source"]["definition"]["content_utf8"], TWB.decode())

    def test_mcp_wrong_state_malformed_part_and_inaccessible_temp_path_are_gaps(self):
        records = [{"record_id": "wrong-state", "tool": "get-view-data", "arguments": {"viewId": "sheet-1", "viewFilters": {}}, "response": text_response("a\n1\n")},
                   {"record_id": "remote-path", "tool": "download-workbook", "arguments": {"workbookId": "workbook-1", "includeExtract": False},
                    "response": text_response({"path": "/private/source-host/remote.twb", "filename": "remote.twb", "mimeType": "application/xml"})}]
        result = capture.import_mcp(request(), {"schema_version": "tableau-mcp-intake.v1", "records": records}, directory=self.directory, allow_source_read=True)
        self.assertEqual(result["capture"]["operations"][0]["status"], "rejected")
        self.assertIn("remote_resource_or_path_not_transferred", result["capture"]["gaps"])
        self.assertFalse(any(a["format"] == "csv" for a in result["capture"]["attachments"]))

    def test_mcp_malformed_later_part_rejects_all_derived_results(self):
        value = request()
        value["api_version"] = "3.30"
        parts = [{"sheetName": "Valid", "columns": ["Units"], "rows": [["1"]], "sheetStatus": "OK"},
                 {"sheetName": "Invalid", "columns": ["Units"], "rows": [["1", "2"]], "sheetStatus": "OK"}]
        record = {"record_id": "malformed", "tool": "get-view-data", "arguments": {"viewId": "dashboard-1", "viewFilters": value["state"]["filters"]}, "response": text_response(parts)}
        result = capture.import_mcp(value, {"schema_version": "tableau-mcp-intake.v1", "records": [record]}, directory=self.directory, allow_source_read=True)
        self.assertEqual(result["capture"]["operations"][0]["status"], "rejected")
        self.assertFalse(list(self.directory.glob("*.csv")))

    def test_keyboard_interrupt_retains_intent_and_no_replay(self):
        source = Source()
        def interrupted(url):
            if "/dashboard-1/image" in url:
                raise KeyboardInterrupt()
        source.override = interrupted
        with self.assertRaises(KeyboardInterrupt):
            run(source, self.directory)
        source.override = None
        self.assertEqual(run(source, self.directory, resume=True)["status"], "partial")
        self.assertEqual(sum("/dashboard-1/image" in url for url in source.calls), 1)

    def test_credentials_in_metadata_or_header_never_enter_retained_response(self):
        source = Source()
        source.workbook["workbook"]["password"] = "private-password-value"
        result = run(source, self.directory)
        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("private-password-value", b"".join(p.read_bytes() for p in self.directory.iterdir()).decode(errors="replace"))

    def test_actual_dma_reader_requires_pin_and_parses_only_retained_definition(self):
        checkout_value = os.environ.get("OMNI_ANALYST_DMA_CHECKOUT")
        if not checkout_value:
            self.skipTest("optional trusted DMA checkout not selected")
        checkout = Path(checkout_value).resolve()
        reader = checkout / "skills/data-model-accelerator/scripts/tableau_source.py"
        result = run(Source(), self.directory)
        options = {"checkout": checkout, "executable": os.environ.get("OMNI_ANALYST_DMA_PYTHON", sys.executable),
                   "producer_revision": "c513474e87af9c2c31deebd2ae675c8602955203"}
        with self.assertRaises(capture.CaptureError):
            capture.enrich_dma(result["output"], expected_reader_sha256="0" * 64, **options)
        enriched = capture.enrich_dma(result["output"], expected_reader_sha256=hashlib.sha256(reader.read_bytes()).hexdigest(), **options)
        inventory = enriched["capture"]["source"]["semantic_inventory"]
        self.assertEqual(inventory["kind"], "tableau_source_inventory")
        self.assertEqual(len(inventory["worksheets"]), 3)
        self.assertEqual(enriched["capture"]["previous_content_hash"], result["capture"]["content_hash"])
        self.assertFalse(list(self.directory.glob(".dma-read-*")))


if __name__ == "__main__":
    unittest.main()
