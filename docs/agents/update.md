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

- 2026-11-03T11:58:30+08:00: Closed prediction-decoupling task:allA-E/ACC01-13 implemented,final773/774118 each,771/77211 official real cases and local independent evidence audit. Final docs3019c8a synced and dedicated proxy closed with explicit remote1080-release confirmation. No remaining work or task resources.

- 2026-11-03T12:42:13+08:00: Clarified forcefield portability from current source:per-node invariant energy plus sum and geometry/mixed derivatives are generic; other official providers require derivative/batch-independence acceptance before enabling their current false capability flags. Existing118/118 and11real-case evidence unchanged. Read-only source consultation, no code changes.

- 2026-11-03T13:14:49+08:00: Started requested actual other-backbone forcefield tests; previous118x2/11case evidence preserved. Plan dedicated Slurm harness for all five original providers, frozen/full strategies and geometry/mixed-gradient/batch-mode diagnostics. No new packages or data needed; production capability flags stay unverified until actual evidence.

- 2026-11-03T13:28:07+08:00: 775 complete:MEGNet/NequIP both modes pass. ALIGNN FD h.002 fails but training succeeds;CGCNN reference-label slot fails pre-test;Equiformer OCP integer bounds reject live strain. Correct reference-only slot and implement original-graph/no_grad topology followed by unchanged live-distance Equiformer path. Preserve upstream bytes/rules. Found documented ALIGNN profile width assertion wrong256;actual source512 and corrected recipe. Next only affected model reruns plusFD convergence;no tolerance relaxation.

- 2026-11-03T13:33:39+08:00: 775 MEGNet/NQ both modes pass.780 CGCNN frozen passes,full BN mode fails numeric batch independence and loss decrease;explicit eval-while-trainable policy is necessary.782 fixed-probe h sweep confirms ALIGNN truncation error converges with smaller h,no tolerance change;documented512 first-layer checked.783/784122 each passed. Await final781 completion then rerun affected modes only;keep archived failed modes.

- 2026-11-03T13:41:38+08:00: 781 Equiformer frozen passed after original-topology/live-distance repair;full gradient/training passed but stochastic train-mode batch mismatch remains. Introduced explicit backbone_eval true for full CGCNN/Equiformer,keeping all backbone parameters trainable. Added monotonic capability-metadata compatibility to preserve old supervised checkpoints as provider verification improves;actual forward/state structure remains strict. Tests7passed/1Slurm-only pending.

- 2026-11-03T13:49:03+08:00: Five other official providers frozen/full candidate acceptance complete (10modes).CGCNN/EQ full require explicit backbone_eval preserving trainable params;ALIGNN h convergence fixed numerical check.Three env126 passed each. Promote only proven capability metadata;final ordinary production resume/inference and actual old-CGCNN metadata-upgrade replay remain.

- 2026-11-03T14:06:10+08:00: Five-other-backbone task scientifically complete:10candidate frozen/full modes and10ordinary production continuation/inference modes passed;MEGNet/NQ normaltrain,CGCNN/EQ explicit trainable-eval,ALIGNN convergedFDstep.0002. OldCGCNN numeric replay exact. Capability flags nowenabled;final docs+standards/mode constraints and158file evidence archived. Enter final documentation synchronization/proxy cleanup.

- 2026-11-03T14:13:08+08:00: Closed requested other-backbone forcefield task:allfive verifiedandcapabilitiesenabled,specialCGCNN/EQtrainable-eval policy documented,metadata-upgrade oldcheckpointnumericreplay0,three-env126regressions,plainproductioncontinuation/inference validated. Final server syncandproxycleanup observedcomplete.

- 2026-11-03T14:18:06+08:00: Clarified current scalar/classification reuse boundary from actual source:custom graph scalar specs and single-label C-logit cross-entropy already supported without backbone-specific adaptation;finite built-in property names mean new names require task.spec/catalog registration and label preprocessing. Current inference emits raw logits and reports training loss;integrated classification metrics/paper benchmark protocols and multilabel BCE are not implemented. No code/environment/remote operations.

- 2026-11-03T14:30:06+08:00: Started authorized head_mode native/reset feature. Distinct from train_readout or readout warmstart:will retain original task semantics/weights and preserve separate component policies. Metadata audit first,then contracts/native wrapper/component views/checkpoint integration and Slurm validation. Priorconsultation notes preserved.

- 2026-11-03T15:31:33+08:00: Implemented head_mode native/reset, strict original task contracts, original head invocation/normalizers, non-registering component ownership, independent freeze, and body-only cross-mode warm start. Reset descriptors/state layout unchanged. Preliminary local contract checks pass; production acceptance pending Slurm.

- 2026-11-03T17:05:17+08:00: Native mode unit and regression acceptance passed139x3. Added documented task matrix,output-unit packaging,strict head-mode resume/warm-start rules and ALIGNN/MACE-native examples. Prepared original-model Slurm acceptance harness;production artifact checks next.

- 2026-11-03T17:14:29+08:00: Completed six-official original-head parity and freeze acceptance and five real matching task training/resume. User-facing head-mode docs/configs implemented. Enter final cross-mode/inference/legacy-checkpoint integration,then evidence documentation and proxy cleanup.

- 2026-11-03T17:32:08+08:00: Native/reset feature complete:6official profiles,originalhead task/normalization contracts,freezeindependent,strict checkpoint/warmstart;139x3 tests and all6 original-model+transfer suites pass. Added native configs/userstandards/evidence. Final docs audit then same-session sync+proxycleanup pending.

- 2026-11-03T17:36:20+08:00: Task complete and synchronized4fc8796;proxy38788closed and1080release verified sameconnection. Native/reset code,standard,examples and fully audited evidence delivered. Closure records committed/pushed locally only;unrelateddocs/paper untouched.

- 2026-11-03T17:52:00+08:00: Consultation:current supported properties checked directly in local code. Distinguish11catalog entries,derivedE/F/S andworkflowoutputs,custom scalar/classification specs,andnativeoriginaltaskrestrictions. No code/config changes or new computation.

- 2026-11-03 18:12:27 +08:00：完成生成先例研究咨询，核对原论文s41467-025-60963-3、2504.16893/D5MH00774G、s41524-025-01901-1、2610.01898及作者simgen/chggen/DM2仓库。不将架构改造等同于直接复用官方力场checkpoint，也不把仅弛豫/筛选登记为生成网络。未修改业务代码。

- 2026-11-03T19:08:59+08:00: ustc-gpu connection attempted with interactivePTY;remote closesbeforeauthentication. Confirmedfailurestage with one-vvdiagnostic and askedusercampusVPN/jump prerequisites. No source/config/serverfile changes,no computation.

- 2026-11-03T19:13:48+08:00: ustc-gpuupdatedjumpconfigurationverified:successfulMFAloginhanhai22-01thenimmediatecleanexitafterbannerprohibitsCodexservices. No businesscommands,serverchangesorcredentialfilestorage. Reportresultandrestrictiontouser.

- 2026-11-03T19:17:43+08:00: Added ustc-gpu.md current access note per user-confirmed updated guide permission;linked at top of gpu.md and lessons.md,updated current state/plan. Historical banner and clean-exit records retained. Documentation checks pass;no remote actions.

- 2026-11-03T19:59:44+08:00: Created docs/plan/arxiv_v1_experiments.md fromstory:full-data16-cellfirststage then29-cellmatrix/seed,scalars/classes/tensors/spectrum/nonperiodicforces/plugin,optionalconditionalgeneration/Matbench. Current67.58GiB supports24-39GiBincrementbudgetwith20GiBreserve;flaggedmissingparentenvironment,train-onlyevaluationandpretraininglabeloverlap. No fulltraining/deletion/installstarted.

- 2026-11-03T20:04:07+08:00: Planningcomplete:writtenandindexed arxiv_v1_experiments.md;finalcapacity67.62GiB,first16fullcells then29/seed,24-40GiBnewpeak. Addedsourcecounts/full-definition/splits/metrics/native-vs-reset/freezeandlabeloverlaprequirements,optionalconditionalgeneration andcheckpointretention. Missingparentenvironment recordedinenv/lessons. No trainingorcleanupperformed.

## Guqq2 各用户磁盘排名：连接前权限阻塞

- 用户请求统计 Guqq2 上最大磁盘用户及其主要占用。已记录权限、Slurm 统计范围与检查计划。
- 默认 ssh -G Guqq2 显示 hostname guqq2、user codexsandboxoffline，未加载用户别名。显式 ssh -F C:/Users/asus/.ssh/config -G Guqq2 返回 Permission denied。
- 受控 require_escalated 读取配置被当前 Granular 策略直接拒绝，sandbox_approval=false；不是服务器认证或网络故障，不能绕过控制或复制密钥。
- 已查 docs/agents/lessons.md 既有 SSH 本地权限经验，停止重复同类尝试。Get-Process 仅确认既有 SSH PID 45976/47424/49080/57324 存在，没有停止任何进程或创建代理。
- 未建立服务器连接、未执行 git pull、未提交作业；无新用户排名结果。已有 2026-11-03 20:00 左右记录只显示 xmz home 17.532 GiB、系统盘剩余67.62 GiB，不能据此判断其他用户或最大占用项。
- 下一步须恢复当前执行环境对既有 SSH 配置/认证路径的访问，再继续已经授权的只读统计。原有其他规划/实验修改保持未提交，不覆盖或回滚。

## 2026-11-03 Guqq2 可读目录存储审计完成

- 用户调整权限后受控配置读取成功；普通连接均显式禁转发、先通过用户既有SOCKS端到端HTTP200，再检查仓库并git pull --ff-only。没有新建或关闭用户代理。
- 其他10个home均750，xmz不可读；sudo -n -l要求认证。用户随后明确选择“先统计当前可读目录”，此后不再尝试管理员访问。
- Slurm819（node42，1CPU，1GiB）20:11:27–20:11:29，COMPLETED/0:0：du同文件系统、不跟随符号链接、含隐藏目录，记录不可读项。
- Slurm820（同资源）20:14:23–20:14:33，COMPLETED/0:0：以lstat/scandir仅扫描可访问元数据，按st_blocks×512统计实际分配量，按设备+inode去重硬链接；按UID归属并聚合目录，不读取文件内容。错误354条，包含私有目录权限拒绝；作业成功不意味着全盘覆盖。
- 可见分配量105870802944字节（约98.60GiB），按UID：root76020502528（70.80GiB）、xmz22844665856（21.28GiB）、sgyang5404135424（5.03GiB）、zjl642748416（0.60GiB）、user416997376（0.39GiB）。这些是可见部分，不能判断全机最大用户；其他用户私有数据绝非0。
- 最大可见顶层目录opt约37.31GiB，其中abacus20.27GiB，intel11.98GiB。ABACUS主要三个版本：3.9.0.25_gnu约6.57GiB、3.9.0.17约6.00GiB、LTS约5.68GiB，含toolchain/build编译目录与约2.02GiB zip。Intel主要oneAPI编译器/MKL/VTune/DAL等。
- xmz家目录约17.53GiB，pip缓存11.184GiB、universal5.496GiB（runs5.054GiB）、venvs0.661GiB；其UID全可见归属21.28GiB还包括/tmp等位置。tmp可见4.407GiB，主要torch/CUDA依赖wheel和安装临时目录。
- sgyang可见5.03GiB中，/package内两个Intel oneAPI离线安装包合计约4.63GiB；私有home未扫描，不能视为其总量。
- 20:15:05容量复核：总1967317549056字节，已用1794723344384，可用72584384512（约67.60GiB），97%使用。可读扫描只覆盖df已用约5.90%；差额含未授权读取数据、文件系统元数据及可能已删除但打开文件等，未作归因或补差。
- 原始JSON和作业状态在results/user-storage-20261103/audit-819.json、detail-820.json、collection-820.txt（生成物忽略）。已核验按UID求和等于可见总分配量、单位换算及作业退出状态；最后squeue为空，本任务普通SSH均已退出，无任务自有代理需清理。
- 仅新增任务临时控制脚本和结果、追加管理记录；未修改服务器受管源码、删除数据、安装依赖、停止其他用户进程或提交Git。初次PowerShell传输末尾换行引起轻量for语法错误后改用Python传LF脚本，后续两扫描正常；既有SSH权限经验已查。

- 2026-11-03T20:17:06+08:00: Answered availability of four chosen official checkpoints using actualregisteredprofiles and prior acceptance;weights remainGuqq2 models/official,environmentrestorestillneeded. No code/config/serverchanges.

## 2026-11-03 Guqq 内存查询：目标 SSH 无响应

- 用户指定Guqq，配置核实为xmz@211.86.155.221，经vlab；此前Guqq2为114.214.215.42，二者不能混用结果。
- 已预先记录只读连接目的与仓库门禁。拟执行free/proc内存、PSI、短时vmstat、进程RSS及用户汇总，均为轻量诊断；没有模型计算或递归目录扫描。
- 首次连接仅取得Vlab欢迎，最后SSH返回255，Timeout server211.86.155.221 not responding；无远程脚本stdout。没有确认完成任务仓库存在检查或pull。
- 仅一次有界诊断重试：BatchMode=yes、ConnectTimeout15、keepalive10秒×2、总65秒上限。日志确认Vlab公钥认证成功，然后目标在banner exchange阶段超时，返回255；未进入目标认证或取得任何内存值。
- 不据连接超时断言内存耗尽，也不将Guqq2已有RAM/显存信息当作Guqq实测。可能的目标主机/网络/sshd原因尚未确定。
- 原始重试日志在results/guqq-memory-20261103/attempt2-ssh.txt，stdout文件无远程指标。未新建代理，未停止既有用户SSH；拟结束首个自有连接时身份检查不匹配，未执行Stop-Process，随后该连接自行返回。
- 两个任务连接均结束；不继续盲目重试。等待目标可连接后，再执行已授权的只读内存快照。不修改其他未提交文档或Guqq2资源结论。

