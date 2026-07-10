# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Lightweight output events for efficient ASS generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, MutableMapping

from .convert import Convert

if TYPE_CHECKING:
    from .ass_core import Line


@dataclass(frozen=True, slots=True)
class Event:
    """A render-ready ASS event independent of extended line data.

    Unlike :class:`pyonfx.ass_core.Line`, an Event contains only fields needed
    for ASS serialization. It is suitable for effects that generate many
    output events and do not need to deep-copy words, syllables, or chars.
    """

    layer: int
    start_time: int
    end_time: int
    style: str
    text: str
    actor: str = ""
    margin_l: int = 0
    margin_r: int = 0
    margin_v: int = 0
    effect: str = ""
    comment: bool = False

    @classmethod
    def from_line(cls, line: Line, *, text: str | None = None) -> Event:
        """Create an Event from the serializable fields of a Line."""

        return cls(
            layer=line.layer,
            start_time=line.start_time,
            end_time=line.end_time,
            style=line.style,
            text=line.text if text is None else text,
            actor=line.actor,
            margin_l=line.margin_l,
            margin_r=line.margin_r,
            margin_v=line.margin_v,
            effect=line.effect,
            comment=line.comment,
        )

    def serialize(self, time_cache: MutableMapping[int, str] | None = None) -> str:
        """Serialize this event using the same field format as Line.serialize()."""

        start_ms = max(0, int(self.start_time))
        end_ms = max(0, int(self.end_time))
        start_text = _format_time(start_ms, time_cache)
        end_text = _format_time(end_ms, time_cache)
        return (
            f"{'Comment' if self.comment else 'Dialogue'}: {self.layer},"
            f"{start_text},{end_text},{self.style},{self.actor},"
            f"{self.margin_l:04d},{self.margin_r:04d},{self.margin_v:04d},"
            f"{self.effect},{self.text}\n"
        )


def _format_time(value: int, cache: MutableMapping[int, str] | None) -> str:
    if cache is None:
        return Convert.time(value)
    cached = cache.get(value)
    if cached is not None:
        return cached
    formatted = Convert.time(value)
    cache[value] = formatted
    return formatted
