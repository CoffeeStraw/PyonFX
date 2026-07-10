"""Compare buffered and streaming Event output in isolated processes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Iterator, Sequence

from benchmarks.run_memory_baseline import _process_memory_info
from pyonfx import Ass, Event


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "Ass" / "ass_core.ass"


def _events(count: int) -> Iterator[Event]:
    for index in range(count):
        yield Event(
            layer=index % 8,
            start_time=1000 + (index % 100) * 10,
            end_time=3000 + (index % 100) * 10,
            style="Default",
            text=f"{{\\pos({index % 1920},{index % 1080})}}event-{index}",
        )


def _child(mode: str, count: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pyonfx-writer-") as temp_dir:
        output = Path(temp_dir) / f"{mode}.ass"
        io = Ass(str(FIXTURE), str(output), keep_original=False, extended=False)
        before = _process_memory_info()
        tracemalloc.start()
        started = time.perf_counter_ns()
        if mode == "buffered":
            io.write_events(_events(count))
            io.save(quiet=True)
        elif mode == "streaming":
            io.save_events(_events(count), batch_size=4096, quiet=True)
        else:
            raise ValueError(f"unknown mode: {mode}")
        elapsed = time.perf_counter_ns() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        after = _process_memory_info()
        return {
            "mode": mode,
            "count": count,
            "elapsed_ns": elapsed,
            "tracemalloc_current_bytes": current,
            "tracemalloc_peak_bytes": peak,
            "process_memory_before": before,
            "process_memory_after": after,
            "output_bytes": output.stat().st_size,
        }


def _parent(count: int) -> dict[str, Any]:
    results = []
    for mode in ("buffered", "streaming"):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "benchmarks.run_streaming_writer_benchmark",
                "--count",
                str(count),
                "--child-mode",
                mode,
            ],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        results.append(json.loads(completed.stdout))
    return {"schema_version": 1, "count": count, "results": results}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--child-mode", choices=("buffered", "streaming"))
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.count < 1:
        raise ValueError("--count must be at least 1")
    report = _child(args.child_mode, args.count) if args.child_mode else _parent(args.count)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(serialized)
    else:
        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8", newline="\n")
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