- 2026-11-03T20:38:11+08:00: Updated arxiv_v1_experiments.md andindex to requested48cells/seed,mandatoryfour-modelgeneration,fullFTvsscratchsamearchitecture/heads andnewinitentryneeded. Addedper-taskbatch/RAMstartingranges,measuredparameter/staticmemoryestimates,separatebounded144runstoragebudget. Sharedforcebenchmark nowMLearnperiodic;optionalrMDonlyeligibleproviders. Resourceassessmentcomplete;no implementation/trainingstarted.

## 2026-11-03 Guqq 内存重试成功

- 用户再次要求重试后，Guqq211.86.155.221恢复公钥登录；不是此前Guqq2。初次恢复连接HOME/universal不存在且1080拒绝，未越过门禁查业务指标。
- 专用隐藏holder53440被Vlab关闭并确认本地消失；此前ss无监听和curl拒绝后，仅替换一个受控holder3052（UTC约12:39:28.966659）。后续端到端HTTP200，从已确认remote浅clone到HOME/universal，跳过LFS自动下载；clone成功后才读轻量系统指标。
- 实测时间2026-11-03T20:40:25+08:00，主机node221。RAM总270309412864字节=251.745GiB，可用247585054720=230.582GiB（91.59%），free显示已用16190951424=15.079GiB，空闲1.127GiB，buff/cache235.539GiB。低MemFree主要伴随大量缓存，不能解释为RAM耗尽。
- Swap总2147479552字节约2GiB，已用1836236800=1.710GiB；vmstat两个1秒间隔si/so均0，memory PSI some/full avg10/60/300均0。本次短时采样无明显内存压力，Swap占用本身不足以证明当前正在缺内存。
- 最大进程RSS：xmz python PID1840005，4944708KiB=4.716GiB；父python1840002约0.460GiB。按RSS简单汇总xmz5664696KiB=5.402GiB、user约3.808GiB、wgh约0.715GiB；共享页可重复计数，不当作唯一物理内存归属。
- RTX5090 GPU总32607MiB，已用13008MiB，空闲19113MiB；显存与RAM分开解释。
- 原始stdout/stderr保存results/guqq-memory-20261103/snapshot-final.txt及对应stderr；连接/代理失败诊断也保留。内存查询均为free/proc/vmstat/ps/nvidia元数据，未运行模型或目录扫描，无需Slurm。
- 收尾：控制器核对3052进程名/命令/启动UTC后仅停止自有代理。Windows文本管道的CLOSE末尾CRLF导致初次严格token不匹配（cleanup退出2），没有影响代理已成功停止的事实；随后独立仅ss诊断确认GUQQ_MEMORY_PROXY_1080_RELEASED且exit0，所有任务连接结束，原Guqq2用户代理未动。
- 无缓存清理、用户进程终止、服务器重启、模型运行或Git提交；其他任务已有未提交改动保留。

- 2026-11-03T20:44:20+08:00: Appended section11 actionable preparation/training/evidence checklist to arxiv_v1_experiments.md per explicit documentation request;preserved existing design. Includes48-cell matrix,fullscratch definition,shared datasets included in disk budget and three-seed reporting. Documentation checks pass;no code/git/remote changes.

- 2026-11-03T20:52:35+08:00: Corrected previousperiodic-only wording:CGCNN/ALIGNNnetworkweights can be retained withpropernonperiodicgraphinputadaptation;currentUGNNproviderrestrictionsareimplementationboundary. AddedCGneighbor/RBF/padding,ALIGNNlinegraph/angles,livegeometry/forceandregressiontests. FourmodelrMD17comparisonpossibleafterimplementation;MLearnremainscurrentperiodicbaseline. No sourcecodeorserverchanges.

- 2026-11-03 20:52:50 +08:00：核对Equiformer现行provider、ForceFieldModel、训练模式策略与forcefield-backbones验收记录，答复周期半径图/预计算拓扑/可微几何、新能量头求导以及eval模式保留参数梯度。使用最新能力开放证据，不沿用早期仅MACE可用的旧状态。仅只读咨询。

- 2026-11-03T21:02:44+08:00: Recorded agreednonofficialgraphdefault6Aradius forcrystals/molecules withPBCflags,fullradius(nohiddenKNNcap),livegeometry,andoriginalofficialfeaturecompatibility. Updatedstandards/arxivplan/dataREADME;currentdefaultknn/4A remainsuntilimplemented,explicitradius6alreadyworksstandardGNNs. OfficialpreprocessingandexplicitKNNexamplepreserved.

- 2026-11-03 21:03:56 +08:00：按用户要求在arxiv_v1_experiments.md末尾追加全量训练/推理前清理小规模测试配置的强制要求。区分structures/输入文件/推理limit与报告限量，覆盖设备、Slurm、训练预算、批次、精度/梯度、末尾评估采样、流式输出、checkpoint及初始化。明确单改all或epochs不足，配置覆盖和代码缺口分别验收；仅文档修改。

- 2026-11-03T21:15:55+08:00: Reported48-cellmatrixnotreadyforformalfulllaunch;hardwarebudgetfeasiblebutenvrestore,fullsourcepreparation/splits,scratchinit,molecular6Ainput,independentevaluation,propergenerationprotocol,andCUDAresourcequalificationremain. Existingofficialload/derivatives/mini-batch/native-reset testsremainhistoricalsmall-dataevidence. No serveractions.

- 2026-11-03T21:39:18+08:00: Clarified batch isnumberofstructures,notatoms;default32 applieswithouttask-specificautotuning,configs override. Currentforcefield.json andgeneration still32. Flagforce-mixedgrads,ALIGNNlinegraphanddensegeneratedcells asprioritymemorycases;responseauxderivativesdifferfromforce-through-backbone. No code/config/SSH changes.

- 2026-11-03T21:45:48+08:00: Recorded userapproved OOM precheck backoff inplan12.5 andlongjobgate:halvebatchuntilsuccessor1,cleanretryprocess,fullstep+worstcase,samplingseparate,recordfailures/finalconfig/peaks/effectivebatch;matchedinitcomparisonsusecommonsafeB. Documentationonly,notimplementedorclaimedtestedonGPU.

- 2026-11-03T22:13:59 +08:00: Arxiv execution preparation: add isolated CUDA batch-preflight controller/worker with typed-OOM halving and persisted failures/resolved success config; add immutable group split manifests and bounded regression/binary metric primitives. 12 local control/metadata/metric tests pass; GPU worker and training integration remain pending. Goal stays full48/seed,3seed144; no formal training submitted. Restore-owned-base install failed; remote diagnosis blocked by approval timeouts. Experimental plan now records implemented control vs unverified GPU/full-data stages.

- 2026-11-03T22:19:02 +08:00: Automatic approval timed out for git add and its one permitted retry before command creation. No commit or push completed; new modules remain local. Remote log-inspection retry also timed out. No task-owned proxy/SSH holder remains; existing user proxy was not changed. Goal remains active; pending user guidance/execution channel recovery for remote checks and publication.

- 2026-11-03T22:40:23 +08:00: Prepare commit for source-bound JSONL partitions in training/inference, validation-only true-best selection/optional early stop, train-only scales, optimizer-free best + strict resumed selection and crash recovery, streamed test metrics/predictions. Add Slurm full regression and actual-CUDA allocation OOM harness. 17 local protocol tests and static/doc/shell checks pass; model tests unexecuted. Approval read-only retry recovered; remote diagnosis confirms missing PySocks in base, bootstrap underway. Full48/144 remains active; no long training launched.

- 2026-11-03T22:48:04 +08:00: commit1b8c33e published and remote pull verified. Follow-up adds standalone test-metrics provenance and normative partition/paired-checkpoint standards. Local protocol/static/docs checks pass; model integration awaitsSlurm. Existing user proxy preserved, PySocks bootstrapped; Torch install process still live.

- 2026-11-03T22:48:45 +08:00: Correction to preceding live-install note: latest poll of session25239 returned terminal exit1, so installation is stopped, not a verified wait. PySocks1.7.1 import was verified before that failure; Torch success remains unproven. Next inspect logs before any install retry.

- 2026-11-03T22:54:23 +08:00: Owned dedicated proxy PID25840(exec73725) started only after local old holder absent/remote1080 free, verified end-to-end GitGET and pull. Previous pip failure traced to proxy disappearing mid NVRTC88MB download (2.5MB received); no Torch restore claimed. PySocks remains verified. Inspect cache/precise URLs before retry.

- 2026-11-03T23:02:01 +08:00: Add independent CPU Slurm17-protocol regression entry while scientific binaries download. Source-cache scratch audit found MACE extract-config copies learned references and NequIP public config is checkpoint-indirect; recorded required fresh-constructor checks instead of partial reset. Owned proxy is healthy for Git; active pip12487 shows NVRTC partial download/resume8.4MB, not completion.

- 2026-11-03T23:12:29 +08:00: Ownership guard stopped no processes: holderPID25840 was already gone before Stop-Process. Authoritative polls now show73725 terminal (server114.214.215.42 not responding) and install-controller12487 terminal1; CIM finds no local ssh processes. Remote pip state unproven until a new healthy/pulled connection checks it. Do not restart installation from lost observation alone.

- 2026-11-03T23:24:59 +08:00: Fix package eagerTorch import for dependency-free split/metadata validation while preserving public geometry names via lazy exports. Add true no-site-packages subprocess regression; retain all original protocol tests (18total). Slurm821 failure retained; current model/GPU environment restore31548 still live at last poll under ownedproxy96733. No duplicate installer launched; next actions publishedfix,pull/retest when health gate succeeds.

- 2026-11-03T23:32:58 +08:00: USER EXPLICITLY APPROVED offline Git synchronization: allow necessary scp bundle upload before pull, then git pull --ff-only from verified bundle; do not edit server tracked source/change origin. First resource bundle4994468:6241B SHA2566001ab6e16a6b08e40ca9b69e80b5a3c51a7d14eb529c32a9953dfa353f92887, prerequisite656f2ab, head4994468 already pushed. Connect via ClearAllForwardings; no remote internet/proxy needed. After successful offlinepull inspect failed821 logs/ownbase process+versions and submit corrected18-protocol Slurm.

- 2026-11-03T23:47:13 +08:00: User approved offlineGit bundle-before-pull;6241B SHA-verified bundle pulled server to4994468, full821trace confirmed eagerTorch failure, corrected18-protocol822submitted. Base audit PySocks only and no activeinstaller; oldprocess failed CuBLAS download with proxy gone. Add targeted16-wheel cache recovery (including legacycc4, preserves cache,20GiBreserve,Slurm12GiB) and4passing local tests; this may recover existingCUDAcache before anylarge transfer.

- 2026-11-04T00:18:07 +08:00: USER EXPLICITLY APPROVED HTTP resumable transfer for large fixed wheel resources after SCP failures. Local read-only loopback service52372/session6866 port54339, whitelist42public-resource paths, local Range/HEAD/404 tests passed. Before any servertransfer: offlinepull90cf140, check1080free and localSSHholders; create exactlyone dedicatedproxy, then end-to-end HEAD localresourcehealth before resourcecurl. No publiclisten/no trackedsourcewrites. All fullhash/assembly viaSlurm, no duplicatepip.

- 2026-11-04T00:40:27 +08:00: Add model-independent full-release streaming JARVIS preparer+Slurm entry for bandgap/classification shareddata/split and200channelphononDOS (optional300eDOS), auditedfilters/provenance/MP-reference+geometrygroups/noatomcap.5localtests pass. Physicalstatus:822passed18protocols;823passed4cachetests,recoveredSHA-matchingTorch1.039GB only;15CUDAwheels2.799GB+49common101MB downloaded/verified locally. UserapprovedprivateHTTP;824computehealth200.825/826immediate sh-pipefail failure retained, explicitBashfix quote-tested;827/828resubmitted downloadonly. Model/GPUscientificacceptance not yetrun.

- 2026-11-04T01:00:52 +08:00: Prepare commit:fullJARVIS streamingpreparer5tests;verifiedwheelarchive restore4tests;offlinefoundation+exactCUDAinstallSlurm templates (pipcheck then additiveownedpth;provider/modelchecksremain). Alllocalmatchingchecks pass. ActualprivateHTTP transmitted~40MB beforeVlabclosed; keepallpartialchunks and resumeonlyterminaljobs afternewownedproxyhealthproof. Neitherdatasets norenvreadyclaims made.

- 2026-11-04T01:43:44 +08:00: Completed full GMTNet dielectric preparation implementation with shared immutable writer/grouping/audit and6 local plain-data tests; original5 JARVIS tests unchangedpass. NumPy and full release acceptance remain Slurm gates. Actual832 commonbase installation succeeded; resumed only CUDA resources with approved HTTP and canceled exact833/834 stuckdependencies. Preparing publish/offline sync for Slurm GMT fixture/full-data work.

- 2026-11-04T02:52:50 +08:00: Completed sourceb6e83d5/Slurm84712tests, actualfullGMT5000->4999(split3998/502/499,max88) andfullJARVIS75993->75993(split60823/7590/7580,max140); smallaudit/codeSHA evidence copiedandverified. Slurm853 continuesDOSfrompartials. Locallydownloaded15MLearn/PerovfixedGitblobs41,310,943B and59+2providerwheels151,474,154B; noneofthese installed/preprocessedlocally. Formal48/144trainingNOTstarted.

