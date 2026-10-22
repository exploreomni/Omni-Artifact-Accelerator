"""Offline design evidence integrity and recorded coverage, never design certification."""
import importlib.util
from pathlib import Path
import re
from urllib.parse import urlsplit

_spec = importlib.util.spec_from_file_location("_design_project", Path(__file__).with_name("analyst_project.py"))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

STATUSES = {"pass", "fail", "blocked", "not_run", "not_applicable"}
LANES = {"craft", "numerical", "native_behavior", "responsive", "accessibility", "access",
         "performance", "human_usability", "business_acceptance"}
EFFECTS = {
    "candidate": LANES,
    "design": {"craft", "native_behavior", "responsive", "accessibility", "human_usability"},
    "brand": {"craft", "responsive", "accessibility", "human_usability"},
    "query": {"numerical", "native_behavior", "access", "performance", "human_usability"},
    "source": {"numerical", "native_behavior", "access", "human_usability"},
    "expectation": {"numerical", "native_behavior", "human_usability"},
}
CHANGES = {"material_new", "material_redesign", "focused_edit", "faithful_migration"}
DESIGNERS = {"app-designer", "dashboard-designer", "design-systems"}


def has_text(value):
    return type(value) is str and bool(value.strip())


def text(value, label):
    P.need(has_text(value), label + " required")


def rows(value, label):
    P.need(type(value) is list, label + " must be a list")
    ids = set()
    for row in value:
        P.need(type(row) is dict, label + " row must be an object")
        text(row.get("id"), label + " id")
        P.need(row["id"] not in ids, "duplicate " + label + " id")
        ids.add(row["id"])
    return value


def relative(value):
    text(value, "path")
    path = Path(value)
    P.need(not path.is_absolute() and ".." not in path.parts and "\\" not in value and
           path.as_posix() == value and value != "project.json", "canonical engagement path required")
    return value


def file_pin(root, path):
    raw = P.relative_file(root, relative(path)).read_bytes()
    return {"path": path, "sha256": P.digest(raw), "bytes": len(raw)}


def target(value, surface):
    P.need(type(value) is dict and value.get("surface") == surface, "candidate target surface mismatch")
    P.need(value.get("state") in {"local", "draft", "published"}, "target state required")
    if value["state"] != "local":
        text(value.get("document_id"), "target document_id")
        origin = urlsplit(value.get("instance", ""))
        P.need(origin.scheme == "https" and origin.netloc and not origin.username and
               not origin.password and origin.path in {"", "/"} and not origin.query and
               not origin.fragment, "target instance must be an HTTPS origin")
    if value["state"] == "draft":
        text(value.get("draft_id"), "exact draft_id")
    else:
        P.need(value.get("draft_id") is None, "draft_id only belongs to a draft")


