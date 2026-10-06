# Blaster baseline harness

Runs the `blaster` tactic on every goal of the six suites (NNG4, STG4, ITL4,
MiniF2F, Verina, UPLC) and writes one JSON line per goal.

## Setup (once)

```bash
lake exe cache get                     # Mathlib oleans
lake build Blaster                     # Blaster @ 585c5fc (pinned in lakefile.lean)
benchmarks/blaster/install_z3.sh       # Z3 4.15.2 into .tools/ (sha256-verified)
python3 benchmarks/blaster/blaster_bench.py check
```

## Run

```bash
benchmarks/blaster/run_suite.sh NNG4   # one suite
benchmarks/blaster/run_all.sh          # all six
```

Options: `--out DIR` (default `results/<UTC time>-<blaster sha>/`), `--jobs N`
(default 1; anything above 1 perturbs timings and therefore timeouts).

Every run first verifies, and aborts with exit code 2 on any mismatch:
Lean 4.24.0, the Blaster commit in `lake-manifest.json` and in the checkout (which
must be clean), and that the `z3` Blaster will spawn is exactly 4.15.2. Blaster
itself accepts any `z3` on PATH without checking its version, so the harness puts
`.tools/z3-4.15.2/bin` first (override the directory with `BLASTER_Z3_DIR`; the
version is still enforced).

## How a goal is run

The goal's source file is copied with `import Blaster` prepended and only that
goal's proof replaced by `blaster (verbose: 1) (random-seed: 42)`; nothing else
in the file changes. It is elaborated by `lean --json` with Blaster's native
library loaded (`--load-dynlib`; plain `lake env lean` would interpret Blaster,
about 3x slower). Status comes from the messages attributed to the goal's lines:

| status       | evidence                                                         |
|--------------|------------------------------------------------------------------|
| Valid        | `declaration uses 'blasterProven'` warning, no error             |
| Falsified    | `Goal was falsified` error                                       |
| Undetermined | only `unsolved goals` (Blaster returns the optimized goal)        |
| Error        | any other error, a crash, or no Blaster outcome                  |
| Timeout      | wall clock exceeded `time_limit_s` (the process group is killed) |

Before the goals, each suite runs a compile check (every goal's proof replaced by
`sorry`); `statement_compiles` records whether the statement elaborates on its own.

Goal ids: theorem name (NNG4, STG4, ITL4, MiniF2F), task file stem (Verina,
target theorem `*_spec_satisfied`), `Width/<stem>` or `Depth/<stem>` (UPLC).

## Output

`<out>/<SUITE>.jsonl` (goals in source order), `<out>/manifest.json` (versions,
Z3 sha256, seed, limits, platform, counts) and `<out>/work/` (the exact files
elaborated). Per line:

```json
{"suite": "NNG4", "goal_id": "add_comm", "status": "Valid",
 "error_group": null, "error_message": null,
 "stage_times_s": {"Optimization": 0.058},
 "total_time_s": 0.71, "time_limit_s": 20,
 "blaster_commit": "585c5fc...", "random_seed": 42,
 "statement_compiles": true, "source": "BlasterBenchmarks/NNG4/NNG4.lean", "theorem": "add_comm"}
```

`stage_times_s` holds the stages Blaster actually ran (it stops early when
optimization alone decides the goal). It is empty for a Timeout: Lean only
emits the verbose output when the tactic finishes. `total_time_s` is the wall
time of the whole `lean` process, including imports and the rest of the file.