- 2026-11-04T03:08:14 +08:00: Preparepublish fullMLearnE/F standardJSONL preprocessor withauthor-test retention, per-elementtrainingfamilyvalidation, exact-cross-releasegeometry refusal, fullsource/blobSHA checks/noatomcap,7fixtures. Preserve prioractualGMT4999/JARVIS75993 audits. Addcontrolledgroup/split hooks withoutchangingexistingreleaseoutputs; existingpreparertests remainpass.

- 2026-11-04T03:31:12 +08:00: 4595354publishedandverifiedofflinepull; fullMLearnstandardizer/author-test+groupedvalidation implementedand19Slurmfixturespassed. Data855queuedseriallyafter853; originalfullGMT4999andgap75993evidencepreserved. RecoveredstandaloneofficialNequIPpretrainarchitecture YAML, enablingexactconstructorworknext withoutguessing orrecursivepartialreset. Networkdirectexceptionrequestedwithconcretesyntaxcheckeddraft, notexecuted.

- 2026-11-04T04:15:53+08:00 Perov-5准备器：固定三CSV逐文件验证，沿用作者三划分，ASE读取完整5原子晶胞，丢弃性质列，不做primitive/标签筛选，ID重复或跨分区精确几何显式拒绝。6项纯数据测试通过，实际ASE与全量待Slurm。回传并验收声子14244和MLearn1566的完整审计；尚无正式训练。CGCNN/ALIGNN初始化原型留在本地未发布，不能称所有官方scratch已支持。

- 2026-11-04T04:25:38+08:00：Perov-5全量阶段完成：668b59a已发布/离线pull，Slurm858测试与859转换均成功；主体六任务数据全部准备并独立审计，正式48/144训练尚未开始。CUDA857继续，额外provider未安装，CGCNN/ALIGNN初始化原型未发布。完成数据HTTP精确清理，wheel HTTP和唯一自有代理继续工作。

- 2026-11-04T04:34:35+08:00：新增engine/generative独立协议模块和Slurm训练先验准备入口：逐epoch/稳定ID噪声、严格旧目标续训边界、仅训练晶胞的对数体积/原子先验、固定无放回条件及经验W1。纯std9测试通过；下一步发布/离线pull后CPU Slurm实算全Perov-5训练先验，再接生成训练与独立质量评测。

- 2026-11-04T05:03:13+08:00：完成生成纯协议4859cc9发布/离线同步及Slurm860全训练先验。新鲜逐epoch噪声、val-best完整test去噪、擦除真值模板的独立质量评测（1000=200条件×5draw、有效性/唯一性/分组成新颖性/匹配/W1）已本地实现并准备8项数值测试，但尚未发布/运行。Vlab代理启动/状态观察两类故障已分辨并修复本地监督器，精确确认两批自有旧进程退出/端口释放；新64242/PID49220真实HTTP健康后交862接续321230147B native partial，保持唯一自有代理与wheel服务，未运行direct例外DRAFT。

- 2026-11-04T06:06:12+08:00：原始MACE/NequIP蓝图参数策略与标准记录结构评分拆成无Torch依赖模块；7项纯配置/导入测试通过，评分真实物理案例待Slurm。MACE/NQ实际构造器与生成/preflight集成已在本地扩展，仍未发布/数值验收；native邻居统计的自动准备/绑定还待接。863缓存恢复47.4MB，下一步仅补传已本地存在的24.2MB通用依赖，先完成无需Torch的结构评分验收。新CPU Torch本机下载待自动审批要求的明确许可，CUDA862由64242继续。

- 2026-11-04T06:36:39+08:00：Slurm864实际complete：已存在资源包24,209,507B经私有HTTP续传，全部59轮校验/离线安装完成，pipcheck=0；真实ASE/Pymatgen结构评分6/6、纯蓝图7/7通过。四份收据已SCP回传，核对59项实际版本、13个测试与c095dd6源码提交；Torch/CUDA/DGL仍未就绪，正式训练0/144。

- 2026-11-04T06:37:52+08:00：新增native原包图计数聚合策略与3项纯std验收，区分MACE/NequIP零度节点分母、要求完整train计数与身份收据；更新全量计划为六类数据已备齐、正式0/144及仍待数值门禁。自动建图扫描/入口绑定仍未完成；没有把计数fixture当作真实scratch训练验证。

- 2026-11-04T06:51:20+08:00：本地新增engine/initialization模块与独立Slurm校准入口原型：逐结构调用原生native_input、绑定完整训练分区和实际dtype指纹、artifact/图源码/依赖版本，缓存失配拒绝；纯策略3项通过，6项原包图验收待环境。尚未自动接入训练/容量worker，也未发布；c8128af计数策略和864环境记录已发布并经离线pull，865继续恢复CUDA。

- 2026-11-04T06:51:50+08:00：Slurm866实际通过计数聚合全部3项，收据/测试日志已回传并核对c8128af；Linux/Python3.10兼容验收完成。865实际RUNNING，磁盘可用64,806,625,280B，约60.36GiB，高于20GiB预留；这是快照而非独占配额。仍无正式训练，原图扫描6测试未运行。

- 2026-11-04T09:07:22+08:00：独立环境恢复流水线补齐：发现official缺失依赖后上传1.55MB既有资源，868已校验暂存；新增有SHA/共享Torch/e3nn隔离门禁的离线安装脚本与3纯std测试。四模型静态词表覆盖主体全部元素，无需删样本。原native初始化自动接训练/预检已在本地实现并通过12控制+3身份测试，原图/模型/生成数值仍待环境；运行时继续保留未发布。旧55564已实际terminal，诊断后新55164/exec15798接867续传，无重复active作业。

- 2026-11-04T09:19:00+08:00：Slurm869实际通过离线installer全部3项纯std测试；收据/日志已回传，按ed2a646的Git blob核对脚本SHA 6e91bb1f328ed84eb8fad4d69dadffcb61707d24329d36f7d42c3bf6f876bd8a。这验证Linux/Python3.10门禁兼容，不代表实际pip安装或模型/CUDA验收。NequIP作者YAML已在服务器模型缓存通过11565B/SHA轻量核验，未改源码。

- 2026-11-04T10:17:11+08:00：新增完整144组正式配置定义与CPU Slurm准备入口；五份完整数据/源顺序ID/固定划分及四模型原资源强校验。训练和推理加载分区时可强制source与canonical manifest SHA，覆盖新数据路径时清理旧身份；默认不带校验的配置保持兼容。基线预算、初始batch与运行前门禁均明确为待实测，生成配置不提交训练。15项纯std测试通过；真实完整输入生成待发布后Slurm，Torch/API/原包/GPU仍待恢复，正式0/144。

- 2026-11-04T10:32:01+08:00：be3d579已推送并通过校验离线bundle在服务器pull；Slurm872实际完成完整144配置准备与15项纯std验收，收据/源码Git blob/每配置摘要核验完成。873仅检查已有CPU缓存，目标不在；本机旧Torch2.6CPU资源与官方HTML索引SHA已一致，但没有上传/安装或以它替代正式Torch2.7cu128。孤立远端3420794按UID/精确启动/唯一性/健康失败证据仅TERM该PID，端口释放后恢复唯一HTTP续传监督器，未修改远端源码。正式训练仍0/144。

- 2026-11-04T10:46:17+08:00：新增benchmarks/pairing完整成对容量编排：从冻结144矩阵选择pair并核对摘要，任务设置一致，独立预检后共同batch双侧重验，复验再次OOM继续共同下调；失败保留所有尝试，成功才导出两份最终配置及摘要，不变更原矩阵/图/精度/数据/采样步数，不保留预检权重。10项纯std检查及已发布源码隔离检查通过，计划发布后CPU Slurm复跑；这不是实际显存或正式训练结果。

- 2026-11-04T11:01:44+08:00：a7b127c已发布/服务器pull；875实际10项成对预检控制验收全部通过，收据按真实Git blob核验。补齐本地运维监督器预先绑定远端唯一新增sshd身份：只在自己Popen终止、已绑定身份/主机/UID未变、端到端失败时，用pidfd释放该精确遗留连接；元数据失败保留健康代理，歧义不清理，零字节进展仍停止。旧3426030已严格核验后精确释放；新版76272/40620健康且已实际绑定远端身份，876 RUNNING。没有下载新CPU二进制或安装环境，正式训练仍0/144。

- 2026-11-04T11:19:18+08:00：修复容量预检漏测声明worst的调度：热身后每个worst单独填满候选batch，测量次数取请求与worst数的较大值，再轮转普通样本；worker记录requested/actual/completed_worst，未全部完成不能成功。发布范围调整为纯scheduler及从已发布HEAD提取的worker调度小改动，因其不改变NN/导数运算且6项纯调度检查可独立覆盖；未发布工作树中原有native校准/生成协议运行时，真实GPU仍作为正式门禁。后续完整原图扫描必须证明极值选择来源，调度覆盖不能代替扫描。

- 2026-11-04T11:34:02+08:00：8fdea11已发布/服务器pull，调度修复经Slurm878六项纯检查和三源Git blob核验。补充完整扫描模块计划：selection.py/native_scan.py尚未实现；需同时统计native与EquivariantAdapter额外radius graph，CGCNN分清padding槽位，ALIGNN统计line graph，并另外实测生成噪声/采样轨迹。几何适配可从scalar native特征构造响应通道，因此不能只看native irreps断言张量不可适配。正式训练0/144，完整扫描与数值预检仍是下一阶段。

- 2026-11-04T12:31:02+08:00：新增download_offline_cuda_resources.py，同一curl最多8个1MiB Range、20s连接/30s操作预算、-C续原partial/--next复用/--fail-early遇错止后片；校验CR/收到字节与append位置，协议错只回滚新追加、网络部分保留，最终SHA前不发布。保留固定16 catalog、20GiB、未知/SOCKS拒绝失败和POSIX单writer锁，计算节点先单独验证proxy；仅暂存不安装。Windows9项包括真实curl通过；880三组12193792B接收前缀全部匹配固定源，证实可行但非严格超时因果实验。下一步CPU Slurm9项后才替换877，健康SSH不重启。

- 2026-11-04T12:51:17+08:00：完整训练图计数流的probe选择器已实现：强制逐条源顺序身份，保留五维极值与确定性普通候选，区分CGCNN padded slots，聚合本身不签发真实图扫描证明。调度保证所有worst满batch后至少一个普通batch。本地12项通过，待CPU Slurm；实际native_scan仍未实现。资源新工具881九项真实通过，新882保留旧断点恢复；正式0/144。

- 2026-11-04T12:56:51+08:00：dd0fcb0的完整计数流probe选择/普通batch改进完成Linux控制验收：883/884共12项及执行源码核验通过。完整图构造仍未实施，不把计数聚合当扫描。882断点至少推进到72.7MB；本地SSH超时/连接重置和curl7说明本次停顿与代理链路相符，未见续传协议/SHA失败。继续环境恢复及原包数值，正式0/144。

- 2026-11-04T14:51:38+08:00：新增Slurm-only完整原图扫描和CLI、独立CUDA格式/guard检查入口；原生图与启用readout图均计数，严格完整train身份及源/划分/checkout稳定性，失败不发布probe，声明clean geometry而非全噪声轨迹。七项控制本地及隔离已发布源码均通过，数值/真实原包图仍待依赖。73597监督器实际live，882已离队，885在队列空确认后继续原断点，未重开健康代理；正式0/144。

- 2026-11-04T14:56:17+08:00：6072d4c完整原图扫描工具已发布/服务器pull，886七项纯控制验收及五Git blob核验完成，arxiv计划12.5更新实现/实测边界。五项CUDA格式/guard与真实四骨干全图、scratch/生成/导数仍未验收，不把扫描工具存在当全图成功；885继续下载，正式0/144。

- 2026-11-04T15:09:33+08:00：修复NequIP原始scratch的参数准备：作者[128,64]是按角动量而非按层；从实际checkpoint元数据确认布局，显式转为官方FullNequIPGNNModel所需irreps和每层radial参数，保留独立32维type embed及原ZBL/物理设置。五项新/七项旧控制本地和隔离源码通过，runtime仍待Slurm，不冒充已完成数值。

- 2026-11-04T15:21:30+08:00：4c4616c的NequIP Full参数展开已完成887实际五项控制及三Git blob核验；从原包模块提取布局的runtime prototype保留严格state/irreps检查，尚未发布/数值验收。885恢复窗口仍RUNNING，旧监督器/代理实际终止并释放后，经新诊断仅受控恢复68162/29980，健康绑定3521912，不修改图/版本/精度/实验矩阵。正式0/144。

- 2026-11-04T16:00:46+08:00：用户暂停实验并要求试服务器直接下载后，889实际官方HTTPS四MiB验证通过，890从原断点直连剩余依赖，首次已增长25.6MB。Torch根wheel1.039GB已存在且SHA校验后跳过；原耗时主要CUDA依赖和本机/SSH中转。已关闭旧任务HTTP服务，未开启新代理、安装或训练。正式0/144，实验目标维持paused。

- 2026-11-04T16:50:12+08:00：用户继续目标后已实际提交891 DGL、892 base(after890)、893 extras(after892+891)、894 GPU最小图/训练求导/checkpoint及六输出/OOM诊断(after893)，未执行任何登录节点数值。新增真实pilot准备器：五源64/16/16、48原模型/两初始化配置、3epoch/batch2，保留原144定义，七项控制本地及隔离通过，待Slurm实际生成；original scratch等数值仍待，正式0/144。

