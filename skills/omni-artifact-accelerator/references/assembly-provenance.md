# Deterministic assembly provenance

The first-party assembler joins explicitly ordered, pinned local byte files with
one fixed separator. It retains a private record of the exact inputs, manifest,
builder source hashes and output bytes. It performs no templating, variable
substitution, HTML interpretation, minification, code evaluation, generated-source
imports, network calls or dependency installation.

This is local source preparation. The existing build-stage guard still applies.
The resulting HTML must enter the existing candidate freeze and review workflow;
assembly does not create acceptance, dispatch workers or authorize publication.

## API

The fixed package module `scripts/assembly_provenance.py` exposes:

| Function | Request fields | Result |
| --- | --- | --- |
| `build(project, request, P=None, provider=None)` | `manifest`, `output`, `record` | New HTML and provenance record; status `built` |
| `verify(project, request, P=None)` | `record` | Status `verified` or `unknown` |
| `compare(project, request, P=None)` | `previous`, `current` | Status `changed`, `unchanged` or `unknown` |

All request paths are canonical paths relative to the private engagement.
`build` requires a new `.html` output path and a different new `.json` record path.
Parents must already exist. Files are created with mode `0600`, without replacing
anything. Existing paths, symlinks, path traversal and non-regular input files are
rejected. Engagements must be outside the package repository. No runtime or
builder can be selected by a request, environment variable or input manifest.

A successful write creates two files. An ordinary write failure removes files
created by that attempt. The filesystem cannot make the pair transactional across
a process or machine crash; inspect incomplete files after interruption and use
new versioned output and record paths. Never substitute an incomplete record for
candidate evidence.

Example requests:

```json
{
  "manifest": "contracts/assembly-v1.json",
  "output": "deliverables/candidate-v1.html",
  "record": "evidence/assembly-v1.json"
}
```

```json
{"record": "evidence/assembly-v1.json"}
```

```json
{"previous": "evidence/assembly-v1.json", "current": "evidence/assembly-v2.json"}
```

## Manifest contract

The manifest has exactly these fields:

```json
{
  "schema_version": 1,
  "kind": "assembly_manifest",
  "mode": "utf8",
  "separator_utf8": "\n",
  "parts": ["page", "theme"],
  "dependencies": [
    {
      "id": "page",
      "kind": "component",
      "path": "inputs/page.html",
      "sha256": "<SHA-256 of the exact input bytes>",
      "bytes": 123,
      "scopes": ["product_owner", "qa", "security", "ui_ux"],
      "freshness": {
        "mode": "immutable",
        "checked_at": "2026-01-01T00:00:00+00:00",
        "expires_at": null
      }
    },
    {
      "id": "theme",
      "kind": "styles",
      "path": "inputs/theme.html",
      "sha256": "<SHA-256 of the exact input bytes>",
      "bytes": 456,
      "scopes": ["qa", "security", "ui_ux"],
      "freshness": {
        "mode": "immutable",
        "checked_at": "2026-01-01T00:00:00+00:00",
        "expires_at": null
      }
    }
  ]
}
```

Replace the illustrative hashes and lengths with actual pins before building.
Duplicate JSON keys, unknown fields and undeclared part IDs are rejected.
Dependency IDs and paths must each be unique. The `parts` sequence can repeat a
declared ID. Empty input files are permitted. `separator_utf8` is explicit and is
inserted only between parts, without a prefix or trailing separator.

- Kinds are `component`, `styles`, `query`, `asset`, `runtime`, and `unknown`.
  Pin query contracts, selected assets and runtime contracts even when they are
  not emitted into the HTML. A dependency can be retained without appearing in
  `parts`; changes to it still appear in comparison.
- `utf8` validates the emitted files as UTF-8 and preserves their original bytes,
  including line endings and a byte-order mark. Non-emitted binary assets remain
  valid. `bytes` permits arbitrary emitted bytes without decoding. Neither mode
  claims that the result is valid, safe or renderable HTML.
- Dependencies hold literal source bytes. Supply any intended `<style>`,
  `<script>` or markup wrappers in those files. There are no implicit wrappers,
  escaping rules, placeholders, imports or executable build steps.
- `scopes` is a sorted, nonempty subset of `security`, `ui_ux`, `product_owner`,
  and `qa`. These are author-declared hints, never exclusion rules. In particular,
  classifying a file as styles cannot exempt it from security or QA review.
- Freshness uses timezone-aware timestamps. `immutable` means the retained local
  bytes are a fixed source, not that external observations remain current.
  `until` requires an expiry after the checked time. Runtime dependencies require
  `until`; use it for any other externally changing context as well. Future or
  expired evidence blocks building. Expiry or future timestamps discovered later
  produce `unknown`. These timestamps are supplied evidence, not an authenticated
  observation of runtime state.

Limits are 128 dependencies, 128 emitted parts, 1 MiB per dependency, 4 MiB total
dependency bytes, 256 KiB manifest bytes, 4 KiB separator bytes, 5 MiB output bytes,
and 8 MiB provenance-record bytes. Repeated parts count toward output size.

## Records and verification

The record retains the original manifest and every declared dependency as base64
snapshots, the fixed assembler policy, hashes of the first-party assembler and
its helper sources, and the exact output path, SHA-256 and byte count. A canonical
record hash covers the full body. Treat these source snapshots with the same
confidentiality as their originals; keep engagement records private and out of
source control. Snapshots may contain source code, query text or other sensitive
content already present in the declared input files.

`verify` checks record structure and hashes, decodes bounded snapshots, verifies
each original dependency pin, reproduces the output without executing it, and
compares the reproduced bytes with the recorded output pin and live output file.
It also checks current builder sources, live manifest and input pins, and declared
freshness. A manually edited output, stale input, changed builder or unsupported
record cannot return `verified`.

`compare` reproduces both records from their retained snapshots. Historical input
paths may have changed since the previous build; the old snapshots preserve that
baseline. Both retained output files must still match their pins. Current live
inputs and manifest must match the current record. Both records must use the
current builder and have unexpired declared freshness. Keep old HTML outputs and
records instead of overwriting them.

Comparison reports changed dependency IDs and the union of their declared scope
hints, including query, asset or runtime changes that did not alter emitted HTML.
It separately reports recipe and output changes. Added or removed dependencies,
changed kind/scope mapping, unknown dependencies, stale sources or builders,
expired evidence, edited output, corrupt snapshots, missing records and unsupported
schemas yield `unknown`. All such cases retain the full review requirement.

## Authority and coverage limits

Every result retains all four `review_required_scopes` and explicitly reports:

- `review_scope_reduction_allowed: false`
- `authority_changed: false`
- `publication_authorized: false`
- `claims_authenticated: false`
- `dependency_coverage: declared_only`
- `external_state_verified: false`

Neither `verified` nor `unchanged` carries a review forward. Keep the existing
security, UI/UX, product-owner and QA rules, independence requirements, full-context
checks and native-observation requirements. An assembly record does not loosen
[review gates](stage-gates.md) or [dependency policy](dependency-policy.md).

The assembler cannot prove that a declared dependency inventory is semantically
complete, discover hidden network behavior, validate external permissions, or
qualify isolation or rendered quality. It detects inconsistent recorded bytes;
an actor able to rewrite all records and hashes can construct a different
self-consistent history. Durable trusted retention and host enforcement remain
separate responsibilities.
