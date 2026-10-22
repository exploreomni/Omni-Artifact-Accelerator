"""Bounded Hex source intake using synthetic transport; no tenant/source execution."""

import base64
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
from urllib.parse import urlsplit
import zlib

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/omni-artifact-translator/scripts"


def module(name):
    spec = importlib.util.spec_from_file_location(
        "test_hex_" + name, SCRIPTS / (name + ".py")
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C = module("hex_capture")
V = module("hex_visual")
P, VERSION, CELL, INPUT, CODE, NOTE, STATIC, RUN, BUTTON, WRITE, COMPONENT = [
    "20000000-0000-4000-8000-" + str(n).zfill(12) for n in range(1, 12)
]
NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
TOKEN = "synthetic-hex-token"


def native():
    return {
        "schemaVersion": 3,
        "meta": {
            "projectId": P,
            "sourceVersionId": VERSION,
            "title": "Inventory",
            "hexType": "PROJECT",
        },
        "cells": [
            {
                "cellId": CELL,
                "cellType": "CHARTV2",
                "config": {"chartSpec": {"type": "bar", "dataFrame": "inventory"}},
            },
            {
                "cellId": INPUT,
                "cellType": "INPUT",
                "config": {
                    "name": "region",
                    "inputType": "DROPDOWN",
                    "defaultValue": "West",
                },
            },
            {
                "cellId": CODE,
                "cellType": "CODE",
                "config": {
                    "source": 'raise RuntimeError("never execute")',
                    "codeLanguage": "PYTHON",
                },
            },
            {
                "cellId": NOTE,
                "cellType": "MARKDOWN",
                "config": {"source": "# Original context"},
            },
            {
                "cellId": BUTTON,
                "cellType": "INPUT",
                "config": {"name": "run", "inputType": "BUTTON"},
            },
            {
                "cellId": WRITE,
                "cellType": "WRITEBACK",
                "config": {"table": "never_write"},
            },
            {
                "cellId": COMPONENT,
                "cellType": "COMPONENT_IMPORT",
                "config": {"component": {"id": P, "version": VERSION}},
            },
        ],
        "appLayout": {
            "tabs": [
                {
                    "name": "Inventory " + str(n),
                    "rows": [
                        {
                            "columns": [
                                {
                                    "start": 0,
                                    "end": 120,
                                    "elements": [
                                        {"cellId": CELL},
                                        {"cellId": INPUT},
                                        {"cellId": NOTE},
                                        {
                                            "cellId": CODE,
                                            "hideOutput": True,
                                            "showSource": True,
                                        },
                                    ],
                                }
                            ]
                        }
                    ],
                }
                for n in range(7)
            ]
        },
        "sharedFilters": [
            {
                "name": "Site",
                "manualLinks": [
                    {
                        "staticCellId": STATIC,
                        "dataFrame": "inventory",
                        "dataFrameColumn": "site",
                        "isExclude": True,
                    }
                ],
                "autoLinks": [],
            }
        ],
        "dataAppCellIds": [CELL],
        "genAppFiles": [
            {
                "path": "App.js",
                "contents": "if (selected) { /* conditional source retained, never executed */ }",
            }
        ],
    }


def request(images=False):
    return {
        "schema_version": C.REQUEST,
        "capture_id": "inventory",
        "source_origin": "https://hex.synthetic.invalid",
        "workspace_id": "fixture-workspace",
        "principal_ref": "fixture-viewer",
        "authorization_ref": "fixture-read",
        "evidence_mode": "synthetic_fixture",
        "route": "reuse_existing",
        "route_reference": "fixture-model",
        "target_surface": "both",
        "exports": [
            {
                "project_id": P,
                "version": "latest",
                "expected_source_version_id": VERSION,
                "source_path": "inventory.hex.yaml",
            }
        ],
        "outputs": [
            {
                "output_id": "inventory-chart",
                "project_id": P,
                "source_version_id": VERSION,
                "cell_id": CELL,
                "static_id": STATIC,
                "run_id": RUN,
                "source_mode": "published",
                "expected_project_version": "7",
                "identity_reference": "fixture-explicit-cell-static-crosswalk",
            }
        ],
        "images": [
            {
                "output_id": "inventory-chart",
                "width": None,
                "height": None,
                "include_title": False,
            }
        ]
        if images
        else [],
        "state": {
            "state_id": "west",
            "inputs": {"region": "West"},
            "filters": {},
            "timezone": "UTC",
            "locale": "en-US",
            "principal": "fixture-viewer",
            "data_time_policy": "fixture-population",
        },
    }


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
        + chunk(b"IDAT", zlib.compress(b"\0\1\2\3"))
        + chunk(b"IEND", b"")
    )