def validate(spec, project):
    P.need(type(spec) is dict and type(spec.get("schema_version")) is int and
           spec["schema_version"] == 1 and spec.get("kind") == "analyst_design_review_spec",
           "unsupported design review spec")
    text(spec.get("id"), "review id")
    scope = spec.get("scope")
    P.need(type(scope) is dict and scope.get("change") in CHANGES, "design change scope required")
    text(scope.get("rationale"), "scope rationale")
    surfaces = scope.get("surfaces")
    P.need(type(surfaces) is list and surfaces and len(surfaces) == len(set(surfaces)) and
           set(surfaces) <= set(project["surfaces"]), "scope surfaces must belong to project")
    lanes = scope.get("required_lanes")
    P.need(type(lanes) is list and lanes and len(lanes) == len(set(lanes)) and
           set(lanes) <= LANES and "craft" in lanes, "required lanes must include craft")
    if project["mode"] == "migration" and scope["change"] in {"material_new", "material_redesign"}:
        P.need(scope.get("scope_change_path"), "migration redesign requires explicit scope_change_path")
    if scope["change"] == "faithful_migration":
        P.need(project["mode"] == "migration", "faithful_migration requires migration project")
    deps = rows(spec.get("dependencies"), "dependencies")
    for dep in deps:
        P.need(dep.get("kind") in EFFECTS and dep.get("surface") in [*surfaces, "shared"],
               "invalid dependency kind/surface")
        relative(dep.get("path"))
        if dep["kind"] == "candidate":
            P.need(dep["surface"] != "shared", "candidate must have one surface")
            target(dep.get("target"), dep["surface"])
    for surface in surfaces:
        P.need(sum(d["kind"] == "candidate" and d["surface"] == surface for d in deps) == 1,
               "exactly one candidate per scoped surface required")
        P.need(any(d["kind"] == "design" and d["surface"] in {surface, "shared"} for d in deps),
               "resolved design dependency required per surface")
    for key in ("concepts", "captures", "deviations", "findings", "cases"):
        rows(spec.get(key, []), key)
        for row in spec.get(key, []):
            for field in ("candidate_id", "case_id", "retest_case_id"):
                if field in row:
                    text(row[field], key + " " + field)
    P.need(type(spec.get("selection", {})) is dict, "selection must be an object by surface")
    for selection in spec.get("selection", {}).values():
        P.need(type(selection) is dict, "selection row must be an object")
        if "concept_id" in selection:
            text(selection["concept_id"], "selection concept_id")
    for concept in spec.get("concepts", []):
        P.need(concept.get("surface") in surfaces, "concept surface outside scope")
        for key in ("task", "composition", "tradeoffs"):
            text(concept.get(key), "concept " + key)
        P.need(type(concept.get("render_paths")) is list, "concept render_paths list required")
    for capture in spec.get("captures", []):
        P.need(capture.get("kind") in {"native", "prototype"}, "capture kind required")
        context = capture.get("context")
        P.need(type(context) is dict, "capture context required")
        viewport = context.get("viewport")
        P.need(type(viewport) is list and len(viewport) == 2 and
               all(type(n) is int and 0 < n <= 32768 for n in viewport), "capture viewport required")
        for key in ("appearance", "state"):
            text(context.get(key), "capture " + key)
    for case in spec.get("cases", []):
        P.need(case.get("surface") in surfaces and case.get("lane") in LANES and
               case.get("status") in STATUSES and type(case.get("executed")) is bool,
               "invalid case surface/lane/status/executed")
        P.need(type(case.get("reviewed_dependencies", {})) is dict, "reviewed_dependencies object required")
        P.need(type(case.get("capture_ids", [])) is list and
               all(type(i) is str for i in case.get("capture_ids", [])), "capture_ids string list required")
        for key in ("method", "reviewer", "observation", "rationale"):
            P.need(key not in case or type(case[key]) is str, "case " + key + " must be text")
    for key in ("deviations", "findings"):
        for row in spec.get(key, []):
            P.need(row.get("surface") in surfaces, key + " surface outside scope")
    return spec


def references(spec):
    """Enumerate every declared file; the frozen manifest cannot omit embedded references."""
    paths = {relative(d["path"]) for d in spec["dependencies"]}
    scope = spec["scope"]
    for key in ("scope_change_path", "source_obligations_path", "accepted_differences_path"):
        if scope.get(key):
            paths.add(relative(scope[key]))
    for concept in spec.get("concepts", []):
        paths.update(relative(p) for p in concept["render_paths"])
    for capture in spec.get("captures", []):
        paths.add(relative(capture.get("path")))
    for collection in ("deviations", "findings", "cases"):
        for row in spec.get(collection, []):
            values = row.get("evidence_paths", [])
            P.need(type(values) is list, "evidence_paths must be a list")
            paths.update(relative(p) for p in values)
            if row.get("accepted_difference_path"):
                paths.add(relative(row["accepted_difference_path"]))
    return sorted(paths)


