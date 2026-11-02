# 兼容不变与等变 GNN 的 ALIGNN 2.0 下游任务工具箱

更新日期：2026-11-02。状态：设计评审稿，尚未实现。

## 0. 当前设计结论与实施边界

整体架构已足以进入原型：数据/条件 → 六类 backbone 的节点抽取 → 特征适配 → 按输出格式创建读出 → 直接预测或导数操作 → 训练/评测/生成/模拟。性质库负责把用户选择展开成规格与依赖，核心不按性质名或模型名写特殊分支。

已确认：六类模型范围、逐节点接口/边可选、输出格式驱动、响应默认求导、无晶体空间群约束、按任务分别训练、公开数据优先且不新增 DFT。统一读出首先指统一 API；同一组已训练权重跨模型共用不属于默认目标。

两种路线显式区分，不把两者叠加为所有模型的强制要求：

| 路线 | 特征与读出 | 适用边界 |
| --- | --- | --- |
| invariant_alignn | 不变节点通道适配，公共 API 后接分量 MLP/响应或能量求导 | 不要求高阶几何提升；固定坐标张量分量不保证一般旋转变换 |
| common_equivariant | 选择共同等变 profile，经原生投影/必要几何提升后接同一等变读出 | 对要求相同等变输入的实验使用；hybrid 和 568 维 profile 是本路线示例，不是框架全局默认 |

路线由模型/任务 preset 明确选择并记录，不自动从一条回退到另一条；当前尚未冻结覆盖全部任务的默认 preset。两条路线均保持响应默认 derivative，求导方式与变换保证分别声明。

实施前/首轮原型需落实的具体规格：

1. 冻结 StructureBatch、FeatureSpec/CanonicalFeatures、OutputSpec/ResponseSpec、DatasetBinding 的字段、shape、单位与校验错误；当前代码/JSON 仍为草图。
2. 锁定六类 backend 的具体实现版本、取层、元素/邻居/PBC 与所需梯度能力，并确定实际源码落地位置和依赖环境。
3. 给出首批性质条目及数据绑定/划分/指标清单；逐项标记定义、数据可获取、实现与评测状态，不将计划覆盖当作已支持。
4. 固定第一套生成配方的状态、时间条件、噪声目标、晶格/周期参数化、采样与评分预算；当前只有工作流边界，尚非完整采样算法配置。

这些属于实现规格与验证工作，不需要再引入新的统一抽象。先用一个等变模型和一个不变模型完成标量、能量求导与响应求导的最小闭环，再扩展到六类模型和全部目标工作流；本轮仍不开始实施。

## 1. 当前需求与已接受的前提

目标是覆盖 ALIGNN 2.0 的性质、逐原子、力场、张量、谱、晶体生成和派生模拟任务，让用户选择模型/数据集或编写适配器即可运行。ALIGNN 2.0 提供任务范围、公开数据及评测参考，不要求与其内部实现、任务头、训练步或数值结果逐一对齐。

当前模型范围由用户明确限定：

- 同时支持等变与不变 GNN；首批适配 MACE、NequIP、Equiformer、ALIGNN、CGCNN、MEGNet。PaiNN、SevenNet、UMA 等保留为后续扩展。
- 需要求导的任务要求接入后的计算链对相应几何/辅助变量可微；不能仅凭模型名称假定现成实现已满足这一要求。
- 模型提供逐节点特征，不保证返回边特征。
- 用户已有等变模型适配方式；工具箱提供接口，不额外规定必须使用 ALIGNN 的几何/消息传递。
- 按输出格式组织核心接口，不按介电、弹性等性质名实现独立任务头；已支持的响应性质默认采用 GMTNet 风格求导读出，直接 irreps→Cartesian 保留为显式覆盖选项，不加入晶体空间群约束。

本稿替代上一稿“固定原任务壳、头、导数路径及逐训练步行为回归”的硬要求。复用已有 ALIGNN 代码仍是优先工程选择，但兼容旧包、旧命令、旧 checkpoint 键不再是任务完成的前置条件。

本轮只修订计划和分析困难，不实现代码、不下载数据、不安装环境、不运行模型或连接服务器。[AFM 研究计划](afm_transferability.md)保持独立。

## 2. 保持哪些可比条件，允许改变什么

| 层次 | 当前要求 |
| --- | --- |
| 任务定义 | 明确输入、目标、单位、条件、输出层级及指标，覆盖论文对应任务 |
| 数据 | 优先复用已公开数据和固定划分；允许自行整理/划分，但记录版本及差异，测试集不参与选模 |
| 评测 | 同一对照实验使用相同测试数据、目标定义、评分与预算；协议变化单列 |
| 模型适配 | 允许不同图后端、表示、读出、能量求导和去噪头，按模型能力实现 |
| 训练/生成 | 允许调整实现和超参数；记录训练预算、噪声/采样设置、条件和后处理，不能把不同预算当相同实验 |
| 原 ALIGNN 兼容 | 可保留为一个参考 backend；只对声称兼容的入口做兼容检查，不要求全部新实现数值等价 |

不再强制把新 GNN 的输出转换成 ALIGNN 的边/三体特征，不再要求复制其逐边 virial 实现或原坐标 score 头。不能为了保持一个旧接口而增加不必要的模型限制。

## 3. 最小公共接口：节点特征及其语义

框架的共同部分是结构/标签、模型适配器、任务头和实验执行。节点是主接口，边是可选信息。

```python
class BackboneAdapter:
    def describe(self) -> FeatureSpec: ...
    def encode(self, structure_batch, context=None) -> NodeFeatures: ...
```

`FeatureSpec` 必须说明：节点特征的不可约表示/通道变换规则、基底和归一化、节点顺序、周期性/支持元素，以及几何输入的梯度连接。ALIGNN、CGCNN、MEGNet 等不变模型的 C 个标量通道可描述为 Cx0e，无须实现高阶 irreps；非标量特征则不能仅凭 [N,D] 维度解释。

`NodeFeatures` 保留 sample/atom 对应、batch 索引、必需的节点通道及其规格；非标量等变通道和边特征均允许缺省。结构批次另提供几何上下文，任务头可以使用它或模型额外信息，但不把边特征提升为所有模型的必填项。

可选 graph_features 承载 MEGNet 等模型更新后的全局状态；输入条件通过 context 映射到其 state 输入。全局特征不替代逐节点输出，也不成为其他 backbone 的必填字段。

读出前新增 UnifiedFeatureAdapter：将上述原生节点特征与几何统一成固定 profile 的 CanonicalFeatures；模型私有表示和 native/geometry 差异由该层处理，统一读出器不再直接消费六种原生特征。详细方案见[统一特征适配层](unified_feature_adapter.md)。

不要求用户使用特定 irreps 库。由用户适配器完成内部表示到任务头约定表示的转换；不能将不同阶/奇偶性的通道当作普通向量任意线性混合。

固定输入的 frozen 特征可以缓存；力场求导、全参微调和生成过程中需要在线调用 backbone。冻结参数不应截断输入梯度。

### 3.1 按输出格式而非性质名组织

