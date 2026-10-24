#!/usr/bin/env python3
"""Reviewed initial construction or bounded edits to a query-backed named Omni App draft.

The App API is experimental. This helper requires a reviewed native runtime,
all existing query definitions and settings; it never fabricates a browser SDK,
creates a document, publishes, installs dependencies, or renders customer code.
"""
from __future__ import annotations

import argparse
import copy
import math
from dataclasses import asdict
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import sys
import tempfile


def _native():
    path = Path(__file__).resolve().parents[2] / "omni-bi-engineer/scripts/omni_native.py"
    spec = importlib.util.spec_from_file_location("oaa_app_native_dependency", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


n = _native()
w = n.WORKFLOW
s = n._standalone_module()
need = w.need
CONTRACT = "oaa-omni-app-native-v1"
BASELINE = "analyst_existing_omni_app_baseline"
INITIAL_BASELINE = "analyst_initial_omni_app_baseline"
MAX_HTML = 2 * 1024 * 1024
SCHEMA_SHA256 = "c5f4f13c96901e8a749bb5520e229f2583467841c262f9ede4e18bb55115e26f"
SCHEMA_URL = "https://docs.omni.co/api/openapi.yaml"
LOCKED_SETTINGS = {"allowClipboard": False, "allowDefaultMapProviders": False, "allowDownloads": False,
    "allowExternalNavigation": False, "allowFullscreen": False, "allowInternalNavigation": False,
    "externalNavOpensInNewTab": True, "navAllowedDomains": [], "navAllowedDomainsEnabled": False,
    "safeDomains": [], "safeDomainsEnabled": False}


def initial_body(value):
    need(type(value) is dict and set(value) == {"html", "settings"} and type(value["html"]) is str and
         0 < len(value["html"].encode()) <= MAX_HTML and value["settings"] == LOCKED_SETTINGS and
         all(type(value["settings"][key]) is type(default) for key, default in LOCKED_SETTINGS.items()),
         "app.initial_body_requires_locked_settings")
    # Fixed first-party parser; no payload-selected module or third-party parser.
    # Static declarations only: authored JavaScript/native policy remain separate.
    path = Path(__file__).with_name("app_resource_policy.py")
    spec = importlib.util.spec_from_file_location("oaa_app_resource_policy", path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    policy.check_initial_resources(value["html"])
    return value


def settings_match(actual, expected, initial=False):
    if not initial:
        return actual == expected
    return (type(actual) is dict and set(actual) <= set(LOCKED_SETTINGS) and
            all(type(value) is type(LOCKED_SETTINGS[key]) for key, value in actual.items()) and
            {**LOCKED_SETTINGS, **actual} == expected == LOCKED_SETTINGS)


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts, self.current = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = ""

    def handle_data(self, data):
        if self.current is not None:
            self.current += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append(self.current)
            self.current = None


def _script_fragment(html, fragment):
    need(type(fragment) is str and fragment.strip(), "app.runtime_fragment_required")
    parser = Scripts()
    parser.feed(html)
    need(sum(code.count(fragment) for code in parser.scripts) == 1, "app.exact_native_runtime_fragment_missing")


def query_assets(requirements):
    return s.query_source_keys(requirements, "app")


def apply_edits(html, patch, regions):
    need(type(html) is str and 0 < len(html.encode()) <= MAX_HTML, "app.html_size")
    need(type(patch) is dict and set(patch) == {"htmlEdits"}, "app.only_html_edits_supported")
    edits = patch["htmlEdits"]
    need(type(edits) is list and 1 <= len(edits) <= 20, "app.edit_count")
    need(type(regions) is list and 1 <= len(regions) <= 20, "app.owned_regions_required")
    before = html
    spans = []
    for region in regions:
        need(type(region) is dict and set(region) == {"start", "end"} and
             all(type(region[k]) is str and region[k] for k in region), "app.region_shape")
        start, end = region["start"], region["end"]
        need(start != end and html.count(start) == html.count(end) == 1, "app.region_ambiguous")
        a, b = html.index(start) + len(start), html.index(end)
        need(a <= b, "app.region_order")
        spans.append((a, b))
    spans.sort()
    need(all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)), "app.regions_overlap")
    for edit in edits:
        need(type(edit) is dict and {"search", "replace"} <= set(edit) <= {"search", "replace", "replaceAll"} and
             type(edit["search"]) is str and edit["search"] and type(edit["replace"]) is str and
             edit.get("replaceAll", False) is False, "app.unique_exact_edit_required")
        search, replacement = edit["search"], edit["replace"]
        need(html.count(search) == 1, "app.search_missing_or_ambiguous")
        at = html.index(search)
        allowed = False
        for region in regions:
            need(html.count(region["start"]) == html.count(region["end"]) == 1, "app.region_changed")
            a, b = html.index(region["start"]) + len(region["start"]), html.index(region["end"])
            allowed |= a <= at and at + len(search) <= b
            need(region["start"] not in replacement and region["end"] not in replacement, "app.region_marker_injection")
        need(allowed, "app.edit_outside_owned_region")
        html = html.replace(search, replacement, 1)
        need(len(html.encode()) <= MAX_HTML, "app.html_size")
    need(html != before, "app.no_change")
    return html