def image_file(root, path):
    """Magic bytes only: neither decoding nor judging an image or its provenance."""
    raw = P.relative_file(root, path).read_bytes()
    return (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff") or
            (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"))


def evaluate(root, spec, pins, stale):
    gaps, results = [], []
    deps = {d["id"]: d for d in spec["dependencies"]}
    captures = {c["id"]: c for c in spec.get("captures", [])}
    scope = spec["scope"]

    def gap(code, **detail):
        gaps.append({"code": code, **detail})

    material = scope["change"] in {"material_new", "material_redesign"}
    for surface in scope["surfaces"]:
        concepts = [c for c in spec.get("concepts", []) if c["surface"] == surface]
        if material:
            if len(concepts) < 2:
                gap("rendered_alternatives_missing", surface=surface)
            selection = spec.get("selection", {}).get(surface, {})
            if (selection.get("concept_id") not in {c["id"] for c in concepts} or
                    selection.get("status") not in {"proposed", "user_accepted"} or
                    not has_text(selection.get("rationale"))):
                gap("selected_direction_missing", surface=surface)
            for concept in concepts:
                if not concept["render_paths"]:
                    gap("concept_render_missing", concept=concept["id"], surface=surface)
                for path in concept["render_paths"]:
                    if path in stale or not image_file(root, path):
                        gap("concept_render_invalid_or_stale", concept=concept["id"], path=path, surface=surface)
    if scope["change"] == "faithful_migration":
        if not scope.get("source_obligations_path") or not any(d["kind"] == "source" for d in deps.values()):
            gap("migration_source_obligations_missing")
    for case in spec.get("cases", []):
        reasons = []
        candidate = deps.get(case.get("candidate_id"))
        if not candidate or candidate["kind"] != "candidate" or candidate["surface"] != case["surface"]:
            reasons.append("candidate_identity_mismatch")
        else:
            if case.get("target") != candidate["target"]:
                reasons.append("target_identity_mismatch")
        required = {ident: d for ident, d in deps.items() if
                    d["surface"] in {case["surface"], "shared"} and case["lane"] in EFFECTS[d["kind"]]}
        if case["lane"] == "numerical" and case["status"] == "pass" and not {
                "query", "expectation"} <= {d["kind"] for d in required.values()}:
            reasons.append("query_and_independent_expectation_dependencies_missing")
        for ident, dep in required.items():
            if case.get("reviewed_dependencies", {}).get(ident) != pins[dep["path"]]["sha256"]:
                reasons.append("reviewed_dependency_mismatch:" + ident)
            if dep["path"] in stale:
                reasons.append("stale_dependency:" + ident)
        evidence = case.get("evidence_paths", [])
        if any(path in stale for path in evidence):
            reasons.append("stale_case_evidence")
        if case["status"] == "pass":
            if not case["executed"] or not evidence or not all(has_text(case.get(k)) for k in ("reviewer", "method", "observation")):
                reasons.append("executed_review_evidence_missing")
            if case["lane"] in {"craft", "native_behavior", "responsive", "accessibility"}:
                selected = [captures.get(i) for i in case.get("capture_ids", [])]
                if not selected or any(c is None for c in selected):
                    reasons.append("capture_missing")
                for capture in filter(None, selected):
                    if (not candidate or capture.get("candidate_id") != candidate["id"] or
                            capture.get("candidate_sha256") != pins[candidate["path"]]["sha256"] or
                            capture["path"] in stale or not image_file(root, capture["path"])):
                        reasons.append("capture_invalid_or_stale")
                    remote = candidate and candidate["target"]["state"] != "local"
                    if ((remote and capture["kind"] != "native") or
                            (capture["kind"] == "native" and not remote) or
                            (case.get("method") == "native_observation" and not remote)):
                        reasons.append("native_capture_identity_missing")
            if case["lane"] == "craft" and (case.get("method") != "designer_critique" or
                    case.get("reviewer_role") not in DESIGNERS or case.get("independence") != "independent"):
                reasons.append("independent_designer_critique_missing")
            if case["lane"] == "native_behavior" and case.get("method") != "native_observation":
                reasons.append("native_execution_missing")
            if case["lane"] == "human_usability" and case.get("method") != "participant_observation":
                reasons.append("participant_observation_missing")
        elif case["status"] == "not_applicable":
            if not has_text(case.get("rationale")) or case["lane"] == "craft":
                reasons.append("applicability_unjustified")
        effective = case["status"] if not reasons else "not_run"
        results.append({"id": case["id"], "surface": case["surface"], "lane": case["lane"],
                        "reported_status": case["status"], "recorded_status": effective,
                        "reasons": reasons, "claim_authenticated": False})
    by_id = {r["id"]: r for r in results}
    for deviation in spec.get("deviations", []):
        disposition = deviation.get("disposition")
        candidate = deps.get(deviation.get("candidate_id"), {})
        justified = (disposition in {"accepted", "corrected"} and
                     candidate.get("kind") == "candidate" and candidate.get("surface") == deviation["surface"] and
                     deviation.get("candidate_sha256") == pins[candidate["path"]]["sha256"] and
                     deviation.get("designer_role") in DESIGNERS and
                     all(has_text(deviation.get(k)) for k in ("designer", "intended", "actual", "reason", "rationale")) and
                     deviation.get("evidence_paths"))
        if disposition == "corrected":
            retest = by_id.get(deviation.get("retest_case_id"), {})
            justified = justified and retest.get("recorded_status") == "pass" and retest.get("lane") == "craft" and retest.get("surface") == deviation.get("surface")
        if scope["change"] == "faithful_migration" and deviation.get("affects_source_behavior") is not False:
            justified = justified and bool(deviation.get("accepted_difference_path"))
        if not justified or any(path in stale for path in deviation.get("evidence_paths", [])):
            gap("unresolved_design_deviation", deviation=deviation["id"], surface=deviation.get("surface"))
    for finding in spec.get("findings", []):
        original = by_id.get(finding.get("case_id"), {})
        retest = by_id.get(finding.get("retest_case_id"), {})
        corrected = (finding.get("disposition") == "corrected" and retest.get("recorded_status") == "pass" and
                     retest.get("lane") == original.get("lane") and retest.get("surface") == finding["surface"])
        accepted = finding.get("impact") == "minor" and finding.get("disposition") == "accepted" and has_text(finding.get("rationale")) and finding.get("evidence_paths")
        if (not original or not has_text(finding.get("problem")) or not has_text(finding.get("owner")) or
                not (corrected or accepted) or any(p in stale for p in finding.get("evidence_paths", []))):
            gap("open_design_finding", finding=finding["id"], surface=finding.get("surface"))
    for surface in scope["surfaces"]:
        for lane in scope["required_lanes"]:
            cases = [r for r in results if r["surface"] == surface and r["lane"] == lane]
            if not cases or any(r["recorded_status"] not in {"pass", "not_applicable"} for r in cases):
                gap("required_lane_incomplete", surface=surface, lane=lane)
    return gaps, results


def freeze(root, spec_path, output_relative):
    root, project = P.load_project(root)
    spec_path = P.no_links(spec_path)
    P.need(spec_path.resolve().is_relative_to(root.resolve()), "spec must be inside engagement")
    spec_relative = spec_path.relative_to(root).as_posix()
    spec, raw = P.read_json(spec_path)
    validate(spec, project)
    paths = references(spec)
    P.need(output_relative not in [*paths, spec_relative], "output cannot replace review input")
    output = root / relative(output_relative)
    pins = [file_pin(root, path) for path in paths]
    P.need(type(project.get("design_review_history", [])) is list, "design_review_history must be a list")
    value = {"schema_version": 1, "kind": "analyst_design_review", "project_id": project["id"],
             "project_mode": project["mode"], "project_surfaces": project["surfaces"],
             "spec": spec, "spec_file": {"path": spec_relative, "sha256": P.digest(raw), "bytes": len(raw)},
             "pins": pins, "authority": "recorded_evidence_only"}
    value["content_sha256"] = P.digest(P.canonical(value))
    # Reject malformed declarations before committing a new record or selecting it.
    evaluate(root, spec, {p["path"]: p for p in pins}, set())
    P.write_json(output, value)
    record = file_pin(root, output_relative)
    project.setdefault("design_review_history", []).append(record)
    project["design_review"] = record
    P.write_json(root / "project.json", project, replace=True)
    return {"path": str(output), "report": check(root)}


def check(root, record_relative=None):
    root, project = P.load_project(root)
    selected = project.get("design_review")
    if not record_relative and not selected:
        return {"status": "not_assessed", "coverage": "incomplete", "gaps": [{"code": "design_evidence_missing"}],
                "cases": [], "assessment": "not_assessed", "native_verification": "not_assessed",
                "business_acceptance": "not_assessed"}
    path = record_relative or selected["path"]
    record, raw = P.read_json(P.relative_file(root, path))
    if selected and path == selected["path"]:
        P.need(P.digest(raw) == selected["sha256"], "selected design review changed")
    P.need(record.get("kind") == "analyst_design_review" and type(record.get("schema_version")) is int and
           record["schema_version"] == 1, "unsupported frozen design review")
    P.need(record.get("content_sha256") == P.digest(P.canonical({k: v for k, v in record.items() if k != "content_sha256"})), "design review self-hash mismatch")
    P.need(record.get("project_id") == project["id"] and record.get("project_mode") == project["mode"] and
           record.get("project_surfaces") == project["surfaces"], "design review project scope changed")
    spec = validate(record["spec"], project)
    pins = record["pins"]
    P.need(type(pins) is list and len(pins) == len(references(spec)) and
           sorted(p["path"] for p in pins) == references(spec), "review pin manifest mismatch")
    stale = set()
    for pin in [*pins, record["spec_file"]]:
        P.need(type(pin.get("sha256")) is str and re.fullmatch(r"[a-f0-9]{64}", pin["sha256"]), "invalid evidence hash")
        try:
            if file_pin(root, pin["path"]) != pin:
                stale.add(pin["path"])
        except (ValueError, OSError):
            stale.add(pin["path"])
    if record["spec_file"]["path"] not in stale:
        original, _ = P.read_json(P.relative_file(root, record["spec_file"]["path"]))
        P.need(P.canonical(original) == P.canonical(spec), "embedded spec differs from pinned original")
    indexed = {p["path"]: p for p in pins}
    gaps, cases = evaluate(root, spec, indexed, stale)
    if record["spec_file"]["path"] in stale:
        for case in cases:
            case["recorded_status"] = "not_run"
            case["reasons"].append("review_spec_changed")
    gaps.extend({"code": "changed_or_missing_evidence", "path": p} for p in sorted(stale))
    return {"status": "inconsistent" if stale else "consistent", "coverage": "incomplete" if gaps else "complete",
            "review_id": spec["id"], "scope": spec["scope"], "gaps": gaps, "cases": cases,
            "check_scope": "file_integrity_and_recorded_coverage_only", "assessment": "not_assessed",
            "native_verification": "not_assessed", "business_acceptance": "not_assessed",
            "publication_authorized": False, "claims_authenticated": False}
