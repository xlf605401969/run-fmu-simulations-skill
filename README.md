# Run FMU Simulations Skill

用于 Codex 的 FMU 仿真 skill。它主要解决几件事：查看 FMU 接口、检查 FMI 模式和步长信息、运行仿真、导出结果，以及从结果文件中提取数据和绘图。

This repository contains a Codex skill for FMU simulation work. It helps with interface inspection, FMI mode and step-size checks, running simulations, exporting results, and plotting recorded signals.

## What Is Included

主要内容都在 [`run-fmu-simulations/`](./run-fmu-simulations) 目录下，这个目录就是最终要安装到 Codex skills 目录中的 skill 本体。

The actual skill lives in [`run-fmu-simulations/`](./run-fmu-simulations), which is the folder you would place into your Codex skills directory.

比较关键的文件有：

- [`run-fmu-simulations/SKILL.md`](./run-fmu-simulations/SKILL.md): skill 的主说明
- [`run-fmu-simulations/scripts/inspect_fmu.py`](./run-fmu-simulations/scripts/inspect_fmu.py): 查看接口、模式、默认步长和固定内部步长
- [`run-fmu-simulations/scripts/run_fmu.py`](./run-fmu-simulations/scripts/run_fmu.py): 运行仿真，支持标量和数组输入，并导出 CSV
- [`run-fmu-simulations/scripts/data_tools.py`](./run-fmu-simulations/scripts/data_tools.py): 提取结果数据和绘图

Key files:

- [`run-fmu-simulations/SKILL.md`](./run-fmu-simulations/SKILL.md): main skill instructions
- [`run-fmu-simulations/scripts/inspect_fmu.py`](./run-fmu-simulations/scripts/inspect_fmu.py): inspect interface, modes, and step-related metadata
- [`run-fmu-simulations/scripts/run_fmu.py`](./run-fmu-simulations/scripts/run_fmu.py): run simulations with scalar or array inputs and export CSV results
- [`run-fmu-simulations/scripts/data_tools.py`](./run-fmu-simulations/scripts/data_tools.py): extract data and generate plots

## Installation

把 [`run-fmu-simulations/`](./run-fmu-simulations) 复制到你的 Codex skills 目录下即可：

Copy [`run-fmu-simulations/`](./run-fmu-simulations) into your Codex skills directory:

```text
~/.codex/skills/run-fmu-simulations/
```

## Capabilities

这个 skill 目前支持：

- 查看 FMI 2.x 和 FMI 3.0 FMU 的接口变量
- 查看执行模式、默认实验步长和固定内部步长
- 运行 FMU 仿真
- 使用标量输入和数组输入信号
- 将 outputs、locals 和 inputs 导出到 CSV
- 从 CSV 提取指定变量并绘图
- 区分 `ModelExchange` 的 solver step size 和 `CoSimulation` 的 communication step size

Current capabilities:

- inspect FMU interface variables for FMI 2.x and FMI 3.0 models
- inspect execution mode, default experiment step size, and fixed internal step size
- run FMU simulations
- support both scalar and array input signals
- export outputs, locals, and inputs to CSV
- extract variables from CSV and generate plots
- distinguish `ModelExchange` solver step size from `CoSimulation` communication step size

## Usage Notes

有几条使用上的约定需要注意：

- 对 `CoSimulation` FMU，使用 `--communication-step-size`
- 对 `ModelExchange` FMU，使用 `--step-size`
- 如果没有显式传步长，脚本会输出并记录最终实际使用的步长
- 对 `modelDescription.xml` 不完全规范的 FMU，可以使用 `--no-validate`
- 数组输入和输出使用 1-based 的 FMI cross-check 风格列名；一维数组例如 `Vabc[1]`、`Vabc[2]`、`Vabc[3]`，多维数组例如 `A[1,1]`、`A[1,2]`

A few practical notes:

- use `--communication-step-size` for `CoSimulation` FMUs
- use `--step-size` for `ModelExchange` FMUs
- if no step is passed, the script reports and records the effective step it actually uses
- use `--no-validate` for FMUs with imperfect `modelDescription.xml`
- array inputs and outputs use 1-based FMI cross-check style column names; one-dimensional arrays look like `Vabc[1]`, `Vabc[2]`, and `Vabc[3]`, while multi-dimensional arrays look like `A[1,1]` and `A[1,2]`
