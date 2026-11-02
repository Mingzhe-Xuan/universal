# UGNN 扩展接口与文件格式标准 v1

本文件是 GNN、分子/晶体图、config、dataset 和 checkpoint 的统一规范。
使用命令见 [usage](plan/usage.md)，最小可执行扩展见
[custom_knn_gcn](../examples/custom_knn_gcn/README.md)。规范与实现对应，未支持的能力不通过字段名暗示。

## 1. 版本与职责

| 对象 | 当前版本 | 版本字段 / 实现 |
| --- | --- | --- |
| 配置 | 1 | `schema_version: 1`；`engine/configuration.py` |
| 数据集 | 1 | JSON 包装对象 `schema_version: 1`；`data/formats.py` |
| 图 | 1 | `GraphRecord` / `GraphBatch`，JSON graph 可标 `schema_version: 1` |
| GNN 协议 | 1 | `BaseGNN`、`GNNOutput`、`StandardBackbone` |
| checkpoint 容器 | 2 | `format_version: 2`，独立于上述接口版本 |
| 续训状态 | 1 | 可选 `training_state.version: 1` |

未知显式版本报错。未带版本的旧 JSON/JARVIS/ASE 数据、旧配置、format 1/2 权重继续兼容读取，
不将旧记录改写成新格式。新 checkpoint 的 `contract_versions` 记录生产者支持的四种接口版本，
不表示训练源文件已被改写。

模型/图构建器不得将 targets 当输入特征；标签仅供训练损失使用。

职责：dataset 提供原子、几何、标签和可选原始图；graph builder 提供拓扑与可选特征；GNN 只提供
读出前的节点表示；统一 adapter/readout 根据性质规格生成预测。原子顺序和样本映射在整个链中保持。

## 2. 几何输入：Structure / StructureBatch

`universal_gnn.contracts.Structure` 表示一个结构，`StructureBatch.from_structures` 负责拼批。
运行时默认浮点使用 float64；设备和精度通过 `batch.to(device, dtype)` 一致迁移。

| 字段 | Shape / 类型 | 含义 |
| --- | --- | --- |
| `numbers` | int64 `[N]` | 正原子序数；内置元素嵌入覆盖 1–118 |
| `positions` | float `[N,3]` | 笛卡尔坐标，angstrom |
| `cell` | float `[3,3]`；拼批为 `[B,3,3]` | 非奇异，晶格矢量按行存储，`r = f @ cell` |
| `pbc` | bool `[3]`；拼批为 `[B,3]` | 各晶格轴周期性 |
| `identifier` / `identifiers` | string / tuple | 样本标识 |
| `targets` | 字典 / 按样本的 tuple | 原始或绑定后的标签，不放入可训练节点表示 |
| `metadata` | 字典 / tuple | 来源、单位等说明 |
| `graph` / `graphs` | 可选 GraphRecord / tuple | 导入图，可不提供 |
| `batch` | int64 `[N_total]` | 每个原子属于哪个样本，仅拼批对象有 |
| `ptr` | int64 `[B+1]` | 原子前缀和，从 0 到 N_total |

非周期分子用三个 false。标准 JSON 可省略其 cell：读取器生成每轴跨度加12 angstrom的包围盒，
不移动原坐标，并记录其为计算用非周期包围盒。周期结构必须显式提供 cell。
分子包围盒的应力不是物理体材料应力，不能据此伪造分子 stress 标签。

## 3. 图规范与导入

### GraphRecord：单结构局部图

```python
GraphRecord(edge_index, cell_shifts=None, node_features=None, edge_features=None)
```

| 字段 | Shape / 类型 | 规则 |
| --- | --- | --- |
| `edge_index` | int64 `[2,E]` | 第一行 src，第二行 dst；消息从 src 到 dst；局部索引在 `[0,N)` |
| `cell_shifts` | int64 `[E,3]` | src 的周期镜像偏移；省略视为零；非周期轴必须为零 |
| `node_features` | 可选 float `[N,F_n]` | 按原子顺序的标量输入属性 |
| `edge_features` | 可选 float `[E,F_e]` | 与边顺序逐行对应的标量属性，例如键类型编码 |

