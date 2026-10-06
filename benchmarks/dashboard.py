#!/usr/bin/env python3
"""
Blaster Benchmark Dashboard
Generates a self-contained interactive HTML report from benchmark CSV results.

Usage:
    python3 dashboard.py [results_dir] [output_html]

Defaults:
    results_dir  = benchmark_results
    output_html  = benchmark_results/dashboard.html
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Color palette ────────────────────────────────────────────────────────────

TACTIC_COLORS = {
    "blaster":                   "#2EC4F0",
    "blaster (only-optimize: 1)":"#1760B0",
    "smt":                       "#FF5C8D",
    "smt +model":                "#C2185B",
    "auto":                      "#69E06A",
    "aesop":                     "#FF9F1C",
    "hammer":                    "#B24BF3",
    "omega":                     "#F44336",
    "grind":                     "#00BFA5",
    "simp":                      "#FFEB3B",
    "decide":                    "#8BC34A",
    "decide +native":            "#FF6D00",
    "canonical":                 "#90A4AE",
    "rfl":                       "#A1887F",
}

TACTIC_DASHES = {
    "blaster":                   [],
    "blaster (only-optimize: 1)":[8, 4],
    "smt":                       [],
    "smt +model":                [8, 4],
    "auto":                      [],
    "aesop":                     [4, 4],
    "hammer":                    [12, 4, 4, 4],
    "omega":                     [4, 4],
    "grind":                     [12, 4],
    "simp":                      [2, 4],
    "decide":                    [],
    "decide +native":            [8, 4],
    "canonical":                 [4, 4],
    "rfl":                       [2, 2],
}

STATUS_COLORS = {
    "OK":      "#4ade80",
    "TIMEOUT": "#fbbf24",
    "FAIL":    "#f87171",
}

DEFAULT_COLOR = "#90A4AE"


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_tactics(rows: list[dict]) -> list[str]:
    if not rows:
        return []
    return [k[: -len("_status")] for k in rows[0] if k.endswith("_status")]


def get_time_ms(row: dict, tactic: str) -> float | None:
    status = row.get(f"{tactic}_status", "FAIL")
    raw = row.get(f"{tactic}_time", "")
    if status == "OK" and str(raw).lstrip("-").isdigit():
        return float(raw)
    return None


# ── Stats computation ─────────────────────────────────────────────────────────

def bench_stats(rows: list[dict], tactics: list[str]) -> dict:
    stats = {}
    for t in tactics:
        times = [get_time_ms(r, t) for r in rows]
        ok = [x for x in times if x is not None]
        to = sum(1 for r in rows if r.get(f"{t}_status") == "TIMEOUT")
        fa = sum(1 for r in rows if r.get(f"{t}_status") == "FAIL")
        stats[t] = {
            "ok": len(ok),
            "timeout": to,
            "fail": fa,
            "total": len(rows),
            "avg_ms": sum(ok) / len(ok) if ok else None,
            "median_ms": sorted(ok)[len(ok) // 2] if ok else None,
            "times_s": sorted(x / 1000 for x in ok),
        }
    return stats


def to_js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# ── HTML generation ───────────────────────────────────────────────────────────

def make_dashboard(results_dir: str, output_html: str) -> None:
    results_path = Path(results_dir)
    csv_files = sorted(results_path.glob("*_results.csv"))

    if not csv_files:
        print(f"No *_results.csv files found in {results_dir}", file=sys.stderr)
        sys.exit(1)

    benchmarks = []
    for csv_path in csv_files:
        name = csv_path.stem.replace("_results", "")
        rows = load_csv(str(csv_path))
        tactics = get_tactics(rows)
        stats = bench_stats(rows, tactics)
        benchmarks.append({"name": name, "rows": rows, "tactics": tactics, "stats": stats})

    js_benchmarks = []
    for b in benchmarks:
        rows, tactics, stats = b["rows"], b["tactics"], b["stats"]
        theorem_names = [r.get("Theorem", f"thm_{i}") for i, r in enumerate(rows)]
        heatmap = {t: [r.get(f"{t}_status", "FAIL") for r in rows] for t in tactics}
        cactus = {t: stats[t]["times_s"] for t in tactics}
        bar = {
            t: {
                "ok": stats[t]["ok"],
                "timeout": stats[t]["timeout"],
                "fail": stats[t]["fail"],
                "total": stats[t]["total"],
                "avg_ms": stats[t]["avg_ms"],
                "median_ms": stats[t]["median_ms"],
            }
            for t in tactics
        }
        colors = {t: TACTIC_COLORS.get(t, DEFAULT_COLOR) for t in tactics}
        dashes = {t: TACTIC_DASHES.get(t, []) for t in tactics}
        js_benchmarks.append({
            "name": b["name"],
            "theorem_names": theorem_names,
            "tactics": tactics,
            "heatmap": heatmap,
            "cactus": cactus,
            "bar": bar,
            "colors": colors,
            "dashes": dashes,
        })

    payload = to_js(js_benchmarks)
    status_colors = to_js(STATUS_COLORS)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Blaster · Benchmark Results</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

:root{{
  --bg:      #0d0908;
  --bg2:     #120a07;
  --bg3:     #180d0a;
  --ink:     #b84032;
  --ink2:    #8f2d20;
  --green:   #4ade80;
  --red:     #f87171;
  --amber:   #fbbf24;
  --sky:     #7dd3fc;
  --text:    #dde1ef;
  --dim:     #7a8099;
  --border:  rgba(255,255,255,0.04);
  --border2: rgba(255,255,255,0.08);
  --ease-out: cubic-bezier(.16,1,.3,1);
}}

html{{scroll-behavior:smooth}}
body{{
  font-family:'IBM Plex Sans',sans-serif;
  font-size:17px;
  background:var(--bg);
  color:var(--text);
  line-height:1.65;
  overflow-x:hidden;
}}

.page{{display:none}}
.page.active{{display:block}}

::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:rgba(255,255,255,0.1);border-radius:3px}}

/* ── Nav ── */
nav{{
  position:fixed;top:0;left:0;right:0;z-index:100;
  padding:13px 48px;
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(13,9,8,0.90);backdrop-filter:blur(18px);
  border-bottom:1px solid var(--border);
}}
.nav-logo{{
  display:flex;align-items:center;gap:10px;
  font-family:'IBM Plex Sans',sans-serif;font-weight:700;font-size:1.2rem;
  color:var(--text);text-decoration:none;letter-spacing:0.01em;cursor:pointer;
}}
.nav-links{{display:flex;gap:28px;align-items:center}}
.nav-links a{{
  color:var(--dim);text-decoration:none;font-size:0.95rem;font-weight:500;
  transition:color 0.2s;
}}
.nav-links a:hover{{color:var(--text)}}
.nav-gh{{
  display:flex;align-items:center;gap:6px;
  padding:6px 14px;border-radius:5px;font-weight:600;font-size:0.82rem;
  font-family:'IBM Plex Mono',monospace;
  background:transparent;color:var(--dim);text-decoration:none;
  border:1px solid var(--border);transition:all 0.2s;
}}
.nav-gh:hover{{border-color:rgba(184,64,50,0.25);color:var(--text)}}
#nav-breadcrumb{{display:none;align-items:center;gap:10px}}
#nav-breadcrumb .back{{
  display:flex;align-items:center;gap:6px;color:var(--ink);
  cursor:pointer;font-weight:500;font-family:'IBM Plex Mono',monospace;
  font-size:0.8rem;transition:opacity .15s;
}}
#nav-breadcrumb .back:hover{{opacity:.7}}
#nav-breadcrumb .sep{{color:var(--dim);opacity:0.4}}
#nav-breadcrumb .crumb{{color:var(--text);font-weight:600;font-family:'IBM Plex Mono',monospace;font-size:0.8rem}}

/* ── Hero ── */
.hero{{
  min-height:100vh;display:flex;flex-direction:column;
  align-items:flex-start;justify-content:center;
  padding:130px 48px 80px;max-width:900px;margin:0 auto;
}}
.hero-eyebrow{{
  font-family:'IBM Plex Mono',monospace;font-size:0.8rem;font-weight:600;
  letter-spacing:0.1em;text-transform:uppercase;color:var(--ink);
  margin-bottom:20px;opacity:0.85;animation:rise 0.7s ease-out both;
}}
.hero h1{{
  font-family:'IBM Plex Sans',sans-serif;
  font-size:clamp(3.2rem,7.5vw,6.5rem);font-weight:700;line-height:1.0;
  letter-spacing:-0.01em;animation:rise 0.7s ease-out 0.1s both;
}}
.hero h1 .word-prove{{
  background:linear-gradient(110deg,#8f2d20 0%,#b84032 45%,#c96040 100%);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
}}
.hero-sub{{
  font-size:1.15rem;color:var(--dim);max-width:560px;
  margin-top:22px;line-height:1.75;font-weight:400;
  animation:rise 0.7s ease-out 0.2s both;
}}
.hero-actions{{
  margin-top:30px;display:flex;gap:12px;flex-wrap:wrap;
  animation:rise 0.7s ease-out 0.3s both;
}}
.btn{{
  padding:9px 22px;border-radius:4px;font-weight:600;font-size:0.82rem;
  font-family:'IBM Plex Mono',monospace;letter-spacing:0.02em;
  text-decoration:none;display:inline-flex;align-items:center;gap:7px;
  transition:all 0.2s;border:none;cursor:pointer;
}}
.btn-ink{{background:var(--ink);color:#fff}}
.btn-ink:hover{{background:#c96040}}
.btn-ghost{{background:transparent;color:var(--dim);border:1px solid var(--border)}}
.btn-ghost:hover{{color:var(--text);border-color:rgba(255,255,255,0.10)}}
.hero-demo{{
  margin-top:52px;width:100%;max-width:580px;
  animation:rise 0.7s ease-out 0.4s both;
}}
.demo-pane{{background:var(--bg2);border:1px solid var(--border);border-radius:3px;overflow:hidden}}
.demo-pane-bar{{
  padding:8px 14px;display:flex;align-items:center;gap:7px;
  border-bottom:1px solid var(--border);
}}
.demo-pane-bar .dot{{width:8px;height:8px;border-radius:50%}}
.demo-pane-bar .dot.r{{background:rgba(248,113,113,0.5)}}
.demo-pane-bar .dot.y{{background:rgba(251,191,36,0.5)}}
.demo-pane-bar .dot.g{{background:rgba(74,222,128,0.5)}}
.demo-pane-bar .label{{margin-left:6px;font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim)}}
.demo-pane pre{{padding:18px 20px;font-family:'IBM Plex Mono',monospace;font-size:0.88rem;line-height:1.8;overflow-x:auto}}
.c-kw{{color:#a78bfa}}.c-fn{{color:var(--ink)}}.c-ty{{color:var(--sky)}}
.c-cm{{color:#3e4459;font-style:italic}}.c-ok{{color:var(--green)}}.c-err{{color:#f87171}}
.c-dim{{color:#333b52}}
.c-cursor{{display:inline-block;width:2px;height:1.1em;background:var(--ink);vertical-align:text-bottom;margin-left:1px;animation:blink 1s step-end infinite}}
@keyframes blink{{50%{{opacity:0}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}

/* ── Shared section styles ── */
.wrap{{max-width:1080px;margin:0 auto;padding:96px 48px}}
.section-tag{{
  font-family:'IBM Plex Mono',monospace;font-size:0.72rem;font-weight:600;
  letter-spacing:0.14em;text-transform:uppercase;color:var(--ink);margin-bottom:12px;
}}
.section-h{{
  font-family:'IBM Plex Sans',sans-serif;font-size:2.4rem;font-weight:700;
  letter-spacing:-0.01em;margin-bottom:14px;
}}
.section-p{{
  font-family:'IBM Plex Sans',sans-serif;color:var(--dim);font-size:1.05rem;
  max-width:540px;line-height:1.75;margin-bottom:48px;
}}

/* ── Pipeline ── */
.flow{{display:flex;align-items:flex-start;overflow-x:auto;padding-bottom:8px}}
.flow-step{{flex:1;min-width:160px;padding:24px 20px;border-left:1px solid var(--border)}}
.flow-step:first-child{{border-left:none}}
.flow-step .step-icon{{width:36px;height:36px;margin:0 0 14px;display:flex;align-items:center;justify-content:center}}
.flow-step h4{{font-family:'IBM Plex Sans',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:6px}}
.flow-step p{{font-family:'IBM Plex Sans',sans-serif;font-size:0.95rem;color:var(--dim);line-height:1.65}}
.flow-arrow{{align-self:center;padding:0 8px;color:rgba(255,255,255,0.08);font-size:1.2rem;flex-shrink:0;user-select:none}}
.flow-note{{
  margin-top:24px;padding:14px 20px;border-left:2px solid rgba(184,64,50,0.3);
  font-family:'IBM Plex Sans',sans-serif;font-size:1rem;color:var(--dim);line-height:1.65;
}}
.flow-note strong{{color:var(--text);font-weight:600}}

/* ── Examples ── */
.ex-tabs{{display:flex;flex-wrap:wrap;margin-bottom:28px;border-bottom:1px solid var(--border)}}
.ex-tab{{
  padding:8px 18px;font-size:0.82rem;font-weight:600;font-family:'IBM Plex Mono',monospace;
  background:transparent;border:none;border-bottom:2px solid transparent;
  color:var(--dim);cursor:pointer;transition:all 0.2s;margin-bottom:-1px;
}}
.ex-tab.active{{border-bottom-color:var(--ink);color:var(--ink)}}
.ex-tab:hover:not(.active){{color:var(--text)}}
.ex-panel{{display:none}}
.ex-panel.active{{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}}
@media(max-width:720px){{.ex-panel.active{{grid-template-columns:1fr}}}}
.ex-code{{background:var(--bg2);border:1px solid var(--border);border-radius:3px;overflow:hidden}}
.ex-code-bar{{padding:8px 14px;border-bottom:1px solid var(--border);font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim)}}
.ex-code pre{{padding:18px 20px;font-family:'IBM Plex Mono',monospace;font-size:0.86rem;line-height:1.8;overflow-x:auto}}
.ex-prose h3{{font-family:'IBM Plex Sans',sans-serif;font-size:1.25rem;font-weight:700;margin-bottom:10px}}
.ex-prose p{{font-family:'IBM Plex Sans',sans-serif;font-size:1rem;color:var(--dim);line-height:1.7;margin-bottom:12px}}
.ex-prose .tag{{display:inline-block;padding:1px 8px;border-radius:2px;font-size:0.7rem;font-weight:600;font-family:'IBM Plex Mono',monospace;margin-right:5px;margin-bottom:4px}}
.tag-ink{{background:rgba(184,64,50,0.08);color:var(--ink)}}
.tag-green{{background:rgba(74,222,128,0.07);color:var(--green)}}
.tag-sky{{background:rgba(125,211,252,0.07);color:var(--sky)}}
.tag-amber{{background:rgba(251,191,36,0.07);color:var(--amber)}}

/* ── Outcomes ── */
.outcomes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}}
.outcome-card{{border-left:1px solid var(--border);padding:28px 28px 28px 24px}}
.outcome-card:first-child{{border-left:none;padding-left:0}}
.outcome-card.valid{{border-left-color:rgba(74,222,128,0.2)}}
.outcome-card.falsified{{border-left-color:rgba(248,113,113,0.2)}}
.outcome-verdict{{font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;margin-bottom:12px;letter-spacing:0.03em}}
.outcome-card.valid .outcome-verdict{{color:var(--green)}}
.outcome-card.falsified .outcome-verdict{{color:var(--red)}}
.outcome-card.unknown .outcome-verdict{{color:var(--dim)}}
.outcome-card h3{{font-family:'IBM Plex Sans',sans-serif;font-size:1.15rem;font-weight:700;margin-bottom:8px}}
.outcome-card p{{font-family:'IBM Plex Sans',sans-serif;font-size:1rem;color:var(--dim);line-height:1.7}}
.outcome-cex{{margin-top:14px;padding:10px 14px;border-left:2px solid rgba(248,113,113,0.25);font-family:'IBM Plex Mono',monospace;font-size:0.8rem;line-height:1.7;color:var(--dim)}}
.outcome-cex .cex-label{{color:var(--red)}}

/* ── Interactive benchmark cards ── */
.bench-grid-interactive{{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:2px;
}}
.bench-card-i{{
  background:rgba(255,255,255,0.02);border:1px solid var(--border);
  padding:32px 36px;cursor:pointer;position:relative;overflow:hidden;
  transition:border-color .2s var(--ease-out),background .2s;
  opacity:0;transform:translateY(16px);
  animation:cardIn .5s var(--ease-out) forwards;
}}
.bench-card-i:nth-child(1){{animation-delay:.05s}}
.bench-card-i:nth-child(2){{animation-delay:.12s}}
.bench-card-i:nth-child(3){{animation-delay:.19s}}
@keyframes cardIn{{to{{opacity:1;transform:translateY(0)}}}}
.bench-card-i::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--card-accent,var(--ink));
  transform:scaleX(0);transform-origin:left;transition:transform .3s var(--ease-out);
}}
.bench-card-i::after{{
  content:'';position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .3s;
  background:radial-gradient(ellipse 60% 50% at 30% 0%,var(--card-glow,rgba(184,64,50,0.05)),transparent);
}}
.bench-card-i:hover{{border-color:rgba(184,64,50,0.2);background:rgba(255,255,255,0.04)}}
.bench-card-i:hover::before{{transform:scaleX(1)}}
.bench-card-i:hover::after{{opacity:1}}
.bc-name{{font-family:'IBM Plex Sans',sans-serif;font-size:1.4rem;font-weight:700;color:var(--text);margin-bottom:4px}}
.bc-sub{{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim);letter-spacing:.4px;margin-bottom:28px}}
.bc-big-num{{
  font-family:'IBM Plex Sans',sans-serif;font-size:3.5rem;font-weight:700;
  line-height:1;color:var(--card-accent,var(--ink));display:inline;
}}
.bc-big-unit{{font-size:1.1rem;color:var(--dim);font-weight:300;margin-left:2px}}
.bc-big-label{{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);letter-spacing:.5px;text-transform:uppercase;margin-top:4px;margin-bottom:24px}}
.bc-bar{{height:3px;background:rgba(255,255,255,0.04);border-radius:2px;display:flex;overflow:hidden;gap:1px;margin-bottom:10px}}
.bc-seg{{height:100%;transition:width .6s var(--ease-out)}}
.bc-legend{{display:flex;gap:16px;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim)}}
.bc-legend span{{display:flex;align-items:center;gap:4px}}
.bc-legend b{{display:inline-block;width:6px;height:6px;border-radius:1px}}
.bc-footer{{margin-top:24px;padding-top:20px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}}
.bc-note{{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim)}}
.bc-note strong{{color:var(--card-accent,var(--ink));font-weight:600}}
.bc-arrow{{font-size:1.2rem;color:var(--dim);transition:transform .2s var(--ease-out),color .2s}}
.bench-card-i:hover .bc-arrow{{transform:translateX(5px);color:var(--card-accent,var(--ink))}}

/* ── Get started ── */
.setup-grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}}
@media(max-width:700px){{.setup-grid{{grid-template-columns:1fr}}}}
.setup-num{{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;font-weight:700;color:var(--ink);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px}}
.setup-step h4{{font-family:'IBM Plex Sans',sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:14px}}
.code-block{{background:var(--bg2);border:1px solid var(--border);border-radius:3px;overflow:hidden;margin-bottom:16px}}
.code-block-bar{{padding:7px 14px;border-bottom:1px solid var(--border);font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim)}}
.code-block pre{{padding:16px 18px;font-family:'IBM Plex Mono',monospace;font-size:0.86rem;line-height:1.75;overflow-x:auto}}

/* ── Footer ── */
footer{{
  padding:24px 48px;border-top:1px solid var(--border);
  font-size:0.8rem;color:var(--dim);
  font-family:'IBM Plex Mono',monospace;
  max-width:1080px;margin:0 auto;
}}
footer a{{color:var(--dim);text-decoration:none}}
footer a:hover{{color:var(--text)}}

/* ── Detail page ── */
#page-detail{{
  padding-top:80px;
  max-width:1200px;margin:0 auto;
  padding-left:48px;padding-right:48px;padding-bottom:80px;
}}
.detail-hero{{padding:52px 0 40px;border-bottom:1px solid var(--border);margin-bottom:40px;animation:fadeUp .4s var(--ease-out) both}}
.detail-eyebrow{{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;letter-spacing:2.5px;text-transform:uppercase;color:var(--dim);margin-bottom:12px}}
.detail-title{{font-family:'IBM Plex Sans',sans-serif;font-size:clamp(1.8rem,4vw,3rem);font-weight:700;color:var(--text);margin-bottom:8px}}
.detail-title em{{font-style:italic;color:var(--ink)}}
.detail-meta{{font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:var(--dim);display:flex;gap:24px;flex-wrap:wrap}}
.detail-meta-item{{display:flex;align-items:center;gap:6px}}
.detail-meta-item::before{{content:'';width:4px;height:4px;border-radius:50%;background:rgba(255,255,255,0.1)}}
.stat-row{{display:flex;gap:2px;flex-wrap:wrap;margin-bottom:36px;animation:fadeUp .4s var(--ease-out) .08s both}}
.stat-pill{{background:rgba(255,255,255,0.02);border:1px solid var(--border);padding:16px 22px;flex:1;min-width:140px}}
.stat-pill .sp-val{{font-family:'IBM Plex Sans',sans-serif;font-size:1.8rem;font-weight:700;color:var(--ink);line-height:1;margin-bottom:4px}}
.stat-pill .sp-lbl{{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;letter-spacing:.8px;text-transform:uppercase;color:var(--dim)}}
.stat-pill .sp-sub{{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim);margin-top:2px;opacity:.7}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.section-block{{margin-bottom:36px}}
.section-head{{display:flex;align-items:center;gap:14px;margin-bottom:20px}}
.section-label{{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;font-weight:600;letter-spacing:2.2px;text-transform:uppercase;color:var(--dim);white-space:nowrap}}
.section-rule{{flex:1;height:1px;background:linear-gradient(90deg,var(--border) 0%,transparent 100%)}}
.charts-row{{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:2px}}
@media(max-width:900px){{.charts-row{{grid-template-columns:1fr}}}}
.chart-card{{background:rgba(255,255,255,0.02);border:1px solid var(--border);padding:24px 26px}}
.chart-title{{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--dim);margin-bottom:20px}}
canvas{{width:100%!important}}
.cactus-controls{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:16px}}
.cactus-controls label{{display:flex;align-items:center;gap:6px;font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:var(--dim);cursor:pointer}}
.cactus-controls input[type=checkbox]{{accent-color:var(--ink);width:12px;height:12px}}
.cactus-controls select{{background:rgba(255,255,255,0.04);border:1px solid var(--border);color:var(--text);padding:4px 10px;font-family:'IBM Plex Mono',monospace;font-size:0.72rem;cursor:pointer}}
.heatmap-card{{background:rgba(255,255,255,0.02);border:1px solid var(--border);padding:24px 26px;margin-bottom:2px;overflow-x:auto}}
.heatmap-card::-webkit-scrollbar{{height:4px}}
.table-card{{background:rgba(255,255,255,0.02);border:1px solid var(--border);padding:24px 26px;margin-bottom:2px;overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:rgba(255,255,255,0.03);padding:9px 14px;text-align:left;font-family:'IBM Plex Mono',monospace;font-size:0.65rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--border);white-space:nowrap}}
td{{padding:8px 14px;border-bottom:1px solid var(--border);white-space:nowrap;font-family:'IBM Plex Mono',monospace}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,255,255,.02)}}
.pill{{display:inline-block;padding:2px 7px;font-size:0.65rem;font-weight:600;font-family:'IBM Plex Mono',monospace;letter-spacing:.3px}}
.pill-ok{{background:rgba(74,222,128,.1);color:#4ade80;outline:1px solid rgba(74,222,128,.2)}}
.pill-timeout{{background:rgba(251,191,36,.1);color:#fbbf24;outline:1px solid rgba(251,191,36,.2)}}
.pill-fail{{background:rgba(248,113,113,.1);color:#f87171;outline:1px solid rgba(248,113,113,.2)}}
.time-fast{{color:#4ade80}}.time-mid{{color:var(--text)}}.time-slow{{color:#fbbf24}}

@media(max-width:720px){{
  nav{{padding:12px 20px}}
  .nav-links{{display:none}}
  .wrap{{padding:64px 20px}}
  .hero{{padding:110px 20px 60px}}
  .flow{{flex-direction:column}}
  #page-detail{{padding-left:20px;padding-right:20px}}
}}
</style>
</head>
<body>

<!-- ── Nav ── -->
<nav>
  <div class="nav-logo" onclick="showWebsite()">Blaster</div>
  <div class="nav-links" id="nav-links">
    <a href="#pipeline">Pipeline</a>
    <a href="#examples">Examples</a>
    <a href="#benchmarks">Benchmarks</a>
    <a href="#start">Get started</a>
  </div>
  <div id="nav-breadcrumb">
    <span class="back" onclick="showWebsite()">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
      Overview
    </span>
    <span class="sep">·</span>
    <span class="crumb" id="crumb-name"></span>
  </div>
  <a href="https://github.com/input-output-hk/Lean-blaster" target="_blank" class="nav-gh">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
    GitHub
  </a>
</nav>

<!-- ═══════════════════════════════════
     PAGE: WEBSITE
═══════════════════════════════════ -->
<div class="page active" id="page-website">

<!-- ── Hero ── -->
<section>
  <div class="hero">
    <div class="hero-eyebrow">Lean4 · Automated Reasoning</div>
    <h1><span class="word-prove">Prove</span> it.</h1>
    <p class="hero-sub">
      Write a Lean4 theorem. Call <code style="font-family:'IBM Plex Mono',monospace;color:var(--ink);font-size:0.9em">blaster</code>.
      Get a proof, or a concrete counterexample that tells you exactly why it's wrong.
    </p>
    <div class="hero-actions">
      <a href="https://github.com/input-output-hk/Lean-blaster" class="btn btn-ink" target="_blank">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
        View on GitHub
      </a>
      <a href="#benchmarks" class="btn btn-ghost">See benchmarks ↓</a>
    </div>
    <div class="hero-demo">
      <div class="demo-pane">
        <div class="demo-pane-bar">
          <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
          <span class="label">Proof.lean</span>
        </div>
        <pre id="demo-code" style="min-height:140px"></pre>
      </div>
    </div>
  </div>
</section>

<!-- ── Pipeline ── -->
<section id="pipeline">
  <div class="wrap">
    <div class="section-tag">How it works</div>
    <h2 class="section-h">Three steps, one command</h2>
    <p class="section-p">Blaster doesn't just pass your goal to the solver. It first tries to close it through symbolic simplification. No SMT query needed.</p>
    <div class="flow">
      <div class="flow-step">
        <div class="step-icon" style="background:rgba(251,191,36,0.1)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <h4>Optimize</h4>
        <p>Beta reduction, function unfolding, let-inlining, 30+ algebraic rewriting rules</p>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">
        <div class="step-icon" style="background:rgba(184,64,50,0.1)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#b84032" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
        </div>
        <h4>Translate</h4>
        <p>Lean4 types and expressions encoded as SMT-LIB V2: sorts, terms, quantifiers</p>
      </div>
      <div class="flow-arrow">→</div>
      <div class="flow-step">
        <div class="step-icon" style="background:rgba(125,211,252,0.1)">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7dd3fc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
        </div>
        <h4>Solve</h4>
        <p>Proof or counterexample. No manual proof required.</p>
      </div>
    </div>
    <div class="flow-note">
      <strong>Early exit:</strong> if the optimizer reduces the goal to
      <code style="font-family:'IBM Plex Mono',monospace;font-size:0.9em;color:var(--green)">True</code>,
      Blaster declares Valid immediately — no SMT call. Reduction to
      <code style="font-family:'IBM Plex Mono',monospace;font-size:0.9em;color:var(--red)">False</code>
      gives an instant Falsified. The solver only runs when symbolic reasoning is not enough.
    </div>
  </div>
</section>

<!-- ── Examples ── -->
<section id="examples">
  <div class="wrap" style="padding-top:0">
    <div class="section-tag">Examples</div>
    <h2 class="section-h">What Blaster can prove</h2>
    <p class="section-p">From first-order arithmetic to polymorphic inductive types and state machines, all with a single tactic.</p>
    <div class="ex-tabs">
      <button class="ex-tab active" onclick="showEx('arith',this)">Arithmetic</button>
      <button class="ex-tab" onclick="showEx('inductives',this)">Inductive types</button>
      <button class="ex-tab" onclick="showEx('recursive',this)">Recursive functions</button>
      <button class="ex-tab" onclick="showEx('statemachine',this)">State machines</button>
    </div>
    <!-- Arithmetic -->
    <div class="ex-panel active" id="ex-arith">
      <div class="ex-code">
        <div class="ex-code-bar">Theorems.lean</div>
        <pre><span class="c-dim">-- Basic arithmetic properties</span>
<span class="c-fn">#blaster</span> [ <span class="c-kw">&#8704;</span> (a b : <span class="c-ty">Nat</span>), a + b = b + a ]
<span class="c-ok">&#10003; Valid</span>

<span class="c-fn">#blaster</span> [ <span class="c-kw">&#8704;</span> (n : <span class="c-ty">Nat</span>), n * n &#8804; n + n ]
<span class="c-err">&#10007; Falsified</span>
<span class="c-dim">Counterexample: n = 3</span></pre>
      </div>
      <div class="ex-prose">
        <h3>First-order arithmetic</h3>
        <p>Integer and natural number goals are translated to SMT arithmetic theories. Blaster handles equality, inequality, and modular arithmetic over Nat and Int.</p>
        <span class="tag tag-ink">Nat</span><span class="tag tag-ink">Int</span><span class="tag tag-sky">QF_NIA</span><span class="tag tag-green">constant folding</span>
      </div>
    </div>
    <!-- Inductive types -->
    <div class="ex-panel" id="ex-inductives">
      <div class="ex-code">
        <div class="ex-code-bar">Either.lean</div>
        <pre><span class="c-kw">inductive</span> <span class="c-ty">Either</span> (&#945; &#946; : <span class="c-ty">Type</span>) <span class="c-kw">where</span>
  | Left  : &#945; &#8594; Either &#945; &#946;
  | Right : &#946; &#8594; Either &#945; &#946;

<span class="c-kw">theorem</span> <span class="c-fn">isLeft_or_isRight</span> (x : Either &#945; &#946;) :
    isLeft x <span class="c-kw">&#8744;</span> isRight x := by <span class="c-fn">blaster</span>
<span class="c-ok">&#10003; Valid</span></pre>
      </div>
      <div class="ex-prose">
        <h3>Parametric &amp; mutual inductives</h3>
        <p>Blaster encodes inductive types as uninterpreted SMT sorts with constructor predicates. It handles parametric types, mutually inductive definitions, and polymorphic functions.</p>
        <span class="tag tag-ink">parametric</span><span class="tag tag-sky">uninterpreted sorts</span><span class="tag tag-green">polymorphism</span>
      </div>
    </div>
    <!-- Recursive -->
    <div class="ex-panel" id="ex-recursive">
      <div class="ex-code">
        <div class="ex-code-bar">Lists.lean</div>
        <pre><span class="c-fn">#blaster</span> [ <span class="c-kw">&#8704;</span> (x : <span class="c-ty">Nat</span>) (xs : List <span class="c-ty">Nat</span>),
  xs.length + 1 = (x :: xs).length ]
<span class="c-ok">&#10003; Valid</span>

<span class="c-kw">mutual</span>
  <span class="c-kw">def</span> <span class="c-fn">isEven</span> : <span class="c-ty">Nat</span> &#8594; <span class="c-ty">Bool</span>
    | 0   =&gt; true  | n+1 =&gt; isOdd n
  <span class="c-kw">def</span> <span class="c-fn">isOdd</span>  : <span class="c-ty">Nat</span> &#8594; <span class="c-ty">Bool</span>
    | 0   =&gt; false | n+1 =&gt; isEven n
<span class="c-kw">end</span>
<span class="c-fn">#blaster</span> [ <span class="c-kw">&#8704;</span> n, isEven (n+2) &#8594; isEven n ]
<span class="c-ok">&#10003; Valid</span></pre>
      </div>
      <div class="ex-prose">
        <h3>Recursive &amp; mutually recursive</h3>
        <p>Blaster unfolds recursive definitions and applies algebraic normalization before SMT translation, often reducing recursive properties to straightforward quantified formulae.</p>
        <span class="tag tag-ink">recursive defs</span><span class="tag tag-ink">mutual recursion</span><span class="tag tag-amber">+ induction tactic</span>
      </div>
    </div>
    <!-- State machines -->
    <div class="ex-panel" id="ex-statemachine">
      <div class="ex-code">
        <div class="ex-code-bar">TrafficLight.lean</div>
        <pre><span class="c-kw">inductive</span> <span class="c-ty">Light</span> <span class="c-kw">where</span>
  | Red | Yellow | Green

<span class="c-dim">-- search for violation up to depth 6</span>
<span class="c-fn">#bmc</span> (max-depth: 6) [<span class="c-ty">Light</span>]
<span class="c-ok">&#10003; No counterexample found</span>

<span class="c-dim">-- prove it holds for all reachable states</span>
<span class="c-fn">#kind</span> (max-depth: 2) [<span class="c-ty">Light</span>]
<span class="c-ok">&#10003; Valid  (KInd at Depth 2)</span></pre>
      </div>
      <div class="ex-prose">
        <h3>State machine verification</h3>
        <p>Define states, transitions, and safety invariants as ordinary Lean4 types. <code style="font-family:'IBM Plex Mono',monospace;color:var(--ink);font-size:0.88em">#bmc</code> searches for violations up to a bounded depth. <code style="font-family:'IBM Plex Mono',monospace;color:var(--ink);font-size:0.88em">#kind</code> proves the invariant via k-induction.</p>
        <span class="tag tag-ink">#bmc</span><span class="tag tag-sky">#kind</span><span class="tag tag-amber">k-induction</span>
      </div>
    </div>
  </div>
</section>

<!-- ── Outcomes ── -->
<section>
  <div class="wrap" style="padding-top:0">
    <div class="section-tag">Results</div>
    <h2 class="section-h">Three possible answers</h2>
    <p class="section-p">Every call to <code style="font-family:'IBM Plex Mono',monospace;color:var(--ink)">blaster</code> ends in one of three outcomes, each actionable.</p>
    <div class="outcomes">
      <div class="outcome-card valid">
        <div class="outcome-verdict">&#10003; Valid</div>
        <h3>Theorem holds</h3>
        <p>The solver returned <em>unsat</em> for the negated goal. The tactic closes the proof with <code style="font-family:'IBM Plex Mono',monospace;font-size:0.85em;color:var(--green)">admit</code>. Note: proof reconstruction is not yet implemented.</p>
      </div>
      <div class="outcome-card falsified">
        <div class="outcome-verdict">&#10007; Falsified</div>
        <h3>Counterexample found</h3>
        <p>The solver returned <em>sat</em>: the goal is provably wrong. The satisfying model is decoded into a Lean4 value and printed inline.</p>
        <div class="outcome-cex">
          <span class="cex-label">Counterexample:</span><br>
          &nbsp;- n: 42
        </div>
      </div>
      <div class="outcome-card unknown">
        <div class="outcome-verdict">? Undetermined</div>
        <h3>Solver gave up</h3>
        <p>The solver returned <em>unknown</em>, typically due to timeout or a formula outside decidable fragments. The goal is returned as-is for manual reasoning.</p>
      </div>
    </div>
  </div>
</section>

<!-- ── Benchmarks (interactive) ── -->
<section id="benchmarks">
  <div class="wrap" style="padding-top:0">
    <div class="section-tag">Benchmarks</div>
    <h2 class="section-h">Proven on real proof libraries</h2>
    <p class="section-p">Blaster evaluated against established Lean4 proof corpora. Click a benchmark suite to explore detailed results.</p>
    <div class="bench-grid-interactive" id="bench-grid"></div>
  </div>
</section>

<!-- ── Get started ── -->
<section id="start">
  <div class="wrap" style="padding-top:0">
    <div class="section-tag">Get started</div>
    <h2 class="section-h">Add Blaster to your project</h2>
    <p class="section-p">Two steps: declare the dependency, then call <code style="font-family:'IBM Plex Mono',monospace;color:var(--ink)">blaster</code>.</p>
    <div class="setup-grid">
      <div class="setup-step">
        <div class="setup-num">Step 1: Add dependency</div>
        <h4>lakefile.toml</h4>
        <div class="code-block">
          <div class="code-block-bar">lakefile.toml</div>
          <pre><span style="color:#c084fc">[[require]]</span>
<span style="color:#b84032">name</span> = <span style="color:#4ade80">"Blaster"</span>
<span style="color:#b84032">git</span>  = <span style="color:#4ade80">"https://github.com/input-output-hk/Lean-blaster"</span>
<span style="color:#b84032">rev</span>  = <span style="color:#4ade80">"main"</span></pre>
        </div>
      </div>
      <div class="setup-step">
        <div class="setup-num">Step 2: Use it</div>
        <h4>Your Lean4 file</h4>
        <div class="code-block">
          <div class="code-block-bar">MyProofs.lean</div>
          <pre><span style="color:#c084fc">import</span> <span style="color:#b84032">Blaster.Command.Tactic</span>

<span style="color:#c084fc">theorem</span> <span style="color:#b84032">addComm</span> (a b : <span style="color:#7dd3fc">Nat</span>) :
    a + b = b + a := by
  <span style="color:#b84032">blaster</span>
<span style="color:#4ade80">-- &#10003; Valid</span></pre>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ── Built by ── -->
<section>
  <div class="wrap" style="padding-top:0;padding-bottom:60px">
    <p style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--dim);margin-bottom:20px">Built at</p>
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <a href="https://iog.io" target="_blank" style="display:flex;align-items:center;gap:10px;padding:10px 16px;border:1px solid var(--border);border-radius:3px;text-decoration:none;color:var(--dim);font-family:'IBM Plex Sans',sans-serif;font-weight:600;font-size:1rem;transition:color 0.2s" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--dim)'">
        Input Output Global
      </a>
    </div>
  </div>
</section>

<footer>
  Apache 2.0 &middot; <a href="https://github.com/input-output-hk/Lean-blaster">github.com/input-output-hk/Lean-blaster</a>
  <span style="margin:0 16px;opacity:.3">|</span>
  Benchmarks generated {generated_at}
</footer>

</div><!-- /page-website -->

<!-- ═══════════════════════════════════
     PAGE: DETAIL
═══════════════════════════════════ -->
<div class="page" id="page-detail">
  <div class="detail-hero">
    <div class="detail-eyebrow">Benchmark Suite</div>
    <div class="detail-title" id="detail-title"></div>
    <div class="detail-meta" id="detail-meta"></div>
  </div>
  <div class="stat-row" id="detail-stats"></div>
  <div class="section-block">
    <div class="section-head"><span class="section-label">Performance Charts</span><div class="section-rule"></div></div>
    <div class="charts-row" id="detail-charts"></div>
  </div>
  <div class="section-block">
    <div class="section-head"><span class="section-label">Result Heatmap</span><div class="section-rule"></div></div>
    <div id="detail-heatmap"></div>
  </div>
  <div class="section-block">
    <div class="section-head"><span class="section-label">Statistics</span><div class="section-rule"></div></div>
    <div id="detail-tables"></div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script>
const BENCHMARKS    = {payload};
const STATUS_COLORS = {status_colors};
const CHARTS        = {{}};

const $ = id => document.getElementById(id);
const el = (tag, cls, html) => {{
  const e = document.createElement(tag);
  if (cls)  e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}};
const destroyChart = id => {{ if(CHARTS[id]){{ CHARTS[id].destroy(); delete CHARTS[id]; }} }};

const pill = s => {{
  const m = {{OK:['pill-ok','&#10003;'],TIMEOUT:['pill-timeout','&#8987;'],FAIL:['pill-fail','&#10007;']}};
  const [c,i] = m[s]||['pill-fail','&#10007;'];
  return `<span class="pill ${{c}}">${{i}} ${{s}}</span>`;
}};
const fmtTime = ms => {{
  if (ms == null) return `<span style="color:var(--dim)">&#8212;</span>`;
  const cls = ms < 800 ? 'time-fast' : ms < 3000 ? 'time-mid' : 'time-slow';
  return `<span class="${{cls}}">${{ms.toFixed(0)}} ms</span>`;
}};

function animCount(el, target, duration=900) {{
  const start = performance.now();
  const step = now => {{
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(ease * target);
    if (t < 1) requestAnimationFrame(step);
  }};
  requestAnimationFrame(step);
}}

/* ── Routing ── */
function showWebsite() {{
  $('page-website').classList.add('active');
  $('page-detail').classList.remove('active');
  $('nav-links').style.display = '';
  $('nav-breadcrumb').style.display = 'none';
  window.scrollTo({{top: 0, behavior: 'smooth'}});
}}

function showDetail(name) {{
  $('page-website').classList.remove('active');
  $('page-detail').classList.add('active');
  $('nav-links').style.display = 'none';
  $('nav-breadcrumb').style.display = 'flex';
  $('crumb-name').textContent = name;
  window.scrollTo({{top: 0, behavior: 'instant'}});
  renderDetail(BENCHMARKS.find(b => b.name === name));
}}

/* ── Benchmark cards ── */
function renderLanding() {{
  const grid = $('bench-grid');
  grid.innerHTML = '';
  BENCHMARKS.forEach(b => {{
    const total     = b.theorem_names.length;
    const bestT     = [...b.tactics].sort((a,z) => b.bar[z].ok - b.bar[a].ok)[0];
    const bestOk    = bestT ? b.bar[bestT].ok : 0;
    const bestPct   = total > 0 ? Math.round(bestOk / total * 100) : 0;
    const solvedAny = b.theorem_names.filter((_,i) =>
      b.tactics.some(t => b.heatmap[t][i]==='OK')).length;
    const aggOk  = b.tactics.reduce((s,t) => s + b.bar[t].ok,      0);
    const aggTo  = b.tactics.reduce((s,t) => s + b.bar[t].timeout, 0);
    const aggFa  = b.tactics.reduce((s,t) => s + b.bar[t].fail,    0);
    const aggSum = aggOk + aggTo + aggFa || 1;
    const okW  = (aggOk  / aggSum * 100).toFixed(2);
    const toW  = (aggTo  / aggSum * 100).toFixed(2);
    const faW  = (aggFa  / aggSum * 100).toFixed(2);
    const accentColor = b.colors[bestT] || 'var(--ink)';
    const accentGlow  = (b.colors[bestT] || '#b84032') + '10';
    const card = el('div','bench-card-i');
    card.style.setProperty('--card-accent', accentColor);
    card.style.setProperty('--card-glow',   accentGlow);
    card.innerHTML = `
      <div class="bc-name">${{b.name}}</div>
      <div class="bc-sub">${{b.tactics.length}} tactics &middot; ${{total}} theorems</div>
      <div><span class="bc-big-num" data-target="${{bestOk}}">0</span><span class="bc-big-unit"> / ${{total}}</span></div>
      <div class="bc-big-label">theorems proved &mdash; best: ${{bestT||'n/a'}} (${{bestPct}}%)</div>
      <div class="bc-bar">
        <div class="bc-seg" style="width:${{okW}}%;background:#4ade80"></div>
        <div class="bc-seg" style="width:${{toW}}%;background:#fbbf24"></div>
        <div class="bc-seg" style="width:${{faW}}%;background:#f87171"></div>
      </div>
      <div class="bc-legend">
        <span><b style="background:#4ade80"></b>${{okW}}% solved</span>
        <span><b style="background:#fbbf24"></b>${{toW}}% timeout</span>
        <span><b style="background:#f87171"></b>${{faW}}% fail</span>
      </div>
      <div class="bc-footer">
        <div class="bc-note"><strong>${{solvedAny}}</strong> theorems solved by &#8805;1 tactic</div>
        <div class="bc-arrow">&#8594;</div>
      </div>`;
    card.onclick = () => showDetail(b.name);
    grid.appendChild(card);
    requestAnimationFrame(() => {{
      const numEl = card.querySelector('.bc-big-num');
      animCount(numEl, bestOk, 1000);
    }});
  }});
}}

/* ── Detail ── */
function renderDetail(b) {{
  const total = b.theorem_names.length;
  const bestT = [...b.tactics].sort((a,z) => b.bar[z].ok - b.bar[a].ok)[0];
  const solvedAny = b.theorem_names.filter((_,i) =>
    b.tactics.some(t => b.heatmap[t][i]==='OK')).length;

  $('detail-title').innerHTML = `${{b.name}} <em>Results</em>`;
  $('detail-meta').innerHTML = [
    `${{total}} theorems`,
    `${{b.tactics.length}} tactics`,
    `Best: ${{bestT}} (${{b.bar[bestT].ok}}/${{total}})`,
  ].map(s=>`<span class="detail-meta-item">${{s}}</span>`).join('');

  const statsEl = $('detail-stats');
  statsEl.innerHTML = '';
  [
    [total,      'Theorems',        ''],
    [solvedAny,  'Solved by &#8805;1',  'at least one tactic'],
    [b.bar[bestT]?.ok??0, 'Best tactic', bestT||''],
    [b.tactics.length, 'Tactics',   'compared'],
  ].forEach(([val,lbl,sub]) => {{
    const p = el('div','stat-pill');
    p.innerHTML = `<div class="sp-val">${{val}}</div>
                   <div class="sp-lbl">${{lbl}}</div>
                   ${{sub ? `<div class="sp-sub">${{sub}}</div>` : ''}}`;
    statsEl.appendChild(p);
  }});

  const chartsEl = $('detail-charts');
  chartsEl.innerHTML = '';
  const barCard = el('div','chart-card');
  barCard.innerHTML = `<div class="chart-title">Success Rate by Tactic</div>`;
  barCard.appendChild(Object.assign(document.createElement('canvas'),{{id:`bar-${{b.name}}`}}));
  chartsEl.appendChild(barCard);
  const cactusCard = el('div','chart-card');
  cactusCard.innerHTML = `
    <div class="chart-title">Cactus Plot &#8212; Cumulative Solves vs Time</div>
    <div class="cactus-controls">
      <label><input type="checkbox" id="log-${{b.name}}" checked/> Log scale</label>
      <label>Timeout&thinsp;
        <select id="timeout-${{b.name}}">
          <option value="5">5 s</option>
          <option value="10">10 s</option>
          <option value="20" selected>20 s</option>
          <option value="60">60 s</option>
          <option value="300">300 s</option>
        </select>
      </label>
    </div>`;
  cactusCard.appendChild(Object.assign(document.createElement('canvas'),{{id:`cactus-${{b.name}}`}}));
  chartsEl.appendChild(cactusCard);

  $('detail-heatmap').innerHTML = '';
  const hmCard = el('div','heatmap-card');
  hmCard.innerHTML = `<div class="chart-title">Per-Theorem Result Heatmap</div>`;
  hmCard.appendChild(buildHeatmap(b));
  $('detail-heatmap').appendChild(hmCard);

  $('detail-tables').innerHTML = '';
  const statsCard = el('div','table-card');
  statsCard.innerHTML = `<div class="chart-title">Tactic Statistics</div>`;
  statsCard.appendChild(buildStatsTable(b));
  $('detail-tables').appendChild(statsCard);
  const thmCard = el('div','table-card');
  thmCard.innerHTML = `<div class="chart-title">Results per Theorem</div>`;
  thmCard.appendChild(buildThmTable(b));
  $('detail-tables').appendChild(thmCard);

  requestAnimationFrame(() => {{
    renderBarChart(b);
    renderCactusChart(b, 20, true);
    $(`log-${{b.name}}`).onchange  = () => refreshCactus(b);
    $(`timeout-${{b.name}}`).onchange = () => refreshCactus(b);
  }});
}}

/* ── Bar chart ── */
function renderBarChart(b) {{
  const id = `bar-${{b.name}}`;
  destroyChart(id);
  const total = b.theorem_names.length;
  CHARTS[id] = new Chart($(id), {{
    type:'bar',
    data:{{
      labels: b.tactics,
      datasets:[
        {{label:'Solved',  data:b.tactics.map(t=>b.bar[t].ok),      backgroundColor:'#4ade8088',borderColor:'#4ade80',borderWidth:1,borderRadius:2}},
        {{label:'Timeout', data:b.tactics.map(t=>b.bar[t].timeout), backgroundColor:'#fbbf2488',borderColor:'#fbbf24',borderWidth:1,borderRadius:2}},
        {{label:'Failed',  data:b.tactics.map(t=>b.bar[t].fail),    backgroundColor:'#f8717188',borderColor:'#f87171',borderWidth:1,borderRadius:2}},
      ]
    }},
    options:{{
      indexAxis:'y', responsive:true,
      plugins:{{
        legend:{{labels:{{color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace",size:11}}}}}},
        tooltip:{{
          backgroundColor:'#120a07',borderColor:'rgba(255,255,255,0.06)',borderWidth:1,
          titleColor:'#dde1ef',bodyColor:'#7a8099',
          callbacks:{{label: ctx=>`  ${{ctx.dataset.label}}: ${{ctx.raw}}/${{total}}`}}
        }}
      }},
      scales:{{
        x:{{stacked:true,max:total,
          ticks:{{color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace"}}}},
          grid:{{color:'rgba(255,255,255,0.03)'}}}},
        y:{{stacked:true,
          ticks:{{color:'#dde1ef',font:{{family:"'IBM Plex Mono',monospace",weight:'600'}}}},
          grid:{{color:'rgba(255,255,255,0.03)'}}}}
      }}
    }}
  }});
}}

/* ── Cactus chart ── */
function refreshCactus(b) {{
  renderCactusChart(b,
    parseFloat($(`timeout-${{b.name}}`).value),
    $(`log-${{b.name}}`).checked);
}}

function makeCactusDataset(times, timeout, color, dash, label) {{
  const pts = [];
  times.forEach((t,i) => {{ if(t<=timeout) pts.push({{x:t,y:i+1}}); }});
  if (pts.length > 0) pts.push({{x:timeout, y:pts[pts.length-1].y}});
  return {{
    label, data:pts,
    borderColor:color, backgroundColor:color+'18',
    borderWidth:2, pointRadius:0,
    stepped:'after', borderDash:dash, tension:0, fill:false,
  }};
}}

function renderCactusChart(b, timeout=20, logScale=true) {{
  const id = `cactus-${{b.name}}`;
  destroyChart(id);
  const datasets = b.tactics
    .filter(t => b.cactus[t].length > 0)
    .map(t => makeCactusDataset(b.cactus[t], timeout, b.colors[t], b.dashes[t]||[], t));
  const allT = b.tactics.flatMap(t => b.cactus[t].filter(x => x<=timeout));
  const xMin = logScale && allT.length
    ? Math.pow(10, Math.floor(Math.log10(Math.min(...allT))))
    : 0;
  CHARTS[id] = new Chart($(id), {{
    type:'line', data:{{datasets}},
    options:{{
      responsive:true, animation:{{duration:250}},
      plugins:{{
        legend:{{labels:{{color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace",size:11}},boxWidth:18}}}},
        tooltip:{{
          backgroundColor:'#120a07',borderColor:'rgba(255,255,255,0.06)',borderWidth:1,
          titleColor:'#dde1ef',bodyColor:'#7a8099',
          mode:'index',intersect:false,
          callbacks:{{
            title: items => `${{parseFloat(items[0].label).toFixed(3)}} s`,
            label: ctx  => `  ${{ctx.dataset.label}}: ${{ctx.raw.y}} solved`,
          }}
        }}
      }},
      scales:{{
        x:{{
          type:logScale?'logarithmic':'linear',
          min:xMin, max:timeout,
          title:{{display:true,text:`time (s${{logScale?', log':''}})`,color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace"}}}},
          ticks:{{color:'#7a8099',maxTicksLimit:8,font:{{family:"'IBM Plex Mono',monospace"}}}},
          grid:{{color:'rgba(255,255,255,0.03)'}}
        }},
        y:{{
          min:0, max:b.theorem_names.length,
          title:{{display:true,text:'problems solved',color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace"}}}},
          ticks:{{color:'#7a8099',font:{{family:"'IBM Plex Mono',monospace"}}}},
          grid:{{color:'rgba(255,255,255,0.03)'}}
        }}
      }}
    }}
  }});
}}

/* ── Heatmap SVG ── */
function buildHeatmap(b) {{
  const tactics=b.tactics, theorems=b.theorem_names;
  const CW=14,CH=26,LW=148,TOP=150,LEG=28;
  const ns='http://www.w3.org/2000/svg';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('width',  LW+theorems.length*CW+10);
  svg.setAttribute('height', TOP+tactics.length*CH+LEG);
  svg.style.display='block';
  svg.style.minWidth=(LW+theorems.length*CW+10)+'px';
  const txt=(x,y,s,a={{}})=>{{
    const t=document.createElementNS(ns,'text');
    t.setAttribute('x',x); t.setAttribute('y',y);
    t.setAttribute('font-size',a.size||'10');
    t.setAttribute('fill',a.fill||'#7a8099');
    t.setAttribute('font-family',"'IBM Plex Mono',monospace");
    if(a.anchor) t.setAttribute('text-anchor',a.anchor);
    if(a.rotate) t.setAttribute('transform',a.rotate);
    t.textContent=s; svg.appendChild(t);
  }};
  theorems.forEach((thm,ti)=>{{
    const x=LW+ti*CW+CW/2;
    const short=thm.length>13?thm.slice(0,12)+'&#8230;':thm;
    txt(x,TOP-4,short,{{anchor:'start',rotate:`rotate(-60,${{x}},${{TOP-4}})`}});
  }});
  tactics.forEach((tactic,ri)=>{{
    const y=TOP+ri*CH;
    txt(LW-8,y+CH/2+4,tactic,{{anchor:'end',fill:b.colors[tactic]||'#7a8099',size:'11'}});
    theorems.forEach((thm,ti)=>{{
      const status=b.heatmap[tactic][ti];
      const fill=STATUS_COLORS[status]||'#1a0a06';
      const r=document.createElementNS(ns,'rect');
      r.setAttribute('x',LW+ti*CW+1); r.setAttribute('y',y+2);
      r.setAttribute('width',CW-2);   r.setAttribute('height',CH-4);
      r.setAttribute('fill',fill);    r.setAttribute('rx','2');
      r.setAttribute('opacity','0.8');
      const title=document.createElementNS(ns,'title');
      title.textContent=`${{thm}} \xb7 ${{tactic}}: ${{status}}`;
      r.appendChild(title); svg.appendChild(r);
    }});
  }});
  const ly=TOP+tactics.length*CH+LEG-4;
  Object.entries(STATUS_COLORS).forEach(([s,c],i)=>{{
    const rx=LW+i*100;
    const r=document.createElementNS(ns,'rect');
    r.setAttribute('x',rx); r.setAttribute('y',ly-11);
    r.setAttribute('width',10); r.setAttribute('height',10);
    r.setAttribute('fill',c);  r.setAttribute('rx','2');
    svg.appendChild(r);
    txt(rx+15,ly,s,{{fill:'#7a8099'}});
  }});
  return svg;
}}

/* ── Stats table ── */
function buildStatsTable(b) {{
  const wrap=el('div'), table=el('table'), thead=el('thead'), hr=el('tr');
  ['Tactic','Solved','Timeout','Failed','Rate','Avg','Median'].forEach(h=>hr.appendChild(el('th','',h)));
  thead.appendChild(hr); table.appendChild(thead);
  const tbody=el('tbody');
  [...b.tactics].sort((a,z)=>b.bar[z].ok-b.bar[a].ok).forEach(t=>{{
    const d=b.bar[t];
    const pct=d.total>0?(d.ok/d.total*100).toFixed(1)+'%':'&#8212;';
    const tr=el('tr');
    [
      `<span style="color:${{b.colors[t]}};font-weight:600">${{t}}</span>`,
      `<span class="pill pill-ok">${{d.ok}}/${{d.total}}</span>`,
      `<span class="pill pill-timeout">${{d.timeout}}</span>`,
      `<span class="pill pill-fail">${{d.fail}}</span>`,
      `<strong style="color:var(--text)">${{pct}}</strong>`,
      d.avg_ms!=null    ? fmtTime(d.avg_ms)    : `<span style="color:var(--dim)">&#8212;</span>`,
      d.median_ms!=null ? fmtTime(d.median_ms) : `<span style="color:var(--dim)">&#8212;</span>`,
    ].forEach(html=>{{ const td=el('td'); td.innerHTML=html; tr.appendChild(td); }});
    tbody.appendChild(tr);
  }});
  table.appendChild(tbody); wrap.appendChild(table); return wrap;
}}

/* ── Theorem table ── */
function buildThmTable(b) {{
  const wrap=el('div'), table=el('table'), thead=el('thead'), hr=el('tr');
  hr.appendChild(el('th','',`Theorem (${{b.theorem_names.length}})`));
  b.tactics.forEach(t=>{{
    const th=el('th');
    th.innerHTML=`<span style="color:${{b.colors[t]}}">${{t}}</span>`;
    hr.appendChild(th);
  }});
  thead.appendChild(hr); table.appendChild(thead);
  const tbody=el('tbody');
  b.theorem_names.forEach((thm,i)=>{{
    const tr=el('tr');
    const td0=el('td'); td0.style.color='#dde1ef'; td0.textContent=thm; tr.appendChild(td0);
    b.tactics.forEach(t=>{{
      const td=el('td'); td.innerHTML=pill(b.heatmap[t][i]); tr.appendChild(td);
    }});
    tbody.appendChild(tr);
  }});
  table.appendChild(tbody); wrap.appendChild(table); return wrap;
}}

/* ── Website JS: example tabs ── */
function showEx(id, btn) {{
  document.querySelectorAll('.ex-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.ex-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('ex-'+id).classList.add('active');
}}

/* ── Website JS: animated hero demo ── */
(function() {{
  const demoEl = document.getElementById('demo-code');
  if (!demoEl) return;

  function syntax(text) {{
    let h = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    h = h.replace(/\\b(theorem|def|by|fun|let|have|show|where)\\b/g,'<span class="c-kw">$1</span>');
    h = h.replace(/\\b(Nat|Int|Bool|String|Type|Prop|True|False)\\b/g,'<span class="c-ty">$1</span>');
    h = h.replace(/\\b(blaster|sorry|omega|simp|rfl|linarith)\\b/g,'<span class="c-fn">$1</span>');
    return h;
  }}

  let code = '', outputLines = [];
  function render() {{
    const outHtml = outputLines.length ? '\\n' + outputLines.join('\\n') : '';
    demoEl.innerHTML = syntax(code) + '<span class="c-cursor"></span>' + outHtml;
  }}
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function typeText(text, delay) {{
    for (const ch of text) {{ code += ch; render(); await sleep(delay + Math.random()*delay*0.3); }}
  }}
  async function deleteChars(n, delay) {{
    for (let i = 0; i < n && code.length > 0; i++) {{ code = code.slice(0,-1); render(); await sleep(delay); }}
  }}
  function addOutput(html) {{ outputLines.push(html); render(); }}
  function clearOutput()   {{ outputLines = [];        render(); }}

  const PREFIX     = 'theorem sub_cancel (n k : Nat)';
  const SORRY_TAIL = ' :\\n    n - k + k = n := by\\n  sorry';
  const BLAST_TAIL = ' :\\n    n - k + k = n := by\\n  blaster';
  const FIX_INSERT = ' (h : k \\u2264 n)';

  async function run() {{
    code = ''; clearOutput(); render();
    await sleep(700);
    await typeText(PREFIX + SORRY_TAIL, 28);
    await sleep(900);
    await deleteChars(5, 40);
    await typeText('blaster', 55);
    await sleep(800);
    addOutput('<span class="c-err">-- \\u274C Falsified</span>');
    await sleep(350);
    addOutput('<span class="c-dim">--    counterexample: n := 0, k := 1</span>');
    await sleep(350);
    addOutput('<span class="c-dim">--    0 - 1 + 1 = 1  (Nat subtraction truncates)</span>');
    await sleep(2800);
    clearOutput();
    await deleteChars(BLAST_TAIL.length, 18);
    await sleep(450);
    await typeText(FIX_INSERT, 50);
    await typeText(BLAST_TAIL, 30);
    await sleep(800);
    addOutput('<span class="c-ok">-- \\u2705 Valid</span>');
    await sleep(4000);
    run();
  }}
  run();
}})();

/* ── Boot ── */
renderLanding();
</script>
</body>
</html>"""

    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard saved: {out}")
    print(f"Open in browser: file://{out.resolve()}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)

    results_dir = sys.argv[1] if len(sys.argv) > 1 else "benchmark_results"
    output_html = sys.argv[2] if len(sys.argv) > 2 else os.path.join(results_dir, "dashboard.html")

    if not os.path.isdir(results_dir):
        print(f"Error: results directory not found: {results_dir}", file=sys.stderr)
        sys.exit(1)

    make_dashboard(results_dir, output_html)


if __name__ == "__main__":
    main()
