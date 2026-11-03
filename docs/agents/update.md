# 进展记录

## 2026-11-02：直接 irreps→Cartesian 统一张量读出候选

- 用户询问不同性质是否必须不同求导方式，以及能否直接转换 final irreps。核对 e3nn 官方 CartesianTensor、ReducedTensorProducts、Irreps 和 TensorProduct 文档后确认该路线可行。
- 关键区分：任意 backbone 隐藏表示先经可学习等变 linear/张量积映射为目标 irreps；目标系数到 Cartesian 只是固定线性换基。只有 final 表示已精确对应目标时才可省去前一步。
- 计划新增 §5.4 候选：统一 head 工厂，目标 rank/parity/multiplicity 和输出层级由配置描述，各任务可有独立参数。不擅自删除此前用户已确认的求导方案。
- 角动量耦合递推核对通用 polar 二/三/四阶表示，维数分别 9/27/81；未加入指标置换或空间群约束。线性读出缺少所需类型时要显式补张量积或报告表达范围，不能补零假装完整。
- 对辅助变量线性的响应头，Jacobian 提取的是系数，直接预测系数属于另一参数化；非线性/绑定权重不同的实现不声称严格等价。
- 文档格式/相对链接/原 JSON 与求导路线检查通过，新增候选和表示计数核对通过，AFM 文件与状态历史保留。本轮无 e3nn 安装、运行时转换、训练或评测。

## 2026-11-02：张量仅保留求导式读出

- 用户明确只要张量求导读出，无需对称约束。已修订计划第 5 节、任务表、困难清单、T2 验收与索引，移除空间群识别、群平均/feature mask、equality adjustment 和分量强制约束。
- 核对 GMTNet 原文 §3.3 与官方 transformer.py：Gradient_block、Piezo_block、Elastic_block 采用辅助响应变量和 autograd Jacobian。计划明确 epsilon=dD/dE、e=dD/deta、C=dsigma/deta，不将求导读出误解为普通多输出头，也不强制这些响应来自独立力场的同一能量函数。
- 训练保留 Jacobian 图，使张量监督可更新读出与 backbone；辅助变量求导和几何导数分开声明。读出使用用户适配方式，无模型实现或求导实跑。
- 文档静态检查通过；历史记录和既有 AFM 计划保持。本轮没有代码实现、训练、下载或远程动作。

## 2026-11-02：按可微等变节点模型重订任务覆盖设计

- 用户进一步明确只需覆盖任务、不要求实现对齐；默认等变且可微、有节点特征、边特征可选，张量按 GMTNet 风格接入已有适配方式。
- 已将计划重写为节点特征主接口与模型专用读出，保留数据/目标/单位/测试和预算可比性；撤掉强制原 ALIGNN 输出头、边/三体特征、逐边 virial 和数值/训练步等价要求。
- 原始来源核对：GMTNet ICML 2024 论文、作者 gmtnet.py 和 data.py。读出包括晶体节点汇聚、feature mask 和输出块；data.py 用 spglib 识别对称群、构造投影及处理结构/标签坐标。区分固定结构回归与动态响应/生成引导中离散对称识别的问题。
- 无边特征的生成采用节点极向量读出路线，单列时间条件、带噪几何、晶格参数化和 fractional score/位移转换；独立角扩散不是覆盖生成任务的硬条件。
- 力场允许对完整坐标/应变计算图求导；剩余问题为梯度含义、单位、邻居边界连续性、所需高阶反向和成本，不再把已知模型可微性/节点表示当成未知障碍。
- check_equivariant_plan.py 通过：格式/链接/JSON、最新假设与任务覆盖、旧硬约束撤销、历史保留及 AFM 计划哈希。不声称已读取用户现有适配器或获得任务精度结果。

## 2026-11-02：工具箱设计收敛为 ALIGNN 2.0 最小解耦

- 用户明确只去除专属 GNN 依赖，其余下游保持一致。已重写 docs/plan/gnn_task_toolkit.md 并更新索引，替代上一稿独立框架/CLI/新任务实现方向。
- 静态读取固定上游的 config.py、train.py、train_alignn.py、alignn_atomwise_pure.py、calculator 和 CSP denoiser/model/train 路径，确认模型实例化和任务读出/求导存在耦合，不能仅替换 import。
- 新设计只抽出 stem/消息传递与必要几何适配，保留原任务壳；增加 backbone 工厂/注册以及用户数据薄适配。旧配置缺省使用原 ALIGNN，继续使用原命令、输出键和 checkpoint 选择。
- 明确保留张量扁平多输出、谱网格、能量修正/求导/单位、CSP 条件/头/扩散/采样及后处理预算，不默认引入新的等变头或生成算法。
- 原 ALIGNN 回归覆盖 forward、loss、梯度、一个优化步、恢复和 calculator/采样；新 GNN 再按原下游接口验收。无法相容的模型/任务组合或尚未获取的上游资产显式列出，不伪装保留或支持。
- check_alignn_plan.py 通过：文档格式/JSON 片段/相对链接、固定 SHA 与耦合路径、原输出键、原历史保留及 AFM 计划哈希。无业务代码、模型计算、下载或服务器动作。

## 2026-11-02：通用原子 GNN 下游任务工具箱设计落地

- 用户要求先在 docs/plan 审阅设计，本轮收敛为文档工作；未执行此前提及的工具箱实现。
- 新增 docs/plan/gnn_task_toolkit.md（16 节），更新计划索引；原 AFM 研究计划保持逐字节不变。
- 核心决策：统一 Structure/Target/Representation 契约、保留模型原生后端，按 model+dataset+task 组合检查能力；新增模型/数据通过 plugins 下的 register(registry) 扩展。
- 覆盖性质、逐原子、力场、张量、谱与固定组成 CSP 六类任务，分别规定坐标/应变导数、旋转变换、谱横轴、生成条件和后处理预算；不承诺任意 GNN 仅改输出形状即可兼容全部任务。
- 包含 frozen/finetune/native 三轨、统一训练与评测、配置示例、模块目录、真实小数据及物理验收、P0–P5 阶段，以及 Slurm/缓存约束。生成分 raw 与弛豫后评分，力场分静态可用与 MD-ready。
- 核对 PyTorch autograd、e3nn 与 ASE 官方文档；ASE 旧路径不可用，已使用当前 docs.ase-lib.org calculator 链接。
- 文档检查通过：UTF-8、行尾空白、代码块、示例 JSON、相对链接、接口/任务覆盖、历史追加保留及既有 AFM 文件哈希。没有模型运行、数据下载、环境安装、服务器连接或 Git 提交。

## 2026-11-02 00:04 +08:00：Guqq2 存储检查阻塞

用户授权连接服务器查询剩余空间；已在 gpu.md 记录用途、权限范围和只读检查方案。当前执行环境无法读取 SSH 配置，用户修改权限后重试仍被拒绝，提权请求亦被当前策略拒绝。未连接服务器，磁盘剩余容量及个人配额未确认。没有远程修改或计算任务，本地目录不是 Git 仓库，未提交。

## 2026-11-01：ALIGNN 2.0 存储预算

范围：按论文方法开展主要性质、谱线/张量、力场、WBM/CHIPS-FF、CSP 任务；不新增 DFT，不镜像全部原始 VASP 输出，不重复下载同一数据的 JSON/JSONL/Parquet 镜像。

已核实的体积锚点（十进制 GB）：

