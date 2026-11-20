"""Prepare a reviewable branch-only Omni request from the coordinator's rechecked candidate.

The caller owns project/route validation, host capability and authorization. This
module performs no I/O, takes no credentials and exposes no adapter or write CLI.
"""
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re


def require(value, message):
    if not value:
        raise ValueError("semantic_branch." + message)


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(raw).hexdigest()


def object_value(value, message):
    require(isinstance(value, dict), message)
    return value


def inventory(raw):
    """Compare every file in Omni's combined YAML response, including unedited files."""
    object_value(raw, "yaml_response_required")
    files = object_value(raw.get("files"), "complete_file_map_required")
    checksums = object_value(raw.get("checksums"), "complete_checksum_map_required")
    require(files.keys() == checksums.keys() and type(raw.get("version")) is int
            and raw["version"] >= 0 and all(type(k) is str and k for k in files)
            and all(type(value) is str for value in files.values())
            and all(type(value) is str and value for value in checksums.values()),
            "incomplete_yaml_response")
    return {"version": raw["version"], "inventory_sha256": digest({"files": files, "checksums": checksums})}


def author_scope(identity, models, context, authorization=None):
    """Return the observed writer scope. An organization key never supplies viewer evidence."""
    if not all(isinstance(v, dict) for v in (identity, models, context)):
        return None
    principal = context.get("principal_id")
    roles = identity.get("rolesByModel")
    if not isinstance(roles, dict):
        return None
    role = roles.get(context.get("model_id"))
    user = identity.get("user")
    if (not principal or not isinstance(user, dict) or user.get("membershipId") != principal
            or not isinstance(role, dict) or not role or identity.get("rolesByModelTruncated") is True):
        return None
    if identity.get("keyScope") == "user":
        return "user"
    if (identity.get("keyScope") != "organization" or identity.get("orgRole") != "ORG_ADMIN"
            or role.get("baseRole") != "CONNECTION_ADMIN" or not isinstance(role.get("permissions"), list)
            or not all(permission in role["permissions"] for permission in ("UPDATE", "USE_IDE"))
            or not isinstance(authorization, dict) or authorization.get("kind") != "omni_branch_authorization"
            or authorization.get("role") != "user" or authorization.get("context") != context
            or not all(isinstance(authorization.get(k), str) and authorization[k].strip()
                       for k in ("reference", "response_text", "topic_name"))):
        return None
    branch = models.get(context.get("branch_id"))
    parent = models.get(context.get("model_id"))
    if (not isinstance(branch, dict) or not isinstance(parent, dict)
            or parent.get("modelKind") not in ("SHARED", "SHARED_EXTENSION")
            or branch.get("modelKind") != "BRANCH" or branch.get("userId") != user.get("id")
            or not user.get("id") or branch.get("id") != context.get("branch_id")
            or parent.get("id") != context.get("model_id") or branch.get("baseModelId") != parent["id"]
            or any(obj.get("deletedAt") is not None for obj in (parent, branch))
            or not parent.get("connectionId") or parent["connectionId"] != branch.get("connectionId")
            or parent["connectionId"] != role.get("connectionId")):
        return None
    creator = branch.get("createdByPrincipal")
    if isinstance(creator, str):
        try:
            creator = json.loads(creator)
        except ValueError:
            return None
    if (isinstance(creator, dict) and creator.get("type") == "USER"
            and creator.get("userId") == user["id"] and creator.get("membershipId") == principal):
        return "organization_branch_author"
    return None


