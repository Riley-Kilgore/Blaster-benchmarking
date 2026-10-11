#!/usr/bin/env python3
"""Blaster baseline harness: run the `blaster` tactic on every goal of the
benchmark suites and write one JSON line per goal.

    blaster_bench.py check              verify the pinned environment, run nothing
    blaster_bench.py suite <NAME> ...   run one suite (NNG4 STG4 ITL4 Verina UPLC)
    blaster_bench.py all                run all six suites

Each goal is run in its own `lean` process on a copy of its source file in which
only that goal's proof is replaced by `blaster (verbose: 1) (random-seed: SEED)`;
every other line of the file is left untouched. Goal files are never modified.

The run aborts before doing any work if Lean, the Blaster commit, or Z3 differ
from the pinned versions below.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---- pinned environment ------------------------------------------------------
EXPECTED_LEAN_VERSION = "4.24.0"
EXPECTED_BLASTER_COMMIT = "585c5fc1370196a03cfceec674f5a5ac2ed3c2f2"
EXPECTED_Z3_VERSION = "4.15.2"
# Blaster maps `(random-seed: 0)` to "no seed", so the fixed seed must be non-zero.
RANDOM_SEED = 42
DEFAULT_Z3_DIR = REPO_ROOT / ".tools" / f"z3-{EXPECTED_Z3_VERSION}" / "bin"
BLASTER_PKG = REPO_ROOT / ".lake" / "packages" / "Blaster"
BLASTER_DYLIB_NAMES = ("libBlaster.dylib", "libBlaster.so")

STATUSES = ("Valid", "Falsified", "Undetermined", "Error", "Timeout")


@dataclass(frozen=True)
class Suite:
    name: str
    paths: tuple[str, ...]  # a single .lean file (mode "file") or task directories (mode "taskdir")
    mode: str               # "file": every `theorem` in the file is a goal
                            # "taskdir": each .lean file is one goal (its target theorem)
    time_limit_s: int
    target: str = ""        # taskdir only: regex the target theorem name must match


# Time limits match benchmarks/benchmark_config.sh.
SUITES = {
    s.name: s for s in [
        Suite("NNG4", ("BlasterBenchmarks/NNG4/NNG4.lean",), "file", 20),
        Suite("STG4", ("BlasterBenchmarks/STG4/STG4.lean",), "file", 20),
        Suite("ITL4", ("BlasterBenchmarks/ITL4/ITL4.lean",), "file", 20),
        # MiniF2F is a held-out suite: it is not on this branch (see README, "Held-out suites").
        Suite("Verina", ("BlasterBenchmarks/Verina",), "taskdir", 20, r"_spec_satisfied$"),
        Suite("UPLC", ("BlasterBenchmarks/UPLC/Width", "BlasterBenchmarks/UPLC/Depth"), "taskdir", 90, r"."),
    ]
}


class HarnessError(Exception):
    """Environment or harness problem: the run must not proceed."""


# ---- goal discovery and proof replacement ------------------------------------
THEOREM_RE = re.compile(r"^(\s*)theorem\s+([^\s:({]+)")
BY_RE = re.compile(r":=\s*by\b")


@dataclass
class Goal:
    suite: str
    goal_id: str
    source: Path       # original file (never written)
    theorem: str       # theorem name inside `source`
    theorem_idx: int   # 0-based line index of the `theorem` keyword in `source`


def natural_key(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def theorem_lines(lines: list[str]) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(lines):
        m = THEOREM_RE.match(line)
        if m:
            out.append((i, m.group(2)))
    return out


def discover_goals(suite: Suite) -> list[Goal]:
    goals: list[Goal] = []
    if suite.mode == "file":
        src = REPO_ROOT / suite.paths[0]
        lines = src.read_text(encoding="utf-8").splitlines()
        thms = theorem_lines(lines)
        names = [n for _, n in thms]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            raise HarnessError(f"{src}: duplicate theorem names {dups}")
        for idx, name in thms:
            goals.append(Goal(suite.name, name, src, name, idx))
        return goals

    target_re = re.compile(suite.target)
    for d in suite.paths:
        ddir = REPO_ROOT / d
        files = sorted(ddir.glob("*.lean"), key=lambda p: natural_key(p.name))
        if not files:
            raise HarnessError(f"no task files in {ddir}")
        for f in files:
            thms = [(i, n) for i, n in theorem_lines(f.read_text(encoding="utf-8").splitlines())
                    if target_re.search(n)]
            if len(thms) != 1:
                raise HarnessError(f"{f}: expected exactly one target theorem matching "
                                   f"/{suite.target}/, found {[n for _, n in thms]}")
            idx, name = thms[0]
            goal_id = f.stem if len(suite.paths) == 1 else f"{Path(d).name}/{f.stem}"
            goals.append(Goal(suite.name, goal_id, f, name, idx))
    return goals


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def proof_span(lines: list[str], thm_idx: int) -> tuple[int, int, int]:
    """Return (by_line, col, body_end) for the theorem starting at `thm_idx`:
    `by_line` holds the first `:= by` (any spacing), `col` is its column, and the proof body is
    lines (by_line, body_end) exclusive, i.e. every following line that is blank
    or indented deeper than the `theorem` keyword."""
    base = indent_of(lines[thm_idx])
    by_line = None
    for j in range(thm_idx, len(lines)):
        if j > thm_idx and lines[j].strip() and indent_of(lines[j]) <= base:
            break  # reached the next declaration without finding `:= by`
        m = BY_RE.search(lines[j])
        if m:
            by_line, col = j, m.start()
            break
    if by_line is None:
        raise HarnessError(f"theorem at line {thm_idx + 1}: no `:= by` found")
    end = by_line + 1
    while end < len(lines) and (not lines[end].strip() or indent_of(lines[end]) > base):
        end += 1
    while end - 1 > by_line and not lines[end - 1].strip():
        end -= 1
    return by_line, col, end


def render_variant(lines: list[str], replacements: dict[int, str]) -> tuple[str, dict[int, tuple[int, int]]]:
    """Render `lines` with an `import Blaster` header and the proof of every theorem
    index in `replacements` swapped for the given tactic text. Returns the new file
    text and, per replaced theorem, its 1-based (first, last) line range in the new
    file (from the `theorem` keyword through the `:= by <tactic>` line)."""
    spans = {i: proof_span(lines, i) for i in replacements}
    out = ["import Blaster"]
    ranges: dict[int, tuple[int, int]] = {}
    i = 0
    while i < len(lines):
        if i in spans:
            by_line, col, end = spans[i]
            first = len(out) + 1
            out.extend(lines[i:by_line])
            out.append(lines[by_line][:col] + ":= by " + replacements[i])
            ranges[i] = (first, len(out))
            i = end
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out) + "\n", ranges


# ---- environment -------------------------------------------------------------
def run_capture(cmd: list[str], **kw) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if res.returncode != 0:
        raise HarnessError(f"command failed ({res.returncode}): {' '.join(cmd)}\n{res.stderr.strip()}")
    return res.stdout


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(path: Path) -> tuple[str, bool]:
    head = run_capture(["git", "-C", str(path), "rev-parse", "HEAD"]).strip()
    dirty = bool(run_capture(["git", "-C", str(path), "status", "--porcelain"]).strip())
    return head, dirty


def prepare_environment(build: bool = True) -> dict:
    """Verify every pinned component and return the run context. Raises HarnessError."""
    ctx: dict = {}

    # Lean toolchain
    toolchain = (REPO_ROOT / "lean-toolchain").read_text().strip()
    if toolchain != f"leanprover/lean4:v{EXPECTED_LEAN_VERSION}":
        raise HarnessError(f"lean-toolchain is {toolchain!r}, expected v{EXPECTED_LEAN_VERSION}")

    # Blaster: manifest pin, checkout, and local modifications
    manifest = json.loads((REPO_ROOT / "lake-manifest.json").read_text())
    pkgs = {p["name"]: p for p in manifest["packages"]}
    if "Blaster" not in pkgs:
        raise HarnessError("lake-manifest.json has no `Blaster` package")
    if pkgs["Blaster"]["rev"] != EXPECTED_BLASTER_COMMIT:
        raise HarnessError(f"lake-manifest.json pins Blaster at {pkgs['Blaster']['rev']}, "
                           f"expected {EXPECTED_BLASTER_COMMIT}")
    if build:
        # No-op when up to date; guarantees the native library matches the checkout.
        res = subprocess.run(["lake", "build", "Blaster"], cwd=REPO_ROOT, capture_output=True, text=True)
        if res.returncode != 0:
            raise HarnessError(f"`lake build Blaster` failed:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
    head, dirty = git_head(BLASTER_PKG)
    if head != EXPECTED_BLASTER_COMMIT:
        raise HarnessError(f"{BLASTER_PKG} is checked out at {head}, expected {EXPECTED_BLASTER_COMMIT} "
                           f"(run `lake update Blaster`?)")
    if dirty:
        raise HarnessError(f"{BLASTER_PKG} has local modifications; refusing to record a baseline")
    dylib = next((BLASTER_PKG / ".lake/build/lib" / n for n in BLASTER_DYLIB_NAMES
                  if (BLASTER_PKG / ".lake/build/lib" / n).exists()), None)
    if dylib is None:
        raise HarnessError("Blaster shared library not found; run `lake build Blaster`")
    ctx["blaster_commit"] = head
    ctx["blaster_dylib"] = str(dylib)
    ctx["mathlib_rev"] = pkgs.get("mathlib", {}).get("rev")

    # Lake environment, captured once so each goal runs `lean` directly.
    env_json = run_capture(["lake", "env", sys.executable, "-c",
                            "import os, json; print(json.dumps(dict(os.environ)))"], cwd=REPO_ROOT)
    env = json.loads(env_json.strip().splitlines()[-1])
    prefix = run_capture(["lake", "env", "lean", "--print-prefix"], cwd=REPO_ROOT).strip()
    lean_bin = Path(prefix) / "bin" / "lean"
    lean_version = run_capture([str(lean_bin), "--version"], env=env).strip()
    if f"version {EXPECTED_LEAN_VERSION}" not in lean_version:
        raise HarnessError(f"lean reports {lean_version!r}, expected {EXPECTED_LEAN_VERSION}")
    ctx["lean_bin"] = str(lean_bin)
    ctx["lean_version"] = lean_version

    # Z3: Blaster spawns the first `z3` on PATH and does not check its version, so the
    # harness puts the pinned binary first and verifies exactly what will be resolved.
    z3_dir = Path(os.environ.get("BLASTER_Z3_DIR", DEFAULT_Z3_DIR)).resolve()
    env["PATH"] = f"{z3_dir}{os.pathsep}{env.get('PATH', '')}"
    z3_resolved = shutil.which("z3", path=env["PATH"])
    if z3_resolved is None:
        raise HarnessError(f"no z3 found (expected {z3_dir}/z3); run benchmarks/blaster/install_z3.sh")
    z3_resolved = str(Path(z3_resolved).resolve())
    z3_version = subprocess.run([z3_resolved, "-version"], capture_output=True, text=True).stdout.strip()
    if z3_version != f"Z3 version {EXPECTED_Z3_VERSION} - 64 bit":
        raise HarnessError(f"z3 at {z3_resolved} reports {z3_version!r}, expected Z3 {EXPECTED_Z3_VERSION}; "
                           f"run benchmarks/blaster/install_z3.sh")
    ctx["z3_path"] = z3_resolved
    ctx["z3_version"] = z3_version
    ctx["z3_sha256"] = sha256_file(Path(z3_resolved))

    env["LC_ALL"] = "C"
    ctx["env"] = env
    return ctx


# ---- running and classifying one goal -----------------------------------------
STAGE_END_RE = re.compile(r"^\[End\]: (.+) \(([0-9.]+)s\)$", re.M)


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_lean(ctx: dict, file: Path, time_limit_s: float) -> tuple[str, str, int | None, float]:
    """Run lean on `file` in its own process group (so a timeout also kills z3)."""
    cmd = [ctx["lean_bin"], "--json", f"--load-dynlib={ctx['blaster_dylib']}", str(file)]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=ctx["env"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=time_limit_s)
        code: int | None = proc.returncode
    except subprocess.TimeoutExpired:
        kill_group(proc)
        out, err = proc.communicate()
        code = None
    elapsed = time.monotonic() - start
    kill_group(proc)  # reap any solver left behind by a finished lean
    return out, err, code, elapsed


def parse_messages(stdout: str) -> tuple[list[dict], list[str]]:
    msgs, raw = [], []
    for line in stdout.splitlines():
        if line.startswith("{"):
            try:
                msgs.append(json.loads(line))
                continue
            except json.JSONDecodeError:
                pass
        if line.strip():
            raw.append(line)
    return msgs, raw


def in_range(msg: dict, rng: tuple[int, int]) -> bool:
    pos = msg.get("pos") or {}
    return rng[0] <= pos.get("line", -1) <= rng[1]


def normalize_error(text: str) -> str:
    """Collapse an error message to a group key: first line, with quoted names,
    metavariable ids and numbers abstracted."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    first = re.sub(r"`[^`]*`", "`_`", first)
    first = re.sub(r"'[^']*'", "'_'", first)
    first = re.sub(r"\?[\w.]*\d+", "?m", first)
    first = re.sub(r"\d+", "N", first)
    first = re.sub(r"\s+", " ", first).strip()
    return first[:200]


def classify(msgs: list[dict], rng: tuple[int, int], code: int | None, stderr: str, raw: list[str]):
    """Return (status, error_group, error_message, stage_times)."""
    mine = [m for m in msgs if in_range(m, rng)]
    stages: dict[str, float] = {}
    for m in mine:
        if m.get("severity") == "information":
            for name, secs in STAGE_END_RE.findall(m.get("data", "")):
                stages[name] = round(stages.get(name, 0.0) + float(secs), 6)

    if code is None:
        return "Timeout", None, None, stages

    errors = [m["data"] for m in mine if m.get("severity") == "error"]
    if any("Goal was falsified" in e for e in errors):
        return "Falsified", None, None, stages
    other = [e for e in errors if not e.startswith("unsolved goals")]
    if other:
        return "Error", normalize_error(other[0]), other[0][:2000], stages
    if errors:
        return "Undetermined", None, None, stages
    if any(m.get("severity") == "warning" and "blasterProven" in m.get("data", "") for m in mine):
        return "Valid", None, None, stages

    # No Blaster outcome attributable to the goal: lean crashed, or failed elsewhere first.
    if code != 0:
        file_errors = [m["data"] for m in msgs if m.get("severity") == "error"]
        detail = file_errors[0] if file_errors else (stderr.strip() or "\n".join(raw).strip()
                                                       or f"lean exited with code {code}")
        return "Error", normalize_error(detail), detail[:2000], stages
    return "Error", "no blaster result reported for goal", None, stages


# ---- suite driver ----------------------------------------------------------
def tactic_text() -> str:
    return f"blaster (verbose: 1) (random-seed: {RANDOM_SEED})"


def compile_check(ctx: dict, suite: Suite, goals: list[Goal], work: Path) -> dict[str, str | None]:
    """Does each goal's statement elaborate with its proof replaced by `sorry`?
    Returns goal_id -> None (compiles) or the first error message."""
    result: dict[str, str | None] = {}
    by_source: dict[Path, list[Goal]] = {}
    for g in goals:
        by_source.setdefault(g.source, []).append(g)
    for src, gs in by_source.items():
        lines = src.read_text(encoding="utf-8").splitlines()
        text, ranges = render_variant(lines, {g.theorem_idx: "sorry" for g in gs})
        f = work / "compile_check" / f"{src.stem}.lean"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        out, err, code, _ = run_lean(ctx, f, max(120, suite.time_limit_s))
        msgs, raw = parse_messages(out)
        for g in gs:
            if code is None:
                result[g.goal_id] = "compile check timed out"
                continue
            errs = [m["data"] for m in msgs if m.get("severity") == "error" and in_range(m, ranges[g.theorem_idx])]
            if not errs and code != 0 and not any(m.get("severity") == "error" for m in msgs):
                errs = [err.strip() or "\n".join(raw) or f"lean exited with code {code}"]
            result[g.goal_id] = errs[0] if errs else None
    return result


def run_goal(ctx: dict, suite: Suite, goal: Goal, work: Path) -> dict:
    lines = goal.source.read_text(encoding="utf-8").splitlines()
    text, ranges = render_variant(lines, {goal.theorem_idx: tactic_text()})
    f = work / "goals" / (goal.goal_id.replace("/", "__") + ".lean")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    out, err, code, elapsed = run_lean(ctx, f, suite.time_limit_s)
    msgs, raw = parse_messages(out)
    status, group, message, stages = classify(msgs, ranges[goal.theorem_idx], code, err, raw)
    return {
        "suite": suite.name,
        "goal_id": goal.goal_id,
        "status": status,
        "error_group": group,
        "error_message": message,
        "stage_times_s": stages,
        "total_time_s": round(elapsed, 3),
        "time_limit_s": suite.time_limit_s,
        "blaster_commit": ctx["blaster_commit"],
        "random_seed": RANDOM_SEED,
        "source": str(goal.source.relative_to(REPO_ROOT)),
        "theorem": goal.theorem,
    }


def run_suite(ctx: dict, suite: Suite, out_dir: Path, jobs: int) -> dict[str, int]:
    goals = discover_goals(suite)
    work = out_dir / "work" / suite.name
    print(f"== {suite.name}: {len(goals)} goals, time limit {suite.time_limit_s}s, jobs {jobs}", file=sys.stderr)

    compiles = compile_check(ctx, suite, goals, work)
    bad = [g for g in goals if compiles[g.goal_id] is not None]
    if bad:
        print(f"   {len(bad)} goal statement(s) do not compile:", file=sys.stderr)
        for g in bad:
            print(f"     {g.goal_id}: {normalize_error(compiles[g.goal_id])}", file=sys.stderr)

    records: dict[str, dict] = {}

    def one(g: Goal) -> dict:
        rec = run_goal(ctx, suite, g, work)
        rec["statement_compiles"] = compiles[g.goal_id] is None
        return rec

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(one, g): g for g in goals}
        for n, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            rec = fut.result()
            records[rec["goal_id"]] = rec
            print(f"   [{n}/{len(goals)}] {rec['goal_id']}: {rec['status']} ({rec['total_time_s']}s)"
                  + (f"  {rec['error_group']}" if rec["error_group"] else ""), file=sys.stderr)

    out_file = out_dir / f"{suite.name}.jsonl"
    with open(out_file, "w", encoding="utf-8") as fh:
        for g in goals:  # source order, independent of completion order
            fh.write(json.dumps(records[g.goal_id], ensure_ascii=False, sort_keys=True) + "\n")

    counts = {s: 0 for s in STATUSES}
    for r in records.values():
        counts[r["status"]] += 1
    print(f"   {suite.name}: " + "  ".join(f"{s}={c}" for s, c in counts.items()), file=sys.stderr)
    return counts


def write_manifest(ctx: dict, out_dir: Path, suites: list[Suite], jobs: int, started: str,
                   counts: dict[str, dict[str, int]] | None) -> None:
    harness_head, harness_dirty = git_head(REPO_ROOT)
    manifest = {
        "started_utc": started,
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat() if counts is not None else None,
        "blaster_commit": ctx["blaster_commit"],
        "harness_commit": harness_head,
        "harness_dirty": harness_dirty,
        "lean_version": ctx["lean_version"],
        "mathlib_rev": ctx["mathlib_rev"],
        "z3_version": ctx["z3_version"],
        "z3_path": ctx["z3_path"],
        "z3_sha256": ctx["z3_sha256"],
        "random_seed": RANDOM_SEED,
        "tactic": tactic_text(),
        "jobs": jobs,
        "suites": {s.name: {"time_limit_s": s.time_limit_s, "paths": list(s.paths)} for s in suites},
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "counts": counts,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="verify the pinned environment and exit")
    for name in ("suite", "all"):
        p = sub.add_parser(name)
        if name == "suite":
            p.add_argument("names", nargs="+", choices=list(SUITES), metavar="SUITE",
                           help=" | ".join(SUITES))
        p.add_argument("--out", type=Path, help="output directory (default: results/<UTC time>-<blaster sha>)")
        p.add_argument("--jobs", type=int, default=1,
                       help="goals run concurrently (default 1; >1 perturbs timings and timeouts)")
    args = ap.parse_args(argv)

    try:
        ctx = prepare_environment()
    except HarnessError as e:
        print(f"ENVIRONMENT CHECK FAILED: {e}", file=sys.stderr)
        return 2
    print(f"Blaster {ctx['blaster_commit']} | {ctx['lean_version']} | {ctx['z3_version']} ({ctx['z3_path']}) "
          f"| seed {RANDOM_SEED}", file=sys.stderr)
    if args.cmd == "check":
        return 0

    suites = list(SUITES.values()) if args.cmd == "all" else [SUITES[n] for n in args.names]
    started = datetime.datetime.now(datetime.timezone.utc)
    out_dir = args.out or REPO_ROOT / "results" / f"{started:%Y%m%dT%H%M%SZ}-{ctx['blaster_commit'][:7]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(ctx, out_dir, suites, args.jobs, started.isoformat(), None)

    counts: dict[str, dict[str, int]] = {}
    try:
        for s in suites:
            counts[s.name] = run_suite(ctx, s, out_dir, args.jobs)
    except HarnessError as e:
        print(f"HARNESS ERROR: {e}", file=sys.stderr)
        return 2
    write_manifest(ctx, out_dir, suites, args.jobs, started.isoformat(), counts)
    print(f"Results: {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