输出格式由若干正交维度组成，而不是一张 shape 列表。核心无需识别性质名称，但必须知道对象位置、各轴意义、变换规则和输出的构造关系。下表中的 B 是结构数，N 是批次原子总数，C 是独立通道数，K 是采样点数；节点批次另存 batch/ptr 与原子映射。

| 格式 | 典型布局 | 统一实现与必要声明 |
| --- | --- | --- |
| 连续标量/多标量 | 结构 [B,C]，节点 [N,C] | 不变读出；声明 sum/mean/其他聚合、单位及标准化。标量是零阶张量 |
| 连续向量 | [B,C,3] 或 [N,C,3] | 一阶等变读出；区分极向量/轴向量与坐标点 |
| 连续高阶张量 | [B,C,3,...,3] 或 [N,C,3,...,3] | 按 rank/parity/指标定义生成目标 irreps，再转换 Cartesian；不默认指标对称或空间群约束 |
| 带采样域的数组/场 | 标量谱 [B,K,C]，张量谱 [B,K,C,3,3] | 在上述表示上增加网格轴；声明频率/能量等网格、单位、mask 与需要的积分权重。K 轴不参与空间旋转 |
| 离散类别/概率 | [B,C_classes] 或 [N,C_classes] | 分类 logits，声明类别表、有效类别 mask、归一化与损失；多标签和互斥分类分别配置 |
| 结构化几何 | {positions:[N,3], cell:[B,3,3], species:[N], ptr, pbc} | 多个输出及输入上下文的组合；声明点坐标/晶格基向量、坐标系与周期规则，不能当一个普通张量回归头 |

前三项可共用连续 Cartesian 张量读出工厂，标量/向量只是 rank=0/1。采样域是附加轴，结构是组合容器，不需要各自重新设计一套 backbone。复数值可按 dtype 或显式实/虚部通道编码；时间、样本、轨迹是附加轴，不另建性质类别。

scope 独立于数值表示：graph、node，后续有需要再加入 pair/edge。逐原子和结构级输出可复用同一表示转换，但其聚合不同。当前主任务不要求所有模型提供边特征；未来 pair 输出可由端点节点与几何构造专用读出，不倒推骨干必须返回边特征。

位置是随平移改变的点；普通向量不随整体平移改变。采用 ASE 的 cell 布局时，晶格矩阵的三行是晶格基向量，一侧指标代表基向量编号，不能按介电等二阶张量的双空间指标规则旋转。[E3] 相同 shape 不代表相同表示。

### 3.2 输出格式与构造操作分开

拟议 OutputSpec 最小包含：key、scope、value_kind、representation、axes、reduction，以及单位/坐标/标准化约定。数学变换规则可用 irreps 或明确的 Cartesian 指标与 parity 描述，不强制用户依赖某个库。

另用计算依赖图声明 construction：

- direct：从 CanonicalFeatures 学习目标系数，必要时聚合与换基；native/geometry/hybrid 来源由前置 feature_adapter 显式配置。
- derivative：声明 source、wrt、导数阶数、符号/比例、参考点及批次求导规则；可表达负坐标梯度、应变导数及辅助变量 Jacobian。
- algebra/convert：显式组合、单位与坐标变换；不从性质名字猜测规则。

连续头按输出表示创建；求导按操作创建。力和其他极向量可以共享目标格式，但如果要求能量一致的力场，必须声明力来自能量的负梯度，不能仅因 shape 相同就改成独立向量回归。张量直接读出和响应求导也共用输出规格，后者额外声明其响应函数与辅助变量。

loss/metric 从配置选择并绑定输出，不能仅靠 shape 自动决定；同一谱数组可选择逐点误差或带网格权重的误差，同 shape 的 logits 可采用互斥或多标签损失。模型调用也保留 context，以传入温度、电场、噪声时间步等输入条件。

### 3.3 性质语义的保留边界

核心可以完全忽略性质名称，但不能完全忽略数学/物理定义。性质名称仅用于数据绑定、显示和实验记录；必要规则显式声明，数据集/任务 preset 可自动填写，用户新增性质无需增加 if property_name 分支。

| 相同格式的例子 | 仍需显式声明的差异 |
| --- | --- |
| 总能量与带隙：结构标量 | 广延/强度目标及聚合，原子参考能、单位与归一化 |
| 力、位移与位置：[N,3] | 能量求导关系、极向量与点的变换、坐标系；不能由 shape 推断 |
| 介电与应力：[B,3,3] | 单位、符号、指标/Voigt 约定，以及是否由其他输出求导 |
| 应力与晶格：[B,3,3] | 双空间指标张量与晶格基向量组的不同变换规则 |
| 谱与无序多目标：[B,K] | K 是有序采样网格还是独立通道，mask、归一化与评分权重 |

生成模型每一步可以只输出节点向量、晶格变量与可选类别 logits，但完整生成还需要噪声过程、时间条件、采样器及周期状态更新。弛豫/MD/声子等同样是输出与导数的调用流程；它们不能仅由输出数组格式定义。固定组成 CSP 的原子数与元素来自输入，不要求新增元素/原子数生成。

因此采用三层：OutputSpec/读出描述“输出是什么”，计算操作描述“如何构造”，workflow 描述“如何训练、采样或模拟”。首期只实现覆盖 ALIGNN 任务所需的格式与操作，不扩展成任意科学计算引擎。

### 3.4 性质库：为通用核心提供声明式默认配置

维护可扩展的性质目录（PropertyCatalog），用户可以按熟悉的性质名称选择，目录解析器再将其展开为 OutputSpec、构造依赖及可覆盖的 loss/metric 默认值。读出和训练核心只消费展开后的规格，不按性质名称分支。用户仍可绕过目录直接声明输出。

| 层次 | 内容与职责 |
| --- | --- |
| PropertySpec | 稳定 id/版本、明确的性质定义、输出 scope/表示/轴、规范单位、符号/指标/坐标约定、必要输入条件及支持的构造方式 |
| DatasetBinding | 数据源/标签列、原子对应、源单位与转换、实际谱网格、缺失值 mask、数据版本/划分；标准化统计仅用训练集拟合 |
| TaskPreset / WorkflowPreset | 选择性质及明确的构造方式、组合依赖、损失/评分设置和可覆盖默认值；生成/MD/弛豫另由 workflow 描述流程 |

同名但不同定义应有不同 id/变体，例如总能量/每原子能量、静态/频率依赖响应、固定电场/其他边界条件。数据集别名不能直接作为物理定义；只允许语义匹配后的绑定，不因名称相似自动合并。

典型条目可包括 energy.total（结构标量、节点能量求和）、force.conservative（节点极向量、对选定总能量的负坐标梯度）、force.direct（节点极向量、直接预测）、response.dielectric.static（结构二阶张量、明确响应定义和单位）。direct/derivative 的选择必须显式记录；不在某种能力缺失时静默切换，保守力配置会自动补齐其依赖的总能量输出。

