# Data File Format

## CSV output

- Default delimiter: comma
- Default encoding: UTF-8
- Header row: always present
- First column: `time`
- Remaining columns: variable names returned by the FMU

Example:

```text
time,u,speed,torque
0.0,0.0,0.0,1.0
0.1,0.2,0.4,1.2
```

`run_fmu.py` defaults to exporting FMU `output`, `local`, and `input` variables. If `--output-vars` is supplied, only the listed variables are recorded.

Array-valued variables are flattened to 1-based FMI cross-check style column names in the CSV. One-dimensional arrays use names like `Vabc[1]`; multi-dimensional arrays use comma-separated indices like `A[1,1]`.

```text
time,Vabc[1],Vabc[2],Vabc[3],Uabc[1],Uabc[2],Uabc[3]
```

## Input signal CSV

Use `--input-file` with a CSV that contains:

- A required `time` column
- One column per FMU input variable
- At least one data row

Example:

```text
time,Vabc[1],Vabc[2],Vabc[3],Tm
0.0,0.0,0.0,0.0,0.0
0.005,12.0,-6.0,-6.0,1.0
0.01,0.0,0.0,0.0,0.0
```

Parsing rules:

- Scalar and array inputs both use FMI cross-check CSV naming
- Array elements must use 1-based indices
- One-dimensional arrays use column names like `name[1]`, `name[2]`
- Multi-dimensional arrays use column names like `name[1,1]`, `name[1,2]`
- Empty cells are rejected
- Columns that are not FMU input variables are rejected

## Metadata JSON

`run_fmu.py` writes a sidecar JSON file next to the CSV with the same basename and `.json` suffix.

Fields:

- `fmu_path`: source FMU path
- `input_file`
- `input_columns`
- `fmi_type`
- `start_time`
- `stop_time`
- `step_size`
- `communication_step_size`
- `effective_step_size`
- `effective_communication_step_size`
- `output_variables`
- `start_values`
- `row_count`

## Filtering rules

`data_tools.py extract` and `data_tools.py plot` apply filtering in this order:

1. Read CSV header and rows.
2. Keep only the requested columns if `--columns` or `--y` is provided.
3. Drop rows outside `--start-time` and `--stop-time` if supplied.
4. Write filtered CSV or JSON, or render a plot from the remaining rows.
