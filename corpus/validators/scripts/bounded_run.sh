#!/usr/bin/env bash
# Usage: bounded_run.sh <label> <timeout-seconds> <cwd> -- <command...>
# Runs the command in its own session/process group under a wall-clock bound,
# kills the whole group on timeout (SIGTERM, then SIGKILL after 10 s), writes
# <label>.log and appends one TSV row to commands.tsv in this logs directory.
set -u
LOGDIR="$(cd "$(dirname "$0")/../logs" && pwd)"
label="$1"; bound="$2"; cwd="$3"; shift 4
log="$LOGDIR/$label.log"
start=$(date +%s.%N)
{ echo "# cwd: $cwd"; echo "# cmd: $*"; echo "# bound: ${bound}s"; echo "# start: $(date -u +%FT%TZ)"; } > "$log"
( cd "$cwd" && exec setsid timeout -k 10 "$bound" "$@" ) >> "$log" 2>&1
rc=$?
end=$(date +%s.%N)
secs=$(python3 -c "print(round($end-$start,2))")
# report any live (non-zombie) lean/z3/lake survivors
survivors=$(ps -eo pid,stat,comm | awk '$2 !~ /Z/ && ($3=="lean"||$3=="z3"||$3=="lake"||$3=="aiken")' | wc -l)
{ echo "# exit: $rc"; echo "# seconds: $secs"; echo "# live lean/z3/lake/aiken survivors after run: $survivors"; } >> "$log"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$label" "$rc" "$secs" "$cwd" "$*" >> "$LOGDIR/commands.tsv"
echo "$label exit=$rc secs=$secs survivors=$survivors"
exit $rc
