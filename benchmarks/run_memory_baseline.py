"""Measure isolated memory usage and key call counts for benchmark cases."""

# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from benchmarks.cases import build_cases, run_operations
from pyonfx import Convert, Line, Shape
from pyonfx.font import Font

ROOT = Path(__file__).resolve().parents[1]


def _windows_memory_info() -> dict[str, int] | None:
    if sys.platform != "win32":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    process = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "working_set_bytes": int(counters.WorkingSetSize),
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
        "pagefile_bytes": int(counters.PagefileUsage),
        "peak_pagefile_bytes": int(counters.PeakPagefileUsage),
    }


def _process_memory_info() -> dict[str, int | None]:
    windows = _windows_memory_info()
    if windows is not None:
        return windows
    try:
        import resource
    except ImportError:
        return {
            "working_set_bytes": None,
            "peak_working_set_bytes": None,
            "pagefile_bytes": None,
            "peak_pagefile_bytes": None,
        }
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform != "darwin":
        peak *= 1024
    return {
        "working_set_bytes": None,
        "peak_working_set_bytes": peak,
        "pagefile_bytes": None,
        "peak_pagefile_bytes": None,
    }


@contextmanager
def _count_key_calls() -> Iterator[dict[str, int]]:
    counts = {
        "font_init": 0,
        "line_copy": 0,
        "line_serialize": 0,
        "shape_init": 0,
        "text_to_shape": 0,
        "to_multipolygon": 0,
    }
    original_font_init = Font.__init__
    original_line_copy = Line.copy
    original_line_serialize = Line.serialize
    original_shape_init = Shape.__init__
    original_text_to_shape = Convert.text_to_shape
    original_to_multipolygon = Shape.to_multipolygon

    def font_init(self: Font, *args: Any, **kwargs: Any) -> None:
        counts["font_init"] += 1
        original_font_init(self, *args, **kwargs)

    def line_copy(self: Line) -> Line:
        counts["line_copy"] += 1
        return original_line_copy(self)

    def line_serialize(self: Line) -> str:
        counts["line_serialize"] += 1
        return original_line_serialize(self)

    def shape_init(self: Shape, *args: Any, **kwargs: Any) -> None:
        counts["shape_init"] += 1
        original_shape_init(self, *args, **kwargs)

    def text_to_shape(*args: Any, **kwargs: Any) -> Shape:
        counts["text_to_shape"] += 1
        return original_text_to_shape(*args, **kwargs)

    def to_multipolygon(self: Shape, *args: Any, **kwargs: Any) -> object:
        counts["to_multipolygon"] += 1
        return original_to_multipolygon(self, *args, **kwargs)

    Font.__init__ = font_init
    Line.copy = line_copy
    Line.serialize = line_serialize
    Shape.__init__ = shape_init
    Convert.text_to_shape = staticmethod(text_to_shape)
    Shape.to_multipolygon = to_multipolygon
    try:
        yield counts
    finally:
        Font.__init__ = original_font_init
        Line.copy = original_line_copy
        Line.serialize = original_line_serialize
        Shape.__init__ = original_shape_init
        Convert.text_to_shape = staticmethod(original_text_to_shape)
        Shape.to_multipolygon = original_to_multipolygon


def _run_child(case_name: str, tier: str) -> dict[str, Any]:
    cases = {case.name: case for case in build_cases()}
    if case_name not in cases:
        raise ValueError(f"unknown case: {case_name}")
    case = cases[case_name]
    iterations = case.iterations[tier]

    gc.collect()
    memory_before = _process_memory_info()
    tracemalloc.start()
    started = time.perf_counter_ns()
    with _count_key_calls() as counts:
        run_operations(case.operation, iterations)
    elapsed_ns = time.perf_counter_ns() - started
    traced_current, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    memory_after = _process_memory_info()

    return {
        "name": case.name,
        "description": case.description,
        "iterations": iterations,
        "elapsed_ns": elapsed_ns,
        "per_operation_ns": elapsed_ns / iterations,
        "tracemalloc_current_bytes": traced_current,
        "tracemalloc_peak_bytes": traced_peak,
        "process_memory_before": memory_before,
        "process_memory_after": memory_after,
        "key_call_counts": counts,
    }


def _run_parent(tier: str) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in build_cases():
        command = [
            sys.executable,
            "-B",
            "-m",
            "benchmarks.run_memory_baseline",
            "--tier",
            tier,
            "--child-case",
            case.name,
        ]
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"memory benchmark child failed for {case.name}:\n{completed.stderr}"
            )
        results.append(json.loads(completed.stdout))

    return {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tier": tier,
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "benchmarks": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("S", "M", "L"), default="S")
    parser.add_argument("--child-case", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.child_case:
        report = _run_child(args.child_case, args.tier)
    else:
        report = _run_parent(args.tier)

    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
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
