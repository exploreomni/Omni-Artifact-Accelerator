# Connect through Omni MCP or the Omni CLI

Honor a user-selected connection, including on resume. For automatic setup, use the first available route that covers the next operation in the intended workspace.

1. Discover the Omni connector through the host’s tool picker, deferred tool search or the configured Omni MCP server’s tool list. Match the tool description and inputs to the next task. For example, a tool that lists Topics can support discovery. Creating an App needs its own authoring operation. A documentation search, a legacy platform’s connector, or the accelerator’s local workflow MCP server does not establish an Omni data connection.
2. If a matching Omni tool is available, use it and carry its name into the engagement’s host inventory. This works in a chat with no local shell. If the automatic check finds no match, inspect the CLI on the machine that will execute it. If the user explicitly chose MCP or CLI and it cannot do the task, explain what is missing and let them choose an alternative.
3. When neither route covers the task, offer to connect Omni MCP through the host, set up the official CLI with permission, or continue offline. If the host cannot inspect a registry or machine, describe that part as unknown. Retain a declined installation for the engagement.

Discovery identifies a candidate connection. Verify the intended identity, instance, Topic access and any DMA handoff through the existing Stage A workflow. Use the existing publication and access approvals for writes. If the operation or target changes, check coverage again.

## Use the setup helper in a shell

The host owns MCP discovery. Pass the exact matching identifier from the configured Omni connector. When the host completed discovery and found no matching operation, use the second invocation instead. Omitting both discovery flags leaves MCP availability unknown.

```sh
OAA_SETUP=skills/omni-artifact-accelerator/scripts/omni_cli_setup.py
python3 -I -S -B "$OAA_SETUP" --omni-mcp-tool "$OAA_MATCHING_TOOL"
python3 -I -S -B "$OAA_SETUP" --no-matching-omni-mcp-tool
```

| Automatic or MCP result | Agent action |
| --- | --- |
| `use_mcp` | Continue through the named tool and the normal access checks. Skip CLI setup. |
| `inspect_host_mcp` | Inspect the host’s available Omni tools. If discovery is unavailable, explain the limitation and available alternatives. |
| `choose_connection` | The host found no matching tool and the helper found no usable CLI candidate. Use the reported CLI status to explain the choices. |
| `mcp_operation_unavailable` | The explicitly selected MCP route lacks this operation. Surface that gap and available alternatives. |
| `inspect_configured_cli`, `inspect_existing_cli` | Verify the CLI candidate as described below before use. |

Use `--route mcp` for an explicit MCP choice. An explicit API or offline route skips both connection checks. In a host without a shell, use the same MCP selection directly and retain the existing execution requirements for later gates.

## Check before offering CLI installation

Once the user chooses the CLI, use the selected orchestrator's own helper on the intended machine:

```sh
OAA_SETUP=skills/omni-artifact-accelerator/scripts/omni_cli_setup.py
python3 -I -S -B "$OAA_SETUP" --route cli
```

| Result | Agent action |
| --- | --- |
| `inspect_configured_cli`, `inspect_incomplete_pin` | Check the existing host configuration. A missing file, mismatched digest or incomplete pin needs reconciliation with its owner. |
| `inspect_existing_cli` | Confirm this is the official, approved executable. Resolve any package-manager link to its canonical binary. Reuse it if covered. Finding a name on PATH neither establishes provenance nor authorizes execution. |
| `prepare_install_offer` | Read public metadata from the returned official release API with the host's approved read tool. Save that JSON in a private temporary location. Prepare the offer below. No binary is needed yet. |
| `unsupported_platform`, `inspect_destination` | Explain the specific gap and offer an available connector or operator-managed installation. |

```sh
python3 -I -S -B "$OAA_SETUP" --route cli --release-metadata "$OAA_RELEASE_JSON"
```