已支持响应条目的 default_construction=derivative：目录保存 response_spec，声明响应函数/source、辅助变量/wrt、阶数、参考点、比例与单位/指标约定。用户只选性质时自动展开该求导配置；只有显式覆盖 construction=direct 才采用直接读出，覆盖项和最终配置均写入实验记录。不能凭张量 shape 或性质名称前缀自动判断响应类型，也不将所有标量/谱/生成输出改为求导。

响应函数、变量或梯度能力缺失时，运行前报出具体缺项，不自动回退直接预测。线性响应函数可以没有独立响应量标签，直接用目标 Jacobian 的监督损失训练；这不要求另取扰动态数据或额外 DFT，也不强制与力场共用一个能量函数。

相同格式的性质共用头工厂，性质目录不存独立模型实现，也不自动共享不同输出的参数。张量条目按当前范围不强制晶体空间群或额外指标对称约束。谱网格可由绑定提供，但应满足 PropertySpec 的轴与归一化定义。

拟议便捷入口可以只指定模型、数据绑定和性质列表，例如选择 energy.total 与 force.conservative，再由 preset 展开依赖；生成则选择固定组成 CSP workflow，并解析其内部所需输出。以下均属于计划接口，并未实现。

- 已有格式/算子能够描述的新性质：增加 YAML/JSON 条目与数据绑定即可，通常无需 Python 代码。
- 需要新响应函数、数学变换或损失：注册相应通用算子/读出插件，再由性质条目引用；不能承诺所有新性质都只改配置。
- 自定义性质目录：允许从用户指定目录加载，使用 user: 等命名空间避免覆盖内置条目，并校验 id/版本及依赖循环。

目录项登记、模型/算子能力兼容、数据已获取、端到端评测通过分别记录。性质库存在某条目不表示已有数据、权重或可信精度。实验保存展开后的完整规格、目录版本和用户覆盖项，避免默认值变化使实验无法追溯。

### 3.5 不变/等变 backbone 范围与适配顺序

以下为 2026-11-02 对原始论文、官方文档及源码的静态核查，不是已实现或实测兼容清单。区分模型架构、实际暴露的特征层和预训练 checkpoint；一种架构可适配，不等于任意版本/权重已经满足所有任务。

用户指定的首批范围为 MACE、NequIP、Equiformer、ALIGNN、CGCNN、MEGNet。前三类验证等变节点表示，后三类验证不变节点表示。Equiformer 默认先落原版架构适配，具体 PBC/元素与导数实现需锁版本；EquiformerV2 用独立 adapter id 与配置扩展，不将前述 V2 原始源码限制泛化到整个家族。

