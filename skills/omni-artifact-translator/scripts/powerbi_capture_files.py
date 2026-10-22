"""Passive bounded Power BI evidence files; no native execution or remote reads."""

from __future__ import annotations
import base64
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
import zipfile
import zlib

MAX_FILE = 8_000_000
MAX_JSON = 32_000_000
MAX_FILES = 512
MAX_TOTAL = 32_000_000


class CaptureError(ValueError):
    pass


def need(value, code):
    if not value:
        raise CaptureError(code)


def encoded(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def raw_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    return raw_sha(encoded(value))


def decode(raw):
    need(type(raw) is bytes and len(raw) <= MAX_JSON, "json_size_limit")

    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    try:
        result = json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                CaptureError("nonfinite_json")
            ),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CaptureError("invalid_json") from exc
    stack, count = [(result, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        need(count <= 200000 and depth <= 48, "json_structure_limit")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    return result


def safe_text(raw):
    need(len(raw) <= MAX_FILE and b"\x00" not in raw, "text_size_or_encoding")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise CaptureError("utf8_required") from exc
    need(
        not re.search(
            r"(?i)(?:Bearer\s+[A-Za-z0-9._~-]{12,}|(?:password|passwd|access_token|client_secret)\s*[=:]\s*[^\s,;\"}]+)",
            text,
        ),
        "credential_bearing_text",
    )
    return text


def secret_check(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            for key, val in item.items():
                normalized = re.sub("[^a-z]", "", key.lower())
                need(
                    not (
                        normalized
                        in {
                            "password",
                            "passwd",
                            "pwd",
                            "accesstoken",
                            "refreshtoken",
                            "clientsecret",
                            "authorization",
                            "credential",
                            "credentials",
                            "apikey",
                            "privatekey",
                        }
                        and val
                    ),
                    "credential_bearing_json",
                )
                stack.append(val)
        elif type(item) is list:
            stack.extend(item)


def source_path(name):
    need(type(name) is str and 0 < len(name) <= 1000, "source_path_rejected")
    path = PurePosixPath(name)
    need(
        not path.is_absolute()
        and str(path) == name
        and ".." not in path.parts
        and len(path.parts) <= 32
        and not any(c in name for c in ("\\", ":", "\x00"))
        and all(ord(c) >= 32 for c in name),
        "source_path_rejected",
    )
    return name


def validate_parts(parts):
    need(type(parts) is list and 1 <= len(parts) <= MAX_FILES, "definition_part_limit")
    seen, prefixes, result, total = set(), {}, [], 0
    for name, raw in parts:
        source_path(name)
        key = unicodedata.normalize("NFC", name).casefold()
        need(
            key not in seen
            and not any(
                key.startswith(p + "/") or p.startswith(key + "/") for p in seen
            ),
            "source_path_collision",
        )
        path_parts = PurePosixPath(name).parts
        for size in range(1, len(path_parts) + 1):
            prefix = "/".join(path_parts[:size])
            folded = unicodedata.normalize("NFC", prefix).casefold()
            need(
                folded not in prefixes or prefixes[folded] == prefix,
                "source_path_collision",
            )
            prefixes[folded] = prefix
        seen.add(key)
        total += len(raw)
        need(
            type(raw) is bytes and len(raw) <= MAX_FILE and total <= MAX_TOTAL,
            "definition_byte_limit",
        )
        suffix = PurePosixPath(name).suffix.lower()
        need(
            suffix not in (".pbix", ".pbit", ".abf", ".zip", ".exe", ".dll"),
            "opaque_model_or_archive_unsupported",
        )
        text = None
        if suffix in (
            ".json",
            ".pbip",
            ".pbir",
            ".pbism",
            ".bim",
            ".tmdl",
        ) or name.endswith(".platform"):
            text = safe_text(raw)
            if suffix != ".tmdl":
                secret_check(decode(raw))
        result.append({"source_path": name, "raw": raw, "content_utf8": text})
    report_roots = [
        p
        for p in result
        if p["source_path"] in ("report.json", "definition/report.json")
        or p["source_path"].endswith("/definition/report.json")
    ]
    need(len(report_roots) == 1, "exactly_one_report_definition_required")
    return sorted(result, key=lambda p: p["source_path"])


def fabric_parts(payload):
    need(
        type(payload) is dict and type(payload.get("definition")) is dict,
        "fabric_definition_required",
    )
    rows = payload["definition"].get("parts")
    need(type(rows) is list and 1 <= len(rows) <= MAX_FILES, "definition_part_limit")
    parts = []
    for row in rows:
        need(
            type(row) is dict
            and set(row) == {"path", "payload", "payloadType"}
            and row["payloadType"] == "InlineBase64"
            and type(row["payload"]) is str
            and len(row["payload"]) <= (MAX_FILE + 2) // 3 * 4,
            "fabric_part_unsupported",
        )
        try:
            raw = base64.b64decode(row["payload"], validate=True)
        except (ValueError, TypeError) as exc:
            raise CaptureError("invalid_definition_base64") from exc
        parts.append((row["path"], raw))
    return validate_parts(parts)


def no_links(path):
    path = Path(path).absolute()
    need(".." not in path.parts, "parent_path_rejected")
    for item in (path, *path.parents):
        need(not item.is_symlink(), "symlink_path_rejected")
    return path


def read_file(path, maximum=MAX_FILE):
    path = no_links(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        need(
            stat.S_ISREG(before.st_mode) and before.st_size <= maximum,
            "file_size_or_type",
        )
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    need(
        len(raw) == before.st_size <= maximum
        and before.st_mtime_ns == after.st_mtime_ns,
        "file_changed",
    )
    return raw


def local_parts(root):
    root = no_links(root)
    need(root.is_dir(), "definition_directory_required")
    parts, total = [], 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        need(
            all(not (Path(directory) / d).is_symlink() for d in dirs),
            "source_symlink_rejected",
        )
        for name in sorted(files):
            path = Path(directory) / name
            raw = read_file(path)
            total += len(raw)
            need(
                len(parts) < MAX_FILES and total <= MAX_TOTAL,
                "definition_inventory_limit",
            )
            parts.append((path.relative_to(root).as_posix(), raw))
    return validate_parts(parts)


def private_directory(path):
    path = no_links(path)
    if not path.exists():
        path.mkdir(mode=0o700, parents=True)
    need(
        path.is_dir()
        and path.stat().st_uid == os.getuid()
        and path.stat().st_mode & 0o077 == 0,
        "private_owner_directory_required",
    )
    return path


def write_once(root, name, raw):
    need(
        type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}", name),
        "private_filename_rejected",
    )
    need(len(raw) <= MAX_JSON, "private_file_size_limit")
    target = no_links(root / name)
    need(not target.exists(), "evidence_already_exists")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target, follow_symlinks=False)
        fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": name, "sha256": raw_sha(raw), "bytes": len(raw)}


def read_pin(root, pin):
    need(
        type(pin) is dict
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,150}", pin.get("path", "")),
        "attachment_path_rejected",
    )
    raw = read_file(root / pin["path"], MAX_JSON)
    need(
        len(raw) == pin.get("bytes") and raw_sha(raw) == pin.get("sha256"),
        "evidence_bytes_changed",
    )
    return raw


def png_info(raw):
    need(
        0 < len(raw) <= MAX_FILE and raw.startswith(b"\x89PNG\r\n\x1a\n"),
        "png_signature_or_size",
    )
    offset, width, height, channels, ended = 8, None, None, None, False
    compressed = bytearray()
    while offset + 12 <= len(raw):
        size = struct.unpack(">I", raw[offset : offset + 4])[0]
        end = offset + size + 12
        need(end <= len(raw), "png_truncated_chunk")
        kind, data = raw[offset + 4 : offset + 8], raw[offset + 8 : end - 4]
        need(
            zlib.crc32(kind + data) & 0xFFFFFFFF
            == struct.unpack(">I", raw[end - 4 : end])[0],
            "png_crc",
        )
        if width is None:
            need(kind == b"IHDR" and size == 13, "png_header")
            width, height, depth, color, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", data)
            )
            channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color)
            need(
                depth == 8 and channels and compression == filtering == interlace == 0,
                "png_encoding_unsupported",
            )
            need(
                0 < width <= 8192
                and 0 < height <= 8192
                and width * height <= 16_000_000,
                "png_dimension_limit",
            )
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            need(size == 0 and end == len(raw), "png_end")
            ended = True
            break
        else:
            need(
                kind in (b"sRGB", b"gAMA", b"cHRM", b"pHYs", b"bKGD", b"sBIT"),
                "png_chunk_unsupported",
            )
        offset = end
    need(ended and compressed, "png_missing_data")
    expected = height * (1 + width * channels)
    need(expected <= 64_000_000, "png_decoded_limit")
    try:
        inflater = zlib.decompressobj()
        pixels = inflater.decompress(bytes(compressed), expected + 1)
        need(
            len(pixels) == expected
            and inflater.eof
            and not inflater.unused_data
            and not inflater.unconsumed_tail,
            "png_decoded_size",
        )
    except zlib.error as exc:
        raise CaptureError("png_invalid_compression") from exc
    need(
        all(pixels[i] <= 4 for i in range(0, len(pixels), 1 + width * channels)),
        "png_invalid_filter",
    )
    return {"width": width, "height": height}


