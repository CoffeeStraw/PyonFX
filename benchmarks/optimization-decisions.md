# PyonFX optimization decisions

This report records the evidence behind the optimization work completed on
Windows 11 with Python 3.14.0. Benchmark results are evidence, not universal
performance guarantees: compare reports only when their fixture, dependency,
Python, and platform metadata are compatible.

## Accepted changes

| Area | Decision and measured result | Evidence |
| --- | --- | --- |
| Lightweight output event | Added public `Event`, `write_event`, and `write_events`. For 100 generated events, the measured path changed from about 58.90 ms with `Line.deepcopy()` to 0.208 ms, about 282.9 times faster. Tracemalloc peak changed from about 170.7 KB to 41.9 KB, with byte-equivalent output. The gain primarily comes from avoiding deep copies of extended `Line` data. | `baseline-m-event-writer-python314-windows.json`, `memory-event-writer-s-python314-windows.json` |
| Streaming output | Added `save_events()` with bounded batches. At 100,000 events, elapsed time changed from about 1019 ms to 1042 ms (+2.3%), while tracemalloc peak fell from about 13.69 MB to 0.70 MB (94.9%) and peak working set fell from about 113.12 MB to 90.44 MB (about 20%). Output size and bytes were equivalent. | `streaming-writer-100k-python314-windows.json` |
| Selective extended data | Added `extended_features`. Relative to full extended parsing at about 7.15 ms, line-only measured about 2.10 ms (70.7% lower), words about 2.77 ms (61.3% lower), and syllables about 3.94 ms (44.9% lower). Selective-mode tracemalloc peak was about 179.9 KB versus 266.5 KB for full processing. | `selective-extended-public-s-python314-windows.json`, `selective-extended-m-python314-windows.json`, `selective-extended-memory-s-python314-windows.json` |
| Geometry helpers | Added normalization, repair, explicit bounds overlap, and safe boolean helpers. Valid-path intersection measured about 3.3% faster than the previous shared implementation. An explicit bounds guard measured about 2.66 times faster for disjoint geometry. Invalid and collection fixtures preserved area, validity, and polygon component counts. | Geometry helper tests and the recorded TODO-06 experiment results |
| Multipolygon cache | Added a shared LRU cache bounded to 128 entries and keyed by immutable drawing text plus tolerance. Repeated warm conversion measured about 94.4% faster and a mixed drawing workload about 95.0% faster. A 128-entry complex translated-glyph workload increased process working set by about 2.59 MB (2.87%). | `multipolygon-cache-m-python314-windows.json`, `multipolygon-cache-memory-s-python314-windows.json` |
| Timing helpers | Added explicit line- and syllable-relative retiming helpers. One thousand fixed-seed randomized cases matched the existing shared effect helpers. The measured performance ratio was about 0.996, effectively neutral. | Timing helper tests and the recorded TODO-07 experiment results |
| Stable random seeds | Added versioned BLAKE2b 64-bit seed derivation and independent `Random` construction. Golden values prove cross-process stability without Python's randomized `hash()`. A derivation measured about 2.25 microseconds. | Random helper tests and the recorded TODO-11 experiment results |
| Correctness and benchmark tools | Added S/M/L benchmark tiers, memory/call-count reports, and ASS fingerprints covering hashes, encoding, line endings, event structure, tags, drawing scale, event-stream hash, and first difference. A real `fx_010` library/standalone comparison found 47 equivalent events and no first difference. | `baseline-s-python314-windows.json`, `memory-baseline-s-python314-windows.json`, `fx010-fingerprint-comparison-v2.json` |

## Rejected experiments

Rejected implementations were removed after evidence collection; their JSON
reports remain as historical evidence.

| Experiment | Decision |
| --- | --- |
| Font instance reuse | Removed. Construction count fell from 17 to 11, but default full extended processing slowed about 7.8% and memory increased. |
| Single-character extents cache | Removed. Full extended improved only about 2.1%, while line/words/syllables modes slowed about 10.9% to 36.7%. |
| Global glyph drawing cache | Removed. Warm and mixed workloads improved about 51% to 55%, but a cold miss remained about 16.6% slower and a reliable real-effect hit rate was not established. |
| New ASS number formatter | Removed. The best correctness-safe implementation remained about 15% to 16% slower than the existing formatter. |
| New alpha/HSV wrappers | Not added because `Convert` already exposes equivalent public color and alpha operations. |
| `TimeSpan` value object | Not added because object wrapping did not demonstrate sufficient correctness or maintenance value. |

Relevant historical reports include the `font-reuse-*`,
`single-char-extents-cache-*`, and `glyph-shape-*-cache-*` JSON files under
`benchmarks/results/`.

## Deferred architecture

### General multiprocessing

Multiprocessing remains effect-local. A fully extended line serialized to
about 16,038 bytes in the investigation, worker input/output boundaries are
not standardized, and Windows spawn adds Font/GEOS lifecycle and stable-order
complexity. A core framework should be reconsidered only after multiple
effects converge on batch-oriented `Event` worker output.

### Asset session

A core asset-session abstraction was rejected for now. Only one local stroke
effect uses the versioned asset-cache/session pattern, so it remains an
external extension until there is a second independent consumer.

### Rust or another native language

No Rust/PyO3 implementation is justified at this stage. The evaluated machine
did not have `rustc`, `cargo`, or `maturin`, and introducing a compiler plus
cross-platform wheels would be a substantial release and maintenance cost.
The current Python work already addresses the measured common costs:

- `Event` generation is about 2 microseconds per event in the component
  benchmark;
- streaming 100,000 events is about 10.4 microseconds per event including I/O;
- selective extended processing avoids about 45% to 71% of unnecessary work;
- repeated drawing-to-multipolygon conversion is about 95% faster with the
  bounded cache.

Rust should be reconsidered only when profiling a real effect shows that a
non-cacheable drawing parser/flattening path consumes at least about 20% of
total runtime, and when a batch-oriented boundary can prove byte- or
geometry-equivalent output.

## Compatibility and platform notes

- `extended=True` without `extended_features` preserves historical full
  behavior. `extended=False` remains base parsing only.
- Existing `Line`, `write_line()`, and `save()` workflows remain supported.
- `Shape.to_multipolygon()` now returns a cached Shapely `MultiPolygon` for an
  identical drawing/tolerance key. Callers must treat the returned geometry
  as immutable. The cache is process-local and bounded to 128 entries.
- Stable seed derivation is portable, but rendered text geometry and benchmark
  timing still depend on installed fonts, Shapely/GEOS, Python, CPU, and OS.
- Multiprocessing consumers must account for Windows spawn semantics and must
  establish deterministic event ordering themselves.
- ASS output correctness should be checked with semantic fingerprints in
  addition to byte hashes when platform-specific line endings or encoding are
  intentionally different.

## Validation policy

An optimization is accepted only with before/after correctness, performance,
and memory evidence. Failed experiments are removed instead of retained for
sunk-cost reasons. The pytest suite, API documentation, structured benchmark
reports, and worktree audit form the release evidence for this change set.