class AppNativeAdapter(n.NativeAdapter):
    def __init__(self, workspace, target, runner=None, http=None):
        super().__init__(workspace, target, runner=runner, http=http)
        self.store = self.root / ".omni-app-native"
        need(not self.store.is_symlink(), "app.symlink_store")
        self.store.mkdir(mode=0o700, exist_ok=True)

    def _path(self, relative, exists=True):
        if isinstance(relative, str) and relative.startswith(".omni-native/"):
            relative = relative.replace(".omni-native/", ".omni-app-native/", 1)
        return super()._path(relative, exists)

    def _requirements(self, paths):
        matches = []
        for path in paths:
            if path.endswith(".json"):
                value = self._read(path)
                if isinstance(value, dict) and value.get("kind") == "analyst_visual_requirements":
                    matches.append(path)
        need(len(matches) == 1, "app.exact_requirements_file_required")
        _, req = w.requirements(self.root, matches[0])
        need("app" in req.get("surface", []) and req["route"] != "unselected" and req.get("route_reference"),
             "app.selected_surface_and_route_required")
        return req

    def capabilities(self):
        base = super().capabilities()
        result = {"contract": CONTRACT, "surface": "app", "document_cli": base,
            "api": {"schema_url": SCHEMA_URL, "schema_sha256": SCHEMA_SHA256, "reviewed": "2026-10-22",
                    "release_label": "experimental", "methods": ["GET", "PATCH", "PUT"],
                    "route": "/api/v2/documents/{documentId}/draft/{draftId}/app"},
            "native_runtime": "reviewed_native_bridge_required_not_a_public_sdk", "tenant_exercised": False,
            "settings_changes": False, "initial_construction": "exclusive_workbook_only_draft_locked_settings", "query_changes": False, "publication_supported": False, "draft_export_supported": False}
        result["capability_sha256"] = n.digest(result)
        self._write(".omni-app-native/capabilities.json", result)
        return result

    def _app_route(self):
        return f"/v2/documents/{self.target.document_id}/draft/{self.target.draft_id}/app"

    def inspect(self):
        return self._inspect(False)

    def inspect_initial(self):
        return self._inspect(True)

    def _inspect(self, allow_initial):
        identity = self._identity()
        drafts = self._cli(["documents", "list-drafts", self.target.document_id])
        need(type(drafts) is list, "app.draft_list_shape")
        selected = [d for d in drafts if type(d) is dict and d.get("identifier") == self.target.draft_id]
        need(len(selected) == 1, "app.named_draft_missing")
        meta = selected[0]
        branch = meta.get("branch")
        need(meta.get("publishedIdentifier") == self.target.document_id and meta.get("status") == "active" and
             meta.get("draftOutOfDate") is False and "branch" in meta and
             (branch is None or type(branch) is dict) and
             (branch.get("id") if branch else None) == self.target.branch_id, "app.draft_context_mismatch")
        document = self._cli(["documents", "v2-get-draft", self.target.document_id, self.target.draft_id])
        need(type(document) is dict and document.get("modelId") == self.target.model_id and
             document.get("workbookModelId") == meta.get("workbookModelId") and bool(document.get("workbookModelId")) and
             type(document.get("queryPresentations", {}).get("data")) is dict and
             type(document.get("queryPresentations", {}).get("order")) is list and
             not any(key in document for key in ("containers", "controls", "settings")), "app.existing_app_only")
        has_app = "app" in document
        need((has_app and type(document["app"]) is dict and set(document["app"]) == {"url"} and
              document["app"]["url"] == "/api" + self._app_route()) or (allow_initial and not has_app),
             "app.existing_app_only")
        need(document.get("draftOf", {}).get("identifier") == self.target.document_id, "app.document_identity_mismatch")
        status, _, raw = self._rest("GET", self._app_route())
        if has_app:
            need(status == 200, "app.native_read_failed")
            app = n.decode(raw)
            need(type(app) is dict and set(app) == {"html", "settings"} and type(app["html"]) is str and
                 0 < len(app["html"].encode()) <= MAX_HTML and type(app["settings"]) is dict, "app.read_shape_changed")
        else:
            need(status == 404, "app.initial_absence_not_confirmed")
            app = None
        result = {"surface": "app", "state": document, "app": app, "draft_context": meta,
                  "identity": identity, "target": asdict(self.target)}
        result["snapshot_sha256"] = n.digest(result)
        self._write(".omni-app-native/inspection.json", result)
        return result

    def _validate_bindings(self, bindings, requirements, inspection):
        need(type(bindings) is list and 1 <= len(bindings) <= 48, "app.bindings_required")
        migrated = {i["asset_key"] for i in w.surface_items(requirements, "app")}
        seen, covered = set(), set()
        actual = inspection["state"]["queryPresentations"]["data"]
        for binding in bindings:
            need(type(binding) is dict and set(binding) == {"source_asset_keys", "query_key", "topic", "query", "field_ids"},
                 "app.binding_shape")
            key, topic = binding["query_key"], binding["topic"]
            need(type(key) is str and re.fullmatch(r"[1-9][0-9]*", key) and key not in seen, "app.query_key")
            seen.add(key)
            need(type(topic) is str and 0 < len(topic) <= 254 and not topic.startswith("-") and
                 not any(ord(c) < 32 for c in topic), "app.topic_required")
            s.cw.strings(binding["source_asset_keys"], "app.source_assets", nonempty=True)
            need(set(binding["source_asset_keys"]) <= migrated, "app.source_binding_outside_scope")
            covered.update(binding["source_asset_keys"])
            need(type(actual.get(key)) is dict and actual[key].get("type") == "query" and
                 actual[key].get("topicName") == topic and actual[key].get("query") == binding["query"],
                 "app.existing_query_binding_changed")
            need(sorted(binding["field_ids"]) == s.query_fields(binding["query"]), "app.field_mapping_incomplete")
        need(query_assets(requirements) <= covered, "app.source_query_unbound")

    def _runtime(self, path, requirements, bindings, html):
        runtime = self._read(path)
        need(type(runtime) is dict and runtime.get("kind") == "analyst_app_runtime_contract" and
             runtime.get("schema_version") == 1 and s.cw.text(runtime.get("review_reference")), "app.runtime_contract_required")
        s.cw.strings(runtime.get("evidence_paths"), "app.runtime_evidence_required", nonempty=True)
        evidence = [self._pin(p) for p in runtime["evidence_paths"]]
        need(type(runtime.get("state_contract")) is dict and
             {"loading", "empty", "error", "restricted", "stale", "reset"} <= set(runtime["state_contract"]) and
             all(s.cw.text(x) for x in runtime["state_contract"].values()), "app.state_contract_required")
        by_key = {b["query_key"]: b for b in bindings}
        components = runtime.get("components")
        need(type(components) is list and 1 <= len(components) <= 100, "app.components_required")
        seen, bound, component_queries = set(), set(), {}
        for component in components:
            need(type(component) is dict and set(component) == {"component_id", "query_key", "runtime_fragment", "query_reference"},
                 "app.component_shape")
            ident, key = component["component_id"], component["query_key"]
            need(s.cw.text(ident) and ident not in seen and key in by_key, "app.component_query_mismatch")
            seen.add(ident)
            component_queries[ident] = key
            bound.add(key)
            fragment, reference = component["runtime_fragment"], component["query_reference"]
            need(type(fragment) is str and type(reference) is str and reference in fragment and
                 (f'"{key}"' in reference or f"'{key}'" in reference), "app.query_reference_required")
            _script_fragment(html, fragment)
        need(bound == set(by_key), "app.runtime_query_unbound")
        controls = runtime.get("controls", [])
        need(type(controls) is list and len(controls) <= 48, "app.control_contract_shape")
        required = s.control_source_keys(requirements, "app")
        control_bound, selectors = set(), []
        for control in controls:
            need(type(control) is dict and set(control) == {"source_asset_keys", "component_id", "query_keys", "topic",
                 "field_ids", "runtime_fragment", "reset_fragment", "contract_reference"}, "app.control_contract_shape")
            s.cw.strings(control["source_asset_keys"], "app.control_sources", nonempty=True)
            s.cw.strings(control["query_keys"], "app.control_queries", nonempty=True)
            s.cw.strings(control["field_ids"], "app.control_fields", nonempty=True)
            need(set(control["source_asset_keys"]) <= required and not control_bound.intersection(control["source_asset_keys"]),
                 "app.control_source_mismatch")
            control_bound.update(control["source_asset_keys"])
            need(control["component_id"] in seen and set(control["query_keys"]) <= bound and
                 component_queries[control["component_id"]] in control["query_keys"] and
                 all(by_key[k]["topic"] == control["topic"] for k in control["query_keys"]) and
                 s.cw.text(control["contract_reference"]), "app.control_scope_mismatch")
            for fragment in (control["runtime_fragment"], control["reset_fragment"]):
                _script_fragment(html, fragment)
                need(all(f'"{key}"' in fragment or f"'{key}'" in fragment for key in control["query_keys"]),
                     "app.control_query_reference_missing")
            need(all(field in control["runtime_fragment"] for field in control["field_ids"]), "app.control_field_not_in_runtime")
            selectors.append({"query_key": None, "control_id": control["component_id"], "topic": control["topic"],
                              "query": {}, "field_ids": control["field_ids"]})
        scenarios = runtime.get("scenario_controls", [])
        need(type(scenarios) is list and len(scenarios) <= 48, "app.scenario_contract_shape")
        scenario_ids = set()
        for control in scenarios:
            need(type(control) is dict and set(control) == {"source_asset_keys", "component_id", "query_keys", "input_id",
                 "minimum", "maximum", "default", "formula_reference", "runtime_fragment", "reset_fragment"},
                 "app.scenario_contract_shape")
            s.cw.strings(control["source_asset_keys"], "app.scenario_sources", nonempty=True)
            s.cw.strings(control["query_keys"], "app.scenario_queries", nonempty=True)
            need(set(control["source_asset_keys"]) <= required and not control_bound.intersection(control["source_asset_keys"]),
                 "app.scenario_source_mismatch")
            control_bound.update(control["source_asset_keys"])
            ident = control["input_id"]
            need(type(ident) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", ident) and ident not in scenario_ids and
                 control["component_id"] in seen and set(control["query_keys"]) <= bound and
                 component_queries[control["component_id"]] in control["query_keys"] and s.cw.text(control["formula_reference"]),
                 "app.scenario_scope_mismatch")
            scenario_ids.add(ident)
            need(all(type(control[k]) in (int, float) and math.isfinite(control[k]) for k in ("minimum", "maximum", "default")) and
                 control["minimum"] <= control["default"] <= control["maximum"], "app.scenario_numeric_domain")
            for fragment in (control["runtime_fragment"], control["reset_fragment"]):
                _script_fragment(html, fragment)
                need(all(f'"{key}"' in fragment or f"'{key}'" in fragment for key in [ident, *control["query_keys"]]),
                     "app.scenario_runtime_reference")
        need(control_bound == required, "app.source_control_unbound")
        return runtime, evidence, [*bindings, *selectors]

    def _construction_review(self, path, body, runtime):
        review = self._read(path)
        need(type(review) is dict and set(review) == {"schema_version", "kind", "exclusive_draft_reference",
             "native_bridge_reference", "resource_policy_reference", "behavior_reference", "evidence_paths",
             "input_bindings", "state_fragments"} and review["schema_version"] == 1 and
             review["kind"] == "analyst_app_construction_review", "app.construction_review_required")
        need(all(s.cw.text(review[k]) for k in ("exclusive_draft_reference", "native_bridge_reference",
             "resource_policy_reference", "behavior_reference")), "app.construction_review_reference")
        s.cw.strings(review["evidence_paths"], "app.construction_evidence", nonempty=True)
        evidence = [self._pin(p) for p in review["evidence_paths"]]
        states = review["state_fragments"]
        need(type(states) is dict and set(states) == {"loading", "empty", "error", "restricted", "stale", "reset", "run"},
             "app.initial_states_required")
        for fragment in states.values():
            _script_fragment(body["html"], fragment)
        controls = [*(runtime.get("controls", [])), *(runtime.get("scenario_controls", []))]
        inputs = review["input_bindings"]
        need(type(inputs) is list and len(inputs) == len(controls), "app.initial_inputs_required")
        seen, matched = set(), set()
        for item in inputs:
            need(type(item) is dict and set(item) == {"input_id", "source_asset_keys", "query_keys", "mode", "value_type",
                 "default", "allowed_values", "minimum", "maximum", "change_fragment", "reset_fragment", "review_reference"},
                 "app.input_shape")
            ident = item["input_id"]
            need(type(ident) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", ident) and ident not in seen and
                 re.search(r'\bid\s*=\s*([\"\'])' + re.escape(ident) + r'\1', body["html"]) and
                 s.cw.text(item["review_reference"]), "app.input_identity")
            seen.add(ident)
            s.cw.strings(item["source_asset_keys"], "app.input_sources", nonempty=True)
            s.cw.strings(item["query_keys"], "app.input_queries", nonempty=True)
            candidates = [(i, c) for i, c in enumerate(controls) if
                c["source_asset_keys"] == item["source_asset_keys"] and c["query_keys"] == item["query_keys"]]
            need(len(candidates) == 1 and candidates[0][0] not in matched, "app.input_control_scope")
            index, control = candidates[0]
            matched.add(index)
            scenario = "input_id" in control
            need(item["mode"] == ("local_scenario" if scenario else "governed_filter"), "app.input_role_mismatch")
            if item["value_type"] == "number":
                values = (item["minimum"], item["maximum"], item["default"])
                need(all(type(x) in (int, float) and math.isfinite(x) for x in values) and
                     item["minimum"] <= item["default"] <= item["maximum"] and item["allowed_values"] is None,
                     "app.input_numeric_domain")
            else:
                need(item["value_type"] == "enum" and item["minimum"] is None and item["maximum"] is None,
                     "app.input_type_unsupported")
                s.cw.strings(item["allowed_values"], "app.input_domain", nonempty=True)
                need(item["default"] in item["allowed_values"], "app.input_default")
            if scenario:
                need(all(item[k] == control[k] for k in ("input_id", "minimum", "maximum", "default")) and
                     item["value_type"] == "number", "app.scenario_domain_mismatch")
            for key, control_key in (("change_fragment", "runtime_fragment"), ("reset_fragment", "reset_fragment")):
                fragment = item[key]
                need(fragment == control[control_key] and (f'"{ident}"' in fragment or f"'{ident}'" in fragment),
                     "app.input_runtime_binding")
                _script_fragment(body["html"], fragment)
        return review, evidence

    def capture_initial_baseline(self, spec_path, output_relative):
        spec = self._read(spec_path)
        need(spec.get("schema_version") == 1 and spec.get("kind") == "analyst_initial_omni_app_baseline_spec" and
             s.cw.text(spec.get("review_ref")), "app.initial_baseline_spec_required")
        req = self._requirements([spec["requirements_path"]])
        inspection = self.inspect_initial()
        need(inspection["app"] is None, "app.initial_requires_workbook_only_draft")
        body = initial_body(self._read(spec["body_path"]))
        self._validate_bindings(spec["bindings"], req, inspection)
        runtime, evidence, selectors = self._runtime(spec["runtime_path"], req, spec["bindings"], body["html"])
        review, review_evidence = self._construction_review(spec["construction_review_path"], body, runtime)
        snapshot = self._semantic_snapshot(selectors, inspection)
        _, project = w.ap.load_project(self.root)
        record = s.cw.sealed({"schema_version": 1, "kind": INITIAL_BASELINE, "surface": "app", "project_id": project["id"],
            "target": asdict(self.target), "route": req["route"], "route_reference": req["route_reference"],
            "spec": self._pin(spec_path), "requirements": self._pin(spec["requirements_path"]),
            "runtime": self._pin(spec["runtime_path"]), "runtime_evidence": evidence,
            "body": self._pin(spec["body_path"]), "initial_body": body,
            "construction_review": self._pin(spec["construction_review_path"]), "construction_contract": review,
            "construction_evidence": review_evidence,
            "source_files": [self._pin(p["path"]) for p in req["source_files"]], "bindings": spec["bindings"],
            "runtime_contract": runtime, "semantic_selectors": selectors, "inspection": inspection,
            "semantic_snapshot": snapshot, "semantic_sha256": n.digest(snapshot),
            "selected_backend": s.selected_backend(self.root, req, w),
            "native_verified": False, "business_accepted": False, "authorizes_target_write": False})
        self._write(output_relative, record, exclusive=True)
        return {"status": "baseline_captured", "surface": "app", "operation": "initial_put", "baseline_sha256": record["sha256"],
                "file": self._pin(output_relative), "bindings": len(spec["bindings"]), "native_verified": False}

    def initial_baseline(self, path, live=None):
        baseline = self._read(path)
        s.cw.check_seal(baseline, INITIAL_BASELINE)
        _, project = w.ap.load_project(self.root)
        need(baseline.get("target") == asdict(self.target) and baseline.get("project_id") == project["id"] and
             baseline.get("surface") == "app" and baseline.get("authorizes_target_write") is False and
             baseline.get("native_verified") is False and baseline["inspection"]["app"] is None,
             "app.initial_baseline_context_changed")
        for pin in [baseline["spec"], baseline["requirements"], baseline["runtime"], baseline["body"], baseline["construction_review"],
                    *baseline["runtime_evidence"], *baseline["construction_evidence"], *baseline["source_files"]]:
            need(self._pin(pin["path"]) == pin, "app.initial_baseline_evidence_changed")
        req = self._requirements([baseline["requirements"]["path"]])
        spec = self._read(baseline["spec"]["path"])
        need(spec.get("kind") == "analyst_initial_omni_app_baseline_spec" and spec["bindings"] == baseline["bindings"] and
             all(spec[key + "_path"] == baseline[key]["path"] for key in ("requirements", "runtime", "body", "construction_review")) and
             baseline["source_files"] == [self._pin(p["path"]) for p in req["source_files"]] and
             baseline["route"] == req["route"] and baseline["route_reference"] == req["route_reference"] and
             baseline["selected_backend"] == s.selected_backend(self.root, req, w), "app.initial_baseline_binding_changed")
        body = initial_body(self._read(baseline["body"]["path"]))
        need(body == baseline["initial_body"], "app.initial_body_changed")
        inspection = live or baseline["inspection"]
        self._validate_bindings(baseline["bindings"], req, inspection)
        runtime, evidence, selectors = self._runtime(baseline["runtime"]["path"], req, baseline["bindings"], body["html"])
        review, review_evidence = self._construction_review(baseline["construction_review"]["path"], body, runtime)
        need(runtime == baseline["runtime_contract"] and evidence == baseline["runtime_evidence"] and
             selectors == baseline["semantic_selectors"] and review == baseline["construction_contract"] and
             review_evidence == baseline["construction_evidence"], "app.initial_runtime_binding_changed")
        snapshot = self._semantic_snapshot(selectors, inspection) if live else baseline["semantic_snapshot"]
        s.semantic_definitions(snapshot, selectors)
        need(snapshot == baseline["semantic_snapshot"] and n.digest(snapshot) == baseline["semantic_sha256"],
             "app.current_semantic_context_drift")
        return baseline

    def prepare_initial(self, spec_path):
        self._stage_gate("build")
        spec = self._read(spec_path)
        need(spec.get("schema_version") == 1 and spec.get("kind") == "analyst_native_app_initial_spec" and
             s.cw.text(spec.get("review_ref")), "app.initial_candidate_spec_required")
        body = initial_body(self._read(spec["body_path"]))
        engagement = self._stage_gate("build", body["html"].encode("utf-8"))
        caps, before = self.capabilities(), self.inspect_initial()
        need(before["app"] is None, "app.initial_requires_workbook_only_draft")
        baseline = self.initial_baseline(spec["baseline_path"], before)
        need(spec["requirements_path"] == baseline["requirements"]["path"] and
             spec["body_path"] == baseline["body"]["path"], "app.initial_candidate_paths")
        need(body == initial_body(self._read(spec["body_path"])), "app.initial_body_changed")
        candidate = {"contract": CONTRACT, "surface": "app", "operation": "initial_put", "target": asdict(self.target), "created_at": n.now(),
            "spec": self._pin(spec_path), "baseline": self._pin(spec["baseline_path"]),
            "requirements": self._pin(spec["requirements_path"]), "body_file": self._pin(spec["body_path"]),
            "initial_body": body, "before": before, "expected_app": body,
            "semantic_sha256": baseline["semantic_sha256"], "capability_sha256": caps["capability_sha256"],
            "validation": "prepared_only", "native_verified": False, "business_accepted": False,
            "runtime_validation": "reviewed_construction_contract_independent_native_cases_required"}
        if engagement is not None:
            candidate["engagement"] = engagement
        digest = n.digest(candidate)
        candidate["candidate_sha256"] = digest
        path = f".omni-app-native/candidates/{digest}.json"
        self._stage_gate("build", body["html"].encode("utf-8"), expected=engagement, execution=True)
        self._write(path, candidate, exclusive=True)
        return {"status": "prepared", "surface": "app", "operation": "initial_put", "candidate_sha256": digest, "path": path,
                "native_verified": False}

    def _initial_candidate(self, value, check_evidence):
        need(value["before"]["app"] is None and "app" not in value["before"]["state"] and
             not any(k in value["before"]["state"] for k in ("containers", "controls", "settings")) and
             initial_body(value["initial_body"]) == value["expected_app"], "app.initial_candidate_state")
        if check_evidence:
            for pin in (value["spec"], value["baseline"], value["requirements"], value["body_file"]):
                need(self._pin(pin["path"]) == pin, "app.initial_candidate_evidence_changed")
            baseline = self.initial_baseline(value["baseline"]["path"])
            spec = self._read(value["spec"]["path"])
            need(spec.get("kind") == "analyst_native_app_initial_spec" and spec.get("schema_version") == 1 and
                 s.cw.text(spec.get("review_ref")) and spec["baseline_path"] == value["baseline"]["path"] and
                 spec["requirements_path"] == value["requirements"]["path"] and spec["body_path"] == value["body_file"]["path"] and
                 value["requirements"] == baseline["requirements"] and value["body_file"] == baseline["body"] and
                 value["initial_body"] == baseline["initial_body"] and value["semantic_sha256"] == baseline["semantic_sha256"],
                 "app.initial_candidate_contract_changed")
            self._validate_bindings(baseline["bindings"], self._requirements([value["requirements"]["path"]]), value["before"])
        return value

    def capture_baseline(self, spec_path, output_relative):
        spec = self._read(spec_path)
        need(spec.get("schema_version") == 1 and spec.get("kind") == "analyst_existing_omni_app_baseline_spec" and
             s.cw.text(spec.get("review_ref")), "app.baseline_spec_required")
        req = self._requirements([spec["requirements_path"]])
        inspection = self.inspect()
        self._validate_bindings(spec["bindings"], req, inspection)
        runtime, evidence, selectors = self._runtime(spec["runtime_path"], req, spec["bindings"], inspection["app"]["html"])
        snapshot = self._semantic_snapshot(selectors, inspection)
        _, project = w.ap.load_project(self.root)
        record = s.cw.sealed({"schema_version": 1, "kind": BASELINE, "surface": "app", "project_id": project["id"],
            "target": asdict(self.target), "route": req["route"], "route_reference": req["route_reference"],
            "spec": self._pin(spec_path), "requirements": self._pin(spec["requirements_path"]),
            "runtime": self._pin(spec["runtime_path"]), "runtime_evidence": evidence,
            "source_files": [self._pin(p["path"]) for p in req["source_files"]], "bindings": spec["bindings"],
            "runtime_contract": runtime, "semantic_selectors": selectors, "inspection": inspection,
            "semantic_snapshot": snapshot, "semantic_sha256": n.digest(snapshot),
            "selected_backend": s.selected_backend(self.root, req, w),
            "native_verified": False, "business_accepted": False, "authorizes_target_write": False})
        self._write(output_relative, record, exclusive=True)
        return {"status": "baseline_captured", "surface": "app", "baseline_sha256": record["sha256"],
                "file": self._pin(output_relative), "bindings": len(spec["bindings"]), "native_verified": False}

    def baseline(self, path, live=None):
        baseline = self._read(path)
        if baseline.get("kind") == INITIAL_BASELINE:
            return self.initial_baseline(path, live)
        s.cw.check_seal(baseline, BASELINE)
        _, project = w.ap.load_project(self.root)
        need(baseline.get("target") == asdict(self.target) and baseline.get("project_id") == project["id"] and
             baseline.get("surface") == "app" and baseline.get("authorizes_target_write") is False and
             baseline.get("native_verified") is False, "app.baseline_context_changed")
        for pin in [baseline["spec"], baseline["requirements"], baseline["runtime"], *baseline["runtime_evidence"], *baseline["source_files"]]:
            need(self._pin(pin["path"]) == pin, "app.baseline_evidence_changed")
        req = self._requirements([baseline["requirements"]["path"]])
        spec = self._read(baseline["spec"]["path"])
        need(spec["bindings"] == baseline["bindings"] and spec["runtime_path"] == baseline["runtime"]["path"] and
             spec["requirements_path"] == baseline["requirements"]["path"] and
             baseline["source_files"] == [self._pin(p["path"]) for p in req["source_files"]] and
             baseline["route"] == req["route"] and baseline["route_reference"] == req["route_reference"] and
             baseline["selected_backend"] == s.selected_backend(self.root, req, w), "app.baseline_binding_changed")
        inspection = live or baseline["inspection"]
        self._validate_bindings(baseline["bindings"], req, inspection)
        runtime, evidence, selectors = self._runtime(baseline["runtime"]["path"], req, baseline["bindings"], inspection["app"]["html"])
        need(runtime == baseline["runtime_contract"] and evidence == baseline["runtime_evidence"] and
             selectors == baseline["semantic_selectors"], "app.runtime_binding_changed")
        snapshot = self._semantic_snapshot(selectors, inspection) if live else baseline["semantic_snapshot"]
        s.semantic_definitions(snapshot, selectors)
        need(snapshot == baseline["semantic_snapshot"] and n.digest(snapshot) == baseline["semantic_sha256"],
             "app.current_semantic_context_drift")
        return baseline

    def prepare(self, spec_path):
        self._stage_gate("build")
        spec = self._read(spec_path)
        need(spec.get("schema_version") == 1 and spec.get("kind") == "analyst_native_app_spec" and
             s.cw.text(spec.get("review_ref")), "app.candidate_spec_required")
        saved = self.baseline(spec["baseline_path"])
        patch = self._read(spec["patch_path"])
        expected = apply_edits(saved["inspection"]["app"]["html"], patch, spec["owned_regions"])
        engagement = self._stage_gate("build", expected.encode("utf-8"))
        caps, before = self.capabilities(), self.inspect()
        baseline = self.baseline(spec["baseline_path"], before)
        need(baseline["kind"] == BASELINE and spec["requirements_path"] == baseline["requirements"]["path"], "app.requirements_mismatch")
        need(patch == self._read(spec["patch_path"]) and
             expected == apply_edits(before["app"]["html"], patch, spec["owned_regions"]), "app.candidate_input_changed")
        req = self._requirements([spec["requirements_path"]])
        self._runtime(baseline["runtime"]["path"], req, baseline["bindings"], expected)
        candidate = {"contract": CONTRACT, "surface": "app", "target": asdict(self.target), "created_at": n.now(),
            "spec": self._pin(spec_path), "baseline": self._pin(spec["baseline_path"]),
            "requirements": self._pin(spec["requirements_path"]), "patch_file": self._pin(spec["patch_path"]),
            "patch": patch, "owned_regions": spec["owned_regions"], "before": before,
            "expected_app": {"html": expected, "settings": before["app"]["settings"]},
            "semantic_sha256": baseline["semantic_sha256"], "capability_sha256": caps["capability_sha256"],
            "validation": "prepared_only", "native_verified": False, "business_accepted": False,
            "runtime_validation": "retained_reviewed_fragments_only"}
        if engagement is not None:
            candidate["engagement"] = engagement
        digest = n.digest(candidate)
        candidate["candidate_sha256"] = digest
        path = f".omni-app-native/candidates/{digest}.json"
        self._stage_gate("build", expected.encode("utf-8"), expected=engagement, execution=True)
        self._write(path, candidate, exclusive=True)
        return {"status": "prepared", "surface": "app", "candidate_sha256": digest, "path": path, "native_verified": False}

    def _candidate(self, digest, check_evidence=True):
        need(type(digest) is str and n.HASH.fullmatch(digest), "app.candidate_digest")
        value = self._read(f".omni-app-native/candidates/{digest}.json")
        need(value.get("candidate_sha256") == digest and n.digest({k: v for k, v in value.items() if k != "candidate_sha256"}) == digest and
             value.get("contract") == CONTRACT and value.get("surface") == "app" and value.get("target") == asdict(self.target),
             "app.candidate_changed")
        if value.get("operation") == "initial_put":
            return self._initial_candidate(value, check_evidence)
        need(value.get("operation") in (None, "bounded_patch"), "app.unknown_candidate_operation")
        if check_evidence:
            for pin in (value["spec"], value["baseline"], value["requirements"], value["patch_file"]):
                need(self._pin(pin["path"]) == pin, "app.candidate_evidence_changed")
            baseline = self.baseline(value["baseline"]["path"])
            need(baseline["semantic_sha256"] == value["semantic_sha256"], "app.candidate_baseline_changed")
            spec = self._read(value["spec"]["path"])
            need(value["patch"] == self._read(value["patch_file"]["path"]) and value["owned_regions"] == spec["owned_regions"] and
                 value["expected_app"]["html"] == apply_edits(value["before"]["app"]["html"], value["patch"], value["owned_regions"]) and
                 value["expected_app"]["settings"] == value["before"]["app"]["settings"], "app.expected_state_changed")
            req = self._requirements([value["requirements"]["path"]])
            need(value["requirements"] == baseline["requirements"] and
                 spec["baseline_path"] == value["baseline"]["path"] and spec["patch_path"] == value["patch_file"]["path"],
                 "app.candidate_contract_paths_changed")
            self._runtime(baseline["runtime"]["path"], req, baseline["bindings"], value["expected_app"]["html"])
        return value

    @staticmethod
    def matches(candidate, observed):
        meta = observed.get("draft_context", {})
        before = candidate["before"]["draft_context"]
        target = candidate["target"]
        branch = meta.get("branch")
        context_matches = (type(meta) is dict and meta.get("identifier") == target["draft_id"] and
            meta.get("publishedIdentifier") == target["document_id"] and meta.get("status") == "active" and
            meta.get("draftOutOfDate") is False and "branch" in meta and (branch is None or type(branch) is dict) and
            (branch.get("id") if isinstance(branch, dict) else None) == target["branch_id"] and
            meta.get("workbookModelId") == observed.get("state", {}).get("workbookModelId") and
            all(meta.get(key) == before.get(key) for key in
                ("identifier", "publishedIdentifier", "workbookModelId", "branch", "status", "draftOutOfDate")))
        initial = candidate.get("operation") == "initial_put"
        expected_state = copy.deepcopy(candidate["before"]["state"])
        if initial:
            expected_state["app"] = {"url": f'/api/v2/documents/{target["document_id"]}/draft/{target["draft_id"]}/app'}
        observed_app = observed.get("app")
        return (context_matches and isinstance(observed_app, dict) and
                observed_app.get("html") == candidate["expected_app"]["html"] and
                settings_match(observed_app.get("settings"), candidate["expected_app"]["settings"], initial) and
                observed["state"] == expected_state and
                observed["identity"] == candidate["before"]["identity"])

    def execute(self, candidate_sha256, authorization_ref):
        return self._execute(candidate_sha256, authorization_ref, False)

    def execute_initial(self, candidate_sha256, authorization_ref):
        return self._execute(candidate_sha256, authorization_ref, True)

    def _execute(self, candidate_sha256, authorization_ref, initial):
        self._stage_gate("release")
        need(s.cw.text(authorization_ref), "app.exact_authorization_required")
        with self._lock():
            candidate = self._candidate(candidate_sha256)
            content = candidate["expected_app"]["html"].encode("utf-8")
            self._stage_gate("release", content, expected=candidate.get("engagement"), execution=True)
            need((candidate.get("operation") == "initial_put") is initial, "app.separate_initial_authorization_required")
            intent = f".omni-app-native/executions/{candidate_sha256}/intent.json"
            need(not self._path(intent, exists=False).exists(), "app.intent_exists_reconcile_never_replay")
            need(self.capabilities()["capability_sha256"] == candidate["capability_sha256"], "app.capability_changed")
            before = self.inspect_initial() if initial else self.inspect()
            need(before == candidate["before"], "app.draft_or_identity_drift")
            baseline = self.baseline(candidate["baseline"]["path"], before)
            receipt = {"contract": CONTRACT, "surface": "app", "target": asdict(self.target), "candidate_sha256": candidate_sha256,
                "authorization_ref": authorization_ref, "started_at": n.now(), "status": "intent_persisted",
                "semantic_sha256": baseline["semantic_sha256"], "native_verified": False, "business_accepted": False, "published": False}
            if initial:
                receipt["operation"] = "initial_put"
            self._stage_gate("release", content, expected=candidate.get("engagement"), execution=True)
            self._write(intent, receipt, exclusive=True)
            try:
                status, _, raw = self._rest("PUT" if initial else "PATCH", self._app_route(),
                                            candidate["initial_body"] if initial else candidate["patch"])
                response = n.decode(raw)
                need(status == 200 and response.get("identifier") == self.target.document_id and
                     response.get("draftIdentifier") == self.target.draft_id and type(response.get("app")) is dict,
                     "app.write_response_mismatch")
                receipt["response"] = response
                after = self.inspect()
                self.baseline(candidate["baseline"]["path"], after)
                receipt["baseline_check"] = {"semantic_snapshot": baseline["semantic_snapshot"],
                    "semantic_sha256": baseline["semantic_sha256"], "checked_at": n.now()}
                receipt["readback"] = after
                receipt["status"] = "readback_matched" if self.matches(candidate, after) else "readback_mismatch"
            except (ValueError, OSError, TimeoutError, TypeError, KeyError, AttributeError) as exc:
                receipt["status"], receipt["error_class"] = "outcome_unknown", type(exc).__name__
            receipt["finished_at"] = n.now()
            self._write(f".omni-app-native/executions/{candidate_sha256}/receipt.json", receipt)
            return receipt

    def reconcile(self, candidate_sha256):
        return self._reconcile(candidate_sha256, False)

    def reconcile_initial(self, candidate_sha256):
        return self._reconcile(candidate_sha256, True)

    def _reconcile(self, candidate_sha256, initial):
        with self._lock():
            candidate = self._candidate(candidate_sha256, check_evidence=False)
            need((candidate.get("operation") == "initial_put") is initial, "app.separate_initial_authorization_required")
            intent = self._read(f".omni-app-native/executions/{candidate_sha256}/intent.json")
            current = self.inspect_initial() if initial else self.inspect()
            try:
                self._candidate(candidate_sha256)
                self.baseline(candidate["baseline"]["path"], current)
                fresh = True
            except (ValueError, OSError):
                fresh = False
            receipt = {**intent, "reconciled_at": n.now(), "readback": current, "source_evidence_current": fresh,
                "automatic_retry_allowed": False,
                "status": "readback_matched" if fresh and self.matches(candidate, current) else "conflict_or_stale_evidence"}
            if fresh:
                baseline = self.baseline(candidate["baseline"]["path"])
                receipt["baseline_check"] = {"semantic_snapshot": baseline["semantic_snapshot"],
                    "semantic_sha256": baseline["semantic_sha256"], "checked_at": n.now()}
            self._write(f".omni-app-native/executions/{candidate_sha256}/reconciliation.json", receipt)
            return receipt

    def export_start(self, *args, **kwargs):
        raise n.NativeError("Named App draft export has no qualified contract; retain independent native preview evidence")

    export_status = export_start
    export_file = export_start


