# Windows setup (preview)

Use this path for a local Windows 11 x64 workspace, a standard user account, a fixed NTFS drive, Git and an existing approved 64-bit x64 Python 3.9 or later. The preview uses native Windows Python and PowerShell 5.1 or 7. Source checks have been run on macOS. End-to-end operation on Windows still needs verification.

## Open a workspace and start a chat

1. Create an empty local folder and open it in your coding assistant. If your Documents or Desktop folder is synchronized or redirected, choose an ordinary local folder for this preview.
2. Clone the preview revision supplied by your maintainer into a subfolder named `Omni-Artifact-Accelerator`. If you already have that checkout, open the folder containing it. Keep the project beside the checkout.
3. Paste the same message as on Mac:

   > Read `Omni-Artifact-Accelerator/AGENTS.md` and use the accelerator in that folder. Help me get started.

For example, to create the parent folder in PowerShell:

```powershell
$workspace = Join-Path $env:LOCALAPPDATA 'OmniWork'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
Set-Location -LiteralPath $workspace
```

For a published preview revision, let your assistant clone the repository and select the supplied commit in that new checkout. The equivalent PowerShell steps are:

```powershell
git clone https://github.com/exploreomni/Omni-Artifact-Accelerator.git
$previewRevision = Read-Host 'Paste the full Windows preview commit supplied by the maintainer'
git -C Omni-Artifact-Accelerator switch --detach $previewRevision
git -C Omni-Artifact-Accelerator rev-parse HEAD
```

Confirm the printed revision matches the one you selected, then open the parent folder in your assistant.

The assistant should confirm the checkout, use your stated migration or net-new goal, and run the workspace check below. A local checkout can be used directly. WSL, copying global skills and installing another CLI are unnecessary for this setup.

## What the assistant checks

Run the helper from the checkout. In PowerShell, use `Get-Command py,python -ErrorAction SilentlyContinue` to locate installed interpreters. Use the approved local Python for this workspace. For a Windows Python launcher the equivalent PowerShell command is:

```powershell
Set-Location -LiteralPath (Join-Path $workspace 'Omni-Artifact-Accelerator')
py -3 -I -S -B skills/omni-artifact-accelerator/scripts/analyst_project.py workspace-setup --workspace "$workspace"
```

The result reports the interpreter platform, the local workflow and the connection separately. An assistant with access to an Omni MCP registry passes the observed tool name with `--mcp-tool` or records an inventory with no matching tool using `--mcp-checked`. A user-selected CLI, API or offline route can be supplied with `--route`. The setup check reads existing configuration and filesystem capabilities. It creates no project and has no publication authority. If Python is unavailable, continue the interview and explain which prerequisite is missing before proposing any installation.

| Operation | Windows preview scope |
| --- | --- |
| Local onboarding, project creation, journal, and resume | Implemented for private single-user projects on local NTFS. The assistant uses the existing `init`, `run-start`, `stage-status` and other stage commands in the selected checkout. Native behavior is pending verification. |
| Migration and net-new design | Preserve migrations use one source-matched specification. Redesign and net-new work retain three choices. Local controls, assembly and review use the same contracts as Mac. Domo Pro Code planning accepts supplied original files. Individual readers and connected source capture need separate qualification. |
| Additional migration readers, report imports and Data Model Accelerator handoffs | Windows execution for these paths is pending. Keep the original source evidence and handoff receipts. Use a qualified host for a reader that requires POSIX. |
| Existing Omni MCP or CLI | Discover an operation-specific host MCP tool or existing Windows CLI. A declared route still needs identity and access checks. Host-managed read access can support authorized discovery. |
| Windows CLI release | Existing executable inspection and release planning are available. For a separately approved, pinned binary, a scoped version preview prepares the exact host action. Packaged installation and tenant transport require further Windows qualification. [CLI setup](../skills/omni-artifact-accelerator/references/omni-cli-setup.md) |
| Native create, update, publication, installed-skill activation and local visual MCP server | Outside this Windows preview. Record the missing operation and retain the candidate for authorized continuation. The host's Omni connector and the optional local visual MCP server are separate tools. |

## Recovery

If the local gate is blocked, retain the original brief, source evidence and last recorded stage. The assistant can continue permitted read-only discovery. Stop dependent builds and native writes. Avoid generating an alternative App outside the journal or asking the tester to publish a diagnostic App and paste logs.

New Windows projects are prepared privately under a unique `.oaa-init-*` directory and moved into the requested name only after local initialization completes. After an interruption, leave any staging directory and prior project intact. Resume a completed project from the original workspace. If the requested project was never committed, a new initialization can use the still-unused project name. Inspect leftovers before separately authorized cleanup. Switching machines, changing a checkout in place, or downgrading an upgraded journal requires separate review. [Project continuity](HOW_TO.md#resume-a-project-on-its-original-version)

## Preview qualification

On a Windows 11 x64 test machine with a local NTFS temporary directory, a maintainer can run `py -3 -I -S -B tests/test_windows_files.py -v` from the preview checkout. This exercises real ACLs, simultaneous processes, file replacement, junction handling and resume in a new interpreter. Record the test results and investigate any skipped checks before promoting Windows support. The platform routing and interrupted setup checks run separately with `py -3 -I -S -B scripts/validate_source.py --case workspace-setup`.
