#!/usr/bin/env python3
"""Freeze supplied migration scope and return checked, non-authorizing evidence."""
import argparse
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cowork as cw

ap = cw.ap
LANES = cw.LANES + ["native", "operations", "business"]
FILE_ROLES = ("query", "design", "implementation", "qa")


def envelope(value, kind):
    ap.need(type(value) is dict and type(value.get("schema_version")) is int and
            value["schema_version"] == 1 and value.get("kind") == kind, "unsupported migration contract")


def output_path(root, path):
    ap.need(type(path) is str and path and not Path(path).is_absolute() and ".." not in Path(path).parts and
            "\\" not in path and Path(path).as_posix() == path, "use a canonical relative output path")
    destination = ap.no_links(root / path)
    ap.need(destination.parent.is_dir() and not destination.exists(), "use a new output in an existing engagement directory")
    return destination


def pin(root, obj, path):
    return cw.file_pin(root, path, obj)


def check_pin(root, obj, record):
    ap.need(pin(root, obj, record["path"]) == record, "migration evidence changed: " + record["path"])


def surface_deliveries(root, obj, scope, spec):
    """Recheck surface-specific local evidence without granting native acceptance."""
    selected = {surface for unit in scope["units"] if unit["disposition"] == "migrate" for surface in unit["surfaces"]}
    supplied = spec.get("surface_deliveries", {})
    ap.need(type(supplied) is dict and set(supplied) <= selected, "surface delivery lies outside selected migration scope")
    required = bool(supplied) or any(inv["platform"] in ("looker", "hex", "periscope", "metabase", "webfocus", "thoughtspot", "qlik", "microstrategy", "cognos", "businessobjects", "ssrs", "powerbi_paginated", "crystal") for inv in scope["inventories"])
    verified, files, gaps, targets = {}, {}, [], set()
    for surface, delivery in supplied.items():
        ap.need(type(delivery) is dict and set(delivery) == {"candidate_path", "execution_receipt_path", "coverage_path"},
                "surface delivery needs exact candidate, execution receipt and coverage paths")
        import standalone
        if surface == "report":
            import importlib.util
            report_path = Path(__file__).resolve().parents[2] / 'omni-report-builder/scripts/report_native.py'
            ap.no_links(report_path)
            module_spec = importlib.util.spec_from_file_location('migration_report_delivery', report_path)
            verifier = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(verifier)
        else:
            ap.need(surface in ('app', 'dashboard'), 'unknown delivery surface')
            verifier = standalone._app_module() if surface == "app" else standalone
        proof = verifier.verify_delivery(root, delivery)
        ap.need(proof.get("surface") == surface, "surface delivery kind mismatch")
        origin = urlsplit(proof["target"]["base_url"])
        target = (origin.scheme.lower(), origin.hostname.lower().rstrip("."), origin.port or 443, proof["target"]["document_id"])
        ap.need(target not in targets, "artifact surfaces require separate target documents")
        targets.add(target)
        requirements, _ = ap.read_json(ap.relative_file(root, proof["requirements"]["path"]))
        units = [unit for unit in scope["units"] if unit["disposition"] == "migrate" and surface in unit["surfaces"]]
        inventory_paths = {unit["inventory_path"] for unit in units}
        ap.need(len(inventory_paths) == 1, "one dependency-complete inventory per surface delivery required")
        inventory_path = next(iter(inventory_paths))
        inventory = next(inv for inv in scope["inventories"] if inv["path"] == inventory_path)
        ap.need({k: inventory[k] for k in ("path", "sha256")} in requirements["source_files"],
                "surface delivery belongs to another frozen source inventory")
        source_keys = {key for unit in units for key in unit["asset_keys"]}
        ap.need(source_keys == {item["asset_key"] for item in requirements["items"] if item["disposition"] == "migrate"
                                and surface in item.get("target_surfaces", requirements["surface"])},
                "surface delivery requirements differ from selected source obligations")
        for role in ("requirements", "baseline", "candidate", "execution_receipt", "coverage"):
            check_pin(root, obj, proof[role])
            files[proof[role]["path"]] = proof[role]
        gaps.extend({**gap, "surface": surface} for gap in proof["gaps"])
        verified[surface] = proof
    if required:
        gaps.extend({"code": "missing_surface_delivery", "surface": surface} for surface in sorted(selected - set(verified)))
    return verified, files, gaps, required


