# QM9 四标量性质实验

2026-11-25。按用户要求新增32项实验，独立于原48项与其重跑。

| 性质库名称 | 官方列 | 输出 | 单位 |
|---|---|---|---|
| `homo` | HOMO | 图级不变标量 | eV |
| `lumo` | LUMO | 图级不变标量 | eV |
| `dipole_magnitude` | mu | 图级不变标量 | Debye |
| `isotropic_polarizability` | alpha | 图级不变标量 | Bohr³ |

四性质 × CGCNN/ALIGNN/MACE/NequIP × 官方权重微调/同架构从头训练。
仅训练seed123；预测头为随机初始化的mean graph MLP，骨干和头均训练。
全量、float32、300epoch上限、patience30、learning rate3e-4，与原标量配方一致。
不把偶极矩模长当作矢量，不把各向同性极化率当作3×3张量，不使用辅助变量求导。

官方[Figshare发布](https://doi.org/10.6084/m9.figshare.c.978904.v5)有133885个分子；
按作者`uncharacterized.txt`排除3054个，使用全部130831个。HOMO/LUMO由Hartree
乘27.211386245988转为eV；mu与alpha保留原单位。原始坐标和全部氢原子保留，
PBC=false，无原子数截断。零偶极矩保留。只读取公开标签，无新DFT。

固定original-SMILES分组、split seed0、请求80/10/10比例，并记录实际条数。
所有模型、初始化和性质共享该划分。这是UGNN自己的冻结划分，不宣称是文献标准
划分；与他人数字比较必须先对齐划分及清洗协议。

模块与接口：

- [数据转换](../../src/universal_gnn/data/preparation/qm9/README.md)：官方源SHA/MD5、XYZ解析、清洗、JSONL和manifest。
- [实验执行](../../src/universal_gnn/benchmarks/qm9/README.md)：冻结32配置、8组合CPU数值控制、完整训练图CUDA扫描、四性质分别配对容量预检、全量训练、独立测试重评分和Slurm派发。
- [统一入口](../../scripts/run_qm9.py)：`prepare/smoke/preflight/train/assess/terminal`。

CGCNN/ALIGNN显式采用`molecular_radius`、6Å、全部半径邻居、非PBC；原权重参数名、
模块及高斯基底保持。MACE/NequIP保留原生分子构图/截断。缺少元素支持必须失败，
不得偷偷丢弃元素或换模型。scratch的原生邻居统计仅使用完整训练集。

预检采用2个warmup与至少100个测量batch，覆盖完整训练图扫描选出的极端结构和普通样本。
初始batch32；仅typed CUDA OOM逐步减半到可容纳值，同性质/骨干的两初始化重新验证共同batch。
其他错误包括CUDA launch timeout都按失败保留，不能通过缩小数据、截断原子或跳过结构绕过。

数据处理、数值控制、预检、训练、独立评测和checkpoint校验均经Slurm。
32项训练各有后续独立评测和afterany终态记录；共146个调度作业代表32项实验。
每项训练的Slurm14天上限是资源分配，不是预计耗时。无盲目重复提交或自动重试。

耗时按各模型/初始化的GPU实测`structures_per_second`，分别列50/150/300epoch场景：
训练+每轮完整validation+6次辅助训练遍历+一次完整test，再乘1.5预留构图、I/O等开销。
初始若GPU被既有作业占用，可借原任务GPU吞吐给出明确标注的粗估；新数据实际吞吐
由GPU预检完成后自动写入各模型`report.json`，排队等待另外说明。不可把CPU吞吐称为GPU实测。
