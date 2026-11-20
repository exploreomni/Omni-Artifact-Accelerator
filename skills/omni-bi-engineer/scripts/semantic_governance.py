"""Plan one reviewed audience's exact model/document access from supplied evidence.

Pure comparison of local JSON values. The result is a review proposal only.
"""


class Gap(ValueError):
    """The supplied inspection or request cannot support this exact change."""


def need(condition, message):
    if not condition:
        raise Gap(message)


def text(value):
    return type(value) is str and bool(value.strip())


def name(value):
    return text(value) and value.isascii() and value.replace("_", "a").isalnum() and (
        value[0].isalpha() or value[0] == "_")


def values(items):
    need(isinstance(items, list) and all(text(v) for v in items)
         and len(items) == len(set(items)), "provide distinct, exact values")
    return items


def literal(value):
    return (text(value) and value.strip() == value and value.isascii()
            and all(c.isalnum() or c in " ._-" for c in value)
            and value.casefold() not in ("all", "everyone", "any", "null"))


def group_attribute(current, attr, group):
    need(name(attr), "provide the exact inspected user attribute name")
    observed = current["attributes"].get(attr)
    need(isinstance(observed, dict) and text(observed.get("evidence_ref"))
         and observed.get("complete") is True, "verify effective attribute assignments and defaults")
    need(observed.get("value_mode") == "exact" and observed.get("missing_value_behavior") == "deny",
         "verify literal matching and the effective unprovisioned-user behavior")
    assignments = observed.get("group_values")
    need(isinstance(assignments, dict) and group in assignments,
         "verify the requested group's existing attribute mapping")
    for mapped in assignments.values():
        need(all(literal(v) for v in values(mapped)), "resolve wildcard or expression-valued entitlements")
    selected = values(assignments[group])
    need(selected and all(literal(v) for v in selected), "supply the group’s precise literal attribute values")
    default = values(observed.get("default_values"))
    individuals = values(observed.get("individual_values"))
    need(all(literal(v) for v in default + individuals), "resolve wildcard default or individual entitlements")
    return selected, default, individuals, assignments


def grant_plan(current, request, group, snippets, reused):
    grant = request["grant"]
    if grant is None:
        return
    need(isinstance(grant, dict) and set(grant) == {"name", "user_attribute", "allowed_values", "target"},
         "supply one grant name, attribute, allowed values and exact binding target")
    grant_name, attr, target = grant["name"], grant["user_attribute"], grant["target"]
    need(name(grant_name), "supply an exact model grant name")
    requested = values(grant["allowed_values"])
    selected, default, individuals, assignments = group_attribute(current, attr, group)
    need(set(requested) == set(selected), "requested grant values differ from the inspected group mapping")
    others = set(default) | set(individuals)
    for other_group, assigned in assignments.items():
        if other_group != group:
            others.update(assigned)
    need(not others.intersection(requested), "grant values also match another group, an individual override or a default")
    need(isinstance(current["access_grants"], dict), "inspect existing model grant definitions")
    definition = {"user_attribute": attr, "allowed_values": sorted(requested)}
    if grant_name in current["access_grants"]:
        existing = current["access_grants"][grant_name]
        need(isinstance(existing, dict) and set(existing) == set(definition)
             and existing["user_attribute"] == attr
             and set(values(existing["allowed_values"])) == set(requested),
             "an existing grant with this name has a different definition")
        reused.append({"kind": "model_grant", "name": grant_name})
    else:
        need(text(current.get("model_grant_syntax_ref")),
             "supply the inspected native model access_grants syntax reference")
        usage = current.get("grant_usage", {})
        need(isinstance(usage, dict) and usage.get("complete") is True and text(usage.get("evidence_ref"))
             and isinstance(usage.get("bindings"), dict), "inspect model-wide references to the missing grant")
        bound = values(usage["bindings"].get(grant_name, []))
        target_ref = "topic:" + current["topic_name"] if target == "topic" else "field:" + str(target)
        need(set(bound) <= {target_ref}, "the missing grant is referenced outside the requested target")
        snippets["model"] = {"access_grants": {grant_name: definition}}

    if target == "topic":
        required = values(current["topic"]["required_access_grants"])
        section = snippets.setdefault("topic", {})
    else:
        field = current["fields"].get(target)
        need(isinstance(field, dict) and field.get("kind") in ("dimension", "measure"),
             "resolve the exact Topic or protected field binding")
        required = values(field["required_access_grants"])
        section = snippets.setdefault("fields", {}).setdefault(target, {})
    need(not required or required == [grant_name],
         "preserve existing grant requirements and review their combination semantics")
    if grant_name in required:
        reused.append({"kind": "required_access_grant", "target": target, "name": grant_name})
    else:
        if target != "topic":
            need(values(current["fields"][target].get("bound_topics")) == [current["topic_name"]],
                 "review other Topics using the field before a model-wide field change")
        section["required_access_grants"] = [grant_name]


