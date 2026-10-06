#!/usr/bin/env bash
# Run all six Blaster baseline suites into one results directory: run_all.sh [--out DIR] [--jobs N]
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/blaster_bench.py" all "$@"
