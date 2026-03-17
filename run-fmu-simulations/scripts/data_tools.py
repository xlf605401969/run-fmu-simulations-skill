#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path


def read_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")
        rows = list(reader)
        return list(reader.fieldnames), rows


def filter_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    columns: list[str] | None,
    start_time: float | None,
    stop_time: float | None,
) -> tuple[list[str], list[dict[str, str]]]:
    kept_columns = columns or headers
    missing = [column for column in kept_columns if column not in headers]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    filtered: list[dict[str, str]] = []
    for row in rows:
        time_value = float(row["time"]) if "time" in row and row["time"] not in {"", None} else None
        if start_time is not None and time_value is not None and time_value < start_time:
            continue
        if stop_time is not None and time_value is not None and time_value > stop_time:
            continue
        filtered.append({column: row[column] for column in kept_columns})
    return kept_columns, filtered


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def handle_extract(args: argparse.Namespace) -> int:
    headers, rows = read_rows(Path(args.csv))
    columns, filtered = filter_rows(headers, rows, args.columns, args.start_time, args.stop_time)

    if args.format == "json":
        payload = {"columns": columns, "rows": filtered}
        text = json.dumps(payload, indent=2)
        if args.output:
            output_path = Path(args.output)
            ensure_parent(output_path)
            output_path.write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0

    if args.output:
        output_path = Path(args.output)
        ensure_parent(output_path)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(filtered)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=columns)
        writer.writeheader()
        writer.writerows(filtered)
    return 0


def handle_plot(args: argparse.Namespace) -> int:
    try:
        # Keep plotting headless and avoid writing cache files to user-profile paths.
        os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for plotting. Install it with 'pip install matplotlib'.") from exc

    headers, rows = read_rows(Path(args.csv))
    y_columns = args.y or [column for column in headers if column != args.x]
    columns, filtered = filter_rows(headers, rows, [args.x] + y_columns, args.start_time, args.stop_time)
    if args.x not in columns:
        raise ValueError(f"Missing x-axis column: {args.x}")

    x_values = [float(row[args.x]) for row in filtered]
    plt.figure(figsize=(10, 6))
    for column in y_columns:
        plt.plot(x_values, [float(row[column]) for row in filtered], label=column)

    plt.xlabel(args.x)
    plt.ylabel("value")
    plt.title(args.title or Path(args.csv).stem)
    plt.grid(True, alpha=0.3)
    plt.legend()

    output_path = Path(args.output)
    ensure_parent(output_path)
    plt.tight_layout()
    plt.savefig(output_path, dpi=args.dpi)
    print(f"Wrote plot to {output_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract or plot FMU simulation data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Filter CSV data and write CSV or JSON.")
    extract_parser.add_argument("csv", help="Input CSV path.")
    extract_parser.add_argument("--columns", nargs="+", help="Columns to keep.")
    extract_parser.add_argument("--start-time", type=float, default=None)
    extract_parser.add_argument("--stop-time", type=float, default=None)
    extract_parser.add_argument("--output", help="Output file path. Writes to stdout when omitted.")
    extract_parser.add_argument("--format", choices=["csv", "json"], default="csv")
    extract_parser.set_defaults(func=handle_extract)

    plot_parser = subparsers.add_parser("plot", help="Plot selected columns from a CSV file.")
    plot_parser.add_argument("csv", help="Input CSV path.")
    plot_parser.add_argument("--x", default="time", help="X-axis column.")
    plot_parser.add_argument("--y", nargs="+", help="Y-axis columns. Defaults to all columns except x.")
    plot_parser.add_argument("--start-time", type=float, default=None)
    plot_parser.add_argument("--stop-time", type=float, default=None)
    plot_parser.add_argument("--title", help="Plot title.")
    plot_parser.add_argument("--dpi", type=int, default=150)
    plot_parser.add_argument("--output", required=True, help="Output image path.")
    plot_parser.set_defaults(func=handle_plot)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
