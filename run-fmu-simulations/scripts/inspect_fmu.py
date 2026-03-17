#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET


def load_model_description(fmu_path: Path) -> ET.Element:
    if not fmu_path.is_file():
        raise FileNotFoundError(f"FMU not found: {fmu_path}")
    with zipfile.ZipFile(fmu_path) as archive:
        with archive.open("modelDescription.xml") as handle:
            tree = ET.parse(handle)
    return tree.getroot()


def text_or_none(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


def scalar_variables(root: ET.Element) -> list[dict[str, object]]:
    variables: list[dict[str, object]] = []
    model_variables = root.find("ModelVariables")
    if model_variables is None:
        return variables

    for variable in list(model_variables):
        if variable.tag == "ScalarVariable":
            # FMI 1.x / 2.0: type information is nested below ScalarVariable.
            type_node = next(iter(variable), None)
            dimensions = []
            if type_node is not None:
                for dimension in type_node.findall("Dimension"):
                    dimensions.append(
                        {
                            "start": text_or_none(dimension.attrib.get("start")),
                            "valueReference": text_or_none(dimension.attrib.get("valueReference")),
                        }
                    )
            variable_type = type_node.tag if type_node is not None else None
            start = type_node.attrib.get("start") if type_node is not None else None
            unit = type_node.attrib.get("unit") if type_node is not None else None
        else:
            # FMI 3.0: the variable node itself carries the type, dimensions are direct children.
            type_node = variable
            dimensions = []
            for dimension in variable.findall("Dimension"):
                dimensions.append(
                    {
                        "start": text_or_none(dimension.attrib.get("start")),
                        "valueReference": text_or_none(dimension.attrib.get("valueReference")),
                    }
                )
            variable_type = variable.tag
            start = variable.attrib.get("start")
            unit = variable.attrib.get("unit")

        entry = {
            "name": variable.attrib.get("name"),
            "valueReference": variable.attrib.get("valueReference"),
            "causality": text_or_none(variable.attrib.get("causality")),
            "variability": text_or_none(variable.attrib.get("variability")),
            "initial": text_or_none(variable.attrib.get("initial")),
            "description": text_or_none(variable.attrib.get("description")),
            "type": variable_type,
            "start": start,
            "unit": unit,
            "dimensions": dimensions,
        }
        variables.append(entry)
    return variables


def supported_modes(root: ET.Element) -> list[dict[str, object]]:
    mode_nodes = ["ModelExchange", "CoSimulation", "ScheduledExecution"]
    modes: list[dict[str, object]] = []

    for node_name in mode_nodes:
        node = root.find(node_name)
        if node is None:
            continue
        capabilities = {k: v for k, v in sorted(node.attrib.items())}
        if node_name == "CoSimulation" and "fixedInternalStepSize" not in capabilities:
            capabilities["fixedInternalStepSize"] = None
        modes.append({"mode": node_name, "capabilities": capabilities})
    return modes


def default_experiment(root: ET.Element) -> dict[str, object] | None:
    node = root.find("DefaultExperiment")
    if node is None:
        return None
    return {
        "startTime": text_or_none(node.attrib.get("startTime")),
        "stopTime": text_or_none(node.attrib.get("stopTime")),
        "stepSize": text_or_none(node.attrib.get("stepSize")),
        "tolerance": text_or_none(node.attrib.get("tolerance")),
    }


def root_metadata(root: ET.Element) -> dict[str, object]:
    return {
        "fmiVersion": root.attrib.get("fmiVersion"),
        "modelName": root.attrib.get("modelName"),
        "guid": root.attrib.get("guid") or root.attrib.get("instantiationToken"),
        "description": text_or_none(root.attrib.get("description")),
        "author": text_or_none(root.attrib.get("author")),
        "version": text_or_none(root.attrib.get("version")),
        "generationTool": text_or_none(root.attrib.get("generationTool")),
        "generationDateAndTime": text_or_none(root.attrib.get("generationDateAndTime")),
        "defaultExperiment": default_experiment(root),
        "variableCount": len(scalar_variables(root)),
        "numberOfContinuousStates": root.attrib.get("numberOfContinuousStates"),
        "numberOfEventIndicators": root.attrib.get("numberOfEventIndicators"),
    }


def print_table(rows: Iterable[dict[str, object]], columns: list[str]) -> None:
    row_list = list(rows)
    widths = []
    for column in columns:
        width = len(column)
        for row in row_list:
            width = max(width, len(str(row.get(column, "") or "")))
        widths.append(width)

    header = "  ".join(column.ljust(width) for column, width in zip(columns, widths))
    print(header)
    print("  ".join("-" * width for width in widths))
    for row in row_list:
        print("  ".join(str(row.get(column, "") or "").ljust(width) for column, width in zip(columns, widths)))


def handle_interface(args: argparse.Namespace) -> int:
    root = load_model_description(Path(args.fmu))
    payload = {
        "metadata": root_metadata(root),
        "variables": scalar_variables(root),
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return 0

    print(json.dumps(payload["metadata"], indent=2))
    print()
    columns = ["name", "type", "causality", "variability", "initial", "start", "unit", "dimensions", "valueReference"]
    print_table(payload["variables"], columns)
    return 0


def handle_modes(args: argparse.Namespace) -> int:
    root = load_model_description(Path(args.fmu))
    payload = {
        "metadata": root_metadata(root),
        "modes": supported_modes(root),
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2))
        return 0

    print(json.dumps(payload["metadata"], indent=2))
    print()
    if not payload["modes"]:
        print("No explicit FMI mode nodes found in modelDescription.xml")
        return 0

    for mode in payload["modes"]:
        print(mode["mode"])
        capabilities = mode["capabilities"]
        if not capabilities:
            print("  capabilities: none")
            continue
        for key, value in capabilities.items():
            print(f"  {key}: {value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect FMU interface and supported modes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    interface_parser = subparsers.add_parser("interface", help="Show FMU variables and metadata.")
    interface_parser.add_argument("fmu", help="Path to the FMU file.")
    interface_parser.add_argument("--format", choices=["table", "json"], default="table")
    interface_parser.set_defaults(func=handle_interface)

    modes_parser = subparsers.add_parser("modes", help="Show supported FMI modes and capability flags.")
    modes_parser.add_argument("fmu", help="Path to the FMU file.")
    modes_parser.add_argument("--format", choices=["text", "json"], default="text")
    modes_parser.set_defaults(func=handle_modes)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except zipfile.BadZipFile:
        print("Invalid FMU archive.", file=sys.stderr)
        return 1
    except KeyError:
        print("modelDescription.xml is missing from the FMU.", file=sys.stderr)
        return 1
    except ET.ParseError as exc:
        print(f"Failed to parse modelDescription.xml: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