def prepare_branch(checked_wrapper, snapshot):
    """Create review material only. Unknown prior write outcomes require native reconciliation."""
    wrapper = object_value(checked_wrapper, "candidate_wrapper_required")
    require(wrapper.get("kind") == "omni_modeling_candidate", "candidate_wrapper_required")
    candidate = object_value(wrapper.get("candidate"), "candidate_required")
    require(candidate.get("kind") == "oaa_semantic_model_candidate" and candidate.get("status") == "candidate"
            and candidate.get("authorizes_target_write") is False, "reviewable_candidate_required")
    ctx = object_value(wrapper.get("context"), "destination_required")
    scope = object_value(candidate.get("destination"), "destination_required")
    shared, branch = ctx.get("model_id"), ctx.get("branch_id")
    require(all(isinstance(v, str) and v for v in (shared, branch)) and shared != branch
            and scope.get("model_id") == shared and scope.get("branch_id") == branch
            and ctx.get("workbook_model_id") is None, "distinct_model_branch_required")
    name = wrapper.get("topic_name")
    require(name == candidate.get("topic_name") and isinstance(name, str)
            and re.fullmatch(r"[a-z_][a-z0-9_]*", name), "topic_scope_changed")
    object_value(snapshot, "snapshot_required")
    require(type(snapshot.get("schema_version")) is int and snapshot["schema_version"] == 1
            and snapshot.get("kind") == "omni_semantic_branch_snapshot"
            and snapshot.get("context") == ctx and snapshot.get("baseline_ref") == scope.get("evidence_ref")
            and snapshot.get("candidate_sha256") == candidate.get("candidate_sha256")
            and isinstance(candidate.get("candidate_sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", candidate["candidate_sha256"]),
            "snapshot_scope_changed")
    identity = object_value(snapshot.get("identity"), "current_identity_required")
    models = object_value(snapshot.get("models"), "models_required")
    authorization = snapshot.get("branch_author")
    scope_type = author_scope(identity, models, ctx, authorization)
    require(scope_type is not None and (scope_type == "user" or authorization["topic_name"] == name),
            "intended_branch_author_required")
    parent = object_value(models.get(shared), "shared_model_required")
    child = object_value(models.get(branch), "branch_model_required")
    require(parent.get("id") == shared and parent.get("modelKind") in ("SHARED", "SHARED_EXTENSION")
            and child.get("id") == branch and child.get("modelKind") == "BRANCH"
            and child.get("baseModelId") == shared and parent.get("connectionId")
            and child.get("connectionId") == parent["connectionId"]
            and all(m.get("deletedAt") is None for m in (parent, child)), "wrong_branch_ancestry")
    version = ctx.get("model_version_id")
    require(version is None or child.get("modelVersionId") == version, "branch_model_version_changed")
    review = object_value(snapshot.get("reviewed_baseline"), "reviewed_baseline_required")
    current = object_value(snapshot.get("current"), "current_inventory_required")
    observed = {k: inventory(current.get(k)) for k in ("shared", "branch")}
    require(set(review) == set(observed) and all(isinstance(review[k], dict)
            and type(review[k].get("version")) is int and review[k]["version"] >= 0
            and isinstance(review[k].get("inventory_sha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", review[k]["inventory_sha256"]) for k in observed),
            "reviewed_inventory_digests_required")
    require(scope["evidence_ref"] == "sha256:" + digest(review), "reviewed_baseline_not_pinned_by_candidate")
    require(review["shared"] == observed["shared"], "shared_model_changed")

    files = object_value(candidate.get("files"), "file_map_required")
    require(len(files) == 1, "one_regular_topic_per_branch_plan")
    path, yaml = next(iter(files.items()))
    # The combined YAML API takes a native filename. Filesystem export aliases
    # may be reviewed locally, but silently changing one here would invalidate its pin.
    require(path == name + ".topic", "native_filename_required_rebuild_as_topic")
    require(type(yaml) is str and yaml.strip(), "regular_topic_file_required")
    changes = candidate.get("changes")
    require(type(changes) is list and len(changes) <= 1, "single_change_required")
    result = {"kind": "omni_semantic_branch_plan", "schema_version": 1, "context": dict(ctx),
              "topic_name": name, "candidate_sha256": candidate["candidate_sha256"],
              "baseline": observed, "author_scope": scope_type, "requests": [], "authorizes_target_write": False,
              "native_verified": False}
    if snapshot.get("previous_attempt") is not None:
        attempt = object_value(snapshot["previous_attempt"], "prior_attempt_required")
        require(attempt.get("candidate_sha256") == candidate["candidate_sha256"]
                and attempt.get("file_name") == path and attempt.get("context") == ctx
                and isinstance(attempt.get("reference"), str) and attempt["reference"].strip(),
                "prior_attempt_scope_changed")
        return {**result, "status": "reconcile_prior_attempt", "attempt_reference": attempt["reference"]}
    require(review["branch"] == observed["branch"], "branch_changed_since_review")
    suffixes = {name.casefold() + suffix for suffix in (".topic", ".topic.yaml", ".topic.yml")}
    branch_files = current["branch"]["files"]
    for origin in ("shared", "branch"):
        aliases = {k for k in current[origin]["files"] if PurePosixPath(k).name.casefold() in suffixes}
        require(aliases <= {path}, "ambiguous_topic_path")
    if not changes:
        require(branch_files.get(path) == yaml, "unchanged_topic_drift")
        return {**result, "status": "unchanged"}
    action = object_value(changes[0], "change_required")
    require(action.get("path") == path and action.get("sha256") == sha256(yaml.encode()).hexdigest(),
            "candidate_file_digest_changed")
    if action.get("operation") == "create":
        require(action.get("expected_sha256") is None and path not in branch_files
                and path not in current["shared"]["files"], "topic_name_collision")
    else:
        require(action.get("operation") == "update" and path in branch_files
                and action.get("expected_sha256") == sha256(branch_files[path].encode()).hexdigest(),
                "existing_file_baseline_changed")
    body = {"branchId": branch, "fileName": path, "yaml": yaml, "mode": "combined"}
    require(type(snapshot.get("git_enabled")) is bool and all(
        not isinstance(model.get("hasGit"), bool) or model["hasGit"] == snapshot["git_enabled"]
        for model in (parent, child)), "git_configuration_required")
    if snapshot["git_enabled"]:
        message = snapshot.get("commit_message")
        require(isinstance(message, str) and 0 < len(message.strip()) <= 240
                and message.isprintable(), "reviewed_commit_message_required")
        body["commitMessage"] = message
    result["requests"].append({"operation": "models yaml-create", "model_id": shared, "body": body})
    return {**result, "status": "prepared_for_review"}