def filter_plan(current, request, group, snippets, reused):
    requested = request["row_filter"]
    if requested is None:
        return
    need(isinstance(requested, dict) and set(requested) == {"field", "user_attribute"},
         "supply one exact row field and user attribute binding")
    field = current["fields"].get(requested["field"])
    need(isinstance(field, dict) and field.get("kind") == "dimension",
         "verify the row key as a reachable dimension on the selected Topic")
    need(requested["user_attribute"] in values(field.get("equality_attributes")),
         "verify the field and attribute represent the same entitlement key with compatible equality semantics")
    _, default, _, _ = group_attribute(current, requested["user_attribute"], group)
    need(not default, "review the nonempty default row entitlement before planning this filter")
    filters = current["topic"].get("access_filters")
    need(isinstance(filters, list), "inspect the current Topic access_filters")
    need(not filters or filters == [requested], "review the entire existing row access filter combination")
    if requested in filters:
        reused.append({"kind": "row_filter", **requested})
    else:
        snippets.setdefault("topic", {})["access_filters"] = [dict(requested)]


def document_plan(current, item, group, proposals, reused, controls):
    need(isinstance(item, dict) and set(item) == {"document_id", "source", "role", "controls"},
         "supply the exact document, intended grant source, role and control scopes")
    doc_id, requested, role = item["document_id"], item["source"], item["role"]
    need(text(doc_id) and requested in ("direct", "inherited") and text(role), "invalid document grant request")
    document = current["documents"].get(doc_id)
    need(isinstance(document, dict) and text(document.get("evidence_ref")) and document.get("complete") is True,
         "inspect this exact document's effective direct and inherited group access")
    need(role in values(document.get("read_only_roles")) and not any(t in role.casefold() for t in
         ("own", "edit", "admin", "manage", "publish", "creat", "writ")), "verify the exact native read-only document role")
    direct, inherited = document.get("direct"), document.get("inherited")
    need(isinstance(direct, dict) and isinstance(inherited, dict), "inspect both direct and inherited document grants")
    for grants in (direct, inherited):
        if group in grants:
            need(grants[group] == role, "existing direct or inherited role differs; preserve it for owner review")
    effective = document.get("effective")
    need(isinstance(effective, dict) and group in effective,
         "inspect effective access for this group, including public, nested and inherited access")
    if group in direct or group in inherited:
        need(effective[group] == role, "effective access differs from the scoped role or its inspected grant")
    else:
        need(effective[group] is None,
             "the group already has access through another source; inspect its origin before adding a direct grant")
    if group in document[requested]:
        reused.append({"kind": "document_grant", "document_id": doc_id, "source": requested, "role": role})
    elif requested == "inherited":
        raise Gap("requested inherited grant is absent; identify and review the parent and its affected documents")
    elif group in inherited:
        raise Gap("access is already inherited; clarify the need for a second, direct grant")
    else:
        proposals.append({"operation": "propose_direct_group_grant", "document_id": doc_id,
                          "group_id": group, "role": role, "inspection_ref": document["evidence_ref"]})

    need(isinstance(item["controls"], list), "declare the relevant document control scopes")
    seen = set()
    for control in item["controls"]:
        need(isinstance(control, dict) and set(control) == {"id", "field", "consumer_ids"},
             "identify each existing control, governed field and affected consumers")
        cid = control["id"]
        need(text(cid) and cid not in seen, "duplicate or missing control identity")
        seen.add(cid)
        selected = values(control["consumer_ids"])
        actual = document.get("controls", {}).get(cid)
        need(selected and isinstance(actual, dict) and control["field"] in current["fields"]
             and actual.get("field") == control["field"]
             and set(values(actual.get("consumer_ids"))) == set(selected),
             "control field or affected consumer scope is missing or differs")
        controls.append({"document_id": doc_id, "control_id": cid, "field": control["field"],
                         "consumer_ids": sorted(selected)})