- 2026-11-04T17:38:10+08:00: Repair official dependency installer after actual893 conflict: preserve documented official MACE/e3nn0.4.4 parent, universal NequIP0.5.8 and shared Torch2.7.1cu128; remove only known own0.5.8 overlay, six pinned offline wheels, five control tests passed. Actual892 installed CUDA/base successfully. Real pilot preparation895 was collected: seven tests,48 configs/24 pairs, full-parent source verification, prepared_not_launched; zero pilot/formal training.

- 2026-11-04T17:48:05+08:00：本批依赖安装完成并通过GPU基础验收：共享Torch2.7.1+cu128/CUDA12.8，三个环境pip check正常，官方包及DGL/PyG扩展在RTX5090可执行；修复official e3nn覆盖冲突并保留各模型原版本。实际作业896/897/898/899通过，18回归零skip、五项图检查、六任务合成训练及OOM策略全部通过，完整收据已回传。准备好的48真实pilot配置尚未训练，正式0/144；本次按用户要求交付安装完成状态。

- 2026-11-04T18:15:12+08:00?????????????????????????scratch???/????????????state?/???MACE??????/???NequIP?????angular layout???Full builder???native/scratch???????????warm-start???????calibration CLI????????21??std??????????????????Slurm???????????/???????

- 2026-11-04T18:32:21+08:00????????900???16??????CGCNN?BN???????raw-key?????901/903??????/???????fresh???MACE??bool???NequIP global_state???904??????CGCNN?counter/MACE?bool???????shape??????strict??CGCNN????canonical?MACE?????flag???NequIP??????????RNG/dtype???????????????????????

- 2026-11-04T18:48:24+08:00????????CGCNN/ALIGNN??905???/??/BN/???17???MACE??906?????/??/????/RNG?????907???NequIP?????shift??????908/909?????device=cuda?????????????????20??std?????pilot????????????144?????

- 2026-11-04T19:22:37+08:00：首批真实实验完成：四原模型带隙微调与整骨干scratch共8次，Slurm912/913/916/915，64/16/16、三epoch、共同batch2；原包对照、完整诊断训练图、成对100batch容量、validation-best/精确测试ID和重载全部通过。原构造器910/911验收也通过，修复旧BN/结构bool/逐元素shift、NequIP全局状态及通用CUDA设备索引。完整结果和限定口径记录arxiv-pilots.md；正式仍0/144，下一步分类/声子谱及导数/生成运行时，不缩减范围。

- 2026-11-04T21:55:37+08:00：完成分类/声子谱全部16版真实pilot回传核验，累计24/48。发布新噪声生成、val-best/全test去噪、擦除参考几何的独立质量评测及训练/生成/预检自动原生统计；保持只用训练集拟合和显式sampling/初始化的严格续训。32项纯控制/隔离候选通过，40项真实数值回归待Slurm；原模型生成/力场/介电与全量144仍未完成。

- 2026-11-04T22:18:35+08:00：新增分类balanced accuracy（两类召回均值，缺类null）及只读原混淆计数的Slurm补充报告入口；不改预测、原报告或权重。修正生成数值套件收据以完整40个唯一主测试分组与零错误/零跳过验收，保留pytest的实际56含子测试汇总。5项SQLite测试及隔离候选、真实JUnit与5损坏变体/guard/AST/bash检查通过。925原作业收据失败保留；发布后重新完整数值回归并为已有8版分类补算。当前24/48诊断，正式0/144。

- 2026-11-04T22:30:53+08:00：完成生成927数值验收与分类928八版指标补充的独立证据校验。新增可复用物理任务验收器：实际配置/原骨干能力、混合梯度、独立中心差分、平移旋转、固定坐标/等变保证区分及分批一致性；新增E/atom测试指标与natoms记录，不改变原训练目标。提交前静态/guard/文档检查通过，14项数值回归及四原模型物理任务仍待Slurm。保持24/48诊断、正式0/144。
- 2026-11-04：物理CLI复审修正原生校准适用条件，保留不适用模型与pretrained路径；静态检查通过，随物理单元共同同步，不把未运行的真实数值门禁当完成。

- 2026-11-04T22:54:18+08:00：修复全矩阵FF定义和实际运行协议的脱节：total_energy输出/损失绑定源energy标签，定义revision2，旧872/895和934–937失败证据保持不可变。新增跨模块真实监督协议检查；14项控制在隔离候选通过，144配置精确对照证明其余120不变、24只三处语义等价命名纠正。远程cf58来源锁定不变，等既有管线及942重载诊断结束后再发布同步并重建完整定义；尚无新FF训练结果。

- 2026-11-04T23:08:04+08:00：从真实失败定位GPU归约可重复性问题，942–944在原精度/容差下证明状态逐项完全相同且确定性比较全部64记录差异0。新增精确state检查与仅重载验收期间启用/异常恢复确定性策略，保持训练更新与原容差；训练入口配置默认cuBLAS确定性workspace。静态/脚本/文档检查通过，25+40项Slurm数值待运行。FF定义revision2修复一并等待发布重建；原930–941已终态，其中新增11版管线完成待回传，正式0/144。

- 2026-11-05T00:06:38+08:00：推进35个独立核验诊断格及947完整144 revision2定义。新950/951力场、952介电、953生成管线通过，仍待独立回传；CGCNN/ALIGNN力场在固定h应力FD止步，955实证原大h跨邻居拓扑。新增统一相邻步长收敛准则，保持误差标准；修复旧float64零张量参考。954 MACE采样NaN节点因ValueError误分类，改为严格数值FloatingPointError，形状/OOM仍致命并新增端到端覆盖。静态与4控制通过，19+43数值待Slurm；正式0/144，完整范围未缩减。
- 2026-11-05 01:34 +08:00：读取962/963/964实际收据，MACE全部1309训练图及两模式物理/容量验收通过，NequIP最坏力FD失败；CGCNN同参数float64通过、float32量化失败。新增相同参数能量参考精度提升，保留实际float32训练和解析导数、原容差与步长收敛，并补大能量偏置/错力拒绝/状态保持测试。4控制本地与隔离各通过、AST/bash/文档通过；22主数值待Slurm。记录固定Git源码缓存规则，为MACE两版完整300epoch/原早停正式请求准备启动，不计未完成训练，144及扩展范围不变。
- 2026-11-05 01:57 +08:00：全量正式首批已提交：MACE968微调正在训练完整1309/93/164、300epoch/patience30/B4，969完整scratch排队；0/144完成、2/144提交。独立核验47小规模任务格/64生成样本与96522主GPU回归；CGCNN最后scratch973排队。修复NequIP参考副本的固定embedding输出dtype，仅限validation且保持原骨干及统计源hash，974两模式真实最坏输入CPU直接证明策略。新增两项边界测试、24主Slurm回归；纯控制/隔离/AST/bash/文档检查通过，24数值待Slurm。保留966/967启动断言失败及970类型失败，精确取消尚未运行的已知无效972，不中断968。
- 2026-11-05 02:06 +08:00：在正式MACE968持续运行期间补齐计划标量训练均值基线模块。两遍流式核验完整原始数据/清单SHA和全部有序ID，train-only均值，完整val/test原单位MAE/RMSE和预测JSONL，拒绝截取/非法标签/覆盖输出；独立Slurm CLI及说明。6控制本地与隔离各通过，AST/bash/门禁/文档通过，待发布后完整JARVIS CPU执行。正式仍2提交/0完成、47诊断/64生成样本；不把基线或CPU兼容检查计入144。
- 2026-11-05 02:20 +08:00：完成并独立核验981全量标量均值基线与6主/8子控制，全部75,993源/15,170留出预测及六源Git SHA绑定，测试MAE0.9069491665/RMSE1.3388291889eV，供24个带隙配置共享。更新计划当前执行状态、完整证据与已完成准备项，保留早期历史并澄清旧定义/重载故障已修复。正式MACE968最近69epoch仍运行；2/144提交、0完成，47诊断/64样本保持，其他GPU门禁依次排队。
- 2026-11-05 02:40 +08:00：为其他三模型正式力场启动修复外层容量证据的固定计数假设。新增pairing/evidence按真实控制器报告链验证typed-OOM/减半/全部测量与最坏覆盖/最终共同batch，接受合法额外尝试但拒绝未知错误及篡改。6控制本地/隔离各通过，原962/963实际容量记录直接验证通过；不改变模型、图、精度或科学容差。待发布后替换尚未运行979/980并安排六个门禁依赖正式作业，968继续原训练；全144目标保持。
- 2026-11-05 03:02 +08:00：982 CPU控制在pytest收集时因tests包导入失败，正式提交器在报告门禁前停止，核实未产生claim或调度改动。修复共享fixture为__file__相邻路径runpy加载，隔离候选模拟tests命名空间被占用仍完整通过6主/8子。保留982原失败，发布后以新Slurm控制复验才继续替换预检/六个正式提交；不改容量标准或原模型。
- 2026-11-05 03:20 +08:00：修复容量证据固定四文件假设并完成983六主/八子Linux控制及实际收据验证；测试fixture导入和启动器owner检查错误均在动作前门禁止步，保留失败记录后修复。984/985完整预检替代待运行979/980，CGCNN986/987、ALIGNN988/989、NequIP990/991正式两模式已成功条件提交。每case按947完整数据/预算执行，实际门禁通过才启动，严格源/版本兼容，原MACE968继续至最近158epoch。累计8/144提交、0完成，47诊断/64生成样本；全矩阵及扩展保持原目标。

- 2026-11-05T03:54:14+08:00：安装收据核对通过：897完成、三个环境版本及899单独/汇总报告一致、RTX5090 CUDA12.8验收通过、898 JUnit18项零失败/错误/跳过；未执行重复安装。

- 2026-11-05T04:08:23+08:00：完成首个正式全量结果968的独立证据验收（1/144），MACE test能量MAE13.288meV/atom/力MAE30.803meV/angstrom，174epoch提前停止/best144；969仍运行。973使诊断48/48。994修复CGCNN原包读取对照且误差0，995完整准备和996/997正式请求保留历史替换旧PENDING986/987；未改科学定义或环境。993独立重评/训练后物理通过，1566源推理运行。四骨干完整声子谱准备998–1001已排在力场后；原144及扩展不缩减。

- 2026-11-05T04:16:22+08:00：首个全量模型完整源推理证据闭合：993完成164标签独立重评、best物理检查和1566源流式推理；1002逐条独立核对全部有序ID/形状/有限性/SHA及完成标记通过。所有报告和来源哈希归档results/paper-completed-20261105/；训练完成数仍1/144，GPU969及后续谱998–1001等请求继续保留。

- 2026-11-05T04:30:53+08:00：实现benchmarks/assessment独立张量后评测及Slurm CLI：校验完整源/划分/全部test ID和原dtype标签，保留原overall指标，增加整张量范数零/非零和逐分量标签零/非零两组绝对误差及各分量MAE/RMSE；不加对称约束、不改训练/模型/既有指标。7主stdlib控制通过，下一步固定提交CPU Slurm复核八版真实诊断及4999全源。正式仍1/144，969运行，当前GPU请求不变。

- 2026-11-05T04:42:24+08:00：张量分组评测376b00a已在CPU Slurm1003完成真实验收：整张量和分量两个分组、各轴绝对误差、精确dtype原标签/源/ID及原overall保持；完整4999标签分布已核验，所有整张量非零但test2611零分量，证明需分量分组。四完整介电预检1004–1007已排在声子谱后。正式仍1/144，8唯一case；969继续运行，其他模型/任务与三seed及原扩展保留。

- 2026-11-05T04:57:41+08:00：新增独立预训练ID审计模块与Slurm入口，6主控制通过；固定ALIGNN包中已发现可审计44569/5572/5572发布ID，将在完整冻结JARVIS带隙/分类、介电、谱源上比较，保留所有数据与947定义。四权重来源及其他交集unknown单列docs/agents/pretraining-overlap.md；不把未列出ID当几何未见，不把reset当消除预训练曝光。

- 2026-11-05T05:13:02+08:00：预训练审计1008在已通过6主17子后因发布ID非互斥停止；1009确认原train/test共享两个ID，未改权重、数据、划分或训练。新增显式歧义报告模式并保留默认strict拒绝；报告多角色、完整成员关系及保守训练曝光，7主控制通过，下一步新固定源码全源审计。

- 2026-11-05T05:26:18+08:00：完成预训练来源/ID曝光审计：1010全源通过，保留原train/test两ID冲突；本次带隙/class test7580中4405原训练+586原验证曝光，因此明确仅作迁移适配，介电/谱为跨目标且披露材料曝光，其他模型交集unknown。7主17子控制、源/ID/分区和独立集合复查通过。新增四骨干带隙1011–1014和分类1015–1018完整预检，原60823/7590/7580和947定义不变，正式仍1/144，继续所有当前GPU请求。

- 2026-11-05T05:42:43+08:00: Installation follow-up verified: Slurm897 complete; all three environments Torch2.7.1+cu128/CUDA12.8 and provider-specific e3nn agree with899 aggregate/individual RTX5090 passed receipts;898 JSON and JUnit18 tests agree with zero failures/errors/skips. Dependencies already installed and GPU-accepted; no reinstall, environment changes, new jobs or local neural computation.