def build_scope(root, obj, spec_path):
    spec, _ = ap.read_json(ap.relative_file(root, spec_path))
    envelope(spec, "analyst_migration_scope_spec")
    cw.safe_id(spec.get("scope_id"))
    ap.need(cw.text(spec.get("decision_reference")), "scope decision reference required")
    cw.strings(spec.get("inventory_paths"), "inventory paths", nonempty=True)
    inventories, denominator = [], {}
    for path in spec["inventory_paths"]:
        value, _ = ap.read_json(ap.relative_file(root, path))
        envelope(value, "omni_analyst_source_inventory")
        cw.verify_periscope_inventory(root, obj, path)
        cw.verify_metabase_inventory(root, obj, path)
        cw.verify_webfocus_inventory(root, obj, path)
        cw.verify_thoughtspot_inventory(root, obj, path)
        cw.verify_qlik_inventory(root, obj, path)
        cw.verify_microstrategy_inventory(root, obj, path)
        cw.verify_cognos_inventory(root, obj, path)
        cw.verify_businessobjects_inventory(root, obj, path)
        cw.verify_report_source_inventory(root, obj, path)
        rows = value.get("assets")
        ap.need(type(rows) is list, "source inventory assets required")
        keys = set()
        for row in rows:
            ap.need(type(row) is dict and cw.text(row.get("asset_key")) and row["asset_key"] not in keys,
                    "missing/duplicate inventory asset key")
            keys.add(row["asset_key"])
            denominator[(path, row["asset_key"])] = {k: copy.deepcopy(row.get(k)) for k in
                ("asset_key", "kind", "source_id", "source_identity", "source_path", "source_payload_sha256")}
        inventories.append({**pin(root, obj, path), "platform": value.get("source", {}).get("platform"),
                            "migration_context": copy.deepcopy(value.get("migration_context", {})),
                            "gaps": copy.deepcopy(value.get("gaps", [])),
                            "export_completeness": value.get("export_completeness", "not_established")})
    ap.need(bool(denominator), "migration scope needs a supplied asset denominator")
    units = spec.get("units")
    ap.need(type(units) is list and bool(units), "migration units required")
    seen_units, seen_assets = set(), set()
    for unit in units:
        ap.need(type(unit) is dict and cw.text(unit.get("unit_id")) and unit["unit_id"] not in seen_units,
                "missing/duplicate migration unit id")
        seen_units.add(unit["unit_id"])
        ap.need(unit.get("inventory_path") in spec["inventory_paths"], "unit inventory is outside selected scope")
        cw.strings(unit.get("asset_keys"), "unit asset keys", nonempty=True)
        ap.need(unit.get("disposition") in ("migrate", "exclude", "defer") and cw.text(unit.get("rationale")),
                "explicit migration disposition and rationale required")
        cw.strings(unit.get("frontend_asset_ids"), "frontend asset ids", nonempty=unit["disposition"] == "migrate")
        cw.strings(unit.get("surfaces"), "unit surfaces", nonempty=unit["disposition"] == "migrate")
        ap.need(set(unit["surfaces"]) <= set(obj["surfaces"]), "unit surface is outside frontend engagement")
        if unit["disposition"] != "migrate":
            ap.need(not unit["frontend_asset_ids"] and not unit["surfaces"], "excluded/deferred unit cannot claim a frontend delivery")
        for key in unit["asset_keys"]:
            identity = (unit["inventory_path"], key)
            ap.need(identity in denominator and identity not in seen_assets, "unknown/duplicate source asset disposition")
            source_identity = denominator[identity].get('source_identity') or {}
            ap.need(unit['disposition'] != 'migrate' or source_identity.get('source_platform') not in ('webfocus', 'thoughtspot', 'qlik', 'microstrategy', 'cognos', 'businessobjects', 'ssrs', 'powerbi_paginated', 'crystal')
                    or source_identity.get('restricted_private_scope') is not True,
                    'Unselected private source scope cannot migrate')
            seen_assets.add(identity)
    ap.need(seen_assets == set(denominator), "scope omits supplied source assets; disposition every asset explicitly")
    context = None
    migration_scope = "standalone_frontend"
    if spec.get("backend_context_path") is not None:
        context = pin(root, obj, spec["backend_context_path"])
        backend, _ = ap.read_json(root / context["path"])
        cw.check_seal(backend, "analyst_dma_context")
        ap.need(backend.get("migration_scope") == "full_dashboard", "backend selected scope has no frontend obligation; keep standalone or explicitly revise DMA scope")
        ap.need(backend.get("authorizes_target_write") is False, "backend context cannot grant authority")
        migration_scope = backend["migration_scope"]
    listing = pin(root, obj, spec["independent_source_listing_path"]) if spec.get("independent_source_listing_path") else None
    record = cw.sealed({"schema_version": 1, "kind": "analyst_migration_scope", "project_id": obj["id"],
        "scope_id": spec["scope_id"], "migration_scope": migration_scope, "decision_reference": spec["decision_reference"],
        "spec": pin(root, obj, spec_path), "backend_context": context, "inventories": inventories,
        "independent_source_listing": listing, "units": copy.deepcopy(units),
        "source_assets": [{"inventory_path": path, **row} for (path, _), row in denominator.items()],
        "coverage": "supplied_inventory_only", "source_completeness": "not_established",
        "authorizes_target_write": False, "origin_authenticated": False, "migration_accepted": False})
    return record