def validate_delivery(root, candidate_path, execution_receipt_path, coverage_path):
    """Offline recomputation for standalone and real DMA returns; no remote calls."""
    root, _ = w.ap.load_project(root)
    candidate = w.load(root, candidate_path)
    adapter = AppNativeAdapter(root, n.TargetConfig(**candidate["target"]))
    need(adapter._candidate(candidate["candidate_sha256"]) == candidate and
         candidate_path == f'.omni-app-native/candidates/{candidate["candidate_sha256"]}.json', "app.delivery_candidate_mismatch")
    baseline = adapter.baseline(candidate["baseline"]["path"])
    folder = f'.omni-app-native/executions/{candidate["candidate_sha256"]}'
    need(execution_receipt_path in {folder + "/receipt.json", folder + "/reconciliation.json"}, "app.receipt_location")
    receipt, intent = w.load(root, execution_receipt_path), w.load(root, folder + "/intent.json")
    need(receipt.get("contract") == CONTRACT and receipt.get("surface") == "app" and receipt.get("status") == "readback_matched" and
         receipt.get("target") == candidate["target"] and receipt.get("candidate_sha256") == candidate["candidate_sha256"] and
         intent.get("contract") == CONTRACT and intent.get("candidate_sha256") == candidate["candidate_sha256"] and
         intent.get("status") == "intent_persisted" and intent.get("target") == candidate["target"] and
         intent.get("operation") == receipt.get("operation") == candidate.get("operation") and
         intent.get("authorization_ref") == receipt.get("authorization_ref") and s.cw.text(receipt.get("authorization_ref")) and
         receipt.get("semantic_sha256") == baseline["semantic_sha256"] and receipt.get("published") is False and
         receipt.get("business_accepted") is False and receipt.get("native_verified") is False and
         adapter.matches(candidate, receipt["readback"]), "app.receipt_mismatch")
    readback = receipt["readback"]
    need(readback.get("target") == candidate["target"] and readback.get("snapshot_sha256") ==
         n.digest({k: v for k, v in readback.items() if k != "snapshot_sha256"}), "app.readback_hash")
    check = receipt.get("baseline_check", {})
    need(check.get("semantic_snapshot") == baseline["semantic_snapshot"] and
         check.get("semantic_sha256") == baseline["semantic_sha256"] and s.cw.text(check.get("checked_at")), "app.baseline_recheck_missing")
    coverage = w.load(root, coverage_path)
    need(coverage["requirements"] == w.pin(root, candidate["requirements"]["path"]) and coverage["candidate"] == w.pin(root, candidate_path),
         "app.coverage_binding_mismatch")
    with tempfile.TemporaryDirectory(dir=root / "evidence") as temporary:
        output = str((Path(temporary) / "coverage.json").relative_to(root))
        w.coverage(root, candidate["requirements"]["path"], candidate_path, [p["path"] for p in coverage["evidence"]], output)
        need(w.load(root, output) == coverage, "app.coverage_changed")
    return {"surface": "app", "target": candidate["target"], "candidate_sha256": candidate["candidate_sha256"],
            "requirements": candidate["requirements"], "baseline": candidate["baseline"],
            "candidate": adapter._pin(candidate_path), "execution_receipt": adapter._pin(execution_receipt_path),
            "coverage": adapter._pin(coverage_path), "pending_cases": coverage["pending_cases"],
            "deferred_assets": coverage["deferred_assets"], "unresolved_assets": coverage["unresolved_assets"],
            "native_verification": "recorded_readback_only", "runtime_validation": "independent_cases_required",
            "native_verified": False, "migration_accepted": False}


