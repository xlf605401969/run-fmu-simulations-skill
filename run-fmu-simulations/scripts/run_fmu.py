#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from ctypes import c_int
from pathlib import Path
from typing import Any


def parse_start_values(items: list[str]) -> dict[str, object]:
    values: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid start value '{item}'. Use name=value.")
        name, raw_value = item.split("=", 1)
        name = name.strip()
        raw_value = raw_value.strip()
        if not name:
            raise ValueError(f"Invalid start value '{item}'. Name is empty.")
        lowered = raw_value.lower()
        if lowered in {"true", "false"}:
            values[name] = lowered == "true"
        else:
            try:
                values[name] = int(raw_value)
            except ValueError:
                try:
                    values[name] = float(raw_value)
                except ValueError:
                    values[name] = raw_value
    return values


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_fmpy():
    try:
        from fmpy import simulate_fmu
        from fmpy.model_description import read_model_description
        from fmpy.util import read_csv as read_fmpy_csv
        from fmpy.util import write_csv as write_fmpy_csv
    except ImportError as exc:
        raise RuntimeError("fmpy is required to run FMU simulations. Install it with 'pip install fmpy'.") from exc
    return simulate_fmu, read_model_description, read_fmpy_csv, write_fmpy_csv


def default_outputs(model_description) -> list[str]:
    names: list[str] = []
    for variable in model_description.modelVariables:
        causality = getattr(variable, "causality", None)
        if causality in {"output", "local", "input"}:
            names.append(variable.name)
    if not names:
        names = [variable.name for variable in model_description.modelVariables[:20]]
    return names


def build_variable_map(model_description) -> dict[str, Any]:
    return {variable.name: variable for variable in model_description.modelVariables}


def infer_communication_step_size(model_description, start_time: float, stop_time: float) -> float:
    interval = None
    co_simulation = getattr(model_description, "coSimulation", None)
    experiment = getattr(model_description, "defaultExperiment", None)

    fixed_internal = getattr(co_simulation, "fixedInternalStepSize", None) if co_simulation is not None else None
    experiment_step = getattr(experiment, "stepSize", None) if experiment is not None else None

    if fixed_internal is not None:
        interval = float(fixed_internal)
    elif experiment_step is not None:
        interval = float(experiment_step)

    if interval is not None:
        while (stop_time - start_time) / interval > 1000:
            interval *= 2
        return interval

    from fmpy.simulation import auto_interval

    return float(auto_interval(stop_time - start_time))