def freeze(project, spec_path, output_relative):
    root, obj = ap.load_project(project)
    destination = output_path(root, output_relative)
    record = build_scope(root, obj, spec_path)
    ap.write_json(destination, record)
    return {"status": "scope_frozen", "path": str(destination), "sha256": record["sha256"],
            "source_assets": len(record["source_assets"]), "migration_accepted": False}


def load_scope(root, obj, path):
    scope, _ = ap.read_json(ap.relative_file(root, path))
    cw.check_seal(scope, "analyst_migration_scope")
    ap.need(scope.get("project_id") == obj["id"] and scope.get("authorizes_target_write") is False and
            scope.get("migration_accepted") is False, "migration scope identity/authority mismatch")
    for record in [scope["spec"], scope.get("backend_context"), scope.get("independent_source_listing")]:
        if record:
            check_pin(root, obj, record)
    for record in scope["inventories"]:
        check_pin(root, obj, {k: record[k] for k in ("path", "sha256", "bytes")})
    ap.need(scope == build_scope(root, obj, scope["spec"]["path"]), "migration scope differs from pinned specification/inventory")
    return scope


def build_return(root, obj, scope_relative, return_spec_path):
    scope = load_scope(root, obj, scope_relative)
    spec, _ = ap.read_json(ap.relative_file(root, return_spec_path))
    if spec.get("kind") == "analyst_standalone_migration_return_spec":
        import standalone
        return standalone.build_return(root, obj, scope_relative, return_spec_path,
                                       SimpleNamespace(load_scope=load_scope, envelope=envelope, surface_deliveries=surface_deliveries))
    envelope(spec, "analyst_migration_return_spec")
    ap.need(spec.get("scope_sha256") == scope["sha256"], "return belongs to another migration scope")
    catalog_pin, catalog = cw.current_catalog(root, obj)
    candidate = catalog["source"]["original_sha256"] if catalog else None
    ap.need("candidate_review_sha256" in spec and spec["candidate_review_sha256"] == candidate,
            "return semantic candidate is stale; recheck affected frontend work")
    expected = {(asset, surface, unit["unit_id"]) for unit in scope["units"] if unit["disposition"] == "migrate"
                for asset in unit["frontend_asset_ids"] for surface in unit["surfaces"]}
    rows = spec.get("assets")
    ap.need(type(rows) is list, "frontend asset returns required")
    received, seen, files, gaps = set(), set(), {}, []
    for row in rows:
        ap.need(type(row) is dict and cw.text(row.get("asset_id")) and row.get("surface") in obj["surfaces"],
                "invalid frontend asset return")
        identity = (row["asset_id"], row["surface"])
        ap.need(identity not in seen, "duplicate frontend asset return")
        seen.add(identity)
        cw.strings(row.get("unit_ids"), "asset migration units", nonempty=True)
        assigned = {(row["asset_id"], row["surface"], unit) for unit in row["unit_ids"]}
        ap.need(assigned <= expected, "frontend asset maps outside selected migration scope")
        received.update(assigned)
        ap.need("candidate_review_sha256" in row and row["candidate_review_sha256"] == candidate,
                "frontend asset semantic candidate is stale; recheck affected work")
        ap.need(type(row.get("files")) is dict and set(row["files"]) == set(FILE_ROLES), "query/design/implementation/qa file roles required")
        for role in FILE_ROLES:
            paths = row["files"][role]
            cw.strings(paths, "frontend " + role + " files")
            if not paths:
                gaps.append({"code": "missing_frontend_files", "asset_id": row["asset_id"], "surface": row["surface"], "role": role})
            for path in paths:
                files[path] = pin(root, obj, path)
    for asset, surface, unit in sorted(expected - received):
        gaps.append({"code": "missing_frontend_asset", "asset_id": asset, "surface": surface, "unit_id": unit})
    if candidate is None:
        gaps.append({"code": "semantic_baseline_missing", "status": "assessment_only"})
    if not scope["independent_source_listing"]:
        gaps.append({"code": "independent_source_listing_missing"})
    for unit in scope["units"]:
        if unit["disposition"] == "defer":
            gaps.append({"code": "deferred_source_unit", "unit_id": unit["unit_id"]})
    lanes = spec.get("lanes")
    ap.need(type(lanes) is list, "QA lane claims required")
    seen_lanes = set()
    for row in lanes:
        ap.need(type(row) is dict and row.get("lane") in LANES and row["lane"] not in seen_lanes,
                "unknown/duplicate QA lane")
        seen_lanes.add(row["lane"])
        ap.need(row.get("status") in ("pass", "fail", "blocked", "not_run", "not_applicable") and cw.text(row.get("rationale")),
                "QA lane status and rationale required")
        cw.strings(row.get("evidence_paths"), "QA lane evidence paths")
        ap.need(row["status"] not in ("pass", "not_applicable") or bool(row["evidence_paths"]),
                "pass/not-applicable lane claims need evidence; declarations remain unverified")
        for path in row["evidence_paths"]:
            files[path] = pin(root, obj, path)
        if row["status"] in ("fail", "blocked", "not_run"):
            gaps.append({"code": "pending_qa_lane", "lane": row["lane"], "status": row["status"]})
    missing_lanes = sorted(set(LANES) - seen_lanes)
    gaps.extend({"code": "missing_qa_lane", "lane": lane} for lane in missing_lanes)
    cw.strings(spec.get("unresolved"), "unresolved requirements")
    # Read current exchange evidence so omitted unresolved responses cannot vanish.
    requirement_resolutions, impact_pin = [], None
    if obj.get("dma_import", {}).get("exchange_id"):
        exchange = cw.safe_id(obj["dma_import"]["exchange_id"])
        impact_path = "exchanges/" + exchange + "/impact.json"
        manifest, _ = ap.read_json(root / "exchanges" / exchange / "exchange.json")
        cw.check_seal(manifest, "analyst_backend_exchange")
        request = cw.fresh_request(root, obj, manifest["request_path"])
        ap.need(request["sha256"] == manifest["request_sha256"], "selected request changed after backend receipt")
        impact_pin = pin(root, obj, impact_path)
        recorded = next(r for r in manifest["files"] if r["path"] == "impact.json")
        ap.need(impact_pin["sha256"] == recorded["sha256"], "exchange impact changed")
        impact, _ = ap.read_json(root / impact_path)
        requirement_resolutions = impact.get("requirement_resolutions", [])
        gaps.extend({"code": "backend_requirement_not_resolved", "requirement_id": row["id"], "status": row["status"]}
                    for row in requirement_resolutions if row["status"] != "proposed")
    deliveries, delivery_files, delivery_gaps, needs_deliveries = surface_deliveries(root, obj, scope, spec)
    files.update(delivery_files)
    gaps.extend(delivery_gaps)
    if needs_deliveries:
        gaps.extend({"code": "retained_source_inventory_gaps", "inventory_path": inv["path"], "count": len(inv["gaps"])}
                    for inv in scope["inventories"] if inv["gaps"])
        gaps.extend({"code": "declared_unresolved", "detail": value} for value in spec["unresolved"])
    coverage = "incomplete" if (needs_deliveries and gaps) or any(
        g["code"] in ("missing_frontend_files", "missing_frontend_asset", "semantic_baseline_missing") for g in gaps) else "complete"
    report = {"candidate_coverage": coverage, "coverage_basis": (
        "declared_scope_files_and_recomputed_surface_evidence" if needs_deliveries else "declared_scope_and_retained_file_presence_only"),
              "gaps": gaps, "missing_lanes": missing_lanes, "acceptance": "not_assessed"}
    record = cw.sealed({"schema_version": 1, "kind": "analyst_frontend_return", "project_id": obj["id"],
        "scope": pin(root, obj, scope_relative), "scope_sha256": scope["sha256"], "migration_scope": scope["migration_scope"],
        "backend_context": scope["backend_context"], "spec": pin(root, obj, return_spec_path),
        "catalog": catalog_pin, "candidate_review_sha256": candidate, "assets": copy.deepcopy(rows),
        "files": list(files.values()), "surface_deliveries": deliveries,
        "lane_claims": copy.deepcopy(lanes), "lane_claim_assurance": "reported_unverified",
        "requirement_resolutions": requirement_resolutions, "impact": impact_pin,
        "source_gaps": [{"inventory_path": inv["path"], "gaps": inv["gaps"]} for inv in scope["inventories"]],
        "source_completeness": "not_established", "unresolved": spec["unresolved"], **report,
        "native_verification": "not_assessed", "business_acceptance": "not_assessed",
        "authorizes_target_write": False, "origin_authenticated": False, "migration_accepted": False})
    return record


