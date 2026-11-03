# 用官方MACE权重进行力场预测

当前有两种不同用法。直接使用已有官方力场预测，应保留原MACE能量头，使用官方MACECalculator。
本框架的forcefield任务则保留官方主干、新建随机能量头，再由该能量对坐标和应变求导得到力和
应力。因此框架路径必须先训练新头；仅加载官方主干并不能直接恢复原官方力场的预测。

## 在模拟数据集上微调，再预测

配置 [mace_forcefield.yaml](../configs/mace_forcefield.yaml) 使用已验收的官方MACE-MP small.model，
完整主干和新任务头一起训练。原始权重位置是backbone.checkpoint；--resume指本框架保存的
checkpoint，用于继续训练或推理，两者不能混用。原层数、宽度、cutoff均来自官方模型。

先准备 `data/simulation/train.jsonl` 与 `data/simulation/test.jsonl`；也可修改配置/CLI中的路径。
标准JSONL每行一个完整结构，字段为schema_version:1、唯一id、numbers、positions、cell、pbc、
targets和可选metadata。positions是angstrom下的笛卡尔坐标；cell是按行排列的3×3晶格矩阵。
不需要自行提供邻居图，官方MACE构图器会按原规则构图。具体格式见 [standards.md](standards.md)。

训练标签由task.supervised_outputs选择；省略时保持原来的E/F/S三项默认值：

| targets中的名称 | 形状 | 约定 |
| --- | --- | --- |
| total_energy | 标量 | 整个结构总能量，eV |
| forces | N×3 | 每原子笛卡尔力，eV/angstrom |
| stress | 3×3 | 拉伸为正的应力，GPa |

只有力标签时，使用 [mace_force_only.yaml](../configs/mace_force_only.yaml)，或在原配置中加：

```yaml
task:
  kind: forcefield
  supervised_outputs: [forces]
```

这时只需真实forces标签；未选择的能量/应力绑定、尺度统计和损失均跳过，不需要伪造标签。
也可选择[total_energy, forces]等非空子集。loss_weights仅加权，不替代监督项选择。
能量头仍用于F=-dE/dR，力损失通过坐标/参数混合导数更新主干和新头；能量的常数偏移及元素参考能
无法由力标签确定。推理仍可计算E/F/S，但绝对能量未校准，应力也未直接监督。
完整续训要求监督项相同；旧配置/旧checkpoint未声明该字段时仍按E/F/S解释。
预测数据可以没有标签，targets可为空。非周期分子的包围盒应力不是体材料应力。

如果原数据字段名不同，通过dataset.bindings指定key。unit字段记录约定，不自动换算。
例如原始ASE应力为eV/angstrom³、六分量顺序xx,yy,zz,yz,xz,xy，可将stress绑定改成：

```yaml
stress:
  key: stress_ase
  factor: 160.21766208
  voigt: true
  unit: GPa
```

Guqq2仓库根目录中，先按AGENTS.md同步代码，再执行以下提交命令：

```bash
mkdir -p runs
sbatch scripts/ugnn.slurm --mode train --model mace --task forcefield \
  --dataset data/simulation/train.jsonl --config configs/mace_forcefield.yaml \
  --logging logs/mace-forcefield --save checkpoints/mace-forcefield.pt
```

脚本默认使用已配置的universal-official环境。训练使用全部所选数据、batch_size=4、float32；
上述轮数和学习率是起始配置，不表示已在你的模拟数据上确定最佳参数。更换权重时修改
backbone.checkpoint，使用兼容的原始可训练.model及对应依赖和元素表。

力标签单独训练时，将--config改为configs/mace_force_only.yaml，并指定实际force-only训练文件；
训练与推理的其他CLI参数相同，--resume仍使用训练后保存的本框架checkpoint。

训练完成后，使用保存的本框架checkpoint预测新结构：

```bash
sbatch scripts/ugnn.slurm --mode infer --model mace --task forcefield \
  --dataset data/simulation/test.jsonl --resume checkpoints/mace-forcefield.pt \
  --logging logs/mace-forcefield-infer --results results/mace-forcefield.jsonl
```

推理从checkpoint继承模型、任务、精度和batch大小；JSONL逐结构保存total_energy、forces、stress，
分别为eV、eV/angstrom、GPa，并保留结构ID。完整数据无需合并成一个计算batch。
继续训练时使用原训练数据和配置，加--resume，并将--epochs设置为累计目标轮数。

## 直接使用原官方力场，不重新训练

此路径保留预训练能量头，不创建本框架的随机新头。对于ASE可读的模拟轨迹，例如extxyz：

```python
from ase.io import iread
from mace.calculators import MACECalculator

calc = MACECalculator(
    model_paths="models/official/mace/small.model",
    device="cpu",
    default_dtype="float32",
)
for atoms in iread("data/simulation/test.extxyz", index=":"):
    atoms.calc = calc
    energy = atoms.get_potential_energy()  # eV
    forces = atoms.get_forces()            # eV/angstrom
    print(energy, forces)
```

周期结构还可调用atoms.get_stress(voigt=False)，ASE返回eV/angstrom³，乘160.21766208才是GPa。
将代码保存为自己的脚本后，在Guqq2仍必须通过Slurm执行：

```bash
sbatch --partition=compute --cpus-per-task=2 --mem=12G --time=00:30:00 \
  --output=runs/mace-native-%j.out --error=runs/mace-native-%j.err \
  --wrap='/home/xmz/.venvs/universal-official/bin/python predict_native.py'
```

官方API见 [MACE ASE文档](https://mace-docs.readthedocs.io/en/latest/guide/ase.html)；
本例model_paths参数另与本项目实际MACE0.3.16发行包核对。当前UGNN CLI没有直接保留原MACE头的
零样本推理开关。force-only路径已在既有十个真实结构及原力标签上完成训练/续训/重载验收，
两环境各80项回归通过，详见 [仅力监督验收](agents/force-only.md)。未在未提供的用户模拟数据上训练。