The planner selects one stable tagged asset for the current OS and architecture, verifies its official URL and requires a published SHA-256 digest. A missing digest, unmatched platform or unavailable metadata leaves installation pending. The read-only plan can be prepared offline from official release metadata the operator has already obtained. [Official installation guide and supported platforms](https://github.com/exploreomni/cli#installation)

## Ask once for the exact installation

Use a short question with real values from the plan:

> I can install Omni CLI {version} for your account at {destination} and run a local version check. May I proceed? You can also skip setup or use your existing Omni connection.

Show the platform, official archive link, SHA-256 and actions in the review details. Cover the tagged release's bundled dependencies, license, provenance, known advisory information and verification limits under the [dependency policy](dependency-policy.md). The scope is one prebuilt binary, temporary files, the necessary user-owned directory and a local version check. The only download is from the official release and its GitHub asset delivery service. Describe removal of this exact new file as rollback. Use the host's real one-time approval interface when available. The user must consent, and Austin's project dependency sign-off must cover these exact actions. When the user is the authorized approver, one scoped approval can cover both.

A qualified host executes the approved steps on the user's behalf. A chat response, an agent-written file or the plan hash alone cannot authenticate host authority. If declined, retain that choice. If the host cannot enforce the grant or reach the **intended machine**, provide the exact plan for the operator and continue independent work. Never silently install, upgrade the existing CLI, run an installer from a moving branch, or request a permanent shell permission.

## Complete the approved install

1. Have the trusted host bind the exact plan and dependency review to the permission. Create a private temporary directory on the destination filesystem. Check that the destination directory belongs to the user, that other users cannot write to it, and that its path has no links or redirections. Create it with private permissions if necessary. Use the current user's access.
2. Download the plan's exact `url` into that staging directory through the approved host transport. Use HTTPS, bounded downloads and GitHub's official asset-delivery origins. Omit credentials. Retain the reviewed metadata. Use an already-approved attestation verifier if required by the organization. [Upstream verification](https://github.com/exploreomni/cli#verifying-release-artifacts)
3. Run the following with the `plan_sha256` from the host approval. The helper rechecks the offer and archive digest, reads only the named binary, and creates a new, non-executable `omni.payload` in the private directory. It returns the **binary** digest used by the transport. A changed offer or failed checksum stops the install.

```sh
python3 -I -S -B "$OAA_SETUP" --route cli --release-metadata "$OAA_RELEASE_JSON" \
  --plan-sha256 "$OAA_PLAN_SHA256" --archive "$OAA_ARCHIVE" --stage-in "$OAA_STAGE"
```

4. Have the host perform the following file operation under the actual install grant. Supply `staged` from its private staging directory, `destination` from the approved plan and `binary_sha256` from step 3. The new hard link fails if the destination appeared concurrently. On interruption, inspect the destination and its digest before retrying. Remove only this run's temporary files.

```python
# Trusted host operation, after checking the user-owned directory and approval.
from pathlib import Path
import hashlib
import os

staged, destination = Path(staged), Path(destination)
if staged.resolve(strict=True) != staged or destination.parent.resolve(strict=True) != destination.parent:
    raise ValueError("The approved paths must be canonical")
if hashlib.sha256(staged.read_bytes()).hexdigest() != binary_sha256:
    raise ValueError("Staged bytes changed")
if os.name == "posix":
    staged.chmod(0o700)
os.link(staged, destination)
if hashlib.sha256(destination.read_bytes()).hexdigest() != binary_sha256:
    raise ValueError("Installed bytes need investigation")
```
5. Run the **absolute, verified executable** with `--version` using the host's clean environment without credentials, with `OMNI_NO_UPDATE_NOTIFIER=1`. Compare the reported version with the selected tag. Report the installed path and version, or the precise verification failure. Using the absolute path also works when the user's bin directory is off PATH.
6. For the accelerator's bounded POSIX transport, supply the canonical executable path as `OAA_OMNI_CLI_PATH` and its **installed binary** SHA-256 as `OAA_OMNI_CLI_SHA256` through the approved host configuration. This native binary runs directly. Use a clean host configuration with `OAA_OMNI_RUNTIME_PATH` and `OAA_OMNI_RUNTIME_SHA256` absent. An existing interpreter configuration needs owner review before switching. The official Windows binary supports direct CLI use. The package's bounded process transport requires a qualified POSIX host.

**Connecting Omni comes next.** Verify the intended instance and identity separately at Stage A. For direct interactive use, the user can configure a profile privately with `omni config init`. For bounded adapters, use the host's approved secret mechanism. A successful version check establishes local execution only. Leave shell profiles, saved credentials and tenant resources under their own permissions. [Official CLI quick start](https://github.com/exploreomni/cli#quick-start)