def patch_fmpy_input_support() -> None:
    import numpy as np
    import fmpy.fmi3 as fmi3
    import fmpy.simulation as sim

    if getattr(sim.Input, "_codex_array_patch", False):
        return

    class CompatibleInput(sim.Input):
        _codex_array_patch = True

        def __init__(self, fmu, modelDescription, signals, set_input_derivatives=False):
            self.fmu = fmu

            if signals is None:
                self.t = None
                return

            self.t = signals[signals.dtype.names[0]]
            self.t_events = sim.Input.findEvents(signals, modelDescription)
            self.set_input_derivatives = set_input_derivatives

            is_fmi1 = isinstance(fmu, sim._FMU1)
            is_fmi2 = isinstance(fmu, sim._FMU2)

            setters = {}
            if is_fmi1:
                setters["Real"] = (fmu.fmi1SetReal, sim.fmi1Real)
                setters["Integer"] = (fmu.fmi1SetInteger, sim.fmi1Integer)
                setters["Boolean"] = (fmu.fmi1SetBoolean, sim.c_int8)
                setters["Enumeration"] = (fmu.fmi1SetInteger, sim.fmi1Integer)
            elif is_fmi2:
                setters["Real"] = (fmu.fmi2SetReal, sim.fmi2Real)
                setters["Integer"] = (fmu.fmi2SetInteger, sim.fmi2Integer)
                setters["Boolean"] = (fmu.fmi2SetBoolean, sim.fmi2Boolean)
                setters["Enumeration"] = (fmu.fmi2SetInteger, sim.fmi2Integer)
            else:
                setters["Float32"] = (fmu.fmi3SetFloat32, fmi3.fmi3Float32)
                setters["Float64"] = (fmu.fmi3SetFloat64, fmi3.fmi3Float64)
                setters["Int8"] = (fmu.fmi3SetInt8, fmi3.fmi3Int8)
                setters["UInt8"] = (fmu.fmi3SetUInt8, fmi3.fmi3UInt8)
                setters["Int16"] = (fmu.fmi3SetInt16, fmi3.fmi3Int16)
                setters["UInt16"] = (fmu.fmi3SetUInt16, fmi3.fmi3UInt16)
                setters["Int32"] = (fmu.fmi3SetInt32, fmi3.fmi3Int32)
                setters["UInt32"] = (fmu.fmi3SetUInt32, fmi3.fmi3UInt32)
                setters["Int64"] = (fmu.fmi3SetInt64, fmi3.fmi3Int64)
                setters["UInt64"] = (fmu.fmi3SetUInt64, fmi3.fmi3UInt64)
                setters["Boolean"] = (fmu.fmi3SetBoolean, fmi3.fmi3Boolean)
                setters["Enumeration"] = (fmu.fmi3SetInt64, fmi3.fmi3Int64)

            self.continuous = []
            self.discrete = []

            for variable in modelDescription.modelVariables:
                if variable.causality != "input" and variable.variability != "tunable":
                    continue

                if variable.name not in signals.dtype.names:
                    if variable.causality == "input":
                        print(f'Warning: missing input for variable "{variable.name}"')
                    continue

                setter, value_type = setters[variable.type]
                raw_values = np.asarray(signals[variable.name], dtype=value_type)
                n_values = int(np.prod(variable.shape)) if getattr(variable, "shape", None) else 1
                table = raw_values.reshape((len(self.t), n_values)).T
                vrs = (sim.c_uint32 * 1)(variable.valueReference)
                values = (value_type * n_values)()

                if variable.type in {"Float32", "Float64", "Real"} and variable.variability not in ["discrete", "tunable"]:
                    order = (c_int * n_values)(*([1] * n_values))
                    derivatives = (value_type * n_values)()
                    self.continuous.append((vrs, values, order, derivatives, table, setter))
                else:
                    self.discrete.append((vrs, values, table, setter))

        def apply(self, time, continuous=True, discrete=True, after_event=False):
            if self.t is None:
                return

            is_fmi1 = isinstance(self.fmu, sim._FMU1)
            is_fmi3 = isinstance(self.fmu, fmi3._FMU3)

            if continuous:
                for vrs, values, order, derivatives, table, setter in self.continuous:
                    values[:], derivatives[:] = self.interpolate(
                        time=time, t=self.t, table=table, discrete=False, after_event=after_event
                    )
                    if is_fmi3:
                        setter(self.fmu.component, vrs, len(vrs), values, len(values))
                    else:
                        setter(self.fmu.component, vrs, len(vrs), values)

                    if self.set_input_derivatives and hasattr(self.fmu, "fmi2SetRealInputDerivatives"):
                        self.fmu.fmi2SetRealInputDerivatives(self.fmu.component, vrs, len(vrs), order, derivatives)

            if discrete:
                for vrs, values, table, setter in self.discrete:
                    values[:], _ = self.interpolate(time=time, t=self.t, table=table, discrete=True, after_event=after_event)

                    if is_fmi1 and values._type_ == sim.c_int8:
                        setter(self.fmu.component, vrs, len(vrs), sim.cast(values, sim.POINTER(sim.c_char)))
                    else:
                        if is_fmi3:
                            setter(self.fmu.component, vrs, len(vrs), values, len(values))
                        else:
                            setter(self.fmu.component, vrs, len(vrs), values)

    sim.Input = CompatibleInput


def load_input_signals(input_path: Path, model_description, read_fmpy_csv):
    if not input_path.is_file():
        raise FileNotFoundError(f"Input signal file not found: {input_path}")

    variable_map = build_variable_map(model_description)
    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Input signal CSV is missing a header row.")
        raw_columns = list(reader.fieldnames)
        if "time" not in raw_columns:
            raise ValueError("Input signal CSV must contain a 'time' column.")
        for row in reader:
            for field in raw_columns:
                raw = row.get(field)
                if raw is None or raw == "":
                    raise ValueError(f"Input signal CSV contains an empty value in column '{field}'.")

    signals = read_fmpy_csv(str(input_path), structured=True)
    signal_names = [name for name in signals.dtype.names if name != "time"]
    if not signal_names:
        raise ValueError("Input signal CSV must contain at least one FMU input column.")

    missing = [name for name in signal_names if name not in variable_map]
    if missing:
        raise ValueError(f"Input signal columns are not FMU variables: {', '.join(missing)}")

    non_inputs = [name for name in signal_names if getattr(variable_map[name], "causality", None) != "input"]
    if non_inputs:
        raise ValueError(f"Input signal columns must map to FMU input variables: {', '.join(non_inputs)}")

    return signals, signal_names