所有特征须有限。没有边特征是正常输入；不得依赖其必然存在。需要张量输入的自定义模型应基于
几何构造相应表示，或明确在自定义接口中处理类型，不能将任意向量分量当不变标量使用。

### GraphBatch：构图器和 GNN 之间的输入

`GraphBatch(geometry, edge_index, cell_shifts, node_features=None, edge_features=None, metadata={})`。
`geometry` 必须保留传入的同一个 StructureBatch；拼批索引为全局原子索引，无跨样本边。
整数索引/shift 和浮点特征与几何同设备，浮点特征与几何同 dtype。

派生属性：`src`、`dst`、`edge_batch`、`vectors`、`distances`。位移定义为：

```python
vectors = positions[src] + cell_shifts @ cell[edge_batch] - positions[dst]
```

`vectors` 每次从活的 positions/cell 计算，保留 autograd；图中不缓存脱离计算图的距离代替它。
图构建器允许离散选择拓扑，GNN 的几何特征须在该拓扑上连续计算。KNN换邻、等距截断等边界
不能承诺全局可微；测试力/二阶导应避开拓扑变化点。这与把坐标 detach 后计算消息不同。

### BaseGraphBuilder

```python
from universal_gnn.contracts import BaseGraphBuilder, GraphBatch

class MyGraph(BaseGraphBuilder):
    def forward(self, batch) -> GraphBatch:
        # 计算局部/全局拓扑，保留 batch 及原子顺序
        return GraphBatch(batch, edge_index, cell_shifts)
```

支持的 `graph.name`：

- `knn`：非周期、逐分子 KNN，默认 k=3，对称并去重；每个原子的候选数取 min(k,N-1)。
  孤立点无边。等距邻居按原子序号稳定截断，重排等距原子时不能据此承诺严格置换等变。
- `radius`：cutoff 内完整周期镜像图，支持晶体；明确设置 `cutoff`。
- `stored`：导入每个 Structure.graph，拼批时给局部索引加 ptr 偏移，保留特征对应关系。
- `plugin:/folder`：加载该目录 `plugin.py:build_graph_builder(**options)`，必须返回 BaseGraphBuilder。

内置 KNN/radius 可传递节点属性，重建边时拒绝沿用未重排的静态 edge_features；这类输入须选 stored
或由自定义构图器重新计算/映射边属性。不得静默错配。

## 4. 标准 GNN 与统一包装类

```python
from universal_gnn.contracts import BaseGNN, GNNOutput

class MyGNN(BaseGNN):
    def __init__(self, width=16, context_dim=0):
        super().__init__(irreps=f"{width}x0e", kind="invariant", context_dim=context_dim)
        # 注册原模型 / 可训练模块，如 self.encoder = ExistingGCN(...)

    def forward(self, graph, context=None) -> GNNOutput:
        # 原模型可在这里适配自己的参数签名：
        # nodes = self.encoder(x, graph.edge_index, ...)
        return GNNOutput(nodes)
```

`BaseGNN.forward` 输入 GraphBatch；可选 context 为 `[B,context_dim]` 的不变条件，必须在
声明 context_dim>0 时处理。生成等条件任务会传入它；不能静默忽略声明支持的条件。

`GNNOutput` 字段：

| 字段 | Shape / 类型 | 规则 |
| --- | --- | --- |
| `nodes` | float `[N_total,D]` | 必需，读出前节点特征；D 等于声明 irreps 的维数 |
| `graph_features` | 可选 float `[B,F]` | 图状态；共用读出不会自动拼接它到 nodes |
| `metadata` | dict | 非训练说明 |

`kind="invariant"` 只允许 `0e` 通道；等变模型声明准确的 O(3) irreps、奇偶性和通道排列。
所有节点必须一一对应原子，不在 backbone 中池化或删除节点。类型/形状检查不能证明任意用户网络
真的满足声明的旋转规律，用户须验证其数学性质。输出须与几何同设备/精度并有限。

