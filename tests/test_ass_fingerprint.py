from __future__ import annotations

from pathlib import Path

from benchmarks.ass_fingerprint import compare_fingerprints, fingerprint


ASS_HEADER = """[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _write(path: Path, dialogue: str, *, bom: bool = False, newline: str = "\n") -> None:
    content = (ASS_HEADER + dialogue).replace("\n", newline)
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(content, encoding=encoding, newline="")


def test_fingerprint_collects_ass_structure(tmp_path: Path) -> None:
    path = tmp_path / "中文 sample.ass"
    _write(
        path,
        "Dialogue: 2,0:00:01.00,0:00:02.00,Default,,0,0,0,,"
        r"{\p1\1c&HFFFFFF&}m 0 0 l 10 0 10 10" + "\n",
        bom=True,
        newline="\r\n",
    )

    result = fingerprint(path)

    assert result["utf8_bom"] is True
    assert result["line_endings"]["crlf"] > 0
    assert result["event_count"] == 1
    assert result["layers"] == {"2": 1}
    assert result["styles"] == {"Default": 1}
    assert result["tags"][r"\p"] == 1
    assert result["tags"][r"\Nc"] == 1
    assert result["drawing_event_count"] == 1
    assert result["drawing_scales"] == {"1": 1}


def test_compare_fingerprints_identifies_first_changed_event(tmp_path: Path) -> None:
    left_path = tmp_path / "left.ass"
    right_path = tmp_path / "right.ass"
    first = "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,first\n"
    second_left = "Dialogue: 1,0:00:01.00,0:00:02.00,Default,,0,0,0,,left\n"
    second_right = "Dialogue: 1,0:00:01.00,0:00:02.00,Default,,0,0,0,,right\n"
    _write(left_path, first + second_left)
    _write(right_path, first + second_right)

    comparison = compare_fingerprints(fingerprint(left_path), fingerprint(right_path))

    assert comparison["equal"] is False
    assert comparison["first_event_difference"] == 2
    assert "sha256" in comparison["field_differences"]
    assert "event_stream_sha256" in comparison["field_differences"]


def test_equal_content_ignores_source_path(tmp_path: Path) -> None:
    left_path = tmp_path / "a.ass"
    right_path = tmp_path / "b.ass"
    dialogue = "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,same\n"
    _write(left_path, dialogue)
    _write(right_path, dialogue)

    comparison = compare_fingerprints(fingerprint(left_path), fingerprint(right_path))

    assert comparison["equal"] is True
    assert comparison["first_event_difference"] is None
