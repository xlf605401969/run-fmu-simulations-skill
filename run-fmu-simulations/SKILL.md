---
name: run-fmu-simulations
description: Inspect FMU files, identify supported FMI execution modes, run FMU simulations, collect time-series data into files, and extract or plot variables from recorded datasets. Use when Codex needs to work with `.fmu` models for interface discovery, capability checks, simulation runs, CSV export, post-processing, or plotting.
---

# Run FMU Simulations

## Overview

Use the bundled scripts to inspect an `.fmu`, run a simulation, save results to CSV, then extract or plot selected variables from the generated data file.

Prefer the scripts over ad-hoc Python snippets so outputs stay consistent and repeatable.

## Quick Start

1. Inspect the FMU interface.
2. Inspect supported FMI modes and capability flags.
3. Run the FMU and save results to CSV.
4. Extract the variables you need or plot them from the CSV.

## Inspect the FMU

Use `scripts/inspect_fmu.py` for both interface and mode inspection.

Commands:

```powershell
python scripts/inspect_fmu.py interface path\to\model.fmu
python scripts/inspect_fmu.py modes path\to\model.fmu
```

Use `--format json` when the result needs to be consumed programmatically.

## Run the FMU

Use `scripts/run_fmu.py`.

Example:

```powershell
python scripts/run_fmu.py path\to\model.fmu `
  --output data\result.csv `
  --input-file data\inputs.csv `
  --start-time 0 `
  --stop-time 10 `
  --communication-step-size 0.01 `
  --start-value gain=2.0 `
  --start-value enabled=true
```

Notes:

- Install `fmpy` before running simulations.
- Use `--input-file` to provide time-varying input signals as CSV with a `time` column and one column per FMU input variable.
- For array variables, use 1-based FMI cross-check style column names. One-dimensional arrays look like `Vabc[1]`, `Vabc[2]`, `Vabc[3]`; multi-dimensional arrays use comma-separated indices such as `A[1,1]`, `A[1,2]`.
- Use `--communication-step-size` for CoSimulation FMUs. This maps to FMPy's `output_interval`, which is the communication step passed into `doStep()`.
- Use `--step-size` only for ModelExchange FMUs, where it controls the solver step size.
- If no step size is passed, `run_fmu.py` prints the effective step that will actually be used and writes it to the sidecar JSON metadata.
- Pass repeated `--start-value name=value` pairs to override FMU start values.
- By default the output CSV includes `time` plus FMU `output`, `local`, and `input` variables, so input traces are captured together with outputs.
- Array outputs are flattened to CSV columns using the same 1-based naming rule, for example `Uabc[1]`, `Uabc[2]`, `Uabc[3]` or `A[1,1]`, `A[1,2]`.
- Pass repeated `--output-vars` names to limit exported columns explicitly.
- A sidecar JSON file is written next to the CSV with run metadata.

Example `inputs.csv`:

```text
time,Vabc[1],Vabc[2],Vabc[3],Tm
0.0,0.0,0.0,0.0,0.0
0.005,12.0,-6.0,-6.0,1.0
0.01,0.0,0.0,0.0,0.0
```

## Extract or Plot Recorded Data

Use `scripts/data_tools.py`.

Examples:

```powershell
python scripts/data_tools.py extract data\result.csv --columns time speed --output data\speed.csv
python scripts/data_tools.py plot data\result.csv --y speed torque --output plots\speed-torque.png
```

Use `--start-time` and `--stop-time` on `extract` or `plot` to limit the time window. Use `--format json` on `extract` for machine-readable output.

## Data Format

Read [references/data-format.md](references/data-format.md) when you need the CSV schema, sidecar metadata schema, or filtering behavior.

## Script Map

- `scripts/inspect_fmu.py`: Read `modelDescription.xml` directly from the FMU zip and report metadata, variables, and supported modes. No third-party dependencies required.
- `scripts/run_fmu.py`: Run the FMU with `fmpy`, export a CSV, and save run metadata to JSON.
- `scripts/data_tools.py`: Extract filtered data from the CSV and optionally generate plots with `matplotlib`.

## Failure Handling

- If `fmpy` is missing, stop and tell the user to install it before running simulations.
- If `matplotlib` is missing, allow extraction to proceed and fail only for plotting.
- If the FMU does not expose the requested variables, inspect the interface first and then rerun with valid variable names.

## Preconditions

- Use Python 3.10+.
- Install `fmpy` to run simulations.
- Install `matplotlib` only when plotting is required.
- Keep output CSV paths outside the skill directory when generating user artifacts.
