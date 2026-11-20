"""Compare caller-supplied, pinned local evidence for one native Omni Topic."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urlsplit


PERSONAS = ("allowed", "restricted", "default")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class Missing(ValueError):
    """Unavailable evidence remains pending."""


class Conflict(ValueError):
    """Observed evidence contradicts its binding or expectation."""


class InvalidPin(Conflict):
    """Changed original bytes invalidate the assembled evidence packet."""


def require(ok, msg):
    if not ok:
        raise Conflict(msg)


def need(ok, msg):
    if not ok:
        raise Missing(msg)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode()


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def unique_keys(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON key")
        obj[key] = value
    return obj


def original(ref, originals):
    need(ref is not None, "missing original reference")
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "invalid original reference")
    path, digest = ref["path"], ref["sha256"]
    require(text(path) and not PurePosixPath(path).is_absolute()
            and all(part not in ("", ".", "..") for part in path.split("/"))
            and "\\" not in path, "invalid engagement-relative evidence path")
    require(isinstance(digest, str) and HASH.fullmatch(digest), "invalid original digest")
    need(path in originals, "original bytes unavailable")
    raw = originals[path]
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != digest:
        raise InvalidPin("original digest mismatch")
    try:
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys,
                            parse_constant=lambda _: require(False, "nonfinite JSON value"))
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise Conflict("invalid original JSON") from exc
    require(isinstance(record, dict), "original must be a JSON object")
    return record


def observed(record, scope, kind):
    require(record.get("kind") == kind and record.get("scope") == scope, "wrong observation kind or scope")
    need(text(record.get("source_ref")), "missing original source reference")
    stamp = record.get("observed_at")
    need(text(stamp), "missing observation time")
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Conflict("invalid observation time") from exc
    require(when.tzinfo is not None, "missing observation timezone")


def signed_user(identity, principal, *, persona=False):
    need(isinstance(identity, dict) and identity.get("keyScope") == "user", "intended user session unavailable")
    user = identity.get("user")
    need(isinstance(user, dict) and text(user.get("membershipId")), "observed membership unavailable")
    require(user["membershipId"] == principal, "wrong effective principal")
    if persona:
        need(user.get("isOrgAdmin") is False, "non-administrative user session unverified")


def results(value):
    need(isinstance(value, dict) and value.get("status") == "complete", "complete result unavailable")
    need(value.get("truncated") is False and not value.get("partial"), "result completeness unavailable")
    require(not value.get("error") and not value.get("errors"), "query returned an error")
    cols, rows = value.get("columns"), value.get("rows")
    require(isinstance(cols, list) and cols and all(text(c) for c in cols)
            and len(set(cols)) == len(cols), "invalid result columns")
    require(isinstance(rows, list) and all(isinstance(row, dict) and set(row) == set(cols)
            for row in rows), "invalid result rows")
    # Ordering may differ. Preserve duplicates, JSON types, exact values and column identity.
    return set(cols), sorted(canonical(row) for row in rows)


def scope_of(context, topic, candidate):
    require(isinstance(context, dict) and all(text(context.get(k)) for k in
            ("base_url", "model_id", "principal_id")) and "branch_id" in context, "model context and principal required")
    url = urlsplit(context["base_url"])
    require(url.scheme == "https" and url.hostname and not url.username and not url.password
            and not url.query and not url.fragment and url.path in ("", "/"), "invalid tenant origin")
    for key in ("branch_id", "workbook_model_id"):
        require(context.get(key) is None or text(context[key]), "invalid model identity")
    ids = [context[k] for k in ("model_id", "branch_id", "workbook_model_id") if context.get(k) is not None]
    require(len(ids) == len(set(ids)), "distinct model identities required")
    require(text(topic) and isinstance(candidate, str) and HASH.fullmatch(candidate), "invalid Topic or candidate")
    scope = {k: context[k] for k in ("base_url", "model_id", "branch_id")}
    if context.get("workbook_model_id") is not None:
        scope["workbook_model_id"] = context["workbook_model_id"]
    if context.get("model_version_id") is not None:
        require(text(context["model_version_id"]), "invalid model version")
        scope["model_version_id"] = context["model_version_id"]
    return {**scope, "topic_name": topic, "candidate_sha256": candidate}


def model_identity(record, ctx):
    signed_user(record.get("identity"), ctx["principal_id"])
    models = record.get("models")
    need(isinstance(models, dict), "model ancestry unavailable")
    base = models.get(ctx["model_id"])
    need(isinstance(base, dict), "shared model ancestry unavailable")
    require(base.get("id") == ctx["model_id"] and base.get("modelKind") in ("SHARED", "SHARED_EXTENSION")
            and text(base.get("connectionId")) and base.get("deletedAt") is None, "shared model differs")
    effective = base
    if ctx["branch_id"] is not None:
        branch = models.get(ctx["branch_id"])
        need(isinstance(branch, dict), "development branch ancestry unavailable")
        require(branch.get("id") == ctx["branch_id"] and branch.get("modelKind") == "BRANCH"
                and branch.get("baseModelId") == ctx["model_id"] and branch.get("deletedAt") is None
                and branch.get("connectionId") in (None, base["connectionId"]), "development ancestry differs")
        effective = branch
    if ctx.get("workbook_model_id") is not None:
        workbook = models.get(ctx["workbook_model_id"])
        need(isinstance(workbook, dict), "workbook model ancestry unavailable")
        require(workbook.get("id") == ctx["workbook_model_id"] and workbook.get("modelKind") == "WORKBOOK"
                and workbook.get("baseModelId") == effective["id"] and workbook.get("deletedAt") is None
                and workbook.get("connectionId") in (None, base["connectionId"]), "workbook ancestry differs")
        effective = workbook
    if ctx.get("model_version_id") is not None:
        need(effective.get("modelVersionId") is not None, "model version unavailable")
        require(effective["modelVersionId"] == ctx["model_version_id"], "model version differs")



def model_validation(record, ctx):
    signed_user(record.get("identity"), ctx["principal_id"])
    need(text(record.get("run_id")) and record.get("status") in ("complete", "failed"), "validation run incomplete")
    require(record.get("model_id") == (ctx["branch_id"] or ctx["model_id"]), "validated a different model")
    require(record["status"] == "complete", "model validation failed")
    need(isinstance(record.get("errors"), list), "validation errors unavailable")
    require(record["errors"] == [], "model validation failed")


def read_topic(record, ctx, topic, expected):
    signed_user(record.get("identity"), ctx["principal_id"])
    require(record.get("model_id") == (ctx.get("workbook_model_id") or ctx["branch_id"] or ctx["model_id"]),
            "read back a different model")
    response = record.get("response")
    need(isinstance(response, dict) and response.get("success") is True, "successful Topic readback unavailable")
    definition = response.get("topic")
    need(isinstance(definition, dict) and isinstance(definition.get("views"), list)
         and definition["views"], "regular Topic views unavailable")
    require(definition.get("name") == topic and definition.get("is_composite") is not True,
            "read back a different or composite Topic")
    require(all(isinstance(view, dict) and all(isinstance(view.get(f, []), list)
                and all(isinstance(field, dict) for field in view.get(f, []))
                for f in ("dimensions", "measures", "filter_only_fields")) for view in definition["views"]),
            "invalid native Topic views")
    digest = fingerprint(response)
    require(digest == expected, "whole Topic response fingerprint differs")
    return digest


def indexed(records, name):
    need(isinstance(records, list), name + " unavailable")
    index = {}
    for rec in records:
        require(isinstance(rec, dict) and text(rec.get("id")) and rec["id"] not in index,
                "missing or duplicate " + name + " ID")
        index[rec["id"]] = rec
    return index


def compare_query(contract, record, policy, ctx):
    signed_user(record.get("identity"), ctx["principal_id"])
    need(text(record.get("query_id")), "saved/executed query identity unavailable")
    query = contract.get("query")
    require(isinstance(query, dict) and query and canonical(record.get("query")) == canonical(query),
            "different query or filter scope")
    require(record["source_ref"] != policy["source_ref"], "comparison is its own baseline")
    expected = results(contract.get("expected"))
    need(expected[1], "independent comparison needs an informative expected population")
    need(any(type(value) in (int, float) for row in contract["expected"]["rows"] for value in row.values()),
         "original numerical expectation unavailable")
    require(contract["level"] != "total" or len(expected[1]) == 1, "total must have one expected row")
    require(results(record.get("result")) == expected, "governed query result differs")


def compare_probe(check, captured):
    request = check.get("request")
    require(isinstance(request, dict) and text(request.get("resource")) and text(request.get("operation"))
            and canonical(request) == canonical(captured.get("request")), "probe operation or resource differs")
    need(text(captured.get("operation_id")), "executed operation identity unavailable")
    response = captured.get("response")
    need(isinstance(response, dict), "operation result unavailable")
    status, exp, kind = response.get("http_status"), check.get("expected"), check["kind"]
    need(type(status) is int and (status == 403 or 200 <= status < 300), "ambiguous native operation result")
    if exp == "denied":
        require(status == 403, "operation unexpectedly allowed")
        return
    require(status != 403 and response.get("success") is not False and not response.get("error")
            and not response.get("errors"), "operation reported a denial or error")
    if kind in ("rights", "document"):
        require(exp == ("allowed" if kind == "rights" else "visible"), "invalid access expectation")
        require(response.get("resource") == request["resource"], "returned resource differs")
    else:
        require(results(response.get("result")) == results(exp), "visible rows or control result differs")


def verify_topic(spec, *, context, topic_name, candidate_sha256, originals=None, artifact_sha256=None, document_ids=None):
    """Evaluate supplied bytes only. No read, mutation, delegation or grant occurs."""
    originals = {} if originals is None else originals
    report = {"status": "pending", "model_ready": False, "delivery_ready": False, "write_authorized": False,
              "topic_response_sha256": None, "origin_authenticated": False, "documents": [], "checks": [], "gaps": [], "failures": []}

    def run(name, stage, fn):
        try:
            value = fn()
        except (Missing, Conflict, TypeError, KeyError, ValueError, RecursionError, OverflowError) as exc:
            pending = isinstance(exc, Missing)
            status = "pending" if pending else "failed"
            if isinstance(exc, InvalidPin):
                stage = "model"
            reason = str(exc) if isinstance(exc, (Missing, Conflict)) else "malformed evidence"
            report["gaps" if pending else "failures"].append({"check": name, "reason": reason})
            value = None
        else:
            status = "verified"
        report["checks"].append({"check": name, "stage": stage, "status": status})
        return value

    def finish():
        model = [c for c in report["checks"] if c["stage"] == "model"]
        report["model_ready"] = bool(model) and all(c["status"] == "verified" for c in model)
        report["delivery_ready"] = report["model_ready"] and all(c["status"] == "verified" for c in report["checks"])
        report["status"] = "failed" if report["failures"] else "verified" if report["delivery_ready"] else "pending"
        return report

    def setup():
        require(isinstance(spec, dict) and type(spec.get("schema_version")) is int
                and spec["schema_version"] == 1 and isinstance(originals, dict), "invalid verification contract")
        require(artifact_sha256 is None or isinstance(artifact_sha256, str) and HASH.fullmatch(artifact_sha256),
                "invalid artifact fingerprint")
        require(document_ids is None or isinstance(document_ids, (list, tuple)) and document_ids
                and all(text(d) for d in document_ids) and len(set(document_ids)) == len(document_ids),
                "invalid requested document identities")
        return scope_of(context, topic_name, candidate_sha256)

    scope = run("scope", "model", setup)
    if scope is None:
        return finish()

    def load(ref, kind):
        record = original(ref, originals)
        observed(record, scope, kind)
        return record

    def policy_check():
        policy = load(spec.get("policy"), "policy")
        require(isinstance(policy.get("topic_response_sha256"), str)
                and HASH.fullmatch(policy["topic_response_sha256"]), "reviewed Topic fingerprint required")
        comparisons = indexed(policy.get("comparisons"), "comparison")
        require({x.get("level") for x in comparisons.values()} == {"total", "slice"},
                "independent total and slice required")
        require(len({fingerprint(x.get("query")) for x in comparisons.values()}) == len(comparisons),
                "distinct total and slice query scopes required")
        personas = policy.get("personas")
        need(isinstance(personas, dict) and all(p in personas for p in PERSONAS), "three persona expectations required")
        uniform = policy.get("audience", {}).get("mode") == "uniform"
        if uniform:
            need(text(policy["audience"].get("basis_ref")) and text(policy["audience"].get("reason")),
                 "uniform existing audience policy unavailable")
        roles = list(PERSONAS)
        if uniform and isinstance(personas["restricted"], dict) and text(personas["restricted"].get("not_applicable_reason")):
            roles.remove("restricted")
        require(all(isinstance(personas[p], dict) and text(personas[p].get("principal_id")) for p in roles),
                "intended persona identities required")
        if not uniform:
            require(len({personas[p]["principal_id"] for p in roles}) == len(roles),
                    "three distinct intended personas required")
        if uniform and personas["allowed"]["principal_id"] == personas["default"]["principal_id"]:
            require(personas["allowed"].get("attributes") == personas["default"].get("attributes") == {},
                    "one session may represent the same unprovisioned public audience only")
        return policy

    policy = run("policy", "model", policy_check)
    if policy is None:
        return finish()
    run("identity", "model", lambda: model_identity(load(spec.get("identity"), "identity"), context))
    run("validation", "model", lambda: model_validation(load(spec.get("validation"), "validation"), context))
    report["topic_response_sha256"] = run("readback", "model", lambda: read_topic(
        load(spec.get("readback"), "readback"), context, topic_name, policy["topic_response_sha256"]))

    def observations(key, kind):
        refs = spec.get(key, [])
        require(isinstance(refs, list), "observation references must be a list")
        return indexed([load(ref, kind) for ref in refs], kind)

    queries = run("query captures", "model", lambda: observations("queries", "query")) or {}
    for c in policy["comparisons"]:
        def compare(c=c):
            need(c["id"] in queries, "query result unavailable")
            compare_query(c, queries[c["id"]], policy, context)
        run("query/" + c["id"], "model", compare)

    people = run("access captures", "model", lambda: observations("access", "access")) or {}
    surfaces = policy.get("surfaces", {})
    additional = {}

    def delivery_policy():
        record = load(spec["delivery_policy"], "delivery_policy")
        need(artifact_sha256 is not None, "delivery artifact revision not supplied")
        require(record.get("artifact_sha256") == artifact_sha256
                and record.get("policy_sha256") == spec["policy"]["sha256"], "delivery review binding differs")
        require(not surfaces and not any(c.get("kind") in ("document", "control")
                for row in policy["personas"].values() for c in row.get("probes", [])),
                "delivery policy cannot supersede an existing surface plan")
        extension = record.get("personas")
        require(isinstance(extension, dict) and set(extension) <= set(PERSONAS)
                and isinstance(record.get("surfaces"), dict), "invalid delivery policy")
        for probes in extension.values():
            require(isinstance(probes, list) and all(isinstance(c, dict) and c.get("kind") in ("document", "control")
                    for c in probes), "delivery policy may only add surface checks")
        return record

    if spec.get("delivery_policy") is not None:
        supplement = run("delivery policy", "delivery", delivery_policy)
        if supplement is not None:
            surfaces, additional = supplement["surfaces"], supplement["personas"]

    def artifact_binding():
        need(artifact_sha256 is not None, "delivery artifact revision not supplied")
        docs = surfaces.get("document", {}).get("resources")
        need(isinstance(docs, list) and docs, "exact delivery document required")
        if document_ids is not None:
            require(set(docs) == set(document_ids), "delivery document set differs")

    run("artifact binding", "delivery", artifact_binding)
    for role in PERSONAS:
        planned = policy["personas"][role]
        if (role == "restricted" and policy.get("audience", {}).get("mode") == "uniform"
                and text(planned.get("not_applicable_reason"))):
            continue

        def access_setup():
            need(role in people, "persona session unavailable")
            rec = people[role]
            signed_user(rec.get("identity"), planned["principal_id"], persona=True)
            attributes = planned.get("attributes")
            need(isinstance(attributes, dict) and isinstance(rec.get("attributes"), dict),
                 "effective user attributes unavailable")
            require(canonical(attributes) == canonical(rec["attributes"]), "effective user attributes differ")
            return indexed(rec.get("probes"), "probe")

        actual = run("session/" + role, "model", access_setup)

        def plan_checks():
            checks = indexed(planned.get("probes"), "policy probe")
            kinds = {c.get("kind") for c in checks.values()}
            require({"rights", "rows"} <= kinds <= {"rights", "rows", "document", "control"},
                    "model rights and rows probes required")
            for kind in ("rights", "rows"):
                scoped = [c for c in checks.values() if c.get("kind") == kind and
                          c.get("request", {}).get("resource") == topic_name and
                          c["request"].get("operation") in ("query", "query-rows")]
                need(scoped, "effective Topic query rights and row scope required")
                if role == "allowed":
                    require(any(c.get("expected") == "allowed" if kind == "rights" else
                                isinstance(c.get("expected"), dict) for c in scoped),
                            "intended allowed user must be able to query this Topic")
            return checks

        checks = run("coverage/" + role, "model", plan_checks) or {}
        if role in additional:
            def more():
                additions = indexed(additional[role], "delivery probe")
                require(not set(checks).intersection(additions), "conflicting probe ID")
                return additions
            checks.update(run("delivery plan/" + role, "delivery", more) or {})
        for kind in ("document", "control"):
            def coverage(kind=kind):
                targets = surfaces.get(kind)
                need(isinstance(targets, dict), "surface applicability unspecified")
                applicable = targets.get("resources")
                need(isinstance(applicable, list), "surface resources unspecified")
                require(all(text(t) for t in applicable) and len(set(applicable)) == len(applicable),
                        "invalid surface resources")
                need(applicable or text(targets.get("not_applicable_reason")), "surface exclusion unexplained")
                covered = {c["request"]["resource"] for c in checks.values() if c["kind"] == kind}
                need(set(applicable) <= covered, "required surface probe missing")
                require(covered == set(applicable), "unexpected surface target")
            run("coverage/" + role + "/" + kind, "delivery", coverage)
        for pid, check in checks.items():
            def probe():
                need(actual is not None and pid in actual, "persona operation unavailable")
                capture = actual[pid]
                if check["kind"] in ("document", "control"):
                    need(artifact_sha256 is not None and capture.get("artifact_sha256") is not None,
                         "artifact revision unobserved")
                    require(capture["artifact_sha256"] == artifact_sha256, "artifact revision differs")
                    request = check.get("request", {})
                    document = request.get("resource") if check["kind"] == "document" else request.get("document_id")
                    docs = surfaces.get("document", {}).get("resources", [])
                    require(text(document) and document in docs and capture.get("document_id") == document,
                            "operation observed on a different document")
                compare_probe(check, capture)
                if check["kind"] == "document" and check["expected"] == "visible":
                    if document not in report["documents"]:
                        report["documents"].append(document)
            stage = "delivery" if check["kind"] in ("document", "control") else "model"
            run(role + "/" + pid, stage, probe)
    def opened_documents():
        docs = surfaces.get("document", {}).get("resources")
        need(isinstance(docs, list) and docs and set(docs) == set(report["documents"]),
             "visible observation required for each delivery document")

    run("visible delivery documents", "delivery", opened_documents)
    report["documents"].sort()
    return finish()
