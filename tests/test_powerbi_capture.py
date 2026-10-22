"""Synthetic current-shaped PBIR and official response-contract capture tests.

No tenant, native rendering, customer data or native acceptance is represented.
"""

import base64
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile
import zlib

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/omni-artifact-translator/scripts/powerbi_capture.py"
)
spec = importlib.util.spec_from_file_location("pbi_capture_test", SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
F = C.F
WORKSPACE = "11111111-1111-4111-8111-111111111111"
REPORT = "22222222-2222-4222-8222-222222222222"
DATASET = "33333333-3333-4333-8333-333333333333"
OPERATION = "44444444-4444-4444-8444-444444444444"
NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def png():
    def chunk(kind, raw):
        return (
            struct.pack(">I", len(raw))
            + kind
            + raw
            + struct.pack(">I", zlib.crc32(kind + raw) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + chunk(b"IEND", b"")
    )


def definitions():
    """Authored native-shaped modern PBIR. IDs/captions intentionally differ."""
    schema = "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    docs = {
        "definition.pbir": {
            "version": "4.0",
            "datasetReference": {"byPath": {"path": "../Inventory.SemanticModel"}},
        },
        "definition/version.json": {
            "$schema": schema + "definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
        "definition/report.json": {
            "$schema": schema + "definition/report/3.3.0/schema.json",
            "themeCollection": {},
            "filterConfig": {"filters": []},
        },
        "definition/pages/pages.json": {
            "$schema": schema + "definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": ["ReportSectionOps", "ReportSectionDetail"],
            "activePageName": "ReportSectionOps",
        },
        "definition/pages/ReportSectionOps/page.json": {
            "$schema": schema + "definition/page/2.1.0/schema.json",
            "name": "ReportSectionOps",
            "displayName": "Inventory exceptions",
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
            "visualInteractions": [
                {
                    "source": "site_selector",
                    "target": "available_by_site",
                    "type": "DataFilter",
                }
            ],
        },
        "definition/pages/ReportSectionDetail/page.json": {
            "$schema": schema + "definition/page/2.1.0/schema.json",
            "name": "ReportSectionDetail",
            "displayName": "Inventory exceptions",
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        },
        "definition/bookmarks/bookmarks.json": {
            "items": [
                {
                    "name": "BookmarkInitial",
                    "displayName": "Initial view",
                    "explorationState": {"activeSection": "ReportSectionOps"},
                }
            ]
        },
    }
    for index, (page, ident, kind, role) in enumerate(
        [
            (
                "ReportSectionOps",
                "available_by_site",
                "clusteredColumnChart",
                "Category",
            ),
            ("ReportSectionOps", "site_selector", "slicer", "Values"),
            ("ReportSectionDetail", "available_by_site", "pivotTable", "Rows"),
        ]
    ):
        docs[f"definition/pages/{page}/visuals/{ident}/visual.json"] = {
            "$schema": schema + "definition/visualContainer/2.9.0/schema.json",
            "name": ident,
            "position": {
                "x": index * 10,
                "y": 0,
                "z": index,
                "height": 300,
                "width": 400,
            },
            "visual": {
                "visualType": kind,
                "query": {
                    "queryState": {
                        role: {
                            "projections": [
                                {
                                    "field": {
                                        "Column": {
                                            "Expression": {
                                                "SourceRef": {"Entity": "Inventory"}
                                            },
                                            "Property": "Site",
                                        }
                                    },
                                    "queryRef": "Inventory.Site",
                                }
                            ]
                        }
                    }
                },
                "visualContainerObjects": {
                    "title": [
                        {
                            "properties": {
                                "text": {
                                    "expr": {"Literal": {"Value": "'Stock by site'"}}
                                }
                            }
                        }
                    ]
                },
            },
        }
    result = {p: F.encoded(v) for p, v in docs.items()}
    result["Inventory.SemanticModel/definition/tables/Inventory.tmdl"] = (
        b"table Inventory\n\tmeasure Available = SUM(Inventory[Units])\n\tcolumn Site\n\t\tdataType: string\n"
    )
    result["StaticResources/RegisteredResources/logo.png"] = png()
    return result


def fabric_payload(parts=None):
    return {
        "definition": {
            "parts": [
                {
                    "path": path,
                    "payload": base64.b64encode(raw).decode(),
                    "payloadType": "InlineBase64",
                }
                for path, raw in (parts or definitions()).items()
            ]
        }
    }


def request():
    return {
        "schema_version": C.REQUEST,
        "capture_id": "synthetic-inventory",
        "workspace_id": WORKSPACE,
        "report_id": REPORT,
        "dataset_id": DATASET,
        "principal_ref": "synthetic-operator",
        "authorization_ref": "synthetic-read-grant",
        "evidence_mode": "synthetic_fixture",
        "route": "omni_semantic_reconstruction",
        "route_reference": "synthetic-human-selection",
        "views": [
            {
                "page_id": "ReportSectionOps",
                "visual_id": "available_by_site",
                "export_png": True,
            },
            {
                "page_id": "ReportSectionOps",
                "visual_id": "site_selector",
                "export_png": True,
            },
            {
                "page_id": "ReportSectionDetail",
                "visual_id": "available_by_site",
                "export_png": True,
            },
        ],
        "state": {
            "state_id": "initial",
            "filters": [{"filter": "Inventory/Site eq 'East'"}],
            "bookmark": None,
            "locale": "en-US",
            "timezone": None,
            "principal": None,
            "data_time_policy": "independent refresh evidence pending",
        },
        "queries": [
            {
                "query_id": "available-units",
                "query": 'EVALUATE ROW("Available", [Available])',
                "page_id": "ReportSectionOps",
                "visual_id": "available_by_site",
                "context_reference": "reviewed-query-scope-unknown-render-equivalence",
            }
        ],
    }


def reply(value, code=200, **headers):
    return code, {"content-type": "application/json", **headers}, F.encoded(value)


class Transport:
    def __init__(self):
        self.calls = []
        self.export_count = 0
        self.definition_calls = 0
        self.query_value = {"results": [{"tables": [{"rows": [{"[Available]": 12}]}]}]}
        self.definition_drift = False
        self.pending_export = False
        self.lro = False
        self.lro_running = False

    def __call__(self, method, url, token, body, maximum, timeout):
        self.calls.append((method, url, token, F.decode(body) if body else None))
        if url.startswith(C.FABRIC):
            assert token == "fabric-synthetic-token"
            if "/getDefinition?" in url:
                self.definition_calls += 1
                if self.lro:
                    return (
                        202,
                        {
                            "location": C.FABRIC + "/v1/operations/" + OPERATION,
                            "x-ms-operation-id": OPERATION,
                            "retry-after": "0",
                        },
                        b"",
                    )
                data = definitions()
                if self.definition_drift and self.definition_calls > 1:
                    value = F.decode(data["definition/report.json"])
                    value["annotations"] = [{"name": "changed", "value": "yes"}]
                    data["definition/report.json"] = F.encoded(value)
                return reply(fabric_payload(data))
            if url.endswith("/result"):
                return reply(fabric_payload())
            return reply(
                {"status": "Running" if self.lro_running else "Succeeded"},
                **{"retry-after": "1"},
            )
        assert token == "powerbi-synthetic-token"
        if url.endswith("/executeQueries"):
            return reply(self.query_value)
        if url.endswith("/ExportTo"):
            self.export_count += 1
            return reply(
                {
                    "id": "opaque/+=" + str(self.export_count),
                    "reportId": REPORT,
                    "status": "NotStarted",
                },
                202,
            )
        if "/exports/" in url:
            if url.endswith("/file"):
                return 200, {"content-type": "image/png"}, png()
            from urllib.parse import unquote

            export_id = unquote(url.split("/exports/")[1])
            return reply(
                {
                    "id": export_id,
                    "reportId": REPORT,
                    "status": "Running" if self.pending_export else "Succeeded",
                    "resourceLocation": url + "/file",
                },
                **{"retry-after": "1"},
            )
        if url.endswith("/pages"):
            return reply(
                {
                    "value": [
                        {
                            "name": "ReportSectionOps",
                            "displayName": "Inventory exceptions",
                            "order": 0,
                        },
                        {
                            "name": "ReportSectionDetail",
                            "displayName": "Inventory exceptions",
                            "order": 1,
                        },
                    ]
                }
            )
        return reply(
            {
                "id": REPORT,
                "name": "Synthetic inventory",
                "datasetId": DATASET,
                "reportType": "PowerBIReport",
            }
        )


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / "capture"
        self.transport = Transport()

    def run_capture(self, req=None, **kw):
        return C.capture(
            req or request(),
            self.directory,
            fabric_token="fabric-synthetic-token",
            powerbi_token="powerbi-synthetic-token",
            transport=kw.pop("transport", self.transport),
            now=kw.pop("now", NOW),
            allow_source_read=True,
            allow_source_query=True,
            **kw,
        )

    def test_actual_producer_preserves_all_files_repeated_native_ids_and_unknown_state(
        self,
    ):
        result = self.run_capture()
        value = result["capture"]
        self.assertEqual(result["status"], "complete", value["gaps"])
        self.assertEqual(
            {p["source_path"] for p in value["source"]["definition_files"]},
            set(definitions()),
        )
        for pin in value["source"]["definition_files"]:
            self.assertEqual(
                F.read_pin(self.directory, pin), definitions()[pin["source_path"]]
            )
        self.assertEqual(
            len([a for a in value["attachments"] if a["format"] == "png"]), 3
        )
        self.assertEqual(value["source"]["state_observation"], {"status": "unknown"})
        query = next(a for a in value["attachments"] if a.get("query_id"))
        self.assertEqual(query["result_completeness"]["status"], "unknown")
        self.assertEqual(value["native_validation"], "not_performed")
        self.assertFalse(value["target_write_authority"])
        before = len(self.transport.calls)
        self.assertEqual(self.run_capture(resume=True)["status"], "complete")
        self.assertEqual(len(self.transport.calls), before)
        self.assertTrue(
            all(
                "opaque%2F%2B%3D" in url
                for _, url, _, _ in self.transport.calls
                if "/exports/" in url
            )
        )
        self.assertEqual(
            json.loads(Path(result["output"]).read_text())["content_hash"],
            value["content_hash"],
        )

    def test_local_and_fabric_import_do_not_resolve_semantic_reference(self):
        source = self.root / "source"
        source.mkdir()
        for name, raw in definitions().items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        with patch("socket.socket", side_effect=AssertionError("no network")):
            local = C.import_local(
                request(), source, self.directory, allow_source_read=True
            )
            supplied = C.import_fabric_definition(
                request(),
                fabric_payload(),
                self.root / "fabric",
                allow_source_read=True,
            )
        self.assertEqual(local["status"], "partial")
        self.assertEqual(
            local["capture"]["source"]["definition_fingerprint"],
            supplied["capture"]["source"]["definition_fingerprint"],
        )
        self.assertEqual(
            local["capture"]["request"]["route"], "omni_semantic_reconstruction"
        )
        self.assertFalse(
            any(
                "model.bim" in p["source_path"]
                for p in local["capture"]["source"]["definition_files"]
            )
        )

    def test_ambiguous_post_is_durable_and_never_repeated(self):
        original = self.transport

        def broken(*args):
            if args[0] == "POST":
                original.calls.append((args[0], args[1], args[2], None))
                raise TimeoutError("untrusted server detail")
            return original(*args)

        result = self.run_capture(transport=broken)
        self.assertEqual(result["status"], "blocked")
        count = len(original.calls)
        self.run_capture(resume=True)
        self.assertEqual(len(original.calls), count)
        self.assertEqual(result["capture"]["operations"][-1]["status"], "ambiguous")
        self.assertNotIn("untrusted server detail", Path(result["output"]).read_text())

    def test_export_pending_resumes_same_post_and_honors_delay(self):
        self.transport.pending_export = True
        first = self.run_capture()
        self.assertEqual(first["status"], "partial")
        count = len(self.transport.calls)
        self.run_capture(resume=True)
        self.assertEqual(len(self.transport.calls), count)
        self.transport.pending_export = False
        result = self.run_capture(resume=True, now=NOW + timedelta(seconds=2))
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        self.assertEqual(self.transport.export_count, 3)

    def test_fabric_lro_result_preserves_link_and_no_duplicate_definition_post(self):
        self.transport.lro = True
        self.transport.lro_running = True
        first = self.run_capture()
        self.assertEqual(first["status"], "partial")
        self.transport.lro_running = False
        result = self.run_capture(resume=True, now=NOW + timedelta(seconds=2))
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        self.assertEqual(self.transport.definition_calls, 2)

    def test_source_drift_blocks_without_claiming_parity(self):
        self.transport.definition_drift = True
        result = self.run_capture()
        self.assertEqual(result["status"], "blocked")
        self.assertNotEqual(
            result["capture"]["source"]["definition_fingerprint"],
            result["capture"]["source"]["definition_after_fingerprint"],
        )

    def test_http_200_query_error_is_partial_not_numeric_complete(self):
        self.transport.query_value = {
            "results": [
                {
                    "tables": [{"rows": [{"[Available]": 12}]}],
                    "error": {"message": "More than allowed rows"},
                }
            ]
        }
        result = self.run_capture()
        self.assertEqual(result["status"], "partial")
        record = next(a for a in result["capture"]["attachments"] if a.get("query_id"))
        self.assertEqual(record["result_completeness"]["status"], "partial")
        self.assertIn("query_partial:available-units", result["capture"]["gaps"])

    def test_fixed_audiences_query_grant_and_source_grant(self):
        with self.assertRaisesRegex(ValueError, "source_read_grant"):
            C.capture(request(), self.directory)
        with self.assertRaisesRegex(ValueError, "source_query_grant"):
            C.capture(request(), self.directory, allow_source_read=True)
        self.assertEqual(self.transport.calls, [])
        self.run_capture()
        for method, url, _, body in self.transport.calls:
            if url.endswith("/executeQueries"):
                self.assertEqual(body["serializerSettings"], {"includeNulls": True})
            if url.endswith("/ExportTo"):
                self.assertEqual(body["format"], "PNG")
                self.assertEqual(
                    body["powerBIReportConfiguration"]["reportLevelFilters"],
                    request()["state"]["filters"],
                )

    def test_throttle_post_retries_only_after_known_response_delay(self):
        original = self.transport
        throttled = []

        def transport(*args):
            if args[0] == "POST" and not throttled:
                throttled.append(True)
                return 429, {"retry-after": "10"}, b"not retained"
            return original(*args)

        first = self.run_capture(transport=transport)
        self.assertEqual(first["status"], "partial")
        result = self.run_capture(
            transport=transport, resume=True, now=NOW + timedelta(seconds=11)
        )
        self.assertEqual(result["status"], "complete")
        operation = next(
            o
            for o in result["capture"]["operations"]
            if o["key"] == "definition.before"
        )
        self.assertEqual(operation["attempts"], 2)

    def test_budgets_resume_and_old_evidence_cannot_be_changed(self):
        req = request()
        req["max_requests_per_invocation"] = 2
        first = self.run_capture(req)
        self.assertEqual(first["status"], "partial")
        self.assertEqual(first["capture"]["budget"]["requests"], 2)
        second = self.run_capture(req, resume=True)
        self.assertLessEqual(second["capture"]["budget"]["requests"], 4)
        pin = second["capture"]["source"]["definition_files"][0]
        (self.directory / pin["path"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "evidence_bytes_changed"):
            self.run_capture(req, resume=True)

    def test_lro_host_escape_and_token_echo_are_rejected_without_secret_receipts(self):
        for mode in ("location", "token"):
            with self.subTest(mode=mode):
                self.directory = self.root / mode
                original = Transport()

                def transport(*args):
                    if args[0] == "POST":
                        if mode == "location":
                            return (
                                202,
                                {
                                    "location": "https://attacker.invalid/v1/operations/"
                                    + OPERATION,
                                    "x-ms-operation-id": OPERATION,
                                    "retry-after": "0",
                                },
                                b"",
                            )
                        return reply({"message": "fabric-synthetic-token"})
                    return original(*args)

                result = self.run_capture(transport=transport)
                self.assertEqual(result["status"], "blocked")
                for path in self.directory.glob("capture-*.json"):
                    self.assertNotIn("fabric-synthetic-token", path.read_text())
                self.assertFalse(
                    any("attacker.invalid" in url for _, url, _, _ in original.calls)
                )

    def test_response_media_and_malformed_png_fail_closed(self):
        for media, raw in [
            ("text/html", b"<html>error</html>"),
            ("image/png", png()[:-3]),
        ]:
            self.directory = self.root / str(len(raw))
            original = Transport()

            def transport(*args):
                if args[1].endswith("/file"):
                    return 200, {"content-type": media}, raw
                return original(*args)

            self.assertEqual(self.run_capture(transport=transport)["status"], "blocked")

    def test_zip_members_paths_and_png_validation(self):
        def archive(name, raw=png(), symlink=False):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as z:
                item = zipfile.ZipInfo(name)
                if symlink:
                    item.external_attr = 0o120777 << 16
                z.writestr(item, raw)
            return buffer.getvalue()

        self.assertEqual(
            F.image_parts(archive("ReportSectionOps.png"))[0][0], "ReportSectionOps.png"
        )
        for raw in (
            archive("../escape.png"),
            archive("file.html"),
            archive("link.png", symlink=True),
            archive("bad.png", b"invalid"),
        ):
            with self.assertRaises(ValueError):
                F.image_parts(raw)

    def test_definition_paths_duplicate_secret_and_symlink_rejected(self):
        for name in ("../escape.json", "/absolute.json", "a\\b.json"):
            payload = fabric_payload()
            payload["definition"]["parts"][0]["path"] = name
            with self.assertRaises(ValueError):
                F.fabric_parts(payload)
        payload = fabric_payload()
        payload["definition"]["parts"].append(
            copy.deepcopy(payload["definition"]["parts"][0])
        )
        with self.assertRaises(ValueError):
            F.fabric_parts(payload)
        payload = fabric_payload()
        payload["definition"]["parts"][0]["payload"] = base64.b64encode(
            b'{"password":"secret-value"}'
        ).decode()
        with self.assertRaises(ValueError):
            F.fabric_parts(payload)
        source = self.root / "source"
        source.mkdir()
        (source / "file.json").symlink_to(SCRIPT)
        with self.assertRaises(ValueError):
            F.local_parts(source)

    def test_definition_directory_prefix_aliases_rejected_before_intake(self):
        for first, second in (("Report", "report"), ("Caf\u00e9", "Cafe\u0301")):
            parts = [
                (first + "/definition/report.json", b"{}"),
                (second + "/definition/pages/pages.json", b'{"pageOrder":[]}'),
            ]
            for ordered in (parts, list(reversed(parts))):
                with self.assertRaisesRegex(ValueError, "source_path_collision"):
                    F.validate_parts(ordered)
        consistent = [
            ("Report/definition/report.json", b"{}"),
            ("Report/definition/pages/pages.json", b'{"pageOrder":[]}'),
        ]
        self.assertEqual(len(F.validate_parts(consistent)), 2)
        ambiguous = dict(consistent)
        ambiguous["report/definition/pages/Other/page.json"] = b"{}"
        with self.assertRaisesRegex(ValueError, "source_path_collision"):
            C.import_fabric_definition(
                request(),
                fabric_payload(ambiguous),
                self.directory,
                allow_source_read=True,
            )
        self.assertFalse(self.directory.exists())

    def test_default_transport_http_error_status_and_redirect(self):
        class Opener:
            def open(self, request, timeout):
                raise HTTPError(
                    request.full_url,
                    429,
                    "rate limited",
                    {"Retry-After": "3", "Content-Type": "application/json"},
                    io.BytesIO(b"{}"),
                )

        with patch.object(C, "build_opener", return_value=Opener()):
            status, headers, raw = C.default_transport(
                "GET",
                C.POWERBI + "/v1.0/myorg/groups/" + WORKSPACE + "/reports/" + REPORT,
                "source-token",
                None,
                100,
                5,
            )
        self.assertEqual((status, headers["retry-after"], raw), (429, "3", b"{}"))
        with self.assertRaisesRegex(ValueError, "redirect"):
            C.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://attacker.invalid"
            )

    def test_body_bearing_202_is_lro_receipt_not_definition(self):
        self.transport.lro = True
        original = self.transport

        def transport(*args):
            code, headers, raw = original(*args)
            if code == 202 and args[1].startswith(C.FABRIC):
                raw = F.encoded({"status": "Running"})
            return code, headers, raw

        result = self.run_capture(transport=transport)
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        op = next(
            o
            for o in result["capture"]["operations"]
            if o["key"] == "definition.before"
        )
        self.assertEqual(
            F.decode(F.read_pin(self.directory, op["response"])), {"status": "Running"}
        )

    def test_single_visual_bookmark_rejected_page_bookmark_explicit(self):
        req = request()
        req["state"]["bookmark"] = {"name": "BookmarkInitial"}
        with self.assertRaisesRegex(ValueError, "bookmark_not_supported"):
            self.run_capture(req)
        self.assertEqual(self.transport.calls, [])
        req["views"] = [
            {"page_id": "ReportSectionOps", "visual_id": None, "export_png": True}
        ]
        req["queries"] = []
        result = self.run_capture(req)
        self.assertEqual(result["status"], "complete")
        body = next(
            body
            for _, url, _, body in self.transport.calls
            if url.endswith("/ExportTo")
        )
        self.assertEqual(
            body["powerBIReportConfiguration"]["defaultBookmark"],
            {"name": "BookmarkInitial"},
        )
        self.assertEqual(
            result["capture"]["source"]["state_observation"]["status"], "unknown"
        )

    def test_dot_segment_export_id_and_unknown_job_state_never_download(self):
        for mode in ("dot", "unknown"):
            self.directory = self.root / mode
            original = Transport()

            def transport(*args):
                if mode == "dot" and args[1].endswith("/ExportTo"):
                    return reply(
                        {"id": "..", "reportId": REPORT, "status": "NotStarted"}, 202
                    )
                code, headers, raw = original(*args)
                if mode == "unknown" and "/exports/" in args[1]:
                    value = F.decode(raw)
                    value["status"] = "FutureVendorStatus"
                    return reply(value)
                return code, headers, raw

            result = self.run_capture(transport=transport)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(
                any(url.endswith("/file") for _, url, _, _ in original.calls)
            )

    def test_total_attempt_byte_age_and_request_drift_limits(self):
        for key, value in (("max_total_requests", 1), ("max_total_bytes", 10)):
            self.directory = self.root / key
            req = request()
            req[key] = value
            self.assertEqual(self.run_capture(req)["status"], "blocked")
        self.directory = self.root / "age"
        req = request()
        req["max_requests_per_invocation"] = 1
        self.assertEqual(self.run_capture(req)["status"], "partial")
        changed = copy.deepcopy(req)
        changed["state"]["filters"] = []
        with self.assertRaisesRegex(ValueError, "capture_request_changed"):
            self.run_capture(changed, resume=True)
        self.assertEqual(
            self.run_capture(req, resume=True, now=NOW + timedelta(days=2))["status"],
            "blocked",
        )
        self.directory = self.root / "polls"
        self.transport = Transport()
        self.transport.pending_export = True
        req = request()
        req["max_attempts_per_operation"] = 1
        self.assertEqual(self.run_capture(req)["status"], "partial")
        self.assertEqual(
            self.run_capture(req, resume=True, now=NOW + timedelta(seconds=2))[
                "status"
            ],
            "blocked",
        )
        self.assertEqual(self.transport.export_count, 1)

    def test_base64_definition_cannot_hide_injected_token(self):
        original = self.transport

        def transport(*args):
            if args[1].startswith(C.FABRIC):
                parts = definitions()
                parts["definition/report.json"] = F.encoded(
                    {"description": "fabric-synthetic-token"}
                )
                return reply(fabric_payload(parts))
            return original(*args)

        result = self.run_capture(transport=transport)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["capture"]["source"]["definition_files"])
        encoded_secret = base64.b64encode(
            F.encoded({"description": "fabric-synthetic-token"})
        )
        for path in self.directory.iterdir():
            if path.is_file():
                self.assertNotIn(encoded_secret, path.read_bytes())

    def test_real_cli_supplied_import_outputs_existing_private_receipt(self):
        request_path = self.root / "request.json"
        response_path = self.root / "definition.json"
        request_path.write_bytes(F.encoded(request()))
        response_path.write_bytes(F.encoded(fabric_payload()))
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "import-fabric",
                "--request",
                str(request_path),
                "--response",
                str(response_path),
                "--directory",
                str(self.directory),
                "--allow-source-read",
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )
        result = F.decode(completed.stdout)
        self.assertEqual(set(result), {"status", "output"})
        self.assertEqual(result["status"], "partial")
        self.assertEqual(Path(result["output"]).parent, self.directory)
        self.assertTrue(Path(result["output"]).is_file())

    def test_offline_without_service_ids_uses_definition_namespace_live_rejects(self):
        req = request()
        req["workspace_id"] = req["report_id"] = req["dataset_id"] = None
        req["queries"] = []
        result = C.import_fabric_definition(
            req, fabric_payload(), self.directory, allow_source_read=True
        )
        identity = result["capture"]["source"]["identity"]
        self.assertEqual(identity["identity_scope"], "definition_only")
        self.assertEqual(
            identity["namespace"],
            "definition:" + result["capture"]["source"]["definition_fingerprint"],
        )
        self.assertIsNone(identity["workspace_id"])
        with self.assertRaisesRegex(ValueError, "request_identity_rejected"):
            self.run_capture(req)
        self.assertFalse(self.transport.calls)

    def test_omitted_render_is_explicit_partial_even_after_metadata_capture(self):
        req = request()
        req["views"][0]["export_png"] = False
        result = self.run_capture(req)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(
            result["capture"]["captures"][0]["gaps"], ["render_not_requested"]
        )

    def test_query_attachment_preserves_exact_response_bytes_and_decimal_tokens(self):
        raw = b'{ "results": [{"tables": [{"rows": [{"[Available]": 12345678901234567890.123456789}]}]}] }'
        original = self.transport

        def transport(*args):
            if args[1].endswith("/executeQueries"):
                return 200, {"content-type": "application/json"}, raw
            return original(*args)

        result = self.run_capture(transport=transport)
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        record = next(a for a in result["capture"]["attachments"] if a.get("query_id"))
        operation = next(
            o for o in result["capture"]["operations"] if o["key"].startswith("query.")
        )
        self.assertEqual(F.read_pin(self.directory, record), raw)
        self.assertEqual(record["sha256"], operation["response"]["sha256"])


if __name__ == "__main__":
    unittest.main()
