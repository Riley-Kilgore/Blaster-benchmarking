# Job #91 — pass 5 step 1: integration prerequisite

Date: 2026-10-12. Scope: check that the read-only PlutusCoreBlaster and CardanoLedgerApiBlaster
build against untouched lean-blaster. This run does no corpus, family or ak-equiv-check work.

## Verdict

| Library | Library build | Test-driver build (`Tests`) |
|---|---|---|
| PlutusCoreBlaster | **PASS** (`PlutusCore` exit 0, `Lemmas` exit 0) | **PASS** (exit 0, 84 s) |
| CardanoLedgerApiBlaster | **PASS** (`CardanoLedgerApi` exit 0) | **INCONCLUSIVE**: reached the 1200 s bound (exit 124) with no errors |

No incompatibility was found. Both libraries compile against lean-blaster@ab82a3c.
CardanoLedgerApi's test suite did not finish within the bound. Up to that point it had
no errors and no failed `#blaster` results: 8 of 13 test modules were built, giving 15 `✅ Valid`, 0 Falsified and 0 Undetermined.
These modules had not finished: `Tests.Scripts.HelloWorld.Properties`, `Tests.Scripts.SellNFT.Properties`,
`Tests.Scripts.UnlockPIN.Properties`, and the aggregators `Tests.Scripts`, `Tests.Basic` and `Tests`.
Per the job rules it was not retried.

## Exact HEADs (all clean working trees, before and after)

| Repo | HEAD | Branch |
|---|---|---|
| lean-blaster | `ab82a3cb647cbdecc198202244622554e2464e4d` | hillclimb-base |
| Blaster-benchmarking | `ea924d4476cc41118d42d7605a3b15c43e90a83a` | blaster-baseline-harness |
| ak-equiv-check | `e0a530e7f99b64cac86b130a1dfb97ce154d38ec` | main |
| PlutusCoreBlaster | `4ef48606303c45225d3ed2e2a87fc50280a763b7` | detached |
| CardanoLedgerApiBlaster | `577e3eb03b5be09354cfdb1c0d0c12e9e16541a0` | detached |

After the run, `git status --short` was empty for all repos except Blaster-benchmarking. There the
only new path is `corpus/` (this report); `corpus/validators/prereq/work/` is git-ignored.

Toolchain: Lean 4.24.0 (commit 797c613eb9b6, aarch64-unknown-linux-gnu), Lake 5.0.0-src+797c613,
Z3 **5.1.0** (`/usr/local/bin/z3`). Note that both repos' CI and the sandbox notes pin Z3 4.15.2;
5.1.0 is what is installed here.

## Upstream build configuration (read before building)

- PlutusCoreBlaster `lakefile.lean`: `require Blaster from git "https://github.com/input-output-hk/Lean-blaster" @ "main"`
  (manifest pin `c576289cb554…`, which is an ancestor of lean-blaster HEAD, 34 commits behind).
  Libraries: `PlutusCore` (default), `Tests` (test_driver), `Lemmas`, `Cryptograph`. Makefile
  `build_plutus_core` = `lake build PlutusCore; lake build Lemmas`; `build_tests` = `lake test`.
- CardanoLedgerApiBlaster `lakefile.lean`: `require PlutusCore from git …PlutusCoreBlaster @ "main"`
  (manifest pin `17cee18a…`, an ancestor of PlutusCoreBlaster HEAD) and
  `require Blaster from git …Lean-blaster @ "beta-lambda-cache-optimization"` (manifest pin
  `eff8cbbf…`, **not present** in the local lean-blaster clone). Makefile `build_cardano_ledger_api` =
  `lake build CardanoLedgerApi`; `build_tests` = `LEAN_NUM_THREADS=5 lake test`.
- In both repos `.lake` is a symlink into an empty `/cache/lake-*` directory, so no git
  dependencies were cached. A build as-is would need network clones, which are out of scope.
  The local overlay below was used instead.

## Dependency resolution: disposable overlays