def image_parts(raw):
    """Inspect PNG or PNG-only ZIP in memory; never extract or execute members."""
    if raw.startswith(b"\x89PNG"):
        return [("image.png", raw, png_info(raw))]
    need(len(raw) <= MAX_FILE and raw.startswith(b"PK"), "png_or_zip_required")
    result, seen, total = [], set(), 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            need(1 <= len(archive.infolist()) <= 100, "zip_member_limit")
            for entry in archive.infolist():
                name = source_path(entry.filename)
                key = unicodedata.normalize("NFC", name).casefold()
                need(key not in seen, "zip_collision")
                seen.add(key)
                mode = entry.external_attr >> 16
                need(
                    not stat.S_ISLNK(mode)
                    and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                    and not entry.flag_bits & 1
                    and entry.compress_type
                    in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    "zip_member_rejected",
                )
                need(
                    name.lower().endswith(".png")
                    and entry.file_size <= MAX_FILE
                    and entry.file_size <= max(entry.compress_size, 1) * 100,
                    "zip_expansion_or_type",
                )
                total += entry.file_size
                need(total <= MAX_TOTAL, "zip_total_limit")
                with archive.open(entry) as stream:
                    data = stream.read(MAX_FILE + 1)
                need(len(data) == entry.file_size, "zip_truncated_member")
                result.append((name, data, png_info(data)))
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise CaptureError("invalid_zip") from exc
    return result
