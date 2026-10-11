# Soundness gate

Decides whether a Lean-blaster commit is acceptable to the improvement loop. A change is kept
only if the gate passes on **every** registered Z3 build.

```bash
python3 benchmarks/blaster/gate/gate.py setup-z3             # install + verify Z3 builds (once)
python3 benchmarks/blaster/gate/gate.py manifest --write     # (re)write protected-files manifest
python3 benchmarks/blaster/gate/gate.py run <commit>         # all checks, all builds
python3 benchmarks/blaster/gate/gate.py run <commit> --source /path/to/Lean-blaster   # local commits
```

Exit code: 0 pass, 1 fail, 2 the gate could not run. Output: `results/gate/<sha7>/summary.md`,
`gate.json`, and per build `<build>/report.json` (+ `heldout_report.json`, details of held-out
goals only; keep it away from the agent).

## Checks (per Z3 build)

| | check | fails when |
|---|---|---|
| a | Lean-blaster `Tests/` at `<commit>` | any test file has an error (each file elaborated directly, as `lake build Tests` would; import-only aggregators skipped) |
| b | known-false set | any entry is **Valid**, or a case's plain-Lean refutation does not hold |
| c | protected files | any manifest entry is missing or changed |
| d | consistency | for any Valid result seen in the run, the SMT assertions **without the negated goal** are unsat under Z3 (this build) or cvc5 |

**Known-false set.** `known_false/climb.json`: the 244 `(solve-result: 1)` tests of Lean-blaster
`Tests/` and `Issue33.lean:74` (case D, command form), all run from copies pinned at 585c5fc so
that editing tests cannot weaken the check; plus `known_false/cases/*.lean`, one Blaster call per
file (A #194, B #226, C #225 in tactic and command form; D #194 tactic form), each with a refutation
that the gate checks on a copy with the Blaster call replaced by `sorry` (axioms must not include
`sorryAx` or `blasterProven`; command forms must refute the identical statement). Held-out
entries (misformalized MiniF2F goals) live in `results/baseline/heldout/known_false_heldout.json`,
outside the repository.

**Consistency.** Valid results come from re-running the six suites with the harness tactic plus
`(dump-smt-lib: 1)`, every Lean-blaster test file that calls Blaster (dump added, `#guard_msgs`
wrappers removed, line numbers kept), and any Valid known-false entry. The negated goal is the
query's final `(assert (not …))`; the rest is given to Z3 and to cvc5 (`--mbqi`,
`--full-saturate-quant`), 120 s each. When one call yields several queries (e.g.
`induction … <;> blaster`, one per goal, all Valid), every query is checked and the worst verdict
is reported. Verdicts: `consistent` (some solver: sat), `vacuous` (some
solver: unsat), `conflict` (sat and unsat), `undecided`, `n/a` (decided by the optimizer, no SMT
query), `not-checked` (`#kind`/`#bmc` results, whose queries are not dumped). For a vacuous set
the unsat core is extracted and labelled `#194` when it pairs an `_ext_fun` axiom with a
`_def_cstr` lambda definition.

## Z3 builds

Lean and Blaster always run natively; only the `z3` on `PATH` (which Blaster spawns as
`z3 -in -smt2`) changes. Each binary's sha256 is checked before use and recorded in the report.

| build | binary sha256 | how it runs |
|---|---|---|
| `macos-arm64` | `b8c06968b96f7b485382746cb8a956e131423ddd8be54ccdaed88b1466f5fc35` | native (harness pin); gives the false Valid on `Issue33.lean:74` |
| `linux-x64` | `4a84b0d866ced6c692c162cfe2f79baf7e5260dc71aff85b8fb5d30b47d76dbc` | official glibc build (Lean-blaster CI's) in a `linux/amd64` container via a `docker exec` wrapper |

On an arm64 host the linux-x64 build is emulated (slower): goals near the 20 s harness limit
can time out there that do not on the native build. cvc5 (`1.3.4`) is native; its path, version
and sha256 are recorded.