def plan_access(spec, *, context, topic_name):
    """Return reusable matches, inert model fragments and precise document grant proposals."""
    report = {"status": "pending", "topic_name": topic_name, "model_snippets": {}, "document_proposals": [],
              "reused": [], "controls": [], "gaps": [], "authorizes_target_write": False, "native_verified": False}
    try:
        need(isinstance(spec, dict) and type(spec.get("schema_version")) is int and spec["schema_version"] == 1,
             "use governance plan schema version 1")
        need(name(topic_name) and isinstance(context, dict) and all(text(context.get(k)) for k in
             ("base_url", "model_id", "principal_id")) and "branch_id" in context, "supply the selected native context")
        cur, req = spec["current"], spec["request"]
        need(isinstance(cur, dict) and cur.get("context") == context and cur.get("topic_name") == topic_name
             and text(cur.get("evidence_ref")), "the inspection must match this model, branch, Topic and principal")
        need(isinstance(req, dict) and set(req) == {"request_ref", "group_id", "grant", "row_filter", "documents"}
             and text(req["request_ref"]), "supply the attributable audience request and all requested scopes")
        group = req["group_id"]
        need(text(group) and isinstance(cur.get("groups"), dict) and cur["groups"].get(group) == "scoped_group",
             "identify one existing scoped native group by ID")
        if req["grant"] is not None or req["row_filter"] is not None:
            need(isinstance(cur.get("topic"), dict) and isinstance(cur.get("attributes"), dict),
                 "inspect current Topic and user attribute policy")
        need(isinstance(req["documents"], list), "supply an explicit list of requested documents")
        need(req["grant"] is not None or req["row_filter"] is not None or bool(req["documents"]),
             "specify a model, row or document access outcome")
        report.update(group_id=group, source_ref=cur["evidence_ref"], request_ref=req["request_ref"])
    except (Gap, KeyError, TypeError, AttributeError) as exc:
        report["gaps"].append(str(exc) if isinstance(exc, Gap) else "missing or malformed context or policy")
        return report

    def inspect(label, operation, *args):
        try:
            operation(*args)
        except (Gap, KeyError, TypeError, AttributeError) as exc:
            report["gaps"].append(label + ": " + (str(exc) if isinstance(exc, Gap) else "missing or malformed input"))

    snippets, proposals, reused, controls = {}, [], [], []
    inspect("model grant", grant_plan, cur, req, group, snippets, reused)
    inspect("row access", filter_plan, cur, req, group, snippets, reused)
    seen = set()
    for item in req["documents"]:
        doc_id = item.get("document_id") if isinstance(item, dict) else None
        if not text(doc_id) or doc_id in seen:
            report["gaps"].append("document: missing or duplicate document ID")
            continue
        seen.add(doc_id)
        inspect("document " + doc_id, document_plan, cur, item, group, proposals, reused, controls)
    if report["gaps"]:
        return report
    if "fields" in snippets:
        snippets["fields"] = {field: frag for field, frag in snippets["fields"].items() if frag}
    snippets = {key: obj for key, obj in snippets.items() if obj}
    report.update(model_snippets=snippets, document_proposals=proposals, reused=reused, controls=controls,
                  status="proposal" if snippets or proposals else "reuse_existing")
    return report
