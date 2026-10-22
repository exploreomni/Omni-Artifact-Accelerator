"""Actual Looker capture producer with authored source contracts, no tenant."""

from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit, parse_qs
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/omni-artifact-translator/scripts/looker_capture.py"
spec = importlib.util.spec_from_file_location("looker_capture_test", SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
F = C.F
NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
TOKEN = "synthetic-looker-token"
DID = "inventory::exceptions"


def png():
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x01\x02\x03"))
        + chunk(b"IEND", b"")
    )


def dashboard():
    return {
        "id": DID,
        "title": "Inventory exceptions",
        "query_timezone": "UTC",
        "folder": {"id": "folder1"},
        "dashboard_elements": [
            {
                "id": "tile-kpi",
                "title": "Available",
                "type": "vis",
                "look_id": "look-1",
            },
            {
                "id": "tile-trend",
                "title": "Available",
                "type": "vis",
                "result_maker": {
                    "id": "rm1",
                    "query_id": "q-trend",
                    "filterables": [
                        {
                            "model": "inventory",
                            "view": "stock",
                            "listen": [
                                {"dashboard_filter_name": "Site", "field": "stock.site"}
                            ],
                        }
                    ],
                },
            },
            {
                "id": "tile-table",
                "type": "vis",
                "query_id": "q-table",
                "listen": {"Site": ""},
            },
            {
                "id": "tile-note",
                "type": "text",
                "body_text": "<script>never execute</script>",
                "title": "Notes",
            },
            {
                "id": "tile-merged",
                "type": "vis",
                "result_maker": {"id": "not-merge-id", "merge_result_id": "merge-1"},
                "vis_config": {"type": "custom"},
            },
        ],
        "dashboard_filters": [
            {
                "id": "filter1",
                "name": "Site",
                "type": "field_filter",
                "model": "inventory",
                "explore": "stock",
                "dimension": "stock.site",
                "default_value": "West",
            }
        ],
        "dashboard_layouts": [
            {
                "id": "layout1",
                "dashboard_layout_components": [
                    {
                        "id": "place1",
                        "dashboard_element_id": "tile-kpi",
                        "row": 0,
                        "column": 0,
                        "width": 6,
                        "height": 3,
                    },
                    {
                        "id": "place2",
                        "dashboard_element_id": "tile-kpi",
                        "row": 3,
                        "column": 0,
                        "width": 6,
                        "height": 3,
                    },
                ],
            }
        ],
        "tabs": [{"id": "tab1", "name": "Overview"}, {"id": "tab2", "name": "Details"}],
        "unrecognized_vendor_facet": {"retained": True},
    }


def query(qid):
    return {
        "id": qid,
        "model": "inventory",
        "view": "stock",
        "fields": ["stock.site", "stock.available"],
        "filters": {"stock.site": "West"},
        "limit": "500",
        "query_timezone": "UTC",
        "sorts": ["stock.available desc"],
        "vis_config": {"type": "looker_grid" if qid == "q-table" else "single_value"},
        "pivots": ["stock.site"] if qid == "q-table" else [],
        "dynamic_fields": '[{"table_calculation":"difference","expression":"${stock.available}-1"}]',
        "total": True,
        "row_total": "right",
    }


def request():
    return {
        "schema_version": C.REQUEST,
        "capture_id": "synthetic-looker",
        "source_instance": "https://looker.example.invalid",
        "api_version": "4.0",
        "dashboard_id": DID,
        "principal_ref": "reviewed-viewer",
        "authorization_ref": "synthetic-only",
        "expected_user_id": "user1",
        "evidence_mode": "synthetic_fixture",
        "route": "unselected",
        "route_reference": None,
        "target_surface": "both",
        "views": [
            {"element_id": eid, "tab_id": "tab1", "layout_id": "layout1"}
            for eid in (
                "tile-kpi",
                "tile-trend",
                "tile-table",
                "tile-note",
                "tile-merged",
            )
        ],
        "state": {
            "state_id": "west",
            "filters": {"Site": "West & North"},
            "parameters": {},
            "timezone": "UTC",
            "locale": "en-US",
            "principal": "user1",
            "data_time_policy": "fixture-only",
        },
        "renders": [
            {
                "render_id": "overview",
                "tab_ids": ["tab1"],
                "width": 1280,
                "height": 720,
                "dashboard_style": "tiled",
                "theme": None,
            }
        ],
        "queries": [
            {
                "binding_id": "available",
                "element_id": "tile-kpi",
                "query_id": "q-look",
                "inline_query": None,
                "context_reference": "reviewed query to tile binding",
                "options": {
                    "limit": 500,
                    "cache": True,
                    "cache_only": False,
                    "force_production": True,
                    "server_table_calcs": True,
                },
            }
        ],
        "expected_manifest": {
            "reference": "independent authored fixture denominator",
            "completeness": "selected_dashboard",
            "objects": [
                {"object_id": "/dashboard_elements/0", "kind": "visual"},
                {"object_id": "/dashboard_elements/3", "kind": "content"},
            ],
        },
    }