class Transport:
    def __init__(self, transform=None):
        self.calls = []
        self.transform = transform
        self.exports = 0

    def __call__(self, method, url, token, body, maximum, timeout):
        self.calls.append((method, url, body))
        path = urlsplit(url).path
        if path.endswith("/export"):
            self.exports += 1
            assert method == "POST" and json.loads(body) == {
                "projectId": P,
                "version": "latest",
            }
            value = {
                "filename": "inventory.hex.yaml",
                "content": json.dumps(native(), ensure_ascii=False),
            }
        elif path.endswith("/image"):
            value = {
                "projectId": P,
                "runId": RUN,
                "staticId": STATIC,
                "mimeType": "image/png",
                "imageBase64": base64.b64encode(png()).decode(),
            }
        elif "/runs/" in path:
            value = {
                "projectId": P,
                "runId": RUN,
                "projectVersion": "7",
                "status": "COMPLETED",
                "startTime": "2026-10-21T00:00:00Z",
                "endTime": "2026-10-21T00:00:01Z",
            }
        else:
            value = {
                "id": P,
                "lastEditedAt": "2026-10-20T00:00:00Z",
                "lastPublishedAt": "2026-10-20T00:00:00Z",
            }
        if self.transform:
            result = self.transform(self, method, url, value)
            if result is not None:
                return result
        return 200, {"content-type": "application/json"}, json.dumps(value).encode()


def capture_fixture(directory, supplied_request=None, rest=False):
    directory = Path(directory)
    if rest:
        with patch.object(
            socket.socket, "connect", side_effect=AssertionError("network forbidden")
        ):
            return C.capture(
                supplied_request or request(True),
                directory,
                token=TOKEN,
                transport=Transport(),
                allow_source_read=True,
                now=NOW,
            )
    source = directory.parent / (directory.name + "-source")
    source.mkdir(parents=True)
    (source / "inventory.hex.yaml").write_text(json.dumps(native(), ensure_ascii=False))
    return C.import_local(
        supplied_request or request(), source, directory, allow_source_read=True
    )


