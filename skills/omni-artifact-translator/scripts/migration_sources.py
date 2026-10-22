"""Bounded projections of emitted Domo/Sigma contracts; no engine imports or APIs.

This is deliberately not the source engines' schema/authorization validator.
Local structural/hash checks do not authenticate provenance or store readiness.
"""
import copy
import hashlib
import json
import re

PINS = {"domo": "55eba0ca0690fbf14f39eddbc8a04c94a720c155",
        "sigma": "f4eda45b0f49dc7335496d028665f7339ed82e8f"}
MODES = {"omni_semantic_reconstruction", "warehouse_first_refactor"}
SHA = re.compile(r"[a-f0-9]{64}\Z")
BEHAVIOR_FIELDS = ("field_ids", "measure_ids", "grouping_ids", "sort_ids", "filter_ids",
    "filter_context_ids", "control_ids", "interaction_ids", "drill_ids", "visualization_ids",
    "formatting_ids", "layout_ids", "responsive_ids", "security_ids", "persona_ids", "operation_ids")
SECRET_KEYS = {"authorization", "password", "clientsecret", "accesstoken", "refreshtoken",
    "bearertoken", "producttoken", "dataflowtoken", "xdomodevelopertoken", "developertoken",
    "apikey", "apitoken", "privatekey", "credentials"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Bridge:
    def __init__(self, helpers):
        for name, function in helpers.items():
            setattr(self, name, function)

    def obj(self, value, code="migration.object_required"):
        self.require(type(value) is dict, code)
        return value

    def text(self, value, code="migration.identity_required"):
        self.require(type(value) is str and self.identity(value) is not None, code)
        return value

    def strings(self, value, code="migration.string_array_required", unique=True):
        self.require(type(value) is list and all(type(v) is str and v for v in value), code)
        self.require(not unique or len(value) == len(set(value)), "migration.duplicate_reference")
        return value

    def hash_value(self, value, prefix=False):
        self.require(type(value) is str and bool(SHA.fullmatch(value[7:] if prefix and value.startswith("sha256:") else value))
                     and (not prefix or value.startswith("sha256:")), "migration.invalid_hash")
        return value

    def no_credentials(self, value):
        stack = [value]
        while stack:
            current = stack.pop()
            if type(current) is dict:
                for key, child in current.items():
                    normalized = key.lower().replace("_", "").replace("-", "")
                    if normalized in SECRET_KEYS:
                        self.require(child is None or child == "" or child == "[REDACTED]" or child == {"redacted": "secret"},
                                     "migration.credential_bearing_input")
                    stack.append(child)
            elif type(current) is list:
                stack.extend(current)

    def reject_authority(self, value):
        # Only contract fields are checked; strings in source code remain inert.
        for key, child in value.items():
            if key.startswith("authorizes_") or key in ("analytical_build_authorized", "target_write_authority"):
                self.require(child is False, "migration.contradictory_authority")

    def context(self, result, payload):
        result["migration_context"] = {"source_contract": payload.get("contract_version", payload.get("schema_version", payload.get("snapshotContract"))),
            "run_id": payload.get("run_id"), "scope_id": payload.get("scope_id"),
            "migration_unit_id": payload.get("migration_unit_id"),
            "classification": payload.get("classification"), "synthetic": payload.get("synthetic"),
            "route": None, "route_status": "not_supplied", "upstream_write_permitted": False,
            "target_write_authority": False, "build_authority": False,
            "store_backed_readiness": "not_verified", "acceptance": "not_established",
            "hash_validation": "input_bytes_only", "source_reverification": "not_performed"}
        self.gap(result, "migration.import_does_not_register_or_authorize")

    def asset(self, result, kind, row, path, source_id, scope=None, fields=None, **identity):
        facets = fields or {"query": {"status": "declared", "value": row},
                            "interactions": {"status": "needs_review", "value": None},
                            "security": {"status": "needs_review", "value": None}}
        return self.add_asset(result, kind, row, path, source_id, scope, facets,
                              id_kind=identity.pop("id_kind", "native_id"), source_identity=identity)

    def dependency(self, result, source, target, relation, path, known=None):
        self.text(source); self.text(target); self.text(relation)
        resolved = known is not None and source in known and target in known
        result["dependencies"].append({"from_source_key": source, "to_source_key": target,
            "relation": relation, "source_path": path, "status": "supplied_graph_binding" if resolved else "unresolved"})
        if known is not None and not resolved:
            self.gap(result, "migration.dangling_relationship", path)

    def domo_bundle(self, result, bundle, prefix=""):
        self.require(bundle.get("contract_version") == "omnikit.domo.evidence.v1", "domo.unsupported_bundle")
        self.require(bundle.get("mode") in ("api", "manual", "hybrid"), "domo.invalid_acquisition_mode")
        collections = {name: self.rows(bundle.get(name), "domo.collection_required") for name in
                       ("objects", "edges", "coverage", "manual_capture_queue", "checkpoints")}
        self.strings(bundle.get("diagnostics"), unique=False)
        material = copy.deepcopy(bundle)
        declared = material.pop("bundle_fingerprint", None)
        self.hash_value(declared, True)
        for name, key in (("objects", lambda r: r["object_type"] + ":" + r["object_id"]),
                          ("edges", lambda r: r["source_key"] + "|" + r["relation"] + "|" + r["target_key"]),
                          ("coverage", lambda r: r["capability"]), ("manual_capture_queue", lambda r: r["request_id"]),
                          ("checkpoints", lambda r: r["endpoint"])):
            material[name] = sorted(material[name], key=key)
        material["diagnostics"] = sorted(set(material["diagnostics"]))
        self.require(declared == "sha256:" + sha(material), "domo.bundle_fingerprint_mismatch")
        result["migration_context"]["hash_validation"] = "supplied_bundle_fingerprint_checked_not_authenticated"
        result["upstream_coverage"] = copy.deepcopy(collections["coverage"])
        result["manual_capture_queue"] = copy.deepcopy(collections["manual_capture_queue"])
        known = set()
        for i, row in enumerate(collections["objects"]):
            native_id = self.text(row.get("object_id")); object_type = self.text(row.get("object_type"))
            key = object_type + ":" + native_id
            self.require(key not in known, "domo.duplicate_object_key"); known.add(key)
            attrs = self.obj(row.get("attributes"))
            state = row.get("redaction_state")
            self.require(state in ("not_required", "redacted", "tokenized") or
                         (not attrs and row.get("title") is None), "domo.unsanitized_object")
            self.require(row.get("definition_state") in ("definition_complete", "definition_partial", "metadata_only", "manual_capture_required", "blocked"), "domo.invalid_definition_state")
            kind = {"page": "page", "subpage": "page", "card": "visual", "app_studio_app": "app", "custom_app": "app"}.get(object_type, "definition")
            self.asset(result, kind, row, prefix + "/objects/" + str(i), native_id,
                self.text(row.get("tenant_ref")) + "/" + object_type,
                {"visual": self.facet(attrs, ("metadata", "definition", "card_definition", "chart")),
                 "query": {"status": "declared", "value": attrs},
                 "layout": self.facet(attrs, ("layout", "placements", "page_definition", "definition")),
                 "filters": self.facet(attrs, ("filters", "variables", "definition")),
                 "interactions": self.facet(attrs, ("interactions", "drill", "definition")),
                 "security": {"status": "declared", "value": {"object_type": object_type, "attributes": attrs,
                     "visibility_principal_ref": row.get("visibility_principal_ref"), "permission_context_ref": row.get("permission_context_ref")}},
                 "content": self.facet(row, ("title",))}, object_key=key, definition_state=row["definition_state"])
            if row["definition_state"] != "definition_complete":
                self.gap(result, "domo.definition_incomplete", prefix + "/objects/" + str(i), {"object_key": key, "state": row["definition_state"]})
        for i, row in enumerate(collections["edges"]):
            self.dependency(result, row.get("source_key"), row.get("target_key"), row.get("relation"), prefix + "/edges/" + str(i), known)
        for i, row in enumerate(collections["coverage"]):
            self.require(row.get("status") in ("complete", "partial", "blocked", "not_requested"), "domo.invalid_coverage_status")
            self.require(not (row["status"] == "complete" and row.get("truncated") is True), "domo.contradictory_coverage")
            self.strings(row.get("object_keys")); self.strings(row.get("gaps"), unique=False)
            if row["status"] != "complete" or row["gaps"] or row.get("truncated"):
                self.gap(result, "domo.upstream_coverage_gap", prefix + "/coverage/" + str(i), row)
            if not set(row["object_keys"]) <= known:
                self.gap(result, "domo.coverage_references_missing_objects", prefix + "/coverage/" + str(i))
        for name in ("manual_capture_queue", "checkpoints", "diagnostics"):
            for i, row in enumerate(bundle[name]):
                if name != "checkpoints" or row.get("complete") is not True or row.get("truncated") or row.get("warnings"):
                    self.gap(result, "domo.upstream_" + name, prefix + "/" + name + "/" + str(i), row)

    def domo_plan(self, result, payload):
        source = self.obj(payload.get("source")); context = self.obj(source.get("context"))
        page = self.obj(source.get("page")); page_id = self.text(page.get("object_id"))
        self.require(context.get("page_id") == page_id, "domo.page_context_mismatch")
        self.require(payload.get("proposal_only") is True, "domo.plan_must_be_proposal")
        self.reject_authority(payload)
        for field in ("run_id", "scope_id", "migration_unit_id"):
            self.require(self.text(payload.get(field)) == context.get(field), "domo.plan_scope_mismatch")
        for key in ("plan_hash",): self.hash_value(payload.get(key), True)
        self.obj(payload.get("security_metadata")); self.obj(payload.get("provenance"))
        cards = self.rows(source.get("cards"), "domo.cards_required")
        queries = self.rows(source.get("queries"), "domo.queries_required")
        placements = self.rows(source.get("placements"), "domo.placements_required")
        card_ids = [self.text(self.obj(c.get("card")).get("object_id")) for c in cards]
        query_ids = [self.text(self.obj(q.get("query")).get("object_id")) for q in queries]
        placement_ids = [self.text(p.get("placement_id")) for p in placements]
        self.require(len(set(card_ids)) == len(cards) and len(set(query_ids)) == len(queries)
                     and len(set(placement_ids)) == len(placements), "domo.duplicate_denominator")
        for order, expected in (("source_card_order", card_ids), ("source_placement_order", placement_ids)):
            self.require(set(self.strings(context.get(order))) == set(expected), "domo.source_order_denominator_mismatch")
        for name, field, expected in (("card_mappings", "source_card_id", card_ids), ("query_mappings", "query_id", query_ids)):
            mapping_rows = self.rows(payload.get(name), "domo.mapping_required")
            values = [self.text(m.get(field)) for m in mapping_rows]
            self.require(len(values) == len(set(values)), "domo.duplicate_mapping")
            if set(values) != set(expected):
                self.gap(result, "domo.incomplete_" + name, "/" + name,
                         {"missing": sorted(set(expected) - set(values)), "extra": sorted(set(values) - set(expected))})
        query_by_id = dict(zip(query_ids, queries))
        placement_by_id = dict(zip(placement_ids, placements))
        for card, cid in zip(cards, card_ids):
            ids = self.strings(card.get("query_ids"))
            self.require(all(qid in query_by_id and query_by_id[qid].get("card_id") == cid for qid in ids), "domo.card_query_mismatch")
        self.asset(result, "page", source, "/source", None, page_id,
            {"layout": {"status": "declared", "value": {"placements": placements, "source_card_order": context["source_card_order"], "source_placement_order": context["source_placement_order"]}},
             "security": {"status": "declared", "value": payload["security_metadata"]}},
            id_kind="native_id_not_supplied", object_id=page_id)
        for i, (card, cid) in enumerate(zip(cards, card_ids)):
            self.asset(result, "visual", card, "/source/cards/" + str(i), None, cid,
                       object_id=cid, id_kind="native_id_not_supplied")
        for i, placement in enumerate(placements):
            self.require(placement.get("page_id") == page_id and placement.get("card_id") in card_ids,
                         "domo.placement_membership_mismatch")
            self.asset(result, "layout", placement, "/source/placements/" + str(i), None, placement_ids[i],
                {"layout": {"status": "declared", "value": placement}},
                placement_id=placement_ids[i], id_kind="contract_placement_id_not_native")
        behavior_ids = set()
        for i, (query, qid) in enumerate(zip(queries, query_ids)):
            self.require(query.get("card_id") in card_ids, "domo.query_card_mismatch")
            self.require(qid in cards[card_ids.index(query["card_id"])]["query_ids"], "domo.query_membership_mismatch")
            for pid in self.strings(query.get("placement_ids")):
                self.require(pid in placement_by_id and placement_by_id[pid]["card_id"] == query["card_id"], "domo.query_placement_mismatch")
            behaviors = self.rows(query.get("behaviors"), "domo.behaviors_required")
            observed = [self.text(b.get("behavior_id")) for b in behaviors]
            denominator = self.obj(query.get("behavior_denominator"))
            declared = [bid for field in BEHAVIOR_FIELDS for bid in self.strings(denominator.get(field))]
            self.require(len(observed) == len(set(observed)) and len(declared) == len(set(declared)), "domo.duplicate_behavior")
            if set(observed) != set(declared): self.gap(result, "domo.query_behavior_denominator_mismatch", "/source/queries/" + str(i))
            mapping = next((m for m in payload["query_mappings"] if m["query_id"] == qid), None)
            mapping_names = ("fields", "measures", "groupings", "sorts", "filters", "filter_contexts", "controls",
                             "interactions", "drills", "visualizations", "formatting", "layouts", "responsive", "security", "personas", "operations")
            if mapping is not None and mapping.get("outcome") == "mapped":
                for field, name in zip(BEHAVIOR_FIELDS, mapping_names):
                    if name not in mapping:
                        self.gap(result, "domo.query_behavior_mapping_not_supplied", "/query_mappings", {"query_id": qid, "facet": name})
                        continue
                    bound = [m.get("source_behavior_id") for m in self.rows(mapping[name], "domo.invalid_behavior_mapping")]
                    self.require(all(type(bid) is str for bid in bound), "domo.mapping_behavior_identity_required")
                    if len(bound) != len(set(bound)) or set(bound) != set(denominator[field]):
                        self.gap(result, "domo.query_behavior_mapping_gap", "/query_mappings", {"query_id": qid, "facet": name,
                            "missing": sorted(set(denominator[field]) - set(bound)), "extra": sorted(set(bound) - set(denominator[field]))})
            elif mapping is not None:
                self.gap(result, "domo.query_disposition_requires_source_store", "/query_mappings", {"query_id": qid})
            behavior_ids.update(observed)
            self.asset(result, "query", query, "/source/queries/" + str(i), None, qid,
                {"query": {"status": "declared", "value": query},
                 "filters": {"status": "declared", "value": {k: denominator[k] for k in ("filter_ids", "filter_context_ids", "control_ids")}},
                 "security": {"status": "declared", "value": {k: denominator[k] for k in ("security_ids", "persona_ids")}}},
                object_id=qid, id_kind="native_id_not_supplied")
        specials = self.rows(source.get("special_behaviors"), "domo.special_behaviors_required")
        resolutions = self.rows(payload.get("behavior_resolutions"), "domo.resolutions_required")
        resolved_ids = [self.text(r.get("source_behavior_id")) for r in resolutions]
        self.require(len(resolved_ids) == len(set(resolved_ids)), "domo.duplicate_behavior_resolution")
        for i, behavior in enumerate(specials):
            bid = self.text(behavior.get("behavior_id")); behavior_ids.add(bid)
            self.asset(result, "definition", behavior, "/source/special_behaviors/" + str(i), None, bid,
                       behavior_id=bid, id_kind="contract_behavior_id_not_native")
            found = [r for r in resolutions if r["source_behavior_id"] == bid]
            if not found or found[0].get("status") != "accepted":
                self.gap(result, "domo.special_behavior_unresolved", "/source/special_behaviors/" + str(i), behavior)
        if not set(resolved_ids) <= behavior_ids:
            self.gap(result, "domo.resolution_outside_denominator", "/behavior_resolutions")
        result["migration_context"].update({"page_id": page_id, "source_context": copy.deepcopy(context),
            "plan_hash": payload["plan_hash"], "plan_hash_verification": "retained_not_recomputed",
            "source_denominator": copy.deepcopy(source), "target_proposal": {k: copy.deepcopy(payload[k]) for k in
                ("target", "page_mapping", "card_mappings", "query_mappings", "topic_bindings", "profile_bindings", "decision_bindings", "behavior_resolutions") if k in payload}})
        self.gap(result, "domo.plan_registration_and_component_hashes_require_source_store")

    def domo_handoff(self, result, payload):
        self.reject_authority(payload)
        self.require(payload.get("assignment_only") is True, "domo.handoff_assignment_only_required")
        self.require(payload.get("capability") in ("application_redesign", "operations_governance", "platform_ingestion"), "domo.unsupported_handoff_capability")
        decision = self.obj(payload.get("accepted_decision"))
        self.require(decision.get("status") == "accepted" and self.text(decision.get("accepted_by_ref")).startswith("human-ref://"), "domo.human_decision_declaration_required")
        self.text(payload.get("owner_ref")); self.text(payload.get("handoff_ref"))
        self.hash_value(payload.get("handoff_hash"), True)
        material = {k: v for k, v in payload.items() if k != "handoff_hash"}
        self.require(payload["handoff_hash"] == "sha256:" + sha(material), "domo.handoff_hash_mismatch")
        self.strings(payload.get("side_effect_kinds")); self.strings(payload.get("evidence_refs"))
        for name in ("source_objects", "analytic_outputs"):
            for i, row in enumerate(self.rows(payload.get(name), "domo.handoff_objects_required")):
                self.hash_value(row.get("object_hash"), True)
                object_type = self.text(row.get("object_type")); native = self.text(row.get("native_id"))
                kind = "app" if object_type in ("app_studio_app", "custom_app") else "definition"
                self.asset(result, kind, row, "/" + name + "/" + str(i), native, object_type,
                    object_id=self.text(row.get("object_id")), object_type=object_type)
        result["migration_context"].update({"handoff_id": payload.get("handoff_id"), "capability": payload["capability"],
            "owner_ref": payload["owner_ref"], "side_effect_kinds": payload["side_effect_kinds"],
            "assignment_only": True, "decision_verification": "reference_only_not_authenticated",
            "hash_validation": "supplied_handoff_hash_checked_not_authenticated"})
        self.gap(result, "domo.external_handoff_assigns_work_only")

    def sigma_envelope(self, result, payload):
        self.hash_value(payload.get("content_hash"))
        self.text(payload.get("artifact_id")); self.text(payload.get("producer"))
        self.strings(payload.get("source_references"))
        for item in self.rows(payload.get("upstream_hashes"), "sigma.upstream_hashes_required"):
            self.text(item.get("artifact_id")); self.hash_value(item.get("content_hash"))
        self.require(payload["content_hash"] == sha({k: v for k, v in payload.items() if k != "content_hash"}), "sigma.artifact_hash_mismatch")
        result["migration_context"].update({"artifact_id": payload["artifact_id"], "content_hash": payload["content_hash"],
            "upstream_hashes": payload["upstream_hashes"], "hash_validation": "supplied_artifact_hash_checked_not_authenticated"})
        if payload.get("supersession_state", "current") != "current":
            self.gap(result, "sigma.superseded_artifact")
        return self.obj(payload.get("payload"))

    def sigma_id(self, row, *keys, required=True):
        values = [self.identity(row[key]) for key in keys if row.get(key) is not None]
        self.require(all(v is not None for v in values) and len(set(values)) <= 1,
                     "sigma.conflicting_or_invalid_identity_alias")
        self.require(values or not required, "sigma.identity_required")
        return values[0] if values else None

    def sigma_workbook(self, result, workbook, path):
        wid = self.sigma_id(workbook, "workbookId", "id")
        self.asset(result, "workbook", workbook, path, wid, "workbook", {
            "layout": self.facet(workbook, ("pages", "elements")),
            "filters": self.facet(workbook, ("controls",)),
            "interactions": self.facet(workbook, ("controls", "schedules", "bookmarks")),
            "security": self.facet(workbook, ("grants",), "declared")})
        pages = self.rows(workbook.get("pages"), "sigma.pages_required")
        page_ids = [self.sigma_id(row, "pageId", "id") for row in pages]
        self.require(len(page_ids) == len(set(page_ids)), "sigma.duplicate_page")
        bulk, placements, controls = {}, {}, set()
        for i, row in enumerate(self.rows(workbook.get("elements", []), "sigma.elements_invalid")):
            eid = self.sigma_id(row, "elementId", "id")
            self.require(eid not in bulk, "sigma.duplicate_element")
            bulk[eid] = (row, path + "/elements/" + str(i))

        def project(row, locator, pid, origin):
            eid = self.sigma_id(row, "elementId", "id")
            kind = row.get("type", row.get("kind"))
            self.asset(result, "visual" if kind in ("chart", "table", "visualization") else "definition", row,
                locator, eid, wid + "/page:" + str(pid), {
                    "visual": self.facet(row, ("type", "kind", "visualizationType", "vizualizationType", "columns")),
                    "query": {"status": "declared", "value": row},
                    "layout": self.facet(row, ("layout", "position", "pageId")),
                    "filters": self.facet(row, ("filters", "controls")),
                    "interactions": {"status": "needs_review", "value": None}},
                page_id=pid, workbook_id=wid, placement_evidence=origin)

        for pi, page in enumerate(pages):
            pid = page_ids[pi]; pp = path + "/pages/" + str(pi)
            self.asset(result, "page", page, pp, pid, wid, {"layout": {"status": "declared", "value": page}})
            seen = set()
            for ei, row in enumerate(self.rows(page.get("elements"), "sigma.elements_required")):
                eid = self.sigma_id(row, "elementId", "id")
                self.require(eid not in seen, "sigma.duplicate_element"); seen.add(eid)
                self.require(row.get("pageId") is None or self.identity(row["pageId"]) == pid, "sigma.element_page_mismatch")
                if eid in bulk:
                    other = bulk[eid][0]
                    # Aliases and placement geometry may differ; overlapping definition fields may not.
                    for key in set(row) & set(other) - {"id", "elementId", "pageId", "layout", "position"}:
                        self.require(row[key] == other[key], "sigma.conflicting_element_definition")
                    self.require(other.get("pageId") is None or self.identity(other["pageId"]) == pid,
                                 "sigma.element_page_mismatch")
                placements.setdefault(eid, set()).add(pid)
                project(row, pp + "/elements/" + str(ei), pid, "page_membership")
        for eid, (row, locator) in bulk.items():
            if eid in placements:
                continue
            pid = self.identity(row.get("pageId")) if row.get("pageId") is not None else None
            self.require(row.get("pageId") is None or pid in page_ids, "sigma.orphan_element_page")
            placements[eid] = {pid}
            project(row, locator, pid, "bulk_page_reference" if pid is not None else "unresolved")
            self.gap(result, "sigma.bulk_only_placement_requires_review", locator)
        for ci, control in enumerate(self.rows(workbook.get("controls", []), "sigma.controls_invalid")):
            cid = self.sigma_id(control, "controlId", "elementId", "id", required=False)
            if cid is not None:
                self.require(cid not in controls, "sigma.duplicate_control"); controls.add(cid)
            cp = path + "/controls/" + str(ci)
            self.asset(result, "filter", control, cp, cid, wid, {"filters": {"status": "declared", "value": control}})
            self.gap(result, "sigma.control_binding_requires_review", cp)
        if "controls" not in workbook:
            self.gap(result, "sigma.controls_not_supplied", path)
        return wid, set(placements), controls

    def sigma_snapshot(self, result, payload):
        acquisition = self.obj(payload.get("_omnikit_acquisition", {}))
        if "_omnikit_acquisition" in payload:
            self.require(acquisition.get("contract") == "sigma-api-v2", "sigma.unsupported_snapshot")
        markers = [v for v in (payload.get("snapshotContract"), acquisition.get("contract")) if v is not None]
        self.require(markers and all(v == "sigma-api-v2" for v in markers), "sigma.unsupported_snapshot")
        self.rows(payload.get("connections"), "sigma.connections_required")
        result["migration_context"]["source_contract"] = "sigma-api-v2"
        result["migration_context"]["snapshot_profile"] = "api_acquisition" if acquisition else "legacy_declared_snapshot"
        element_ids, control_ids, workbook_ids, model_ids = {}, {}, set(), set()
        for mi, model in enumerate(self.rows(payload.get("dataModels"), "sigma.models_required")):
            mid = self.sigma_id(model, "dataModelId", "id"); spec = self.obj(model.get("spec"))
            self.require(mid not in model_ids, "sigma.duplicate_model"); model_ids.add(mid)
            self.require(self.sigma_id(spec, "dataModelId", "id", required=False) in (None, mid), "sigma.model_identity_mismatch")
            self.asset(result, "definition", model, "/dataModels/" + str(mi), mid, "data_model", source_object_type="data_model")
            for pi, page in enumerate(self.rows(spec.get("pages", []), "sigma.model_pages_invalid")):
                for ei, element in enumerate(self.rows(page.get("elements", []), "sigma.model_elements_invalid")):
                    eid = self.sigma_id(element, "elementId", "id")
                    self.asset(result, "definition", element, f"/dataModels/{mi}/spec/pages/{pi}/elements/{ei}", eid, "data-model:" + mid,
                        {"query": {"status": "declared", "value": element}}, source_object_type="model_element")
        for wi, workbook in enumerate(self.rows(payload.get("workbooks"), "sigma.workbooks_required")):
            wid, elements, controls = self.sigma_workbook(result, workbook, f"/workbooks/{wi}")
            self.require(wid not in workbook_ids, "sigma.duplicate_workbook"); workbook_ids.add(wid)
            element_ids[wid], control_ids[wid] = elements, controls
        if acquisition:
            for field, known in (("selectedWorkbookIds", workbook_ids), ("selectedDataModelIds", model_ids)):
                self.require(set(self.strings(acquisition.get(field))) == known, "sigma.acquisition_selection_mismatch")
            result["migration_context"]["acquisition"] = copy.deepcopy(acquisition)
        original_hash = sha({k: v for k, v in payload.items() if k not in ("prepush_context", "_migration_scope")})
        if payload.get("prepush_context") is not None:
            context = self.obj(payload["prepush_context"])
            self.require(context.get("schema_version") == "sigma-prepush-context.v1" and context.get("source_sha256") == original_hash, "sigma.context_stale_or_invalid")
            wid = self.text(context.get("workbook_id")); self.require(wid in workbook_ids, "sigma.context_workbook_missing")
            for name, known in (("elements", element_ids[wid]), ("controls", control_ids[wid])):
                items = self.obj(context.get(name))
                self.require(set(items) <= known, "sigma.context_unknown_identity")
                for key, value in items.items():
                    self.obj(value)
                    if name == "controls":
                        self.require(set(self.strings(value.get("target_element_ids"))) <= element_ids[wid], "sigma.context_unknown_control_target")
            result["migration_context"]["source_context"] = copy.deepcopy(context)
            self.gap(result, "sigma.context_is_supplied_observation_not_native_authority")
        if payload.get("_migration_scope") is not None:
            scope = self.obj(payload["_migration_scope"])
            self.require(scope.get("schema_version") == "sigma-migration-scope.v1" and scope.get("original_source_sha256") == original_hash,
                         "sigma.scope_stale_or_invalid")
            self.reject_authority(scope)
            result["migration_context"]["pilot_scope"] = copy.deepcopy(scope)
            self.gap(result, "sigma.scope_exclusions_not_rederived_full_source_retained")
        for name in ("gaps", "diagnostics", "documentedOmissions"):
            if payload.get(name): self.gap(result, "sigma.upstream_" + name, "/" + name, payload[name])
        result["migration_context"]["original_source_sha256"] = original_hash
        self.gap(result, "sigma.native_layout_controls_permissions_and_freeze_require_validation")

    def sigma_capability_bundle(self, result, payload):
        self.text(payload.get("run_id")); self.text(payload.get("scope_id"))
        self.require(payload.get("status") in ("ready_for_human_review", "blocked"), "sigma.invalid_bundle_status")
        self.strings(payload.get("blockers"), unique=False)
        self.rows(payload.get("gate_recommendations"), "sigma.bundle_gate_recommendations_required")
        observations = self.rows(payload.get("observations"), "sigma.observations_required")
        named = [("run_manifest", self.obj(payload.get("run_manifest"))),
                 *[("observations/" + str(i), row) for i, row in enumerate(observations)],
                 *[(key, self.obj(payload.get(key))) for key in
                   ("capability_matrix", "workbook_graph", "data_model_snapshot", "behavior_manifest")]]
        original_context = copy.deepcopy(result["migration_context"])
        by_id, data = {}, {}
        for key, artifact in named:
            self.require(all(artifact.get(k) == payload[k] for k in ("run_id", "scope_id")), "sigma.bundle_scope_mismatch")
            expected_schema = ("sigma-observation.v1" if key.startswith("observations/") else
                               "sigma-api-capability-matrix.v1" if key == "capability_matrix" else
                               "sigma-" + key.replace("_", "-") + ".v1")
            self.require(artifact.get("schema_version") == expected_schema, "sigma.bundle_component_schema")
            data[key] = self.sigma_envelope(result, artifact)
            self.require(artifact["artifact_id"] not in by_id, "sigma.bundle_duplicate_artifact")
            by_id[artifact["artifact_id"]] = artifact
        manifest = data["run_manifest"]
        for field in ("workbook_id", "data_model_id", "organization_ref", "principal_ref", "authorization_ref"):
            self.text(manifest.get(field))
        self.obj(manifest.get("source_freeze")); self.reject_authority(manifest)
        for key, artifact in named:
            required = [] if key == "run_manifest" else [payload["run_manifest"]]
            if key in ("capability_matrix", "workbook_graph", "data_model_snapshot"):
                required += observations
            elif key == "behavior_manifest":
                required += [payload["capability_matrix"], payload["workbook_graph"]]
            expected = [{"artifact_id": row["artifact_id"], "content_hash": row["content_hash"]} for row in required]
            self.require(artifact["upstream_hashes"] == expected, "sigma.bundle_upstream_mismatch")
            if key.startswith("observations/"):
                self.require(all(data[key].get(k) == manifest.get(k) for k in
                    ("organization_ref", "principal_ref", "effective_account_type", "authorization_ref")), "sigma.bundle_principal_mismatch")
        for key in ("capability_matrix", "workbook_graph", "behavior_manifest"):
            self.require(data[key].get("workbook_id") == manifest.get("workbook_id"), "sigma.bundle_workbook_mismatch")
        self.require(data["data_model_snapshot"].get("data_model_id") == manifest.get("data_model_id"), "sigma.bundle_model_mismatch")
        for key in ("workbook_graph", "data_model_snapshot"):
            self.require(data[key].get("source_freeze") == manifest.get("source_freeze"), "sigma.bundle_freeze_mismatch")
        expected_class = "observed_tenant_behavior" if manifest.get("evidence_mode") == "live_tenant" else "synthetic_fixture"
        self.require(manifest.get("evidence_mode") in ("live_tenant", "synthetic_fixture"), "sigma.bundle_evidence_mode")
        self.require(all(row.get("classification") == expected_class for key, row in named
                         if key not in ("run_manifest", "behavior_manifest")), "sigma.bundle_classification_mismatch")
        self.require(data["capability_matrix"].get("live_tenant_evidence") == (manifest["evidence_mode"] == "live_tenant"),
                     "sigma.bundle_evidence_mode")
        if data["data_model_snapshot"].get("specification_state") != "bound":
            self.require(payload["status"] == "blocked", "sigma.bundle_unavailable_specification")
        component_contexts = {}
        for key in ("workbook_graph", "data_model_snapshot", "behavior_manifest"):
            result["migration_context"] = copy.deepcopy(original_context)
            self.sigma_artifact(result, payload[key], prefix="/" + key)
            component_contexts[key] = copy.deepcopy(result["migration_context"])
        result["migration_context"] = original_context
        result["migration_context"].update({"source_freeze": copy.deepcopy(manifest.get("source_freeze")),
            "capability_bundle": copy.deepcopy({k: payload[k] for k in ("status", "blockers", "gate_recommendations")}),
            "component_hashes": {key: row["content_hash"] for key, row in named},
            "component_contexts": component_contexts,
            "hash_validation": "supplied_component_hashes_and_shared_bindings_checked_not_authenticated"})
        self.gap(result, "sigma.capability_bundle_runtime_gates_not_revalidated")

    def sigma_visual_capture(self, result, payload):
        from pathlib import PurePosixPath
        self.require(payload.get("content_hash") == sha({k: v for k, v in payload.items() if k != "content_hash"}),
                     "sigma.visual_capture_hash_mismatch")
        request = self.obj(payload.get("request")); original = self.obj(payload.get("original_request"))
        self.require(payload.get("request_sha256") == sha(request) and payload.get("original_request_sha256") == sha(original),
                     "sigma.visual_request_hash_mismatch")
        def includes_defaults(effective, supplied):
            if type(supplied) is dict:
                return type(effective) is dict and all(k in effective and includes_defaults(effective[k], v) for k, v in supplied.items())
            return effective == supplied
        self.require(includes_defaults(request, original),
                     "sigma.visual_original_request_mismatch")
        self.require(request.get("schema_version") == "sigma-visual-capture-request.v1" and
                     payload.get("capture_id") == request.get("capture_id"), "sigma.visual_request_identity")
        self.text(payload.get("capture_id"))
        for key in ("workbook_id", "page_id", "element_id", "data_model_id", "expected_organization_id", "expected_user_id"):
            self.text(request.get(key))
        freeze = self.obj(request.get("source_freeze"))
        self.require(freeze.get("strategy") == "version_tag", "sigma.visual_tag_required")
        tag = self.text(freeze.get("workbook_tag_name"))
        self.require(payload.get("status") in ("complete", "partial", "blocked") and
                     payload.get("target_write_authority") is False and payload.get("native_validation") == "not_performed" and
                     payload.get("business_acceptance") == "not_assessed", "sigma.visual_invalid_status_or_authority")
        self.require(type(payload.get("journal_revision")) is int and payload["journal_revision"] >= 1,
                     "sigma.visual_journal_revision")
        if payload.get("previous_content_hash") is not None:
            self.hash_value(payload["previous_content_hash"])
        self.strings(payload.get("gaps"), unique=False)
        self.require(request.get("evidence_mode") in ("synthetic_fixture", "live_tenant") and
                     payload.get("evidence_mode") == request["evidence_mode"], "sigma.visual_evidence_mode")
        jobs = self.rows(payload.get("jobs"), "sigma.visual_jobs_required")
        self.require(len(jobs) == 2 and {j.get("kind") for j in jobs} == {"png", "json"}, "sigma.visual_job_set")
        by_kind = {}
        for job in jobs:
            kind = job["kind"]
            expected = {"tag": tag, "elementId": request["element_id"], "parameters": request.get("parameters"), "format": {"type": kind}}
            if kind == "json": expected["rowLimit"] = request.get("row_limit")
            self.require(job.get("request_body") == expected and job.get("request_sha256") == sha(expected), "sigma.visual_job_request_mismatch")
            self.text(job.get("status"))
            if job.get("query_id") is not None: self.text(job["query_id"])
            if job.get("creation_response") is not None:
                self.require(self.obj(job["creation_response"]).get("queryId") == job.get("query_id"), "sigma.visual_job_query_mismatch")
            by_kind[kind] = job
        source = payload.get("source")
        attachments = self.rows(payload.get("attachments"), "sigma.visual_attachments_required")
        if source is None:
            self.require(not attachments and payload["status"] != "complete" and
                         all(job.get("status") != "downloaded" for job in jobs), "sigma.visual_source_missing")
            self.gap(result, "sigma.visual_source_not_captured")
        else:
            self.obj(source); snapshot = self.obj(source.get("tagged_snapshot"))
            self.require(source.get("tagged_snapshot_sha256") == sha(snapshot), "sigma.visual_snapshot_hash_mismatch")
            self.require(snapshot.get("workbookId") == request["workbook_id"] and snapshot.get("tag") == tag,
                         "sigma.visual_selection_mismatch")
            self.require(snapshot.get("revisionEvidenceSha256") == sha(self.obj(snapshot.get("revisionEvidence"))),
                         "sigma.visual_revision_hash_mismatch")
            self.require(snapshot.get("coherence") == "unchanged_before_after_not_atomic" and
                         source.get("coherence") == snapshot["coherence"], "sigma.visual_coherence_mismatch")
            baseline = self.obj(source.get("baseline")); identity = self.obj(baseline.get("identity"))
            self.require(identity.get("organizationId") == request["expected_organization_id"] and
                         identity.get("userId") == request["expected_user_id"], "sigma.visual_principal_mismatch")
            def coherence(value):
                identity = self.obj(value.get("identity"))
                return sha({**value, "identity": {key: identity.get(key) for key in ("organizationId", "userId")}})
            self.require(source.get("baseline_sha256") == sha(baseline) and
                         source.get("coherence_sha256") == coherence(baseline), "sigma.visual_baseline_hash_mismatch")
            self.require(snapshot["revisionEvidence"] == {"workbook": baseline.get("workbook"), "tags": baseline.get("tags")},
                         "sigma.visual_baseline_revision_mismatch")
            self.require(self.sigma_id(self.obj(baseline.get("workbook")), "workbookId", "id") == request["workbook_id"],
                         "sigma.visual_baseline_workbook_mismatch")
            tags = [row for row in self.rows(baseline.get("tags"), "sigma.visual_tags_required")
                    if (row.get("tagName") or row.get("name")) == tag]
            self.require(len(tags) == 1, "sigma.visual_selected_tag_missing_or_ambiguous")
            versions = {str(tags[0][key]) for key in ("sourceVersion", "version", "workbookVersion")
                        if tags[0].get(key) is not None}
            self.require(len(versions) == 1 and baseline.get("tag_source_version") in versions,
                         "sigma.visual_tag_version_mismatch")
            model = self.obj(baseline.get("data_model_specification"))
            self.require(self.sigma_id(model, "dataModelId", "id") == request["data_model_id"] and
                         str(model.get("documentVersion")) == str(freeze.get("data_model_document_version")), "sigma.visual_model_mismatch")
            self.sigma_workbook(result, snapshot, "/source/tagged_snapshot")
            selected = [a for a in result["assets"] if a["source_id"] == request["element_id"] and
                        a["source_identity"].get("page_id") == request["page_id"]]
            self.require(len(selected) == 1, "sigma.visual_selected_placement_missing")
            if source.get("final_observation") is not None:
                self.require(source.get("final_observation_sha256") == sha(self.obj(source["final_observation"])),
                             "sigma.visual_final_observation_hash_mismatch")
                same = coherence(source["final_observation"]) == source["coherence_sha256"]
                self.require(same or payload["status"] == "blocked", "sigma.visual_final_observation_changed")
                if not same: self.gap(result, "sigma.visual_source_changed_capture_blocked")
            if payload["status"] == "complete":
                self.require(source.get("final_observation") is not None, "sigma.visual_final_observation_missing")
            seen, paths = set(), set()
            for attachment in attachments:
                kind = attachment.get("format")
                self.require(kind in by_kind and kind not in seen, "sigma.visual_attachment_set"); seen.add(kind)
                job = by_kind[kind]
                self.require(attachment.get("query_id") == job.get("query_id") and job.get("query_id") is not None and
                             job.get("status") == "downloaded", "sigma.visual_attachment_job_mismatch")
                for key in ("capture_id", "workbook_id", "page_id", "element_id"):
                    self.require(attachment.get(key) == request.get(key), "sigma.visual_attachment_identity_mismatch")
                self.require(attachment.get("request_sha256") == payload["request_sha256"] and
                             attachment.get("source_snapshot_sha256") == source["tagged_snapshot_sha256"], "sigma.visual_attachment_pin_mismatch")
                path = self.text(attachment.get("path")); parsed = PurePosixPath(path)
                self.require(not parsed.is_absolute() and ".." not in parsed.parts and parsed.as_posix() == path and
                             "\\" not in path and path not in (".", ""), "sigma.visual_attachment_path_invalid")
                self.require(path not in paths, "sigma.visual_attachment_path_duplicate"); paths.add(path)
                self.hash_value(attachment.get("sha256"))
                self.require(type(attachment.get("bytes")) is int and attachment["bytes"] > 0, "sigma.visual_attachment_size_invalid")
            self.require({kind for kind, job in by_kind.items() if job.get("status") == "downloaded"} == seen,
                         "sigma.visual_downloaded_attachment_missing")
            if payload["status"] == "complete":
                self.require(seen == {"png", "json"}, "sigma.visual_complete_missing_files")
        result["migration_context"]["visual_capture"] = copy.deepcopy({k: payload[k] for k in
            ("capture_id", "request", "request_sha256", "content_hash", "status", "jobs", "attachments", "gaps", "journal_revision")})
        result["migration_context"]["hash_validation"] = "supplied_visual_capture_and_embedded_pins_checked_not_authenticated"
        for item in payload["gaps"]: self.gap(result, "sigma.visual_capture_gap", "/gaps", item)
        self.gap(result, "sigma.visual_attachment_bytes_and_journal_history_not_read")
        self.gap(result, "sigma.visual_capture_completeness_privacy_and_native_parity_not_verified")

    def sigma_artifact(self, result, payload, prefix=""):
        data = self.sigma_envelope(result, payload); schema = payload["schema_version"]
        self.reject_authority(data)
        if schema == "sigma-workbook-graph.v1":
            wid = self.text(data.get("workbook_id")); nodes = self.rows(data.get("nodes"), "sigma.nodes_required")
            node_ids = [self.text(n.get("node_id")) for n in nodes]
            self.require(len(node_ids) == len(set(node_ids)), "sigma.duplicate_node")
            expected = [{k: self.text(n.get(k)) for k in ("node_id", "node_type", "native_id")} for n in nodes]
            self.require(data.get("exact_node_set_sha256") == sha(expected), "sigma.node_set_hash_mismatch")
            known = set(node_ids)
            for i, node in enumerate(nodes):
                self.require(node.get("parent_node_id") is None or node["parent_node_id"] in known, "sigma.orphan_parent")
                kind = {"workbook": "workbook", "page": "page", "element": "visual", "control": "filter"}.get(node["node_type"], "definition")
                self.asset(result, kind, node, prefix + "/payload/nodes/" + str(i), node["native_id"], wid + "/" + node["node_type"],
                    {"query": {"status": "declared", "value": self.obj(node.get("properties"))}}, graph_node_id=node["node_id"], parent_node_id=node.get("parent_node_id"))
            edges = self.rows(data.get("edges"), "sigma.edges_required"); seen = set()
            for i, edge in enumerate(edges):
                key = tuple(self.text(edge.get(k)) for k in ("from_node_id", "to_node_id", "relation"))
                self.require(key not in seen and key[0] in known and key[1] in known, "sigma.orphan_or_duplicate_edge"); seen.add(key)
                self.dependency(result, *key, prefix + "/payload/edges/" + str(i), known)
            for missing in self.strings(data.get("unresolved_behavior"), unique=False): self.gap(result, "sigma.unresolved_behavior", prefix + "/payload/unresolved_behavior", missing)
        elif schema == "sigma-data-model-snapshot.v1":
            mid = self.text(data.get("data_model_id")); specification = self.obj(data.get("sanitized_specification"))
            self.require(data.get("specification_sha256") == sha(specification), "sigma.specification_hash_mismatch")
            freeze = self.obj(data.get("source_freeze"))
            if data.get("specification_state") == "bound":
                self.require(specification.get("dataModelId") == mid and str(specification.get("documentVersion")) == str(freeze.get("data_model_document_version")), "sigma.specification_identity_or_version_mismatch")
            else:
                self.require(data.get("specification_state") == "unavailable" and not specification and data.get("specification_unavailability_reason"), "sigma.invalid_unavailable_specification")
                self.gap(result, "sigma.specification_unavailable", prefix + "/payload", data.get("specification_unavailability_reason"))
            self.asset(result, "definition", data, prefix + "/payload", mid, "data_model")
            for missing in self.strings(data.get("documented_omissions"), unique=False): self.gap(result, "sigma.documented_omission", prefix + "/payload/documented_omissions", missing)
            result["migration_context"]["source_bindings"] = copy.deepcopy(data.get("source_bindings", []))
        elif schema == "sigma-behavior-manifest.v1":
            wid = self.text(data.get("workbook_id")); behaviors = self.rows(data.get("behaviors"), "sigma.behaviors_required")
            ids, unresolved = set(), []
            for i, item in enumerate(behaviors):
                bid = self.text(item.get("behavior_id")); self.require(bid not in ids, "sigma.duplicate_behavior"); ids.add(bid)
                self.require(item.get("behavior_type") in ("control", "action", "input_table", "schedule", "saved_view", "embed", "layout", "formatting", "security"), "sigma.invalid_behavior_type")
                state = item.get("disposition"); self.strings(item.get("evidence_refs")); self.text(item.get("acceptance_test"))
                self.require(type(item.get("blocking")) is bool, "sigma.blocking_required")
                if state == "observed": self.require(item["evidence_refs"] and not item["blocking"], "sigma.contradictory_behavior")
                elif state == "partial": self.require(item["evidence_refs"] and item["blocking"], "sigma.contradictory_behavior")
                else:
                    self.require(state in ("manual_capture_required", "external_redesign_required") and item["blocking"]
                                 and self.text(item.get("owner_ref")).startswith("human-ref://"), "sigma.manual_behavior_owner_required")
                if item["blocking"]: unresolved.append(bid); self.gap(result, "sigma.blocking_behavior", prefix + "/payload/behaviors/" + str(i), item)
                facet_name = "security" if item["behavior_type"] == "security" else "layout" if item["behavior_type"] == "layout" else "interactions"
                self.asset(result, "definition", item, prefix + "/payload/behaviors/" + str(i), None, bid,
                    {facet_name: {"status": "declared" if state == "observed" else "needs_review", "value": item}},
                    id_kind="contract_behavior_id_not_native", behavior_id=bid, workbook_id=wid)
            self.require(data.get("unresolved_behavior_ids") == sorted(unresolved) and type(data.get("closed_denominator")) is bool
                         and data["closed_denominator"] == (not unresolved), "sigma.behavior_denominator_mismatch")
            result["migration_context"]["behavior_denominator"] = copy.deepcopy(data)
        elif schema == "sigma-semantic-routing-decision.v1":
            self.sigma_route(result, data)
            self.require(payload.get("run_id") == data.get("run_id") and payload.get("scope_id") == data.get("scope_id"), "sigma.route_scope_mismatch")
        else: raise ValueError("sigma.unsupported_artifact")
        if "source_freeze" in data:
            result["migration_context"]["source_freeze"] = copy.deepcopy(data["source_freeze"])
            self.gap(result, "sigma.source_freeze_is_declared_not_verified")

    def sigma_route(self, result, route):
        mode = route.get("mode"); self.require(mode in MODES, "sigma.explicit_route_required")
        self.require(self.text(route.get("decided_by_ref")).startswith("human-ref://") and
                     self.text(route.get("decision_ref")).startswith("human-decision-ref://"), "sigma.human_route_reference_required")
        self.hash_value(route.get("decision_record_sha256")); self.text(route.get("decision_record_revision"))
        self.text(route.get("migration_unit_id")); self.text(route.get("run_id")); self.text(route.get("scope_id"))
        comparison = self.strings(route.get("comparison_scope_refs")); build = self.strings(route.get("build_scope_refs"))
        self.require(build and set(build) <= set(comparison), "sigma.route_scope_invalid")
        targets = self.strings(route.get("target_environment_refs")); self.require(targets, "sigma.route_targets_required")
        data_targets = [t for t in targets if t.startswith(("environment-ref://dbt/", "environment-ref://warehouse/", "environment-ref://snowflake/"))]
        omni_targets = [t for t in targets if t.startswith("environment-ref://omni/")]
        self.require(len(omni_targets) == 1 and len(data_targets) + 1 == len(targets), "sigma.route_target_mismatch")
        self.require((mode == "omni_semantic_reconstruction" and not data_targets) or
                     (mode == "warehouse_first_refactor" and data_targets), "sigma.route_target_mismatch")
        if "dbt_route" in route:
            expected = "not_applicable_direct_route" if mode == "omni_semantic_reconstruction" else "required_when_approved_blueprint_places_logic_upstream"
            self.require(route["dbt_route"] == expected, "sigma.dbt_route_conflict")
        self.reject_authority(route)
        self.rows(route.get("source_context_bindings"), "sigma.source_context_bindings_required")
        self.require(route["source_context_bindings"], "sigma.source_context_bindings_required")
        for item in route["source_context_bindings"]:
            self.hash_value(item.get("content_hash")); self.text(item.get("artifact_id"))
            self.require(item.get("artifact_scope_id") == route["scope_id"], "sigma.route_source_scope_mismatch")
        result["migration_context"].update({"route": mode, "route_status": "supplied_human_reference_not_authenticated",
            "route_declaration": copy.deepcopy(route), "dbt_planning_applicable": mode != "omni_semantic_reconstruction",
            "upstream_write_permitted": False})
        self.gap(result, "sigma.route_requires_independent_source_and_human_verification")

    def sigma_package(self, result, payload):
        self.reject_authority(payload)
        mode = payload.get("route"); self.require(mode in MODES, "sigma.explicit_route_required")
        self.hash_value(payload.get("source_sha256")); self.hash_value(payload.get("target_sha256"))
        files = self.obj(payload.get("files")); self.require("source.json" in files and "target.json" in files, "sigma.package_sources_required")
        for value in files.values(): self.hash_value(value)
        review = self.obj(payload.get("review")); self.require(review.get("route") == mode and review.get("source_sha256") == payload["source_sha256"]
            and review.get("target_sha256") == payload["target_sha256"] and review.get("decision") == "accept", "sigma.package_review_mismatch")
        self.require(payload.get("target_write_authority") is False and payload.get("migration_accepted") is False, "sigma.package_not_acceptance")
        if mode == "omni_semantic_reconstruction":
            self.require(not any(name.startswith(("dbt/", "warehouse/")) for name in files), "sigma.direct_package_upstream_files")
        result["migration_context"].update({"route": mode, "route_status": "supplied_local_review_not_authenticated",
            "dbt_planning_applicable": mode != "omni_semantic_reconstruction", "package_manifest": copy.deepcopy(payload)})
        self.gap(result, "sigma.package_files_and_os_review_not_reverified")

    def parse(self, payload, raw, source_format, revision):
        platform = source_format.split("-")[0]
        self.require(revision == PINS[platform], "migration.unsupported_or_missing_producer_revision")
        self.no_credentials(payload)
        result = self.base(payload, raw, platform, "supplied_" + platform + "_migration_agent")
        result["source"]["producer"] = {"name": "DomoMigrationAgent" if platform == "domo" else "SigmaMigrationAgent",
            "revision": revision, "revision_evidence": "operator_declared_not_authenticated"}
        self.context(result, payload)
        contract = payload.get("contract_version")
        if platform == "domo":
            if contract == "omnikit.domo.evidence.v1": self.domo_bundle(result, payload)
            elif contract == "omnikit.domo.source-evidence.v1":
                self.require(type(payload.get("payload_json")) is str, "domo.payload_json_required")
                bundle = self.decode(payload["payload_json"].encode()); self.no_credentials(bundle)
                self.require(payload["payload_json"] == canonical(bundle), "domo.noncanonical_envelope_payload")
                self.require(payload.get("envelope_fingerprint") == "sha256:" + sha({k: v for k, v in payload.items() if k != "envelope_fingerprint"}), "domo.envelope_hash_mismatch")
                self.hash_value(payload.get("source_bundle_fingerprint"), True)
                self.require(payload.get("evidence_bundle_fingerprint") == bundle.get("bundle_fingerprint") and
                    payload.get("evidence_ref") == "domo-evidence://sha256/" + str(bundle.get("bundle_fingerprint", ""))[7:], "domo.envelope_reference_mismatch")
                result["decoded_source_payload"] = copy.deepcopy(bundle)
                result["source"]["projection_payload_root"] = "decoded_source_payload"
                self.domo_bundle(result, bundle, "/decoded_source_payload")
            elif contract == "domo-to-omni.dashboard-rebuild-plan.v1": self.domo_plan(result, payload)
            elif contract == "domo-to-omni.external-redesign-handoff.v1": self.domo_handoff(result, payload)
            else: raise ValueError("domo.unsupported_contract")
        else:
            schema = payload.get("schema_version")
            if "snapshotContract" in payload or "_omnikit_acquisition" in payload: self.sigma_snapshot(result, payload)
            elif schema == "sigma-capability-spike-bundle.v1": self.sigma_capability_bundle(result, payload)
            elif schema == "sigma-visual-capture.v1": self.sigma_visual_capture(result, payload)
            elif schema == "sigma-semantic-routing-decision-request.v1": self.sigma_route(result, payload)
            elif schema == "sigma-prepush-package.v1": self.sigma_package(result, payload)
            elif schema in ("sigma-workbook-graph.v1", "sigma-data-model-snapshot.v1", "sigma-behavior-manifest.v1", "sigma-semantic-routing-decision.v1"):
                self.sigma_artifact(result, payload)
            else: raise ValueError("sigma.unsupported_contract")
            if result["migration_context"]["route"] is None:
                self.gap(result, "sigma.target_design_waits_for_explicit_route")
        return result


def parse_migration(payload, raw, source_format, revision, helpers):
    return Bridge(helpers).parse(payload, raw, source_format, revision)