def reply(value, status=200, headers=None):
    return (
        status,
        {"content-type": "application/json", **(headers or {})},
        F.encoded(value),
    )


class Transport:
    def __init__(self):
        self.calls = []
        self.dashboard_calls = 0
        self.submissions = 0
        self.pending = False
        self.pending_file = False
        self.drift = False
        self.principal = "user1"
        self.result = b'{ "metadata":{"fields":{}}, "rows":[{"stock.available":{"value":12345678901234567890.123456789},"stock.site":{"value":"West"}}] }'

    def __call__(self, method, url, token, body, maximum, timeout):
        self.calls.append((method, url, token, body))
        assert token == TOKEN
        parsed = urlsplit(url)
        assert parsed.netloc == "looker.example.invalid"
        path = unquote(parsed.path)
        assert path.startswith(C.API)
        path = path[len(C.API) :]
        if path == "/user":
            assert parse_qs(parsed.query) == {"fields": ["id"]}
            return reply({"id": self.principal})
        if path == "/dashboards/" + DID:
            self.dashboard_calls += 1
            value = dashboard()
            if self.drift and self.dashboard_calls > 1:
                value["dashboard_elements"][0]["title"] = "changed"
            return reply(value)
        if path == "/looks/look-1":
            return reply(
                {"id": "look-1", "query_id": "q-look", "query": query("q-look")}
            )
        if path.startswith("/queries/") and "/run/" not in path:
            return reply(query(path.rsplit("/", 1)[1]))
        if path == "/merge_queries/merge-1":
            return reply(
                {
                    "id": "merge-1",
                    "source_queries": [
                        {
                            "query_id": "q-merge",
                            "merge_fields": [
                                {
                                    "field_name": "stock.site",
                                    "source_field_name": "stock.site",
                                }
                            ],
                        }
                    ],
                    "result_maker_id": "not-merge-id",
                }
            )
        if path.startswith("/render_tasks/dashboards/"):
            assert method == "POST"
            self.submissions += 1
            return reply(
                {"id": "render1", "status": "enqueued_for_query", "dashboard_id": DID}
            )
        if path == "/render_tasks/render1":
            return reply(
                {
                    "id": "render1",
                    "status": "rendering" if self.pending else "success",
                    "dashboard_id": DID,
                    "user_id": self.principal,
                    "result_format": "png",
                }
            )
        if path == "/render_tasks/render1/results":
            if self.pending_file:
                return 202, {"retry-after": "2"}, b""
            return 200, {"content-type": "image/png"}, png()
        if path.endswith("/run/json_bi") or path == "/queries/run/json_bi":
            return 200, {"content-type": "application/json"}, self.result
        raise AssertionError("unapproved fixture route " + path)


