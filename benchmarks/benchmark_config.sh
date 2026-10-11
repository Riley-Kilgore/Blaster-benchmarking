#!/usr/bin/env bash
# Configuration file for benchmark system

# macOS compatibility: prefer gtimeout (GNU coreutils) over BSD timeout
# Install via: brew install coreutils
if ! command -v timeout &>/dev/null && command -v gtimeout &>/dev/null; then
    timeout() { gtimeout "$@"; }
    export -f timeout
fi

# Directories
TEMP_DIR="${TEMP_DIR:-benchmark_temp}"
OUTPUT_DIR="${OUTPUT_DIR:-benchmark_results}"
CACHE_DIR="${CACHE_DIR:-${TEMP_DIR}/cache}"

# Execution settings
TIMEOUT="${TIMEOUT:-20}"
PARALLEL_JOBS="${PARALLEL_JOBS:-1}"
DRY_RUN="${DRY_RUN:-0}"

# Output settings
VERBOSE="${VERBOSE:-0}"
QUIET="${QUIET:-0}"

# Benchmark definitions
# Format: import_path:file_path:display_name:timeout_override
# Paths are relative to the project root (parent of benchmarks/ directory)
BENCHMARK_FILES=(
    "BlasterBenchmarks.NNG4.NNG4:BlasterBenchmarks/NNG4/NNG4.lean:NNG4:20"
    "BlasterBenchmarks.STG4.STG4:BlasterBenchmarks/STG4/STG4.lean:STG4:20"
    "BlasterBenchmarks.ITL4.ITLS:BlasterBenchmarks/ITL4/ITL4.lean:ITL4:20"
    # MiniF2F is held out and not on this branch (README, "Held-out suites").
    "Verina:BlasterBenchmarks/Verina:Verina:20:taskdir"
    "UPLC:BlasterBenchmarks/UPLC/Width:UPLCWidth:90:taskdir"
    "UPLC:BlasterBenchmarks/UPLC/Depth:UPLCDepth:90:taskdir"
)

# Tactics to test
#"rfl" "simp" "decide" "decide +native" "omega" "grind" "smt" "auto" "aesop" "hammer" "blaster (only-optimize: 1)" "blaster"
TACTICS=("smt +model" "blaster" "auto" "aesop" "hammer")

# Tactic-specific imports
# Add entries here if a tactic requires a specific import
declare -A TACTIC_IMPORTS=(
    ["blaster"]="Blaster.Command.Tactic"
    ["blaster (only-optimize: 1)"]="Blaster.Command.Tactic"
    ["auto"]="Auto.Tactic"
    ["hammer"]="Hammer"
    ["aesop"]="Aesop"
    ["smt +model"]="Smt"

)

declare -A TACTIC_PREAMBLES=(
  ["auto"]=$'set_option auto.smt.trust true\nset_option auto.smt true'
)

# Retrieve tactic-specific import statements
get_tactic_import() {
    echo "${TACTIC_IMPORTS[$1]:-}"
}

# Retrieve tactic-specific preamble commands
get_tactic_preamble() {
    echo "${TACTIC_PREAMBLES[$1]:-}"
}

# File locations
CONFIG_FILE="${CONFIG_FILE:-benchmark.conf}"
BASELINE_FILE="${BASELINE_FILE:-}"

# Cache settings
ENABLE_CACHE="${ENABLE_CACHE:-1}"

# Command arguments array
COMMAND_ARGS=()

# Results archiving
ARCHIVE_RESULTS="${ARCHIVE_RESULTS:-1}"
ARCHIVE_DIR="${ARCHIVE_DIR:-${OUTPUT_DIR}/archive}"

# Timing thresholds (milliseconds)
FAST_THRESHOLD=100
SLOW_THRESHOLD=1000

# Export all settings
export TEMP_DIR OUTPUT_DIR CACHE_DIR TIMEOUT PARALLEL_JOBS
export VERBOSE QUIET DRY_RUN ENABLE_CACHE

# Export associative arrays (Bash 5+)
export TACTIC_IMPORTS
export TACTIC_PREAMBLES

# Export functions
export -f get_tactic_import
export -f get_tactic_preamble