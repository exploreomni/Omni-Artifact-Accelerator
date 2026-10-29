#!/usr/bin/env python3
"""Retain supplied Cognos report XML and its declared source context offline.

No connections, query execution, SDK imports, XML inclusion or schema downloads.
The destination must be new; metadata is evidence, never authorization.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def module(name):
    if name not in ("cognos_visual", "translate_artifact"):
        raise ValueError("cognos.module_rejected")
    path = Path(__file__).with_name(name + ".py")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("cognos.module_symlink")
    spec = importlib.util.spec_from_file_location("cognos_import_" + name,
        path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def prepare_report(source, metadata):
    translator = module("translate_artifact")
    meta = translator.decode(translator.read_input(metadata))
    translator.require(set(meta) == {"identity", "inventory", "reference"},
                       "cognos.import_metadata_fields")
    value = module("cognos_visual").import_report_xml(translator.read_input(source),
        meta["identity"], meta["inventory"], meta["reference"])
    # Ensure the envelope is readable by the shared bounded JSON transport.
    translator.decode(translator.encoded(value))
    return value


def import_report(source, metadata, output):
    value = prepare_report(source, metadata)
    module("translate_artifact").write_new(output, value)
    return {"status": "retained_supplied_report", "native_validation": "not_run",
            "source_execution": False, "network_calls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_report(args.source, args.metadata, args.output)))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError, OverflowError):
        print("Cognos import rejected: invalid evidence, unsafe path, limit or existing output. No source content printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
