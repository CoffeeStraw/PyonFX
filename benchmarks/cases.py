"""Benchmark case definitions used by :mod:`benchmarks.run_baseline`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pyonfx import Ass, Convert, Event, Shape


ROOT = Path(__file__).resolve().parents[1]
ASS_FIXTURE = ROOT / "tests" / "Ass" / "ass_core.ass"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """A named operation with tier-specific iteration counts."""

    name: str
    description: str
    operation: Callable[[], object]
    iterations: dict[str, int]


def _discard(value: object) -> None:
    """Keep benchmark call sites explicit without retaining results."""

    del value


def build_cases() -> list[BenchmarkCase]:
    """Create benchmark cases with reusable, immutable setup data."""

    if not ASS_FIXTURE.exists():
        raise FileNotFoundError(f"missing benchmark fixture: {ASS_FIXTURE}")

    output_path = ROOT / "benchmarks" / "_unused_output.ass"
    extended_io = Ass(str(ASS_FIXTURE), str(output_path), extended=True)
    _, _, extended_lines = extended_io.get_data()
    target_line = extended_lines[11]
    target_syllable = target_line.syls[0]
    cached_shape = Convert.text_to_shape(target_syllable)
    drawing = cached_shape.drawing_cmds
    mixed_drawings = [
        Convert.text_to_shape(syllable).drawing_cmds
        for syllable in target_line.syls
        if syllable.text
    ]
    mixed_drawing_index = 0
    time_values = tuple(range(0, 120_000, 137))
    time_index = 0
    batch_size = 100
    batch_io = Ass(str(ASS_FIXTURE), str(output_path), extended=False)
    batch_output_start = len(batch_io._output)

    def parse_basic() -> object:
        return Ass(str(ASS_FIXTURE), str(output_path), extended=False)

    def parse_extended() -> object:
        return Ass(str(ASS_FIXTURE), str(output_path), extended=True)

    def parse_extended_features(features: frozenset[str]) -> Ass:
        return Ass(
            str(ASS_FIXTURE),
            str(output_path),
            extended=True,
            extended_features=features,
        )

    def parse_extended_line() -> object:
        return parse_extended_features(frozenset({"line"}))

    def parse_extended_words() -> object:
        return parse_extended_features(frozenset({"words"}))

    def parse_extended_syllables() -> object:
        return parse_extended_features(frozenset({"syllables"}))

    def deepcopy_line() -> object:
        return target_line.copy()

    def serialize_line() -> object:
        return target_line.serialize()

    def text_to_shape() -> object:
        return Convert.text_to_shape(target_syllable)

    def drawing_to_multipolygon() -> object:
        return Shape(drawing).to_multipolygon()

    def drawing_to_multipolygon_cold() -> object:
        Shape._cached_multipolygon.cache_clear()
        return Shape(drawing).to_multipolygon()

    def drawing_to_multipolygon_mixed() -> object:
        nonlocal mixed_drawing_index
        mixed_drawing = mixed_drawings[mixed_drawing_index]
        mixed_drawing_index = (mixed_drawing_index + 1) % len(mixed_drawings)
        return Shape(mixed_drawing).to_multipolygon()

    def convert_time() -> object:
        nonlocal time_index
        value = time_values[time_index]
        time_index = (time_index + 1) % len(time_values)
        return Convert.time(value)

    def generate_line_batch() -> object:
        for index in range(batch_size):
            line = target_line.copy()
            line.layer = index % 4
            line.start_time = 1000 + (index % 10) * 100
            line.end_time = 2000 + (index % 10) * 100
            line.text = f"event-{index}"
            batch_io.write_line(line)
        result = batch_io._output[batch_output_start:]
        del batch_io._output[batch_output_start:]
        batch_io._plines -= batch_size
        return result

    def generate_event_batch() -> object:
        events = [
            Event(
                layer=index % 4,
                start_time=1000 + (index % 10) * 100,
                end_time=2000 + (index % 10) * 100,
                style=target_line.style,
                text=f"event-{index}",
                actor=target_line.actor,
                margin_l=target_line.margin_l,
                margin_r=target_line.margin_r,
                margin_v=target_line.margin_v,
                effect=target_line.effect,
                comment=target_line.comment,
            )
            for index in range(batch_size)
        ]
        batch_io.write_events(events)
        result = batch_io._output[batch_output_start:]
        del batch_io._output[batch_output_start:]
        batch_io._plines -= batch_size
        return result

    return [
        BenchmarkCase(
            name="ass_parse_basic",
            description="Parse the ASS fixture without extended line data.",
            operation=parse_basic,
            iterations={"S": 1, "M": 5, "L": 20},
        ),
        BenchmarkCase(
            name="ass_parse_extended",
            description="Parse the ASS fixture and build line/word/syllable/char data.",
            operation=parse_extended,
            iterations={"S": 1, "M": 3, "L": 10},
        ),
        BenchmarkCase(
            name="ass_parse_extended_line",
            description="Parse the ASS fixture and build line metrics only.",
            operation=parse_extended_line,
            iterations={"S": 1, "M": 5, "L": 20},
        ),
        BenchmarkCase(
            name="ass_parse_extended_words",
            description="Parse the ASS fixture and build line plus word data.",
            operation=parse_extended_words,
            iterations={"S": 1, "M": 5, "L": 20},
        ),
        BenchmarkCase(
            name="ass_parse_extended_syllables",
            description="Parse the ASS fixture and build line, word, and syllable data.",
            operation=parse_extended_syllables,
            iterations={"S": 1, "M": 5, "L": 20},
        ),
        BenchmarkCase(
            name="line_deepcopy",
            description="Deep-copy a fully extended karaoke Line.",
            operation=deepcopy_line,
            iterations={"S": 10, "M": 100, "L": 1_000},
        ),
        BenchmarkCase(
            name="line_serialize",
            description="Serialize a fully extended karaoke Line to ASS text.",
            operation=serialize_line,
            iterations={"S": 100, "M": 1_000, "L": 10_000},
        ),
        BenchmarkCase(
            name="text_to_shape",
            description="Convert one syllable to a font outline Shape.",
            operation=text_to_shape,
            iterations={"S": 5, "M": 50, "L": 500},
        ),
        BenchmarkCase(
            name="drawing_to_multipolygon",
            description="Parse a glyph drawing and polygonize it with Shapely.",
            operation=drawing_to_multipolygon,
            iterations={"S": 5, "M": 50, "L": 500},
        ),
        BenchmarkCase(
            name="drawing_to_multipolygon_cold",
            description="Polygonize one drawing after clearing the bounded cache.",
            operation=drawing_to_multipolygon_cold,
            iterations={"S": 5, "M": 50, "L": 500},
        ),
        BenchmarkCase(
            name="drawing_to_multipolygon_mixed",
            description="Polygonize a cycle of syllable drawings with a warm cache.",
            operation=drawing_to_multipolygon_mixed,
            iterations={"S": 20, "M": 200, "L": 2_000},
        ),
        BenchmarkCase(
            name="convert_time",
            description="Format integer millisecond timestamps as ASS time strings.",
            operation=convert_time,
            iterations={"S": 1_000, "M": 10_000, "L": 100_000},
        ),
        BenchmarkCase(
            name="generate_100_lines",
            description="Deep-copy Lines and write a batch of 100 generated events.",
            operation=generate_line_batch,
            iterations={"S": 1, "M": 10, "L": 100},
        ),
        BenchmarkCase(
            name="generate_100_events",
            description="Construct Events and write a cached batch of 100 events.",
            operation=generate_event_batch,
            iterations={"S": 1, "M": 10, "L": 100},
        ),
    ]


def run_operations(operation: Callable[[], object], iterations: int) -> None:
    """Execute an operation repeatedly while releasing each result promptly."""

    for _ in range(iterations):
        _discard(operation())
