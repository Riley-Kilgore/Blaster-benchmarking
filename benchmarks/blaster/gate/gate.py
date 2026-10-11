#!/usr/bin/env python3
"""Soundness gate for a Lean-blaster commit.

    gate.py run <commit> [--builds macos-arm64,linux-x64] [--source URL|PATH] [--only a,b,c,d]
    gate.py manifest --write          (re)write the protected-files manifest
    gate.py setup-z3                  install / verify every registered Z3 build

For each registered Z3 4.15.2 build, `run` reports PASS/FAIL for:
  (a) tests      Lean-blaster's own Tests/ at <commit>: every file elaborates with no error
  (b) known-false  no entry of the known-false set (climb + held-out) is Valid
  (c) manifest   protected files match the SHA-256 manifest
  (d) consistency  for every Valid result seen in this run (six suites, Lean-blaster tests,
                 known-false entries) the SMT assertions without the negated goal are not
                 unsat under Z3 (the build under test) or cvc5

Lean and Blaster always run natively; only the `z3` that Blaster spawns changes between builds.
The pinned harness checkout (.lake/packages/Blaster) is never modified: <commit> is checked out
in a git worktree under results/gate/ and loaded through LEAN_PATH and --load-dynlib.

Held-out details (MiniF2F, held-out Verina, held-out known-false) are written only to
heldout_report.json; the main report and summary carry counts for them.
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
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parent
REPO = GATE_DIR.parents[2]
sys.path.insert(0, str(REPO / "benchmarks" / "blaster"))
import blaster_bench as bb  # noqa: E402  (harness: goal discovery, rendering, lean runner)

BASELINE_COMMIT = "585c5fc1370196a03cfceec674f5a5ac2ed3c2f2"
BLASTER_URL = "https://github.com/input-output-hk/Lean-blaster"
KF_CLIMB = GATE_DIR / "known_false" / "climb.json"
DEFAULT_HELDOUT = REPO / "results" / "baseline" / "heldout" / "known_false_heldout.json"
DEFAULT_MANIFEST = REPO / "results" / "baseline" / "gate" / "PROTECTED.tsv"
SPLIT_HELDOUT = REPO / "results" / "baseline" / "split" / "heldout.tsv"
OUT_ROOT = REPO / "results" / "gate"
SUITES = ["NNG4", "STG4", "ITL4", "MiniF2F", "Verina", "UPLC"]
DUMP = "(dump-smt-lib: 1)"
HEADER = "Smt Query:"
CVC5_MODES = ["--mbqi", "--full-saturate-quant"]
CVC5_EXPECTED_VERSION = "1.3.4"
Z3_RELEASE = "https://github.com/Z3Prover/z3/releases/download/z3-4.15.2"

# Every Z3 build the gate knows. Hashes: archive as published on the release, binary as unpacked.
Z3_BUILDS = {
    "macos-arm64": {
        "kind": "native", "asset": "z3-4.15.2-arm64-osx-13.7.6.zip",
        "asset_sha256": "fdc797b046a8b1e030200d30c4c32724fc01be359c3ab88a47ce03655cf6efa4",
        "install_dir": REPO / ".tools" / "z3-4.15.2",
        "binary_sha256": "b8c06968b96f7b485382746cb8a956e131423ddd8be54ccdaed88b1466f5fc35",
        "note": "harness pin on this machine; Issue33.lean:74 gives the false Valid with it",
    },
    "linux-x64": {
        "kind": "docker", "platform": "linux/amd64", "image": "ubuntu:24.04",
        "asset": "z3-4.15.2-x64-glibc-2.39.zip",
        "asset_sha256": "85d2da1bf440fca3288874c2a06e23f96d09befcc21b5a7489fe0fa40444e685",
        "install_dir": REPO / ".tools" / "z3-4.15.2-x64-glibc-2.39",
        "binary_sha256": "4a84b0d866ced6c692c162cfe2f79baf7e5260dc71aff85b8fb5d30b47d76dbc",
        "note": "the build Lean-blaster CI uses; runs in a linux/amd64 container (emulated on arm64 hosts)",
    },
}


class GateError(Exception):
    """The gate itself could not run (environment, build, missing input)."""


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return bb.sha256_file(p)


def sh(cmd: list[str], **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise GateError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


# ---- Z3 builds -------------------------------------------------------------------------
class Z3Build:
    def __init__(self, name: str, out_root: Path):
        if name not in Z3_BUILDS:
            raise GateError(f"unknown Z3 build {name!r}; known: {', '.join(Z3_BUILDS)}")
        self.name, self.spec = name, Z3_BUILDS[name]
        self.binary = self.spec["install_dir"] / "bin" / "z3"
        self.container = f"blaster-gate-z3-{name}"
        self.wrapper_dir = out_root / "tools" / f"z3-{name}" / "bin"
        self.docker = shutil.which("docker")

    def install(self) -> None:
        if self.binary.exists():
            return
        log(f"installing Z3 build {self.name} from {self.spec['asset']}")
        with tempfile.TemporaryDirectory() as td:
            zp = Path(td) / self.spec["asset"]
            urllib.request.urlretrieve(f"{Z3_RELEASE}/{self.spec['asset']}", zp)
            if sha256_file(zp) != self.spec["asset_sha256"]:
                raise GateError(f"{self.spec['asset']}: sha256 mismatch")
            with zipfile.ZipFile(zp) as z:
                z.extractall(td)
            src = Path(td) / self.spec["asset"][:-4]
            self.spec["install_dir"].parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), self.spec["install_dir"])
        os.chmod(self.binary, 0o755)

    def prepare(self) -> dict:
        self.install()
        got = sha256_file(self.binary)
        if got != self.spec["binary_sha256"]:
            raise GateError(f"{self.binary}: sha256 {got}, expected {self.spec['binary_sha256']}")
        if self.spec["kind"] == "docker":
            if not self.docker:
                raise GateError("docker not found (needed for the linux-x64 Z3 build)")
            running = subprocess.run([self.docker, "inspect", "-f", "{{.State.Running}}", self.container],
                                     capture_output=True, text=True).stdout.strip()
            if running != "true":
                subprocess.run([self.docker, "rm", "-f", self.container], capture_output=True)
                sh([self.docker, "run", "-d", "--rm", "--platform", self.spec["platform"], "--name", self.container,
                    "-v", f"{self.spec['install_dir']}:/z3:ro", "-v", f"{REPO}:{REPO}:ro",
                    self.spec["image"], "sleep", "infinity"])
            self.wrapper_dir.mkdir(parents=True, exist_ok=True)
            w = self.wrapper_dir / "z3"
            # Blaster spawns `z3 -in -smt2`; the in-container `timeout` bounds any z3 orphaned
            # when the harness kills the lean process group.
            w.write_text(f'#!/bin/sh\nexec "{self.docker}" exec -i {self.container} '
                         f'timeout -s KILL 900 /z3/bin/z3 "$@"\n')
            os.chmod(w, 0o755)
            arch = sh([self.docker, "exec", self.container, "uname", "-m"]).strip()
        else:
            arch = platform.machine()
        version = subprocess.run([str(self.z3_on_path()), "-version"], capture_output=True, text=True).stdout.strip()
        if version != "Z3 version 4.15.2 - 64 bit":
            raise GateError(f"Z3 build {self.name} reports {version!r}")
        return {"name": self.name, "kind": self.spec["kind"], "binary": str(self.binary),
                "binary_sha256": got, "asset": self.spec["asset"], "asset_sha256": self.spec["asset_sha256"],
                "version": version, "arch": arch, "note": self.spec["note"]}

    def path_dir(self) -> Path:
        return self.wrapper_dir if self.spec["kind"] == "docker" else self.binary.parent

    def z3_on_path(self) -> Path:
        return self.path_dir() / "z3"

    def solve_cmd(self, file: Path, timeout_s: int) -> list[str]:
        if self.spec["kind"] == "docker":
            return [self.docker, "exec", self.container, "/z3/bin/z3", f"-T:{timeout_s}", str(file)]
        return [str(self.binary), f"-T:{timeout_s}", str(file)]

    def cleanup(self) -> None:
        """Kill any z3 left running in the container (no-op for native builds)."""
        if self.spec["kind"] == "docker":
            subprocess.run([self.docker, "exec", self.container, "sh", "-c",
                            'for p in /proc/[0-9]*; do [ "$(cat $p/comm 2>/dev/null)" = z3 ] && '
                            'kill -9 "${p#/proc/}" 2>/dev/null; done; true'], capture_output=True)

    def close(self) -> None:
        if self.spec["kind"] == "docker":
            subprocess.run([self.docker, "stop", "-t", "1", self.container], capture_output=True)


def cvc5_info() -> dict:
    p = shutil.which("cvc5", path=os.environ.get("PATH", ""))
    if not p:
        raise GateError("cvc5 not found on PATH")
    p = str(Path(p).resolve())
    v = subprocess.run([p, "--version"], capture_output=True, text=True).stdout.splitlines()[0].strip()
    if not re.match(rf"cvc5 (version )?{re.escape(CVC5_EXPECTED_VERSION)}\b", v):
        raise GateError(f"cvc5 at {p} reports {v!r}, expected {CVC5_EXPECTED_VERSION}")
    return {"path": p, "version": v, "sha256": sha256_file(Path(p))}


# ---- Lean-blaster at <commit> -----------------------------------------------------------
def setup_blaster(commit: str, source: str) -> tuple[str, Path]:
    src = OUT_ROOT / "src" / "Lean-blaster"
    if not src.exists():
        src.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "clone", "-q", source, str(src)])
    if subprocess.run(["git", "-C", str(src), "cat-file", "-e", f"{commit}^{{commit}}"]).returncode != 0:
        sh(["git", "-C", str(src), "fetch", "-q", source, "+refs/heads/*:refs/remotes/gate/*"])
        if subprocess.run(["git", "-C", str(src), "cat-file", "-e", f"{commit}^{{commit}}"]).returncode != 0:
            sh(["git", "-C", str(src), "fetch", "-q", source, commit])
    sha = sh(["git", "-C", str(src), "rev-parse", f"{commit}^{{commit}}"]).strip()
    wt = OUT_ROOT / sha[:7] / "Lean-blaster"
    if not wt.exists():
        wt.parent.mkdir(parents=True, exist_ok=True)
        sh(["git", "-C", str(src), "worktree", "add", "-q", "--detach", str(wt), sha])
    if sh(["git", "-C", str(wt), "rev-parse", "HEAD"]).strip() != sha:
        raise GateError(f"{wt} is not at {sha}")
    if sh(["git", "-C", str(wt), "status", "--porcelain"]).strip():
        raise GateError(f"{wt} has local modifications")
    tc = (wt / "lean-toolchain").read_text().strip()
    if tc != (REPO / "lean-toolchain").read_text().strip():
        raise GateError(f"Lean-blaster@{sha[:7]} uses toolchain {tc!r}; the benchmarks need "
                        f"{(REPO / 'lean-toolchain').read_text().strip()!r}")
    log(f"building Blaster @ {sha[:7]}")
    # `Blaster:shared` is the single libBlaster dylib passed to lean via --load-dynlib.
    r = subprocess.run(["lake", "build", "Blaster", "Blaster:shared"], cwd=wt, capture_output=True, text=True)
    if r.returncode != 0:
        raise GateError(f"lake build Blaster failed @ {sha[:7]}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return sha, wt


def blaster_dylib(wt: Path) -> Path:
    for n in bb.BLASTER_DYLIB_NAMES:
        p = wt / ".lake" / "build" / "lib" / n
        if p.exists():
            return p
    raise GateError(f"no Blaster shared library under {wt}/.lake/build/lib")


def make_ctx(sha: str, wt: Path, build: Z3Build) -> dict:
    ctx = bb.prepare_environment(build=False)       # lean, Mathlib env from the benchmark workspace
    env = dict(ctx["env"])
    pinned = str(bb.BLASTER_PKG / ".lake" / "build" / "lib" / "lean")
    lp = env["LEAN_PATH"].split(os.pathsep)
    if pinned not in lp:
        raise GateError(f"LEAN_PATH has no entry {pinned}")
    env["LEAN_PATH"] = os.pathsep.join(str(wt / ".lake" / "build" / "lib" / "lean") if p == pinned else p for p in lp)
    harness_z3 = str(Path(os.environ.get("BLASTER_Z3_DIR", bb.DEFAULT_Z3_DIR)).resolve())
    rest = [p for p in env["PATH"].split(os.pathsep) if p and str(Path(p).resolve()) != harness_z3]
    env["PATH"] = os.pathsep.join([str(build.path_dir())] + rest)
    resolved = shutil.which("z3", path=env["PATH"])
    if resolved is None or Path(resolved).resolve() != build.z3_on_path().resolve():
        raise GateError(f"z3 on PATH resolves to {resolved}, expected {build.z3_on_path()}")
    ctx.update(env=env, blaster_dylib=str(blaster_dylib(wt)), blaster_commit=sha)
    return ctx


# ---- Lean output helpers ---------------------------------------------------------------
def top_level_spans(lines: list[str]) -> list[tuple[int, int]]:
    """1-based inclusive line spans of top-level commands: a span starts at each unindented,
    non-comment line outside a block comment."""
    starts, depth = [], 0
    for i, l in enumerate(lines, 1):
        if depth == 0 and l and not l[0].isspace() and not l.startswith("--"):
            starts.append(i)
        depth = max(0, depth + l.count("/-") - l.count("-/"))
    return [(s, (starts[k + 1] - 1) if k + 1 < len(starts) else len(lines)) for k, s in enumerate(starts)]


def span_of(spans: list[tuple[int, int]], line: int) -> tuple[int, int] | None:
    return next((sp for sp in spans if sp[0] <= line <= sp[1]), None)


def msgs_in(msgs: list[dict], sp: tuple[int, int]) -> list[dict]:
    return [m for m in msgs if sp[0] <= (m.get("pos") or {}).get("line", -1) <= sp[1]]


def outcome(ms: list[dict], code: int | None) -> str:
    d = [(m.get("severity"), m.get("data", "")) for m in ms]
    if any(x.startswith("✅ Valid") or x.startswith("❌ Unexpected Valid") or (s == "warning" and "blasterProven" in x)
           for s, x in d):
        return "Valid"
    if any(x.startswith("✅ Expected Falsified") or x.startswith("❌ Falsified") or "Goal was falsified" in x for _, x in d):
        return "Falsified"
    if any(x.startswith("✅ Expected Undetermined") or x.startswith("⚠️ Undetermined") or x.startswith("unsolved goals")
           for _, x in d):
        return "Undetermined"
    if code is None:
        return "Timeout"
    return "Error" if any(s == "error" for s, _ in d) else "NoResult"


def queries_in(ms: list[dict]) -> list[str]:
    """SMT queries dumped by `(dump-smt-lib: 1)`: a message starting with `Smt Query:`, or (verbose)
    a stage message containing it, ending at the next `[Start]:`/`[End]:` line."""
    out = []
    for m in ms:
        if m.get("severity") != "information":
            continue
        for chunk in m.get("data", "").split(HEADER)[1:]:
            body = []
            for line in chunk.split("\n"):
                if line.startswith("[Start]:") or line.startswith("[End]:"):
                    break
                body.append(line)
            out.append("\n".join(body))
    return out


RESULT_PREFIXES = ("✅ Valid", "❌ Unexpected Valid", "✅ Expected Falsified", "❌ Falsified",
                   "✅ Expected Undetermined", "⚠️ Undetermined")


def n_results(ms: list[dict]) -> int:
    return sum(m.get("data", "").startswith(RESULT_PREFIXES) for m in ms)


def all_results_valid(ms: list[dict]) -> bool:
    d = [m.get("data", "") for m in ms]
    return (all(x.startswith(("✅ Valid", "❌ Unexpected Valid")) for x in d if x.startswith(RESULT_PREFIXES))
            and not any(x.startswith("unsolved goals") or "Goal was falsified" in x for x in d))


def run_lean_file(ctx: dict, f: Path, limit: float) -> tuple[list[dict], int | None, float, str]:
    out, err, code, elapsed = bb.run_lean(ctx, f, limit)
    msgs, raw = bb.parse_messages(out)
    return msgs, code, elapsed, (err.strip() or "\n".join(raw))[:2000]


TACTIC_RE = re.compile(r"(\bby\s+|^\s+|;\s*|<;>\s*)blaster\b(?![\w.'])", re.M)


def dump_variant(text: str) -> str:
    """Same file with `(dump-smt-lib: 1)` added to every #blaster command and blaster tactic call,
    and `#guard_msgs in` wrappers (with their expected-output docstrings) blanked. Line numbers are
    preserved so spans line up with the original."""
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.strip() == "#guard_msgs in":
            lines[i] = ""
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0 and lines[j].rstrip().endswith("-/"):
                k = j
                while k >= 0 and "/--" not in lines[k]:
                    k -= 1
                if k >= 0:
                    for t in range(k, j + 1):
                        lines[t] = ""
    out = []
    for l in lines:
        if l.lstrip().startswith("--"):
            out.append(l)
            continue
        l = re.sub(r"^#blaster\b", f"#blaster {DUMP}", l)
        l = TACTIC_RE.sub(lambda m: f"{m.group(1)}blaster {DUMP}", l)
        out.append(l)
    return "\n".join(out)


# ---- (c) protected-files manifest ------------------------------------------------------
def manifest_entries() -> list[tuple[str, str, str]]:
    tracked = sh(["git", "-C", str(REPO), "ls-files", "BlasterBenchmarks", "BlasterBenchmarks.lean", "benchmarks/blaster",
                  "lakefile.lean", "lake-manifest.json", "lean-toolchain"]).split("\n")
    files = {p for p in tracked if p}
    files |= {str(p.relative_to(REPO)) for p in GATE_DIR.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    for d in ["results/baseline/heldout", "results/baseline/split"]:
        files |= {str(p.relative_to(REPO)) for p in (REPO / d).glob("*") if p.is_file()}
    files.add("results/baseline/known_false.jsonl")
    out = [("repo", p, sha256_file(REPO / p)) for p in sorted(files)]
    tests = sh(["git", "-C", str(bb.BLASTER_PKG), "ls-tree", "-r", "--name-only", BASELINE_COMMIT, "--",
                "Tests", "Tests.lean"]).split()
    for p in sorted(tests):
        blob = subprocess.run(["git", "-C", str(bb.BLASTER_PKG), "show", f"{BASELINE_COMMIT}:{p}"],
                              capture_output=True, check=True).stdout
        out.append(("blaster-test", p, sha256_bytes(blob)))
    return out


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ents = manifest_entries()
    path.write_text("# kind\tpath\tsha256 (blaster-test: file at the Lean-blaster commit under test must match "
                    f"its content at {BASELINE_COMMIT[:7]})\n" + "".join(f"{k}\t{p}\t{h}\n" for k, p, h in ents))
    log(f"wrote {len(ents)} entries to {path} (sha256 {sha256_file(path)})")


def check_c(manifest: Path, wt: Path, sha: str) -> dict:
    if not manifest.exists():
        raise GateError(f"manifest {manifest} not found (gate.py manifest --write)")
    bad = []
    n = 0
    for line in manifest.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        kind, p, h = line.split("\t")
        n += 1
        if kind == "repo":
            f = REPO / p
            got = sha256_file(f) if f.exists() else None
        else:
            r = subprocess.run(["git", "-C", str(wt), "show", f"{sha}:{p}"], capture_output=True)
            got = sha256_bytes(r.stdout) if r.returncode == 0 else None
        if got != h:
            bad.append({"kind": kind, "path": p, "expected": h, "got": got or "MISSING"})
    return {"pass": not bad, "entries": n, "manifest": str(manifest.relative_to(REPO)),
            "manifest_sha256": sha256_file(manifest), "mismatches": bad}


# ---- (a) Lean-blaster tests ------------------------------------------------------------
def test_files(wt: Path) -> tuple[list[str], list[str]]:
    fs = [p for p in sh(["git", "-C", str(wt), "ls-files", "Tests", "Tests.lean"]).split() if p.endswith(".lean")]
    run, aggregators = [], []
    for f in sorted(fs):
        code = [l for l in (wt / f).read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("--")]
        (aggregators if code and all(l.startswith("import ") for l in code) else run).append(f)
    return run, aggregators


def build_test_imports(wt: Path, files: list[Path], build: Z3Build) -> None:
    mods = set()
    for f in files:
        mods |= set(re.findall(r"^import (Tests\S*)", f.read_text(encoding="utf-8"), re.M))
    if not mods:
        return
    env = dict(os.environ, PATH=f"{build.path_dir()}{os.pathsep}{os.environ['PATH']}")
    r = subprocess.run(["lake", "build", *sorted(mods)], cwd=wt, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise GateError(f"building test support modules failed:\n{r.stdout[-3000:]}")


def check_a(ctx: dict, wt: Path, build: Z3Build, jobs: int, work: Path) -> dict:
    files, aggregators = test_files(wt)
    build_test_imports(wt, [wt / f for f in files], build)

    def one(f: str) -> dict:
        msgs, code, elapsed, detail = run_lean_file(ctx, wt / f, 1800)
        lines = (wt / f).read_text(encoding="utf-8").split("\n")
        errs = [{"line": m["pos"]["line"], "message": m["data"][:500]} for m in msgs if m.get("severity") == "error"]
        valid_spans = [sp for sp in top_level_spans(lines) if outcome(msgs_in(msgs, sp), code) == "Valid"]
        return {"file": f, "exit": code, "time_s": round(elapsed, 2), "errors": errs,
                "checks_passed": sum("✅" in m.get("data", "") for m in msgs),
                "valid_spans": valid_spans, "detail": detail if code not in (0, 1) else ""}

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        res = list(pool.map(one, files))
    (work / "a_tests.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    failing = [r for r in res if r["errors"] or r["exit"] != 0]
    return {"pass": not failing, "files_run": len(files), "aggregators_skipped": len(aggregators),
            "checks_passed": sum(r["checks_passed"] for r in res),
            "failing": [{"file": r["file"], "exit": r["exit"], "errors": r["errors"][:5]} for r in failing],
            "_valid": [(r["file"], sp) for r in res for sp in r["valid_spans"]]}


# ---- (b) known-false set ---------------------------------------------------------------
def pinned_copy(sha_src: Path, path: str, dest_root: Path) -> Path:
    blob = sh(["git", "-C", str(sha_src), "show", f"{BASELINE_COMMIT}:{path}"])
    d = dest_root / path
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(blob, encoding="utf-8")
    return d


def refutation_ok(msgs: list[dict], name: str) -> tuple[bool, str]:
    ax = [m["data"] for m in msgs if m.get("severity") == "information" and m["data"].startswith("'") and
          (f"{name}' depends on axioms" in m["data"] or f"{name}' does not depend on any axioms" in m["data"])]
    if len(ax) != 1:
        return False, f"no `#print axioms` output for {name}"
    if "sorryAx" in ax[0] or "blasterProven" in ax[0]:
        return False, ax[0]
    return True, ax[0]


CASE_LIMIT_S = 120   # per case file (one Blaster call each); the harness allows 20 s per goal


def bracketed(text: str, start: int, open_: str, close: str) -> str | None:
    """Text between the bracket opening at or after `start` and its matching close."""
    i = text.find(open_, start)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        depth += text[j] == open_
        depth -= text[j] == close
        if depth == 0:
            return text[i + 1:j]
    return None


def refutation_variant(text: str) -> str:
    """The case file with its Blaster call removed: a `blaster` tactic line becomes `sorry`, a
    `#blaster` command is blanked (line numbers kept). Used to check the refutation without Blaster."""
    lines = text.split("\n")
    for s, e in top_level_spans(lines):
        if lines[s - 1].startswith("#blaster"):
            for k in range(s - 1, e):
                lines[k] = ""
    return "\n".join(re.sub(r"^(\s+)blaster\b.*$", r"\1sorry", l) for l in lines)


def case_statement_mismatch(text: str, refutation: str) -> str | None:
    """Command-form cases restate the `#blaster [S]` statement in `theorem <refutation> : ¬ (S)`;
    return a description if the two differ (modulo whitespace)."""
    m = re.search(r"^#blaster\b", text, re.M)
    if not m:
        return None
    norm = lambda s: " ".join((s or "").split())
    s1 = bracketed(text, m.end(), "[", "]")
    r = re.search(rf"theorem {re.escape(refutation)} : ¬ ", text)
    s2 = bracketed(text, r.end(), "(", ")") if r else None
    return None if s1 is not None and norm(s1) == norm(s2) else f"#blaster statement {norm(s1)!r} != refuted {norm(s2)!r}"


def heldout_goal_file(suite: str, goal_id: str, tactic: str, dest: Path) -> tuple[Path, tuple[int, int]]:
    goal = {g.goal_id: g for g in bb.discover_goals(bb.SUITES[suite])}[goal_id]
    text, ranges = bb.render_variant(goal.source.read_text(encoding="utf-8").splitlines(), {goal.theorem_idx: tactic})
    f = dest / f"{suite}__{goal_id.replace('/', '__')}.lean"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f, ranges[goal.theorem_idx]


def check_b(ctx: dict, wt: Path, build: Z3Build, heldout: Path, jobs: int, work: Path) -> tuple[dict, dict]:
    climb = json.loads(KF_CLIMB.read_text())
    if climb["baseline_blaster_commit"] != BASELINE_COMMIT:
        raise GateError("climb.json pins a different baseline commit")
    src = OUT_ROOT / "src" / "Lean-blaster"
    kf = work / "kf"
    files: dict[Path, list[dict]] = {}
    pinned = {p: pinned_copy(src, p, kf / "pinned") for p in sorted({e["file"] for e in climb["blaster_tests"]})}
    build_test_imports(wt, list(pinned.values()), build)
    for e in climb["blaster_tests"]:
        files.setdefault(pinned[e["file"]], []).append({**e, "kind": "blaster-test"})
    for e in climb["cases"]:
        files.setdefault(GATE_DIR / "known_false" / e["file"], []).append({**e, "kind": "case"})

    def run_file(f: Path, entries: list[dict]) -> list[dict]:
        is_case = entries[0]["kind"] == "case"
        msgs, code, elapsed, detail = run_lean_file(ctx, f, CASE_LIMIT_S if is_case else 1800)
        text = f.read_text(encoding="utf-8")
        lines = text.split("\n")
        spans = top_level_spans(lines)
        out = []
        for e in entries:
            line = e["line"] if e["kind"] == "blaster-test" else next(
                i for i, l in enumerate(lines, 1) if l.startswith(e["marker"]))
            sp = span_of(spans, line)
            ms = msgs_in(msgs, sp)
            r = {"id": e["id"], "kind": e["kind"], "file": str(f.relative_to(REPO)), "span": sp,
                 "status": outcome(ms, code), "time_s": round(elapsed, 2),
                 "messages": [m["data"][:300] for m in ms if m.get("severity") != "information"][:3]}
            if is_case:
                # Refutation checked on a copy with the Blaster call removed, in its own process.
                rv = work / "kf" / "refutations" / f.name
                rv.parent.mkdir(parents=True, exist_ok=True)
                rv.write_text(refutation_variant(text), encoding="utf-8")
                rmsgs, rcode, _, _ = run_lean_file(ctx, rv, 600)
                ok, why = refutation_ok(rmsgs, e["refutation"])
                errs = [m["data"][:200] for m in rmsgs if m.get("severity") == "error"]
                mismatch = case_statement_mismatch(text, e["refutation"])
                if errs or rcode != 0:
                    ok, why = False, f"refutation copy has errors: {errs[:2]} (exit {rcode})"
                if mismatch:
                    ok, why = False, mismatch
                r.update(refutation_ok=ok, refutation=why, upstream=e["upstream"])
            out.append(r)
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        res = [r for rs in pool.map(lambda kv: run_file(*kv), files.items()) for r in rs]

    # held-out: suite goals with the harness tactic, plus their refutation file
    ho = json.loads(heldout.read_text())
    ho_res = []
    for g in ho["suite_goals"]:
        f, rng = heldout_goal_file(g["suite"], g["goal_id"], bb.tactic_text(), work / "heldout" / "kf")
        msgs, code, _, detail = run_lean_file(ctx, f, bb.SUITES[g["suite"]].time_limit_s)
        build.cleanup()
        ho_res.append({"suite": g["suite"], "goal_id": g["goal_id"], "file": str(f.relative_to(REPO)), "span": rng,
                       "status": bb.classify(msgs, rng, code, "", [])[0]})
    rf = heldout.parent / ho["refutations"]
    msgs, code, _, _ = run_lean_file(ctx, rf, 600)
    ho_refs = [refutation_ok(msgs, f"{g['goal_id']}_false") for g in ho["suite_goals"]]

    climb_valid = [r for r in res if r["status"] == "Valid"]
    bad_refs = [r for r in res if r["kind"] == "case" and not r["refutation_ok"]]
    ho_valid = [r for r in ho_res if r["status"] == "Valid"]
    ho_bad_refs = sum(not ok for ok, _ in ho_refs)
    from collections import Counter
    summary = {
        "pass": not climb_valid and not ho_valid and not bad_refs and not ho_bad_refs and code == 0,
        "climb_entries": len(res), "climb_status": dict(Counter(r["status"] for r in res)),
        "climb_valid": [{"id": r["id"], "kind": r["kind"], "upstream": r.get("upstream")} for r in climb_valid],
        "case_refutations_ok": sum(r.get("refutation_ok", False) for r in res if r["kind"] == "case"),
        "case_refutation_failures": [{"id": r["id"], "why": r["refutation"]} for r in bad_refs],
        "heldout_entries": len(ho_res), "heldout_valid_count": len(ho_valid),
        "heldout_status": dict(Counter(r["status"] for r in ho_res)),
        "heldout_refutations_ok": len(ho_refs) - ho_bad_refs,
        "_entries": [(REPO / r["file"], tuple(r["span"]), r["id"], r["status"]) for r in res],
        "_heldout_valid": [(r["suite"], r["goal_id"]) for r in ho_valid],
    }
    (work / "b_known_false.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    heldout_detail = {"entries": ho_res, "refutations": [{"goal_id": g["goal_id"], "ok": ok, "axioms": why}
                                                         for g, (ok, why) in zip(ho["suite_goals"], ho_refs)]}
    return summary, heldout_detail


# ---- (d) consistency of every Valid ----------------------------------------------------
@dataclass
class ValidResult:
    origin: str                 # suite | test | known-false
    ident: str
    heldout: bool
    queries: list[str] = field(default_factory=list)   # one per Blaster call in the span
    note: str = ""              # why no query (optimizer-only, not reproduced, ambiguous)
    verdict: str = ""
    solver: dict = field(default_factory=dict)


def strip_negated_goal(query: str) -> tuple[str | None, str]:
    from_cmds = top_level_sexprs(query)
    heads = [c[1:].lstrip().split(None, 1)[0].rstrip(")") for c in from_cmds]
    neg = [i for i, c in enumerate(from_cmds) if heads[i] == "assert" and c[len("(assert"):].lstrip().startswith("(not")]
    if len(neg) != 1 or neg[0] != len(from_cmds) - 1:
        return None, f"unexpected query shape: {len(neg)} negated asserts, last={neg[-1] if neg else None}/{len(from_cmds) - 1}"
    return "\n".join(from_cmds[:-1]) + "\n(check-sat)\n", ""


def top_level_sexprs(text: str) -> list[str]:
    cmds, depth, start, i, n = [], 0, None, 0, len(text)
    while i < n:
        c = text[i]
        if c == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "|":
            i = text.index("|", i + 1) + 1
            continue
        if c == '"':
            i += 1
            while True:
                j = text.index('"', i)
                if j + 1 < n and text[j + 1] == '"':
                    i = j + 2
                    continue
                i = j + 1
                break
            continue
        if c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                cmds.append(text[start:i + 1])
        i += 1
    if depth != 0:
        raise ValueError("unbalanced parentheses")
    return cmds


def suite_valid_results(ctx: dict, build: Z3Build, work: Path, heldout_ids: set) -> tuple[list[ValidResult], dict]:
    from collections import Counter
    out, counts = [], {}
    for s in SUITES:
        suite = bb.SUITES[s]
        c = Counter()
        for g in bb.discover_goals(suite):
            text, ranges = bb.render_variant(g.source.read_text(encoding="utf-8").splitlines(),
                                             {g.theorem_idx: f"{bb.tactic_text()} {DUMP}"})
            f = work / "d" / "suites" / s / (g.goal_id.replace("/", "__") + ".lean")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
            msgs, code, _, _ = run_lean_file(ctx, f, suite.time_limit_s)
            build.cleanup()
            rng = ranges[g.theorem_idx]
            st = bb.classify(msgs, rng, code, "", [])[0]
            c[st] += 1
            if st != "Valid":
                continue
            qs = queries_in([m for m in msgs if bb.in_range(m, rng)])
            v = ValidResult("suite", f"{s}/{g.goal_id}", (s, g.goal_id) in heldout_ids)
            if len(qs) == 1:
                v.queries = qs
            else:
                v.note = "no SMT query (decided by the optimizer)" if not qs else f"{len(qs)} queries"
            out.append(v)
        counts[s] = dict(c)
        log(f"   (d) suites: {s} {dict(c)}")
    return out, counts


def span_valid_results(ctx: dict, files: dict[Path, tuple[set, dict | None]], origin: str, label,
                       work: Path, jobs: int, limit_s: float = 1800) -> list[ValidResult]:
    """Re-run each file with dump enabled (`dump_variant`, line numbers preserved). A span is checked
    if it was Valid in the original run (`orig_valid`) or is Valid in the dump run; `allowed` (span ->
    id), when given, restricts the dump-run spans considered (known-false: only the entries)."""

    def one(f: Path) -> list[ValidResult]:
        orig_valid, allowed = files[f]
        d = work / "d" / origin / (str(f.relative_to(REPO)) if f.is_relative_to(REPO) else f.name)
        d.parent.mkdir(parents=True, exist_ok=True)
        src = f.read_text(encoding="utf-8")
        d.write_text(dump_variant(src), encoding="utf-8")
        msgs, code, _, _ = run_lean_file(ctx, d, limit_s)
        lines = src.split("\n")
        res = []
        for sp in top_level_spans(lines):
            if allowed is not None and sp not in allowed:
                continue
            ms = msgs_in(msgs, sp)
            st = outcome(ms, code)
            if sp not in orig_valid and st != "Valid":
                continue
            v = ValidResult(origin, allowed[sp] if allowed else label(f, sp), False)
            qs = queries_in(ms)
            head = lines[sp[0] - 1].split()[0] if lines[sp[0] - 1].split() else ""
            if head in ("#kind", "#bmc"):
                v.verdict, v.note = "not-checked", f"{head} (state-machine) result; its queries are not dumped"
            elif st != "Valid":
                v.note = f"Valid in the original run but {st} when re-run with dump"
            elif qs and len(qs) == n_results(ms) and all_results_valid(ms):
                # e.g. `induction … <;> blaster`: one query per goal, every goal Valid
                v.queries = qs
                if sp not in orig_valid:
                    v.note = "Valid only visible in the dump run (e.g. under #guard_msgs)"
            else:
                v.note = ("no SMT query (decided by the optimizer)" if not qs else
                          f"{len(qs)} queries for {n_results(ms)} results in one span (cannot pair)")
            res.append(v)
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        return [v for vs in pool.map(one, list(files)) for v in vs]


def solve_one(build: Z3Build, cvc5: dict, axioms: Path, timeout_s: int) -> dict:
    def run(cmd: list[str]) -> str:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s + 60)
            lines = [l.strip() for l in (p.stdout + p.stderr).splitlines() if l.strip() and l.strip() != "success"]
            out = lines[-1] if lines else f"<no output, exit {p.returncode}>"
        except subprocess.TimeoutExpired:
            out = "timeout"
        if out in ("sat", "unsat", "unknown", "timeout"):
            return out
        return "timeout" if "interrupted by timeout" in out else f"error: {out[:200]}"

    t = axioms.read_text()
    if "AT_" in t:
        raise GateError(f"{axioms}: contains AT_, cvc5 renaming would collide")
    cv = axioms.with_suffix(".cvc5.smt2")
    cv.write_text("(set-logic ALL)\n" + re.sub(
        r"\(set-option :(print-success|auto_config|smt\.[\w.-]+|produce-proofs) [^)]*\)\n?", "", t).replace("@", "AT_"))
    r = {"z3": run(build.solve_cmd(axioms, timeout_s))}
    for m in CVC5_MODES:
        r["cvc5" + m] = run([cvc5["path"], m, f"--tlimit={timeout_s * 1000}", str(cv)])
    vals = list(r.values())
    r["verdict"] = ("conflict" if "sat" in vals and "unsat" in vals else "consistent" if "sat" in vals
                    else "vacuous" if "unsat" in vals else "undecided")
    if r["verdict"] in ("vacuous", "conflict"):
        r["unsat_core"] = unsat_core(build, axioms, timeout_s)
    return r


def unsat_core(build: Z3Build, axioms: Path, timeout_s: int) -> dict:
    cmds = top_level_sexprs(axioms.read_text())
    named, names = [], {}
    for c in cmds:
        h = c[1:].lstrip().split(None, 1)[0]
        if h == "assert":
            k = f"gate_a{len(names)}"
            q = re.search(r":qid (\S+?)\)", c)
            names[k] = q.group(1) if q else c[:120].replace("\n", " ")
            named.append(f"(assert (! {c[len('(assert'):-1].strip()} :named {k}))")
        elif h == "check-sat":
            continue
        else:
            named.append(c)
    f = axioms.with_suffix(".core.smt2")
    f.write_text("(set-option :produce-unsat-cores true)\n" + "\n".join(named) + "\n(check-sat)\n(get-unsat-core)\n")
    p = subprocess.run(build.solve_cmd(f, timeout_s), capture_output=True, text=True, timeout=timeout_s + 60)
    core = re.findall(r"gate_a\d+", p.stdout)
    qids = [re.sub(r"(_uniq)?\.\d+", ".N", names[k]) for k in core]
    is194 = any(q.endswith("_ext_fun") and "congr" not in q for q in qids) and any("_def_cstr" in q for q in qids)
    return {"core": qids, "cause": "#194 (guarded extensionality + unguarded lambda definition)" if is194 else "other"}


def check_d(build: Z3Build, cvc5: dict, valids: list[ValidResult], work: Path, timeout_s: int, jobs: int) -> dict:
    qdir = work / "d" / "queries"
    qdir.mkdir(parents=True, exist_ok=True)
    pending: dict[str, list[ValidResult]] = {}
    hashes: dict[int, list[str]] = {}
    for v in valids:
        if v.verdict:
            continue
        if not v.queries:
            v.verdict = "n/a" if v.note.startswith("no SMT query") else "undecided"
            continue
        stripped = [strip_negated_goal(q) for q in v.queries]
        bad = [why for ax, why in stripped if ax is None]
        if bad:
            v.verdict, v.note = "undecided", bad[0]
            continue
        hashes[id(v)] = []
        for ax, _ in stripped:
            h = sha256_bytes(ax.encode())[:16]
            (qdir / f"{h}.axioms.smt2").write_text(ax)
            pending.setdefault(h, []).append(v)
            hashes[id(v)].append(h)
    log(f"   (d) {len(valids)} Valid results, {sum(map(len, pending.values()))} with an SMT query, "
        f"{len(pending)} distinct axiom sets")
    solved: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(solve_one, build, cvc5, qdir / f"{h}.axioms.smt2", timeout_s): h for h in pending}
        for fut in concurrent.futures.as_completed(futs):
            h = futs[fut]
            solved[h] = {**fut.result(), "axioms_file": str((qdir / f"{h}.axioms.smt2").relative_to(REPO))}
    rank = {"vacuous": 0, "conflict": 0, "undecided": 1, "consistent": 2}
    for v in valids:
        if id(v) in hashes:   # worst verdict over the span's queries
            r = min((solved[h] for h in hashes[id(v)]), key=lambda r: rank[r["verdict"]])
            v.verdict, v.solver = r["verdict"], r
            if len(hashes[id(v)]) > 1:
                v.note = (v.note + "; " if v.note else "") + f"{len(hashes[id(v)])} queries, worst verdict shown"
    from collections import Counter

    def row(v: ValidResult) -> dict:
        return {"origin": v.origin, "id": v.ident, "verdict": v.verdict, "note": v.note,
                **{k: v.solver.get(k) for k in ("z3", "cvc5--mbqi", "cvc5--full-saturate-quant", "unsat_core", "axioms_file")
                   if k in v.solver}}

    vis = [v for v in valids if not v.heldout]
    hid = [v for v in valids if v.heldout]
    (work / "d_consistency.jsonl").write_text("".join(json.dumps(row(v), ensure_ascii=False) + "\n" for v in vis))
    failing = [v for v in valids if v.verdict in ("vacuous", "conflict")]
    return {"pass": not failing, "valid_results": len(valids),
            "by_verdict": dict(Counter(v.verdict for v in valids)),
            "by_origin": {o: dict(Counter(v.verdict for v in valids if v.origin == o)) for o in ("suite", "test", "known-false")},
            "failing": [row(v) for v in failing if not v.heldout],
            "failing_heldout_count": sum(v.heldout for v in failing),
            "undecided": [row(v) for v in vis if v.verdict == "undecided"],
            "undecided_heldout_count": sum(v.verdict == "undecided" for v in hid),
            "_heldout_rows": [row(v) for v in hid]}


# ---- driver ----------------------------------------------------------------------------
def heldout_suite_ids() -> set:
    ids = set()
    if SPLIT_HELDOUT.exists():
        for l in SPLIT_HELDOUT.read_text().splitlines():
            if l.strip():
                s, g = l.split("\t")
                ids.add((s, g))
    return ids


def run_build(sha: str, wt: Path, build: Z3Build, cvc5: dict, args, out: Path) -> tuple[dict, dict]:
    work = out / build.name
    work.mkdir(parents=True, exist_ok=True)
    info = build.prepare()
    ctx = make_ctx(sha, wt, build)
    log(f"== build {build.name}: {info['binary_sha256'][:12]} ({info['arch']})")
    rep: dict = {"z3_build": info, "checks": {}}
    ho: dict = {}
    only = set(args.only.split(","))
    t0 = time.monotonic()
    a = b = None
    if "a" in only or "d" in only:
        log("   (a) Lean-blaster tests")
        a = check_a(ctx, wt, build, args.jobs, work)
        build.cleanup()
    if "b" in only or "d" in only:
        log("   (b) known-false set")
        b, ho["known_false"] = check_b(ctx, wt, build, Path(args.heldout), args.jobs, work)
        build.cleanup()
    if "c" in only:
        rep["checks"]["c_manifest"] = check_c(Path(args.manifest), wt, sha)
    if "d" in only:
        log("   (d) consistency: re-running suites with dump")
        valids, suite_counts = suite_valid_results(ctx, build, work, heldout_suite_ids())
        tests: dict[Path, tuple[set, None]] = {}
        for f in test_files(wt)[0]:
            t = (wt / f).read_text(encoding="utf-8")
            ov = {tuple(sp) for g, sp in a["_valid"] if g == f}
            if ov or re.search(r"^#blaster\b", t, re.M) or TACTIC_RE.search(t):
                tests[wt / f] = (ov, None)
        log(f"   (d) re-running {len(tests)} Lean-blaster test files with dump")
        valids += span_valid_results(ctx, tests, "test", lambda f, sp: f"{f.relative_to(wt)}:{sp[0]}", work, args.jobs)
        kf: dict[Path, tuple[set, dict]] = {}
        for f, sp, ident, st in b["_entries"]:
            ov, allowed = kf.setdefault(f, (set(), {}))
            allowed[sp] = ident
            if st == "Valid":
                ov.add(sp)
        # case files: the same per-file limit as in (b); pinned test files: the test limit
        vs = []
        for group, lim in (({f: v for f, v in kf.items() if f.is_relative_to(GATE_DIR)}, CASE_LIMIT_S),
                           ({f: v for f, v in kf.items() if not f.is_relative_to(GATE_DIR)}, 1800)):
            vs += span_valid_results(ctx, group, "known-false", None, work, args.jobs, lim)
        for (s, g) in b["_heldout_valid"]:
            f, rng = heldout_goal_file(s, g, f"{bb.tactic_text()} {DUMP}", work / "heldout" / "d")
            msgs, code, _, _ = run_lean_file(ctx, f, bb.SUITES[s].time_limit_s)
            build.cleanup()
            qs = queries_in([m for m in msgs if bb.in_range(m, rng)])
            v = ValidResult("known-false", f"{s}/{g}", True)
            if bb.classify(msgs, rng, code, "", [])[0] != "Valid":
                v.note = "not Valid when re-run with dump"
            elif len(qs) == 1:
                v.queries = qs
            else:
                v.note = "no SMT query (decided by the optimizer)" if not qs else f"{len(qs)} queries"
            vs.append(v)
        build.cleanup()
        valids += vs
        d = check_d(build, cvc5, valids, work, args.solver_timeout, args.jobs)
        d["suite_status_counts"] = suite_counts
        ho["consistency"] = d.pop("_heldout_rows")
        rep["checks"]["d_consistency"] = d
    if a is not None and "a" in only:
        a.pop("_valid")
        rep["checks"]["a_tests"] = a
    if b is not None and "b" in only:
        b.pop("_entries")
        b.pop("_heldout_valid")
        rep["checks"]["b_known_false"] = b
    rep["pass"] = all(c["pass"] for c in rep["checks"].values())
    rep["elapsed_s"] = round(time.monotonic() - t0, 1)
    (work / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n")
    (work / "heldout_report.json").write_text(json.dumps(ho, indent=1, ensure_ascii=False) + "\n")
    return rep, ho


def summary_md(sha: str, reports: dict, cvc5: dict) -> str:
    L = [f"# Gate: Lean-blaster {sha}", "", f"cvc5: {cvc5['version']} sha256 {cvc5['sha256']}", ""]
    L.append("| check | " + " | ".join(reports) + " |")
    L.append("|---|" + "---|" * len(reports))
    names = {"a_tests": "(a) tests", "b_known_false": "(b) known-false", "c_manifest": "(c) manifest",
             "d_consistency": "(d) consistency"}
    for k, label in names.items():
        L.append(f"| {label} | " + " | ".join(
            ("PASS" if r["checks"][k]["pass"] else "**FAIL**") if k in r["checks"] else "-" for r in reports.values()) + " |")
    L.append("| **gate** | " + " | ".join("PASS" if r["pass"] else "**FAIL**" for r in reports.values()) + " |")
    for name, r in reports.items():
        z = r["z3_build"]
        L += ["", f"## {name}: {z['version']} ({z['arch']}, {z['asset']}), binary sha256 `{z['binary_sha256']}`", ""]
        c = r["checks"]
        if "a_tests" in c:
            a = c["a_tests"]
            L.append(f"- (a) {a['files_run']} test files, {a['checks_passed']} ✅ checks; failing files: "
                     + (", ".join(f"`{x['file']}` ({x['errors'][0]['message'][:60] if x['errors'] else 'exit ' + str(x['exit'])})"
                                  for x in a["failing"]) or "none"))
        if "b_known_false" in c:
            b = c["b_known_false"]
            L.append(f"- (b) climb {b['climb_entries']}: {b['climb_status']}; Valid: "
                     + (", ".join(f"`{x['id']}`" for x in b["climb_valid"]) or "none")
                     + f"; held-out {b['heldout_entries']}: Valid {b['heldout_valid_count']}")
        if "c_manifest" in c:
            m = c["c_manifest"]
            L.append(f"- (c) {m['entries']} entries, {len(m['mismatches'])} mismatches (manifest sha256 `{m['manifest_sha256'][:16]}…`)")
        if "d_consistency" in c:
            d = c["d_consistency"]
            L.append(f"- (d) {d['valid_results']} Valid results: {d['by_verdict']}; by origin {d['by_origin']}")
            for x in d["failing"]:
                L.append(f"  - **{x['verdict']}** {x['origin']} `{x['id']}`: z3={x.get('z3')} "
                         f"cvc5 mbqi={x.get('cvc5--mbqi')} fsq={x.get('cvc5--full-saturate-quant')}; "
                         f"cause: {(x.get('unsat_core') or {}).get('cause')}")
            if d["failing_heldout_count"]:
                L.append(f"  - held-out failing: {d['failing_heldout_count']} (see heldout_report.json)")
            for x in d["undecided"]:
                L.append(f"  - undecided {x['origin']} `{x['id']}`: {x['note'] or 'no solver decided'}")
            if d["undecided_heldout_count"]:
                L.append(f"  - held-out undecided: {d['undecided_heldout_count']} (see heldout_report.json)")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("commit")
    r.add_argument("--builds", default=",".join(Z3_BUILDS))
    r.add_argument("--source", default=BLASTER_URL, help="Lean-blaster git URL or local repo to fetch <commit> from")
    r.add_argument("--only", default="a,b,c,d")
    r.add_argument("--heldout", default=str(DEFAULT_HELDOUT))
    r.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--solver-timeout", type=int, default=120, help="seconds per solver call in (d) (harness: 20 s per goal)")
    m = sub.add_parser("manifest")
    m.add_argument("--write", action="store_true")
    m.add_argument("--path", default=str(DEFAULT_MANIFEST))
    sub.add_parser("setup-z3")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "manifest":
            if a.write:
                write_manifest(Path(a.path))
            else:
                print("\n".join(f"{k}\t{p}\t{h}" for k, p, h in manifest_entries()))
            return 0
        if a.cmd == "setup-z3":
            for n in Z3_BUILDS:
                b = Z3Build(n, OUT_ROOT)
                print(json.dumps(b.prepare()))
                b.close()
            return 0
        cvc5 = cvc5_info()
        sha, wt = setup_blaster(a.commit, a.source)
        out = OUT_ROOT / sha[:7]
        reports, builds = {}, [Z3Build(n, OUT_ROOT) for n in a.builds.split(",")]
        try:
            for b in builds:
                reports[b.name], _ = run_build(sha, wt, b, cvc5, a, out)
        finally:
            for b in builds:
                b.close()
        overall = {"blaster_commit": sha, "pass": all(r["pass"] for r in reports.values()),
                   "builds": {n: {"pass": r["pass"], **{k: v["pass"] for k, v in r["checks"].items()}}
                              for n, r in reports.items()},
                   "cvc5": cvc5, "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (out / "gate.json").write_text(json.dumps(overall, indent=1) + "\n")
        (out / "summary.md").write_text(summary_md(sha, reports, cvc5))
        print((out / "summary.md").read_text())
        return 0 if overall["pass"] else 1
    except GateError as e:
        print(f"GATE ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
