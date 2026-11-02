# 使用说明

框架通过 YAML/JSON 配置选择 backbone、数据和任务。六个标准名称 MACE、NequIP、Equiformer、
ALIGNN、CGCNN、MEGNet 默认选择官方实现与已登记的发布权重，读出前的原模型与预处理保持原样。
下载权重和依赖需预先准备；缺失时报错。旧架构变体必须显式指定 `backbone.implementation: legacy`。
具体包、源码、权重配置及已验收范围见 [官方接入](../src/universal_gnn/backbones/official/README.md)
与 [环境记录](agents/env.md)。NequIP隔离e3nn版本，Equiformer另隔离旧版PyG。

## 文档约定的命令行

主入口为 `ugnn --mode train/infer --model ... --dataset ... --task ... --config ...`。
完整参数、YAML配置、续训和ALIGNN带隙示例见 [CLI使用约定](plan/usage.md)。
`--logging` 指日志目录，`--save` 指训练checkpoint文件，`--results` 指推理JSON文件。
旧子命令入口继续保留，下面的示例也可使用。

## 训练与重载推理

`configs/` 提供形成能、E/F/S、Born 张量、Raman 和固定组成生成示例。
修改 `backbone.name`、`dataset.path` 与必要的 `dataset.bindings`，然后执行：

```bash
ugnn train configs/formation_energy.json --output runs/my_energy
ugnn infer runs/my_energy/checkpoint.pt data/acceptance/formation_energy-10.json --output results/energy.json
```

Guqq2 上上述训练、推理均须放入 Slurm，例如：

```bash
sbatch scripts/ugnn.slurm train configs/formation_energy.json --output runs/my_energy
```

真实十结构数据在服务器 `/home/xmz/universal/data/acceptance`，完整矩阵清单为 `manifest.json`。
标签源 URL、文件哈希、原记录索引、单位和转换随数据保存；数据、权重和运行报告均不进入 Git。
任务读出可通过修改配置切换 backbone；数据的元素、周期性和模型可微能力必须满足原官方模型的约束。
模型不会自动拥有其他单独训练任务的能力。历史96项矩阵使用旧架构变体，不能作为官方权重验收证据。
默认按任务分别训练；联合多任务训练不是本轮实现范围。

## 自定义模型、数据与性质

- 模型：`backbone.name="plugin:/path/to/model"`，该目录的 `plugin.py` 实现
  `build_backbone(**options)`。返回对象提供 `encode(batch, context=None)`、`irreps`、`kind` 和 `cutoff`；
  `encode` 返回读出前的 `NativeFeatures`，保留节点映射和可微几何，边特征可省略。
- 数据：`dataset.path="plugin:/path/to/dataset"`，该目录的 `plugin.py` 实现
  `build_dataset(**options)`，返回非空 `Structure` 序列；参数来自 `dataset.options`。
  也可直接使用规范 JSON/JSONL、JARVIS atoms 字典或 ASE 支持的结构文件。
- 性质：内置性质通过 `task.property` 选择；新性质在 `task.spec` 声明 `scope`、`shape`、
  `unit`、`kind`、`reduction` 和 `construction`。响应指定导数两侧的笛卡尔指标，默认求导读出；
  不施加晶体对称掩码。不同名称不会改变相同输出规格的训练损失逻辑。

详细接口见 [data](../src/universal_gnn/data/README.md)、
[backbones](../src/universal_gnn/backbones/README.md)、
[properties](../src/universal_gnn/properties/README.md) 和
[adapters](../src/universal_gnn/adapters/README.md)。

## 模拟与验收

`UniversalCalculator` 将力场接入 ASE；工作流组合相同 backbone 分别训练的力场、Born 和介电模型。
`python scripts/run_workflows.py --model cgcnn` 使用 `runs/dfpt-tasks` 下的三个 checkpoint；
Guqq2 用 `sbatch --array=0-5%3 scripts/workflows.slurm` 运行全部模型。
API 与设置见 [workflows](../src/universal_gnn/workflows/README.md)。

本轮按十结构验证执行通路。Γ 点模式不是完整布里渊区声子；虚频保持负号并从正频谱剔除。
短 FIRE/MD 不承诺收敛或长期稳定，STEM 使用有限簇与短 MD 快照，KK 使用有限频窗。
生成固定原子数和组成，检查采样执行与几何数值有效性，不据此评价生成质量。
完整论文精度及 CHIPS-FF/WBM/AtomBench 全套基准尚未运行。

## 扩展及文件标准

自定义 GNN、独立构图器、导入分子图和三类文件格式统一见 [standards.md](standards.md)。
可执行例子为 examples/custom_knn_gcn，配置为 configs/custom_knn_gcn.yaml；
包含基类、统一包装、输入输出约束和真实分子测试流程。
