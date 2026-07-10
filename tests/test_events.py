from __future__ import annotations

from pathlib import Path

import pytest

from pyonfx import Ass, Convert, Event


FIXTURE = Path(__file__).resolve().parent / "Ass" / "ass_core.ass"


def _io(tmp_path: Path) -> Ass:
    return Ass(str(FIXTURE), str(tmp_path / "output.ass"), extended=True)


def test_event_from_line_serializes_identically(tmp_path: Path) -> None:
    io = _io(tmp_path)
    line = io.lines[11].copy()
    line.text = r"{\pos(100,200)}event text"

    event = Event.from_line(line)

    assert event.serialize() == line.serialize()


def test_write_events_matches_write_line_output(tmp_path: Path) -> None:
    line_io = _io(tmp_path)
    event_io = _io(tmp_path)
    lines = []
    events = []
    for index in range(20):
        line = line_io.lines[11].copy()
        line.layer = index % 3
        line.start_time = 1000 + (index % 4) * 100
        line.end_time = 2000 + (index % 4) * 100
        line.text = rf"{{\pos({index},{index + 1})}}text"
        lines.append(line)
        events.append(Event.from_line(line))

    for line in lines:
        line_io.write_line(line)
    event_io.write_events(events)

    assert event_io._output == line_io._output
    assert event_io._plines == line_io._plines == 20


def test_write_event_accepts_one_event(tmp_path: Path) -> None:
    io = _io(tmp_path)
    before = len(io._output)
    event = Event(
        layer=2,
        start_time=-100,
        end_time=500,
        style="Default",
        text="hello",
        comment=True,
    )

    io.write_event(event)

    assert len(io._output) == before + 1
    assert io._output[-1].startswith("Comment: 2,0:00:00.00,0:00:00.50,Default,")


def test_write_events_reports_invalid_index(tmp_path: Path) -> None:
    io = _io(tmp_path)
    valid = Event(0, 0, 100, "Default", "valid")

    with pytest.raises(TypeError, match=r"events\[1\]"):
        io.write_events([valid, object()])  # type: ignore[list-item]


def test_batch_writer_reuses_time_strings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    io = _io(tmp_path)
    original = Convert.time
    calls = 0

    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(Convert, "time", staticmethod(counted))
    events = [Event(0, 1000, 2000, "Default", str(index)) for index in range(50)]

    io.write_events(events)

    assert calls == 2
