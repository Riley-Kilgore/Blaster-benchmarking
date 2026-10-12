# Job #91 step 1: validator corpus. Status: BLOCKED at the ak-equiv-check end-to-end prerequisite

Date: 2026-10-12. This continues `prereq/JOB91_PREREQ.md`. In that run both library builds
passed on untouched lean-blaster `ab82a3cb647cbdecc198202244622554e2464e4d`. The optional
CardanoLedgerApi `Tests` timeout is not a prerequisite and was not repeated.

## Outcome

1. **Blaster pin update in ak-equiv-check: done.** It is committed locally on the new branch
   `agent/job91-blaster-pin-ab82a3c` and not pushed. The old pin `402f6d22c1fc…` is replaced by
   `ab82a3cb647cbdecc198202244622554e2464e4d` in three files:
   `tool/blaster_config.json` (`revisions.Lean-blaster`), `tool/blaster-backend/lakefile.lean`
   and `tool/blaster-backend/lake-manifest.json` (`rev`, `inputRev`). Nothing else changed.
   The commit is reachable upstream on `origin/hillclimb-base`, and the new pin is a descendant
   of the old one.
2. **One real pair end to end with CEK replay: BLOCKED.** This was the first real prerequisite
   failure. Per the job rules, the run stopped here and nothing was retried.
3. **Team failures, FAMILIES.md, per-family Lean files and metadata, label evidence: NOT
   STARTED.** All of them depend on step 2. Falsified labels need ak-equiv-check CEK replay, and
   the job rules say to stop at the first prerequisite failure.

## Exact blocker

The host is `linux-aarch64` (`uname -m` = `aarch64`). ak-equiv-check is fail-closed and pins
every executable by platform key. It pins only `linux-x86_64` and `darwin-arm64`:

| Pinned input | Where | linux-aarch64 entry |
|---|---|---|
| Aiken v1.1.22 (old compiler) | `corpus/compiler_pair.json` `old.artifacts` | missing |
| Aiken v1.1.23 (new compiler) | `corpus/compiler_pair.json` `new.artifacts` | missing |
| CEK replay evaluator (aiken-uplc v1.1.23) | `tool/blaster_config.json` `evaluator.artifacts` | missing |
| Z3 4.15.2 | `tool/blaster_config.json` `solver_artifacts` | missing (`config.py:277-282` raises `no pinned solver artifact`) |

Observed failures (verbatim, from the logs):

- `python3 scripts/setup_toolchains.py` → `RuntimeError: no pinned Aiken compiler artifacts for linux-aarch64`
- `equiv-checker profile run historical-regression-v1.1.22-v1.1.23 --strict` → `aikup installation for v1.1.23 not found under /home/agent/.aiken/versions/v1.1.23 (aarch64)`
- `load_blaster_config(blaster_config.json)` → the same evaluator error. The solver check
  comes next in the same function and has no linux-aarch64 entry either.

The system Z3 is 5.1.0. The pinned version is 4.15.2, and the backend checks the version
string (`blaster.py:1215`), so the system Z3 cannot be substituted.

Working around this would need one of the following. Each is outside this job's mandate,
because "pin change only as explicitly assigned" rules out new trust-root pins:

- **(a) Owner approves adding linux-aarch64 pins (recommended).** Upstream publishes the
  artifacts (GitHub release asset lists, queried 2026-10-12):
  - `aiken-aarch64-unknown-linux-musl.tar.gz` for v1.1.22 and v1.1.23. The upstream-published
    archive sha256 values are in `logs/upstream_aarch64_aiken_sha256.txt`; the binary sha256
    still has to be computed.
  - `z3-4.15.2-arm64-glibc-2.34.zip`.

  Adding them would edit `corpus/compiler_pair.json`, `tool/blaster_config.json`,
  `corpus/compiler_release.lock.json` and probably `compiler-artifacts/*.json`. Note that the
  evaluator binary hash is part of the replay provenance, so aarch64 evidence would have a
  different evaluator identity than the published x86_64 baselines.