- 本地 ALIGNN 官方浅克隆（含 .git）实测约 176.43 MB；作者 CSP 分支副本约 176.30 MB，通常仅需选择适用代码版本，不应两份都当成必要成本。
- [MPtrj 官方元数据](https://api.figshare.com/v2/articles/23713842)：MPtrj_2022.9_full.json = 12,188,168,685 bytes，约 12.19 GB，文件本身是 JSON，不再乘一次“解压倍率”。JARVIS 镜像与此版本不必重复存储；数据字段和版本需要分别适配。
- [MATPES 官方 HF 文件表](https://huggingface.co/datasets/materialyze/matpes/tree/main)：2025.1 PBE 1.93 GB + r2SCAN 1.60 GB = 3.53 GB；2025.2 PBE 2.36 GB + r2SCAN 1.95 GB = 4.31 GB。整库显示 24.3 GB 是含版本、JSON/JSONL、整集/划分等重复表示的总量，不能当成单套必要数据。
- [WBM 官方文件元数据](https://api.figshare.com/v2/articles/22715158)：合并 entries+init 的 bz2 包 104,049,739 bytes；summary 12,745,623 bytes；MP computed entries gz 179,351,659 bytes；元素参考仅 6,350 bytes。选择一套必要结构/标签约 0.1–0.3 GB，解压和分析保留 1–5 GB 余量即可。整个 Figshare item 约 17.24 GB 含 all-mp-tasks、镜像/版本与其他任务文件，不是 WBM 必需体积。
- [OQMD 官方下载页](https://oqmd.org/download/)：v1.8 SQL.gz 21.1 GB，官方说明导入 MySQL 还需约 100 GB 附加数据目录空间。若仅从 API/导出文件取结构与目标标签，可避免完整 SQL 导入成本，但不在此宣称同版本完整导出已生成。
- CSP 六个真实 JSON 已在先前读取；准备好的数据约十余 MB量级，12 组模型权重各约 30 MB 的 LFS 指针，远小于主要力场数据。

工程预算（非实测汇总）：

- 代码/必要配套元数据：约 0.2–1 GB；ALIGNN 2.0 全部或大部分预训练权重另留约 5–20 GB（全部包大小未逐项验证）。
- 性质/谱线等整理好数据：暂留 5–15 GB；力场若包括 MPtrj、两套 MATPES、ALIGNN-FF 及百万级扩充数据，暂留 25–60 GB，后两类尚未核实准确发布文件大小。
- 连同 OQMD SQL 下载包，下载和归档预算取约 50–100 GB量级，并非严格上限。保留解压、转换版本、临时副本和完整 SQL 导入，建议可用空间至少约 300 GB。
- 实际训练：LMDB 原子图/线图缓存、radius/kNN 两种构图、不同任务重复缓存和 checkpoint/预测会继续放大。建议 1 TB 起，多个大任务并行且长期保留缓存时预留 1–2 TB 或更多；应在首批数据上测量 bytes/结构后更新预算。
- 全量 VASP/DFPT/CHGCAR/WAVECAR 原始档案、尚未定位的逐原子数据及特殊扩充集不能计入确定合计；如要求一并完整镜像，需要单独列清单核算，当前不能声称 300 GB 是全部资源的上限。

未执行下载、模型计算、SQL 导入或服务器连接。部分 Figshare API 无法抓取，按照既有网络经验停止重复，不将抓取失败解释成文件不存在。

## 2026-11-01 23:49 +08:00：晶体跨模型表示调研

本轮仅查询公开原始论文和核对文档，不连接 Guqq2，不下载权重，不运行模型。本地目录没有 Git 元数据，未进行提交。

### 原始证据与适用边界

1. Li、Walsh，[Platonic representation of foundation machine learning interatomic potentials](https://www.nature.com/articles/s42256-026-01235-7)，Nature Machine Intelligence，2026-05-07。七个 MLIP 经原子锚点相对表示转换后呈现共同几何，但局部差异持续存在。支持共享结构，不能推出原始向量相同或所有目标的信息相同。
2. Chorna 等，[Comparing the Latent Features of Universal Machine-Learning Interatomic Potentials](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aisy.202501497)，Advanced Intelligent Systems，2026-03-22；预印本为 [2512.05717](https://arxiv.org/abs/2512.05717)。比较 MACE、PET、DPA 和 UMA；正文 3.3 在同一 MAD 数据集、近乎相同架构下对照能量/力与 DOS 监督，energy→DOS 的 GFRE/LFRE 为 0.68/0.39，DOS→energy 为 0.56/0.28。两个方向均不能充分重构，支持目标相关差异；该指标不等同于严格信息论包含关系，也不直接证明下游融合收益。
3. Deng 等，[CHGNet](https://arxiv.org/html/2302.14231v2)，2023。磁矩监督参与原子特征学习，with-mag/no-mag 对照支持其作用；训练使用磁矩绝对值。不能把它当成能完整表达带符号磁序或任意非共线自旋态的模型。
4. Xu 等，[Spin-informed universal graph neural networks for simulating magnetic ordering](https://pmc.ncbi.nlm.nih.gov/articles/PMC12260432/)，PNAS，2025。显式引入自旋方向及磁矩初猜，支持磁序建模；这要求额外状态输入，不是普通结构嵌入的无条件替代品。
5. Moro 等，MultiMat：[预印本 v3](https://arxiv.org/html/2312.00111v3)、[2025 正式论文](https://www.sciencedirect.com/science/article/pii/S2950636025000088)。联合晶体、DOS、电荷密度与文本；预印本报告部分下游 MAE 相对 PotNet 最多改善约 10%，四模态相对三模态没有显著收益。支持多物理信息联合学习有价值，但不是三类独立预训练物理模型冻结后拼接的直接实验。

### 研究判断与拟议验证

- 工作假设：共享化学/几何信息与监督目标相关差异共存；不能仅凭“目标都源于量子力学”认定表示等价。
- 本轮检索未定位到完整覆盖力场、电子和磁性三类独立预训练嵌入、并系统验证融合增益的工作；这是检索范围内的结论，不声称不存在先例。
- 建议先冻结模型，比较单模型、两两组合与三模型组合；统一训练集、探针、维度/容量预算，并按材料原型或化学体系分组划分，核对预训练数据重叠。
- 表示分析结合相似性、双向重构和下游消融；跨模型直接逐维比较或直接平均没有充分依据。先以标准化后拼接为基线，再研究共享/私有空间。
- 晶体级池化应对照均值与均值加分布统计；涉及磁序时保留位点信息及自旋状态，避免平均消去反铁磁子晶格差异。通用检索表征与方向相关性质所需的等变表征应分别设计。
- 下一步若进入实验阶段，再按具体模型、目标性质、输入可用性与资源制定实现和 Slurm 计划；本轮没有启动实现或实跑。

## 2026-11-01：开始 ALIGNN 2.0 下游评测可获取性调研

- 已定位 arXiv:2609.19487 与官方仓库 https://github.com/atomgptlab/alignn。
- 将逐项核对性质预测、力场、晶体生成、谱学与显微模拟相关评测资源。
- 本任务仅本地与公开网络资料核查，不连接 Guqq2。

## 2026-11-01 23:24 +08:00：完成资源可获取性核查

结论：不能把“开源了模型”解读为“论文全部下游实验均已完整可复现”。性质预测和 CSP 的资源最明确，CHIPS-FF 与 E/F/S 评测已有实质代码，但存在路径和输入数据依赖；部分逐原子训练标签、WBM 论文专用流程、谱学与显微整套复现实验尚未核实齐备。

### 核查范围与版本

- 论文：[arXiv:2609.19487v1](https://arxiv.org/html/2609.19487v1)，2026-09-16，含附录。
- 官方 ALIGNN：`23f0146c4a61260fab5c5c9eb72a516491b76a70`。
- JARVIS-Leaderboard：`27c7d5591e876a1fc066af0ed5aab1480f5ff72a`。
- AtomBench：`324ed9d1d04ed947788a8435b8fc2e7dcfc76ea3`。
- CHIPS-FF：`7ab37a5e1ec65ad540dd7c6caaa555bda738d595`。
- 作者分支 `crhysc/alignn:lg-angle-diffusion-matrix`：`04ba46afa3c41fbf247ec426887910da49b0f81f`。
- HF CSP 数据：`69d23a2186b803fb3e5505126375cf3b9a2e75ca`；模型：`f52a701309f3a1f5d850206fb13fa455660b9d4a`。
- 下载源码、元数据与只读核查脚本位于忽略的 `tmp/alignn2-audit/`；机器可读摘要为 `evidence.json`。

### 1. 标量性质预测：主要资源可获取，但不是直接原样可运行

- [radius 贡献目录](https://github.com/atomgptlab/jarvis_leaderboard/tree/27c7d5591e876a1fc066af0ed5aab1480f5ff72a/jarvis_leaderboard/contributions/alignn2_radius)、[kNN 贡献目录](https://github.com/atomgptlab/jarvis_leaderboard/tree/27c7d5591e876a1fc066af0ed5aab1480f5ff72a/jarvis_leaderboard/contributions/alignn2_knn) 包含 run.sh、run_<task>.sh、config_<task>.json、预测 CSV zip 及数据构建脚本。
- 测试标签与固定 ID 划分放在 [benchmarks/AI/SinglePropertyPrediction](https://github.com/atomgptlab/jarvis_leaderboard/tree/27c7d5591e876a1fc066af0ed5aab1480f5ff72a/jarvis_leaderboard/benchmarks/AI/SinglePropertyPrediction)；结构由 `jarvis.db.figshare.data(dataset)` 获取。注意 benchmark zip 通常提供 ID→target，不能当成已经包含全部晶体结构。
- `build_property_data.py` 组合 dft_3d 的结构与 benchmark 标签，按 train+val+test 排列；配置使用 keep_data_order 和显式计数。
- `PY`、`TR`、`PYTHONPATH`、`LB` 等写死 `/home/kamalch/...`，需要适配。`alignn2_knn_wide/run.py` 使用 sys.executable，其 make_leaderboard_dataset.py 支持网络下载固定 benchmark，也有缺失结构检查，移植更方便。
- 不断言 Table 1/2 每个实验均有一一对应的已验收 recipe；目前核实的是主要贡献目录，且 README、论文正文与 SI 部分数值存在版本差异。

### 2. 谱线预测、张量与逐原子性质：公开程度不一致

- IR 和 TBmBJ 光学介电谱具有真实数据构建脚本：`build_ir_data.py`、`build_diel_data.py`，以及 run_ir.sh/run_dielectric.sh/config。固定标签入口在 [benchmarks/AI/Spectra](https://github.com/atomgptlab/jarvis_leaderboard/tree/27c7d5591e876a1fc066af0ed5aab1480f5ff72a/jarvis_leaderboard/benchmarks/AI/Spectra)，包括 irdb_ir.json.zip、mbjdiel_dielectric.json.zip、edos_pdos_ph_dos.json.zip。
- 官方有 `alignn/scripts/train_edos_pdos.py`，但它是旧式训练辅助脚本，不能直接认作全部 Table 3 的 2.0 精确复现 recipe。
- 官方 `alignn/examples/recipes/{tensor,spectra,atomwise}` 是合成的 40 个 Si 结构烟雾测试；模型注册表可见相应权重入口，仍不足以证明真实训练数据和测试划分齐备。
- [make_atomwise_dataset.py](https://github.com/atomgptlab/alignn/blob/23f0146c4a61260fab5c5c9eb72a516491b76a70/alignn/scripts/make_atomwise_dataset.py) 明确要求已有带标签 JSON（说明为 in-house 数据）或本地 OUTCAR；Bader 电荷还需另外预处理。`eval_atomwise.py` 能从 Test_results.json 算 MAE/RMSE，但未找到论文该整套标签的明确一键公开获取链路。不能将 dft_3d 的总磁矩当成逐原子磁矩。
- 张量和 Raman 的原始数据有论文出处，但本次没有确认每个目标的确切清洗、展平、归一化、划分及完整评测配置。

### 3. 力场能量/力/应力与 CHIPS-FF：有脚本，存在本地输入依赖

- radius 目录的 `ff_predict.py` 读取 benchmark test IDs，调用 AlignnAtomwiseCalculator 生成能量/力/应力预测；run_mlff_mlearn_*.sh、run_mlff_alignn_ff_db.sh、run_mlff_mptrj.sh 可见。
- `run_mlff_matpes.sh` 明确注明 matpes 不是其当前 jarvis 注册数据名，使用作者机器上的 `TRAINGING/MATPES/DataDir/id_prop.json`；`--model_dir` 也指向本地结果目录。因此脚本公开不等于所需转换后数据与 checkpoint 已经齐备。[MATPES 原始数据项目](https://github.com/materialyzeai/matpes) 公开，但还需复现格式转换与 ID 对齐。
- [CHIPS-FF](https://github.com/atomgptlab/chipsff) 提供 run_chipsff.py、general_material_analyzer.py 及公共 JARVIS 参考数据接口。
- radius 贡献内有 `run_chipsff_matpes.sh`、`submit_chipsff_model.sh`、`chipsff_surf_runner.py`、`chipsff_extract_pred.py`、`chipsff_leaderboard_matpes.py`，以及 matpes 预测 JSON、自洽元素化学势 JSON。这证明并非只有泛化框架。
- `run_chipsff_matpes.sh` 的主要计算步骤写在注释中，实际末尾只运行打包；仍需按说明提交真实计算。104 个 canonical JID、primitive/conventional cell 选择、自洽元素参考能与表面 Miller 指数影响指标，不能直接用默认值替代。
- 未逐个核实论文全部 AFF 变体及所有对比模型的精确 checkpoint 和输入配置。

### 4. Matbench-Discovery / WBM：公共基准可用，论文专用评测尚未定位

- [官方框架](https://github.com/janosh/matbench-discovery) 与 [WBM 数据入口](https://figshare.com/articles/dataset/WBM_dataset/22715158) 有公开来源；[基准论文](https://doi.org/10.1038/s42256-025-01055-1) 明确数据与评测代码公开。
- 在已检查的 ALIGNN 官方源码、root scripts、task_runners、Leaderboard alignn2_* 目录中，未定位到能直接重建该论文 Table 4 全部 F1/DAF/WBM RMSD/diatomic tortuosity 的专用流水线、全量预测和每模型元素参考配置。
- 这是限定检索范围的“尚未定位”，不是证明作者从未发布；也不能把 Matbench 中早期 ALIGNN 的提交当成 2.0 AFF 结果。

### 5. ALIGNN-CSP：资源最完整，需使用作者分支

- 官方有 [scripts/atombench](https://github.com/atomgptlab/alignn/tree/23f0146c4a61260fab5c5c9eb72a516491b76a70/scripts/atombench)：prepare_data.py、prepare_alex_data.py、generate_benchmark.py、symmetrize_predictions.py、score.sh。score.sh 调用 AtomBench 的 `scripts/scripts_consolidated/compute_metrics.py`，并非 inverse/evaluate.py；后者主要用于角分布与弛豫位移诊断。
- [task_runners](https://github.com/atomgptlab/alignn/tree/23f0146c4a61260fab5c5c9eb72a516491b76a70/task_runners) 有训练→生成→对称化→评分及 Slurm 包装，但其中部分旧实验数字、epoch/配置不应直接等同于最终角扩散实验。
- [作者模型分支](https://github.com/crhysc/alignn/tree/lg-angle-diffusion-matrix) 成功 clone；其中明确有 angle_mode=off/derived_aux/independent 与 B3 等实现。HF 模型卡要求该分支，不宜只安装官方 main 来加载独立角状态模型。
- [数据仓库](https://huggingface.co/datasets/crhysc/alignn-csp-ablation-datasets) 成功读取真实 JSON：JARVIS 847/105/103，Alexandria 6603/825/825；含结构、组成、target、target_poscar。DS-A/B 原始 pickle 有 LFS 指针，未下载其二进制。
- [模型仓库](https://huggingface.co/crhysc/alignn-csp-angular-ablations) 有两数据集×六模型的 config.json、history.json、generation_config.json、ABLATION.yaml、sym/nosym 指标与 best_model.pt LFS 指针。12 组 match rate/RMSD 与论文 Table 7 精度相符；例如 Alexandria A0 为 0.566061 / 0.025335 Å，JARVIS A0 为 0.446602 / 0.043622 Å。
- 上述分数属于生成 32 个候选、能量预筛选四个并弛豫后的流水线，不能标成 generator-alone 成绩；具体参数由 generation_config.json 记录。
- 单独 [csp-ablation harness](https://github.com/crhysc/alignn-csp-ablation) 的缓存网页可见，但本次 Git clone 返回 Repository not found；不能承诺完整 harness 当前匿名可拉取。模型本体分支和 HF 元数据成功拉取，不依赖这次失败推断。

### 6. 综合谱学与显微展示：组件可得，整套复现资源未确认

- 论文图 4/S6–S12 的声子→IR/Raman/INS 与光学对照，和图 5/S5 的 ALIGNN-FF→abTEM→AtomVision 管线，超出了直接谱线回归训练脚本。
- 参考数据的 JARVIS ID/MP ID 和方法在论文中有说明，[AtomVision](https://github.com/atomgptlab/atomvision) 也公开。但本次未在已核实仓库中找到这些具体图的全部驱动脚本、实验/DFT 数字曲线、图像文件及模拟参数清单，不判定“已完整开放”。

### 权重可获取性的边界

- [alignn/pretrained.py](https://github.com/atomgptlab/alignn/blob/23f0146c4a61260fab5c5c9eb72a516491b76a70/alignn/pretrained.py) 静态注册 124 项，均有 Figshare URL，设计上每项 zip 包含 best_model.pt、config.json、ids_train_val_test.json。
- 注册表明确注明 Figshare draft 不能匿名下载。当前环境无法成功抓取 Figshare API/下载地址，因此只判“有公开链接入口，未实际验证全部载荷”，不判私有或 404。
- HF 检查止于实际数据 JSON、模型配置/指标和 LFS 指针，未做任何权重反序列化、推理、训练或完整复现。

## 2026-11-01 23:47 +08:00：按方法复现标准重新评估数据问题

用户澄清允许自行整理公开数据、重新划分，不要求恢复精确实验快照，并保持不新增 DFT 的范围。由此需要区分“数据不可获取”和“缺少作者原始脚本/配置”；后者不构成当前任务的数据障碍。

- 补查 JARVIS 源码快照 `add61f2ad1f7020d23ffc2a815f604071ac03c86`：`jarvis/db/figshare.py` 注册 `ramandb`（Figshare file 55928318，约 5k Raman 数据）、`edos_pdos`（29216859）、`alignn_ff_db`（38522315）和 `m3gnet_mpf_1.5mil`（47281519）。仅核实下载入口，未执行这些数据的全量下载。
- [JARVIS 原始数据下载说明](https://jarvis-materials-design.github.io/dbdocs/thedownloads/)列出弹性、DFPT 等原始计算结果；[DFPT 说明](https://jarvis-materials-design.github.io/dbdocs/jarvisdft/)给出从已计算的 vasprun.xml/OUTCAR 提取 Born 电荷、压电/介电响应及 IR 的方式。因此张量任务不应因缺少作者展平好的训练文件就判为数据受阻；下载已有结果并解析不等于新增 DFT。
- 主体标量性质、DOS、IR/Raman、公开力场数据、WBM/CHIPS-FF 及 CSP 均有公共数据来源，可按论文任务定义重新整理。CSP 的真实 JSON 在前一阶段已经校验。
- 逐原子 Bader/net charge、逐原子磁矩的目标数据仍未明确；不能把结构总磁矩作为逐原子标签。论文特定扩充力场数据集和谱学展示用完整参考曲线，也不能仅凭其他公共数据存在就断言已获取。
- 当前结论：主体任务无普遍的数据获取障碍，少数专门标签/扩充数据需要额外核实；精确划分、硬编码路径和缺少成套绘图脚本属于整理与实现工作。

## 2026-11-02 00:06:27 +08:00：完成 Guqq2 剩余存储查询

- 成功登录 node42；根文件系统总 1.8T、已用 1.7T、可用 32G（99%），inode 使用率 5%；无独立 /home 挂载，个人配额工具不可用。
- 仅使用轻量管理命令；未修改远程文件、未启动代理或计算任务。本地非 Git 仓库，记录保存在 docs/agents/。

## 2026-11-02 00:08 +08:00：完成晶体预训练模型类别扩展调研

- 本轮仅查阅公开论文和官方模型说明；未连接服务器、未下载权重或运行模型。
- 声子/振动：VGNN 有结构到声子预测及预训练推理说明，见 https://github.com/RyotaroOKabe/phonon_prediction 。不能将预测声子本身等同于完整非谐热输运模型。
- 力学：MatTen 官方提供预训练弹性张量预测，见 https://github.com/wengroup/matten 。CGCNN 也有体模量、剪切模量专用权重目录。
- 介电/光学/压电：ALIGNN 官方目录有相关性质专用预训练入口，见 https://atomgptlab.github.io/agapi/apps/predict/alignn/ 。标量、完整张量和谱模型需分别核实，不把任务表直接当作所有权重已验证。
- 结构先验：CrysGNN 是图结构自监督预训练（https://github.com/kdmsit/crysgnn）；MatterGen 是结构生成预训练且官方发布基础模型（https://github.com/microsoft/mattergen）。生成器内部特征提取需额外规定噪声时间与池化，不能直接当作固定晶体编码器。
- 衍射/谱学：OpenAlphaDiffract 官方模型卡有公开单模型权重，输入 PXRD、预测晶系/空间群/晶格（https://huggingface.co/linked-liszt/OpenAlphaDiffract）。LightshowAI 的 OmniXAS 为结构到局域 XANES 预测且覆盖有限元素/吸收边（https://lightshowai.bnl.gov/）。从理想结构模拟谱只是另一种视图，不自动增加独立观测信息。
- 文本/工艺知识：MatBERT 是材料文献预训练模型，有官方权重说明（https://github.com/lbnlp/MatBERT）；不能将其文本嵌入解释成确定的工艺或合成可行性预测器。
- 多模态：MultiMat 与 MatBind 跨结构、电子/谱学、文本学习表示；MatBind 2026 预印本明确包含结构、模拟 PXRD、DOS 和文本，见 https://arxiv.org/abs/2607.08470 。本轮仅核实论文，不声称验证其权重可用。
- 判断：分类为监督目标/输入视角，不是互斥的物理信息来源。声子和弹性由势能面导数联系，专门监督仍可能改善有限模型的特征，但互补性需实验确认。全面嵌入可优先考察声子、响应张量和结构自监督，再按是否有真实实验/文本输入扩展。

## 2026-11-02 00:09:37 +08:00：完成 xmz 家目录大小统计

- 通过 Slurm 534 在 node42 执行 du -x -B1 --max-depth=1 /home/xmz，耗时 3 秒，COMPLETED、ExitCode=0:0，stderr 为空。
- 总占用 58040799232 字节（54.05 GiB / 58.04 GB）；generate_md 45856239616 字节（42.71 GiB），.cache 11982290944 字节（11.16 GiB），.nv 201416704 字节（192.09 MiB），pretraining 446464 字节，其余很小。
- 含隐藏项，不跟随符号链接、不跨文件系统；仅查看，无文件清理。Slurm 禁用 accounting，使用 scontrol 成功核验状态。无代码修改，本地非 Git 仓库，未提交。

## 2026-11-02 00:21 +08:00：多教师晶体表示蒸馏方案

- 本轮仅核查方法和文档，不连接服务器、不启动模型计算。
- 核心建议：冻结每个教师，在同一结构/原子对应上取特征；训练单一学生 h=S(X) 和教师专用投影 P_k:h→R^(d_k)，使 P_k(h) 重构固定教师特征。无需先把所有教师映射成相同向量。此多教师投影思路有 AM-RADIO 的视觉先例：https://arxiv.org/html/2312.06709v2 （不将其当作晶体实验验证）。
- UNIC 原文支持教师特征统计差异和独立投影/损失平衡的重要性：https://arxiv.org/html/2408.05088v1 。本方案的归一化和配置是晶体任务建议，并非逐项照搬 UNIC。
- 初始特征损失建议：对旋转不变的教师特征，在训练集固定均值 mu_k 和单一全局 RMS 尺度 s_k，得到 t_k=(z_k-mu_k)/s_k；L_k=mean_i(||P_k(h_i)-stopgrad(t_ki)||²/d_k)。每个教师只对有效样本求平均，无有效样本时跳过。均值/尺度仅由训练集估计。线性投影优先，小 MLP 作对照，防止投影头吸收所有复杂性。
- 不同时自由训练教师投影和学生投影再仅做匹配：双方可能退化到常数。教师目标固定；若增加可训练目标变换，需要额外保真或防塌缩机制。
- 关系蒸馏可在各自 P_k(h) 空间与教师之间比较距离/余弦关系，参考 RKD：https://openaccess.thecvf.com/content_CVPR_2019/html/Park_Relational_Knowledge_Distillation_CVPR_2019_paper.html 。不把彼此不一致的多教师关系都硬施加到同一学生相似度矩阵。
- 固定物理锚点可把教师特征表示为与同一组结构/原子环境的相似度，参考：https://www.nature.com/articles/s42256-026-01235-7 。每位教师要用自己的编码器重新编码同一批锚点，不能跨教师直接复用数值向量；轴语义统一也不保证数值和全部信息一致。
- 晶体约束：保持晶胞和原子映射；晶体级与原子级分开；不同图 cutoff 可以不同但结构/状态须一致。先用标量不变通道；方向相关通道需按 irreps 做等变投影与归一化，见 https://docs.e3nn.org/en/stable/guide/irreps.html 。普通逐分量标准化和全连接混合可能破坏等变性。
- 磁态约束：教师依赖自旋/电荷/温度等状态而学生只输入结构时，不能同时恢复同一结构的不同状态特征。需要条件化学生、固定明确状态或改变为状态分布预测，不能靠空间对齐补足缺失输入。
- 验收：独立化学体系/结构原型测试集上比较原始学生表示的冻结线性探针、各教师投影后的重构/关系相似性、单教师/多教师、特征蒸馏/关系蒸馏和容量对照。CKA 只作诊断，不能替代物理下游验收：https://proceedings.mlr.press/v97/kornblith19a.html 。
- 边界：上述目标鼓励学生保留各教师可读出的信息，但不自动定义一种适合全部性质的通用余弦距离。若重点是检索，需要额外确定相似度的物理语义、分支距离或任务条件度量。

## 2026-11-02 00:50 +08:00：MatterSim-MT 与多教师晶体蒸馏对比

- 主证据为 arXiv:2605.07927v2（2026-05-28）：https://arxiv.org/html/2605.07927v2 。先读 v1 后确认当前 v2 并核对关键段落。官方摘要：https://www.microsoft.com/en-us/research/publication/mattersim-mt-a-multi-task-foundation-model-for-in-silico-materials-characterization/ 。
- MatterSim-MT 已明确学习统一原子表示，不是仅在独立模型输出层集成；采用 GeoMFormer 风格不变/等变双流和任务头（S1.2），以 DFT 物理量监督（S1.3）。正文描述先 PES 预训练再多性质微调。
- 数据量不能混同：S3.1 为 35M E/F/stress 结构，172,488 Bader，3,051 Born 有效电荷/介电矩阵，284,195 铁磁假设下磁矩；不是 35M 全部具有全部任务标签。主要案例使用 10M 参数模型；未据最大 1.3B 扩展规模解释全部演示。
- 已验证多物理模拟包含 SiC LO–TO、BaTiO3 电滞与正极脱锂氧化还原；任务覆盖与本会话全面物理表示目标高度重叠。前序回答应更早把该模型纳入核心基线；不能把已有多物理统一表征作为我们的独有创新。
- 真正的方法区别：其主要监督是物理标签、多任务统一训练/微调；本会话方案是固定异构预训练教师，训练单一学生和独立特征/关系投影。多教师蒸馏不是对该方法的天然升级，也并非方法学空白。学生可能保留或损失教师知识，成本含教师推理。
- 证据边界：MT 磁矩假设铁磁排列（正文 4/讨论/S3.4），不等于任意磁序/非共线建模；列出的辅助直接目标没有完整 DOS 或电子哈密顿量。其主要评测不是冻结晶体嵌入对大量未见性质的统一探针评测。但这些事实不能证明我们的潜在方案更强。
- 公平判断：现阶段 MT 已有模型、数据和物理验证，而本会话尚无实现与实验；只能说其完成度和证据更强，不能声称任一路线在未比较的所有任务上更优。
- 推荐研究收缩：先将 MT 冻结嵌入和单教师/多教师拼接设为基线；在相同学生、可用数据和预算下比较物理输出监督、输出蒸馏与特征蒸馏，统计同等准确率下的数据/推理/训练成本；重点检验新增专家是否在 MT 未覆盖目标上有增量。
- 开放性核查：v2 的代码/数据声明是发表后按编辑要求公开；本轮读取的 microsoft/mattersim 与 Lingyu-Kong/MatterSim-MT README/模型卡仍主要描述 v1。没有把仓库名称或 v1 权重当成 MT checkpoint 已可下载，也不据此断言当前所有渠道均未公开。若后续实跑，需单独验证正确 MT 代码/权重。
- 本轮仅资料调研，无服务器连接、无下载权重、无训练或推理。

## 2026-11-02 01:04 +08:00：统一晶体 Base/Instruct/RL 范式定义

- 用户已明确：同一模型兼顾性质预测、结构生成与优化。此前仅围绕嵌入蒸馏的定位不足以覆盖目标，需从共同物理表示扩展到可条件化任务与行动输出。
- 建议主张：在同一晶体原生骨干上，Base 学习结构-性质先验，Instruct 将其适配为接受目标与约束的预测/生成/编辑模型，RL 利用外部反馈改善设计策略。三阶段各有目标、数据和独立验收，不能只改 checkpoint 名称。
- Base 不必等于 next-token 或纯力场。多物理教师蒸馏/监督可提供表示目标，但若最终需要生成/编辑，基础阶段需包含结构去噪/补全/生成训练和相应输出模块；不把 encoder 特征蒸馏自动视为生成模型。
- Instruct 用统一任务定义（任务、输入结构/缺失模态、条件、硬约束、目标区间、单位/容差）训练同一骨干；语言可作为接口但不是必要条件。不同任务可有类型化输出头；验收应包括未见目标组合/约束，而非仅固定 task ID 对已有回归头路由。
- RL 作用于可采样的结构生成/编辑策略，依据候选结构或编辑轨迹外部评估更新参数。仅调用外部优化器、主动学习补数据、固定模型 best-of-N 筛选不等同于 RL 后训练。代理模型奖励需与独立评价区分；保留预测/校准和多样性验收。
- MatterSim-MT 是统一原子多物理预测/模拟的强基线，外部也可驱动优化，不能声称它不能设计或优化。拟议区别是将任务规范与学习到的生成/编辑策略纳入同一模型的参数化接口，阶段性训练检验其迁移。原文：https://arxiv.org/html/2605.07927v2 。
- 近邻先例需进一步收紧创新主张：MatterGen 已有基础生成与性质条件微调（https://www.nature.com/articles/s41586-025-08628-5）；CrystalICL 已有晶体指令微调（https://aclanthology.org/2025.emnlp-main.929/）；CrystalFormer-RL 已用判别模型奖励后训练生成模型（https://arxiv.org/html/2504.02367v2）。
- PLaID++ 当前 v4（2026-06-11）使用 Qwen、Wyckoff 文本、SFT 和迭代 DPO：https://arxiv.org/html/2509.07150v4 。将 DPO 准确称为偏好优化，不一概写成在线 RL；未采用 v1 的过时机制描述。
- MatMind 2026 预印本已把材料知识训练、共享语言/数值双头预测及生成 SFT+GRPO 放入渐进框架：https://arxiv.org/html/2606.07712v1 。它是比 MatterSim-MT 更贴近“预测+生成+后训练”的相关工作，不能声称该宽泛范式尚无先例；本文仅核对方法，不接受其性能或因果推论为已独立验证事实。
- 可检验贡献建议：晶体原生的多物理预训练；同一模型上预测/生成/编辑的可组合任务接口；反馈后训练在固定评价预算下改善成功率，同时维持物理预测。与多模型路由、纯力场初始化、SFT-only、等预算 best-of-N/外部搜索等对照。
- 表述应使用 propose/aim 等未来设计措辞；尚无实验证明、无首次声明。需共同报告每阶段全部能力，避免 RL 后仅生成指标提高而预测退化。
- 全程仅研究与记录，不连接服务器、不实现、不启动训练和评测。

## 2026-11-02 01:07 +08:00：MatMind 原文定位与分支补查

- 用户的 MatWind 按上文理解为 MatMind（arXiv:2606.07712v1，2026-06-05）。主文：https://arxiv.org/html/2606.07712v1 。
- 核心表述见摘要与引言：结构-性质（作者称 structure-activity）知识与 physics-informed feedback 协同作用，渐进训练中结合知识注入、语言/数值双头与生成 RL。
- 方法 3.2.1：从 S1-Base 8B 出发，将 CIF、性质标注、自然语言材料描述混合做 next-token 训练，再用排名、区间判断、目标选择等构效任务监督得到 MatMind SAR；不是能量/力/应力力场预训练，也不是本会话讨论的异构物理教师嵌入蒸馏。
- 方法 3.2.2：预测模型从 SAR 出发，先冻结骨干 warm-up 数值回归头，再解冻，与语言监督一起训练。
- 方法 3.2.3：生成模型也从 SAR 出发，做 Wyckoff 结构序列 SFT，再以 GRPO 优化有效性、稳定性、新颖性和多样性相关反馈。
- 重要修正：作者在高层强调 unified model/framework，但方法的预测与生成分支都以 SAR 为起点。本轮已读文字不足以证明回归微调→生成 SFT→RL 后，单一最终 checkpoint 同时保持全部预测/生成能力。此前把其概括为一个已证明全面统一的最终模型过于笼统，应改为共同材料底座派生预测与生成能力的框架，不断言其必定采用独立 checkpoint，也不将此直接当成我们的既定创新。
- 对本会话的意义：基础训练信号（物理教师/几何目标 vs 材料文本 next-token）和同一后训练 checkpoint 的能力共存及组合泛化，可以构成待验证区别；仅三阶段命名不构成区别。
- 本轮未执行模型、未下载权重、未连接服务器。

## 2026-11-02 01:20 +08:00：查询式性质筛选与 GNN 检索策略后训练

- 用户提出将性质筛选改为类似 RAG 的查询，作为纯 GNN 嵌入模型 RL 的用途。建议形式化为目标条件晶体检索；只有检索后连接生成器才称完整 RAG，第一版无需 LLM 或结构生成器。
- 查询包含目标区间、硬约束、参考晶体/期望相似性和验证预算；可由结构化条件编码器处理，文本编码器可选。候选晶体由 GNN 编码。相似度 score(q,X)=g_phi(q)^T f_theta(X)（可归一化）。检索返回库中候选，不自动产生全新晶体。
- 三阶段映射：Base 多物理/结构预训练；Instruct 用查询-相关晶体匹配/排序及硬负例训练任务条件匹配；RL 根据检索结果或下游效用反馈更新可采样策略。示例策略是在检索候选池中按 softmax(score/tau) 无放回选择候选，属于上下文 bandit/列表选择，未必需要复杂长时 RL。
- 建议集合奖励为目标满足率、结构/成分覆盖及验证成本的组合，先做硬约束筛查再计算效用；评价器须与训练评分独立或至少留出真实标签。若以同一个相似度自评分，无法证明检索实际有用。
- 动作有两种可选实现，不能混同：离散候选/列表采样，或对输出嵌入构造随机策略。最新 RELER 是后一种，不能将其误写为仅离散文档 softmax。
- 原始先例：CLaSP v2（https://arxiv.org/abs/2501.12919）已对齐材料文本和结构，并支持以描述查询晶体；不声称文本检索首次。RELER v1（https://arxiv.org/html/2610.07731v1，2026-10-06）已研究嵌入空间 RL，用 vMF 嵌入采样、REINFORCE/RLOO，也支持固定索引只更新查询编码器；是通用检索先例，并非晶体实验验证。
- 参数与索引：固定晶体 GNN/索引，只训练查询侧，适合先验证任务奖励有效性，但不能称 GNN 本体经过 RL。若需 RL 更新晶体编码器，应在训练中重编码候选并定期刷新索引；对未召回候选加入探索，不能只重排固定窄池却声称全库最优。
- 基线：完整已知物性使用数据库过滤；比较性质预测后过滤、监督排序/对比学习、冻结 Base、SFT-only 以及等候选验证预算下 RL。语言包装或查询重述本身不构成 RL 贡献。
- 评测：库和查询同时按材料/原型/化学体系和未见目标组合划分，避免性质标签直接进入结构输入导致泄漏；指标包括约束满足率@K、召回/排序质量、候选多样性和成功候选所需评价次数。代理模型评价不能声称新增 DFT 发现；本项目本轮未执行任何计算。
- 推荐定位：利用多物理晶体图表示进行目标条件检索，以科学任务的集合效用做反馈后训练。相关研究空间在物理反馈、复杂查询与跨任务迁移，不在将筛选界面换成自然语言。

## 2026-11-02 01:37 +08:00：推动预训练表示采用的论文定位

- 用户核心目标是用有自身方法与强证据的文章推动性质预测采用预训练特征。现阶段不应把“模型不够 universal”或“社区不愿接受”当成既定事实；需转换为可检验的迁移与部署问题。
- MatterSim-MT v2 已证明广泛物理预测、多任务模拟和部分新体系/理论级别微调收益（https://arxiv.org/html/2605.07927v2）。本轮所读评测不等同于跨未监督性质的冻结表示、轻量读出及统一成本评测；这是证据范围区别，不是证明其表示不通用。它应是强基线/潜在教师，而不是必须击败的假想对立模型。
- 已有近邻包括势能模型中间特征作描述符（https://arxiv.org/abs/2402.18433）、局部冻结迁移（https://www.nature.com/articles/s41524-025-01727-x）、解耦预训练 GNN 特征与简单回归器用于外推（https://journals.aps.org/prxintelligence/accepted/10.1103/pbrg-x848）。因此“冻结特征+MLP 有效”不是足够的新颖主张。不同论文的分子/力场/特定晶体任务范围应分别标注。
- 建议问题定义：如何把已有原子基础模型变为对未见性质可复用、少标签、低新增训练成本的晶体表示？把新任务直接监督、多任务联合训练和不更新编码器的未见任务迁移分别评测。
- 具体待验证瓶颈：缺少相关信息、信息存在但层/池化/预测头读取困难、信息可读但提取/适配成本过大。不能先断言均值池化是唯一原因。特征重构研究支持层位与分布统计值得检查，但不直接证明下游提升：https://arxiv.org/html/2512.05717v1 。
- 推荐候选方法为迁移导向的表示后训练：以物理教师保真/结构约束保持基础信息，再通过跨性质 support/query episode，要求少量 support 标签训练的简单回归头能在 query 上泛化，外层更新表示。在最终完全留出的性质上冻结编码器，用小头验证。任务级目标不是重构任意教师坐标，也不依赖推理时逐性质更新骨干。
- 此候选不是已确立创新：闭式回归器元学习和材料 episodic 外推训练已有先例（https://arxiv.org/abs/1805.08136；https://www.nature.com/articles/s43246-025-00754-x）。本轮后一个期刊页抓取受限，仅使用官方检索摘要确认相关性，不能声称已全文审计。创新需要进一步落在多物理图表示的迁移机制及证据上。
- 先导实验建议：4-6 个公开性质任务、2-3 个可用骨干、多个标签预算与随机种子；先做原始冻结表示、层/池化对照、规范化多教师拼接、同学生架构从零训练及全量/局部微调，不先启动大规模蒸馏或 RL。
- 结果分支：单骨干简单读出已很强则研究稳定可复用提取/成本或压缩；多教师拼接稳定优于最佳单骨干才有理由蒸馏；微调强但冻结弱则研究表示可读性/适配目标。先导失败则收缩或改变假设，不通过选择性任务/划分制造正结果。
- 正式验收需区分结构新颖与性质任务新颖，整类性质留出、化学体系/结构原型或时间划分、多种标签预算、任务级置信区间及负迁移；不能只比 CGCNN。保留同骨干从零训练、强专用模型、强源模型冻结/微调、原始拼接和简单提取基线。
- 成本报告分开源预训练成本、一次特征提取及缓存、后训练、新任务拟合、推理；既不能把源预训练和特征提取都当零成本，也不必将完整源预训练重复计入每个新任务。
- 预训练与下游结构/标签重叠需审计；无法审计时明确未知，不声称严格 OOD。已有监督的性质只作控制，不能冒充未监督迁移。若 MT 权重未核实可用，不用 v1 替代并声称比较了 MT。
- 首篇宜围绕证据诊断+具体迁移方法+低门槛复用资源完成闭环；此前 Base/Instruct/RL/RAG 全部同时推进会扩大范围，RL 只有在主要科学问题需要时引入。
- 本轮仅研究建议，无新代码、无服务器连接和计算，不承诺正结果、绝对 universal 或发表结果。

## 2026-11-02 01:45 +08:00：已有预训练特征轻量迁移主张核对

- 直接回答：已有明确主张；“预训练特征可复用，新任务接轻量预测器”已不是新概念，不能用其作为首次范式贡献。此前定位建议是研究方向，不代表已完成新颖性核查或可发表方法。
- CrysGNN（AAAI 2023）：https://arxiv.org/abs/2301.05852 。原始摘要明确提出从大规模无标签晶体图预训练抽取知识并蒸馏到现有性质预测器，报告相对原始版本改善；它不是“完全冻结编码器+简单头”的同一方法，不混为一类。
- Universal neural network potentials as descriptors（2024）：https://arxiv.org/html/2402.18433v2 。直接把 M3GNet/MACE 预训练图块特征作为描述符，接回归器用于 NMR；实验证据主要为分子化学位移，不能扩张为全类晶体性质已被验证。
- 最接近的原始工作：Achieving Robust Extrapolation in Materials Property Prediction via Decoupled Transfer Learning，https://journals.aps.org/prxintelligence/accepted/10.1103/pbrg-x848 （PRX Intelligence，2026-09-24 accepted）。摘要明确主张分离预训练 GNN 特征与简单回归器，验证层状插层体系、四类外推/时间划分及费米能预测，并讨论连续/不连续化学空间边界。不将其部分任务改善泛化为普遍优于端到端。
- 该工作 arXiv:2602.18054 的检索摘要可见，v1 HTML 返回 404；采用 APS 原始摘要，不声称已全文审计。
- 材料 episodic/learning-to-learn 也已有先例（https://www.nature.com/articles/s43246-025-00754-x），不能把上一轮提出的 support/query 后训练简单包装成首创。
- 进一步判断：科学问题仍有意义，但创新应由新机制/新边界/强资源与可复现证据承担；列出更多任务、更多教师、Base/Instruct/RL 命名或查询包装均不自动补足贡献。
- 建议优先验证最贴近原始意图的问题：多物理专长是否能在最佳单源与强多任务源之外，提供未见性质的可迁移增益；若存在，能否蒸馏进单个冻结 GNN 且保持低适配成本。比较强单源、规范化拼接、同架构单教师与多教师学生，并把增强数据/标签/容量效应分离。
- 先做少量公开任务的低成本先导；稳定多源优势是继续投资该路线的证据，但原始拼接失败不能严格证明无互补。若缺少优势，收缩或转向，不靠夸大现有模型缺陷或选择性报告制造论文故事。
- 本轮仅资料和研究建议，无模型运行、无远程连接，未承诺发表或领域领导性。

## 2026-11-02 02:01 +08:00：预训练任务与下游性质适配关系先例

- 最直接先例：Chang, Wang and Ertekin, Towards overcoming data scarcity in materials science: unifying models and datasets with a mixture of experts framework, npj Computational Materials 8, 242 (2022)。原始出版页：https://www.nature.com/articles/s41524-022-00929-x ；作者预印本：https://arxiv.org/abs/2207.13880 。
- 18 个标量性质源任务分别预训练 CGCNN 特征提取器，19 个小数据下游性质任务；比较单任务、最佳单源迁移和多专家组合。Figure 5 分析预训练源任务到下游任务的学习权重热图。其源模型包含形成能、带隙、有效质量、介电与力学性质；已经直接研究任务关系和组合互补，不能把迁移矩阵或自动专家选择宣称为新概念。
- 边界：迁移/MoE 中冻结除最后卷积层以外的提取器层，并训练新头，因此并非完全冻结嵌入探针。源数据规模为 10,855–132,752，混杂数据规模和分布；学到的专家权重不等于独立迁移增益或因果重要性。期刊摘要为 14/19 优于成对迁移，arXiv 摘要数字不同，交付避免混用版本。
- 分子领域直接相关：Fast and effective molecular property prediction with transferability map, Communications Chemistry 7, 85 (2024)，https://www.nature.com/articles/s42004-024-01169-4 ，开放原文 https://pmc.ncbi.nlm.nih.gov/articles/PMC11024153/ 。PGM 衡量任务相关性并用于选择迁移源，12 个 MoleculeNet 数据集；这是分子证据，不能写成晶体已验证。
- 物理监督表示比较：Comparing the Latent Features of Universal Machine-Learning Interatomic Potentials, Advanced Intelligent Systems (2026)，https://doi.org/10.1002/aisy.202501497 。包含近似同架构和数据的 PET-MAD / PET-MAD-DOS 对照；重点是特征重构和信息关系，不是完整下游性质适配矩阵。
- SSL 目标对照：SPMat, Supervised pretraining for material property prediction (2025)，https://www.nature.com/articles/s43246-025-00999-6 ，比较 CGCNN 上 SimCLR/Barlow Twins 与加入监督的预训练。属于目标设计到下游性质性能的证据，和能量/力/磁/DOS 的受控物理任务对照范围不同。
- 新增研究意义需由实验证明：在一致架构、公共结构子集和可比预算上区分物理监督目标；现成模型对比仅能说明 checkpoint 的适用性。以冻结探针为主，微调单列，排除测试标签泄漏并报告结构重叠；CKA 和重构误差不能替代迁移预测误差。进一步方法应验证能否预测未见目标的源选择、或改善单一表示，相对既有 MoE/拼接/最佳单源和强多任务源评估，不能仅增加热图行列。
- 原始出版页直接打开遇到 Nature cookie 跳转限制，以上关键 2022 方法与数字通过原始出版页的索引全文核对；不声称已审计代码或附录全部细节。没有找到完全一致覆盖不等于证明首次。
- 本轮仅文献检索与 docs/agents 文档更新；未连接服务器、未训练或运行模型。

## 2026-11-02 02:12 +08:00：AFM 三路线迁移比较定位纠偏

- 用户澄清：研究不同物理任务预训练的 Atomic Foundation Models 在下游性质上的迁移差异，以 MatterSim-MT 多任务表示、各物理目标专用 AFM、多个专用 AFM 特征融合三条路线作直接对照。目标是 AFM 迁移可行性、专长与通用性的系统实证，而非普通 CGCNN 迁移方法或必须提出新融合算法。
- 修正此前范围判断：2022 CGCNN/MoE 是任务关联和组合方法背景，不能用来宣称现代 AFM 三路线经验问题已被解决。反过来，基础模型命名和参数规模本身也不足以证明新颖性，应突出比较对象、未覆盖的物理监督轴、冻结/微调、标签效率和外推证据。
- 最贴近 AFM 迁移基准：HackNIP，https://arxiv.org/html/2506.18497v1 。已有 ORB、EquiformerV2、MACE 冻结表示与浅层回归器的 Matbench 比较、层深和数据效率分析；仍主要是势能模型间比较，未直接覆盖多物理任务专长/多任务底座/多专用 AFM 融合三路线。故不能写 AFM 迁移整体 stays unexplored。
- DPA-2，https://pmc.ncbi.nlm.nih.gov/articles/PMC12369844/ ，最终期刊 2024：包含 ST/MT 大原子模型的零样本与下游微调比较；这里任务主要为异构标注 PES/数据域，和能量/DOS/磁/响应不同物理监督的三路线比较有边界。JMP，https://arxiv.org/abs/2310.16802 ，多数据域预训练和广泛下游微调已成立，不把多任务 AFM 迁移宣称为全新。
- MatterSim-MT v2，https://arxiv.org/html/2605.07927v2 ：大规模 PES 预训练后在磁矩、Bader、Born、介电等性质微调。可在本文归入多物理任务 AFM 路线，但描述其训练流程时应保留这一区别；S4.4 报告多任务输出误差，本次读取尚未发现用户所述三路线完整迁移比较。
- 补查 Exploring Transfer Learning for Materials Property Prediction（https://openreview.net/pdf?id=1WftHV5vqT），原始摘要为 MACE-MP-0 微调 Matbench 与负迁移/正则化讨论；网页遇到验证，未断言出版或接收状态。Multi-Task Fine-Tuning Enables Robust Out-of-Distribution Generalization in Atomistic Models（https://arxiv.org/html/2601.08486v1）研究适配时保留力场目标，和预训练表示来源的三路线问题不同。
- 可辩护英文范围：How physical pretraining objectives shape downstream transferability, and how specialist AFMs compare with multi-task AFMs and combinations of specialist representations, remains insufficiently characterized. 这是本次检索支持的定位判断，不是无任何先例的证明。
- 多任务干扰为待检验假设：MT 低于某专用模型可能受架构、容量、标签量和覆盖差异影响。现成模型对照具有独立实践意义；仅在归因监督干扰时补相同底座的专用/联合训练对照。融合收益同时与等维度/容量及同一目标多模型融合比较，以区分物理互补和容量/集成收益。冻结与微调结果分列，目标源选择仅用验证集，未见性质优先论证跨性质迁移。
- 三路线同样预先容纳不同结果：多任务最好支持联合物理表征，专用模型分工支持任务匹配，融合更好支持独立专长互补；不预设 MatterSim-MT 干扰或多源融合必胜。系统 benchmark/analysis 可为主贡献，方法创新并非必要条件。
- 本轮仅原始文献读取与 docs/agents/ 更新，无模型计算、无服务器连接、无 Git 提交。

## AFM 研究思考落地到 docs/plan

- 按用户要求新增 docs/plan/afm_transferability.md，集中保存不同物理监督专用 AFM、多任务 AFM（MatterSim-MT）和多专用 AFM 特征融合的三路线迁移研究。
- 明确系统 benchmark/analysis 可作为主贡献，保留物理任务依赖性、共享表示通用性和独立专长互补三组问题；不要求新增融合算法，不预设多任务干扰或融合必胜。
- 补齐相关工作边界及英文定位、同性质/相关性质/跨性质迁移区分、冻结与微调轨道、验证集源选择、泄漏审计、维度/容量/成本控制、任务干扰归因及不同结果的解释。
- 新增 docs/plan/README.md 作为目录说明与索引；未创建业务模块、未启动模型评测或服务器连接。

## AFM 迁移研究磁盘预算

- 已补充 docs/plan/afm_transferability.md 第 10 节，以情景假设估算磁盘，不代表显存、内存或公开资源实际下载大小。
- 先导工作集 50–150 GB，建议预留 200 GB；完整迁移研究约 200–600 GB，建议 1 TB；扩展原子级多层分析约 0.8–2 TB、大批全参微调约 0.5–2 TB，建议 2 TB 起，两种扩展会叠加。
- 数值核验：20 万结构 × 8 模型 × 4 层 × 512 维 × FP32 为 13.1072 GB；FP16 为 6.5536 GB；平均 40 原子的原子级缓存为 524.288 GB。
- 训练状态例子：FP32 参数与 Adam 两阶矩约 12P 字节；1 亿参数为 1.2 GB，每模型/任务/种子保留两份，10×5×3×2 份合计 360 GB。额外 EMA、权重副本和框架开销需另计。
- 明确无需下载完整预训练语料；冻结缓存共享、融合矩阵按需构建、原子级特征子集化、限制 checkpoint 数量。具体名单确定后使用真实大小和输出形状重新估算。
- 未连接服务器或核查当前剩余配额，未运行训练、推理和批量数据处理。

## 输出格式驱动的统一工具箱设计

- 将计划 §3 扩展为六类格式与正交规格：scope、值类型、空间表示、采样轴、聚合和单位；性质名仅用于数据绑定及记录。
- 将直接/响应求导统一为构造方式，生成/模拟保留为工作流；更新张量方案、JSON 草图、模块职责、验收和目录索引。
- 明确同 shape 不等于同数学对象，保留能量-力依赖、坐标/晶格变换、网格与训练/评测约定；不增加晶体空间群约束。
- 文档检查通过，AFM 计划及状态历史保留；无模型运行、远程连接或 Git 提交。


## 声明式性质库设计

- 在工具箱计划 §3.4 增加 PropertyCatalog，分离 PropertySpec、DatasetBinding 和任务/工作流 preset。
- 支持通过性质名称选择并展开通用输出/导数规格，保留原始规格入口；新增已有格式性质可只写条目与绑定，新算子走插件。
- 补充版本、定义、显式构造依赖、训练集标准化与支持状态边界；同步 properties 模块职责、T0 和索引。
- 文档检查通过，仅设计未实施，无数据下载、服务器连接或模型计算。


## 等变 backbone 候选清单

- 工具箱计划 §3.5 增加九个候选及 eSCN/eSEN 扩展来源，区分原生节点表示、内部取层、边到节点适配与预训练权重接入。
- 建议先 MACE/NequIP/PaiNN，后续 SevenNet/UMA；原始 EquiformerV2 需修正几何梯度，TensorNet 需内部张量取层并检查 PBC 限制。
- FeatureSpec 补充取层、SO(3)/O(3) 与梯度路径；记录 MACE NumPy 描述符与 UMA detached 导出不适于训练接入。
- 官方资料/源码和文档静态检查完成，既有历史与 AFM 计划保留；不代表已实施适配或获得性能结果。


## 首批四类模型与不变/等变接口统一

- 按用户范围指定 MACE、NequIP、Equiformer、ALIGNN，其他模型改为扩展候选；原版 Equiformer 与 V2 分别适配。
- 将 EquivariantBackboneAdapter 改为 BackboneAdapter，不变节点以 Cx0e 接入；新增计划 §3.6，说明几何基底/原生表示/求导路径及其能力检查。
- 同步标题、目录索引、任务映射、张量/力场/生成说明、input_basis 配置、模块与分阶段验收；无边特征强制项或晶体空间群约束。
- 文档检查通过，既有状态历史与 AFM 计划保留；未实现模型适配。


## CGCNN 与 MEGNet 加入首批范围

- 首批不变模型由 ALIGNN 扩展为 ALIGNN/CGCNN/MEGNet，与 MACE/NequIP/Equiformer 共六类；同步计划、目录索引、模块和 T0–T2 验收。
- CGCNN 取 pooling 前节点特征，可微任务在 Torch 中重算距离展开；MEGNet 优先接 Torch 实现，保留可选 state/graph_features，不承诺原 TF 权重自动兼容。
- 复用既有不变特征几何读出/导数路线，文档检查通过；无业务代码、模型运行、服务器连接或 Git 提交。


## 响应性质默认求导读出

- 按用户要求将支持的响应性质默认设为 derivative，性质库展开响应源/辅助变量/阶数/参考点，direct 只作显式覆盖，不自动回退。
- 弹性示例改为辅助应变到应力响应的每样本 Jacobian，保留训练反传图；更新响应章节、模块职责、T2 和索引，六类 backbone 范围不变。
- 文档与依赖配置检查通过，状态历史与 AFM 计划保留；无模型计算、数据下载或远程连接。


## 统一读出前的可训练特征适配层

- 新增 docs/plan/unified_feature_adapter.md，定义六类薄抽取器后的 BasisCanonicalizer、NativeProjector、GeometryLift、Fusion，输出固定 profile 的 CanonicalFeatures。
- 默认建议 hybrid，保留等变原生表示并为不变模型构造多方向几何类型；参数/预算、表示/梯度契约和共享代码/共享权重边界明确。
- 主计划新增 §3.7 和 adapters 模块，JSON 将模式前移到 feature_adapter；统一读出器只消费公共特征，响应仍默认辅助变量 Jacobian。
- 文档与符号检查通过，历史与 AFM 计划保留；未实施或实测模型。


## ALIGNN 风格的不变特征轻量模式

- 在统一特征设计 §6 增加 invariant_alignn：不变节点通道投影后接公共 API，按特征 kind 选择分量/等变 backend，不要求所有不变任务生成 568 维表示。
- 明确 ALIGNN 原张量示例直接分量回归与框架默认求导不同；R(H,q)=A(H)q 的 Jacobian 等价于系数预测，不新增旋转/热力学保证。
- construction 与 transformation_guarantee 分列，固定数据坐标约定与严格等变路线分别记录；完整统一等变输入模式保留，主计划已同步。
- 文档检查通过，既有历史和 AFM 计划保留；仅设计，未实现或运行模型。


## 整体架构清晰度审查

- 主计划新增 §0，明确架构可进入原型，尚需冻结接口/具体版本、性质数据评测与任务 preset、完整生成配方。
- 收口统一 API 与共同等变 profile 两条路线，限定 hybrid/568D 示例仅适用共同等变路线；JSON 显式选择路线，T0/T2 与变换保证分列验收。
- 最小闭环建议一等变＋一不变模型覆盖标量、能量与响应求导，之后扩展六类模型和工作流；本轮不启动实现。
- 文档检查通过，既有历史与 AFM 研究计划保留。


## 生成 backbone 的条件去噪适配

- 主计划 §7 扩展为固定组成状态与调用链、六类模型条件注入、两类坐标读出、晶格/作者配方候选、训练采样区别和未完成项。
- 不变模型参考 ALIGNN 标量权重＋周期位移，边隐特征改为可选；等变模型用向量通道，不要求生成任务采用 568 维响应 profile。
- 明确生成默认直接预测噪声/score，响应默认求导不外推生成；统一预测对象绑定目标空间、尺度及晶格参数化，score/位移变换分别处理。
- 文档/坐标对偶公式检查通过；完整 generation preset、条件注入实现和采样评测仍未冻结/实施。


## 2026-11-02 14:23:24 +08:00：按用户要求移除当前工作区 Git

- 已删除 E:\课业\课题组\universal\.git；保留项目内容及 .gitignore，未创建新仓库。
- 验证其他根目录条目及直属项目文件 SHA256 均保持；操作记录仅追加或更新当前快照，历史保留。

## 2026-11-02 14:25:15 +08:00：删除子目录中的全部 Git 元数据

- 按用户明确授权删除 tmp/alignn2-audit/ 下 10 个 .git，复查工作区内无 .git；876 个非 Git 文件及其他目录保留。
- 未重新初始化，.gitignore 等项目文件保留；无远程连接或代码修改。删除目标：
- tmp/alignn2-audit/leaderboard-source/.git
- tmp/alignn2-audit/leaderboard/.git
- tmp/alignn2-audit/jarvis-source/.git
- tmp/alignn2-audit/jarvis/.git
- tmp/alignn2-audit/csp-model/.git
- tmp/alignn2-audit/csp-data/.git
- tmp/alignn2-audit/chipsff/.git
- tmp/alignn2-audit/atombench/.git
- tmp/alignn2-audit/alignn-csp-matrix/.git
- tmp/alignn2-audit/alignn/.git

## 提权与服务器仓库同步条件确认

- 已验证受控提权后的 SSH 和现有 SOCKS GitHub 端到端访问。
- 确认 /home/xmz/universal 已 clone，先 git pull 后核对 origin/HEAD/工作树，和本地初始提交一致。
- 仅记录连接与同步检查；完整实现目标仍暂停，本轮未继续实现或提交 Slurm。

## 2026-11-02 15:18:20 +0800：公共模块、模型入口和求导响应实现

- 添加结构/批次、完整可微 PBC 图、JSON/extxyz 标签绑定、性质目录、统一特征适配、三类不变架构及等变模型入口、二至四阶求导响应、E/F/S 与训练重载记录框架。
- 13 项解析单元检查通过；官方 MACE/NequIP、Equiformer 与真实 10 结构矩阵尚待 Slurm 验收。记录架构变体，禁止将未验收项标为通过。
- 修正根 data ignore 误伤源码子目录；添加换行规范。服务器网络下载改为本地 Linux wheel+scp，模型依赖分环境。

## 2026-11-02 15:48:44 +0800：固定组成生成与补充模型/力场验导

- 新增周期 wrapped-normal 坐标与六维 log-Cholesky 晶格双头、时间/晶格条件、共用方向读出和 Langevin 采样；添加训练重载执行记录与无标签 infer 命令。使用正定晶格图避免重复特征值问题，生成样本删除模板标签。
- 默认18项单元检查通过，MACE官方模块另1项通过；Slurm真实数据训练矩阵仍待运行，报告显式区分执行检查与生成质量。
- 发现可只读复用服务器已有Torch，已核对其真实路径；子环境不递归处理父环境pth，修正依赖引用方式。

## 2026-11-02 16:07:06 +0800：真实小数据、索引约定和批量验收入口

- 从官方JARVIS与作者GMTNet数据整理11组十结构数据，保留原标签/单位/来源；压电选非零标签，分类5+5，不补造标签。
- 增加VASP Voigt显式顺序，正确处理xy/yz/zx；周期镜像拓扑分块向量化，保留完整镜像与可微几何。
- 新增66格矩阵配置/Slurm数组执行/状态汇总，MACE独立解释器，缺数据或未执行均保留pending。19项本地单元和数据静态检查通过；Slurm535旧版13项已通过。

## 2026-11-02 16:18:31 +08:00：保留力场外部坐标高阶梯度

- 传入requires_grad坐标时不再detach，create_graph=True可从力继续对原输入求Hessian，用于声子等派生流程。2项E/F/S与外部梯度测试通过；无真实训练验收结论。

## 2026-11-02 16:55:57 +0800：首轮66格真实执行验收

- 六骨干各11任务的十结构训练、参数/梯度、loss下降和checkpoint重载推理通过；生成另采样。新增acceptance记录明确架构变体、运行commit70e5bb0、数据来源、依赖和未完成范围。
- 证据已从服务器续传回本地ignored results/server-20261102，原JSON与日志可审阅。旧Slurm状态已清理的64项如实标注。
- 继续EFS/Born/Raman数据与派生流程，不完成或暂停总目标。

## 2026-11-02 17:28:17 +0800：非极性张量基底v2与匹配DFPT入口

- 新增四极矩相关耦合，避免极向量矩为零时丢失允许轴向/奇宇称分量；新训练默认v2，旧无格式标记checkpoint明确重建v1。执行metadata改为训练开始时记录。
- 26项默认单元通过，另DFPT解析1项通过；新增Slurm checkpoint回放入口。原66格仍对应70e5bb0/v1，尚未作为新版训练证据。
- 下载并校验14份JARVIS原始DFPT小归档；新增同几何free_energy/forces/ASE stress/Born/介电解析与Slurm整理脚本，不补零、不做ASR或空间群投影。

## 2026-11-02 17:47:49 +0800：兼容旧VASP DFPT标签

- 首次真实批处理674因ASE未识别epsilon失败0/10，保留失败报告；XML本身已有电子介电张量。兼容旧epsilon（包括ASE返回None），不补造数据。
- 2项标签版本测试通过；源码886f6f0的两环境完整单元与66个历史checkpoint回放已通过。下一步同步此修复并重跑真实批处理。

- 2026-11-02T18:16:41.810936+08:00：实现ASE calculator/FIRE/短MD/Gamma声子、IR/Raman/中子谱、KK与abTEM STEM接口；新增真实Raman/光学整理及自定义数据/性质入口。默认32项通过，DFPT18/18、新张量9/9运行证据已确认；后续真实流程继续验收。

- 2026-11-02T18:37:15.642364+08:00：新增实际report/图像证据汇总器、缺失/失败/重复ID拒绝检查和五份使用配置；真实Raman/光学707各10条整理成功，711训练数组已提交。两环境单元各32通过；706模拟因abTEM1.0.8的Py310 typing.Self兼容问题失败，改pin1.0.6并保留旧日志，下一步隔离环境重装和Slurm pilot。

- 2026-11-02T18:52:18.363550+08:00：完成六模型各16项真实十结构训练/重载推理及各10结构模拟，96格+6工作流服务器/本地审计均通过；补最终验收说明、使用手册和示例路径。原始日志/报告/60图已取回，准确保留各阶段Git源码与失败记录。下一步同步文档并清理自有网络服务。

- 2026-11-02T18:53:45.467005+08:00：最终文档、15链接/16数据集SHA/60图检查通过；自有两个临时HTTP服务已释放。进入最后同步与专用代理释放，模型计算工作已全部完成。

- 2026-11-02T18:55:48.356791+08:00：全部实现、96格训练/重载推理、6×10结构模拟及证据归档完成；最终源码和使用手册已同步服务器。自有HTTP/SSH代理已清理并验证远端1080释放；本提交仅记录收尾，不引入新源码或实验变更。

- 2026-11-02T20:39:40.893380+08:00：落地docs/plan/usage.md约定的--mode入口、YAML/JSON和CLI覆盖、日志/权重/结果独立输出，增加原子epoch checkpoint与Adam/epoch/Torch RNG续训；保留旧入口和基底版本，旧checkpoint明确暖启动。补ALIGNN带隙YAML及Slurm透传/真实十结构验证脚本。下一步同步服务器实跑。

- 2026-11-02T20:49:27.218331+08:00：完成文档式CLI实现与实跑：731十结构train15→resume30→infer、连续30参数完全一致；732/733两环境各39项检查通过；734实际Slurm透传入口通过。证据已本地归档，文档补实测记录，下一步同步记录并释放唯一专用代理22596。

- 2026-11-02T20:51:26.173989+08:00：完成文档式CLI交付与服务器同步；已核对并关闭本轮代理，远端1080释放。新接口可按docs/plan/usage.md使用，无待实现或待验收项。

- 2026-11-02 21:28 +08:00：按用户提问完成当前UGNN快捷工具使用缺点静态评估，重点为默认十结构/全批处理、评估与预检查入口、数据语义配置、模型权重/环境和模拟工作流门槛。仅更新评估记录并向用户交付结论，保留原有未提交实现，不连接服务器或进行功能改造。

- 2026-11-02T21:34:39.952470+08:00：实现GraphRecord/GraphBatch、BaseGraphBuilder/BaseGNN/GNNOutput和StandardBackbone，独立KNN/radius/stored/plugin构图、用户GNN目录工厂，加入最小独立KNN+GCN示例。新增统一docs/standards.md及config/dataset版本、checkpoint协议/源码指纹；数据/图变化和旧缓存不再静默改变恢复语义。单元51项通过，下一步Slurm真实分子。

- 2026-11-02T21:45:18.129110+08:00：首轮735真实分子与导入图对照全部通过、736/737各51通过。最终规范审查修正显式v1字段混用与空标签解释，拼错图属性明确拒绝，补14项针对检查通过；旧无版本几何仍兼容。

- 2026-11-02T21:55:28.845677+08:00：完成自定义GNN/分子图及统一格式标准交付：最终738真实分子动态/导入图与续训对照通过，739/740各52通过，证据与标准数据已取回。docs/standards.md增加接口图和实测来源，下一步同步记录与关闭专用代理41896。

- 2026-11-02T21:59:08.636010+08:00：完成自定义GNN/图协议与统一文件标准交付，最终规范及证据说明已同步；自有代理精确退出、远端1080释放。所有实现和验收项均已完成。

- 2026-11-02 22:15:14 +08:00：完成UGNN生态架构建议及现有模块对照，参考PyPA插件发现和ASE计算器官方接口；提出稳定协议、独立插件、能力认证、配方/基准和渐进路线。本轮仅修改任务记录，未改业务代码或运行服务器任务。

- 2026-11-02T22:25:58+08:00：完成官方checkpoint接入设计评估（无业务代码改动）：列明六个模型的主干变动，建议保留官方主干/预处理并随机初始化统一适配器与读出；需要检查主干参数及buffer完整覆盖，允许缺失仅限新增模块。未运行服务器或数值验证。

- 2026-11-02T22:44:04+08:00：第一实现单元完成本地修改与数据静态/单元检查：默认全量、可复现子集/epoch采样、batch_size/max_atoms/dtype、JSONL索引与流式推理、全局损失尺度和加权报告、生成逐结构固定噪声、续训设置检查。接下来提交同步并用Slurm做训练/推理回归；六官方模型的真实权重加载/微调仍未完成。

- 2026-11-02 22:56:46 +08:00：核对ALIGNN2.0(arXiv:2609.19487)、原ALIGNN(NIST官方论文页)、JMP(arXiv:2310.16802)，完成第一版模型—任务解耦与广任务基准定位。建议避免将逐任务训练误称为同权重通用表示；已有实现任务保留，本轮仅研究讨论记录。

- 2026-11-02T23:05:12+08:00：mini-batch单元服务器两环境各57项回归通过。首批官方artifact已本地下载（CGCNN带隙791173字节、MACE-MP0 small32581838字节、NequIP-OAM-S0.2 5642702字节、MatGL-MEGNet三文件），来源和hash保存在ignored models/official/download-manifest.json；官方包装MACE/CGCNN/MEGNet首版未宣称真实验收，继续依赖安装与10结构微调。

- 2026-11-02 23:05:18 +08:00：核查ALIGNN2.0论文v1(2609.19487)及官方alignn_atomwise_pure.py、tensor recipe。确认常规任务更换读出，力场增加能量导数，生成增加条件输入和去噪训练，派生光谱/显微依赖工作流；未执行新增实验或服务器操作。

- 2026-11-02 23:08:47 +08:00：完成ALIGNN2.0跨任务参数量答疑，核对官方nn.Linear配置及论文3节/表4。区分固定主干下的头部差异与不同宽深发布模型，示例为计算值而非权重逐项实测；未运行模型或服务器任务。

- 2026-11-02T23:19:49+08:00：增加官方artifact嵌入、严格来源hash校验及四个原实现包装；条件特征仅在输出拼接。源模型、元素映射、邻居与径向基不替换。MatGL1.1.3依赖声明dgl>=2与计划DGL1冲突，安装解析失败且未改既有包；将选择支持DGL1且能加载同一官方发布权重的官方MatGL版本，先核对声明再安装。ALIGNN与Equiformer包装、所有官方真实微调仍待完成。

- 2026-11-02T23:27:49+08:00：官方读出截获机制完成3项基础单元和静态检查；新增首个MACE独立参考/10结构微调/自包含重载Slurm验收脚本，其他独立参考分支仍明确未实现。修正文档旧全batch描述。接下来提交同步并先运行已有MACE环境的真实官方checkpoint，官方额外依赖安装独立推进。

- 2026-11-03T00:27:08+08:00：六官方provider首版与五个新增独立原生参考路径已写齐；官方source/version签名、防旧头释放计算图、缺少原生1o时仅在最终生成头做几何适配。相关解析/梯度5项通过，源码85文件校验包通过并已传服务器，依赖安装成功。当前只有MACE743真实官方十结构微调通过；其他模型接下来Slurm验证，不预先宣称全部完成。

- 2026-11-03T00:47:21+08:00：官方真实验收累计MACE743/CGCNN744/MEGNet745三类通过，最新两环境各62项回归。定位并修复NequIP0.14加载器返回容器的接口差异，不重建或修改其GraphModel；输入进一步复用官方from_ase。MatGL状态数组批处理去除低效构造警告，数值转换不变。下一同步重跑NequIP，其余两大模型资源正在校验续传；canonical官方默认和最终文档仍待实施。

- 2026-11-03T01:12:09+08:00: Canonical model names now route to original official providers and registered SHA-checked published weights; legacy variants are explicit and old checkpoints retain original numerics. Examples select all records and mini-batch32/float32; documented CLI retains flags with the official environment as Slurm default. Official-NequIP singleton preprocessing and ALIGNN reference batching corrected; six-model actual acceptance remains incomplete (3 passed, 3 follow-up).

- 2026-11-03T01:26:27+08:00: Official ALIGNN753 now passed full actual acceptance (4/6 complete). Canonical/default migration has complete71-test core and MACE regression evidence. Remaining NequIP strict force parity and Equiformer binary dependency; no claim of six-model completion.

- 2026-11-03T01:53:53+08:00: Finished all6 official live validations, same real10 structures, original trunk parameter changes and loss decreases.71-unit regression passed in core/MACE/new Equiformer environments. Actual documented official ALIGNN CLI chain760 passed. Archived55 bounded JSON/text/source-manifest files locally and independently audited; model/data/generated artifacts stay ignored. Final docs describe exact version/format and historical legacy-matrix boundaries.

- 2026-11-03T01:58:37+08:00: Completed final server sync7724686 and same-connection proxy cleanup, confirmed1080 release. All authorized runtime/original-model fine-tuning work and evidence complete under the previously stated scope; final local documentation records actual cleanup only. No dataset/weights/results added to Git.

- 2026-11-03T09:18:38+08:00: Added configs/mace_forcefield.yaml and docs/mace_forcefield.md, linked from usage/config docs; corrected obsolete full-batch/no-mini-batch statement in standards. Existing backend behavior unchanged. Explain official initialization vs UGNN resume, mandatory E/F/S training labels, stress conversion, and original MACECalculator direct prediction retaining its pretrained head.

- 2026-11-03T09:33:51+08:00: Added canonical task.supervised_outputs selection with old EFS default; data binding/scale/loss paths require only selected labels, report records supervision, full resume checks same set. Added original MACE force-only config and real-force acceptance harness, analytic gradient/selection and optimizer-resume tests. Original GNN modules and energy-derived force/stress computation unchanged.

- 2026-11-03 09:38:42 +08:00：完成最新代码/验收与ALIGNN2.0论文和官方仓库对照。明确已修全量/mini-batch/float32/官方原模型，剩余正式评测、跨任务官方证据、读出方法对照、生成/模拟质量及训练配方不足；仅更新任务记录，保留force-only进行状态。

- 2026-11-03 09:43:36 +08:00：按用户收窄范围完成标量/谱/力场/张量静态评估，聚焦可替换读出、信息保留、物理/网格/单位语义、任务能力声明与正式评测。未增加空间群/生成/模拟/联合多任务要求，未执行新实验或修改业务源码。

- 2026-11-03T09:47:14+08:00: Completed force-only support and live original MACE validation764,10 real geometries/force labels, strict checkpoint/trunk update/loss decrease/full resume/reloaded inference.762/763 each80 passed.37120B evidence archive SHA9ff65e7bf5d5144c5c51eddedf2a1ff7881fb3ff99fedcd6c12415b47139a782 and independent raw-label/geometry audit saved under ignored results/force-only-764. Parallel static-assessment notes preserved.

- 2026-11-03T09:50:23+08:00: Completed force-only source/evidence synchronization ef360c4 and verified own proxy shutdown/remote1080 release. New task supervision, source/gradient/label regression and official MACE real-force-only acceptance fully delivered; parallel assessment working-tree changes remain untouched.

- 2026-11-03 10:00:49 +08:00：新增docs/plan/prediction_decoupling_requirements.md并更新索引，细化adapter/readout/pooling与组件训练策略解耦。保留旧模型路径，显式新prediction配置，约束force-only冻结几何梯度与严格续训；附实施单元和验收矩阵。本轮仅文档，未提交Git或运行模型。

- 2026-11-03 10:06:03 +08:00：修订prediction_decoupling_requirements.md与索引，第一版收敛为统一模型输出协议+可替换readout。默认不插adapter，配置支持backbone.feature_dim声明且不改主干宽度，张量处理可在readout内复用并归其训练参数；同步配置/兼容/验收与路线。仅文档修改。

- 2026-11-03T10:58:00+08:00: Prediction A-D implementation ready for first server validation:explicit native FeatureSpec+runtime contract, registry/direct+response heads, independent optional processing, component optimizer/freezing/eval+state guard, strict full resume and explicit component warm-start, metadata/audits/CLI. Official graph/layers unchanged. Local selected checks passed; unit training/full regression and real CGCNN/MACE acceptance pending Slurm. Requirement source and prior assessment history preserved.

- 2026-11-03T11:27:36+08:00: First implementation ae90d7e complete with765/766114 passed each. Real767/768 failed at Python module discovery before model execution; corrected standalone file/sibling import, no provider/model changes. Added explicit basis-semantic warm-start preflight, complete effective runtime/report defaults and training-mode snapshot. Four canonical new-path YAMLs and usage/standard/README documentation now available; final real acceptance still pending.

- 2026-11-03T11:38:21+08:00: Real acceptance COMPLETE on0cc5a98:771 CGCNN5cases/772 MACE6cases; native parity retained, every real loss decreased, frozen body states exact, force-only full continuation/all-frozen input-derivative inference passed.769/770117 passed each. Local archive51files160856B independently hashed and raw/source real IDs/labels audited. Final review found selected custom-backbone warm-start also needs source signature check; narrow fix and local nonmutation unit passed. Final full regression and documentation/cleanup remain.

- 2026-11-03T11:53:10+08:00: Final source complete:773/774 each118 passed;11 actual official real cases already audited. Added per-ACC evidence summary, requirements/index implementation status, four configs, version/migration/freeze/warm-start standard and usage links. Only final docs synchronization and proxy cleanup remain; same work SSH8180 held at UNITS_READY, healthy owned proxy47020 unchanged.