def prepare_return(project, scope_relative, return_spec_path, output_relative):
    root, obj = ap.load_project(project)
    destination = output_path(root, output_relative)
    record = build_return(root, obj, scope_relative, return_spec_path)
    ap.write_json(destination, record)
    return {"status": "frontend_evidence_prepared", "path": str(destination), "sha256": record["sha256"],
            "design_completion": ap.design_completion(root),
            "report": {k: record[k] for k in ("candidate_coverage", "coverage_basis", "gaps", "missing_lanes", "acceptance")}}


def verify_return(project, receipt_relative):
    root, obj = ap.load_project(project)
    receipt, _ = ap.read_json(ap.relative_file(root, receipt_relative))
    if receipt.get("kind") == "analyst_standalone_migration_return":
        import standalone
        return standalone.verify_return(project, receipt_relative,
                                        SimpleNamespace(load_scope=load_scope, envelope=envelope, surface_deliveries=surface_deliveries))
    cw.check_seal(receipt, "analyst_frontend_return")
    ap.need(receipt.get("project_id") == obj["id"] and receipt.get("authorizes_target_write") is False and
            receipt.get("migration_accepted") is False, "frontend return identity/authority mismatch")
    scope = load_scope(root, obj, receipt["scope"]["path"])
    ap.need(scope["sha256"] == receipt["scope_sha256"] and scope["backend_context"] == receipt["backend_context"],
            "frontend return scope changed")
    for record in [receipt["scope"], receipt["spec"], receipt.get("impact"), *receipt["files"]]:
        if record:
            check_pin(root, obj, record)
    catalog_pin, catalog = cw.current_catalog(root, obj)
    ap.need(catalog_pin == receipt["catalog"] and
            (catalog["source"]["original_sha256"] if catalog else None) == receipt["candidate_review_sha256"],
            "frontend return semantic candidate is stale; recheck affected work")
    ap.need(receipt == build_return(root, obj, receipt["scope"]["path"], receipt["spec"]["path"]),
            "frontend return differs from pinned specification and evidence")
    return {"status": "consistent", "candidate_coverage": receipt["candidate_coverage"],
            "design_completion": ap.design_completion(root),
            "native_verification": "not_assessed", "business_acceptance": "not_assessed",
            "migration_accepted": False, "authorizes_target_write": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "return", "check"):
        command = subs.add_parser(name)
        command.add_argument("--project", required=True)
        if name != "check":
            command.add_argument("--spec", required=True)
            command.add_argument("--output", required=True)
        if name == "return":
            command.add_argument("--scope", required=True)
        if name == "check":
            command.add_argument("--receipt", required=True)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze(args.project, args.spec, args.output)
        elif args.command == "return":
            result = prepare_return(args.project, args.scope, args.spec, args.output)
        else:
            result = verify_return(args.project, args.receipt)
        print(json.dumps({k: v for k, v in result.items() if k != "report"}, indent=2))
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        parser.exit(2, "error: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