- 2026-11-05T05:50:39+08:00: Added public full-generation pair preparation module and CLI/Slurm entry with module documentation. It preserves complete11356 train-only prior/native topology, separately pairs trainingB16 and samplingB4, retains full100x2 sampling and1000/5 formal quality budget, and exports separate configurations. Eight pure control tests pass; new actual server acceptance and four full GPU preparations are next.

- 2026-11-05T05:57:04+08:00: Generation preparation is now public and server-accepted (47a208f;1019). Submitted1020/1021/1022/1023 for CGCNN/ALIGNN/MACE/NequIP after prior queue and control success. Formal count remains1 completed/8 submitted of144, no extra formal trainings or changed science. Latest969 confirmed live2:26:20; exact queue/acceptance retained in ignored results.

- 2026-11-05T06:10:01+08:00: Queued scratch-only CPU post-evaluation1024 afterok969 and complete inference validator1025 afterok1024. Added public supplementary native baseline entry for4 matching original heads on full7580/164 frozen test partitions, no training or target statistics/reference fit; eight pure controls passed. Actual native numerical/full test runs next; original144 scope and GPU queue unchanged.

- 2026-11-05T09:06:45+08:00: MACE full pretrained/scratch pair now independently accepted (968/969): E/atom MAE0.0132882/0.0224615, forceMAE0.0308030/0.0349536, seed123 only. Full scratch inference and source metric re-score verified1024/1025. Added and completed four full original-head native zero-shot baselines and four independent full-source assessments (1026-1034); public implementation7a4b4a3.988 ALIGNN FT completed115 epochs, metadata accepted and1035/1036 post-evaluation running;989 continues. Accepted formal count2/144, submitted8/144; original scope unchanged.

- 2026-11-05T09:31:37+08:00: Added source-bound public predictive formal gate and training entry with execution module README and CLI/Slurm wrapper. It checks complete original source/split/artifacts, every graph-size row/extrema, full paired capacity SHA chains, scratch normalization and dependency/source compatibility, CUDA derivative evidence and measured budget. The runner preserves frozen recipes, logs complete epochs/heldout/configs/resources and rejects duplicate cases; generation orchestration remains separate and original six-task144 goal unchanged. Existing engine/model code and running jobs untouched.

- 2026-11-05T09:53:22+08:00: Public formal predictive entry00b2dc3 completed server151-JUnit control,6 actual full preparation gate checks and3 actual completed result compatibility checks (1037/1038). Source/model/engine and running jobs unchanged; no new formal tasks submitted by acceptance. ALIGNN988 full result independently accepted through1035/1036, formal completed3/144 of8 submitted.989 last confirmed70 epochs. Plan and public execution README now include measured results/limits and commands.

- 2026-11-05T10:39:49+08:00: Installation handoff verified from collected897/898/899 receipts: Torch2.7.1+cu128/CUDA12.8, three compatible environments, actual RTX5090 provider and DGL/PyG CUDA checks passed;18 regressions zero failures/errors/skips,898/899 completed0:0. Installation already complete; no reinstallation, new SSH, proxy, package changes or Slurm submission required. Notify user; broader experiment plan and unrelated work preserved.

- 2026-11-05T10:51:57+08:00: Added separate full-generation training/quality execution, source-bound prior and paired train/sample gates, public CLI/Slurm wrapper, immutable best/last preservation and per-job quality attempts with atomic concurrency claim.27 pure controls and actual144 recipe checks passed. Queued independent ALIGNN scratch CPU stages1040/1041 afterok989;1039 full species report consistent across115730 records and20 provider/source comparisons. Existing engine/model/environment/data and running jobs untouched; formal accepted remains3/144. Next publish and execute CPU acceptance against real preparation and diagnostic report formats.

- 2026-11-05T11:05:58+08:00: Generation execution57a907b accepted by CPU1043:27 main/248 JUnit zero failures/errors/skips,6 genuine full predictive preparation gates,4 real current generation report formats accepted and4 source-proven legacy reports rejected for absent exact reload evidence. All8 diagnostic quality8-attempt reports reject formal1000 protocol.14 executed sources verified against Git blobs.1042 failed overbroad legacy expectation retained, strict code unchanged.989 last confirmed RUNNING154 epochs/2:31:10;1040/1041 pending afterok989. Formal accepted3/144, submitted8/144; full generation numerical gates/training/quality, remaining seeds/tasks and original supplements remain outstanding.

- 2026-11-05T11:34:57+08:00: Saved-generation assessment unit implemented and passed isolated27 pure main tests (9 predictive/10 generation execution/8 assessment),144 actual frozen recipes, Python AST/Bash syntax, CLI Slurm guards and documentation links. Formal integrity now enforces1000/5/seed456 itself; explicit diagnostic8/1 remains non-formal. CPU replay independently reconstructs runtime-dtype raw training fingerprint/prior and every saved geometric/matching/distribution score, checks input/source/version stability, retains new evidence only and performs no sampling or model loading. Actual29-control/64-real-sample CPU acceptance is prepared but not yet executed; publish first.989 last authoritatively158 epochs, formal accepted3/144/submitted8/144; full scope unchanged.

- 2026-11-05T11:44:48+08:00: Independent saved-generation assessment d6a71f6 accepted CPU1045:29 main/236 JUnit zero failure/error/skip,2 actual geometry cases,8 original-environment guarded CLI replays and64 saved diagnostic attempts,49 valid/15 invalid including one zero-valid case. Every row/summary/raw full64-train fingerprint/prior matched; input bytes unchanged, torch.load/jit.load/neural Module calls forbidden.10 parent and7 per-case source hashes Git-verified.1044 controller duplicate argv failure preserved; only local controller corrected. Latest authoritative989 RUNNING194 epochs/3:10:00;1040/41 waiting afterok989. Formal accepted3/144/submitted8/144; no new formal or sampling work counted, all remaining tasks/seeds/supplements retained.

- 2026-11-05T12:35:32+08:00: Completed ALIGNN scratch full independent acceptance through1040/1041; formal index4 unique968/969/988/989 of8 submitted. NequIP990 live83 epochs,991 pending with independent CPU chains1046/1047 and1049/1050 queued.1048 raw piezo/elastic audit and source recovery passed;19500 source records,5000/14499 valid,2297 piezo zero labels,0 shared-ID anchor conflicts; conversion remains next. Plan shifts next launch unit to deferred full-preparation CPU gates/submission because one GPU and long queue should advance automatically from verified preparations, without lowering any science budget or count rules.

- 2026-11-05T13:10:26+08:00: Added deferred full-pair scientific gate and Slurm submission module with public CLI/wrapper/docs. Measured capacity determines finite reserved budgets; exact source/config/script/request tokens and atomic stage claims preserve safe recovery. Generation retains training->1000-attempt quality->independent CPU assessment dependencies; predictive independent evaluation remains mandatory separately.31 local protocol checks passed; existing models/data/engines/environments unchanged. Publish and actual CPU acceptance precede arming20 queued seed123 preparation pairs.

- 2026-11-05T13:22:15+08:00: Published97523c2 deferred submission and accepted actualCPU1051 with31 main/318 JUnit, six real full gates, two CPU-only Slurm children1052/1053 and six Git blob hashes. Armed and independently verified20 CPU gates1054-1073 after their original preparations; two formal modes will launch only after each genuine complete gate. Generation chains1000/5/456/100x2 quality then independent CPU assessment. Initial outer control request missing shebang was explicitly rejected without job and preserved; corrected only ignored local controller. Existing8 formal submissions/4 accepted unchanged;990running174; all original144 cases/seeds and supplements remain required.

- 2026-11-05T13:36:59+08:00: Added supplemental_tensors benchmark module with targets, joint anchored partitions and full-source preparation/public CLI/CPU wrapper. Preserves all valid raw3x6/6x6 labels as free Cartesian27/81, elastic*0.1GPa, original geometry and immutable primary dielectric roles across ID/geometry/MP transitive groups. Reports conflicting anchors rather than dropping records. Existing critical data/model files untouched;32 pure controls passed. Next publish and execute complete sources with independent per-component/cross-task-group validation;144 primary goal unchanged.

- 2026-11-05T13:46:59+08:00: Published86aa7eb and completedCPU1074 full higher-tensor conversion plus1075 independent full label/material-partition replay. Two complete datasets now ready:piezo5000 split3998/502/500, elastic14499 split11587/1442/1470, one bad label recorded. Full primary4999 roles preserved across15904 material groups; zeros/tails/large structures retained.39 main/205 JUnit and9 executed Git blobs verified. New data adds0 formal trainings;990running213, accepted4/submitted8 of144 unchanged. Original remaining seeds/tasks and supplemental model/molecule/plugin/native/freeze/cost obligations retained.

- 2026-11-05T13:56:00+08:00: NequIP990 pretrained formally accepted through1046/1047 after223 epochs/best193: E/atomMAE0.0239988711 and forceMAE0.0451252690 on full164 heldout. Full1566 inference SHA26db0e..., trained15 required physical checks and original metric/source/reload/Slurm/request controls passed. Unique independent formal count5/144, submitted8; previous four proofs preserved.991 scratch nowRUNNING7 with1049/1050 already dependent. Supplemental data1074/1075 remains separate from training counts; primary tasks/seeds and all original supplements still outstanding.

- 2026-11-05T14:07:03+08:00: Found actual Guqq2 RUNNING991 reports GPU only via TresPerNode while public execution required AllocTRES. Added execution/slurm.py running owner/job/node-aware modern/legacy parser and finite wall-budget checks shared by prediction/generation. Explicit CPU/zero allocations never fall back; pending requests never qualify.37 isolated protocol controls passed. Existing private991 training unaffected. Next publish, actual CPU acceptance, queue zero-training GPU check, and replace exact20 ownPENDING97523c2 gates with fixed-source gates while retaining requests/dependencies; remaining seeds456/789 still required.

- 2026-11-05T14:43:04+08:00: Fixed real cluster Slurm allocation-field incompatibility17be214 and acceptedCPU1076:37 main/350 JUnit,6 real full gates, actualCPU rejection,7 Git source hashes. Queued real tinyGPU1077 after991; safely replaced20 own stillPENDING old-source CPU gates with1078-1097 waiting on1077 and original prep, preserving claims/terminal cancellation proof. Added low-priority8 genuine generation prep pairs/seeds456/789 and8 CPU gates1098-1113 covering16 later cases. Actual formal5/144 accepted,8/144 submitted unchanged;991running89. Remaining40 predictive pairs/80 cases need their full preparations; original144 and supplements retained.

- 2026-11-05T15:00:40+08:00: Added public full predictive preparation module and CLI/Slurm wrapper for all60 original predictive pairs. Reuses unchanged native reference, full graph scanner, paired100-batch capacity and two-mode CUDA physical validators with actualcase seeds, complete source/split/calibration checks and both final full gates. CGCNN parity copies only unused CSV labels.45 isolated protocol tests passed; no numerical/model/data/probe source change or new formal training. Next publish/CPU acceptance then queue40 genuine seed456/789 preparation pairs and40 success-only gates for80 remaining primary cases.

- 2026-11-05T15:20:06+08:00: Published full predictive preparationdcb5721 and acceptedCPU1114 45main/393JUnit,4 real full sources/splits,6 existing full mode gates,12 Git blobs. Queued40 genuine GPU prep pairs and40 success-onlyCPU gates1115-1194 for80 remaining predictive cases,low priority/finite16h64GiB, unchanged model/data/engine/probe physics. Verified all144 frozen IDs covered by actualformal8 or genuine full prep/launch pipelines40+16+80, with formal5 accepted/8 submitted unchanged.991running152,1077pending. Existing requests retained; next actual execution/results and independent post chains/supplements, not completion claim.

- 2026-11-05T15:40:16+08:00：安装收据核对通过：897完成、三个环境版本及899单独/汇总报告一致、RTX5090 CUDA12.8验收通过、898 JUnit18项零失败/错误/跳过；未执行重复安装。

- 2026-11-05T16:05:59+08:00: User changed every experiment to one training seed123. Active primary48 (four original models/six tasks/two whole-body initialization modes), supplements also123; frozen144 definitions and all previous5 accepted proofs/43 archives remain. Verified/canceled exact96 ownPENDING excluded456/789 preparation+launch requests (48 gates first,48 preps), retained23 active123/control handles and all old receipts/instantCANCELLED records. Separate machine scope48/excluded96 has matching server/local SHA9b33ab3f987bd9476c24711b7e0adc39cb4abfee666840fe086c6aea31837ea7;4 pure config controls and docs/history/full coverage8+40 passed. First RPC timeout independently proved no action before compact retry.991 reportpassed199 and996running require next independent result collection; no new acceptance count yet.

- 2026-11-05T16:43:03+08:00: Independent predictive assessment implemented: original full training gate, source/dtype-bound raw metrics, distinct unchanged force/response physics tolerances, complete CPU inference and separate no-model all-output validation with source hashes.36 isolated main controls passed (16 new assessment,9 original formal,7 tensor,4 scope), no localTorch;8 Python ASTs/Bash/docs checks passed. Early8 classification diagnostics explicitly opt into missing balanced fields while all original metrics remain strict; formal schemas remain strict. Current numerical science/code/engine unchanged. Next publish then CPU36-control acceptance/40 exact accepted diagnostic replays/six original fullFF and fresh991 post+independent.5/48 accepted unchanged until evidence collected.

