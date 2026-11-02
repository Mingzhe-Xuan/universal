# 命令行使用约定

以下入口已实现，配置支持 YAML/JSON；原始约定示例保留如下。

```bash
ugnn --mode train --model mace --dataset data_path --resume resume_ckpt_path --task formation_energy --config configs/formation_energy.yaml --logging logging_path --save save_ckpt_path

ugnn --mode infer --model mace --dataset data_path --resume ckpt_path --task formation_energy --config configs/formation_energy.yaml --logging logging_path --results results_path
```

`--mode` 选择训练或推理；`--model`、`--dataset`、`--task` 分别指定主干、结构文件/数据插件、性质或任务。
配置优先级为 CLI > 配置文件 > resume checkpoint 中的配置 > 默认值。
从头训练省略 `--resume`；推理必须提供它。训练必须给 `--save`，推理必须给 `--results`。

- `--logging` 是目录：保存追加的 `run.log`、`events.jsonl`、最新 `config.resolved.json`，训练另有 `report.json`。
- `--save` 是 checkpoint 文件路径，`--results` 是推理 JSON 文件路径。推理输出保留输入 ID/来源。
- 新入口默认逐 epoch 原子更新 checkpoint（`checkpoint_every: 1`）；可设间隔，0 表示只保存最终状态。
- 新 checkpoint 的续训恢复模型、Adam、已完成轮数和 Torch 随机状态；`epochs` / `--epochs` 是总目标轮数。
  例如已完成15轮，设30则再训练15轮。所选结构/标签/绑定、训练seed和模型/任务必须兼容。
- 旧 checkpoint 没有优化器状态时，明确提示并记录 `weights_only` 暖启动，从第0轮开始新的优化；不伪装完整恢复。
- 推理的模型/任务/架构参数须与 checkpoint 一致，冲突时报错。可替换推理数据和设备，`--limit` 限制结构数。
- 使用 MACE 时激活其独立环境；核心/NequIP 与 MACE 的 e3nn 版本不同。旧子命令入口继续兼容。

## ALIGNN 训练带隙

```bash
ugnn --mode train \
  --model alignn \
  --dataset data/acceptance/bandgap-10.json \
  --task bandgap \
  --config configs/bandgap.yaml \
  --logging logs/alignn-bandgap \
  --save checkpoints/alignn-bandgap.pt
```

目标为 `optb88vdw_bandgap`（eV），绑定已写入 `configs/bandgap.yaml`。该示例使用已有十结构数据，
训练器仍是小数据全批训练；本接口调整未增加正式数据划分、mini-batch 或基准精度功能。

训练完成后推理：

```bash
ugnn --mode infer \
  --model alignn \
  --dataset data/acceptance/bandgap-10.json \
  --resume checkpoints/alignn-bandgap.pt \
  --task bandgap \
  --config configs/bandgap.yaml \
  --logging logs/alignn-bandgap-infer \
  --results results/alignn-bandgap.json
```

从30轮继续到60轮，在训练命令中加 `--resume checkpoints/alignn-bandgap.pt --epochs 60`。
模型保存位置可继续用同一文件；日志追加并使用不同 run_id。

## Guqq2 上执行

先按仓库规范同步源码，在仓库根目录创建Slurm日志目录，并通过同一个CLI参数提交：

```bash
mkdir -p runs
sbatch scripts/ugnn.slurm --mode train --model alignn \
  --dataset data/acceptance/bandgap-10.json --task bandgap \
  --config configs/bandgap.yaml --logging logs/alignn-bandgap \
  --save checkpoints/alignn-bandgap.pt
```

推理同样提交 `scripts/ugnn.slurm`，将后面的参数替换成上面的 `--mode infer` 命令。
该脚本默认核心环境；MACE 使用 `--export=ALL,UGNN_PYTHON=/home/xmz/.venvs/universal-mace/bin/python`。
所有实际训练、推理均在Slurm计算节点执行。

## 实际验证

源码 `3270e9e` 在Slurm731完成上述十结构ALIGNN带隙训练、续训和推理，恢复15→30轮与连续30轮
参数逐项完全一致；Slurm734另外验证 `scripts/ugnn.slurm` 透传推理结果一致。
两环境Slurm732/733各39项检查通过。本地证据位于
`results/cli-usage-731/evidence.json`，包括实际报告和日志；生成物不进入Git。

## 自定义 GNN 与分子图

统一接口及 ckpt/dataset/config 格式集中在 [standards.md](../standards.md)。
选择 `--model plugin:examples/custom_knn_gcn` 与 `configs/custom_knn_gcn.yaml` 即可使用最小示例。
图配方在顶层 `graph`；也可用 `--graph knn/radius/stored/plugin:...` 选择构图器。
使用自定义图的前提是标准包装 GNN；原生六主干的外部图覆盖会明确拒绝。
