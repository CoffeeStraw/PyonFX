# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

from pathlib import Path

import pytest

from pyonfx import Ass, Event

FIXTURE = Path(__file__).resolve().parent / "Ass" / "ass_core.ass"


def _events(count: int):
    for index in range(count):
        yield Event(
            layer=index % 4,
            start_time=1000 + (index % 10) * 100,
            end_time=2000 + (index % 10) * 100,
            style="Default",
            text=f"event-{index}",
        )


def test_save_events_matches_buffered_save(tmp_path: Path) -> None:
    buffered_path = tmp_path / "buffered.ass"
    streamed_path = tmp_path / "streamed.ass"
    buffered = Ass(
        str(FIXTURE), str(buffered_path), keep_original=False, extended=False
    )
    streamed = Ass(
        str(FIXTURE), str(streamed_path), keep_original=False, extended=False
    )

    buffered.write_events(_events(250))
    buffered.save(quiet=True)
    streamed.save_events(_events(250), batch_size=17, quiet=True)

    assert streamed_path.read_bytes() == buffered_path.read_bytes()
    assert streamed._plines == buffered._plines == 250
    assert streamed._saved is True


def test_save_events_accepts_generator_once(tmp_path: Path) -> None:
    output_path = tmp_path / "streamed.ass"
    io = Ass(str(FIXTURE), str(output_path), keep_original=False, extended=False)
    consumed = 0

    def generated():
        nonlocal consumed
        for event in _events(10):
            consumed += 1
            yield event

    io.save_events(generated(), batch_size=3, quiet=True)

    assert consumed == 10
    assert output_path.read_text(encoding="utf-8-sig").count("Dialogue:") == 10


def test_save_events_rejects_invalid_batch_size(tmp_path: Path) -> None:
    io = Ass(str(FIXTURE), str(tmp_path / "output.ass"), extended=False)
    with pytest.raises(ValueError, match="at least 1"):
        io.save_events([], batch_size=0, quiet=True)