- 2026-11-05T17:11:00+08:00: 1198 again passed36 main/290JUnit with zero failure/error/skip, then actual bandgap replay exposed incorrect universal natoms requirement. Engine writes natoms only for forcefield. Fix assessment to require it there, derive graph-level counts from bound raw source, and validate optional recorded counts. Fixtures now match actual engine format, with new absent-force-count rejection and optional-graph-count acceptance.37 pure main controls pass without localTorch, AST/docs/Bash/diff checks pass; no metrics/tolerances/engine/model/data change.1199/1200 exactPENDING dependent jobs canceled with immediate proof,1195/1198 and transport evidence retained. Publish fix then newattempt003 CPU acceptance.

- 2026-11-05T17:36:31+08:00: Predictive numerical acceptance complete:1201/1202/1203 actualCOMPLETED0:0;37 main/291JUnit zero failures/errors/skips,640 actual diagnostic tests and984 fullFF raw tests/9396 full source saved records,17 executed source blobs. Fresh991 best physical15 checks/full1566/independent source+output verification accepted199/best169. Unique formal6/48,submitted8,old5 proof/43 hashes retained; purged original991/1049/1050 terminal limitation explicit. CGCNN four exact CPUpost/verify1204-1207 request/source/resource/dependency identities accepted metadata-only; no newtraining/CG scientific claim.

- 2026-11-05T19:14:56+08:00: Prediction post launch resolver implemented for exact16 active pairs, both original full preparation gates and frozen managed dispatch/plan/scripts/receipts/tokens/source checked before only4 CPU post/verify stages. Original train claims unchanged, no training submission. Retained-job identity/allocation and complete-artifact fallback for missing handles, stable fingerprints exclude volatile Slurm state, known receipt reuse/unknown stop.59 isolated main controls passed (10 new resolver,12 original dispatch,37 prediction/formal/tensor/scope), no localTorch; AST/Bash/docs/diff passed. New CPU budgets72h32GiB post/4h8GiB verify are finite initial limits, not runtime guarantees. Publish then actual CPU transport/CG996 artifact audit before arming16 resolvers; accepted count remains6 until audit proof.

- 2026-11-05T19:37:43+08:00: Accepted source33afb0c CPU1209 actual0:0:59main/439JUnit zero failure/error/skip,15 Git blobs, actualCPU1211/1212 exact receipt/afterok/reuse and0 duplicate jobs. Independent saved-artifact CG996 audit accepts53/best23/full164/15physics/full1566, original terminal limits explicit; formal7/48/submitted8, prior6/58 hashes retained and17 CG files added (75total). Armed and verified16 CPU post resolvers1213-1228 after original gates1078-1093, expected64 later CPU stages/0 newtraining.997running35, original prep/generation unchanged; sharedfree121.24GiB retains20GiB reserve.

- 2026-11-05T19:53:38+08:00: Rank3/4 validator implemented for graph Cartesian27/81 outputs, all-slot rotation and odd/even inversion, original auxiliary finite differences/mixed gradients/batch checks and no projection.64 pure main controls passed without localTorch; three forcefield AST bodies/rank2 arithmetic unchanged. Current post binds new Cartesian helper SHA; original primary caches remain pinned and untouched. Actual Slurm numerical acceptance follows publication; formal7/48/submitted8 unchanged, no supplemental training claim.

- 2026-11-05T20:10:31+08:00: Actual source d6f2ddb CPU1229/1230 accepted105main/509JUnit zero failure/error/skip,17 high-rank live/oracle/error-injection tests and24 original physical/FD/Eatom/heldout checks plus64 protocols. Eight live rank3/4 fixed/equivariant float32/64 reports and8 Git blobs source/request/retained0:0 bound; no model/core/dataset changes or new training. Added separate16 seed123 higher-tensor definition/source audit exporter,85 local pure tests passed (8new+13data+64protocol), no localTorch. Full19499-record/1309419-component source audit and config export on CPU still pending publication; original48 primary7 accepted/8 submitted unchanged.

- 2026-11-05T20:29:53+08:00: Source90a5836 actualCPU1231/1232 accepted85main/509JUnit,5Gitblobs and publicCLI complete19499 ordered source records/1309419 finite Cartesian components,16 separate seed123 configs/8pairs. Parent1074/1075/data+canonical split/numeric1229/source/request/retained0:0 hashes bound; zeros/tails/primary roles preserved. Actual8 nice1000 GPUprep1233/1235/...1247 plus8 tinyafterany terminal1234/...1248 owner/source/request/resources/afterok1077 dependencies verified. All pending,0 newtrain; full graph/capacity/physics and independent full gates still pending. Live997RUNNING56,1077PENDING,free121.23GiB; primary7/48/8submitted/75archives unchanged. Two receipt-observer failures were pending-resource format assumptions: exact fresh rawTresPerNode=gres:gpu:1 was retained and correctly validated without resubmission.

- 2026-11-05T21:07:29+08:00: Independent supplemental tensor gate implemented with strict closed16 definitions and exact retained preparation terminal/request/source/resource proof. Shared original graph/capacity/native calibration/artifact/version checker preserves primary144 selector AST; stricter rank3/4 CUDA component/parity/geometry/worstIDs/gradients/source/timing and two/100 schedule.119 isolated main controls passed without localTorch (12new plus definitions/data/primary prediction/deferred/generation/typed-OOM regression), AST/Bash/README/history/diff checked. Publish then actualCPU seven completed primary gates/full tensor inputs/eight actual CPU numeric reports/unfinished preparation rejection before arming8 independent gates. Primary7/48,8submitted unchanged. Three CPU terminal observers1249/1250/1251 attach to997/1206/1207 without rerunning; legacy997 WorkDir root+body fixed-cache behavior identified from exact original request/source, first observer attempt stopped before claim and had no submissions.

- 2026-11-05T21:39:50+08:00: Source3483500 actualCPU1252/1253 accepted119main/825JUnit zero failures/errors/skips,7 Gitblobs,seven real complete existing primary mode gates/source/original graph/capacity/physics/training receipts replayed without model loads/forwards. Full19499/1309419 tensor inputs/16 configs checked;8 actual CPU response reports refused as CUDA and8 unfinished preps rejected. Armed/verified8 CPU independent gates1254-1261 after each original GPUprep+its terminal recorder;0 training. Added/verified3 CG terminal observers1249-1251; original997/1206/1207 exactCOMPLETED0:0 captured before purge. CGscratch997 accepted59/best29/full164/15physics/full1566; all8 seed123 full FF now accepted (primary8/48,submitted8), prior7/75 archives intact and15 new files (90total). Ten other original producer prep reports passed (all spectrum/dielectric+CG/AL gap);1013 MACE gapRUNNING,1077PENDING, no failed prep in this observation. Producers still need dependent independent launch gates.

- 2026-11-05T22:11:05+08:00: Implemented separate full supplemental16-case training/CPU post/no-model acceptance entry. Strict successful original independent pair gate plus both hashes and full preparation replay before shared training; complete27/81 raw labels/units/zero-nonzero-component metrics and CPU rank parity/FD/geometry/gradients.130 pure controls passed, primary144 selector/full history unchanged; actual157-control/live numerical/eight completed FF source-gate acceptance follows publication, no new training claim.

- 2026-11-05T22:19:54+08:00: Actual sourcefade5fd CPU1262/1263 accepted157main/946JUnit zero failure/error/skip,18 executed Gitblobs,8 fresh live Cartesian rank3/4 numerical reports and8 completed primary original full gates/training receipts without model execution. Full19499/1309419 data and16 definitions audited;4 actualCPU-f32 schemas accepted while8 CPU reports still failCUDA and8 unfinished higher preps failclosed. Full supplemental train/post/independent entries now accepted; managed Slurm pair launcher/terminal chaining still required before arming16 trainings. Original primary14 producer preps passed/1017MACEclassRUNNING/1077pending at221700. Primary8/48,0newtraining and all90 archived accepted hashes unchanged.

- 2026-11-05T22:48:10+08:00: Implemented managed supplemental pair launcher and immutable terminal telemetry. Original independent gate request/source/resource/retained0:0 bound;12 stages per pair (2train/4scientificCPU/6afterany), signed nice1000 science/0 recorders, separate claims, atomic reuse/unknown and purged stop, full prevalidation before adding stages.141 pure controls passed (11new+130regressions), default primary transport unchanged; no localTorch. Publish then Slurm168 controls/live and six harmless CPU children (including expected exit7) to prove real afterany/reuse/terminal capture before attaching8 original gate resolvers. Primary8/48,0newtraining unchanged.

- 2026-11-05T23:01:08+08:00: Actual source3ef5f11 CPU1264/1265 accepted168main/983JUnit zero failure/error/skip,25Gitblobs,eight full primary gate replays/full19499 records/16spec/8live tensor outputs. Six harmless CPU children1266-1271 proved nondefault claims/tokens/afterok/afterany,4 known receipt reuses0newjobs and actual intentional exit7 recordedFAILED while3 recorderscompleted0:0. Armed/verified8 original-independent-gate terminal observers1272/1274/...1286 and8 managed pair resolvers1273/1275/...1287, each afterok original1254-1261+its recorder; all16PENDING,0newtraining. All16 main predictive producer preps passed;1020CGgenRUNNING samplingcapacity/other3pending/1077pending. Sharedfree114.61GiB,keep20GiB; primary8/48 and all90 archived scientific hashes unchanged.

- 2026-11-05T23:19:36+08:00: Frozen ablation definitions implemented:8 separate pretrained seed123 dielectric/FF cases covering4 original providers, only train_backbone=false relative to original947 recipes; original primary/high-rank definitions untouched. Full6565 source registry/audit/split/ordered-ID/raw unit+shape+finite label audit and fresh8config export CLI added.148 pure controls passed (7new+141 regressions), no localTorch; actualCPU159 including6 frozen numerical state/geometry oracles and5 existing freeze/buffer/checkpoint-resume controls plus full source/export/eight primary gate replays follows publication. No frozen official readiness/training claim.

- 2026-11-05T23:46:44+08:00: Full frozen definition/physics acceptance159main981JUnit15Gitblobs/8configs/full6565+393783labels recorded. New primary managed36 requests independently identity-audited (32pred+4genAL/NQ), formal index44submitted/8accepted, prior90scientific hashes preserved;36 exact tiny train terminal recorders1410-1445 armed+verified. Current1290NeqdielectricFT RUNNING; CGpiezo supplemental originalchain12requests1398-1409 verified/2train pending separate fromprimary. CG1020scratch image-budget51129>50000 andMACE1022pretrained nonfinite nodes are preserved non-OOM sampling failures,4maincases remainunsubmitted; next priority tested generation recovery/full existing-pipeline evidence, no blind retries or scientific protocol reduction. One SSH observation closure was re-polled for the same1288 job, no restart.

- 2026-11-06T00:21:26+08:00: Implemented benchmark-only staged generation readiness and explicit full-quality failure policy. Original failed CGCNN/MACE sampler reports stay failed; unchanged full source/graphs/both100batch CUDA training/config/prior/artifact/version checks remain mandatory. Full trained-best1000/5/456/100x2 batch1 quality and separate CPU no-model assessment remain mandatory. Strict existing entry and all model/graph/engine arithmetic unchanged. Local178 pure controls passed; next publish and CPU189 controls plus real8 generation/8 forcefield gate replays. Main48 scope/submitted44/accepted8 unchanged.

- 2026-11-06T00:30:29+08:00: Corrected new generation failure-evidence adapter to compare original trial report_sha256 with canonical_digest(JSON), preserving separate raw file SHA in readiness output. Updated fixture to actual producer semantics and semantic tamper refusal. Source88b34b6 CPU1446/1447 retained FAILED1:0 after189main/1082JUnit controls passed; all original preparation/science untouched. Local178 regressions pass after correction; next publish and reaccept new source before four missing train/quality dispatch.

- 2026-11-06T00:41:51+08:00: Added explicit original request/control/graph provenance for failed generation parents that lack success-only git_commit. Separate proof retains original job/receipt/request/control hashes and checked original source, without editing failed reports or substituting currentHEAD.181 local regressions passed. CPU1448 passed189/1082 controls but stopped at the previously missing provenance;192-control real-evidence reacceptance is next. Original48 scientific scope and8accepted/44submitted unchanged.

- 2026-11-06T01:10:29+08:00: Accepted staged source4347ca3 actual1450/1451:192main1091JUnit/12blobs/8real generation readiness+strict gates/8accepted FF replays/actual1000-invalid runtime. Four read-only plans1452-1455 completed, exact deployment1456/1458/1460/1462 and terminal observers passed. Independently audited40 managed requests4train/8quality/8assessment/20afterany; exact8 pending old QA canceled,4 legacy train receipts preserved. All90 original scientific hashes intact and all48 active primary training IDs now covered, scientific accepted8 unchanged. Archive and plan/state updated; remaining full science and supplements remain active.

- 2026-11-06T02:00:45+08:00: Implemented closed frozen official-readiness layer: exact accepted8 definitions, matched original finetune/scratch graph/source reference, unchanged disposable probe loop with scoped exact-state/optimizer audit, own100-batch CUDA and worst-two physical checks, separate CPU gate. Default primary positive-backbone physical policy and tolerances unchanged; explicit frozen policy requires zero body and positive readout gradients.193 pure regressions passed, actualCPU220/24oldgates and then8 low-priority GPU preparations pending. No main case/source/data/seed change, no frozen training launched.

- 2026-11-06T02:12:36+08:00: ActualCPU1504 exposed4 tensor oracle setup errors from e3nn CartesianTensor deepcopy;2 force oracles and all other controls passed. Fixed test shadow construction using supported independent factory+strict state load, retaining bitwise/RNG/FD assertions. Production frozen readiness and all model/engine sources unchanged; publish fixture correction and rerun220 controls/24 original gates before8 official frozen prep submissions.

