# Lean Tactic Benchmark System

A comprehensive benchmarking system for testing Lean 4 tactics with support for parallel execution, caching, multiple output formats, and baseline comparison.

## Features

- ✅ **Parallel Execution**: Run tests concurrently for faster results
- ✅ **Result Caching**: Avoid redundant test execution
- ✅ **Multiple Output Formats**: CSV, LaTeX, JSON, and visualizations
- ✅ **Baseline Comparison**: Track improvements and regressions
- ✅ **Progress Tracking**: Real-time progress with ETA
- ✅ **Dry Run Mode**: Preview what will be executed
- ✅ **Summary Statistics**: Automatic aggregation and analysis
- ✅ **Configurable**: External configuration file support
- ✅ **Archive Management**: Automatic archiving of previous results
- ✅ **Visual Analytics**: Generate comparison plots and heatmaps

## Quick Start

```bash
# Run all benchmarks (sequential)
./benchmark.sh run

# Run with 4 parallel jobs
./benchmark.sh run -p 4 -v

# Test a specific theorem
./benchmark.sh test NNG4 zero_add blaster

# Show summary of results
./benchmark.sh summary

# Compare with baseline
./benchmark.sh compare -b benchmark_results/baseline.csv
```

## Installation

1. Place all benchmark scripts in the same directory:
   - `benchmark.sh` - Main entry point
   - `benchmark_config.sh` - Configuration
   - `benchmark_utils.sh` - Utility functions
   - `benchmark_core.sh` - Core testing logic
   - `benchmark_formatters.sh` - Output formatting

2. Make the main script executable:
```bash
chmod +x benchmark.sh
```

3. (Optional) Create a configuration file:
```bash
cp benchmark.conf.example benchmark.conf
# Edit benchmark.conf with your settings
```

## Usage

### Commands

#### `run` - Run Benchmarks
Execute all configured benchmarks.

```bash
./benchmark.sh run [OPTIONS]

Options:
  -p, --parallel N    Run with N parallel jobs
  -t, --timeout N     Set timeout to N seconds
  -v, --verbose       Enable verbose output
  -q, --quiet         Minimal output
  -d, --dry-run       Preview without executing
```

Examples:
```bash
# Run with default settings
./benchmark.sh run

# Run with 8 parallel jobs and verbose output
./benchmark.sh run -p 8 -v

# Dry run with 30-second timeout
./benchmark.sh run -d -t 30
```

#### `test` - Test Single Theorem
Test a specific theorem with a specific tactic.

```bash
./benchmark.sh test <benchmark> <theorem> <tactic>
```

Examples:
```bash
./benchmark.sh test NNG4 zero_add blaster
./benchmark.sh test STG4 some_theorem simp
```

#### `summary` - Show Statistics
Display summary statistics from existing results.

```bash
./benchmark.sh summary
```

#### `compare` - Compare with Baseline
Compare current results with a baseline to detect improvements and regressions.

```bash
./benchmark.sh compare -b <baseline_file>
```

Example:
```bash
./benchmark.sh compare -b benchmark_results/baseline.csv
```

#### `latex` - Generate LaTeX
Generate LaTeX tables from existing CSV results.

```bash
./benchmark.sh latex
```

Output: `benchmark_results/all_benchmarks.tex`

#### `json` - Generate JSON
Generate JSON output from existing CSV results.

```bash
./benchmark.sh json
```

Output: `benchmark_results/all_benchmarks.json`

#### `list` - List Benchmarks
Show all configured benchmarks and their status.

```bash
./benchmark.sh list
```

#### `clean` - Clean Output
Remove all output files and temporary data.

```bash
./benchmark.sh clean
```

## Configuration

### Configuration File

Create `benchmark.conf` to customize behavior:

```bash
# Execution
TIMEOUT=10
PARALLEL_JOBS=4
VERBOSE=1

# Directories
OUTPUT_DIR="my_results"

# Benchmarks
BENCHMARK_FILES=(
    "MyBenchmark.Test:path/to/test.lean:Test:5"
)

# Tactics
TACTICS=("rfl" "simp" "blaster" "my_custom_tactic")
```

### Environment Variables

All configuration options can be set via environment variables:

```bash
# Run with custom settings
TIMEOUT=30 PARALLEL_JOBS=8 VERBOSE=1 ./benchmark.sh run
```

### Benchmark Definition Format

Each benchmark is defined as a colon-separated string:

```
import_path:file_path:display_name:timeout
```

- `import_path`: Lean import path (e.g., `BlasterBenchmarks.NNG4.NNG4`)
- `file_path`: Relative path to file (e.g., `BlasterBenchmarks/NNG4/NNG4.lean`)
- `display_name`: Short name for output (e.g., `NNG4`)
- `timeout`: Optional timeout override in seconds

