# Assemble selected sources without selecting a layout

Use [assemble_experience.py](../scripts/assemble_experience.py) when a local App combines separate authored markup, styles, scripts, data/configuration and assets. It assembles bytes; it does not design a screen, execute code, contact a service, supply an Omni SDK or publish anything. Existing native adapters and their credential/query/settings boundaries remain unchanged. Simple files do not need an assembly step, and native dashboards do not use this HTML helper.

Keep the shell and renderer owned by the engagement. Neither the assembler nor the [behavior controllers](experience-behaviors.md) decides navigation, chart type, page count, image roles, fonts or palette. Record those decisions in the selected design and brand contract. Reuse the existing query/runtime/intent records as pinned references rather than defining their semantics again.

## Input and output

The version 1 manifest has `schema_version: 1`, a `template` file pin, ordered `slots`, optional `references` and optional `max_output_bytes`. Every pin is `{path, sha256}` with a canonical project-relative path and SHA-256 of the exact file. Output is a new directory named explicitly by the caller, containing `index.html` and `assembly.json`. Existing directories are not overwritten. Place output outside the skill installation and repository.

Each slot contains `name`, `kind`, `path`, and `sha256`. The template uses `{{OAA:NAME}}` once for each declared slot. Placement is entirely chosen by the author. Supported kinds:

| Kind | Insertion and extra fields |
| --- | --- |
| `script` | Wraps source in a classic script. Set `script_type: "classic"`; optional `requires` names earlier script slots, and `provides` names declared global exports. Their order must match the template. |
| `style` | Wraps the selected CSS in a style element. No styles are supplied by the assembler. |
| `json` | Parses strict JSON, escapes HTML-sensitive characters, inserts a data script whose ID is the slot name. The consumer reads that ID explicitly. |
| `asset` | Inserts a PNG/JPEG/WebP data URL; declare the matching `mime`. Intended for an authored image attribute, not whole markup. Signature checks do not prove image decoding, identity, quality or rights. |

`references` contains `{role, path, sha256}` entries with distinct role labels. They are pinned in the receipt and not inserted. Use them for the actual query, input-shape, runtime or brand contracts the selected candidate depends on; role labels do not authenticate those records. Include the manifest, referenced files and built candidate in the existing intent/assignment dependency chain when needed. An assembly receipt is not automatically registered or a substitute for current-intent checks.

Classic scripts only are supported in this bounded helper. Module bundling, imports, remote dependency loading and runtime permission configuration remain separately selected tooling. `provides` checks declared collisions, not arbitrary JavaScript globals; source/controller review still needs to check the assembled runtime. Sources may contain authored script and network code and must be reviewed before opening or deploying. Assembly is not an HTML sanitizer or network-policy enforcement boundary.

Limits are 64 slots, 32 references, 2 MiB per input, 8 MiB total selected input, and at most 2 MiB output. Choose a smaller output budget where appropriate. These are helper bounds, not a promise about a native host's current limits. Symlink/traversal inputs, stale hashes, unknown slots, incompatible order, duplicate declared exports, HTML tokenizer delimiters in script/style fragments and oversized output fail before output creation. JSON data is not treated as executable source.

## Minimal local rehearsal

From a new engagement directory, the following creates an intentionally plain, synthetic harness and its manifest. The markup is illustrative; replace it with the selected composition. No native connection is implied.

```python
import hashlib, json
from pathlib import Path

files = {
    "view.html": '<!doctype html><html lang="en"><meta charset="utf-8"><title>Collection totals</title><main><h1>Collection totals</h1><output id="total"></output></main>{{OAA:DATA}}{{OAA:VIEW}}</html>',
    "fixture.json": '{"synthetic":true,"count":12}',
    "view.js": '(() => { const d = JSON.parse(document.getElementById("DATA").textContent); document.getElementById("total").textContent = `${d.count} supplied synthetic records`; })();',
}
for name, value in files.items():
    with Path(name).open("x") as output:
        output.write(value)
def pin(name):
    return {"path": name, "sha256": hashlib.sha256(Path(name).read_bytes()).hexdigest()}
manifest = {
    "schema_version": 1,
    "template": pin("view.html"),
    "slots": [
        {"name": "DATA", "kind": "json", **pin("fixture.json")},
        {"name": "VIEW", "kind": "script", "script_type": "classic", **pin("view.js")},
    ],
}
with Path("assembly.json").open("x") as output:
    json.dump(manifest, output, indent=2)
```

Run with the installed helper's absolute path or from its checkout:

```sh
python "$OAA_APP_SCRIPTS/assemble_experience.py" \
  --project "$OAA_RUN" --manifest assembly.json --output candidate-v1
```

To compose shared behavior, copy only selected helper files into the engagement, pin them, declare their public exports, and load them before the renderer that requires them. The [behavior studio](../assets/behavior-studio.html) demonstrates two presentations using the same controller. A new build consumes the chosen renderer; it does not impose the studio's composition.

## Binding and qualification

For a native candidate, replace a synthetic adapter through the [inspected native data contract](native-data-input.md). Keep exact keys, row grain, units, completeness, source time and pending/applied query scope explicit. Never infer a live bridge from the presence of a script slot or an adapter filename. Preserve query definitions and settings through the existing native authoring route.

Check the first assembled journey, current-result generation handling, selection/return, loading/error/partial outcomes and teardown. Source execution under a DOM double can find wiring errors; it does not prove rendering, actual keyboard focus, access, performance or native data delivery. Qualify the actual target when permitted, and retain any unobserved lanes. If a shared behavior needs different code for every layout, revisit the interface before adding more example screens.