- 2026-11-06T02:45:49+08:00: Frozen readiness sourceb167881 accepted actual1506/1507 after supported independent tensor oracle construction.8 low-priority official full-source CUDA preparations1508/1512/1516/1520/1524/1528/1532/1536,8 independent CPU gates and16 afterany recorders submitted and exact32 identities validated. No official frozen training yet; full execution/post/no-model adapter is next. Primary1290 liveepoch87/best64/full3998train502val; primary48submitted8accepted and all supplements preserved.

- 2026-11-06T03:18:55+08:00: Implemented closed eight-case frozen full training/post/independent acceptance with full-epoch/heldout coverage, unchanged optimizer arithmetic, every-step body-state guard, actual best/last checkpoint body/head/policy reload audits and explicit zero-body/positive-head gradient policy.203 pure controls passed; actual CPU numerical acceptance still required before deployment. Archived original1290 complete94-epoch/best64/499test and retainedCOMPLETED0:0 terminal; existing1306post/1308verify pending,1291running, primary scientific count remains8/48 and full scope48 plus supplements retained.

- 2026-11-06T03:29:39+08:00: Frozen full executor sourcef761dd8 numerically accepted by actual1540/1541,236main1207JUnit37blobs24original gates,6 real whole-training/RNG/checkpoint/input-derivative oracles and3 complete post/no-model controls.64 tiny terminal recorders1542-1605 now preserve future original predictive post/verify terminal proof without new science.1291 NequIPdielectric scratch running14epochs;1290 passed94/best64/499test with retainedCOMPLETED0:0 but independent1306/1308 pending. Primary48submitted8accepted, frozenfull0; next frozen managed executor submission and original pending preparation gates, with all rank3/4/molecular/plugin/cost/source deliverables preserved.

- 2026-11-06T03:47:26+08:00: Added frozen single-case managed six-stage submission and exact original b167 upstream terminal bindings, preserving original full executor/model/engine/capacity/readiness bytes.212 pure controls passed including reuse0new and unknown/foreign/purged refusal. Next actual245-control Slurm acceptance and6 harmless transport children, then8 CPU launch resolvers waiting original gates;0 official frozen training and main48submitted8accepted remain.

- 2026-11-06T04:47:31+08:00: Frozen managed launcher27e2339 accepted1606/1607 (245main1245JUnit45blobs,8 actual incomplete upstream blockers,6 real transport children),16 gate-dependent CPU launch/terminal requests1614-1629 submitted and independentlyPENDING. Resolved original1290 post queue through resource-only2h/1h full assessment: original1306/1308 exactpending cancellations preserved; new1634/1636 plus1635/1637 actualCOMPLETED0:0. Full499 raw tests,5 trained-best O3 checks,4999 complete inference and independent no-model acceptance passed,15 scientific Git blobs, original training unchanged. Main accepted9/48/submitted48, original90+new44 immutable archives; NequIP dielectricFT MAE59.3887019232 RMSE666.8232597672 (dimensionless), CPU90.94s/1.91s.1291 lastobserved46epochsRUNNING. All remaining main39 and native/frozen/high-rank/molecular/plugin/cost/source work preserved.

- 2026-11-06T05:15:27+08:00: Original1291 NequIP dielectric scratch independently accepted55/best25 after full1642post/1644no-model verification; main10/48, all48train requests retained,178 archived SHA. All499 tests/5 physical checks/all4999 inference unchanged. MAE60.1823502192/RMSE700.1185002492 retained alongside1290 MAE59.3887019232/RMSE666.8232597672; one-seed outcomes, no general benefit claim. Only exact pending1310/1311 replaced after actual1638preflight/1640actor; CPU91.4577s/1.9184s, no retraining. Latest1292 CGCNN dielectric FT running; full remaining main/supplement scope remains active.

- 2026-11-06T05:37:07+08:00: Acquired complete author rMD17ethanol v4NPZ67201791B plus first officialCSV/readme; actualSlurm1646full100000-source audit and1647terminal passed.20sourcearchives retained,100000E/2700000F finite/7arrays/official1000+1000lists/6Adegree8. Vlab killedfreshproxy after4.4MB; localGET+MD5 andSCPcompleted, fullSlurmverifiedpriorprefixthenpreserved it. Declared900train100val within officialtrain1000 with99000fullheldout and separate originaltest1000 report; respects author correlated-MD warning without dropping sourceframes. Conversion andofficialnonPBCprofiles remain next; main10/48and48submitted unchanged,1292 RUNNING22epochs.

- 2026-11-06T08:14:12+08:00: FullCGCNNdielectricFT1292 andscratch1293 independently accepted; main12/48,48unique trainingrequests,266scientificSHA. Full45best15/64best34,499rawlabels/4999inference/eache15sources andoriginalrequiredfixed-frame physics passed; nonrequiredrotationcovariance failures retained ratherthan calledO3. MAE73.5451166892vs74.8091329103, originalfull labels/single123. Only4unstartedCPUchildren exactlyreplaced afteractualreadonlypreflights; new8scientific/recordersallCOMPLETED0:0, no retraining. Latest1294MACEFT runs; proceedrMD17conversion/fullremainingmain-supplementgoal.

- 2026-11-06T08:24:31+08:00: Implemented rMD17module source/partitions/conversion withREADME andSlurmCLI, all100000nonPBC sourceframes/explicitSIunits/900-100-99000+official1000testcohort/freshsourceboundaudit.14newpure controls and combined48protocoltests47pass1existingSlurmNumPydeferred; originalsengine/preparation/splits unchanged. Codepublication precedes realSlurm fullconversion/independent verification; no extra primaryscientific completion or molecular training claimed.

- 2026-11-06T08:36:11+08:00: rMD17actualcomplete conversion and independent verification accepted1664-1667;all100000nonPBCframes/positions/100000energy/2700000forces exact/standardloader and900-100-99000 plusofficial1000testcohort passed.48realzero-skiptests/12sourceblobs/34metadataarchives;prior266science+20sourceSHA preserved. Prepareddata159.6MB plus14.4MBsplit readyforfuturemolecularinputs, not yetofficialCG/ALprofile or moleculartraining. Main12/48,1294MACEFT lastRUNNING12epochs; sourcecache4f30bea and alloldercache/queue preserved.

- 2026-11-06T09:20:59+08:00: Implemented explicitmolecular_radius inputprofile for originalCGCNN/ALIGNN withdefault6A/allneighbors/noPBC, sourceboundcheckpoint metadata and unchangedoriginallearnedmodules. DenseCGvalidmask excludespaddingBN/messages and restores modes/hooks; ALusesoriginaltriplets/container and rejectsinventedlattice/nativebulkstress.38pure controls/AST/docs passed, realCPU54+regressions and separateCUDA stillrequired before molecularscience. Existingprimary12/48 andfullrMD17data proofs preserved; oldsourcecaches untouched.

- 2026-11-06T09:37:19+08:00: Original molecular CPU1668 actualFAILED1:0, afterany1669 retained. 219JUnit cases: zeroerrors/skips, one failure in existing periodicALIGNN float64 reference preparation: upstreamGraph created float32atom_features outside a matching default_dtype context while originalmodel was double. All53other original-model cases and32actualCPUfixture calls passed, including molecularFD/mixedgrads. Wrap the periodic reference fixture in restored default_dtype(dtype), the same preparation contract as native input. Preserve independent originalreference, all54cases, outputs and originalassert_same tolerances. Beforecommit run38purestdlib regressions,9AST plus oldperiodic-body equivalence and docs/history checks; then publish/pull clean newsource and rerun full actualCPU219control,full900graphs and8realdiagnostics. No molecularCPU/CUDA/formalacceptance yet; failed1668/1669 bytes remain archived. Main12/48 and singletrainingseed123 unchanged.

- 2026-11-06T11:51:01+08:00: Enter original1294 MACE dielectric pretrained finite CPU post restaging. Original full37/best7 with3998/502/499,seed123,batch4,float32,cap300/pat30 completed;1430 retained trainCOMPLETED0:0. Best2b8e096c9cbd5a9367dac3bc597dd04a5eba43e41c6d3b15c1b793dfc1b76e80. Use accepted27e2339/sourceMACEvenv for model-forbidden fullcontext/retainedsource/preflight; only if old1315/1317 exact ownedPENDING identity and reviewedinput/plan pass may replace their72h/4h resource requests with fullpost2h/verify1h andafterany, originalscience unchanged. Tests: AST/bashsyntax, read-onlySlurm complete formal_context/best/source/receipts, reviewedplanSHA, actor immediate exactcancellation receipts, full499rawtests/unchanged5requiredO3physics/all4999 streamedinference and independent no-model verification before mainindex13. No retraining/shortenedcoverage.

- 2026-11-06T11:53:12+08:00: Original molecular CPU1670 sourceea222be independentlyaccepted:219JUnit counts (170ordinarycases+49passedsubtests),54originalCG/ALIGNNcases,32actualCPUfixture calls, zeroerrors/failures/skips. Eachprovider full900rMD17traininginputgraphs,8100atoms/64800valid nonPBCradius6edges;ALIGNN483088originaltriplets; model-forwardforbiddenduringfullscan. Eightprovider/init/f32-f64 real10-recorddiagnostics40optimizersteps, finitepositivebody/head grads andchangedstates.11Gitblobs/17archives independentlyverified; prior266science+20rawsource +34conversion archives allintact. Actualwall74.360183s/RSS2610204672B. 1670actualCOMPLETED0:0retainedby1671;1671ownfinalexitlivehandlepurged/unavailable,notinferred. SeparateCUDA1672/afterany1673 actualPENDINGsourceea222be; noCUDA/formalmolecularfit/quality/paired100batch or mixed-extremecapacity acceptance. Main12/48/48uniquetrainingrequests andsingletrainingseed123unchanged.

- 2026-11-06T11:59:52+08:00: Precommit actualchecks passed:38purestdlib controls,zeroerrors/failures/skips,9AST, oldCG/ALIGNNperiodicbodies unchanged,docslinks/fences andappend-onlyhistory/gitdiff checks. IndependentCPU1670metadata17archives andprior266science+20source+34conversion SHA passed. Single-seedscope exact9b33ab3 unchanged. MACEfullpostpreflight1674/actor1676 retained0:0 and reviewedplanSHA47bd0279 pass; onlyexactoldownedPENDING1315/1317 cancelledwithimmediateproof. Newfullpost1678/t1679 andindependent1680/t1681 exactsubmitted,postcurrentlycomplete_source_inference (raw499rescore passed); pendingfullcompletion not mainacceptance. All originaltraining preserved.

- 2026-11-06T12:08:22+08:00: Enter campaign matrix CLI single-seed closure. Actualexisting48scope/excluded96 remainscorrect, but scripts/prepare_arxiv_matrix.py called the historical builder defaultseeds123/456/789. Change only thiscampaign CLI to explicitseeds=(123,), preserve reusablebuilder/history144 and alloriginal pinnedworkers. README show explicit current48/APIseeds123 andhistoricaldefault. Testplan: realCLI withmocked full-inputinspection only (no actualbulkdata/no fakeSlurm science), actual48config exports/all4x6x2/only123 andfixedgenerationRNG456; freshoutput refusal, actual inspection target, sourceSHA metadata andnoSlurmentry refusal; historical144/fullcase gates remainunchanged withexistingpurestdlib regressions. AST/bash/docs/history/gitdiffchecks beforecommit. ThreeconsecutiveVlab observationclosures reviewed existinglessons; reports/jobs notdeclaredfailed, no duplicate submissions or blindproxyrestart. FullMACE1678-1681 livecompletionunknownuntilnextsuccessfulread.

- 2026-11-06T12:12:09+08:00: Actualprecommit14purestdlib testsPASSED,zeroerrors/failures/skips:3newrealcampaignCLI controls (mockonlyfullinputinspection/Gitmetadata, actual48configexports andcompleteactivecrossjoin/fixedgenerationRNG456, existingoutputrefusal,noSlurmrefusal),4existingscope,7existing144-matrix/data/recipe regressions. InitialnewtestexpectedLinuxslashmetadata onWindows; correctedonlyfixturekey toactualnativePath producer, allsourcehash assertions retained.2AST passed; CLI moduleexactASTunchangedafterremovingonlynewseeds123keyword; no backbone/readout/engine/dataset/split/scientificvalidatorPythonsourcechanges. ScopeSHA9b33ab3 unchanged, shellsyntax/docslinks/fences/append-onlyhistory/gitdiffchecks passed. No Torch/NumPy/localnumerics, no freshservermatrix or formalcase creation. Remoteobservationcurrently4Vlabclosures; lastconfirmedmain12/48,fullpost1678RUNNING at115808 and CUDA1672PENDING at115155, lateststatesexplicitlyunknown. Awaitconnectivity evidence, no duplicatejobs.

