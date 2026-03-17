# Run FMU Simulations Skill

中文：这是一个用于 Codex 的 FMU 仿真 skill，支持查看 FMU 接口、检查 FMI 模式与步长信息、运行 FMU 仿真、导出结果数据并对结果进行提取和绘图。

English: This is a Codex skill for FMU simulation workflows. It supports inspecting FMU interfaces, checking FMI modes and step information, running FMU simulations, exporting result data, and extracting or plotting recorded signals.

## Repository Layout

中文：
- `run-fmu-simulations/`
  需要安装到 `~/.codex/skills/` 下的 skill 目录
- `run-fmu-simulations/SKILL.md`
  skill 主说明文件
- `run-fmu-simulations/scripts/inspect_fmu.py`
  查看接口、模式和步长相关信息
- `run-fmu-simulations/scripts/run_fmu.py`
  运行仿真，处理标量和数组输入，并导出 CSV 结果
- `run-fmu-simulations/scripts/data_tools.py`
  从 CSV 中提取数据或绘图

English:
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

中文：将 `run-fmu-simulations/` 目录复制到你的 Codex skills 目录下：

English: Copy `run-fmu-simulations/` into your Codex skills directory:

```text
~/.codex/skills/run-fmu-simulations/
```

## Capabilities

中文：
- 支持 FMI 2.x 和 FMI 3.0 FMU 的接口检查
- 查看执行模式以及默认步长或固定内部步长
- 支持标量和数组输入信号的 FMU 仿真
- 将 outputs、locals 和 inputs 导出到 CSV
- 从 CSV 提取数据并绘制曲线
- 区分 `ModelExchange` 求解步长和 `CoSimulation` 通信步长

English:
- Inspect FMU interface variables for FMI 2.x and FMI 3.0 models
- Inspect supported execution mode and default or fixed step information
- Run FMU simulations with scalar or array input signals
- Export outputs, locals, and inputs to CSV
- Plot recorded variables from CSV files
- Distinguish `ModelExchange` solver step size from `CoSimulation` communication step size

## Notes

中文：
- `run_fmu.py` 对 `CoSimulation` 使用 `--communication-step-size`
- `run_fmu.py` 对 `ModelExchange` 使用 `--step-size`
- 如果没有显式传步长，脚本会输出最终实际采用的步长
- 对 `modelDescription.xml` 不完全规范的 FMU，可以使用 `--no-validate`
- `dist/` 目录可以保留打包产物，便于分发

English:
- `run_fmu.py` uses `--communication-step-size` for `CoSimulation` FMUs
- `run_fmu.py` uses `--step-size` for `ModelExchange` FMUs
- If no step is provided, the script reports the effective step it actually uses
- Some FMUs with imperfect `modelDescription.xml` files may require `--no-validate`
- The `dist/` directory can be kept for packaged artifacts and distribution
