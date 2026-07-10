"""Explicit timing helpers for line- and syllable-relative effects."""

from __future__ import annotations


def retime_syllable(
    line_start: int,
    syllable_start: int,
    syllable_end: int,
    start_offset: int = 0,
    end_offset: int = 0,
) -> tuple[int, int]:
    """Return absolute times based on a syllable's start and end."""

    start = line_start + syllable_start + start_offset
    end = line_start + syllable_end + end_offset
    return max(0, start), max(0, end)


def retime_start_to_syllable(
    line_start: int,
    syllable_start: int,
    start_offset: int = 0,
    end_offset: int = 0,
) -> tuple[int, int]:
    """Return absolute times with both boundaries relative to syllable start."""

    start = line_start + syllable_start + start_offset
    end = line_start + syllable_start + end_offset
    return max(0, start), max(0, end)


def retime_line(
    line_start: int,
    line_end: int,
    start_offset: int = 0,
    end_offset: int = 0,
) -> tuple[int, int]:
    """Return absolute times based on a line's start and end.

    The result is clamped to non-negative values. If offsets would place the
    end before the start, the end is clamped to the start.
    """

    start = max(0, line_start + start_offset)
    end = max(0, line_end + end_offset)
    return start, max(start, end)
