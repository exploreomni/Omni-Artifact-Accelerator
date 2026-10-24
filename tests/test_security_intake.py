"""Focused stdlib-only intake regressions; no external producer or YAML imports."""
import copy
import csv
import hashlib
import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/omni-artifact-translator/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location("intake_test_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binding(raw):
    return {"attachment_sha256": hashlib.sha256(raw).hexdigest(),
            **{k: "synthetic" for k in ("capture_content_hash", "page_id", "visual_id",
                "state_sha256", "query_id", "element_id", "binding_id", "query_fingerprint",
                "view_id", "worksheet_id")}}


def profile(headers=("x",)):
    return {"schema_version": 1, "format": "csv", "encoding": "utf-8",
            "subtotal_policy": "preserve", "headers": list(headers),
            "columns": [{"ordinal": i, "name": h, "type": "string", "null_tokens": [],
                         "nullable": False} for i, h in enumerate(headers)]}


class CSVNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.modules = [load(name) for name in ("powerbi_visual", "looker_visual", "tableau_visual")]

    def test_rejects_ragged_row_before_reading_remainder(self):
        raw = b"x\n\n" + b"ignored\n" * 1000
        original = csv.reader
        for module in self.modules:
            with self.subTest(module=module.__name__):
                seen = []
                def counted(*args, **kwargs):
                    for row in original(*args, **kwargs):
                        seen.append(len(row))
                        yield row
                with mock.patch.object(csv, "reader", side_effect=counted):
                    with self.assertRaisesRegex(ValueError, "ragged"):
                        module.normalize_results(raw, profile(), binding(raw))
                self.assertEqual(seen, [1, 0])

    def test_normalization_preserves_quoted_newlines_nulls_locale_and_order(self):
        p = profile(("label", "amount", "when", "optional"))
        p["columns"][1].update(type="number", decimal_separator=",", group_separator=".", percent=False)
        p["columns"][2].update(type="date", date_format="%Y-%m-%d")
        p["columns"][3].update(nullable=True, null_tokens=["NULL"])
        raw = b'\xef\xbb\xbflabel,amount,when,optional\r\n"First,\nline ""quoted""","1.234,50",2026-10-23,NULL\r\nSecond,"-0,25",2026-10-24,value\r\n'
        expected = [{"label": 'First,\nline "quoted"', "amount": "1234.50", "when": "2026-10-23T00:00:00", "optional": None},
                    {"label": "Second", "amount": "-0.25", "when": "2026-10-24T00:00:00", "optional": "value"}]
        for module in self.modules:
            with self.subTest(module=module.__name__):
                value = module.normalize_results(raw, copy.deepcopy(p), binding(raw))
                self.assertEqual(value["rows"], expected)
                self.assertEqual(value["row_count"], 2)
                self.assertEqual(value["parser_profile"], p)
                self.assertEqual(value["completeness"], "not_established")

    def test_duplicate_headers_require_explicit_mapping(self):
        p = profile(("x", "x")); p["columns"][1]["name"] = "other"
        raw = b"x,x\nleft,right\n"
        for module in self.modules:
            with self.subTest(module=module.__name__):
                with self.assertRaisesRegex(ValueError, "duplicate_headers_unresolved"):
                    module.normalize_results(raw, copy.deepcopy(p), binding(raw))
                approved = {**p, "duplicate_header_resolution_reference": "synthetic-reviewed-ordinals"}
                self.assertEqual(module.normalize_results(raw, approved, binding(raw))["rows"],
                                 [{"x": "left", "other": "right"}])

    def test_profile_column_limit_before_reader_is_created(self):
        p = profile(tuple("c" + str(i) for i in range(513)))
        raw = (",".join(p["headers"]) + "\n").encode()
        for module in self.modules:
            with self.subTest(module=module.__name__), mock.patch.object(csv, "reader") as reader:
                with self.assertRaisesRegex(ValueError, "column_limit"):
                    module.normalize_results(raw, p, binding(raw))
                reader.assert_not_called()

    def test_row_cell_column_and_record_limits_stop_iteration(self):
        bounded = load("bounded_csv")
        original = csv.reader
        for key, limit, raw, headers, expected_rows, code in (
                ("MAX_ROWS", 2, b"x\na\nb\nc\nd\n", ["x"], 4, "result_row_limit"),
                ("MAX_CELLS", 3, b"x,y\na,b\nc,d\ne,f\n", ["x", "y"], 3, "cell_limit"),
                ("MAX_COLUMNS", 2, b"x\na,b,c\nlater\n", ["x"], 2, "column_limit")):
            with self.subTest(limit=key):
                seen = []
                def counted(*args, **kwargs):
                    for row in original(*args, **kwargs):
                        seen.append(row)
                        yield row
                with mock.patch.object(bounded, key, limit), mock.patch.object(csv, "reader", side_effect=counted):
                    with self.assertRaisesRegex(ValueError, code):
                        list(bounded.rows(raw, headers, "test"))
                self.assertEqual(len(seen), expected_rows)
        # Single huge physical line is bounded before csv.reader sees it.
        # Quoted multiline records are bounded across physical lines as well.
        for raw in (b'x\n"012345678901234567890"\n', b'x\n"0123456789\n0123456789"\n'):
            with self.subTest(raw=raw), mock.patch.object(bounded, "MAX_RECORD_CHARS", 16):
                with self.assertRaisesRegex(ValueError, "record_limit"):
                    list(bounded.rows(raw, ["x"], "test"))

    def test_actual_row_ceiling_is_incremental(self):
        bounded = load("bounded_csv")
        raw = b"x\n" + b"v\n" * 100005
        original = csv.reader; seen = 0
        def counted(*args, **kwargs):
            nonlocal seen
            for row in original(*args, **kwargs):
                seen += 1
                yield row
        with mock.patch.object(csv, "reader", side_effect=counted):
            with self.assertRaisesRegex(ValueError, "result_row_limit"):
                for _ in bounded.rows(raw, ["x"], "test"):
                    pass
        self.assertEqual(seen, 100002)  # Header + 100,000 valid + first disallowed row.

    def test_header_and_strict_csv_fail_before_later_records(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                raw = b'x\n"unterminated\n'
                with self.assertRaisesRegex(ValueError, "invalid_csv"):
                    module.normalize_results(raw, profile(), binding(raw))
                raw = b"wrong\nignored\n"
                with self.assertRaisesRegex(ValueError, "csv_headers_mismatch"):
                    module.normalize_results(raw, profile(), binding(raw))
                raw = b"x\n"
                self.assertEqual(module.normalize_results(raw, profile(), binding(raw))["rows"], [])

    def test_hex_delegation_preserves_binding_and_early_rejection(self):
        # This imports only repo-owned modules and stdlib. No native/YAML path runs.
        hex_module = load("hex_visual")
        raw = b"x\nvalue\n"
        bind = {"capture_content_hash": "a" * 64, "state_sha256": "b" * 64,
                "attachment_sha256": hashlib.sha256(raw).hexdigest(), "output_id": "synthetic",
                **{key: "11111111-1111-4111-8111-111111111111"
                   for key in ("project_id", "source_version_id", "cell_id")}}
        value = hex_module.normalize_results(raw, profile(), bind)
        self.assertEqual(value["kind"], "hex_normalized_results")
        self.assertEqual(value["binding"], bind)
        self.assertEqual(value["rows"], [{"x": "value"}])
        raw = b"x\n\nignored\n"; bind["attachment_sha256"] = hashlib.sha256(raw).hexdigest()
        original = csv.reader; seen = []
        def counted(*args, **kwargs):
            for row in original(*args, **kwargs):
                seen.append(row)
                yield row
        with mock.patch.object(csv, "reader", side_effect=counted):
            with self.assertRaisesRegex(ValueError, "powerbi.ragged_rows"):
                hex_module.normalize_results(raw, profile(), bind)
        self.assertEqual(len(seen), 2)
        self.assertNotIn("yaml", sys.modules)

    def test_json_normalization_still_preserves_exact_decimals(self):
        raw = b'{"data":[{"x":0.12345678901234567890123456789}]}'
        for module, fmt in zip(self.modules[:2], ("json", "json_bi")):
            p = profile(); p.update(format=fmt, rows_pointer="/data", cell_mode="scalar")
            p["columns"][0].update(type="number", decimal_separator=".", group_separator=None, percent=False)
            with self.subTest(module=module.__name__):
                value = module.normalize_results(raw, p, binding(raw))
                self.assertEqual(value["rows"], [{"x": "0.12345678901234567890123456789"}])
        self.assertNotIn("yaml", sys.modules)


class FileIntakeTests(unittest.TestCase):
    def setUp(self):
        self.files = load("powerbi_capture_files")

    def test_fifo_rejected_without_waiting_for_writer(self):
        if not hasattr(os, "mkfifo") or not hasattr(signal, "setitimer"):
            self.skipTest("POSIX nonblocking descriptor test")
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory).resolve() / "evidence.csv"; os.mkfifo(fifo)
            opened = []; original = os.open
            def tracked(*args, **kwargs):
                fd = original(*args, **kwargs); opened.append(fd); return fd
            previous = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("FIFO blocked")))
            signal.setitimer(signal.ITIMER_REAL, 0.5)
            try:
                with mock.patch.object(os, "open", side_effect=tracked):
                    with self.assertRaisesRegex(self.files.CaptureError, "file_size_or_type"):
                        self.files.read_file(fifo)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])

    def test_regular_file_and_rejected_size_close_descriptors(self):
        original = os.open
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "evidence.csv"; path.write_bytes(b"x\nvalue\n")
            opened = []
            def tracked(*args, **kwargs):
                fd = original(*args, **kwargs); opened.append(fd); return fd
            with mock.patch.object(os, "open", side_effect=tracked):
                self.assertEqual(self.files.read_file(path), b"x\nvalue\n")
                with self.assertRaisesRegex(self.files.CaptureError, "file_size_or_type"):
                    self.files.read_file(path, maximum=1)
            self.assertEqual(len(opened), 2)
            for fd in opened:
                with self.assertRaises(OSError):
                    os.fstat(fd)

    def test_fdopen_failure_releases_original_descriptor(self):
        original = os.open
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "evidence.csv"; path.write_bytes(b"x\n")
            opened = []
            def tracked(*args, **kwargs):
                fd = original(*args, **kwargs); opened.append(fd); return fd
            try:
                with mock.patch.object(os, "open", side_effect=tracked), mock.patch.object(os, "fdopen", side_effect=OSError("synthetic failure")):
                    with self.assertRaisesRegex(OSError, "synthetic failure"):
                        self.files.read_file(path)
                with self.assertRaises(OSError):
                    os.fstat(opened[0])
            finally:
                for fd in opened:
                    try: os.close(fd)
                    except OSError: pass


if __name__ == "__main__":
    unittest.main()
