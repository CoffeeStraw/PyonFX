"""Run repeatable PyonFX component benchmarks and emit structured JSON."""

# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy
import scipy
import shapely

from benchmarks.cases import ASS_FIXTURE, build_cases, run_operations

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except OSError, subprocess.CalledProcessError:
        return None
    return result.stdout.strip()


def _environment() -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "shapely": shapely.__version__,
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_status_porcelain": _git_value("status", "--porcelain"),
    }


def _summarize(samples_ns: list[int], iterations: int) -> dict[str, Any]:
    per_operation = [sample / iterations for sample in samples_ns]
    mean_ns = statistics.fmean(per_operation)
    stdev_ns = statistics.stdev(per_operation) if len(per_operation) > 1 else 0.0
    return {
        "iterations_per_sample": iterations,
        "samples": len(samples_ns),
        "sample_total_ns": samples_ns,
        "per_operation_ns": {
            "minimum": min(per_operation),
            "median": statistics.median(per_operation),
            "mean": mean_ns,
            "maximum": max(per_operation),
            "stdev": stdev_ns,
            "coefficient_of_variation": stdev_ns / mean_ns if mean_ns else 0.0,
        },
    }


def run_benchmarks(tier: str, repeats: int, warmups: int) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in build_cases():
        iterations = case.iterations[tier]
        for _ in range(warmups):
            run_operations(case.operation, iterations)

        samples_ns: list[int] = []
        for _ in range(repeats):
            gc.collect()
            gc.disable()
            try:
                started = time.perf_counter_ns()
                run_operations(case.operation, iterations)
                elapsed = time.perf_counter_ns() - started
            finally:
                gc.enable()
            samples_ns.append(elapsed)

        results.append(
            {
                "name": case.name,
                "description": case.description,
                **_summarize(samples_ns, iterations),
            }
        )

    return {
        "schema_version": 1,
        "tier": tier,
        "repeats": repeats,
        "warmups": warmups,
        "fixture": {
            "path": str(ASS_FIXTURE.resolve()),
            "sha256": _sha256(ASS_FIXTURE),
            "bytes": ASS_FIXTURE.stat().st_size,
        },
        "environment": _environment(),
        "benchmarks": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("S", "M", "L"), default="S")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. Without this option, JSON is printed to stdout.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")
    if args.warmups < 0:
        raise ValueError("--warmups cannot be negative")

    report = run_benchmarks(args.tier, args.repeats, args.warmups)
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