def write_csv_result(result, output_path: Path, write_fmpy_csv) -> int:
    ensure_parent(output_path)
    write_fmpy_csv(str(output_path), result)
    return len(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an FMU simulation and export results to CSV.")
    parser.add_argument("fmu", help="Path to the FMU file.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--input-file", help="CSV file with 'time' and FMU input variable columns.")
    parser.add_argument("--no-validate", action="store_true", help="Skip FMU modelDescription validation.")
    parser.add_argument("--start-time", type=float, default=0.0)
    parser.add_argument("--stop-time", type=float, required=True)
    parser.add_argument("--step-size", type=float, default=None, help="Solver step size for ModelExchange FMUs.")
    parser.add_argument(
        "--communication-step-size",
        type=float,
        default=None,
        help="Communication step size for CoSimulation FMUs. Mapped to FMPy's output_interval.",
    )
    parser.add_argument("--solver", default="CVode")
    parser.add_argument("--relative-tolerance", type=float, default=None)
    parser.add_argument("--output-vars", nargs="+", default=None, help="Variable names to export.")
    parser.add_argument("--start-value", action="append", default=[], help="Override start values as name=value.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        simulate_fmu, read_model_description, read_fmpy_csv, write_fmpy_csv = load_fmpy()
        patch_fmpy_input_support()
        start_values = parse_start_values(args.start_value)
        fmu_path = Path(args.fmu)
        output_path = Path(args.output)

        model_description = read_model_description(str(fmu_path), validate=not args.no_validate)
        is_co_simulation = getattr(model_description, "coSimulation", None) is not None
        input_signals = None
        input_columns: list[str] = []
        if args.input_file:
            input_signals, input_columns = load_input_signals(Path(args.input_file), model_description, read_fmpy_csv)
        outputs = args.output_vars or default_outputs(model_description)
        effective_step_size = args.step_size
        effective_communication_step_size = args.communication_step_size

        simulate_kwargs = {
            "filename": str(fmu_path),
            "validate": not args.no_validate,
            "start_time": args.start_time,
            "stop_time": args.stop_time,
            "output": outputs,
            "solver": args.solver,
            "relative_tolerance": args.relative_tolerance,
            "start_values": start_values,
            "input": input_signals,
        }

        if is_co_simulation:
            if args.communication_step_size is not None:
                simulate_kwargs["output_interval"] = args.communication_step_size
            else:
                effective_communication_step_size = infer_communication_step_size(
                    model_description, args.start_time, args.stop_time
                )
            print(f"FMU type: CoSimulation")
            print(f"Effective communication step size: {effective_communication_step_size}")
        else:
            if args.step_size is not None:
                simulate_kwargs["step_size"] = args.step_size
            print(f"FMU type: ModelExchange")
            print(f"Effective solver step size: {effective_step_size}")

        result = simulate_fmu(
            **simulate_kwargs,
        )

        row_count = write_csv_result(result, output_path, write_fmpy_csv)
        metadata_path = output_path.with_suffix(".json")
        metadata = {
            "fmu_path": str(fmu_path),
            "input_file": str(Path(args.input_file)) if args.input_file else None,
            "input_columns": input_columns,
            "fmi_type": "CoSimulation" if is_co_simulation else "ModelExchange",
            "validate": not args.no_validate,
            "start_time": args.start_time,
            "stop_time": args.stop_time,
            "step_size": args.step_size,
            "communication_step_size": args.communication_step_size,
            "effective_step_size": effective_step_size,
            "effective_communication_step_size": effective_communication_step_size,
            "solver": args.solver,
            "relative_tolerance": args.relative_tolerance,
            "output_variables": outputs,
            "start_values": start_values,
            "row_count": row_count,
        }
        ensure_parent(metadata_path)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"Wrote {row_count} rows to {output_path}")
        print(f"Wrote metadata to {metadata_path}")
        return 0
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
