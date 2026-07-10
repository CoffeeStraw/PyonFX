# PyonFX benchmarks

These benchmarks establish repeatable before/after evidence for PyonFX changes.
They are not correctness tests and must be used together with the pytest suite and
output fingerprints.

Run the small tier without writing a result file:

```powershell
python -B -m benchmarks.run_baseline --tier S
```

Write a structured baseline report:

```powershell
python -B -m benchmarks.run_baseline `
  --tier M `
  --repeats 7 `
  --warmups 1 `
  --output benchmarks\results\baseline-m.json
```

Tiers use the same operations with different iteration counts:

- `S`: quick local and pull-request checks;
- `M`: routine before/after comparison;
- `L`: release or dedicated performance runs.

Each report records the fixture hash, Python and dependency versions, Git commit,
dirty-worktree state, raw sample durations, per-operation median, standard deviation,
and coefficient of variation. Compare results only when the environment and fixture
are compatible.