def verify_delivery(root, spec):
    """Read-only surface proof; accepts three engagement-relative evidence paths."""
    result = validate_delivery(root, spec["candidate_path"], spec["execution_receipt_path"], spec["coverage_path"])
    result["gaps"] = ([{"code": "pending_case", "case_id": value} for value in result["pending_cases"]] +
                      [{"code": "deferred_source_asset", "asset_key": value} for value in result["deferred_assets"]] +
                      [{"code": "unresolved_source_parity", "asset_key": value} for value in result["unresolved_assets"]])
    return result


def build_return(root, project, scope_relative, spec_path, migration):
    spec = w.load(root, spec_path)
    migration.envelope(spec, "analyst_standalone_migration_return_spec")
    need(spec.get("surface") == "app", "app.return_surface_required")
    validate_delivery(root, spec["candidate_path"], spec["execution_receipt_path"], spec["coverage_path"])
    scope = migration.load_scope(root, project, scope_relative)
    need(scope["migration_scope"] == "standalone_frontend" and scope["backend_context"] is None and
         not project.get("dma_import"), "app.standalone_no_dma_required")
    need(scope["sha256"] == spec["scope_sha256"], "app.return_scope_changed")
    baseline = w.load(root, spec["baseline_path"])
    adapter = AppNativeAdapter(root, n.TargetConfig(**baseline["target"]))
    adapter.baseline(spec["baseline_path"])
    candidate = w.load(root, spec["candidate_path"])
    need(adapter._candidate(candidate["candidate_sha256"]) == candidate and
         candidate["baseline"] == adapter._pin(spec["baseline_path"]) and
         candidate["requirements"] == adapter._pin(spec["requirements_path"]), "app.return_candidate_changed")
    requirements = adapter._requirements([spec["requirements_path"]])
    inventory = requirements["source_files"][1]
    need(len(scope["inventories"]) == 1 and all(scope["inventories"][0][k] == inventory[k] for k in inventory),
         "app.return_scope_inventory_mismatch")
    dispositions = {i["asset_key"]: i["disposition"] for i in requirements["items"]}
    need(all(dispositions[key] == unit["disposition"] for unit in scope["units"] for key in unit["asset_keys"]),
         "app.return_disposition_changed")
    folder = f'.omni-app-native/executions/{candidate["candidate_sha256"]}'
    coverage = w.load(root, spec["coverage_path"])
    s.cw.strings(spec.get("unresolved"), "app.unresolved_required")
    gaps = [{"code": "pending_case", "case_id": case} for case in coverage["pending_cases"]]
    gaps += [{"code": "deferred_source_asset", "asset_key": key} for key in coverage["deferred_assets"]]
    gaps += [{"code": "unresolved_source_parity", "asset_key": key} for key in coverage["unresolved_assets"]]
    gaps += [{"code": "declared_unresolved", "requirement": text} for text in spec["unresolved"]]
    other_surfaces = sorted({surface for unit in scope["units"] if unit["disposition"] == "migrate" for surface in unit["surfaces"]} - {"app"})
    gaps += [{"code": "other_surface_requires_separate_receipt", "surface": surface} for surface in other_surfaces]
    if any(i["gaps"] for i in scope["inventories"]):
        gaps.append({"code": "retained_source_gaps"})
    if not scope["independent_source_listing"]:
        gaps.append({"code": "independent_source_listing_missing"})
    files = [adapter._pin(spec[key]) for key in ("baseline_path", "requirements_path", "candidate_path", "execution_receipt_path", "coverage_path")]
    files.append(adapter._pin(folder + "/intent.json"))
    return s.cw.sealed({"schema_version": 1, "kind": s.RETURN_KIND, "surface": "app", "project_id": project["id"],
        "scope": adapter._pin(scope_relative), "scope_sha256": scope["sha256"], "migration_scope": "standalone_frontend",
        "backend_context": None, "spec": adapter._pin(spec_path), "files": files, "target": candidate["target"],
        "source_files": baseline["source_files"], "baseline_sha256": baseline["sha256"], "candidate_sha256": candidate["candidate_sha256"],
        "candidate_coverage": "complete" if not gaps else "incomplete", "gaps": gaps,
        "coverage_basis": "recomputed_source_scope_app_baseline_readback_and_case_evidence",
        "missing_lanes": sorted({case.split("/")[-2] for case in coverage["pending_cases"]}), "acceptance": "not_assessed",
        "native_verification": "recorded_readback_only", "business_acceptance": "not_assessed",
        "remote_freshness": "last_recorded_native_inspection_only", "runtime_validation": "independent_cases_required",
        "authorizes_target_write": False, "origin_authenticated": False, "migration_accepted": False})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--target", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capabilities", "inspect", "inspect-initial"):
        sub.add_parser(name)
    for name in ("baseline-capture", "baseline-capture-initial"):
        baseline = sub.add_parser(name)
        baseline.add_argument("--spec", required=True)
        baseline.add_argument("--output", required=True)
    for name in ("prepare", "prepare-initial"):
        prepare = sub.add_parser(name)
        prepare.add_argument("--spec", required=True)
    for name in ("execute", "reconcile", "execute-initial", "reconcile-initial"):
        command = sub.add_parser(name)
        command.add_argument("--candidate", required=True)
        if name.startswith("execute"):
            command.add_argument("--authorization-ref", required=True)
    args = parser.parse_args(argv)
    root = Path(args.workspace).resolve(strict=True)
    target = w.load(root, args.target)
    adapter = AppNativeAdapter(root, n.TargetConfig(**target))
    if args.command in ("baseline-capture", "baseline-capture-initial"):
        method = adapter.capture_initial_baseline if args.command.endswith("-initial") else adapter.capture_baseline
        result = method(args.spec, args.output)
    elif args.command == "prepare-initial":
        result = adapter.prepare_initial(args.spec)
    elif args.command == "execute-initial":
        result = adapter.execute_initial(args.candidate, args.authorization_ref)
    elif args.command == "reconcile-initial":
        result = adapter.reconcile_initial(args.candidate)
    elif args.command == "prepare":
        result = adapter.prepare(args.spec)
    elif args.command == "execute":
        result = adapter.execute(args.candidate, args.authorization_ref)
    elif args.command == "reconcile":
        result = adapter.reconcile(args.candidate)
    else:
        result = getattr(adapter, args.command.replace("-", "_"))()
    print(n.encoded(result).decode())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(n.encoded({"status": "blocked", "error_class": type(exc).__name__}).decode())
        raise SystemExit(2) from None
