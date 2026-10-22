# Testing and contribution checks

Run these commands from the repository root in the Python environment created during [setup](../README.md). Python 3.12 and Node.js 22 are used in CI. The native adapters and local MCP host require a POSIX system such as macOS or Linux.

```sh
python -m pip install -r requirements.txt
python scripts/check_package.py
python -m unittest discover -s tests -v
```

`check_package.py` checks declared skills, metadata, local documentation links and excluded repository artifacts. It is not a general secret scanner or an approval authenticator. The tests use synthetic fixtures and mock source/Omni transports. No customer credentials, live service connection or Omni CLI login is needed. Node.js is required for the App controller and template tests; without it, those cases skip explicitly.

The normal test run also skips optional integration cases that require separately obtained source engines. CI runs this self-contained configuration; a green job does not mean every optional producer was tested.

## Optional producer compatibility tests

Use an inspected, trusted checkout. These tests load upstream code and its maintained fixtures, so do not point the variables at customer projects or arbitrary downloaded repositories.

For the [Data Model Accelerator](https://github.com/exploreomni/Data-Model-Accelerator), use a Python environment with that checkout's required YAML and SQL dependencies:

```sh
OMNI_ANALYST_DMA_CHECKOUT=/absolute/trusted/Data-Model-Accelerator \
  python -m unittest discover -s tests -v
```

The declared DMA producer contract was exercised at `c513474e87af9c2c31deebd2ae675c8602955203`. Check compatibility before changing producer revisions. See [parser coverage](parser-coverage.md) for the distinct accepted formats.

Sigma compatibility needs its separately obtained engine environment and visual-capture extension, including `test_sigma_visual_capture.py`. The extension is not included in this repository or implied by the base revision alone. Importing supplied Sigma artifacts remains available without it.

```sh
OMNI_ANALYST_DMA_CHECKOUT=/absolute/trusted/Data-Model-Accelerator \
OMNI_ARTIFACT_SIGMA_CHECKOUT=/absolute/trusted/SigmaMigrationAgent \
OMNI_ARTIFACT_SIGMA_PYTHON=/absolute/trusted/SigmaMigrationAgent/.venv/bin/python \
  python -m unittest discover -s tests -v
```

Use the final test summary to distinguish passed, failed and skipped cases. The optional suites exercise actual producers behind synthetic transports; they do not establish live source completeness or tenant acceptance.

## Before proposing a change

1. Keep changes focused on the skill, helper or contract being changed. Preserve source IDs, original evidence and unresolved behavior.
2. Run the relevant tests, then the local suite and package checker. Run optional producer tests when changing a producer bridge and the trusted dependency is available.
3. Document changed setup or contract behavior in the maintained run guide. Use synthetic examples; keep customer evidence, credentials, generated engagements, internal plans and release archives outside this repository.
4. Describe what changed and the actual checks performed. Identify any skipped producer or native verification explicitly.

Local checks, candidate readback, native rendering/query behavior, effective access, business acceptance and publication are separate outcomes. A passing test suite does not authorize source execution or a target write.
