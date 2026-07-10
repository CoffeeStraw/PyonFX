from __future__ import annotations

from pathlib import Path

import pytest

from pyonfx import Ass


FIXTURE = Path(__file__).resolve().parent / "Ass" / "ass_core.ass"


def _selective(tmp_path: Path, feature: str) -> Ass:
    return Ass(
        str(FIXTURE),
        str(tmp_path / f"{feature}.ass"),
        extended=True,
        extended_features={feature},
    )


def test_line_feature_builds_only_line_metrics(tmp_path: Path) -> None:
    io = _selective(tmp_path, "line")
    line = io.lines[11]
    assert line.width > 0
    assert line.height > 0
    assert line.words == []
    assert line.syls == []
    assert line.chars == []


def test_words_feature_builds_line_and_words(tmp_path: Path) -> None:
    io = _selective(tmp_path, "words")
    line = io.lines[11]
    assert line.width > 0
    assert line.words
    assert line.syls == []
    assert line.chars == []


def test_syllables_feature_builds_dependency_chain_without_chars(tmp_path: Path) -> None:
    io = _selective(tmp_path, "syllables")
    line = io.lines[11]
    assert line.words
    assert len(line.syls) == 27
    assert line.chars == []


def test_chars_feature_matches_full_extended(tmp_path: Path) -> None:
    full = Ass(str(FIXTURE), str(tmp_path / "full.ass"), extended=True)
    selective = _selective(tmp_path, "chars")
    full_line = full.lines[11]
    selective_line = selective.lines[11]
    assert len(selective_line.words) == len(full_line.words)
    assert len(selective_line.syls) == len(full_line.syls)
    assert len(selective_line.chars) == len(full_line.chars)
    assert selective_line.width == full_line.width
    assert selective_line.height == full_line.height
    assert [char.text for char in selective_line.chars] == [
        char.text for char in full_line.chars
    ]


def test_unknown_feature_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown extended features"):
        Ass(
            str(FIXTURE),
            str(tmp_path / "unknown.ass"),
            extended_features={"unknown"},
        )


def test_vertical_kanji_requires_chars(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires the chars"):
        Ass(
            str(FIXTURE),
            str(tmp_path / "vertical.ass"),
            vertical_kanji=True,
            extended_features={"line"},
        )


def test_extended_features_requires_extended_true(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires extended=True"):
        Ass(
            str(FIXTURE),
            str(tmp_path / "disabled.ass"),
            extended=False,
            extended_features={"line"},
        )


def test_empty_feature_set_only_parses_base_ass(tmp_path: Path) -> None:
    io = Ass(
        str(FIXTURE),
        str(tmp_path / "empty.ass"),
        extended=True,
        extended_features=set(),
    )
    line = io.lines[11]
    assert line.width != line.width  # NaN from base parsing
    assert line.words == []
    assert line.syls == []
    assert line.chars == []