- 2026-11-06T12:19:52+08:00: MACE1294dielectric pretrained FULLscientificacceptance COMPLETE; main13/48 unique48submitted. Originalfull37/best7,3998/502/499,batch4,float32,seed123,300cap/pat30; best2b8e096c9cbd5a9367dac3bc597dd04a5eba43e41c6d3b15c1b793dfc1b76e80. 1430retainedactualtrain0:0;1678fullpost and1680separatemodel-forbiddenverification actualCOMPLETED0:0 retainedby1679/1681 beforelivehandlepurge. Recorder ownexits unavailable, notinferred; no reruns. Full499rawtest4491labels/5unchangedrequiredO3derivative-geometry checks/all4999source44991finiteoutputs /15executedGitblobs independentlyverified. OriginalstrictMACEclass+wholeparam/buffercoverage1 intact. MAE67.45663556272918 RMSE711.6883389418933 Frob365.2284964839321 relative10.612698249878184. CPUpost273.585509s/independent2.203634s/RSS1549643776B. GPU6603.000659s/allocated1992630784/reserved5964300288B. Infer4268354B SHA9f0d9f859fe8fd4a4247f3630d23c609afcc15a6a4342baf64b89fdae4770775. 44newarchives preserve266prior=>310; original12indexbackedup, no training/science truncation. UsermanualSSHsuccessful; subsequentactualsmall/fullSSH recovered, rootpulled033c7bc. Single-seedCLI14tests+staticchecks passed andpushed033c7bc; allsupplements retained. Testplan/results for thisacceptance: actualparent+independent reports,exactsource/request/report/rawinferenceSHA, retainedscientific0:0/ownobserverlimits, complete499/4999/5physics and310archivehashes mustremainverifiable. Doccheckcurrent13/48/checkbox/metrics/sourcepaths andappend-onlyhistory beforecommit; no new numericaltests needed.

- 2026-11-06T12:27:47+08:00: Enter full nonPBC molecular and directoryplugin supplement definitions/source gate unit. Structure: newbenchmarks/molecular/{source.py(full100000record/source/CSV/split audit), definitions.py(original947FFrecipe inheritance,8officialpretrained-scratch cases+1existing KNN+GCNplugin scratch only),__init__.py,README.md}; scripts/prepare_molecular_experiment_definitions.py Slurmonly CPUentry exportsordinaryconfigs, no jobs/training. All9seed123,full900/100/99000,original1000 testcohort separately,fullsource unfiltered,originalE/Frawbindings andf32/300cap/pat30/B4 inherit. ExplicitCG/ALmolecular_radius6; MACE/NeqoriginalnonPBCinputs retainofficialarchitecture; existingplugin KNNk2/width16/layers2/live-distancegeometry, no fakepretrainedmode. Keep8MLearn primaryacceptances/main48 unchanged; molecularofficial8+plugin1 aredeclaredseparate supplements. Stats use900train only, explicit noPBC/no bulkstressaccuracy/trajectorygeneralization claims. Testsplannedbeforeimplementation: exact9exports/4pairs/only123, unchangedprimary144 andrecipesexceptdata andexplicitinputprofile; pairedconfig equality, pluginfiles/shape contracts, frozenrawSHA vs canonicalmanifest SHA distinction, finiteE/F/geometry/metadata/groups/sourceordering/uniqueoldindices/invalidPBC/NaN/bool adversarialsmallfixture controls, immutablefreshoutput, noSlurmfullaudit/export refusal, noTorch/NumPyimports. Actualfull100000source+fourauthorbytes/officialCSV partitions mustpass CPU Slurm beforedefinitionacceptance. No CUDA/paired100batch/training/modelquality acceptance inferred; own CUDA1672 stillpending after121841. Previousgoalturnprogress main13/48 accepted310archives andCLIseedfix14tests, notwait/block.

- 2026-11-06T12:40:21+08:00: Actualprecommitmolecular definitions checksPASSED:44purestdlib controls zeroerrors/failures/skips, including11newmethods/configs/synthetic-source/adversarial subtests plusoriginal144recipes,rMD17conversion/ split/currentCLI/scope regressions. Actual9configexport usesmockedinspection only anddeclaredmetadata-only unitSlurm marker, notfullsource orscientificevidence. Plugin3codefiles LFhashes,4officialpairs/8configs plus 1pluginrandomcase/seed123, unchangedoriginalrecipes exceptdata andCGALexplicitprofile verified. Private3syntheticframe scanner rejectsbadID/group/PBC/bool/nonfinite/sourceprovenance/oldduplicates/ truncation/extrarecord/SHA; retainszero labels. NoSlurm and20GiB reserve gates verified beforework. 5AST/CLIhelp/docsfences-links/append-onlyhistory/scopeSHA/gitdiffpassed; no criticalbackbone/engine/ data/readout/validator Pythonchanges. No Torch/NumPyimport or localnumerics. NextactualCPUfull100000 source+fourauthorfiles+CSV splits andexport gate on cleanpublishedGit. Main13/48 unchanged;1295training full55complete awaitingfullscience,1296ALIGNNdielFT running4epochs/CUDA1672pending at1235-1236.

- 2026-11-06T12:53:45+08:00: Enter original1295 full MACE dielectric scratch acceptance. Actualoriginal55/best25 and1431retained trainCOMPLETED0:0, best0fff33e9ac92145839b0b177cfb17ba210b53e762c28276f65aab068277b4bad. Wholeparameter/buffercoverage0, originalstate-layout and3998training-onlynativeStats observed. Use accepted27e2339/MACEvenv andunchangedfull499rawtest/5requiredO3physics/4999inference/no-model independent protocol. Preflightmust verifyfullformalcontext/inputhashes/exactold1319/1320ownedPENDING andretainreviewableplanSHA; onlythenresource-restage2h/1h withtwoafterany andimmediatecancellationproof. No retraining/shortening/sourcechanges orotherqueueactions. Tests beforeacceptance: AST/bash, actualSlurmpreflight, exactreviewedplan/identity,fullscientificreports/rawbytes/source15/best/ actualretainedscientificterminals andallprior310archives intact. Main13/48 untilallpass. Independentnew1682/1683 source/data-only definitioncontrol nowpassed44tests/all100000/9configs, 26archives/18Gitblobs andallprior310+20+34+17 intact; no moleculargates/training claim.

- 2026-11-06T12:59:24+08:00: Fullmolecular source/definition source1e19447 accepted actualCPU1682/afterany1683 bothCOMPLETED0:0 andindependentstdlib proof.44tests zeroerrors/failures/skips,18Gitblobs,all100000records/100000E/2700000F/ fourauthorfiles/900-100-99000+original1000cohort verified.9ordinaryconfigs (8originalofficialpairs+1existing directoryKNNGCNrandom)/4pairs/onlyseed123, noGNNconstruction.26archives preserve310science+20rawsource +34conversion+17originalmolecularCPU hashes. Actualwall11.593110963s/RSS194822144B. Definitionsruns/molecular-definition-control-1682/definitions SHAa4226e6fa9460093e3232af39e8a75e5f5651aacfa7e510386eeff4f64045fd3. CanonicalsplitSHAe7ee905372977d76c430a581f4fc9e2f33bfe44a60adb22eae00acb2d78adc69 distinct fromrawprettyprinted d1072a6c351ed760e60929cbade2b1bd1da542931efd715a5e181db1b469e58a. No nativegraph/CUDA/100batch/mixedextreme/physics/formalfit/quality acceptance. Original1295 full55/best25 awaitingfullscience; preflight1684/1685 actual0:0 reviewedplan551266d7, actorrequested toreplaceonlyoldownedPENDING1319/1320 withfull2h/1h/twoafterany, no retraining. Main13/48/48submitted unchanged;1296ALIGNNdielectricFT running9epochs,CUDAtest1672pending.

- 2026-11-06T13:09:33+08:00: MACE1295dielectric wholebackboneSCRATCH fullscientificacceptance complete; main14/48/48submitted. Original55/best25,3998/502/499,seed123,batch4,f32,300cap/pat30; nativeparameter/buffercoverage0 and state-layoutverified, originalnativecalibration only3998train. Best0fff33e9ac92145839b0b177cfb17ba210b53e762c28276f65aab068277b4bad. Original1431retainedtrain0:0; actualfull1688/independent1690 andafterany1689/1691 allCOMPLETED0:0 captured. Exactold1319/1320cancelledwithimmediateandlegacyproof after1684preflight/1686actor, no retraining. All499raw4491labels/5requiredO3physics/full4999inference44991finiteoutputs/15sourceGitblobs independentlyverified. MAE71.92361705390833 RMSE699.6432347993582 Frob385.18144490987726 relative17.14720724328601. CPU266.991999951s/independent2.211928633s/RSS1625030656B; GPU9581.448930381s/alloc1992944128/reserved5964300288B. Infer4266921B SHA712bf66ad5bd09b5fac28f94c8052b907204c7b20eae708b6891bc2a6f4d1fd4. New44archives preserveprior310=>354;13caseindexbackedup. Prior13indexscope descriptiveproviderlist hadduplicatedMACE fromtemporaryglobalprovider replacement whileall13actualcases/proofs werecorrect; new14scope explicitly derivedfromactualCGCNN/MACE/NequIP dielectricpairs, oldbackup/proofs kept. No tolerance/model/math/datachanges oruniversalpretrainingbenefit/crossseed claim. Molecularsource1682/1683 acceptance26archives/source1e19447 andall20+34+17priorinputarchives retained; 9supplement definitions only, no model/capacity/training results counted.

- 2026-11-06T13:34:09+08:00: Enter molecular full native-graph andtraining-onlystatistics preparation unit afteraccepted1682definition. Structure: addbenchmarks/molecular/contracts.py(closeda4226e9config/5model groups,pure metadata graphscope validator),graphs.py(CPUorCUDA full100000source/900train originalinputscan,source-boundselection, MACE/Neqonly900trainingnativeStats,compressedignoredgraphrows),scripts/scan_molecular_graphs.py Slurmonly andREADME. Reuseexisting count_graphs/edge_statistics/forbid_model_forward/select_probe andprepare_native_neighbors; do notchangeanyoldcritical orqueuedworker source. Onepretrained graph reference perofficialpair; plugin directnolearnedGraphBuilder.forward only, GNNforward forbidden. CGpaddedslots versusvalidedges recordedseparately; KNNplugin internalselfupdates separatefromphysicaledges. CPUscan ispreparatory topology/statistics only, cannotreplace requiredactualCUDAgraph/capacity/physics. Futurefinalgate requireexplicitCUDA scope, paired100batch/mixedextremes remainsmandatory. Testsplannedbeforeimplementation: exactclosed5groups/4pairs+plugin andsource/provenance tamperrefusal; fullsource/training source-order rows,coverage/geometrycounts/summaries,failedprefixretention, nonint/invalid counts andsource mutationrefusal; CPU-as-CUDA/incompletegraph/probe fake refuses; noTorch/NumPy top-levelimports. Actualnumerical graphcounter/originalNoPBC shifts/noGNNforward/state preservation andnativeStats only900 checked throughSlurm ineachproperproviderenv oncomplete100000. Main14/48/354scientificarchives and26moleculardefinitionarchives untouched, original1296running, CUDA1672stillpending at131719. Priorgoalturnprogress:newmodule/44tests/actualsource1682 andMACE1295 fullscientific acceptance;notwait/block. No newformaltraining or DFT.

- 2026-11-06T13:45:19+08:00: Substantive graph-unit adjustment fromactualcode evidence: existingexampleMolecularGCN BaseGNN constructor omittedgradient_capabilities; components.resolve_feature_spec defaultsomittedpositions/strain/ mixed toFalse andForceFieldModel rejects allthreefalse beforeexecution. Existing1682source/data-only acceptance correctlyneverconstructedGNN, soits9configs arehistoricalmetadata notruntimeproof. Addonly explicitTrue positions/strain/mixed metadata toknownlive-distanceMolecularGCN, preserveall learnedmodules/math/statekeys/constructorRNG; do notweakenframeworkcapabilitychecks orfakeconfigoverride. UpdateexampleREADME/standards explanation andaddactualSlurm f32/f64 constructor/state/RNG/directfeature equivalence versus1e19447 plusForceField FD/geometry/mixedgradient/reload checks. No localTorch. Plugin3fileprovenance changes, soexportfresh9definitionversion aftercleancommit/fullsourcegate, keeporiginal1682/a4226e26archives unchanged andonlybindnewgraphselector toindependentlyacceptednewSHA. Testsbeforecommit: ASToriginalMolecularGCN identicalafterremovingonlygradient_capabilitieskeyword, puremetadata source/graph/scope regressions, actualnumericSlurm remainsrequiredbeforefinalruntimeacceptance. Main14/48/354 untouched; no originalmodel layer/weight changes or numericaltolerance reduction.

- 2026-11-06T14:06:55+08:00: Actualprecommitgraph/capability implementationchecksPASSED:55purestdlib tests zeroerrors/failures/skips, 11newclosedgroup/fullrow/padded-valid/gzip/failprefix/CPU-as-CUDA/noSlurm/import/constructorAST controls plus original44data/matrix/scope regressions.9AST/CLIhelp/links/fences/append-onlyhistory/gitdiff passed. OriginalMolecularGCN ASTexactlyidentical to1e19447 afterremovingonlygradient_capabilities keyword: no layer/parameter/forward/math change. Corebackbone/featurecontract/engine/data/readout andoriginal graphscanner/capacity/physicalvalidator Pythonunchanged. Newpublicgraphscan supportsCPU/CUDAbutdoesnot certifycapacity; defaultcloseddefinitionstillold1682 anda changedplugin hashfailsclosed untilfreshaccepted versionrebinding.8newSlurmonly plugin tests cover f32/f64/context0-3 constructorRNG/state/directfeatures, unchangedFD/geometry/mixedpolicy andforce-only1step/standardcheckpointreload; notrunlocallyorclaimedpassed. Nextpublishcleannewsource, actualCPU8numericalcases+full100000source/9newconfigs, keepold1682proof. No localTorch/NumPy/GNN or DFT, main14/48/354scientificarchives untouched.