| 候选 | 可接入的节点表示 | 当前适配判断 |
| --- | --- | --- |
| MACE | 按交互层保留的 irreps 节点特征，底层 forward 返回 node_feats | 优先。适合统一表示接口及材料预训练权重接入；声明各层真实 irreps，不能只看最终能量层。[MACE 源码](https://github.com/ACEsuit/mace/blob/main/mace/modules/models.py) |
| NequIP | 卷积中间层的 O(3) irreps，可配置阶数/parity | 优先。当前官方构造器要求末层仅含标量，张量/向量任务需暴露更早的等变节点层。[官方构造器](https://github.com/mir-group/nequip/blob/main/nequip/model/nequip_models.py) |
| Equiformer | 注意力块的逐节点 irreps 表示 | 首批。原版实现也可能在末块投影为标量，应抽取此前的节点表示；不同实现的 PBC/元素映射需适配。[作者仓库](https://github.com/atomicarchitects/equiformer)、[表示实现](https://github.com/atomicarchitects/equiformer/blob/master/nets/dp_attention_transformer.py) |
| ALIGNN | pooling 前的逐节点不变特征 x，可选边/角不变特征 | 首批。标量直接读出，方向性输出结合几何基底或求导；对坐标/应变求导时重建带梯度的距离和角度，不使用已断开计算图的预计算几何特征。[固定源码快照](https://github.com/atomgptlab/alignn/blob/23f0146c4a61260fab5c5c9eb72a516491b76a70/alignn/models/alignn.py) |
| CGCNN | 最后卷积后、crystal pooling 前的逐节点 atom_fea，不变标量 | 首批。适配元素初始特征、邻居索引/截断/填充与批次映射；求导任务在线重算距离及 Gaussian 展开。[作者模型](https://github.com/txie-93/cgcnn/blob/master/cgcnn/model.py)、[原始数据管线](https://github.com/txie-93/cgcnn/blob/master/cgcnn/data.py) |
| MEGNet | 图网络块后的 node_feat，不变标量；edge_feat/state_feat 可选保留 | 首批。优先接 PyTorch 实现并记录具体版本，保留输入 state 和更新后的全局表示；不把原 TensorFlow/Keras 权重视为可自动加载的 Torch 权重。[MatGL 实现](https://github.com/materialsvirtuallab/matgl/blob/main/src/matgl/models/_megnet.py)、[原始实现](https://github.com/materialyzeai/megnet/blob/master/megnet/models/megnet.py) |
| PaiNN | 节点 scalar_representation 与 vector_representation，l=0/1 | 后续可选的较简单基线。高阶目标由额外张量积读出构造并核查表达范围，不能直接线性产生缺失阶数。[SchNetPack 实现](https://github.com/atomistic-machine-learning/schnetpack/blob/master/src/schnetpack/representation/painn.py) |
| SevenNet | NequIP 系的逐节点等变中间表示 | 可作为预训练势与微调适配目标；它基于 NequIP，不当作完全独立架构家族，具体 checkpoint 的层规格仍需检查。[官方仓库](https://github.com/MDIL-SNU/SevenNet) |
| UMA | eSEN 衍生的球谐节点表示，backbone 输出 node_embedding | 后续重要候选。使用底层 backbone 的带梯度输出，不能使用能量头导出的 detached embeddings；保留数据域、charge/spin 等 context，权重按官方获取流程处理。[源码](https://github.com/facebookresearch/fairchem/blob/main/src/fairchem/core/models/uma/escn_md.py)、[官方说明](https://facebookresearch.github.io/fairchem/uma/) |
| EquiformerV2 | SO3_Embedding 球谐节点系数，可配置高阶通道 | 架构适合，但原始实现的边旋转矩阵 detach，且力为独立预测；满足全过程几何可微需更换/修正相关实现并完整验导，不能原样作为保守力场后端。[节点与力输出](https://github.com/atomicarchitects/equiformer_v2/blob/main/nets/equiformer_v2/equiformer_v2_oc20.py)、[旋转代码](https://github.com/atomicarchitects/equiformer_v2/blob/main/nets/equiformer_v2/edge_rot_mat.py) |
| TensorNet | 内部节点 Cartesian 矩阵，分解含标量/向量/二阶通道 | 可扩展。标准 forward 最终做不变量化，需取内部 X 并按真实表示规则转换；原邻居实现对周期盒/cutoff 有限制，不能直接假定覆盖所有小晶胞。[官方源码](https://github.com/torchmd/torchmd-net/blob/main/torchmdnet/models/tensornet.py) |
| EGNN | 节点不变特征与等变坐标更新 | 可作生成/坐标更新基线；坐标点不是通用向量隐藏特征，需要暴露位移或几何读出，高阶张量与晶体 PBC 需额外适配。[作者仓库](https://github.com/vgsatorras/egnn) |
| Allegro | 核心为局部边上的等变/不变表示 | 可以改造成节点接口，但优先级较低：须在不变量化前暴露等变边状态，再按中心原子聚合为节点表示；最终边标量不能恢复被丢弃的方向信息。[官方构造器](https://github.com/mir-group/allegro/blob/main/allegro/model/allegro_models.py) |

eSCN/eSEN 也是球谐表示候选，可沿同类适配路线扩展。FAIR-Chem 官方目前明确区分旧 EquiformerV2/eSEN 与新 UMA 接口，不能用一个未锁版本的适配器声称全部兼容。[接口迁移说明](https://facebookresearch.github.io/fairchem/fairchemv1-v2/)

首批范围依据用户最新选择：MACE、NequIP、Equiformer 验证等变接口，ALIGNN、CGCNN、MEGNet 验证不变接口；之后再接其他模型与预训练权重。适配顺序不代表模型精度排名，框架不依赖只有等变节点特征才可运行。

CGCNN 原数据管线使用 NumPy 预展开距离，不能直接作为完整坐标求导输入；adapter 保留 PBC 镜像和邻居拓扑，在 Torch 中由当前坐标/晶胞重算距离与基函数。填充邻居的处理、cutoff/平滑改动及与旧权重的兼容范围均显式记录，按任务验证，不声称保留原逐步数值行为。

MEGNet 架构支持与原包兼容分开：首期使用可接公共 Torch 训练/求导链的实现，暴露图块节点特征并保留可选状态；原 TensorFlow/Keras 包只作为架构/权重参考。不能用 NumPy 桥接声称跨框架梯度连通；若未来迁移旧权重，另做映射及前向一致性验收。本轮只读取官方源码，尚未锁定安装版本或转换权重。

共同门槛与接口补充：

- FeatureSpec 记录选取层/多层组合、实际 l/parity/基底、SO(3)/O(3) 变换保证及几何梯度路径。SO(3) 系数不能仅凭 l 就标注成已验证的 O(3) parity；若任务要求反演规则，须实现并测试。
- 等变势的最后一层可能只有标量；允许 adapter 提供中间层或多层节点表示，不把 final layer 当作强制抽取位置。
- MACE get_descriptors 的便捷接口返回 NumPy，适合离线分析；训练、几何求导和生成须接底层 Torch 张量并保留计算图。[描述符文档](https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html)
- PBC、元素映射、cutoff/邻居限制及批次对应按实现声明。高阶求导与条件化生成均需各自实测；预训练能量/力权重不会自动成为已训练的响应头或去噪器。
- 模型能力检查依据所选层和算子，不只依据名字。缺少类型时可用张量积读出适配，但需验证表达范围与预算；不要求所有 backbone 原生具备 l=4。

### 3.6 不变模型的方向性输出：统一规格，显式选择信息来源

不变标量属于表示体系的特例，同一个 BackboneAdapter/OutputSpec 可以接纳两类模型。各输出能否构造取决于 backbone、几何上下文和读出的组合，不只取决于骨干名字。

| 输出/操作 | MACE、NequIP、Equiformer 等变节点特征 | ALIGNN、CGCNN、MEGNet 不变节点特征 |
| --- | --- | --- |
| 标量、分类、标量谱 | 从不变通道或等变特征构造不变量 | 直接用节点标量、按 scope 聚合 |
| 力/应力的能量导数 | 对不变总能量求坐标/应变导数 | 同样适用；输入距离/角度必须连回坐标与晶胞 |
| 直接向量/方向张量、张量谱 | 原生表示到目标 irreps，必要时补充张量积或几何基底 | 标量系数与几何方向基底结合，再按目标表示读出 |
| 辅助变量响应 Jacobian | 节点表示与辅助变量构造等变响应 | 结合几何上下文与辅助变量构造响应；单纯求导不会自动补足各向异性 |
| 生成坐标 score/噪声 | 条件化节点极向量读出 | 用条件化标量系数加几何向量读出；保留噪声过程和采样训练 |

native/geometry/hybrid 输入策略前移到 UnifiedFeatureAdapter，读出工厂只消费统一 CanonicalFeatures，不另按模型或性质名写分支。geometry 路线由结构上下文生成相对位移、球谐/张量积等基底，权重可依赖节点不变特征及距离/角度。它需要几何邻域，不要求 backbone 提供可学习边特征。

例如节点向量可写为 v_i = sum_j a_ij(h_i,h_j,d_ij,context) r_ij，r_ij 使用一致 PBC 镜像。该式仅说明方向如何进入读出，不承诺完整张量表达能力。一般高阶张量需要足够的多方向耦合/基底，不能只用 r_ij 的同次外积就声称覆盖所有分量与 parity。

仅有不变 h 的等变映射无法产生一般的非零向量或各向异性张量，0e 通道彼此做张量积也不能生成 l>0；几何、非标量输入条件或真实几何求导可提供方向信息。允许输出各向同性张量，但不能把它当作一般各向异性目标已被支持。禁止把普通 MLP 的 3/9/27/81 个输出直接 reshape 后标为已满足变换规则。

不变 backbone 加几何提升与统一读出后，整个预测器在方向性输出上满足对应等变规则，这不要求替换骨干的消息传递结构。适配层的参数量、额外几何计算及训练预算应单列记录。缺少所选路线能力时给出明确错误，不静默切换 construction；预留用户插件扩展。

### 3.7 同一个读出器之前的公共特征层

在要求相同等变输入的模式下，六类模型先经薄抽取器，再依次做基底规范化、原生通道投影、几何方向提升、融合与类型校验，输出同一 CanonicalFeatures。适配层不做结构 pooling，保留节点/批次、条件及几何计算图；输出阶数/parity/通道数由同一版本化 profile 固定。

在显式选择 common_equivariant 路线时建议 hybrid，保留等变模型原有方向信息，并为不变模型通过多方向球谐/张量积构造所需类型；它不覆盖 invariant_alignn 轻量路线。仅补零或只用单方向外积不能视为完整类型支持；纯换基与学习映射分开。响应辅助变量默认在统一读出器注入，再执行已确认的求导读出。

统一读出代码与结构不等于同一组训练权重可直接跨模型交换；本阶段默认分别训练，若需共享权重须联合训练或对齐。接口、568 维示例 profile、具体步骤、梯度与验收见[详细设计](unified_feature_adapter.md)。

另提供 invariant_alignn 可选轻量模式：ALIGNN/CGCNN/MEGNet 只做标量节点通道适配，按 ALIGNN 风格聚合/MLP与能量求导，不强制几何提升。统一的是公共读出 API，内部按特征类型选择分量或等变 backend。ALIGNN 原张量示例为固定分量直接回归；本框架响应仍默认求导，construction 与 transformation_guarantee 分开配置。固定坐标分量响应不保证一般方向变换，若需要严格变换规则则显式选择几何/等变路线。两种模式和求导包装的数学边界见[详细设计 §6](unified_feature_adapter.md#6-可选简化不变模型按-alignn-路线)。

## 4. 各任务的实现落点

| 任务 | 以节点为主的适配方案 | 当前难度判断 |
| --- | --- | --- |
| 标量/多性质 | 不变通道/不变量读出，加 pooling 与回归/分类头 | 低 |
| 逐原子标量 | 逐节点不变读出；保留原子标签对应 | 低 |
| 标量谱 | 不变读出输出固定频率网格；记录横轴、展宽和归一化 | 低 |
| 方向张量/张量谱 | 响应类默认对响应函数求导，直接读出须显式选择；原生/几何基底共用规格，频率作为附加轴 | 统一表示/变量/单位，不变骨干须补充方向来源 |
| E/F/S 力场 | 不变原子能求和为总能量，从完整几何计算图求力/应力 | 中，重点是求导与单位正确性 |
| 固定组成 CSP | 原生节点极向量或不变节点＋几何向量读出坐标 score/噪声；晶格按约定参数化，注入 timestep/condition | 中—高，主要是训练/采样和坐标约定 |
| 弛豫/MD/声子/谱学/显微 | 将已训练模型挂到对应模拟器，按任务组合能量、力和响应预测器 | 管线与成本问题，逐项集成 |

上述实现可以共用 trainer/数据基础设施，但不要求各任务仅靠一层相同的 MLP。任务覆盖不等于同一个 checkpoint 自动具备全部能力；当前默认分别训练，联合多任务模型另行设计。

## 5. 张量：统一目标表示，响应默认求导读出

张量不按性质名称划分核心实现。已登记且支持的响应性质默认采用 GMTNet 风格求导读出；直接 Cartesian 读出作为显式覆盖选项。两种方式共用目标表示/轴定义，响应变量与函数规格由性质库声明，不要求为每个性质新增专用 Python 类。

### 5.1 默认响应路径与响应定义

只借鉴 GMTNet 的物理响应式读出：由节点等变特征与辅助扰动变量构造响应函数，再对扰动变量求导得到张量。GMTNet 的论文 §3.3 和 Gradient_block/Piezo_block/Elastic_block 将这一读出与额外晶体对称约束分开实现。[G1, G2]

默认 derivative 构造采用“节点等变表示 → 原子级保留或结构级汇聚 → 与辅助变量构造等变响应 → 对辅助变量求导 → 笛卡尔张量”的路径。读出使用用户已有适配方式，不要求边特征或复制 GMTNet backbone。

对于不变 backbone，先以节点标量和几何上下文构造所需方向基底，再接响应块；并非把 ALIGNN 的标量隐藏特征直接声明为高阶等变特征。

典型定义如下，具体单位、比例因子和参考点写入目标配置：

| 目标 | 响应函数 | 读出 |
| --- | --- | --- |
| 介电张量 | 电位移 D(H,E) | 对辅助电场 E 求 Jacobian，epsilon_ij = dD_i/dE_j |
| 压电张量 | 电位移 D(H,eta) | 对辅助应变 eta 求 Jacobian，e_i,jk = dD_i/deta_jk |
| 弹性张量 | 应力 sigma(H,eta) | 对辅助应变 eta 求 Jacobian，C_ij,kl = dsigma_ij/deta_kl |

H 表示节点或汇聚后的等变特征。线性响应头的 Jacobian 与参考扰动取值无关；非线性头则需明确零扰动等评价点。同一机制可扩展逐原子张量，但须单独定义其辅助变量、单位和原子对应，不能直接套用结构级 pooling。

### 5.2 仍需统一的约定

- 目标的阶数、极/轴性质、指标顺序和输出位置；结构介电张量与逐原子 Born 张量不能混用同一种 pooling。
- 节点表示中相应通道是否可读出该目标；线性读出缺少所需表示时，可在适配层加入允许的张量积，而不是认定必须修改 backbone 或提供边特征。
- Cartesian/irreps 基底、归一化、Voigt 顺序及剪切因子；数据标准化或旋转时标签同步变化。
- 材料结构与标签是否在同一晶胞/坐标系；不能只转换结构而保留原标签。

### 5.3 求导链与范围

本路径不调用空间群识别，不做群平均/feature mask、equality adjustment、强制分量相等/为零或晶体对称投影；也不把这些约束列为任务验收条件。等变性来自模型与响应读出的构造，保留相应旋转变换检查。

训练时保留 Jacobian 的计算图，使张量损失可反传到读出和 backbone；推理也不能用会禁用所需辅助变量求导的全局 inference 开关。对辅助变量的 Jacobian 与对结构坐标/晶胞的导数分开声明。

响应必须实际依赖其辅助变量，并在约定参考点按样本提取 Jacobian；不能把整个批次的交叉导数当作单结构响应。验收检查参数反向链及源输出与辅助变量的连接，不因某个物理分量为零就自动判定失败。多阶响应按声明阶数保留所需图，不默认所有已接入算子都支持任意高阶求导。

若后续求 Raman 等几何响应，再沿张量预测到坐标的计算图求导。这不要求张量一定来自力场能量的二阶导数，也不默认与独立力场头满足所有热力学一致性关系；当前只要求目标张量可训练、可求导且定义正确。

因此，前稿列出的离散空间群/投影问题不再是当前张量方案的困难；实现重点只有响应变量、表示/单位、Jacobian 与参数梯度链。

### 5.4 显式可选：统一直接 irreps→Cartesian 读出

直接将目标 irreps 转成笛卡尔特征作为 direct 构造保留，响应任务只有显式覆盖默认 derivative 时才使用。它可供对照实验或其他直接张量目标使用，二者共用 readout 插件与输出表示接口；不因直接路线较省计算而自动替换默认求导路线。

统一路径：节点等变特征 → 按输出层级保留节点或逐 irrep 汇聚 → 可学习等变映射到目标 irreps → 固定基底转换 → 笛卡尔张量。

其中必须区分两步：

1. 学习目标系数。backbone 隐藏表示通常含很多通道；用等变 linear/张量积读出产生该目标的 irreps 系数，不直接把整个隐藏向量 reshape 成张量。
2. 基底转换。目标系数已经匹配目标张量表示时，使用固定线性转换得到 Cartesian 分量；e3nn CartesianTensor.to_cartesian 提供该类接口。[E1, E2]

若 final irreps 本来就是目标表示，仅需第二步。否则按目标生成可学习映射；任务之间共享同一个 head 工厂和转换逻辑，但各任务通常仍有独立参数。

不附加指标置换对称或晶体空间群约束时，通用 polar Cartesian 张量的表示如下。e/o 为反演 parity，不是简单由 l 的奇偶性决定；相同 l 的多份表示对应不同耦合通道。

| 阶数与完整分量数 | 目标 irreps |
| --- | --- |
| 二阶，9 维 | 0e + 1e + 2e |
| 三阶，27 维 | 0o + 3x1o + 2x2o + 3o |
| 四阶，81 维 | 3x0e + 6x1e + 6x2e + 3x3e + 4e |

以公式 ij、ijk、ijkl 描述目标即可程序化构建表示与转换；只在用户明确配置时采用 ij=ji 等指标对称形式，它会改变自由度，且不等于空间群约束。Born 等逐原子张量仍使用同一二阶转换，但不做晶体 pooling。

线性等变读出不能凭空产生输入没有的 (l,parity) 类型。如果骨干只有低阶表示，需要在读出层用允许的张量积构造缺失通道并验证表达范围；不保证任意低阶特征都能完整表达任意高阶目标。纯基底转换也不会补出缺失信息。

不变 backbone 的 0e 特征不能只靠自身张量积补出高阶类型，应走 §3.6 的几何基底路线；得到目标 irreps 后复用相同 Cartesian 转换。

相比辅助变量求导，这条路径不需要为每个张量构造 D(E)、D(eta) 或 sigma(eta)，通常减少 Jacobian 计算图和实现开销，并仍可对坐标/参数反向传播。对于对辅助变量线性的响应头，求导本质是提取线性系数；直接输出相应 irreps 是另一种参数化，但不声称不同参数绑定/非线性响应实现都严格等价。

补充验收：目标表示维数/类型匹配、Cartesian/irreps 往返、旋转/反演变换、原子与结构批处理对应、参数及必要坐标梯度。当前仅核算表示分解和查阅官方接口，尚未安装/实跑 e3nn，也未获得性能或速度对照。

## 6. 力场：允许使用完整坐标/应变求导

力场不要求 backbone 隐藏特征非标量；旋转不变且几何可微的总能量同样可以产生等变力/应力。适配时验证所选实现的坐标、距离、角度和晶胞梯度，不强制沿用 ALIGNN 的边位移求导实现。

- 总能量采用旋转/平移不变读出并明确 extensive 性、原子参考能及 total/per-atom 约定；力定义为总能量对笛卡尔坐标的负梯度。
- 应力从一致的仿射应变下求导：cell 和原子坐标同步变换，或在等价实现中固定分数坐标。单位、符号和 Voigt 规则明确，允许不同 GNN 的原生实现。
- 数学可微不自动保证力平滑：邻居列表更换、硬最近邻数量上限和 cutoff 的连续性仍要检查。新图后端与输入几何的 PBC 约定需统一。
- 力损失更新参数、声子 Hessian 等涉及所需阶数的导数；自定义算子的高阶反向和计算成本用小体系验证，不因默认一阶可微就自动承诺。

重点检查有限差分、旋转变换、能量/力一致性和应变约定，再做真实小数据训练。MD 稳定性单列验收，不能只凭 E/F 测试误差通过就认定适合所有动力学场景。

## 7. 生成：将 backbone 包装为条件去噪器

当前已定的是适配链与输出接口，完整噪声/采样配方尚未冻结，也未实现或运行生成。首期是固定组成 CSP：元素种类、数量和每个样本的原子数由输入给定，联合生成坐标与晶格，不同时承诺任意原子数/元素的无条件生成。

### 7.1 输入状态与调用链

状态包含 species、natoms/batch、带噪分数坐标 F_t、带噪晶格状态 u_t、时间步/噪声水平 t 和可选条件 c。晶格解码器将 u_t 转成有效 L_t；按行向量约定，当前笛卡尔坐标 r_t = F_t L_t。

每一步执行：

```text
(species, F_t, u_t, t, c)
  → 解码 L_t，构造当前 r_t 与 PBC 邻域
  → 条件化 backbone，抽取逐节点特征
  → 按任务适配标量/向量表示
  → 坐标去噪读出 [N,3] ＋ 晶格去噪读出 [B,6]
  → 统一采样器更新 (F_t,u_t)，进入下一步
```

训练加噪后同样调用这条链。每一步都使用当前带噪几何与晶格，不能从干净结构预抽固定特征，也不能在采样时沿用上一时刻的过期几何。构图可有缓存策略，但距离/方向/必要角度须对应当前状态。

### 7.2 时间、晶格与条件如何进入六类模型

encode(structures, context) 的 context 提供 t/噪声、当前晶格状态和组成/目标条件。优先在消息传递前的节点标量嵌入加入可训练条件投影，或在相应中间块加入类型合法的调制，使噪声信息进入 backbone 的特征更新。

| 模型 | 拟议条件接入位置 |
| --- | --- |
| MACE / NequIP | 初始 0e 节点通道或声明的交互块；非标量通道只用不变标量门控 |
| Equiformer | 初始 l=0 节点通道或注意力块的标量条件入口 |
| ALIGNN / CGCNN | atom embedding 后、图卷积前注入节点条件 |
| MEGNet | state/context 通道和需要的节点条件投影，保留状态更新 |

这些是 adapter 需提供的条件注入能力，尚未逐版本实现。仅在最终 head 拼接时间步可作为显式的 head_only 基线，但不能混称已条件化消息传递。配置记录注入位置、冻结/微调策略和新增参数；模型的旧性质/势能 checkpoint 可作初始化，不自动当作已训练去噪器。

### 7.3 坐标输出：两类 backbone，一套目标协议

- 等变模型：从原生/适配后的极向量通道读出笛卡尔向量或协向量，再按采样目标转换到所需坐标表示；生成一般只需标量/向量类型，不要求完整 568 维响应张量 profile。
- 不变模型：保留 ALIGNN 风格标量骨干，用端点节点特征、径向几何和条件预测 a_ij，再将周期边位移按标量权重聚合成每节点输出。可选使用骨干边特征，但不是前置条件；CGCNN/MEGNet 用同一节点对读出接口。

例如，选择分数坐标目标时可按 ALIGNN 风格构造 sum_j a_ij(h_i,h_j,d_ij,t,c) delta_f_ij；delta_f_ij 使用声明的 PBC 镜像规则。作者分支使用节点/边特征预测权重后聚合分数位移，我们将边隐特征改为可选。这是方向读出层，不需要把整个不变骨干改成等变网络。[作者去噪器](https://github.com/crhysc/alignn/blob/04ba46afa3c41fbf247ec426887910da49b0f81f/alignn/inverse/denoiser.py)

输出必须声明 target_kind 与 coordinate_basis：预测噪声、位移、score、scaled_score 不能只用 [N,3] 或 eps_frac 名字混为一类。score 是概率密度的坐标协向量；给定 L，行向量约定下的转换为：

```text
坐标位移：delta_r = delta_f L，delta_f = delta_r L^{-1}
概率 score：s_f = s_r L^T，s_r = s_f L^{-T}
```

实际目标若带噪声尺度，转换还需包含相应缩放。上式是固定 L 的坐标变换，不能直接拿来代替变胞采样中的联合状态定义。分数坐标输出也不等于 Cartesian 极向量；它们在各自空间执行所声明的变换检查。

统一的 GenerationPrediction 拟包含 coordinate_prediction:[N,3]、lattice_prediction:[B,6]、batch/ptr 与 target_spec。target_spec 绑定坐标空间、target_kind、噪声尺度、晶格参数化与标准化版本；sampler 校验完全匹配后才能更新状态，不从字段名猜测转换。

### 7.4 晶格输出与可复用配方

晶格头从结构级不变特征预测六个晶格潜变量的噪声/更新，而不把任意九个数直接当作有效 cell。等变节点先构造不变量，不变节点可直接汇聚；输出与坐标头共享条件化 backbone，不强制两者共用最后一层参数。

作者分支可作为第一套配方候选：分数坐标在周期环面上使用 wrapped-normal 过程并预测噪声尺度归一的 score；晶格以 G=L L^T 的正定平方根及矩阵对数构造六维状态，再做标准化 DDPM。坐标和晶格共享时间索引，但各自加噪，反向去噪器联合读取当前状态。[作者噪声过程](https://github.com/crhysc/alignn/blob/04ba46afa3c41fbf247ec426887910da49b0f81f/alignn/inverse/diffusion.py)

该候选不是已冻结的框架唯一算法。标准化统计、晶格尺度/分量顺序、噪声日程、坐标 target_kind、平移规范、采样步长/校正步骤、条件输入与预算要作为同一 generation preset 固定。wrapped-normal 的高噪声目标不能一律用未包裹高斯噪声的负值代替。

### 7.5 训练、采样和物性响应的区别

训练用带噪状态预测坐标目标与晶格目标，损失按各自 mask、尺度、权重和每结构归一约定组合；更新条件层、特征适配层、去噪头，以及配置允许微调的 backbone。采样器只消费统一预测对象与 schedule，不读取模型名。

生成的噪声/score 默认直接预测。“响应性质默认求导”不要求去噪 score 必须从力场能量求导，score 也不是物理力。若另做标量势 score 或物性梯度引导，作为独立构造/工作流声明并验导；不自动将势能优化当作生成训练。

### 7.6 当前未完成项与验收

尚需冻结第一套 generation preset、逐模型实现条件注入/特征抽取，以及验证共同坐标/晶格协议和采样器。接口设计支持六类模型，不代表已有六个可用生成 checkpoint。

实现时检查：时间/条件到输出的计算连接、训练/采样使用当前带噪几何、原子置换/平移/PBC 与相应旋转规则、score/位移变换、晶格有效性、空邻居/碰撞处理、target 与 sampler 一致性。生成原始质量与力场筛选/弛豫后的质量分别报告，记录候选数、条件和预算，不用测试真值几何挑候选。

独立键角扩散是 ALIGNN 的可选方法变体，不作为覆盖“生成任务”的强制条件；首期不要求 backbone 返回角特征。若做角状态研究，再独立声明状态、条件化和读出。

## 8. 剩余困难：性质与优先级

| 问题 | 为什么前提还没有自动解决 | 处理方式 |
| --- | --- | --- |
| 表示语义 | 等变节点特征仍有不同阶数、奇偶性、基底与原子顺序 | adapter 描述规格，按用户已有方式转换，任务头验证 |
| 不变特征的方向信息 | 不变标量不能单独恢复向量/一般各向异性张量 | 几何基底读出或有明确定义的导数操作；验证基底覆盖和端到端变换 |
| 标签/坐标/单位 | 可微与等变不保证标签来自相同晶胞或正确单位 | 准备数据时记录变换；做旋转、原子置换、Voigt 和单位检查 |
| 生成条件与周期变量 | 节点特征存在不等于模型理解时间步和高噪声几何 | 条件化适配、有效晶格参数化、正确 score 变换与采样训练 |
| 高阶导数与连续性 | 数学一阶可微不自动提供稳定高阶数值或平滑邻居边界 | 小体系导数检查、cutoff 扫查、按预算验证 Hessian/MD |
| 张量求导梯度链 | 求导得到预测后，监督损失仍需更新读出和 backbone | 保留 Jacobian 计算图，核对响应变量/参考点和参数梯度，不引入对称投影 |
| 原始数据与规模 | 少数标签未核实，轨迹/原子级任务更占内存和存储 | 先跑公开小子集、标记覆盖和未知项、实测再扩容 |

在用户前提成立且 readout/adapter 接口落实后，没有发现任务覆盖层面的新原则性障碍。以上主要是契约和数值正确性工作；不再因没有边特征或不复用 ALIGNN 任务头而阻塞适配。可训练不保证任务精度，需通过真实数据评测判断。

## 9. 插件与配置

```text
plugins/
  backbones/my_gnn/       # 不变/等变节点模型接口
    plugin.py
    README.md
  readouts/our_gmtnet/    # 用户已有求导式张量读出，无晶体对称约束
    plugin.py
    README.md
  datasets/my_dataset/
    plugin.py
    README.md
```

各插件通过 register(registry) 注册构造器与规格。readout 可以复用库内实现或用户代码；这里只预留接口，并不表示已经取得或实现了用户现有适配器。

下面为拟议配置示例，不是当前可执行接口；具体命令可在实现时复用 ALIGNN 入口，不以建立新 CLI 为目标：

```json
{
  "backbone": {
    "name": "user:eq_gnn",
    "plugin_dir": "plugins/backbones/my_gnn"
  },
  "dataset": {
    "name": "jarvis_tensor",
    "split_manifest": "splits/elastic.json"
  },
  "feature_adapter": {
    "name": "unified_irreps",
    "route": "common_equivariant",
    "profile": "response_full_rank4_v1",
    "mode": "hybrid",
    "geometry": {"cutoff": 5.0, "seed_lmax": 4, "coupling_depth": 2}
  },
  "task": {
    "workflow": "supervised",
    "auxiliary_inputs": [{
      "key": "eta",
      "scope": "graph",
      "representation": {"format": "cartesian", "indices": "kl", "parity": "even"},
      "unit": "dimensionless",
      "reference": 0.0,
      "requires_grad": true
    }],
    "responses": [{
      "key": "sigma_response",
      "scope": "graph",
      "representation": {"format": "cartesian", "indices": "ij", "parity": "even"},
      "unit": "GPa",
      "readout": {"name": "linear_response", "auxiliary": "eta"}
    }],
    "outputs": [{
      "key": "y",
      "scope": "graph",
      "value_kind": "continuous",
      "representation": {"format": "cartesian", "indices": "ijkl", "parity": "even"},
      "axes": [],
      "reduction": "mean",
      "unit": "GPa",
      "construction": {
        "operator": "derivative",
        "source": "sigma_response",
        "wrt": "eta",
        "order": 1,
        "batch_mode": "per_sample"
      },
      "target_binding": "elastic_tensor"
    }],
    "losses": [{"output": "y", "name": "mse"}],
    "metrics": [{"output": "y", "name": "mae"}]
  },
  "trainer": {"seed": 123, "epochs": 300}
}
```

示例是性质库默认响应方案展开后的草图：sigma_response 对辅助 eta 线性，输出 y 为其在零参考点的每样本 Jacobian C_ij,kl。这里的辅助响应不要求有独立应力标签，也不自动等同于力场应力。elastic_tensor 只是目标数据列绑定；indices 采用完整 ijkl，不默认对称约束。JSON 尚非可执行 API。

此示例明确选择 common_equivariant 路线，feature_adapter 采用 hybrid 后接 linear_response。在这条路线中切换为 ALIGNN/CGCNN/MEGNet 时保持相同 profile，只更换抽取/投影参数；它不是 invariant_alignn 轻量配置。辅助变量在零点取值不代表响应函数可先被常量化再求导；必须先保留变量依赖并计算 Jacobian。

运行前检查目标、节点特征规格和任务所需梯度/条件；不要求原 ALIGNN model.name 或边特征字段。不同 GNN 允许自己的构图；checkpoint 保存 backbone/readout/数据/协议版本，禁止把不匹配权重静默加载为成功。

## 10. 代码结构与复用原则

优先复用 ALIGNN 已有的数据准备、训练基础设施、calculator/模拟接口、生成与 benchmark 资产；允许按任务重构，不以同一 Python 类或输出键为完成标准。

拟按 backbones、adapters、readouts、properties、data、tasks、workflows、engine 八类职责组织，每个模块实现时附 README。若在现有 alignn fork 内落地，可将它们增量放入其源码树，不先迁移整个工程。

- backbones：MACE、NequIP、Equiformer、ALIGNN、CGCNN、MEGNet 及用户不变/等变 GNN 适配；不要求共享图对象，每个适配器目录附 README。
- adapters：模型特征换基/布局规范、公共通道投影、几何提升与融合，输出 CanonicalFeatures；profile/投影/几何/融合各子模块附 README。
- readouts：只消费 CanonicalFeatures，按 scope、目标表示和附加轴构建连续/离散输出及默认求导响应；不承担模型私有特征或几何提升分支。
- properties：维护内置性质条目、版本/定义及用户目录加载；响应条目默认 derivative 并展开 response_spec，显式覆盖另行记录；条目放 definitions/，目录内不放性质专用网络实现。
- data：现有来源与格式转换、划分、原子/坐标对齐、单位和 manifest。
- tasks：OutputSpec 校验、计算依赖、通用导数/转换、配置化 loss 与指标；任务 preset 只组合配置和数据绑定。
- workflows：筛选、生成、弛豫、MD、声子及其他派生应用，记录依赖和预算。
- engine：公共训练/恢复/批处理、结果与资源记录，不承担某 GNN 的私有物理约定。

不要求独立重写全部 trainer 或构建通用平台；先把任务覆盖跑通，再抽取确实复用的模块。

## 11. 分阶段交付与验收

| 阶段 | 交付 | 验收目标 |
| --- | --- | --- |
| T0：最小契约 | 六类薄抽取器、特征/输出/响应规格、性质库与路线 preset；首批六类 adapter | 六类模型可按所选路线抽取/适配节点；共同等变路线另验同一 profile，验证映射/类型/梯度，边输出缺省有效 |
| T1：监督任务 | 性质、逐原子、标量谱和公共训练/评测 | 首批六类模型在约定的同一公开小数据/划分上分别完成标量训练与评分，记录各自构图 |
| T2：向量/张量 | 公共读出 API 与两类 backend，响应默认 derivative；结构/逐原子与谱轴 | 六类模型逐一验收对应路线/保证、每样本 Jacobian、参数梯度、单位/标签；等变输出验变换，固定坐标分量不冒称等变，无空间群约束 |
| T3：力场 | 坐标/应变求导、E/F/S、calculator 与小型弛豫 | 导数/单位/梯度检查、真实小数据和稳定弛豫；MD 另验收 |
| T4：生成 | 节点型去噪、时间条件、晶格/周期采样与 scoring | 固定组成 CSP 跑通，分列原始及后处理结果，无需模型边特征 |
| T5：工作流覆盖 | CHIPS-FF/WBM/AtomBench 与所需谱学/显微流程 | 已获取资产逐项验证，缺失数据/流程标记不可用；指标/预算可追溯 |

必须测试原子置换、旋转变换、批次隔离、PBC、应变有限差分、所需高阶梯度、周期 score 约定和 checkpoint 恢复。检查用户适配器自己的数学契约，不要求逐元素匹配 ALIGNN 的 forward、梯度或优化步。

变换验收按输出声明执行：equivariant 输出及能量求导力/应力检查相应变换；fixed_frame_components 校验坐标/标签协议并记录不提供一般张量旋转保证，不以未声称的保证通过或失败冒充能力结果。

任何真实评测均记录：数据/划分、目标与单位、模型/读出、训练与采样预算、候选和弛豫设置、覆盖和失败样本。变化的是实现，保持的是可解释的任务级对照。

## 12. 当前范围与资源

本计划沿用公开数据、不新增 DFT；少数逐原子标签、特殊扩充集和论文展示流程仍需核实，不因有一个模型接口就声称这些资源已齐备。

默认一次训练一个任务，同一 GNN 类可用于不同任务，但不承诺同 checkpoint 全能或不同头之间热力学自洽。联合学习、AFM 融合和独立角状态研究按后续需要追加。

未来源码在本地修改并通过 Git 同步；服务器上的训练、推理、批量处理、编译和评测均提交 Slurm。缓存注明 backbone/readout/数据与几何版本，在线求导/生成不使用已断开几何梯度的特征缓存。

## 13. 参考与证据边界

- [E1：e3nn CartesianTensor](https://docs.e3nn.org/en/stable/api/io/cartesian_tensor.html)，提供 irreps 与 Cartesian 张量互转接口；不是任意隐藏特征的自动语义转换。
- [E2：e3nn ReducedTensorProducts](https://docs.e3nn.org/en/stable/api/o3/o3_reduce.html)，按指标形式构建目标 irreps 与 change_of_basis；[张量积文档](https://docs.e3nn.org/en/stable/api/o3/o3_tp.html)说明可学习等变通道构造。
- [E3：ASE Atoms.get_cell](https://docs.ase-lib.org/ase/atoms.html#ase.Atoms.get_cell)，明确 cell[i,j] 为第 i 个晶格基向量的第 j 个 Cartesian 分量；结构化几何不能仅凭矩阵 shape 当材料二阶张量处理。
- [G1：GMTNet ICML 2024 原始论文](https://proceedings.mlr.press/v235/yan24d.html)，只借鉴 §3.3 的等变响应/求导读出，不采用额外晶体对称约束模块。
- [G2：作者 GMTNet 输出块](https://github.com/YKQ98/GMTNet/blob/main/transformer.py)，Gradient_block/Piezo_block/Elastic_block 以辅助电场/应变和自动微分得到张量。实际实现由用户适配器接入，不照搬对称 mask 或数值修正步骤。
- [A1：ALIGNN 已核查快照](https://github.com/atomgptlab/alignn/tree/23f0146c4a61260fab5c5c9eb72a516491b76a70)，作为任务与可复用实现来源。
- [A2：CSP 作者分支](https://github.com/crhysc/alignn/tree/04ba46afa3c41fbf247ec426887910da49b0f81f)，作为可选角状态等变体的方法参考，不强制所有生成器复刻。
- [A3：Leaderboard 配套资产](https://github.com/atomgptlab/jarvis_leaderboard/tree/27c7d5591e876a1fc066af0ed5aab1480f5ff72a)，用于数据与任务级评测参考。