`StandardBackbone(gnn, graph_builder, cutoff=4.0)` 是统一包装类：

1. 构图并检查索引、映射、特征；
2. 调用 GNN，检查 GNNOutput；
3. 包成现有 `NativeFeatures`，提供 `.encode(batch, context)`、`.irreps`、`.kind`、`.cutoff`；
4. 接入原有 scalar/equivariant adapter 和通用读出器。

`backbone.cutoff` 是包装层几何提升/方向读出的半径，不等于 KNN 的 k。
`graph.cutoff` 才是 radius 构图的截断；新式 build_gnn 工厂接收除包装层 cutoff 外的 backbone 选项。

目录插件示例：

```python
# plugin.py（支持 .model / .graph 相对导入）
from .model import MyGNN
from .graph import MyGraph

def build_gnn(**options):
    return MyGNN(**options)

def build_graph_builder(**options):
    return MyGraph(**options)
```

两个工厂可在同一目录，也可分别放置。现有 `build_backbone` 插件作为兼容接口保留；要独立选择图，
应实现 build_gnn。原有六种原生主干仍使用自身所需图结构，显式给它们配置外部 graph 会报错，
不会声称已接入实际上被忽略的图。

## 5. Config v1：YAML / JSON

配置必须是 mapping，新文件明确声明版本；JSON 与 YAML 字段等价。

```yaml
schema_version: 1
seed: 123
structures: 10
device: cpu
learning_rate: 0.001
epochs: 30
checkpoint_every: 1
backbone:
  name: plugin:examples/custom_knn_gcn
  width: 16
  layers: 2
  cutoff: 4.0
graph:
  name: plugin:examples/custom_knn_gcn
  k: 2
dataset:
  path: data/acceptance/molecules-g2-10.json
task:
  kind: supervised
  property: ionization_energy
  spec:
    scope: graph
    shape: [1]
    unit: eV
```

`backbone.name` 也可为 gcn，或现有六个内置模型。graph 仅用于标准包装模型。
`dataset.path` 可为标准文件或旧格式，也可为 `plugin:/folder`（工厂 build_dataset，参数在
`dataset.options`）；可选 bindings 显式声明原字段、单位与转换。
`task.kind` 为 supervised / forcefield / generation，性质规格负责输出shape/单位/构造，不由名字猜。

CLI > 配置文件 > resume配置 > 默认值。`--graph` 覆盖图名称，换名称时重置旧构图器专属选项；
额外参数写到对应 graph mapping。所有相对路径以当前工作目录为基准；示例在仓库根目录执行。

完整续训要求相同模型/图配方、选中结构、图/特征、标签/绑定与 seed；epochs 是累计目标轮数，
允许显式调整学习率。推理允许换数据和设备，模型/图/性质构造必须与checkpoint兼容。
当前训练器仍是小数据全批验证，structures 指前多少个样本，不提供正式数据划分/mini-batch。

## 6. Dataset v1：JSON / JSONL

规范 JSON 包装为 `{schema_version: 1, metadata: {...}, structures: [...]}`。
规范 JSONL 每行是下面的单记录，并带 `schema_version: 1`；旧无版本JSONL继续兼容。

预测用格式示例（没有人为构造监督标签）：

```json
{
  "schema_version": 1,
  "metadata": {"coordinate_unit": "angstrom"},
  "structures": [
    {
      "id": "example-n2",
      "numbers": [7, 7],
      "positions": [[0.0, 0.0, -0.565], [0.0, 0.0, 0.565]],
      "pbc": [false, false, false],
      "targets": {},
      "graph": {
        "schema_version": 1,
        "edge_index": [[0, 1], [1, 0]],
        "cell_shifts": [[0, 0, 0], [0, 0, 0]]
      },
      "metadata": {}
    }
  ]
}
```

