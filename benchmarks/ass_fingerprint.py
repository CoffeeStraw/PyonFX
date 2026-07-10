"""Create and compare structural fingerprints for ASS output files."""

# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

# Capture the ASS tag name without consuming its numeric argument. Channel
# prefixes such as ``\1c`` remain part of the name and are normalized below.
TAG_RE = re.compile(r"\\(?:[1-4][ac]|[A-Za-z]+)")
DRAWING_RE = re.compile(r"\\p([1-9][0-9]*)")


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _line_ending_counts(data: bytes) -> dict[str, int]:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    return {"crlf": crlf, "lf": lf, "cr": cr}


def _parse_event(raw: str) -> dict[str, Any] | None:
    if not raw.startswith(("Dialogue:", "Comment:")):
        return None
    event_type, payload = raw.split(":", 1)
    fields = payload.lstrip().split(",", 9)
    if len(fields) != 10:
        return {
            "type": event_type,
            "malformed": True,
            "raw_sha256": _sha256_bytes(raw.encode("utf-8")),
        }
    layer, start, end, style, actor, margin_l, margin_r, margin_v, effect, text = fields
    tags = [_normalize_tag(tag) for tag in TAG_RE.findall(text)]
    drawing_scales = [int(value) for value in DRAWING_RE.findall(text)]
    return {
        "type": event_type,
        "malformed": False,
        "layer": layer.strip(),
        "start": start.strip(),
        "end": end.strip(),
        "style": style,
        "actor": actor,
        "margins": [margin_l, margin_r, margin_v],
        "effect": effect,
        "text_sha256": _sha256_bytes(text.encode("utf-8")),
        "text_length": len(text),
        "tags": tags,
        "drawing_scales": drawing_scales,
        "raw_sha256": _sha256_bytes(raw.encode("utf-8")),
    }


def _normalize_tag(tag: str) -> str:
    if re.fullmatch(r"\\p\d+", tag):
        return r"\p"
    if re.fullmatch(r"\\[1234]a", tag):
        return r"\Na"
    if re.fullmatch(r"\\[1234]c", tag):
        return r"\Nc"
    return tag


def fingerprint(
    path: str | Path, *, include_line_hashes: bool = True
) -> dict[str, Any]:
    """Return a deterministic structural fingerprint for an ASS file."""

    file_path = Path(path).resolve()
    data = file_path.read_bytes()
    has_bom = data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    lines = text.splitlines()

    events: list[dict[str, Any]] = []
    event_types: Counter[str] = Counter()
    layers: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    malformed = 0
    drawing_events = 0
    drawing_scales: Counter[int] = Counter()
    start_values: list[str] = []
    end_values: list[str] = []

    for raw in lines:
        event = _parse_event(raw)
        if event is None:
            continue
        events.append(event)
        event_types[event["type"]] += 1
        if event["malformed"]:
            malformed += 1
            continue
        layers[event["layer"]] += 1
        styles[event["style"]] += 1
        tags.update(event["tags"])
        if event["drawing_scales"]:
            drawing_events += 1
            drawing_scales.update(event["drawing_scales"])
        start_values.append(event["start"])
        end_values.append(event["end"])

    result: dict[str, Any] = {
        "schema_version": 1,
        "path": str(file_path),
        "bytes": len(data),
        "sha256": _sha256_bytes(data),
        "utf8_bom": has_bom,
        "line_endings": _line_ending_counts(data),
        "line_count": len(lines),
        "event_count": len(events),
        "event_types": dict(sorted(event_types.items())),
        "malformed_event_count": malformed,
        "layers": dict(
            sorted(layers.items(), key=lambda item: _numeric_sort_key(item[0]))
        ),
        "styles": dict(sorted(styles.items())),
        "tags": dict(sorted(tags.items())),
        "drawing_event_count": drawing_events,
        "drawing_scales": {
            str(key): value for key, value in sorted(drawing_scales.items())
        },
        "time_text_range": {
            "first_start": min(start_values) if start_values else None,
            "last_end": max(end_values) if end_values else None,
        },
        "event_stream_sha256": _sha256_bytes(
            "\n".join(event["raw_sha256"] for event in events).encode("ascii")
        ),
    }
    if include_line_hashes:
        result["event_line_hashes"] = [event["raw_sha256"] for event in events]
    return result


def _numeric_sort_key(value: str) -> tuple[int, int | str]:
    try:
        return 0, int(value)
    except ValueError:
        return 1, value


def compare_fingerprints(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two fingerprints and identify summary and line-level differences."""

    ignored = {"path", "event_line_hashes"}
    keys = sorted((set(left) | set(right)) - ignored)
    field_differences = {
        key: {"left": left.get(key), "right": right.get(key)}
        for key in keys
        if left.get(key) != right.get(key)
    }

    left_hashes = left.get("event_line_hashes", [])
    right_hashes = right.get("event_line_hashes", [])
    first_event_difference: int | None = None
    for index in range(max(len(left_hashes), len(right_hashes))):
        left_value = left_hashes[index] if index < len(left_hashes) else None
        right_value = right_hashes[index] if index < len(right_hashes) else None
        if left_value != right_value:
            first_event_difference = index + 1
            break

    return {
        "equal": not field_differences and first_event_difference is None,
        "field_differences": field_differences,
        "first_event_difference": first_event_difference,
        "left_event_count": len(left_hashes),
        "right_event_count": len(right_hashes),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-line-hashes", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    left = fingerprint(args.left, include_line_hashes=not args.no_line_hashes)
    if args.right is None:
        result: dict[str, Any] = left
    else:
        right = fingerprint(args.right, include_line_hashes=not args.no_line_hashes)
        result = {
            "left": left,
            "right": right,
            "comparison": compare_fingerprints(left, right),
        }

    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(serialized)
    else:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8", newline="\n")
        json.loads(output_path.read_text(encoding="utf-8-sig"))
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