- **(b)** Run step 2 on an approved linux-x86_64 or darwin-arm64 host.

Not done, by design: no Aiken or Z3 was downloaded or installed, no Aiken was built from source
(that would need an extra clone), and no pin check was bypassed.

## Unit-test check of the pin change

The CI `unit` job's test list ran with the deps locked in `uv.lock`, installed by pip into a
throwaway venv at `/tmp/akvenv` because `uv` is not installed. The command is in
`logs/commands.tsv`.

| Tree | Ran | Result |
|---|---|---|
| pin change | 124 | 1 failure, 17 errors |
| untouched main `e0a530e` (stash) | 124 | 1 failure, 17 errors, **identical failing set** |

All 18 failures are `ValueError: no pinned compiler artifact for linux-aarch64`. This is the
same platform blocker; none is caused by the pin. The tests have to be re-run on a pinned
platform before merge.

The new Blaster pin has not yet been built through ak-equiv-check's own git-require backend.
That would clone lean-blaster, which is out of scope here. The step-1 prereq built PlutusCore,
Lemmas and CardanoLedgerApi against this exact lean-blaster commit, through path overlays, all
with exit 0.

## Team failures (sources/)

**None provided.** `Blaster-benchmarking/corpus/validators/sources/` does not exist, and no
report was invented. If the corpus continues, the ≥1/3 real families would come from published
validators in the approved library sources: the CardanoLedgerApiBlaster `Tests/Scripts`
HelloWorld, SellNFT and UnlockPIN. This has not been done yet.

## Acceptance matrix

| Criterion | Status |
|---|---|
| lean-blaster unchanged at ab82a3c, libraries read-only | ✅ clean trees, HEAD verified |
| ak-equiv-check old Blaster pin → ab82a3c | ✅ (local commit, unpushed) |
| One actual pair end to end, CEK replay if falsified | ❌ blocked: no linux-aarch64 pins (above) |
| Team failures collected / "none" stated | ✅ none provided |
| ≥1/3 real/team families | ❌ not started |
| FAMILIES.md with 10–15 families, provenance, difficulty, pre-chosen size sequence, five goal types | ❌ not started |
| One fixed Lean file + metadata per family | ❌ not started |
| Label evidence (CEK replay for Falsified; argument + seeded random tests for Valid) | ❌ not started (replay unavailable) |
| Offline fixed-Lean hill-climb prep < 30 s, fixed seeds | ❌ not started |
| No sorry/admit/axioms, no fabricated results | ✅ nothing generated, all statuses are from real logs |
| Bounded subprocesses with process-group kill | ✅ `scripts/bounded_run.sh` (setsid + `timeout -k 10`). 0 live lean/z3/lake/aiken processes after every command |
| Owner signoff | ⏳ **pending**, no owner available |

Lingering processes: ten `lean`/`z3` **zombies** from the earlier timed-out CLA `Tests` run
(PIDs 2076–2560) are still listed. Their parent is PID 1 (`sleep infinity`), which does not reap
children. They are dead and hold no CPU, and they cannot be killed further. This run started
no process that outlived its command.

## Evidence paths (exportable)

- `corpus/validators/JOB91_REPORT.md`: this file
- `corpus/validators/job91_report.json`: machine-readable summary
- `corpus/validators/logs/commands.tsv`: every command with UTC time, exit code, seconds and cwd
- `corpus/validators/logs/akeq_*.log`: full output of each command
- `corpus/validators/logs/upstream_aarch64_aiken_sha256.txt`: upstream-published archive hashes (input for option a)
- `corpus/validators/scripts/bounded_run.sh`: the bounded runner
- `corpus/validators/prereq/`: step-1 integration prerequisite (previous run)
- ak-equiv-check branch `agent/job91-blaster-pin-ab82a3c`: the pin commit
