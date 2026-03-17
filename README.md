# Run FMU Simulations Skill

Codex skill for inspecting FMU files, checking FMI modes and step information, running FMU simulations, exporting result data, and plotting signals from recorded datasets.

## Repository Layout

- `run-fmu-simulations/`
  The skill folder to place under `~/.codex/skills/`
- `run-fmu-simulations/SKILL.md`
  Main skill instructions
- `run-fmu-simulations/scripts/inspect_fmu.py`
  Inspect interface, modes, and step-related metadata
- `run-fmu-simulations/scripts/run_fmu.py`
  Run simulations, handle scalar and array inputs, and export CSV results
- `run-fmu-simulations/scripts/data_tools.py`
  Extract or plot result data from CSV files

## Install

Copy `run-fmu-simulations/` into your Codex skills directory:

```text
~/.codex/skills/run-fmu-simulations/
```

## Capabilities

- Inspect FMU interface variables for FMI 2.x and FMI 3.0 models
- Inspect supported execution mode and default/fixed step information
- Run FMU simulations with scalar or array input signals
- Export outputs, locals, and inputs to CSV
- Plot recorded variables from CSV files
- Distinguish `ModelExchange` solver step size from `CoSimulation` communication step size

## Notes

- `run_fmu.py` uses `--communication-step-size` for `CoSimulation` FMUs
- `run_fmu.py` uses `--step-size` for `ModelExchange` FMUs
- If no step is provided, the script reports the effective step it actually uses
- Some FMUs with invalid `modelDescription.xml` require `--no-validate`