每条记录 id 必须为非空字符串且在文件内唯一；numbers 为整数、positions 为有限 N×3，pbc 三个bool。
训练 targets 存 task 指定名称或 bindings 指向的数值，允许节点/谱/张量的嵌套数值数组；标准格式
要求有限值，未标注数据用于推理/生成。任务头检查实际目标shape，不假设所有任务标签相同。

可选 graph 的 node_features、edge_features 使用二维数值列表。零条边写 `edge_index: [[],[]]`；
cell_shifts 可省略或为空列表。空 edge_features 若要保留列数，附 `edge_features_width: F`，
序列化器自动处理。元信息/单位说明放 metadata；不得将缓存的边距离当作实时几何。

Python 导入/导出：`load_structures(path)`、`save_structures(path, structures, metadata=...)`。
数据插件返回 Structure 序列，可给每个对象附 GraphRecord，随后同样由 stored 构图器批处理。
KNN图是几何近邻图，不等于化学键识别，不保证价态/分子有效性。

## 7. Checkpoint v2

使用 `torch.save` 的字典，加载使用 `torch.load(..., weights_only=True)`；不保存模型对象或函数。

| 键 | 内容 |
| --- | --- |
| `format_version` | 2；旧无标记文件按 format 1 的几何基底约定加载 |
| `config` | 重建模型/图/任务的完整解析后配置 |
| `state_dict` | 张量权重，包含 GNN、adapter、readout；构图器若有可训练参数也在其中 |
| `versions` | 已知运行依赖版本 |
| `contract_versions` | `{config:1,dataset:1,graph:1,gnn:1}` |
| `extensions` | 自定义 GNN/graph 的工厂、源目录说明、全部 .py 相对文件和SHA256；没有插件时为空 |
| `scales` | 有监督任务归一化尺度；生成任务无此项 |
| `training_state` | 可选完整续训状态，见下 |

`training_state` 包含 version=1、completed_epochs、optimizer_state_dict、Torch CPU RNG、实际使用
CUDA设备的RNG、data_fingerprint、initial_loss、history与梯度记录。周期性checkpoint原子替换，
日志不进入权重。只恢复权重的旧文件明确记为 weights_only 暖启动。

数据指纹包括选中样本的ID、原子、几何、PBC、标签以及导入图/输入特征；不包含路径元信息。
插件指纹只哈希源码相对路径和字节，不包含绝对目录，可随同项目迁移；运行时从源码加载，避免
陈旧pyc与记录的源码指纹不一致。恢复时若插件源码变化，即使权重shape相同也会报错。

源码由 config 指定的 plugin 工厂重建，不从checkpoint执行pickle代码。分发自定义模型时必须
同时提供实现目录和兼容配置/依赖；仅有state_dict不足以恢复自定义架构。推荐保留仓库相对路径布局。

## 8. 最小验证与能力边界

```bash
# 在已配置环境、仓库根目录下；Guqq2须通过Slurm提交
ugnn --mode train --model plugin:examples/custom_knn_gcn \
  --config configs/custom_knn_gcn.yaml \
  --logging logs/custom-gcn --save checkpoints/custom-gcn.pt

ugnn --mode infer --resume checkpoints/custom-gcn.pt \
  --dataset data/acceptance/molecules-g2-10.json \
  --logging logs/custom-gcn-infer --results results/custom-gcn.json
```

`prepare_molecular_data.py` 从ASE G2-1原条目读取十个真实非周期分子及实验电离能，不计算新DFT。
`validate_extensions.slurm` 检查自定义KNN+GCN训练/续训/推理，另用导入的相同局部图独立训练，
对照连续训练、恢复训练和导入图的模型参数/预测一致性。数据记录源模块版本、文件SHA、ID、单位。

默认GCN使用距离权重，梯度经过节点特征、距离、坐标。没有边属性也可训练。
周期力场、应变和晶体生成须使用支持周期镜像的 radius / graph 插件；分子KNN不会被隐式当成周期图。
响应读出仍按既有求导规则，不能仅凭本接口就宣称任意用户算子支持高阶反向或严格等变。
小数据执行验证不代表泛化精度、化学合理性或完整论文复现。
