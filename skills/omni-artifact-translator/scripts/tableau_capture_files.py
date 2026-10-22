"""Passive, bounded file validation for Tableau source evidence. No external IO."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import zlib

MAX_FILE = 8_000_000
MAX_XML = 2_000_000
MAX_JSON = 12_000_000


class CaptureError(ValueError):
    """A fixed source boundary failed; messages contain no response content."""


def need(test, code):
    if not test:
        raise CaptureError(code)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def raw_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    need(len(raw) <= MAX_JSON, "json_size_limit")
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(CaptureError("nonfinite_json")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CaptureError("invalid_json") from exc


def secret_name(value):
    name = re.sub(r"[^a-z0-9]", "", value.split("}")[-1].lower())
    return name in {"pwd", "pass", "token"} or any(part in name for part in (
        "password", "passwd", "credential", "secret", "accesstoken", "refreshtoken",
        "authtoken", "oauthtoken", "sessiontoken", "authorization", "apikey", "privatekey"))


def safe_xml(raw, workbook=False):
    need(0 < len(raw) <= MAX_XML and b"\x00" not in raw, "xml_size_or_encoding")
    need(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "xml_entity_forbidden")
    try:
        text = raw.decode("utf-8")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError) as exc:
        raise CaptureError("invalid_utf8_xml") from exc
    need(not workbook or root.tag == "workbook", "workbook_root_required")
    count = 0
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        count += 1
        need(count <= 5000 and depth <= 32, "xml_structure_limit")
        need(not any(secret_name(k) and v.strip() for k, v in node.attrib.items()), "credential_bearing_xml")
        need(not (secret_name(node.tag) and (any(v.strip() for v in node.itertext()) or any(node.attrib.values()))), "credential_bearing_xml")
        if node.tag.split("}")[-1].lower() in {"property", "connection-property", "entry", "attribute", "option", "parameter"}:
            selectors = {"name", "key", "property", "id"}
            if any(k in selectors and secret_name(v) for k, v in node.attrib.items()):
                need(not any(k not in selectors and v.strip() for k, v in node.attrib.items())
                     and not any(v.strip() for v in node.itertext()), "credential_bearing_xml")
        stack.extend((child, depth + 1) for child in node)
    return root


def definition(raw):
    """Return bounded TWB authority; inspect ZIP members in memory, never extract."""
    need(0 < len(raw) <= MAX_FILE, "definition_size_limit")
    if not raw.startswith(b"PK"):
        safe_xml(raw, workbook=True)
        return {"format": "twb", "xml": raw, "members": [], "fingerprint": raw_sha(raw)}
    members, workbook = [], []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            need(len(archive.infolist()) <= 50, "zip_member_limit")
            seen, total = set(), 0
            for entry in archive.infolist():
                name = entry.filename
                parts = PurePosixPath(name).parts
                need(name and not any(x in name for x in ("\\", ":", "\x00")) and not name.startswith("/")
                     and ".." not in parts and "." not in name.split("/"), "zip_path_rejected")
                key = unicodedata.normalize("NFC", name.rstrip("/")).casefold()
                need(key not in seen, "zip_colliding_member")
                seen.add(key)
                mode = entry.external_attr >> 16
                need(not stat.S_ISLNK(mode) and stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), "zip_special_member")
                need(not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "zip_encoding_rejected")
                if entry.is_dir():
                    continue
                suffix = PurePosixPath(name).suffix.lower()
                need(suffix not in (".hyper", ".tde", ".tfl", ".tflx"), "extract_or_prep_forbidden")
                need(entry.file_size <= MAX_XML and entry.file_size <= max(entry.compress_size, 1) * 100, "zip_expansion_limit")
                total += entry.file_size
                need(total <= MAX_FILE, "zip_total_expansion_limit")
                with archive.open(entry) as stream:
                    data = stream.read(MAX_XML + 1)
                need(len(data) == entry.file_size, "zip_truncated_member")
                if suffix in (".twb", ".tds"):
                    safe_xml(data, workbook=suffix == ".twb")
                if suffix == ".twb":
                    workbook.append(data)
                members.append({"path": name, "bytes": len(data), "sha256": raw_sha(data)})
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise CaptureError("invalid_zip") from exc
    need(len(workbook) == 1, "exactly_one_twb_required")
    return {"format": "twbx", "xml": workbook[0], "members": members,
            "fingerprint": sha(sorted(members, key=lambda x: x["path"]))}


def csv_info(raw):
    need(0 < len(raw) <= MAX_FILE and b"\x00" not in raw, "csv_size_or_encoding")
    try:
        text = raw.decode("utf-8-sig")
        need(not text.lstrip().lower().startswith(("<!doctype", "<html", "<?xml", "<tsresponse")), "csv_error_body")
        rows = []
        for row in csv.reader(io.StringIO(text, newline=""), strict=True):
            need(len(rows) < 50001, "csv_row_limit")
            rows.append(row)
    except (UnicodeError, csv.Error) as exc:
        raise CaptureError("invalid_csv") from exc
    need(rows and rows[0] and len(rows[0]) <= 1000 and len(rows) <= 50001, "csv_structure_limit")
    width = len(rows[0])
    need(all(len(row) == width and all(len(cell) <= 65536 for cell in row) for row in rows), "csv_ragged_or_oversize")
    return {"columns": rows[0], "observed_rows": len(rows) - 1,
            "duplicate_columns": len(set(rows[0])) != width, "row_completeness": "not_established"}


def png_info(raw):
    need(0 < len(raw) <= MAX_FILE and raw.startswith(b"\x89PNG\r\n\x1a\n"), "png_signature_or_size")
    offset, width, height, channels, seen_end = 8, None, None, None, False
    compressed = bytearray()
    while offset + 12 <= len(raw):
        size = struct.unpack(">I", raw[offset:offset + 4])[0]
        end = offset + size + 12
        need(end <= len(raw), "png_truncated_chunk")
        kind, data = raw[offset + 4:offset + 8], raw[offset + 8:end - 4]
        need(zlib.crc32(kind + data) & 0xffffffff == struct.unpack(">I", raw[end - 4:end])[0], "png_crc")
        if width is None:
            need(kind == b"IHDR" and size == 13, "png_header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
            channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color)
            need(depth == 8 and channels and compression == filtering == interlace == 0, "png_encoding_unsupported")
            need(0 < width <= 8192 and 0 < height <= 8192 and width * height <= 16_000_000, "png_dimension_limit")
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            need(size == 0 and end == len(raw), "png_end")
            seen_end = True
            break
        else:
            need(kind in (b"sRGB", b"gAMA", b"cHRM", b"pHYs", b"bKGD", b"sBIT"), "png_chunk_unsupported")
        offset = end
    need(seen_end and compressed, "png_missing_data")
    expected = height * (1 + width * channels)
    need(expected <= 64_000_000, "png_decoded_limit")
    try:
        inflater = zlib.decompressobj()
        pixels = inflater.decompress(bytes(compressed), expected + 1)
        need(len(pixels) == expected and inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail, "png_decoded_size")
    except zlib.error as exc:
        raise CaptureError("png_invalid_compression") from exc
    stride = 1 + width * channels
    need(all(pixels[i] <= 4 for i in range(0, len(pixels), stride)), "png_invalid_filter")
    return {"width": width, "height": height}


def no_links(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        need(not item.is_symlink(), "symlink_path_rejected")
    return path


def private_directory(path):
    path = no_links(path)
    if not path.exists():
        path.mkdir(mode=0o700, parents=True)
    need(path.is_dir() and path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o077 == 0,
         "private_owner_directory_required")
    return path


def write_once(root, name, raw):
    need(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}", name), "private_filename_rejected")
    need(len(raw) <= MAX_JSON, "private_file_size_limit")
    path = no_links(root / name)
    need(not path.exists(), "evidence_already_exists")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": name, "sha256": raw_sha(raw), "bytes": len(raw)}


def read_pin(root, pin):
    name = pin["path"]
    need(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}", name), "private_filename_rejected")
    path = no_links(root / name)
    need(path.is_file() and path.stat().st_size <= MAX_JSON, "pinned_file_missing_or_large")
    raw = path.read_bytes()
    need(len(raw) == pin["bytes"] and raw_sha(raw) == pin["sha256"], "pinned_file_changed")
    return raw