class LookerCapture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / "capture"
        self.transport = Transport()

    def run_capture(self, req=None, **kwargs):
        return C.capture(
            req or request(),
            self.directory,
            token=TOKEN,
            transport=kwargs.pop("transport", self.transport),
            now=kwargs.pop("now", NOW),
            allow_source_read=True,
            allow_source_query=True,
            **kwargs,
        )

    def test_actual_persisted_producer_scope_dependencies_precision_and_no_replay(self):
        result = self.run_capture()
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        value = C.check_capture(result["output"])
        self.assertEqual(value["source"]["dashboard_export"], dashboard())
        self.assertEqual(
            {(d["kind"], d["id"]) for d in value["source"]["dependencies"]},
            {
                ("look", "look-1"),
                ("query", "q-look"),
                ("query", "q-trend"),
                ("query", "q-table"),
                ("query", "q-merge"),
                ("merge_query", "merge-1"),
            },
        )
        self.assertFalse(
            any(
                "merge_queries/not-merge-id" in url
                for _, url, _, _ in self.transport.calls
            )
        )
        record = next(a for a in value["attachments"] if a.get("binding_id"))
        self.assertEqual(F.read_pin(self.directory, record), self.transport.result)
        self.assertEqual(
            record["query_fingerprint"],
            C.sha(C.query_request(value["request"]["queries"][0])),
        )
        self.assertEqual(record["effective_query"], query("q-look"))
        self.assertEqual(record["result_completeness"]["status"], "unknown")
        self.assertEqual(value["source"]["state_observation"], {"status": "unknown"})
        self.assertFalse(value["target_write_authority"])
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertTrue(
            all(p.stat().st_mode & 0o077 == 0 for p in self.directory.iterdir())
        )
        calls = len(self.transport.calls)
        self.assertEqual(self.run_capture(resume=True)["output"], result["output"])
        self.assertEqual(len(self.transport.calls), calls)

    def test_query_options_and_dashboard_filter_encoding(self):
        self.run_capture()
        execution = next(
            url for _, url, _, _ in self.transport.calls if "/run/json_bi" in url
        )
        opts = parse_qs(urlsplit(execution).query)
        self.assertEqual(opts["rebuild_pdts"], ["false"])
        self.assertEqual(opts["apply_formatting"], ["false"])
        self.assertEqual(opts["force_production"], ["true"])
        body = next(
            F.decode(raw)
            for method, url, _, raw in self.transport.calls
            if method == "POST"
        )
        self.assertEqual(
            parse_qs(body["dashboard_filters"]), {"Site": ["West & North"]}
        )
        self.assertEqual(body["tab_ids"], ["tab1"])

    def test_inline_query_reviewed_source_binding_and_exact_body(self):
        req = request()
        q = req["queries"][0]
        q.update(
            query_id=None,
            source_query_id="q-look",
            inline_query={
                "model": "inventory",
                "view": "stock",
                "fields": ["stock.available"],
                "filters": {"stock.site": "East"},
                "filter_config": None,
            },
        )
        result = self.run_capture(req)
        self.assertEqual(result["status"], "complete")
        record = next(
            a for a in result["capture"]["attachments"] if a.get("binding_id")
        )
        self.assertEqual(record["effective_query"], q["inline_query"])
        self.assertEqual(
            record["query_differences"]["filters"]["original"], {"stock.site": "West"}
        )
        call = next(c for c in self.transport.calls if "/queries/run/json_bi" in c[1])
        self.assertEqual(call[0], "POST")
        self.assertEqual(F.decode(call[3]), q["inline_query"])

    def test_grants_origins_and_rebuild_options_fail_before_calls(self):
        with self.assertRaisesRegex(ValueError, "source_query_grant"):
            C.capture(
                request(),
                self.directory,
                token=TOKEN,
                transport=self.transport,
                allow_source_read=True,
            )
        for origin in (
            "http://looker.example.invalid",
            "https://name:secret@looker.example.invalid",
            "https://looker.example.invalid/path",
            "https://looker.example.invalid?x=1",
        ):
            req = request()
            req["source_instance"] = origin
            with self.assertRaises(ValueError):
                self.run_capture(req)
        req = request()
        req["queries"][0]["options"]["rebuild_pdts"] = True
        with self.assertRaisesRegex(ValueError, "query_options"):
            self.run_capture(req)
        self.assertFalse(self.transport.calls)

    def test_opaque_lookml_ids_preserved_dot_segments_and_unrelated_queries_reject(
        self,
    ):
        req = request()
        req["dashboard_id"] = ".."
        with self.assertRaises(ValueError):
            self.run_capture(req)
        req = request()
        req["queries"][0]["query_id"] = "unrelated-query"
        result = self.run_capture(req)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(
            any(
                "/run/" in url or "/render_tasks/" in url
                for _, url, _, _ in self.transport.calls
            )
        )

    def test_pending_render_resume_never_resubmits_and_retains_job(self):
        self.transport.pending = True
        result = self.run_capture()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(self.transport.submissions, 1)
        self.transport.pending = False
        result = self.run_capture(resume=True, now=NOW + timedelta(seconds=5))
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])
        self.assertEqual(self.transport.submissions, 1)

    def test_pending_result_enforces_retry_after(self):
        self.transport.pending_file = True
        self.assertEqual(self.run_capture()["status"], "partial")
        self.transport.pending_file = False
        count = len([c for c in self.transport.calls if c[1].endswith("/results")])
        self.assertEqual(
            self.run_capture(resume=True, now=NOW + timedelta(seconds=1))["status"],
            "partial",
        )
        self.assertEqual(
            len([c for c in self.transport.calls if c[1].endswith("/results")]), count
        )
        self.assertEqual(
            self.run_capture(resume=True, now=NOW + timedelta(seconds=3))["status"],
            "complete",
        )
        self.assertEqual(self.transport.submissions, 1)

    def test_uncertain_post_is_durable_no_replay_or_secret_exception(self):
        original = self.transport

        def transport(*args):
            if args[0] == "POST":
                raise TimeoutError("credential " + TOKEN)
            return original(*args)

        result = self.run_capture(transport=transport)
        self.assertEqual(result["status"], "blocked")
        before = len(original.calls)
        self.assertEqual(self.run_capture(resume=True)["status"], "blocked")
        self.assertEqual(len(original.calls), before)
        for path in self.directory.iterdir():
            self.assertNotIn(TOKEN.encode(), path.read_bytes())
        op = next(o for o in result["capture"]["operations"] if o["method"] == "POST")
        self.assertEqual(op["status"], "ambiguous")

    def test_process_interruption_retains_intent_and_never_resubmits(self):
        original = self.transport

        def transport(*args):
            if args[0] == "POST":
                raise SystemExit("simulated termination after intent")
            return original(*args)

        with self.assertRaises(SystemExit):
            self.run_capture(transport=transport)
        before = C.check_capture(sorted(self.directory.glob("capture-*.json"))[-1])
        self.assertEqual(
            next(o for o in before["operations"] if o["method"] == "POST")["status"],
            "intent",
        )
        result = self.run_capture(resume=True)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.transport.submissions, 0)

    def test_known_layout_or_tab_mismatch_stops_before_execution(self):
        for field in ("layout_id", "tab_id"):
            self.directory = self.root / field
            self.transport = Transport()
            req = request()
            req["views"][0][field] = "not-in-source"
            self.assertEqual(self.run_capture(req)["status"], "blocked")
            self.assertFalse(
                any(
                    "/run/" in url or "/render_tasks/" in url
                    for _, url, _, _ in self.transport.calls
                )
            )

    def test_source_and_principal_drift_block(self):
        self.transport.drift = True
        self.assertEqual(self.run_capture()["status"], "blocked")
        self.directory = self.root / "principal"
        self.transport = Transport()
        self.transport.pending = True
        self.assertEqual(self.run_capture()["status"], "partial")
        self.transport.principal = "other-user"
        self.assertEqual(self.run_capture(resume=True)["status"], "blocked")
        self.assertEqual(self.transport.submissions, 1)

    def test_unknown_task_status_identity_and_expired_result_do_not_resubmit(self):
        for mode in ("unknown", "identity", "expired"):
            self.directory = self.root / mode
            original = Transport()

            def transport(*args):
                path = urlsplit(args[1]).path
                if mode == "expired" and path.endswith("/results"):
                    return reply({"message": "gone"}, 404)
                if path.endswith("/render_tasks/render1"):
                    value = {
                        "id": "render1",
                        "status": "future_vendor_status"
                        if mode == "unknown"
                        else "success",
                        "dashboard_id": "another" if mode == "identity" else DID,
                    }
                    return reply(value)
                return original(*args)

            result = self.run_capture(transport=transport)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(original.submissions, 1)

    def test_throttle_resume_without_automatic_sleep(self):
        original = self.transport
        throttled = []

        def transport(*args):
            if "/dashboards/" in args[1] and not throttled:
                throttled.append(True)
                return reply({"message": "throttle"}, 429, {"retry-after": "5"})
            return original(*args)

        self.assertEqual(self.run_capture(transport=transport)["status"], "partial")
        result = self.run_capture(resume=True, now=NOW + timedelta(seconds=6))
        self.assertEqual(result["status"], "complete", result["capture"]["gaps"])

    def test_finite_request_byte_dependency_age_and_poll_budgets(self):
        for field, limit in (
            ("max_total_requests", 1),
            ("max_total_bytes", 1),
            ("max_dependencies", 1),
        ):
            self.directory = self.root / field
            req = request()
            req[field] = limit
            self.assertEqual(self.run_capture(req)["status"], "blocked")
        self.directory = self.root / "age"
        req = request()
        req["max_requests_per_invocation"] = 2
        self.assertEqual(self.run_capture(req)["status"], "partial")
        self.assertEqual(
            self.run_capture(req, resume=True, now=NOW + timedelta(days=2))["status"],
            "blocked",
        )
        self.directory = self.root / "poll"
        self.transport = Transport()
        self.transport.pending = True
        req = request()
        req["max_attempts_per_operation"] = 1
        self.assertEqual(self.run_capture(req)["status"], "partial")
        self.assertEqual(self.run_capture(req, resume=True)["status"], "blocked")
        self.assertEqual(self.transport.submissions, 1)

    def test_response_credentials_redirect_and_malformed_png_not_retained(self):
        for mode in ("rawtoken", "encodedtoken", "redirect", "badpng", "media"):
            self.directory = self.root / mode
            original = Transport()

            def transport(*args):
                if args[1].endswith("/results"):
                    if mode == "badpng":
                        return (
                            200,
                            {"content-type": "image/png"},
                            b"\x89PNG\r\n\x1a\nBAD",
                        )
                    if mode == "media":
                        return 200, {"content-type": "text/html"}, png()
                if "/dashboards/" in args[1] and args[0] == "GET":
                    if mode == "rawtoken":
                        return reply({"id": DID, "note": TOKEN})
                    if mode == "encodedtoken":
                        raw = (
                            '{"id":"x","note":"'
                            + "".join("\\u%04x" % ord(c) for c in TOKEN)
                            + '"}'
                        ).encode()
                        return 200, {"content-type": "application/json"}, raw
                    if mode == "redirect":
                        return 302, {"location": "https://other.invalid"}, b""
                return original(*args)

            self.assertEqual(self.run_capture(transport=transport)["status"], "blocked")
            self.assertFalse(
                any(p.name.endswith(".png") for p in self.directory.iterdir())
            )
            for path in self.directory.iterdir():
                self.assertNotIn(TOKEN.encode(), path.read_bytes())

    def test_query_error_and_row_limit_remain_partial(self):
        for value in (
            {"errors": [{"message": "truncated"}], "rows": []},
            {"rows": [{}] * 500},
        ):
            self.directory = self.root / ("err" if "errors" in value else "limit")
            self.transport = Transport()
            self.transport.result = F.encoded(value)
            result = self.run_capture()
            self.assertEqual(result["status"], "partial")
            attachment = next(
                a for a in result["capture"]["attachments"] if a.get("binding_id")
            )
            self.assertEqual(attachment["result_completeness"]["status"], "partial")

    def test_documented_json_bi_encoded_rows_and_column_truncation_preserved(self):
        # JsonBi documents rows as string[]; retain the string token unchanged.
        self.transport.result = b'{"metadata":{"columns_truncated":"true"},"rows":["{\\"stock.available\\":12345678901234567890.123456789}"]}'
        result = self.run_capture()
        self.assertEqual(result["status"], "partial")
        record = next(
            a for a in result["capture"]["attachments"] if a.get("binding_id")
        )
        self.assertEqual(F.read_pin(self.directory, record), self.transport.result)
        self.assertIn("columns_truncated", record["result_completeness"]["flags"])

    def test_embedded_metadata_budget_stops_with_readable_diagnostic(self):
        with patch.object(C, "MAX_EMBEDDED_SOURCE_BYTES", 20):
            result = self.run_capture()
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["capture"]["source"]["dashboard_export"])
        C.check_capture(result["output"])
        self.assertFalse(
            any("/render_tasks/" in url for _, url, _, _ in self.transport.calls)
        )

    def test_supplied_api_wrapper_and_lookml_without_service_identity(self):
        wrapper = {
            "schema_version": 1,
            "kind": "looker_dashboard_export",
            "api_version": "4.0.26.20",
            "dashboard": dashboard(),
            "projection": "supplied",
        }
        raw = json.dumps(wrapper, indent=2).encode()
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network forbidden")
        ):
            result = C.import_api(
                request(), raw, self.directory, allow_source_read=True
            )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(
            F.read_pin(self.directory, result["capture"]["source"]["dashboard_file"]),
            raw,
        )
        self.assertEqual(result["capture"]["source"]["dashboard_export"], wrapper)
        source = self.root / "supplied"
        source.mkdir()
        (source / "inventory.dashboard.lookml").write_text(
            "- dashboard: inventory\n  elements:\n  - name: stock\n    model: inventory\n"
        )
        req = request()
        req.update(source_instance=None, dashboard_id=None, renders=[], queries=[])
        output = C.import_local(
            req, source, self.root / "lookml", allow_source_read=True
        )
        self.assertEqual(
            output["capture"]["source"]["identity"]["identity_scope"], "definition_only"
        )
        self.assertTrue(
            output["capture"]["source"]["identity"]["namespace"].startswith(
                "definition:"
            )
        )
        self.assertIsNone(output["capture"]["source"]["dashboard_export"])
        C.check_capture(output["output"])

    def test_supplied_local_symlink_path_alias_and_credential_rejected(self):
        source = self.root / "source"
        source.mkdir()
        (source / "link.lkml").symlink_to(SCRIPT)
        with self.assertRaises(ValueError):
            C.import_local(request(), source, self.directory, allow_source_read=True)
        (source / "link.lkml").unlink()
        (source / "credentials.json").write_text('{"access_token":"do-not-retain"}')
        with self.assertRaises(ValueError):
            C.import_local(request(), source, self.directory, allow_source_read=True)
        self.assertFalse(self.directory.exists())

    def test_changed_bytes_request_and_journal_reject_resume(self):
        self.transport.pending = True
        result = self.run_capture()
        req = request()
        req["state"]["filters"] = {}
        with self.assertRaisesRegex(ValueError, "capture_request_changed"):
            self.run_capture(req, resume=True)
        definition = (
            self.directory / result["capture"]["source"]["dashboard_file"]["path"]
        )
        definition.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "evidence_bytes_changed"):
            self.run_capture(resume=True)

    def test_real_cli_import_and_check(self):
        request_path, response = (
            self.root / "request.json",
            self.root / "dashboard.json",
        )
        request_path.write_bytes(F.encoded(request()))
        response.write_bytes(F.encoded(dashboard()))
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "import-api",
            "--request",
            str(request_path),
            "--response",
            str(response),
            "--directory",
            str(self.directory),
            "--allow-source-read",
        ]
        completed = subprocess.run(command, capture_output=True, timeout=10, check=True)
        value = F.decode(completed.stdout)
        self.assertEqual(set(value), {"status", "output"})
        checked = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "check", "--capture", value["output"]],
            capture_output=True,
            timeout=10,
            check=True,
        )
        self.assertEqual(F.decode(checked.stdout), value)

    def test_default_transport_preserves_http_error_and_uses_token_scheme(self):
        requests = []

        class Opener:
            def open(self, request, timeout):
                requests.append(request)
                raise HTTPError(
                    request.full_url,
                    429,
                    "limited",
                    {
                        "Retry-After": "5",
                        "Content-Type": "application/json",
                        "Content-Length": "2",
                    },
                    io.BytesIO(b"{}"),
                )

        with patch.object(C, "build_opener", return_value=Opener()):
            code, headers, raw = C.default_transport(
                "GET",
                "https://looker.example.invalid/api/4.0/user",
                TOKEN,
                None,
                100,
                5,
            )
        self.assertEqual((code, headers["retry-after"], raw), (429, "5", b"{}"))
        self.assertEqual(requests[0].headers["Authorization"], "token " + TOKEN)
        with self.assertRaisesRegex(ValueError, "redirect"):
            C.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://other.invalid"
            )


if __name__ == "__main__":
    unittest.main()
