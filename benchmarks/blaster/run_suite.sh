#!/usr/bin/env bash
# Run one Blaster baseline suite: run_suite.sh <NNG4|STG4|ITL4|MiniF2F|Verina|UPLC> [--out DIR] [--jobs N]
set -euo pipefail
[[ $# -ge 1 ]] || { echo "usage: $0 <NNG4|STG4|ITL4|MiniF2F|Verina|UPLC> [--out DIR] [--jobs N]" >&2; exit 1; }
exec python3 "$(dirname "${BASH_SOURCE[0]}")/blaster_bench.py" suite "$@"