Example:
```bash
BENCHMARK_FILES=(
    "BlasterBenchmarks.NNG4.NNG4:BlasterBenchmarks/NNG4/NNG4.lean:NNG4:5"
    "BlasterBenchmarks.STG4.STG4:BlasterBenchmarks/STG4/STG4.lean:STG4:10"
)
```

## Output Formats

### CSV Output

Located in `benchmark_results/<benchmark>_results.csv`

Format:
```csv
Benchmark,Theorem,Statement,rfl_time,rfl_status,simp_time,simp_status,...
NNG4,one_add_one,"1 + 1 = 2",50,OK,timeout,TIMEOUT,...
```

### LaTeX Output

Located in `benchmark_results/all_benchmarks.tex`

Generates publication-ready tables with color coding:
- Green: Fast (< 100ms)
- Black: Normal (100-1000ms)  
- Orange: Slow (> 1000ms)
- Red: Timeout or failure

### JSON Output

Located in `benchmark_results/all_benchmarks.json`

Structured format for programmatic analysis:
```json
{
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "timeout": 5,
    "tactics": ["rfl", "simp", ...]
  },
  "benchmarks": [
    {
      "name": "NNG4",
      "theorems": [
        {
          "name": "one_add_one",
          "statement": "1 + 1 = 2",
          "results": {
            "rfl": {"time_ms": 50, "status": "OK"},
            ...
          }
        }
      ]
    }
  ]
}
```

## Caching

The system caches test results based on:
- Benchmark name
- Theorem name
- Tactic used
- File content hash

Cache is stored in `benchmark_temp/cache/`.

To disable caching:
```bash
ENABLE_CACHE=0 ./benchmark.sh run
```

To clear cache:
```bash
rm -rf benchmark_temp/cache
```

## Parallel Execution

Parallel execution uses `xargs -P` to run multiple tests concurrently.

Benefits:
- Faster overall execution
- Better CPU utilization
- Scales with available cores

Considerations:
- Progress tracking is less detailed in parallel mode
- Memory usage increases with parallel jobs
- File I/O may become a bottleneck

Recommended settings:
- Local machine: `PARALLEL_JOBS=4-8`
- CI server: `PARALLEL_JOBS=$(nproc)`

## Baseline Comparison

To track performance over time:

1. Run initial benchmark:
```bash
./benchmark.sh run
```

2. Save as baseline:
```bash
cp benchmark_results/NNG4_results.csv benchmark_results/baseline.csv
```

3. After changes, compare:
```bash
./benchmark.sh compare -b benchmark_results/baseline.csv
```

The comparison will show:
- ✅ Improvements (failures → success, slower → faster)
- ❌ Regressions (success → failure, faster → slower)
- ↔️ Unchanged results

## Advanced Usage

### Custom Tactic Imports

Add imports for custom tactics in `benchmark_config.sh`:

```bash
declare -A TACTIC_IMPORTS=(
    ["blaster"]="Blaster.Command.Tactic"
    ["my_tactic"]="My.Custom.Import"
)
```

### Multiple Configuration Files

Use different configs for different scenarios:

```bash
./benchmark.sh run -c quick_test.conf
./benchmark.sh run -c full_suite.conf
```

### CI Integration

Example GitHub Actions workflow:

```yaml
- name: Run Benchmarks
  run: |
    ./benchmark.sh run -p $(nproc) -q
    
- name: Compare with Baseline
  run: |
    ./benchmark.sh compare -b baseline.csv || echo "Regressions detected"
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: benchmark_results/
```

### Timeout Strategy

Different theorems may need different timeouts:

```bash
# Quick theorems: 5s timeout
# Complex theorems: 30s timeout
BENCHMARK_FILES=(
    "Simple:path/simple.lean:Simple:5"
    "Complex:path/complex.lean:Complex:30"
)
```

## Troubleshooting

### Tests timing out
- Increase `TIMEOUT` value
- Check if Lean environment is properly configured
- Verify `lake` is in PATH

### Out of disk space
- Script checks for 100MB free space
- Clean old results: `./benchmark.sh clean`
- Clear cache: `rm -rf benchmark_temp/cache`

### Parallel execution issues
- Reduce `PARALLEL_JOBS`
- Check system resource limits
- Try sequential mode: `PARALLEL_JOBS=1`

### Cache issues
- Clear cache: `rm -rf benchmark_temp/cache`
- Disable cache: `ENABLE_CACHE=0`
- 
## Contributing

When adding new features:
1. Add configuration to `benchmark_config.sh`
2. Add utility functions to `benchmark_utils.sh`
3. Add core logic to `benchmark_core.sh`
4. Add output formatting to `benchmark_formatters.sh`
5. Update main command handling in `benchmark.sh`
6. Document in this README

## License

[Add your license here]