class HexCapture(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name).resolve()

    def capture(self, r=None, transport=None, resume=False, now=NOW):
        return C.capture(
            r or request(True),
            self.root / "capture",
            token=TOKEN,
            transport=transport or Transport(),
            allow_source_read=True,
            resume=resume,
            now=now,
        )

    def test_rest_originals_pixels_and_completed_no_replay(self):
        transport = Transport()
        result = self.capture(transport=transport)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(transport.calls), 6)
        value = C.check_capture(result["output"])
        self.assertEqual(
            value["source"]["definition_files"][0]["content_utf8"],
            json.dumps(native(), ensure_ascii=False),
        )
        self.assertEqual(
            (
                Path(result["output"]).parent / value["attachments"][0]["path"]
            ).read_bytes(),
            png(),
        )
        self.capture(transport=transport, resume=True)
        self.assertEqual(len(transport.calls), 6)
        self.assertFalse(value["source_execution"])
        self.assertEqual(value["source"]["state_observation"]["status"], "unknown")
        self.assertTrue(
            all(
                "/runs" not in url or method == "GET"
                for method, url, _ in transport.calls
            )
        )
        self.assertNotIn(TOKEN, Path(result["output"]).read_text())

    def test_timeout_post_is_durable_no_replay(self):
        def fail(t, method, url, value):
            if method == "POST":
                raise TimeoutError("uncertain source read-like POST")

        t = Transport(fail)
        result = self.capture(transport=t)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(t.calls), 2)
        self.capture(transport=t, resume=True)
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(result["capture"]["operations"][-1]["status"], "ambiguous")

    def test_request_budget_resumes_without_replaying_exports(self):
        r = request()
        r["max_requests_per_invocation"] = 1
        t = Transport()
        for _ in range(4):
            result = self.capture(r, t, resume=bool(t.calls))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(t.calls), 4)
        self.assertEqual(t.exports, 2)

    def test_throttle_wait_and_attempt_bound(self):
        def fail(t, method, url, value):
            return 429, {"retry-after": "2"}, b"{}"

        r = request()
        r["max_attempts_per_operation"] = 1
        t = Transport(fail)
        self.assertEqual(self.capture(r, t)["status"], "partial")
        self.capture(r, t, resume=True, now=NOW + timedelta(seconds=1))
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(
            self.capture(r, t, resume=True, now=NOW + timedelta(seconds=3))["status"],
            "blocked",
        )
        self.assertEqual(len(t.calls), 1)

    def test_run_identity_and_source_drift_fail_closed(self):
        for key, changed in [
            ("runId", P),
            ("projectVersion", "8"),
            ("status", "RUNNING"),
        ]:
            with self.subTest(key=key):

                def mutate(t, method, url, value):
                    if "/runs/" in url and "/image?" not in url:
                        value[key] = changed

                result = C.capture(
                    request(True),
                    self.root / key,
                    token=TOKEN,
                    transport=Transport(mutate),
                    allow_source_read=True,
                    now=NOW,
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["capture"]["attachments"], [])

        def drift(t, method, url, value):
            if method == "POST" and t.exports == 2:
                value["content"] += "\n"

        result = self.capture(request(), Transport(drift))
        self.assertEqual(result["status"], "blocked")
        C.check_capture(result["output"])

    def test_bad_png_media_redirect_and_echo_never_persist(self):
        cases = [
            (
                "png",
                lambda v: v.update(imageBase64=base64.b64encode(b"bad png").decode()),
            ),
            ("identity", lambda v: v.update(staticId=CELL)),
        ]
        for label, change in cases:

            def bad(t, method, url, value):
                if "/image?" in url:
                    change(value)

            result = C.capture(
                request(True),
                self.root / label,
                token=TOKEN,
                transport=Transport(bad),
                allow_source_read=True,
                now=NOW,
            )
            self.assertEqual(result["status"], "blocked")
        for n, reply in enumerate(
            [
                (302, {"location": "https://evil.invalid"}, b"{}"),
                (200, {"content-type": "text/html"}, b"{}"),
                (
                    200,
                    {"content-type": "application/json"},
                    json.dumps({"echo": TOKEN}).encode(),
                ),
            ]
        ):
            result = C.capture(
                request(),
                self.root / str(n),
                token=TOKEN,
                transport=lambda *args: reply,
                allow_source_read=True,
                now=NOW,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertNotIn(TOKEN, Path(result["output"]).read_text())

    def test_grant_url_token_and_schema_rejections(self):
        with self.assertRaises(ValueError):
            C.capture(request(), self.root / "no", token=TOKEN)
        for origin in [
            "http://hex.invalid",
            "https://hex.invalid/path",
            "https://u:p@hex.invalid",
            "https://hex.invalid?x=1",
        ]:
            r = request()
            r["source_origin"] = origin
            with self.assertRaises(ValueError):
                C.validate_request(r)
        for raw in [
            b"schemaVersion: 3\nschemaVersion: 3\nmeta: {}",
            b"schemaVersion: 3\nmeta: &x {}\ncells: *x",
            b"!!python/object:evil {}",
        ]:
            with self.assertRaises(ValueError):
                C.read_native(raw)
        n = native()
        n["genAppFiles"][0]["path"] = "../escape"
        with self.assertRaises(ValueError):
            C.read_native(json.dumps(n).encode())
        n = native()
        n["projectAssets"] = {
            "envVars": [{"name": "API_TOKEN", "value": "never-retain"}]
        }
        with self.assertRaises(ValueError):
            C.read_native(json.dumps(n).encode())

    def test_offline_null_identity_and_symlink(self):
        source = self.root / "source"
        source.mkdir()
        n = native()
        n["meta"].pop("projectId")
        n["meta"].pop("sourceVersionId")
        (source / "inventory.hex.yaml").write_text(json.dumps(n))
        r = request()
        r["exports"][0].update(project_id=None, expected_source_version_id=None)
        r["outputs"] = []
        result = C.import_local(
            r, source, self.root / "capture", allow_source_read=True
        )
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["capture"]["source"]["projects"][0]["project_id"])
        C.check_capture(result["output"])
        (source / "alias").symlink_to(source / "inventory.hex.yaml")
        with self.assertRaises(ValueError):
            C.import_local(r, source, self.root / "other", allow_source_read=True)

    def test_imported_mcp_actual_pixels_and_journal_chain(self):
        r = request()
        r["outputs"][0]["source_mode"] = "draft"
        result = capture_fixture(self.root / "capture", r)
        supplied = self.root / "supplied"
        supplied.mkdir()
        (supplied / "mcp.json").write_text(
            json.dumps(
                {
                    "content": [
                        {
                            "type": "image",
                            "mimeType": "image/png",
                            "data": base64.b64encode(png()).decode(),
                        }
                    ]
                }
            )
        )
        spec = {
            "schema_version": 1,
            "kind": "hex_evidence_import",
            "capture_content_hash": result["capture"]["content_hash"],
            "attachments": [
                {
                    "output_id": "inventory-chart",
                    "path": "mcp.json",
                    "format": "mcp-image",
                    "provenance_reference": "fixture-call-receipt",
                    "result_completeness": {
                        "status": "unknown",
                        "reference": None,
                        "flags": [],
                    },
                }
            ],
            "state_observations": [],
            "render_state_observations": [],
        }
        updated = C.import_evidence(result["output"], spec, supplied)
        self.assertEqual(
            updated["capture"]["previous_content_hash"],
            result["capture"]["content_hash"],
        )
        C.load_latest(self.root / "capture")
        with self.assertRaises(ValueError):
            C.import_evidence(result["output"], spec, supplied)
        attachment = updated["capture"]["attachments"][0]
        (self.root / "capture" / attachment["path"]).write_bytes(b"bad")
        with self.assertRaises(ValueError):
            C.check_capture(updated["output"])

    def test_default_transport_http_errors_bounds_and_no_redirect(self):
        error = HTTPError(
            "https://hex.synthetic.invalid/api/v1/projects/export",
            429,
            "throttled",
            {
                "content-type": "application/json",
                "retry-after": "1",
                "content-length": "2",
            },
            io.BytesIO(b"{}"),
        )

        class Opener:
            def open(self, req, timeout):
                self.req = req
                raise error

        opener = Opener()
        with patch.object(C, "build_opener", return_value=opener):
            status, headers, raw = C.default_transport(
                "POST",
                "https://hex.synthetic.invalid/api/v1/projects/export",
                TOKEN,
                b"{}",
                2,
                1,
            )
        self.assertEqual((status, raw), (429, b"{}"))
        self.assertEqual(opener.req.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(headers["retry-after"], "1")
        with self.assertRaisesRegex(ValueError, "redirect_rejected"):
            C.NoRedirect().redirect_request(
                None, None, 302, None, {}, "https://elsewhere.invalid"
            )

        class Response:
            status = 200
            headers = {"content-length": "9", "content-type": "application/json"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self, maximum):
                return b"{}"

        with patch.object(C, "build_opener") as build:
            build.return_value.open.return_value = Response()
            with self.assertRaisesRegex(ValueError, "incomplete_response"):
                C.default_transport(
                    "GET",
                    "https://hex.synthetic.invalid/api/v1/projects/" + P,
                    TOKEN,
                    None,
                    10,
                    1,
                )
            with self.assertRaisesRegex(ValueError, "response_size_limit"):
                C.default_transport(
                    "GET",
                    "https://hex.synthetic.invalid/api/v1/projects/" + P,
                    TOKEN,
                    None,
                    1,
                    1,
                )

    def test_evidence_invalid_batch_leaves_no_partial_write(self):
        result = capture_fixture(self.root / "capture")
        source = self.root / "evidence"
        source.mkdir()
        (source / "data.csv").write_bytes(b"a,b\nx,0\n")
        spec = {
            "schema_version": 1,
            "kind": "hex_evidence_import",
            "capture_content_hash": result["capture"]["content_hash"],
            "attachments": [
                {
                    "output_id": "inventory-chart",
                    "path": "data.csv",
                    "format": "csv",
                    "provenance_reference": "fixture-transfer",
                    "result_completeness": {
                        "status": "complete",
                        "reference": None,
                        "flags": [],
                    },
                }
            ],
            "state_observations": [],
            "render_state_observations": [],
        }
        before = {p.name for p in (self.root / "capture").iterdir()}
        with self.assertRaisesRegex(ValueError, "result_completeness"):
            C.import_evidence(result["output"], spec, source)
        after = {p.name for p in (self.root / "capture").iterdir()}
        self.assertEqual(after - before, {".lock"})
        C.load_latest(self.root / "capture")

    def test_cli_actual_offline_intake(self):
        source = self.root / "source"
        source.mkdir()
        (source / "inventory.hex.yaml").write_text(json.dumps(native()))
        request_path = self.root / "request.json"
        request_path.write_text(json.dumps(request()))
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS / "hex_capture.py"),
                "import-local",
                "--request",
                str(request_path),
                "--source-root",
                str(source),
                "--directory",
                str(self.root / "capture"),
                "--allow-source-read",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        C.check_capture(json.loads(proc.stdout)["output"])


if __name__ == "__main__":
    unittest.main()