Work dir (git-ignored via `prereq/.gitignore` = `work/`):
`/workspace/Blaster-benchmarking/corpus/validators/prereq/work/`

```sh
P=/workspace/Blaster-benchmarking/corpus/validators/prereq
cd $P/work
git -C /workspace/PlutusCoreBlaster archive --prefix=PlutusCoreBlaster/ 4ef48606303c45225d3ed2e2a87fc50280a763b7 | tar -x
git -C /workspace/CardanoLedgerApiBlaster archive --prefix=CardanoLedgerApiBlaster/ 577e3eb03b5be09354cfdb1c0d0c12e9e16541a0 | tar -x
# originals preserved alongside as lakefile.lean.orig / lake-manifest.json.orig
# lakefile edits (full diff in logs/overlay.diff):
#   PlutusCore:  require Blaster from "/workspace/lean-blaster"
#   CLA:         require PlutusCore from "$P/work/PlutusCoreBlaster"
#                require Blaster from "/workspace/lean-blaster"
# the copied lake-manifest.json was removed so Lake re-resolves the path deps (no network)
```

The resolved manifests are in `logs/pc_lake-manifest.resolved.json` and
`logs/cla_lake-manifest.resolved.json`; both contain only `"type": "path"` entries.
lean-blaster was used in place via a path dependency. Its existing build in
`/cache/lake-lean-blaster` was already up to date (`lake build Blaster --no-build` reported
"All targets up-to-date (210 jobs)", exit 0), and no Blaster module was rebuilt.
No tracked file in lean-blaster, PlutusCoreBlaster or CardanoLedgerApiBlaster was modified.

## Commands and results

All commands were run once, from the overlay copy, with output going to `logs/`. The status
summary is in `logs/status.txt`.

| # | cwd | Command | Exit | Time | Log |
|---|---|---|---|---|---|
| 1 | work/PlutusCoreBlaster | `timeout 1200 lake build PlutusCore` | 0 | 32 s | logs/pc_build_PlutusCore.log |
| 2 | work/PlutusCoreBlaster | `timeout 1200 lake build Lemmas` | 0 | 6 s | logs/pc_build_Lemmas.log |
| 3 | work/CardanoLedgerApiBlaster | `timeout 1200 lake build CardanoLedgerApi` | 0 | 18 s | logs/cla_build_CardanoLedgerApi.log |
| 4 | work/PlutusCoreBlaster | `timeout 1200 lake build Tests` | 0 | 84 s | logs/pc_build_Tests.log |
| 5 | work/CardanoLedgerApiBlaster | `LEAN_NUM_THREADS=5 timeout 1200 lake build Tests` | 124 | 1200 s | logs/cla_build_Tests.log |

`lake build Tests` is the test-driver library that `lake test` builds. It was run without the
CI `clean` step, and run #4 covers the whole `Tests` library, not the Makefile's file-coverage
script. The `Cryptograph` library was not built because it is not part of any Makefile/CI target.

Warnings: the one warning is `PlutusCore/UPLC/CekMachine.lean:312:4: declaration uses 'sorry'`.
It comes from upstream PlutusCoreBlaster source at 4ef4860 and was not introduced by this run.

## Blocker / follow-up for coordinator

- Nothing blocks library integration.
- CardanoLedgerApi `Tests` did not finish within 1200 s. The longest module seen was
  `Tests.Scripts.SellNFT.SellNFT` at 163 s; the remaining `*.Properties` modules were still running.
  If a full CLA test verdict is required, a later run should do one of two things:
  (a) build the three unfinished `Properties` modules one at a time with an explicit per-module bound, or
  (b) give one larger, explicitly approved bound. It should not blindly repeat this command.

## Artifacts (export)

- `corpus/validators/prereq/JOB91_PREREQ.md` (this file)
- `corpus/validators/prereq/job91_prereq.json` (machine-readable summary)
- `corpus/validators/prereq/logs/` (overlay.diff, status.txt, five build logs, two resolved manifests)
- `corpus/validators/prereq/.gitignore` (ignores `work/`, about 116 MB of disposable copies and build products)
