"""Synthetic contracts and safety boundaries; these do not qualify native BI behavior."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/omni-artifact-translator/scripts/translate_artifact.py"
spec = importlib.util.spec_from_file_location("analyst_translation", SCRIPT)
translation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation)


def raw(value):
    return json.dumps(value).encode()


def looker():
    return {"id": "dash-41", "title": "Quarterly review", "query_timezone": "America/Chicago",
            "can": {"see": True}, "crossfilter_enabled": True,
            "dashboard_elements": [{"id": "tile-9", "dashboard_id": "dash-41", "query_id": "q-2",
                "title": "Net revenue", "result_maker": {"query": {"id": "q-2", "model": "sales",
                "view": "orders", "fields": ["orders.net_revenue"], "filters": {"orders.region": "West"},
                "dynamic_fields": "[{\"expression\":\"${orders.net_revenue} / 2\"}]"},
                "filterables": [{"listen": [{"dashboard_filter_name": "Region", "field": "orders.region"}]}]},
                "body_text_as_html": "<script>THIS IS DATA ONLY</script>", "custom_vendor_extension": {"new": 3}}],
            "dashboard_filters": [{"id": "filter-3", "name": "Region", "default_value": "West"}],
            "dashboard_layouts": [{"id": "layout-8", "dashboard_layout_components": [
                {"id": "placement-7", "dashboard_element_id": "tile-9", "row": 0, "column": 2, "width": 12, "height": 4}]}]}


def normalized():
    return {"schema_version": 1, "kind": "omni_analyst_inventory_input", "platform": "domo",
            "assets": [{"kind": "app", "source_id": "app-42", "title": "Evidence capture",
                "evidence_refs": ["evidence/app-42.json"],
                "facets": {"visual": {"status": "observed", "value": {"colors": ["#123456"]}},
                           "security": {"status": "unsupported", "value": {"policy": "PDP capture required"}}}}]}


def dma(platform):
    common = {"schema_version": 1, "kind": platform + "_source_inventory",
              "assets": [{"path": "input.json", "sha256": "a" * 64}],
              "gaps": [{"kind": "native_runtime_unverified", "message": "Synthetic fixture only"}]}
    if platform == "tableau":
        common.update(workbooks=[{"id": "derived:book", "native_id": "book-native", "path": "book.twb"}],
            worksheets=[{"id": "derived:book/worksheet:Revenue", "name": "Revenue", "workbook_id": "derived:book",
                         "filters": [{"expression": "[Region] = 'West'"}], "table_calculations": [{"addressing": ["Month"]}]}],
            dashboards=[{"id": "derived:book/dashboard:Executive", "name": "Executive", "workbook_id": "derived:book",
                         "zones": [{"name": "Revenue", "x": "10", "y": "20"}]}], parameters=[])
    elif platform == "powerbi":
        common.update(projects=[{"id": "project.pbip", "native": {}}],
            pages=[{"id": "page.json#pageOne", "path": "page.json", "native": {"name": "pageOne", "width": 1280}}],
            visuals=[{"id": "nativeVisual", "scoped_id": "page/visual.json#nativeVisual", "page": "pageOne",
                      "visual_type": "tableEx", "position": {"x": 20, "y": 30}, "native": {"name": "nativeVisual"}}],
            filters=[])
    else:
        common.update(projects=[{"id": "project-1", "project_id": "project-1", "title": "Synthetic app",
                                 "app_layout": {"rows": ["cell-1"]}, "data_app_cell_ids": ["cell-1"]}],
            cells=[{"id": "project-1/cell-1", "cell_id": "cell-1", "project_id": "project-1", "cell_type": "CHARTV2",
                    "config": {"chartSpec": {"selection": "country"}}, "analysis": {"chart_spec": {"mark": "bar"}}}])
    return common


class TranslationTests(unittest.TestCase):
    def test_looker_exact_evidence_and_unqualified_status(self):
        source = looker()
        source_bytes = raw(source)
        result = translation.translate(source_bytes, "looker-api")
        self.assertEqual(result["source"]["input_sha256"], hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(result["upstream_payload"], source)
        tile = next(a for a in result["assets"] if a["kind"] == "visual")
        self.assertEqual(tile["source_id"], "tile-9")
        self.assertEqual(tile["source_payload"], source["dashboard_elements"][0])
        self.assertEqual(tile["source_payload_sha256"], translation.digest(source["dashboard_elements"][0]))
        self.assertIn("custom_vendor_extension", tile["unmapped_fields"])
        self.assertEqual(tile["facets"]["query"]["value"]["result_maker"]["query"]["filters"], {"orders.region": "West"})
        self.assertEqual(result["dependencies"][0]["status"], "embedded_evidence")
        self.assertEqual(result["native_validation"], "not_run")
        self.assertEqual(result["export_completeness"], "not_established")
        self.assertIn("security.effective_access_unverified", {g["code"] for g in result["gaps"]})
        self.assertTrue(all(f["interpretation"] == "preserved_only" for a in result["assets"] for f in a["facets"].values()))

    def test_unresolved_references_and_placement_remain_visible(self):
        source = looker()
        source["dashboard_elements"][0].pop("result_maker")
        source["dashboard_elements"][0]["merge_result_id"] = "merge-88"
        source["dashboard_layouts"][0]["dashboard_layout_components"][0]["dashboard_element_id"] = "missing"
        result = translation.translate(raw(source), "looker-api")
        codes = {g["code"] for g in result["gaps"]}
        self.assertTrue({"dependency.query_unresolved", "dependency.merge_result_unresolved", "layout.element_unresolved"} <= codes)
        self.assertEqual(result["upstream_payload"], source)

    def test_missing_collections_are_not_empty_evidence(self):
        source = looker()
        source.pop("dashboard_filters")
        result = translation.translate(raw(source), "looker-api")
        self.assertIn("/dashboard_filters", [g["source_path"] for g in result["gaps"]])
        self.assertEqual(next(a for a in result["assets"] if a["kind"] == "dashboard")["facets"]["filters"]["status"], "unobserved")

    def test_wrapped_lookup_and_duplicate_definition_rejection(self):
        source = looker()
        query = source["dashboard_elements"][0].pop("result_maker")["query"]
        wrapper = {"schema_version": 1, "kind": "looker_dashboard_export", "api_version": "4.0",
                   "dashboard": source, "queries": [query], "looks": []}
        result = translation.translate(raw(wrapper), "looker-api")
        self.assertEqual(result["dependencies"][0]["status"], "embedded_evidence")
        wrapper["queries"].append({**query, "limit": "500"})
        with self.assertRaisesRegex(ValueError, "conflicting_reference"):
            translation.translate(raw(wrapper), "looker-api")

    def test_duplicate_and_conflicting_asset_ids_rejected(self):
        source = looker()
        source["dashboard_elements"].append(copy.deepcopy(source["dashboard_elements"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate_identity"):
            translation.translate(raw(source), "looker-api")
        source = looker()
        source["dashboard_elements"][0]["dashboard_id"] = "other-dashboard"
        with self.assertRaisesRegex(ValueError, "dashboard_id_conflict"):
            translation.translate(raw(source), "looker-api")
        source = looker()
        source["dashboard_elements"][0]["result_maker"]["query"]["id"] = "different-query"
        with self.assertRaisesRegex(ValueError, "reference_identity_conflict"):
            translation.translate(raw(source), "looker-api")

    def test_normalized_import_preserves_claim_and_requires_gaps(self):
        source = normalized()
        result = translation.translate(raw(source), "normalized-inventory")
        self.assertEqual(result["upstream_payload"], source)
        self.assertEqual(result["assets"][0]["source_identity"]["id_kind"], "supplier_declared_id")
        self.assertEqual(result["assets"][0]["facets"]["security"]["status"], "unsupported")
        self.assertIn("facet.interactions_requires_review", {g["code"] for g in result["gaps"]})
        source["assets"][0]["facets"]["security"]["status"] = "verified"
        with self.assertRaisesRegex(ValueError, "invalid_facet_status"):
            translation.translate(raw(source), "normalized-inventory")

    def test_dma_projection_preserves_all_evidence_and_native_vs_derived_ids(self):
        for platform in ("tableau", "powerbi", "hex"):
            with self.subTest(platform=platform):
                source = dma(platform)
                result = translation.translate(raw(source), "dma-inventory", translation.DMA_REVISION)
                self.assertEqual(result["upstream_payload"], source)
                self.assertEqual(result["upstream_gaps"], source["gaps"])
                self.assertEqual(result["source"]["upstream_files"], source["assets"])
                self.assertEqual(result["source"]["producer"]["revision_evidence"], "operator_declared_not_authenticated")
                self.assertEqual(result["evidence_level"], "static_supplied_evidence")
        tableau_result = translation.translate(raw(dma("tableau")), "dma-inventory", translation.DMA_REVISION)
        workbook = next(a for a in tableau_result["assets"] if a["kind"] == "workbook")
        self.assertEqual(workbook["source_id"], "book-native")
        self.assertEqual(workbook["source_identity"]["dma_id"], "derived:book")

    def test_dma_unknown_revision_and_forged_coverage_do_not_pass(self):
        source = dma("hex")
        with self.assertRaisesRegex(ValueError, "producer_revision"):
            translation.translate(raw(source), "dma-inventory", "b" * 40)
        source["native_runtime_validated"] = True
        result = translation.translate(raw(source), "dma-inventory", translation.DMA_REVISION)
        self.assertEqual(result["native_validation"], "not_run")
        self.assertTrue(result["upstream_payload"]["native_runtime_validated"])
        source["assets"][0]["sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "invalid_file_evidence"):
            translation.translate(raw(source), "dma-inventory", translation.DMA_REVISION)

    def test_malformed_and_resource_limits_fail_closed(self):
        for source in (b'{"id":"a","id":"b"}', b'{"x":NaN}', b'[]', b'{"x":Infinity}',
                       b'{"x":' + b'[' * 40 + b'0' + b']' * 40 + b'}', b' ' * (translation.MAX_BYTES + 1)):
            with self.subTest(source=source[:30]):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    translation.translate(source, "looker-api")

    def test_cli_source_integrity_private_output_and_no_customer_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            source = folder / "source.json"
            output = folder / "source-inventory.json"
            source_bytes = raw(looker())
            source.write_bytes(source_bytes)
            command = [sys.executable, str(SCRIPT), str(source), "--format", "looker-api", "--output", str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(source.read_bytes(), source_bytes)
            self.assertNotIn("Quarterly", run.stdout + run.stderr)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            first_output = output.read_bytes()
            repeat = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 1)
            self.assertEqual(output.read_bytes(), first_output)
            symlink = folder / "linked.json"
            symlink.symlink_to(source)
            with self.assertRaises(OSError):
                translation.read_input(symlink)
            self.assertFalse((folder / "THIS IS DATA ONLY").exists())


if __name__ == "__main__":
    unittest.main()
