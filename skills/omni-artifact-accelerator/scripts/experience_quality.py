"""Declared delivery coverage and conditional ownership; no dispatch or visual certification."""

CAPABILITIES = {
    "insight": ("data-analyst", "data-storyteller"),
    "custom-visualization": ("app-designer", "app-engineer"),
    "motion": ("app-designer", "motion-designer", "app-engineer"),
    "external-media": ("app-engineer",),
    "live-content": ("bi-engineer", "app-engineer"),
    "data-binding": ("data-analyst", "bi-engineer"),
    "brand-assets": ("branding",),
}
APP_ONLY = {"custom-visualization", "motion", "external-media", "live-content"}
DESTINATION_FIELDS = ("purpose", "primary_action", "evidence", "drill", "return", "responsive")


def present(value):
    return (isinstance(value, str) and bool(value.strip())) or (
        isinstance(value, (dict, list)) and bool(value))


def validate(spec, need, relative, roles):
    """Optional annotations stay backward compatible; incomplete work remains representable."""
    for requirement in spec["requirements"]:
        if "delivery" not in requirement:
            continue
        delivery = requirement["delivery"]
        need(type(delivery) is dict, "delivery_object_required")
        need(set(delivery) <= {"source_ref", "owner", "behavior", "destinations",
                              "dependency_paths", "capabilities"}, "delivery_unknown_field")
        for key in ("source_ref", "behavior"):
            if key in delivery:
                need(isinstance(delivery[key], str), "delivery_" + key + "_text_required")
        if "owner" in delivery:
            need(delivery["owner"] is None or (type(delivery["owner"]) is str and delivery["owner"] in roles), "delivery_owner_invalid")
        for key in ("destinations", "dependency_paths", "capabilities"):
            if key not in delivery:
                continue
            values = delivery[key]
            need(type(values) is list and all(type(v) is str and v.strip() for v in values)
                 and len(values) == len(set(values)), "delivery_" + key + "_invalid")
        for path in delivery.get("dependency_paths", []):
            relative(path)
        need(set(delivery.get("capabilities", [])) <= set(CAPABILITIES), "delivery_capability_unknown")


def inspect(root, state, project_api):
    """Report missing declared coverage, never infer unrecorded requirements or approval."""
    rows, findings, destinations, role_requirements = [], [], {}, {}
    if state["status"] == "inconsistent":
        return {"status": "inconsistent", "findings": state["findings"], "requirements": [],
                "destinations": [], "role_requirements": {}, "claims_authenticated": False,
                "native_verification": "not_assessed", "craft_verification": "not_assessed",
                "publication_authorized": False}
    active = [r for r in state["requirements"] if r["disposition"] not in {"explicitly_omitted", "deferred"}
              and (r["required"] or r["disposition"] == "selected")]
    deferred = [r for r in state["requirements"] if r["required"] and r["disposition"] == "deferred"]
    enabled = any("delivery" in r for r in active + deferred)
    if not enabled:
        findings.append({"code": "delivery_coverage_not_recorded",
                         "action": "Trace material requests into delivery annotations when this workflow applies."})
    if not state["selected"]:
        findings.append({"code": "delivery_selection_pending"})
    for selection in state["selections"]:
        path = selection.get("design_path")
        if not path:
            continue
        try:
            design, _ = project_api.read_json(project_api.relative_file(root, path))
            items = design.get("destinations", [])
            if type(items) is not list:
                raise ValueError("resolved design destinations must be a list")
            ids = set()
            for item in items:
                if type(item) is not dict or not isinstance(item.get("id"), str) or not item["id"].strip() or item["id"] in ids:
                    raise ValueError("resolved design destination IDs must be unique nonempty strings")
                ids.add(item["id"])
                destinations[(selection["surface"], item["id"])] = item
        except (ValueError, OSError, KeyError, TypeError) as exc:
            findings.append({"code": "destination_contract_invalid", "surface": selection["surface"], "detail": str(exc)})
    for req in active:
        delivery = req.get("delivery", {})
        gaps = []
        if enabled:
            for key in ("source_ref", "owner", "behavior", "destinations"):
                if not present(delivery.get(key)):
                    gaps.append("missing_" + key)
            for path in delivery.get("dependency_paths", []):
                try:
                    project_api.relative_file(root, path)
                except (ValueError, OSError) as exc:
                    gaps.append("dependency_unavailable:" + path)
            for surface in req["surfaces"]:
                for dest in delivery.get("destinations", []):
                    item = destinations.get((surface, dest))
                    if item is None:
                        gaps.append("destination_missing:" + surface + "/" + dest)
                    else:
                        gaps.extend("destination_" + key + "_missing:" + surface + "/" + dest
                                    for key in DESTINATION_FIELDS if not present(item.get(key)))
        owner = delivery.get("owner")
        tags = delivery.get("capabilities", [])
        roles = {owner} if owner else set()
        for tag in tags:
            if tag in APP_ONLY and "app" not in req["surfaces"]:
                gaps.append("app_capability_on_dashboard:" + tag)
                continue
            roles.update(CAPABILITIES[tag])
        for role in sorted(roles):
            role_requirements.setdefault(role, []).append(req["id"])
        row = {"id": req["id"], "origin": req["origin"], "disposition": req["disposition"],
               "surfaces": req["surfaces"], "owner": owner,
               "source_ref": delivery.get("source_ref"), "behavior": delivery.get("behavior"),
               "destinations": delivery.get("destinations", []), "capabilities": tags,
               "dependency_paths": delivery.get("dependency_paths", []), "gaps": gaps}
        if req["disposition"] == "unresolved":
            row["gaps"].append("choice_unresolved")
        rows.append(row)
        findings.extend({"code": gap, "requirement_id": req["id"]} for gap in row["gaps"])
    for req in deferred:
        delivery = req.get("delivery", {})
        rows.append({"id": req["id"], "origin": req["origin"], "disposition": "deferred",
                     "surfaces": req["surfaces"], "owner": delivery.get("owner"),
                     "source_ref": delivery.get("source_ref"), "behavior": delivery.get("behavior"),
                     "destinations": delivery.get("destinations", []), "capabilities": [],
                     "dependency_paths": delivery.get("dependency_paths", []), "gaps": ["requirement_deferred"]})
        findings.append({"code": "requirement_deferred", "requirement_id": req["id"]})
    declared = []
    for (surface, ident), item in destinations.items():
        linked = [r["id"] for r in rows if surface in r["surfaces"] and ident in r["destinations"]]
        declared.append({"surface": surface, "id": ident, "requirement_ids": linked})
        if enabled and not linked:
            findings.append({"code": "destination_without_requirement", "surface": surface, "destination": ident})
    return {"status": ("not_assessed" if not enabled else "incomplete" if findings else "ready_for_review"),
            "selected_intent": state["selected"], "requirements": rows, "destinations": declared,
            "findings": findings, "role_requirements": role_requirements,
            "scope": "Declared requirements, named destinations and explicit files only; original-brief completeness needs review.",
            "native_verification": "not_assessed", "craft_verification": "not_assessed",
            "claims_authenticated": False, "publication_authorized": False}
