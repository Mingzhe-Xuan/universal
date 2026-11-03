# ALIGNN 2.0 资源核查

## 2026-11-02 直接 irreps 张量读出候选检查计划

- 对照 e3nn 官方 CartesianTensor/ReducedTensorProducts 文档和实现入口，区分任意隐藏表示与目标张量 irreps 系数。
- 以角动量耦合递推核对通用 polar 二/三/四阶分解与 9/27/81 维计数，明确未加入指标对称或晶体空间群约束。
- 将直接读出记为候选，不擅自删除用户已确认求导路线；维数不足需张量积适配，不靠 reshape 或补零宣称完整输出。
- 检查新增文档/链接/配置与历史保留。本轮不安装 e3nn、不执行模型或张量转换运行时测试。

## 2026-11-02 张量求导读出范围修订检查计划

- 张量实现限定为求导式读出，移除空间群识别、群平均/feature mask、equality adjustment 和晶体分量硬约束的实施与验收要求。
- 明确辅助变量的物理含义、求导指标/单位和训练时梯度链；不将求导式读出错误改成普通线性多输出。
- 检查计划、索引、困难清单和 T2 交付一致；原有状态历史与 AFM 计划保持，文档格式和示例 JSON 正常。本轮不运行模型。

## 2026-11-02 等变节点 GNN 任务覆盖设计检查计划

- 接受用户新前提，不再以缺少 autograd、节点特征或边特征作为泛化障碍；检查 irreps、单位/坐标、求导范围和生成条件等实际契约。
- 核对 GMTNet 官方论文/代码，区分等变张量读出与离散空间群预处理；任务级数据/评分一致不等于实现一致。
- 修改设计中的旧数值等价/强制原任务头/原导数/边特征要求，改用节点特征主接口、可插拔任务头和同任务验收；保持仍未实施的状态。
- 检查 Markdown/JSON/相对链接、现有 AFM 计划与状态历史；不执行模型或下载数据。

## 2026-11-02 ALIGNN 下游保持一致的设计修订检查计划

- 以用户最新要求覆盖上一稿泛化方向，核对真实源码的模型 factory、配置类型、监督 forward 输出、力场 calculator 与 CSP denoiser 读出接口。
- 保留 ALIGNN 数据/schema/任务输出头/损失/训练/扩散/筛选弛豫/评测，不引入新的默认张量读出、归一化、CLI 或生成算法。
- 原 ALIGNN 作为默认 backend 与兼容基线；移除仅靠类名或字符串决定任务能力的耦合，但不能删除整个下游功能或默默改变行为。
- 文档核对 JSON 示例、引用源码路径、相对链接、上游 SHA、旧计划变更说明；现有 AFM 文件和 state.md 历史保持。

## 2026-11-02 通用 GNN 工具箱设计计划检查范围

- 仅新增 docs/plan/gnn_task_toolkit.md、更新目录索引和 agents 记录；不新增业务代码，不运行训练或远程命令。
- 内容验收：覆盖性质、逐原子、力场、张量、谱、条件生成六大任务族；区分张量形状、旋转变换、可微分几何、生成去噪接口和数据标签能力，避免声称任意 GNN 自动兼容全部任务。
- 接口验收：模型/数据插件的最小实现、结构/批次/标签/表示/预测契约、配置选择、预检查和错误处理相互一致；训练、验证、测试、生成、弛豫和评分边界明确。
- 文档验收：UTF-8、相对链接、代码块配对、示例 JSON 可解析、任务名/目录/命令一致；现有 AFM 计划不改动，state.md 已有变更历史完整保留。

## 2026-11-02 预训练目标与下游性质关系核查计划

- 查原始论文：不同 SSL 目标的下游性质比较、不同物理监督的表示比较、单源到多目标的迁移及跨 checkpoint 基准。
- 分别核对是否控制骨干/数据、冻结或微调、是否真正测试下游预测，避免把重构/CKA 等同于迁移收益或因果效应。
- 结论限定检索覆盖，不声称全面首次；提出受控预训练目标、实际模型可用性和标签/结构重叠的不同层次。
- 本轮仅文档与调研，检查编码、格式、引用和历史保留，不运行训练或评测。

## 2026-11-02 预训练表示既有主张核查计划

- 核对 CrysGNN、势能模型描述符、部分冻结微调和解耦特征回归原始摘要/方法；按是否冻结、是否蒸馏、分子或晶体、任务范围分类。
- 优先引用最贴近“冻结 GNN + 简单预测器”的原始论文，不把部分任务收益泛化为所有性质；不声称首次、不承诺发表。
- 仅文档更新，检查编码、格式、链接与历史保留；不运行模型。

## 2026-11-02 预训练晶体表示论文定位核查计划

- 核对已有冻结描述符、局部冻结微调与多任务模型工作，不将“社区不愿使用”写成已证事实，不将宽泛预训练有效视为首次贡献。
- 明确方法假设与已有结果；检验预算、下游标签、预训练重叠、外部任务和基线公平性，区分额外教师信息与迁移接口收益。
- 设计先导实验及根据结果继续/收缩/转向的标准，不承诺正结果或发表。
- 本轮仅研究文档，检查 UTF-8、格式、引用与历史保留，不运行模型。

## 2026-11-02 查询式晶体检索与 RL 核查计划

- 核对材料文本/结构检索与 RL retriever 先例；不将 RAG、普通向量检索、查询包装和 RL 混称。
- 检查查询/候选编码器、训练策略分布、集合奖励、外部评价和索引更新的对应关系；明确只训查询侧时 GNN 本体不更新。
- 对完整已知标签筛选保留数据库过滤基线，对学习方案比较监督排序和等预算候选验证；不把代理奖励当成真实物性发现。
- 本轮仅研究和文档，检查 UTF-8、格式、引用与历史保留，不运行模型。

## 2026-11-02 MatMind 具体表述核查计划

- 核对名称、版本、摘要核心措辞、三阶段目标，以及预测分支和生成分支是否从同一 SAR checkpoint 派生。
- 区分作者统一框架主张、方法实际描述和我们对最终权重共享的判断；不把文字推理监督等同于因果发现。
- 仅文档更新，检查编码、格式、引用与历史保留；不运行模型。

## 2026-11-02 Base/Instruct/RL 范式设计核查计划

- 核对 MatterSim-MT、MatterGen、晶体指令微调和 RL 后训练原始先例，避免声称“材料首次预训练后训练”。
- 明确同一模型的预测/生成/优化动作空间、每阶段目标、反馈类型及独立验收；区分回归微调、固定提示包装和真正可条件化的任务接口。
- 核对 RL 训练更新、代理奖励与独立物理验证的区别；不将样本重排、主动学习或仅梯度优化势能面直接称为 RL。
- 本轮仅文档和研究方案，不启动实现或计算；检查 UTF-8、格式、引用和历史记录保留。

## 2026-11-02 MatterSim-MT 对比核查计划

- 核对论文版本、数据规模、训练阶段、架构、监督目标、下游任务与表示评测，优先使用原文和官方仓库。
- 不将基础 MatterSim-v1 模型卡当成 MT 新功能说明；不将单个模型能力、跨任务迁移与异构多教师蒸馏混同。
- 判断优劣时明确本会话方案未实现、无对照结果；研究建议与已有论文证据分别标注。
- 本轮仅文档改动，检查 UTF-8、格式、文献链接与历史保留，不执行模型测试。

## 2026-11-02 多教师晶体蒸馏方案核查计划

- 核对多教师独立投影、关系蒸馏、CKA 的原始方法；区分通用视觉先例和晶体场景中的建议。
- 检查投影方向、维度、stop-gradient、标准化统计、损失归一化与缺失教师掩码；防止可训练目标分支塌缩和输入状态不可辨识。
- 检查原子级对应、晶胞/周期性、旋转等变通道及磁态输入条件。仅修改文档，执行 UTF-8、格式、链接和历史保留检查。

## 2026-11-02 晶体预训练模型类别扩展核查计划

- 用原始论文或官方模型目录核对模型名称、输入、预训练目标和公开模型入口；只发现论文或注册 URL 时不声称已下载权重。
- 区分性质专用训练模型与通用基础模型；区分独立物理监督和从能量/力导出的响应性质。
- 仅修改文档，检查 UTF-8、链接格式、路径和历史保留；不启动模型测试和远程计算。

## 2026-11-02 Guqq2 存储检查计划

- 核对 SSH 返回主机、文件系统挂载点、总量、已用量、可用量及使用率；区分共享文件系统剩余容量和个人配额。
- 检查 inode 和系统是否提供 quota；配额不可用时明确标注未确认。
- 本次无实现单元，仅执行轻量管理查询；检查新增记录的 UTF-8、命令与结果一致性。

实际结果：本地默认 SSH 未加载 Guqq2 别名；显式 -F 指定配置返回 Permission denied。用户调整权限后重试相同，受控提权被 sandbox_approval=false 策略拒绝。远程容量、inode、配额检查未执行，不能判为通过；未修改服务器。记录按 UTF-8 和尾随空白检查。

## 2026-11-01 存储估算核查计划

- 核实大数据集官方发布文件的 size/压缩格式；同一数据的多个镜像不重复累加。
- 区分官方文件大小、实际本地测量和工程预算，不将估算写成下载实测。
- 覆盖代码、权重、公开训练/评测数据、OQMD SQL 导入、转换缓存和训练产物；未确认标签及原始 VASP 输出单独说明。

实际结果：已核实 MPtrj 12,188,168,685 bytes，MATPES 单套两泛函 3.53/4.31 GB，WBM 必需文件约 0.1–0.3 GB，以及 OQMD 21.1 GB 压缩 SQL/约 100 GB 导入数据目录；本地代码浅克隆约 176.43 MB。未将官方仓库含重复格式/其他数据的总量计为必需空间。50–100 GB 下载、300 GB 数据处理及 1 TB 起训练空间均标为预算，未冒充全量下载实测。

2026-11-02：复核单位换算与加总通过（WBM 上述四项 0.296 GB，MATPES 3.53/4.31 GB）；四份记录 UTF-8/尾随空白检查通过。历史条目保留，当前快照更新为已完成。

## 2026-11-01 晶体表示文献调研核查计划

- 范围：论文名称、日期/版本、模型与监督目标、比较指标、实验支持的结论，以及引用链接。
- 预期：用原始论文支撑技术论断；区分统计相似性、线性/局部不可重构与实际下游互补收益；明确三类模型联合比较是否已经被覆盖。
- 仅修改研究记录，检查 UTF-8、Markdown 格式、链接与本地路径；不运行模型，不连接服务器，不要求新增单元测试。

## 2026-11-01 晶体表示调研实际核查

- 已读取 Wiley 正式论文 3.3 节，核对 PET–MAD 与 PET–MAD–DOS 的架构/数据控制和两向 GFRE/LFRE 数值；没有把它表述为融合增益实验。
- 已读取 Nature Machine Intelligence 表示对齐论文、CHGNet 原文、PNAS 自旋模型原文和 MultiMat v3 的模态/下游比较段落；引用与证据范围一致。
- CHGNet 期刊页访问失败后改读作者 arXiv；PNAS DOI 访问受限后使用 PMC 全文。不把页面访问失败推断为模型或数据不可获取。
- 文档检查：三个文件严格 UTF-8 解码、无替换字符、无尾随空格、28 个 Markdown 链接语法检查，以及状态区标题和六条历史记录保留检查均通过，最终 exit 0。首次标题断言因 PowerShell 管道传递中文常量的编码问题失败，改为 Unicode 转义后按相同要求通过。链接目标的证据内容按上文逐篇原文核对；没有声称重新访问了前序全部链接。未新增代码、未运行训练或推理，目录无 Git 元数据，未提交。

## 2026-11-01 核查计划

- 范围：论文任务表与官方代码、数据下载入口、测试划分、配置及权重的对应关系。
- 预期：每个结论有官方论文或源码依据；区分入口可见与实际下载/执行成功，不将公共数据集存在等同于论文实验可完整复现。
- 文档检查：链接、脚本路径和任务名称一致；不执行训练、推理或完整评测。
- 当前目录没有 `.git`，不进行 Git 提交。

## 2026-11-01 实际结果

- 成功 clone 并读取 ALIGNN 官方源码、Leaderboard 小文件源码、CHIPS-FF、AtomBench Git 树、作者 CSP 分支，以及 Hugging Face CSP 数据/模型 Git 对象。
- `python tmp/alignn2-audit/inspect_resources.py` 最终 exit 0：实际解析两套数据的 train/val/test JSON，计数为 847/105/103 和 6603/825/825；逐条检查晶格/坐标/元素数量与 POSCAR 字段，检查划分之间 ID 无交集，顺序 SHA256 前十位分别为 3fd288e327、5703564835。
- 首次指纹检查失败：HF 数据卡称 sorted IDs，但实际 prepare_data.py 和 prepare_alex_data.py 使用 train+val+test 的文件顺序。按这两个原始实现修正核查公式后通过，未降低验收要求；记录文档与代码的不一致。
- 成功解析 12 组 CSP 配置与 sym 指标，其 match rate/RMSD 按论文表 7 精度吻合；模型权重均仅读取 Git LFS 指针，没有下载约 30 MB/组的二进制载荷。
- AST 静态读取预训练注册表：124 项均有 URL；这仅证明入口存在，不代表已匿名下载验证。
- Leaderboard Git 树：radius/knn/knn_wide/knn_tuned 分别有 65/41/6/1 个预测 CSV zip 路径；没有将路径计数误称为已解压核对所有结果。
- 失败或未覆盖：普通 Python HTTP 被环境阻止；Figshare web 抓取失败；作者单独 csp-ablation harness 的 clone 返回 Repository not found。没有依靠这些失败证明资源不存在。
- 不执行上游脚本、模型反序列化或评测；源码中的硬编码路径按静态证据报告，不声称已跑通。
- 文档验收：四份 agents 记录均可按 UTF-8 读取，无尾随空白；evidence.json 存在。调研引用的仓库路径按已读取源码/Git 树核对，网络受限链接明确标注未验证载荷。

## 2026-11-01 方法复现范围补查

- 核查范围：区分公开原始数据来源与作者整理后的精确快照；核对 Raman/DOS/力场下载注册，以及公开 DFPT/弹性原始输出的获取与解析说明。
- 实际结果：读取 JARVIS `add61f2` 的 figshare.py，核对四类数据的注册名及下载链接；阅读官方 raw/DFPT 文档。未执行数据下载、DFT、训练或评测。
- 判定调整有来源依据：主体任务可自行整理公开数据；逐原子电荷/磁矩等未确定标签继续标记待核实，不用总量或模型预测替代真实标签。

## 2026-11-02 00:05:13 +08:00：存储检查验收计划

- 预期：SSH 成功后取得远程 df -hT、df -ih，以及可用的用户配额；区分文件系统余量和用户可用配额。若连接受阻，报告实际错误，不推测空间。
- 文档核对：保留 state 历史，连接前记录存在；命令为轻量只读操作。

## 2026-11-02 00:06:27 +08:00：存储检查实际结果

- 受控 SSH 成功连接 node42，df -hT 与 df -ih 返回完整数据；根目录可用 32G、使用率 99%，inode 使用率 5%。
- quota 不存在，lfs/mmlsquota 探测未发现命令，个人配额未确认；末尾命令探测 exit 1 为工具不存在。未执行递归目录统计或计算作业。
- state 更新前后校验原变更记录全文保留；连接前已有 gpu 用途记录。当前目录非 Git 仓库，不提交。

## 2026-11-02 00:07:33 +08:00：/home/xmz 占用统计验收计划

- 在 Slurm 作业中执行 du -x -B1 --max-depth=1 /home/xmz，包含隐藏项且不跟随符号链接；核对真实运行节点和挂载来源，确保与登录 node42 的目录对应。
- 作业成功退出，取得总字节数及一级目录占用；如有权限或扫描期间文件变动错误则明确标注局限，不把失败扫描作为完整结果。检查 docs 路径、命令和历史保留。

## 2026-11-02 晶体模型类别扩展实际核查

- 已读取 VGNN、MatTen、CrysGNN、MatterGen 官方预训练使用说明，ALIGNN 官方性质目录、OpenAlphaDiffract 模型卡、LightshowAI 模型范围、MatBERT 下载说明及 MatBind 原始摘要。
- 核对模型输入和用途；区分公开代码/文献、声明提供的预训练入口及本轮未下载验证的权重。CLOUD 期刊页访问受限，本次最终模型示例不依赖该页面的新增判断。
- 文档仅新增研究记录；执行严格 UTF-8、替换字符与尾随空白检查，核对本轮链接及既有状态历史保留。不涉及代码或模型测试。
- 本轮静态检查实际结果：state.md、test.md、update.md 的 UTF-8、替换字符和尾随空白检查，以及既有历史和主要文献链接存在性检查全部通过，exit 0。

## 2026-11-02 00:09:37 +08:00：家目录统计实际验收

- Slurm 534：JobState=COMPLETED、ExitCode=0:0、RunTime=00:00:03、NodeList=node42；日志中 findmnt 确认 /home/xmz 位于 /dev/nvme0n1p2 ext4，与前序登录检查一致。
- du 输出包含隐藏目录，stderr 为空；总 58040799232 字节。一级目录合计 58040696832 字节，不超过总占用（差值为家目录直属文件和目录自身等）。本地核算 GiB/GB 换算通过。
- sacct 不可用已按原要求改用 scontrol 验证，未降低成功退出标准。文档 UTF-8、路径与命令检查通过，原 state 变更记录全文保留；无代码修改或 Git 提交。

## 2026-11-02 多教师蒸馏方案实际核查

- 已读取 AM-RADIO 多教师投影段落、UNIC 特征统计/损失平衡段落、RKD 原文摘要、CKA 原始论文说明、晶体锚点表示方法及 e3nn irreps 文档。
- 维度和梯度人工核对：h 属于 R^d，P_k 输出 R^(d_k)，固定教师目标属于 R^(d_k)；每教师损失按有效样本和维度平均，教师不更新。关系匹配在教师专用预测空间中进行，避免要求单一距离矩阵同时等于互不一致的教师关系。
- 核对监督方向、固定训练统计、掩码、状态输入和等变通道限制；将方法建议与原论文已有实验证据分开标注。本轮未写代码、未运行训练或模型测试。
- 静态检查实际结果：三个记录文件的严格 UTF-8、替换字符、尾随空白、历史保留和主要方法链接存在性检查均通过，exit 0。

## 2026-11-02 MatterSim-MT 对比实际核查

- 已核对 v2 主文 2/4/5、S1.2 架构、S1.3 损失、S3 数据、S4 任务和代码/数据声明。35M 全量势能面标签与小规模辅助标签已区分。
- 读取官方 MatterSim README 和作者名下 MT 仓库 README/模型卡，确认不能直接用其中 v1 模型说明替代 MT 资源核实。
- 已核对本会话实际状态为方法讨论、尚无模型训练结果；最终比较不虚构优势或数值，不把铁磁限制推断为整个模型无磁性能力。
- 文档静态检查覆盖 UTF-8、替换字符、尾随空白、文献链接和历史记录；无业务代码改动、不要求模型单元测试。
- 实际静态检查：三个文件编码、替换字符、尾随空白、历史保留，以及 v2 引用与标签规模存在性检查全部通过，exit 0。

## 2026-11-02 范式设计实际核查

- 原始资料已核对：MatterSim-MT v2、MatterGen 官方说明、CrystalICL ACL 论文页、CrystalFormer-RL v2、PLaID++ v4、MatMind v1 方法部分。
- 方案逻辑核对：Base 包含能支持生成/编辑的训练；Instruct 具有输入条件和类型化输出；RL 更新生成/编辑策略。与固定头回归、外部搜索/筛选和主动学习区分。
- 未声称阶段划分或材料 RL 首创；MatMind 列为近邻。未把代理物理模型评价当成新增 DFT 验证；保留本项目不新增 DFT、所有远程计算需 Slurm 的现有约束。
- 无代码实现和模型运行；对记录执行 UTF-8、替换字符、尾随空白和引用/历史存在性检查。
- 本轮静态检查实际结果：三个文件严格 UTF-8、替换字符、尾随空白、历史记录和新增主要原始文献链接检查均通过，exit 0。

## 2026-11-02 MatMind 具体表述实际核查

- 已读取摘要、§2.1、§3.1/3.2 与 §3.4；核对 S1-Base 8B、next-token、SAR、预测双头及生成 SFT/GRPO。
- §3.2.2 和 §3.2.3 均指向 MatMind SAR；据此将训练分支图明确标为按方法描述的理解，不把未核实的最终权重共享写成事实。
- 区分原文引语、中文释义和对我们方案的研究判断；最终不复述未经审计的全局 SOTA 或因果理解主张。
- 无实现或计算；仅检查记录文件的 UTF-8、替换字符、尾随空白、历史及主要链接存在性。
- 实际静态检查结果：三个记录文件 UTF-8、替换字符、尾随空白、历史与 MatMind 原文链接检查全部通过，exit 0。

## 2026-11-02 查询式晶体检索实际核查

- 已核对 CLaSP v2 原始摘要的文本-结构检索目标和 RELER v1 的嵌入动作、RLOO 及固定索引查询适配；未把通用检索实验当作材料证据。
- 核对设计中的 score 维度一致、softmax 作用于候选动作、列表采样不重复；实际候选池策略与全库召回分别评价。
- 明确纯检索/完整 RAG、查询侧 RL/GNN 本体 RL，以及完整标签过滤/不完整或复合需求的检索之间的差别。
- 本轮无代码或模型测试，仅执行记录编码、替换字符、尾随空白、历史保留和文献链接存在性检查。
- 实际静态检查：三个文件 UTF-8、替换字符、尾随空白、历史和主要原始文献链接检查全部通过，exit 0。

## 2026-11-02 论文定位实际核查

- 已读取 MatterSim-MT v2 微调与任务段落、势能模型作描述符原始摘要、APS 解耦迁移 accepted-paper 原始摘要和特征重构原文；区分实际证明与本轮待验证假设。
- 材料 episodic 外推训练的官方摘要已定位，期刊正文抓取受限，不据此下完整新颖性结论；不把 meta-learning 或冻结特征范式声称为首创。
- 方案核对：预训练支持任务与外部测试任务隔离；保真蒸馏与迁移训练收益通过消融区分；预算包括特征提取和适配，结果包含失败边界。
- 无代码、无模型运行；记录检查覆盖编码、尾随空白、引用与既有历史保留。
- 实际静态检查结果：三个文件的 UTF-8、替换字符、尾随空白、历史和主要研究引用检查均通过，exit 0。

## 2026-11-02 既有主张核查实际结果

- 原始来源已核对：CrysGNN 摘要、2402.18433v2 方法与摘要、APS accepted-paper 原始摘要。正确区分蒸馏、冻结描述符和解耦迁移及各自任务范围。
- arXiv 2602.18054v1 HTML 返回 404，采用 APS 原文摘要；未声称阅读全文或断言资源不存在。
- 结论核对：已有研究声明不等于问题完全解决；研究意义与论文新颖性分开，候选方法及多教师增量尚无本项目实验证据。
- 本轮无实现或模型测试；检查文档 UTF-8、替换字符、尾随空白、主要原始引用和历史保留。
- 实际静态检查结果：三个文件的 UTF-8、替换字符、尾随空白、历史和本轮原始文献引用检查均通过，exit 0。

## 2026-11-02 02:02 +08:00：预训练目标-下游性质调研检查结果

- 原始来源核对通过：2022 CGCNN/MoE 的 18 源任务、19 下游任务、部分冻结策略与任务关系分析；分子 PGM 任务选择；2026 uMLIP 特征比较；SPMat 目标对照。区分期刊/预印本摘要数字，不将权重或重构解释为因果贡献。
- 本地 Python 静态检查通过：state.md、test.md、update.md 严格 UTF-8、无替换字符、无行尾空白；state.md 保留 01:37、01:45、01:55 历史与新增完成记录；update.md 含主要文献 DOI/URL。
- 文档调研未修改代码、配置或脚本；未运行模型测试，无 Git 提交。

## 2026-11-02 AFM 三路线迁移定位核查计划

- 区分已有一般迁移方法、单一 AFM 的下游迁移、多 AFM 表示比较，以及专用/多任务/多专用融合三路线直接比较。
- 核对 MatterSim-MT 训练阶段；不将任务专用微调自动称作从零预训练，不将混合势能数据域等同于不同物理监督。
- 将多任务干扰作为待检验假设；现成模型排名不能独立证明监督任务的因果效应，冻结探针与微调结论分别报告。
- 仅文献和文档更新，检查 UTF-8、格式、链接及历史，不运行模型或服务器操作。

## 2026-11-02 AFM 三路线定位核查实际结果

- 原始论文核对：HackNIP 明确比较 ORB/EquiformerV2/MACE 的固定表示，DPA-2 的 ST/MT 主要对应 PES 数据域；MatterSim-MT 为 PES 预训练加额外性质微调。未将这些局部证据扩大为完整覆盖三路线比较。
- 结论检查：区分 AFM 迁移已被研究和多物理专用/多任务/融合系统比较尚不充分；不预设多任务干扰，不将现成 checkpoint 性能差异写成因果证明。
- Python 静态检查实际通过：state.md、test.md、update.md 严格 UTF-8、无替换字符和行尾空白；历史 01:55/02:01 与本轮 02:08/02:12 记录保留，主要原始来源标识存在。
- 本轮无代码修改、模型运行或远程操作，无 Git 提交。

## AFM 研究计划落地检查计划

- 本单元仅新增 docs/plan/README.md 和 afm_transferability.md，并更新 agents 记录；不新增实现模块，不运行模型或服务器命令。
- 检查三路线、研究问题、已有工作边界、未见性质与同性质适配区分、冻结/微调分列、数据/容量/预算公平性和任务干扰归因要求是否完整。
- 检查 UTF-8、替换字符、行尾空白、Markdown 相对链接目标与引用 URL 格式；确认 state.md 原有变更记录完整保留。

## AFM 研究计划落地实际检查结果

- Python 静态检查通过：docs/plan 的两份新文档和三份 agents 记录均为严格 UTF-8，无替换字符、行尾空白或不配对代码块。
- README 的研究计划链接和 agents 状态链接目标存在；计划中六个原始文献的 HTTPS URL 格式通过，沿用前序已核查来源，本轮未重新开展网络可达性测试。
- 内容检查通过：三路线、RQ1–RQ4、MatterSim-MT/HackNIP/DPA-2/JMP 及新颖性范围表述存在；state.md 原有 01:37、01:55、02:01、02:08、02:12 时间记录保留。
- 人工核对完成：同性质与跨性质、冻结与微调、源选择与测试集隔离、容量/预算公平性及干扰归因已分开描述。新增文件低于 10 MiB。
- 本轮仅文档更新，无训练、模型评测、远程连接或 Git 提交。

## AFM 存储预算检查计划

- 验证 N×M×L×D×bytes 的晶体级特征公式，以及原子级平均原子数、FP16/FP32 的倍率。
- 检查 checkpoint 权重与 Adam 优化器状态估算的适用范围；区分 GB/TB 与 GiB/TiB。
- 给出情景预算而非实际资源大小，避免声称已知所有 AFM 权重尺寸或服务器可用空间。
- 检查新增计划内容、记录的 UTF-8/格式与原有历史；本轮不下载或运行模型，不连接服务器。

## AFM 存储预算实际检查结果

- 本地短时算术检查通过：FP32/FP16 特征、平均原子数倍率、8 层 1024 维缓存、模型纯权重和 Adam checkpoint 算式均与计划一致；十进制 GB 和二进制 GiB 分别转换。
- 计划文档的 UTF-8、替换字符、尾随空白、代码块配对及关键数值检查通过；原有文献内容未改动。
- 情景预算明确标为假设；未以历史占用推断可用配额，未声称已知候选 AFM 实际权重大小。
- 仅文档更新，无代码提交、模型测试或远程操作。

## 通用 GNN 工具箱设计计划实际检查结果

- check_plan.py 最终 exit 0：UTF-8、替换字符、行尾空白、代码块配对、JSON 配置示例、相对链接及六类任务/接口覆盖全部通过。
- state.md 历史以基线原文完整保留后追加；afm_transferability.md SHA256 与修改前一致。
- 首次内联检查因 PowerShell 对代码围栏反引号的转义导致断言失败，改为独立临时 Python 检查文件后通过；没有放宽文档验收要求。
- 人工核对：插件边界、模型原生输入、物理能力门禁、生成原始/后处理评分和分阶段交付相互一致；所有示例命令标记为拟议接口。
- 本轮仅文档更新，不存在可运行工具箱或模型测试结果，无 Git 提交。

## ALIGNN 最小解耦计划修订实际检查结果

- check_alignn_plan.py exit 0：UTF-8/尾随空白/代码块/相对链接通过，新增 backbone JSON 片段可解析，已注明需合并原完整配置。
- 已对照 11 个实际源码文件和固定 SHA，监督输出键 out/additional/grad/stresses/atomwise_pred 与 CSP 输出语义一致；取消新 CLI、默认新张量头及重建下游任务的方案。
- 既有 AFM 计划 SHA256 不变；state.md 原变更记录完整保留并追加本次范围调整。
- 人工核对：保留/替换清单、兼容要求、checkpoint 和 S0–S5 行为回归相互一致；本轮仅设计，尚未实际运行模型回归测试。

## 等变节点 GNN 任务覆盖设计实际检查结果

- GMTNet 官方 gmtnet.py/data.py 与原始论文已读取，固定结构投影和动态几何求导边界有直接源码依据。
- check_equivariant_plan.py exit 0：UTF-8、尾随空白、代码块、相对链接与 JSON 示例通过；节点主接口、边可选、用户张量读出、T0–T5 和旧严格等价要求撤销已核对。
- state.md 历史保留后追加，AFM 研究计划哈希不变；不把先前过期计划的检查条件继续作为新范围要求。
- 本轮仅文档，无模型运行、梯度实测、数据下载、服务器连接或 Git 提交。

## 张量求导读出修订实际检查结果

- check_derivative_plan.py exit 0：格式、JSON、相对链接、三类响应/Jacobian 定义、训练梯度链及取消晶体约束的范围一致。
- 对照 GMTNet 官方 transformer.py 与原文 §3.3；AFM 文档哈希及已有状态历史保持。
- 仅文档验收，无模型/梯度实测或业务代码修改。

## 直接 Cartesian 读出候选实际检查结果

- 原文档格式/JSON/链接检查通过；候选章节未删除既有求导方案。
- 以角动量张量积递推得到二阶 {0:1,1:1,2:1}、三阶 {0:1,1:3,2:2,3:1}、四阶 {0:3,1:6,2:6,3:3,4:1}，按 2l+1 求和为 9/27/81，通过 3^rank 校验。
- 确认原状态历史前缀和 AFM 计划哈希不变；本轮仅算术/文档检查，未运行 e3nn 或模型。

## 输出格式驱动设计检查计划

- 核对 scope、值类型、表示、采样轴、构造操作与工作流边界，不能仅凭 shape 推断物理语义。
- 核对标量/分类、节点/结构张量、谱和结构生成均有映射；力场求导关系与直接张量输出可分别配置。
- 检查 UTF-8、代码围栏、JSON 配置、相对链接、目录索引及章节一致性；保留既有状态变更历史和 AFM 计划哈希。
- 仅设计文档，不执行模型、下载数据或远程操作。


## 输出格式驱动设计实际检查结果

- check_output_format_plan.py exit 0：UTF-8、尾随空白、围栏、相对链接、JSON 与六类格式/操作/工作流覆盖通过。
- 已人工核对 scalar/vector/rank-r 共用工厂、谱附加轴、结构组合、坐标点与向量、晶格与材料张量的区别；direct/derivative 及 loss/metric 显式配置，不依赖性质名分支。
- e3nn CartesianTensor 与 ASE get_cell 官方文档已核对；已有状态变更记录完整保留，AFM 计划 SHA256 不变。
- 只验收设计文档，未实现/运行读出或训练，不以文档检查声称模型功能通过。


## 性质库设计检查计划

- 核对性质目录可展开为通用 OutputSpec/构造配置，不按性质名称添加核心分支。
- 区分性质定义、数据绑定、工作流；区分直接/求导定义以及目录登记与数据/评测就绪。
- 检查格式、JSON/相对链接、模块职责和示例一致性，保留状态历史及 AFM 文档哈希；不运行模型。


## 性质库设计实际检查结果

- check_property_catalog_plan.py exit 0，包含既有格式/JSON/链接检查及新性质目录/绑定/工作流、构造方式和版本记录覆盖检查。
- 已核对性质目录可绕过、已有算子下新增条目无需核心分支、新数学操作仍需插件；不将登记状态当作数据或精度就绪。
- 本轮修改前状态历史完整保留，AFM 计划 SHA256 不变；无模型运行或 Git 提交。


## 等变 backbone 候选核查计划

- 读取原始论文/官方仓库或文档，核对节点/边表示、阶数与 SO(3)/O(3)、PBC 以及权重接口边界。
- 不以架构等变推断最终输出仍含高阶特征，不将架构可适配等同于已有端到端支持。
- 检查计划与引用、UTF-8/JSON/路径及既有历史和 AFM 文档保留；仅文档，不实测模型或梯度。


## 等变 backbone 候选实际核查结果

- 已读取 MACE models.py/描述符文档、NequIP 构造器、SchNetPack PaiNN、SevenNet 官方说明、UMA escn_md.py、EquiformerV2 输出/旋转源码、TensorNet forward 与盒约束、Allegro 构造器和 EGNN 作者示例。
- 人工核对取层、表示与几何梯度边界；明确原始 EquiformerV2 的旋转 detach 不满足当前全过程可微前提，不将其泛化为架构本身不可适配。
- check_backbones_plan.py exit 0：含既有格式/JSON/路径、性质库和当前状态历史/AFM 哈希保留检查；候选内容与实现前验证范围一致。
- 这是官方资料/源码与文档静态核查，无模型输出、性能或梯度实测，无 Git 提交。


## 不变/等变 backbone 统一设计检查计划

- 核对首批模型和 Equiformer/EquiformerV2 版本区分、通用 BackboneAdapter 与标量表示规范。
- 核对不变节点特征的标量直接读出、能量坐标/应变求导、几何方向构造，以及无法只从不变特征恢复各向异性信息的边界。
- 检查任务矩阵/阶段/索引/示例一致性、格式/链接/JSON 及本轮历史与 AFM 文档保留；仅文档，无模型实测。


## 不变/等变统一设计实际检查结果

- check_mixed_backbones_plan.py exit 0：格式、JSON、相对链接、性质库、候选范围、本轮状态历史和 AFM 哈希检查均通过。
- 人工核对首批四类模型、BackboneAdapter、Cx0e、native/geometry、向量/张量/力场/生成映射与 T0–T2 验收一致；明确纯标量不能自行补出 l>0。
- 已读取本地固定快照 ALIGNN pooling 前节点特征和坐标/角度求导逻辑，并核对原版 Equiformer 作者表示实现，V2 限制未泛化到原版。
- 仅文档设计检查，无网络下载、模型运行、旋转/梯度实测或 Git 提交。


## CGCNN/MEGNet 范围补充检查计划

- 核对两模型逐节点不变特征提取、CGCNN 图输入与 MEGNet 全局状态/实现后端；不把离线距离数据当可微几何输入。
- 同步首批六类模型、统一读出、T0/T1 验收和索引；检查 UTF-8/JSON/相对链接、状态历史与 AFM 计划哈希。
- 仅架构与文档检查，无依赖安装、checkpoint 转换或模型运行。


## CGCNN/MEGNet 范围补充实际检查结果

- 已读取 CGCNN 作者 model.py/data.py、MEGNet 原 TensorFlow 实现及 MatGL Torch/PyG 实现；节点 pooling 前位置、可选 state 与 NumPy 距离处理边界有源码依据。
- mixed-backbone 文档检查更新为当前六类范围，保留原格式/JSON/路径/表示/历史验收，并新增 CGCNN/MEGNet 字段核对；脚本 exit 0。旧四类数量断言按用户范围变化更新，未降低功能验收要求。
- 本轮状态历史保留，AFM 文档 SHA256 不变；首批名单、T0–T2、模块与索引一致，已注明未安装/转换/实跑模型。


## 响应性质默认求导读出检查计划

- 核对性质库响应条目默认 derivative、响应源/辅助变量/参考点/阶数和依赖展开；直接读出仅显式覆盖，无能力时不得静默回退。
- 同步张量章节、任务矩阵、默认 JSON、模块与验收；解析配置并核对弹性响应 source/wrt 和每样本 Jacobian，保留无晶体对称约束及独立响应头范围。
- 文档静态检查与已有历史/AFM 哈希保留；无模型梯度实测。


## 响应默认求导实际检查结果

- mixed-backbone 文档检查 exit 0；默认 JSON 从 direct 改 derivative 后，同步核对 source/wrt 对应已声明响应和辅助变量、order=1、per_sample、零参考点、requires_grad 与 ij+kl=ijkl 指标依赖。
- 已核对 default_construction=derivative、response_spec、direct 显式覆盖和禁止静默回退贯穿性质库/章节/示例/T2；六类模型范围和独立响应头、无晶体空间群约束保持。
- 格式/JSON/相对链接通过，本轮状态历史完整保留、AFM 计划哈希不变；仅设计文档，未实测 Jacobian 或参数/几何梯度。


## 统一特征适配层设计检查计划

- 核对六类模型取层映射、节点/批次/可选全局状态、基底/归一化与 SO(3)/O(3) 边界；读出入口不依赖模型名或原始维度。
- 核对不变特征几何提升、不同通道张量积、缺失类型路径/高阶类型覆盖与固定输出规格；符号维度/可达性检查不冒充数值表达能力证明。
- 核对 native/geometry 配置前移到适配层、响应辅助变量在读出端注入、默认 Jacobian 与参数/几何梯度链；统一代码与共享权重的区别写明。
- 检查新文档/索引/主计划/JSON/路径、历史及 AFM 文档哈希；不实现业务代码或运行模型。


## 统一特征适配层实际检查结果

- check_unified_adapter_plan.py exit 0：包含 UTF-8/围栏/空白、JSON/相对链接、六类模型/响应默认与状态历史/AFM 哈希保留检查；新详细设计链接有效，native/geometry 配置已从响应读出移至 feature_adapter。
- 算术/符号检查：profile 维度为 568；通用 rank 2/3/4 的分解维度为 9/27/81，profile 含所需类型和目标 multiplicity；自然 parity 种子一轮未达 0o、两轮可达，公共 profile 类型可达。
- 首次文本检查发现详细稿未显式命名共享权重，已补齐该边界后通过；未降低验收。符号可达性不代表数值非零、表达完备或训练效果。
- 人工核对节点/全局状态、SO(3)/O(3)、不同通道耦合、辅助变量注入与缓存梯度边界；未来实现测试与本轮静态结果已区分。
- 未安装或运行 e3nn/模型，未实测旋转或梯度，无业务代码或 Git 提交。


## ALIGNN 风格不变路线检查计划

- 对照本地固定源码的 pooling/MLP、force 梯度和 tensor 示例，区分直接分量回归与响应求导。
- 补充可选不变轻量路径，说明统一 API、固定坐标分量与严格变换保证的边界；不静默撤销默认求导或把 A(H)q 的 Jacobian 视为新物理约束。
- 文档/JSON/路径与旧方案并存一致性、状态历史及 AFM 哈希检查；无模型运行。


## ALIGNN 风格不变路线实际检查结果

- 已读取固定快照 tensor README/config：output_features 配置固定分量，calculate_gradient=false；与 pooling/MLP 及力场几何求导代码分别核对。
- 文档检查 exit 0，新增 invariant_alignn、ScalarAdapter、fixed_frame_components、construction/transformation_guarantee、线性响应 Jacobian 等价性与可选几何提升边界检查通过。
- 原完整等变 profile/示例配置及符号检查继续通过；两种模式显式区分，默认响应求导未撤销。
- UTF-8/格式/JSON/相对路径、本轮状态历史及 AFM 哈希通过；无模型输出、梯度或性能实测。


## 框架设计清晰度审查计划

- 核对统一 API / 共同等变 profile 两种路线表述、hybrid 模式默认范围及 JSON 的路线声明，不推断用户已选择某一全局默认。
- 核对按声明变换保证验收：fixed_frame_components 不声称一般张量等变，几何求导力/应力及 equivariant 输出仍检查变换规则。
- 列出已确认架构和实现前需冻结的接口/性质/数据/版本/生成配方，保持任务覆盖目标与未实测状态分开。
- 执行文档/配置/路径与历史/AFM 哈希检查，无模型测试。


## 框架设计清晰度实际检查结果

- check_unified_adapter_plan.py exit 0，新增共同等变路线 JSON 显式声明、无全局 hybrid 默认、实施边界/待冻结规格及按输出声明验收核对；原文档/符号检查继续通过。
- 已人工核对两条路线无静默回退、两类响应均默认 derivative；fixed_frame_components 不冒称旋转等变，能量求导与等变输出仍按契约测试变换。
- 格式/JSON/相对链接通过，状态变更历史与 AFM 哈希保留；无业务代码、模型能力/速度/精度或梯度实测。


## 生成模型适配说明检查计划

- 核对固定组成状态、当前带噪几何重算与条件注入位置，区分等变向量读出和不变节点/几何权重读出，无 backbone 边特征要求。
- 核对坐标 score/噪声和晶格预测接口、求导响应规则不外推生成；按 r=fL 区分向量与协向量变换。
- 将已定适配链、作者配方候选与未冻结参数分列，检查文档/相对链接/JSON、原历史和 AFM 哈希；无模型或采样实测。


## 生成适配说明实际检查结果

- 文档检查 exit 0：新 §7.1–7.6、统一 GenerationPrediction/target_spec、条件注入、直接去噪与响应求导边界，以及原配置/链接/表示检查通过。
- 对照作者固定快照 denoiser/diffusion：坐标头为标量权重聚合周期分数位移，晶格头输出六维，时间条件进入节点；wrapped-normal 坐标目标为尺度化 score。节点替代边隐特征属于本框架拟议适配，未宣称原实现行为相同。
- 非正交 L 的纯算术检查保持 score 与位移的功配对：s_r·delta_r=s_f·delta_f；错误的同向矩阵变换被该例区分。仅公式检查，不是模型梯度/采样实测。
- 本轮状态历史完整保留，AFM 文档哈希不变；无模型运行、依赖安装或远程操作。


## 实现单元 U0：公共类型、PBC 几何与任务规格测试计划

- 数据/批次：原子对应、单位/标签 mask、PBC 整数镜像、批次无串联；真实标签与合成测试标签明确分开。
- 几何：非正交晶胞、多周期镜像、旋转/平移/置换；距离/方向的坐标和应变梯度及有限差分。
- 规格：性质目录与响应 source/wrt/默认 derivative、张量表示/单位、数据绑定和无效配置报错。
- 集成最终要求：六模型 × 目标任务，10 个真实结构的训练/推理/checkpoint 重载；输出有限、loss/参数更新、所需梯度及前后预测一致。10 结构仅验通路，不声称泛化精度。
- 训练/推理/评测在服务器 Slurm 执行；本地可执行静态检查和轻量配置测试。


## 2026-11-02 14:23:24 +08:00：移除当前工作区 Git 的验收计划

- 删除前核对绝对目标 E:\课业\课题组\universal\.git 为根目录直接子目录且非链接；记录根目录其他条目及直属文件 SHA256。
- 仅删除该 .git；预期目标不存在、其他根目录条目保留，直属项目文件哈希不变；不递归处理嵌套仓库、不创建新仓库。

- 实际结果：删除目标绝对路径验证通过；.git 已不存在，其余根目录条目保留，直属文件 SHA256 一致；原 state 历史保留。未重新初始化、未修改嵌套仓库，无需单元测试。

## 2026-11-02 14:25:15 +08:00：删除子目录 Git 的验收计划

- 删除前遍历工作区（包括隐藏项），不跟随目录链接；核对每个 .git 的绝对路径位于 E:\课业\课题组\universal 内，且目标非链接。
- 预期移除 10 个 .git；重新扫描后目标数量为 0；非 Git 文件路径、大小、最后修改时间及其他目录保留。仅操作元数据，不新建 Git 仓库。

- 实际结果：10 个目标路径及非链接验证通过；删除后全工作区 .git 数量为 0，876 个非 Git 文件路径、大小和修改时间一致，其他目录保留；state 原历史完整保留。无需单元测试，未创建新仓库。

## 用户提权与服务器 clone 后的检查结果

- 受控提权 SSH -G 正确加载 Guqq2，工作连接成功；普通沙箱仍拒读配置，后续连接沿受控提权路径。
- 现有 SOCKS 端到端 GitHub HTTP 200，未重启代理。
- 服务器 /home/xmz/universal 首先 git pull --ff-only 成功，origin 与本地一致；完整 HEAD 与本地匹配，远程 git status --short 为空。
- 当前目标 paused，本轮无训练/推理/环境安装或服务器源码编辑，未新建需清理的代理持有会话。


## U0 实现单元测试计划（恢复后有效）

- 验证结构/标签/单位、批次原子映射、非正交小晶胞的完整 cutoff 镜像与无串联。
- 检查坐标、共同应变的可微路径与有限差分；测试空邻居、非法晶胞、不同 mask 和性质默认。
- 只将单元解析结构用于接口验收；10 个真实结构训练/推理矩阵另列。显著计算与训练/推理在 Slurm 中运行。


## U1/U3 实现单元测试计划

- 三类不变模型逐节点输出、真实消息传递/全局/线图路径、批次隔离和条件参数连接；无边隐特征输出前提。
- 公共适配/响应：不变分量与等变表示两路线；二/三/四阶 Jacobian 的参数链、旋转/反演与几何梯度，用小解析标签仅做单元测试。
- E/F/S：共同应变、力符号和应力单位、损失更新参数；checkpoint 重载与明确的目标/归一化 metadata。

## 2026-11-02 15:18:20 +0800：基础与响应检查实际结果

- pytest tests/test_geometry.py tests/test_data.py tests/test_backbones.py：9 passed；覆盖周期自镜像、多镜像、非正交坐标/应变梯度、数据绑定及 CGCNN/MEGNet/ALIGNN 条件梯度。
- pytest tests/test_readouts.py：4 passed；二/三/四阶 Jacobian 的节点/参数反传、eval 一致，以及等变二阶响应的两轴旋转变换。仅解析单元检查，不代表真实数据训练/推理通过。
- Linux Torch CPU wheel SHA256=35a9e78b7e4096968b54c1a198687b981569c50ae93e661aa430f9fd208da102，与下载源记录一致。

## 2026-11-02 15:22:11 +08:00：U2 官方等变骨干及 E/F/S 测试计划

- 分别在 MACE 与 NequIP 环境运行指定真实后端，缺少包应失败；检查节点 irreps、旋转与反演、条件和坐标梯度、二阶参数梯度，不使用不变后端替代。
- E/F/S 使用解析结构检查能量对坐标及共同应变的有限差分、符号/单位、力与应力损失的 backbone 参数梯度；不声称真实数据验收。
- 先在本地执行小型 Equiformer/力场单元，官方后端和完整测试在 Slurm 执行。

## 2026-11-02 15:30:53 +08:00：U4 固定组成生成测试计划

- 检查周期 wrapped-normal score 与 log 概率有限差分一致，覆盖周期边界及小噪声。
- 晶格采用 Gram 的 Cholesky 因子规范化，正对角取 log、下三角剪切取无量纲比值；检查往返保持 Gram、体积和全局旋转等价，避免 log-SPD 的重复特征值导数问题。
- 检查条件节点输入、坐标/晶格两头损失向 backbone 反传、周期与固定组成采样契约；真实 10 结构训练及 checkpoint 重载在 Slurm 验收。

- 2026-11-02 15:32:00 +08:00：U2/EFS 本地解析实际结果：Equiformer 与有限差分测试 2 passed；MACE 官方模块指定运行 1 passed（约67秒），旋转/反演、坐标/条件和二阶参数梯度均通过。尚无服务器训练验收。

## 2026-11-02 15:48:44 +0800：U2/U4 与命令检查实际结果

- 默认完整 pytest：18 passed（几何/数据/三类不变骨干/Equiformer/二至四阶响应/力应力有限差分/生成数学与采样契约）。另指定 MACE 官方模块测试 1 passed。无训练执行或泛化结论。
- compileall src/tests 通过；显式 PYTHONPATH=src 的 CLI --help 显示 train/infer；git diff --check 的 README 尾空行已修正后通过。

- 2026-11-02 15:54:43 +08:00：Guqq2 Slurm535（90989f9）COMPLETED，ExitCode0:0，13 passed in3.97s，stderr为空。新提交65badd5已pull，但NequIP依赖下载在torchmetrics983kB处被代理中断；未提交NequIP作业，不记通过。

## 2026-11-02 16:00:03 +08:00：U0 数据约定与几何性能补充计划

- GMTNet 原始张量采用 VASP Voigt 顺序xx,yy,zz,xy,yz,zx，新增显式voigt_order绑定并检验xy与yz不混淆；kbar到GPa仅在绑定显式乘0.1。
- 将完整周期镜像拓扑枚举向量化、分块控制内存；仍保留所有cutoff镜像，使用既有小晶胞镜像数、周期重包裹和坐标/应变有限差分检查确保数值语义不变。
- 真实数据整理保留来源URL、原文件SHA256、索引和标签定义；只选十个有限标签及有限原子数真实结构，不制造或补零标签。

## 2026-11-02 16:06:01 +08:00：真实小数据与矩阵调度验收计划

- 检查11组各10个不同几何结构、目标shape/有限标签、单位绑定与来源SHA。分类保持5+5，压电选择非零真实标签。仅轻量读取/整理约20MB对象，实测整理不足2秒，训练/批量评测在Slurm。
- 矩阵准备须产生模型×任务唯一配置；MACE通过独立Python解释器运行。每格独立报告，失败不阻断其他格，汇总显式保留缺数据项，不以部分通过判完整。

## 2026-11-02 16:07:06 +0800：数据与几何补充实际结果

- 周期拓扑分块向量化、VASP Voigt绑定后默认全套19 passed；原镜像计数、重包裹、有限差分均通过。
- 真实11个cohort各10个不同几何，所有目标绑定/shape/有限标签检查通过；来源URL、SHA、记录序号保存到ignored数据JSON。整理脚本约2秒，非训练评测。
- 矩阵prepare产生66个唯一配置；summarize正确显示0通过/0失败/66待运行，并单列forcefield/Born/Raman缺数据项。未运行的矩阵不判通过。

## 2026-11-02 16:10:56 +08:00：力场外部高阶几何梯度计划

- 当调用者传入requires_grad坐标时保留该输入计算图；create_graph=True下力对原输入的Jacobian应有限且非零，满足声子/响应用途。无梯度输入仍可正常推理。原能量力应力有限差分和参数反传测试继续通过。

- 2026-11-02 16:18:31 +08:00：力场补充2项测试通过：既有力/应力有限差分和参数链保留，新增force对外部requires_grad坐标的非零有限Jacobian与总力为零检查通过。compileall及diff检查通过。

## 2026-11-02 16:55:57 +0800：六模型首轮真实训练/推理实际结果

- Slurm539四模型44格、583 NequIP11格、595 MACE11格：66/66逐格report passed；每格10真实结构、30epoch、参数/梯度/loss和checkpoint重载检查通过，生成含随机初态采样。源码70e5bb0，不把当前HEAD当作运行版本。
- Slurm538官方NequIP/Equiformer等20项解析检查通过；594 MACE/力场/响应6项通过。已有535 13项通过。
- SFTP reget续传后本地gzip归档解包/路径边界/66格索引校验通过。控制器只保留2个COMPLETED，64个旧记录已清理；逐格原jobID和日志保留，不虚构状态。
- 真实EFS/Born/Raman及派生流程仍pending，不把小集合执行验收当泛化或完整目标通过。

## 2026-11-02 17:02:17 +08:00：统一几何提升的非极性分量覆盖计划

- 补充中心反演但允许轴向分量的环境：极向一阶矩必须为零，Born二阶响应的反对称分量仍可非零。现有仅用极向量叉积的轴向路径在此退化，新增独立四极矩耦合。
- 对非极性D2d环境检查极向一阶矩为零时可产生允许的2o分量（用于三阶响应），并保留旋转/反演及参数/几何梯度。
- 新几何基底需版本化，旧66格checkpoint按旧基底加载、保持输出一致；新训练显式记录新版，不以变更后的源码冒充旧运行证据。

## 2026-11-02 17:23:12 +08:00：原始DFPT匹配数据整理计划

- 原始Figshare ZIP必须与已公开清单SHA一致；从同一vasprun.xml读取几何、原始force/free_energy、ASE应力及Born/电子介电张量，不从其他结构拼接，不补造缺失标签。
- ASE官方DFPT小XML用于解析接口和应力转换单元检查；真实14档的批量解析/十结构选择通过Slurm执行。Born保持原始分量，不施加ASR/空间群投影。
- 声明E/F/S监督使用VASP电子free_energy，ASE tensile-positive stress乘160.21766208转GPa；标签shape/有限性和唯一几何必须通过。

## 2026-11-02 17:28:17 +0800：基底v2与DFPT解析检查实际结果

- 非极性/中心反演轴向Born、D2d允许2o、旋转/反演、几何梯度、旧/新checkpoint格式共6项通过；修改后的全套默认26 passed。随后checkpoint2项在兼容guard修改后再次通过。
- ASE官方DFPT XML的几何/力/应力/Born匹配解析单元1项通过。14份真实原档全部与公开清单SHA256一致；批量XML整理尚未执行，将交Slurm。
- compileall、TOML/verify命令和diff检查通过；README尾空行已修正。下一步在服务器回放旧66份checkpoint及运行真实DFPT批处理，不用解析单元替代训练验收。

## 2026-11-02 17:47:00 +0800??VASP?????????????

- Slurm674???0/10?13????ASE????epsilon?????1???XML???????????????????ZIP??????3x3 epsilon??????????
- ASE??XML???epsilon?dielectric_dft???????????epsilon????XML???????????????????????????????????????

- 2026-11-02 17:47:49 +0800：旧/新电子介电XML标签解析2项通过；compileall/diff检查通过。服务器新版core/NequIP 28项、MACE 27项解析检查均通过；旧66个实际checkpoint全部回放匹配原预测，未重训或覆盖旧报告。

## 2026-11-02 18:00:02 +08:00：calculator/模拟/谱学实现计划

- ASE接口检查energy eV、forces eV/angstrom、stress GPa到ASE eV/angstrom^3转换；坐标更新必须触发重新计算。
- 解析平移不变双原子谐势核对Hessian、质量加权、零平移模及频率单位；检查弛豫/短MD有限输出和真实模型调用，不以合成势替代真实十结构验收。
- 光谱用正常模/Born/介电导数构造，记录Gamma近似、原始虚频、正频选择、展宽/网格/单位；不把虚频取绝对值伪装稳定。真实十结构链通过Slurm。
- CRD完整原始Raman张量与频率用于真实曲线标签；不以HF稀疏峰文本代替完整光谱。

## 2026-11-02 18:24 +0800：模拟与扩展入口检查

- 解析谐振双原子验证ASE能/力/应力单位、坐标缓存失效、FIRE和短MD，Hessian质量加权/频率单位/平移零模及Born选择定则；Raman旋转不变、虚频剔除、KK主值积分解析解。3项实际通过。
- 自定义dataset目录的相对导入/dataclass、自定义三分类性质按kind选择损失及backbone梯度1项实际通过。此前已记录workflow计划，但该插件实现单元未先补独立测试计划；补记范围并以实际检查验收，不倒填时间。
- 提交前检查全套默认单元、compileall、TOML/路径/命令与diff；真实十结构Raman/光学训练及六骨干模拟继续Slurm验收，不以解析单元替代。

- 2026-11-02T18:16:41.810936+08:00：实际全套默认32 passed；compileall与git diff --check通过。新接口测试覆盖单位/缓存/解析力学/主值积分及目录插件；真实Raman/光学和模拟待Slurm。

- 2026-11-02T18:27:12.314952+08:00：下一文档/示例单元：补齐可运行标量、EFS、张量、谱配置并修正生成数据路径。计划逐一JSON解析、结构文件路径/目标绑定和文档链接检查；不因文档再重复训练。

- 2026-11-02T18:29:01.681566+08:00：计划汇总验收证据：读取实际矩阵/report（不可从配置推断通过），要求六模型各16任务和六模型各10结构完整模拟记录、有限且非平凡显微图；测试缺report/失败/错误结构数不得通过，并检查所有本地归档路径和源版本。

- 2026-11-02T18:31:58.278463+08:00：703因CRD部分条目张量列表短于3N而正确拒绝。接下来严格筛选同档中频率和张量槽均为3N且有实际张量的10条，不填充/推测模式索引；保留原失败与筛选剔除清单。计划Slurm重跑实际整理，并新增不匹配模式数拒绝检查。

- 2026-11-02T18:35:43.907268+08:00：依赖兼容修复单元：abTEM1.0.8/Py310 Self导入失败。计划换官方1.0.6、验证其依赖/API签名，先Slurm单模型十结构再六模型完整流程；保留706失败日志。Raman/光学707已各整理10条，子数组711已提交。

- 2026-11-02T18:37:15.642364+08:00：证据审计/CRD槽数拒绝2项通过，compileall、CLI help、5份JSON配置/TOML及diff检查通过；abTEM1.0.6官方wheel无typing.Self导入且API签名覆盖使用参数，实际模拟仍需Slurm pilot。

- 2026-11-02T18:39:56.601886+08:00：真实CRD v2原始十条本地/服务器SHA一致2ace32d8c9c2fb1f9ef2e425c21092273dd44ab1a1e5badc4c749100aa801358；707 Raman与光学各10条整理成功，711六模型×两谱12/12训练/重载推理通过，pending_data为空。abTEM1.0.6两任务前缀安装成功，725模拟pilot运行中。

- 2026-11-02T18:52:18.363550+08:00：最终默认全套34 passed；725 CGCNN、726其余五模型各10结构模拟通过。服务器collect_evidence实际96训练格+6完整工作流passed，缺失/失败0；2051712字节归档SHA与本地一致，310文件路径安全解包，本地独立审计再次96+6通过，60张STEM数组有限且非恒定。新增5份同源cohort与manifest已复制回本地，原11文件SHA逐一一致。

- 2026-11-02T18:53:45.467005+08:00：最终文档检查：15条本地链接、16数据集路径及SHA、60图数量、TOML、git diff --check全部通过。仅文档变更，无需重复模型测试。

- 2026-11-02T18:55:48.356791+08:00：最终清理检查通过：两自有HTTP监听释放；关停已确认专用代理后，既有远端工作连接实际确认1080释放并exit0，最终服务器HEAD71de59f。收尾仅状态/操作日志文档，diff/格式检查通过。

## 2026-11-02T20:21:06.407804+08:00：文档约定CLI实现前测试计划

- 配置：JSON/YAML safe_load、拒绝非映射/危险标签，CLI模型/数据/任务覆盖顺序；未知/冲突参数及时报错，推理不允许伪装checkpoint模型/任务。
- 运行时：日志、权重、结果分别落指定路径；完整checkpoint恢复Adam/epoch/随机状态，分段续训与连续训练参数一致；旧权重仅暖启动时明确记录。生成恢复同一噪声样本语义。
- 集成：真实参数解析而非mock，训练→续训→推理可重载且输出一致，旧子命令兼容；旧基底版本保持。先本地针对性单元，再Slurm真实ALIGNN十结构带隙train/resume/infer链，所有服务器计算走Slurm。
- 文档：示例路径、参数及JSON/YAML、help、diff检查；每次提交前记录实际结果。

- 2026-11-02T20:34:59.551057+08:00：首轮CLI/旧checkpoint针对检查5 passed；新增生成续训用例首次因测试配置sampling.steps=1触发现有至少2噪声级校验（非实现回归），已修正为有效steps=2，保持参数完全一致的续训判据后重跑。

- 2026-11-02T20:39:40.893380+08:00：本地全套38 passed（新增CUDA保护前）；随后新增CPU快照不初始化GPU，并对完整5项CLI测试重跑，5 passed。覆盖安全YAML/覆盖顺序、真实参数训练→续训→推理、旧入口/旧权重、断点/生成续训与连续参数完全一致。compileall、两入口help、YAML/TOML/文档链接和diff通过。

- 2026-11-02T20:46:23.417312+08:00：Slurm731真实ALIGNN十结构：15轮训练→恢复至30轮→推理通过，并与连续30轮模型参数逐项完全一致；推理与重载预测完全一致。Slurm732核心/NequIP全套39 passed，733 MACE全套39 passed。代码3270e9e。

- 2026-11-02T20:49:27.218331+08:00：Slurm734新增ugnn.slurm透传入口通过十结构推理，预测与731完全一致；本地取回82711字节JSON证据，SHA256 5f5df24e33eb28b53811241c0cac21aa34a1e029d59fa420a91c37916ea609f6，经JSON解析/10结构/两份39 passed日志/续训对照标志检查通过。最终仅文档记录，链接/路径/命令和diff检查通过。

- 2026-11-02T20:51:26.173989+08:00：收尾检查通过：最终服务器同步40fa648；停止唯一已确认代理后远端1080实际释放，连接正常退出。此提交仅状态/操作记录，diff检查通过，不重复计算测试。

## 2026-11-02T21:00:31.020502+08:00：自定义GNN/分子图与文件标准实现前测试计划

- 图：KNN逐分子构建、k截断/孤立点、对称去重、无跨batch边，禁止非周期KNN误用PBC；输入图全局偏移/原子顺序/特征一致，边向量保留位置/晶胞梯度，非法dtype/shape/indices/shift明确拒绝。
- 模型：标准包装校验N×irreps节点输出/可选context、不要求边特征；真实目录GNN与graph插件相对导入，KNN+GCN参数梯度、坐标有限差分/二阶梯度，checkpoint恢复后输出一致；拓扑/模型代码变化检测。
- 格式：统一schema_version=1配置/数据，checkpoint兼容现有format1/2并记录协议版本和插件代码指纹。拒绝未知版本/错graph配置/错误结构，旧JSON/插件/CLI和旧checkpoint继续通过。
- 实跑：选十个有真实标签的非周期分子，通过Slurm运行自定义KNN+GCN训练/续训/推理、导入图相同结果对照；保存源数据ID/单位/哈希、版本/Slurm与报告。不用合成标签冒充真实分子验收。
- 每次提交前检查对应单元/集成、YAML/文档链接/命令、diff；新增模块/示例目录附README。

## 2026-11-02 21:24 +08:00：UGNN 使用缺点评估检查范围

- 本轮为源码/文档静态评估，不修改业务代码；核对 CLI、配置合并、数据绑定、训练/推理批处理、模型实现边界、工作流和Slurm脚本，预期结论可定位到实际代码，区分执行验收与泛化精度。
- 实际核查：训练默认 `structures=10` 且取前N条，训练与推理各构造单个StructureBatch；无独立eval/预检查CLI，配置schema仅有限校验；单位因子需显式填写；模拟另走脚本/API。确认本轮引用路径存在，未执行训练、推理或服务器操作，不将历史测试冒充本轮验证。
- 文档检查结果：9/9 引用文件存在，三份记录的 `git diff --check` 通过（仅Git换行格式提示）；本轮不提交Git。

- 2026-11-02T21:34:39.952470+08:00：针对图/标准/旧插件/旧checkpoint的14项通过；随后本地全套51 passed。空图保留特征列宽的解析细化后又重跑7项格式检查，7 passed。compileall、CLI --graph help、YAML/扩展路径、9条规范相关本地链接及diff通过。真实G2十结构及两环境兼容将交Slurm。

- 2026-11-02T21:42:41.600650+08:00：Slurm735真实10分子训练/续训/推理及导入图对照通过，736/737各51 passed。格式最终审查新增边界单元：显式v1不能混用旧atoms/coords/cartesian别名，缺targets应为空而非把几何当标签，拼错图属性应拒绝；旧无版本输入继续兼容。计划针对拒绝/空标签/旧别名兼容检查，并同步后重跑实际数据流确认。

- 2026-11-02T21:45:18.129110+08:00：格式边界修正后，标准/旧插件/CLI针对14项通过；compileall/diff通过。新增v1未知字段/旧别名拒绝、空标签字典、旧JARVIS分数坐标兼容均已验证，未降低任何原判据。下一同步后重新运行真实分子与两环境完整单元。

- 2026-11-02T21:55:28.845677+08:00：最终源码a07ab00：Slurm738真实10 G2分子自定义KNN+GCN train15→resume30→infer、连续30、导入图独立训练全部通过，参数/预测逐项一致。739/740两环境各52 passed。217277字节证据本地SHA b8cc046cf498e9e992bf7a4e295ccded33c54bd82c91f2aa6ce7be1b417d81ea核对通过；两份标准分子数据本地读入/10 ID/图索引验证通过。文档链接、YAML/命令和diff检查通过。

- 2026-11-02T21:59:08.636010+08:00：最终清理验证通过：服务器源码/规范已同步fef1567；关闭唯一自有代理后由既有工作连接实际确认1080释放并exit0。此提交仅操作/状态文档，diff检查通过。

## 2026-11-02 22:14:09 +08:00：生态架构建议核查范围

- 本轮仅提供架构建议，不修改业务代码、不运行训练或服务器操作。核对现有contracts、模型包装和目录插件边界；外部接口仅引用官方文档。预期每项新增功能明确为建议，文档引用路径存在，状态历史保留。

- 实际结果：5/5本地引用存在；四份任务记录git diff --check通过（仅换行提示）。核对PyPA插件发现/entry points和ASE计算器官方文档；新架构、包名和接口均标明为建议，未将其记作已实现或新增测试通过。

## 2026-11-02T22:25:27+08:00：官方checkpoint与主干改动评估

- 检查范围：六个backbone构造、特征提取切点、归一化/构图/context差异；引用路径及diff格式。预期明确现有变体不能仅删除head就加载官方权重，保留原主干的替换读出方案可行。本轮不进行权重或数值一致性验收。

- 2026-11-02T22:25:58+08:00：实际检查4/4引用路径存在，任务记录diff格式通过。已对照官方CGCNN源码、Equiformer实现与MACE微调文档；仅静态评估，无官方权重加载、预测一致性或梯度实测。

## 2026-11-02T22:30:29+08:00：运行与官方模型修复测试计划（实施前）

- 数据/mini-batch：超过10条默认全部使用、显式随机子集复现、JSONL惰性读取/重复ID拒绝；尾batch和不同原子数/缺失标签的全局统计正确；float32/64输入模型输出一致；分batch推理顺序/数值与整batch对照，JSONL输出无全集图保留；epoch边界中断恢复与连续训练参数完全一致，改变batch/dtype/采样设置的完整恢复明确拒绝。
- 任务回归：性质、节点/图张量导数、力场、谱和生成的mini-batch及重载；旧配置/checkpoint读取和CLI继续兼容。参数冻结不能切断输入求导。
- 官方provider：实际发布checkpoint来源/hash、原架构/配置和buffer严格覆盖；与官方原生调用的特征/预测对照（换头前），禁止silent missing keys；统一特征包装保留梯度，最终新头随机初始化；保存后不依赖原权重路径重载。
- 真实验收：六个支持模型各10真实结构通过Slurm加载官方权重、微调、重载推理，有限loss/非零主干梯度及参数变化，来源/任务/版本清楚；执行验收不宣称泛化。安装/数据准备按服务器权限，编译和较重转换走Slurm。
- 每次commit前执行对应测试/静态检查并记录实际结果；源码仅本地编辑，服务器pull同步。

- 2026-11-02T22:41:48+08:00：首轮数据检查3项通过；增加缺失值用例后发现标准v1明确要求finite，测试NaN fixture与格式要求冲突。保留标准校验，改为旧格式NaN用例验证既有masked-loss约定；此为有源码依据的fixture修正，不放宽验收。ruff未安装，不宣称lint通过；使用compileall/diff和实际pytest。

- 2026-11-02T22:44:04+08:00：数据单元修正后3 passed（另2项真实训练/推理集成留待Slurm）；compileall通过。实现包括性质/力场/生成mini-batch、JSONL流式推理和精度/续训设置；完整集成和历史回归待提交后Slurm执行，尚未宣称通过。

## 2026-11-02T22:53:10+08:00：官方模型包装实现单元测试计划

- 包装层不得修改官方model子模块/配置/原生预处理值，严格加载完整state与buffer；捕获读出前节点特征，条件信息仅在最终输出适配中加入。首批实现MACE与CGCNN，其余四个随后按真实发布格式实现。
- 自包含artifact保存原始模型发布文件/配置，以允许删除原下载路径后重载；真实源文件SHA、包版本、加载覆盖率和源URL必须记录。比较官方原生特征及原始预测，再在10真实结构上微调和重载。
- CGCNN NumPy原生预处理没有坐标计算图，梯度桥必须保留官方前向数值，并以等价几何公式提供一/二阶梯度；不更改官方层、BN、邻居规则或径向基。用解析单元和实际有限差分验证，不把输出形状匹配当数值一致性。

## 2026-11-02 22:56:21 +08:00：第一版研究定位核查

- 本轮仅研究建议，无业务代码修改。预期区分模型架构跨任务、预训练表示迁移和同权重多任务三种证据；先例使用论文/作者官方来源，不把覆盖更多任务直接认定为首次或通用权重。检查相关文档差异格式并保留正在执行的实现计划。

- 实际结果：论文摘要/官方来源已核对，三层证据边界明确；本轮任务记录git diff --check通过（仅换行提示）。未运行任何新增模型实验，未用其他正在推进任务的测试结果证明本轮建议。

## 2026-11-02 23:04:18 +08:00：ALIGNN2.0适配机制核查

- 预期按任务追踪读出、梯度、条件及工作流；区分论文方案和当前仓库示例。仅引用论文和官方源码，不运行模型或服务器任务；检查任务记录格式。

- 2026-11-02T23:05:12+08:00：a11cb36完整回归Slurm741核心/NequIP 57 passed（10.82秒），742MACE 57 passed（10.63秒，JobState COMPLETED/ExitCode0:0）；741已被scontrol清理但日志完整57 passed，未虚构其exitcode。包含float32/64各13结构mini-batch训练/精确恢复/整batch推理对照/JSONL逐条输出；不是六官方模型微调验收。包装基础2项本地单元通过（精确forward值及一/二阶梯度、嵌入artifact脱离源文件和hash损坏拒绝）。

- 实际结果：官方源码forward中mean/fc、fc_atomwise、grad和应力分支与论文方法3.1/3.2对应；tensor recipe的output_features=9/18/36核对，生成方法3.6与谱学3.4核对。记录git diff --check通过（仅换行提示）；无新增模型运行结果。

## 2026-11-02 23:08:30 +08:00：ALIGNN2.0参数量核查

- 预期核对官方线性头参数公式(D*(d+1))，明确示例数值非checkpoint实测；核对论文模型宽度/深度及表4参数，不把求导输出数量当可训练参数量。仅轻量核查，无模型实例化或训练。

- 实际结果：PowerShell轻量算术核对5个D*(256+1)值均一致；官方nn.Linear默认bias与论文表4的0.55M/4.04M已核对。记录git diff --check通过（仅换行提示）；无模型实例化或新增实验。

- 2026-11-02T23:19:49+08:00：官方基础和格式数据单元13 passed；compileall与diff格式检查通过。MACE/CGCNN/MatGL-MEGNet/NequIP包装已写首版，第四个直接调用ModelFromPackage eager并从原始per_atom_energy_readout前取特征；真实加载/数值对照/微调尚未执行，不以此提交宣称模型支持验收。

- 2026-11-02T23:27:18+08:00：读出边界截获增加解析单元，官方基础3 passed、compileall通过。NequIP旧力场头的内部autograd可能释放特征计算图，故特征路径在原读出前停止，原主干模块/运算保持不变；原完整forward单独保留用于数值对照。新增Slurm验收脚本首先实现MACE独立Calculator特征/能量对照，其余provider独立参考分支明确拒绝而不是假装通过。

- 2026-11-02T23:43:52+08:00：MACE官方Slurm743 COMPLETED/ExitCode0:0，10真实结构4epoch微调passed，loss2.363604688644409→2.1337198495864866，含官方Calculator描述符/能量对照、一二阶坐标导数及自包含checkpoint重载；完整validation.json待归档。其他5模型已取官方实际权重，尚未完成微调，不扩大此结果适用范围。

## 2026-11-02T23:52:08+08:00：官方标量特征的生成读出适配测试计划

- 官方MACE-small及EquiformerV1读出前可仅含标量；保持官方主干不增加1o通道，在最终DirectionReadout选择既有几何加权向量路径。验证输出旋转协变、输入一二阶导数有限、原生有1o通道时仍用原线性向量投影；不修改官方模型、邻居图或预训练参数形状。

## 2026-11-03T00:07:52+08:00：官方源码资源打包单元计划

- CGCNN/Equiformer/OCP源码采用固定commit的官方archive下载；不修改源码，将包目录及原始许可证打成可复现资源包，用于网络不稳时本地传服务器。检查每个打包成员与原archive逐字节SHA一致、无越界路径/符号链接、包完整且不带权重或日志，解包只创建缺失或内容完全相同的当前任务资源。测试/检查及实际下载清单记录，不把资源文件提交Git。

- 2026-11-03T00:10:51+08:00：新官方基础+生成输出适配5 passed（另3项未选）；源码bundle第一次因Equiformer非包目录oc20/trainer中的上游符号链接拒绝。证据确认所需nets包内无链接，先过滤未选择目录再执行链接拒绝，仍保持payload完全无symlink；重跑打包验证后才提交。

- 2026-11-03T00:13:11+08:00：源码资源包重跑通过：3个固定官方commit、85个原始文件，bundle131330字节，SHA03d01b5c27b0f2adaaa801f64cf01b46061f645b9b8b395797298cca56a96df8；打包后逐成员与上游archive内容hash一致，未加入权重/日志/符号链接。仅包目录外的上游训练文件链接被排除，原始包源码未修改。Python3.10兼容hash实现已改为分块SHA256，需复核最终脚本静态检查。

- 2026-11-03T00:47:21+08:00：cf2e993 Slurm744 CGCNN独立CIFData/原forward对照+10真实结构微调/重载passed（loss1.4448969364→1.0030168835）；745 MatGL-MEGNet原predict_structure对照+微调/重载passed（1.0224616975→0.8826507658）。747core/748MACE完整回归各62 passed。746 NequIP真实发布包能反序列化，但旧官方API返回ModuleDict，metadata读取失败；新增保留原对象的容器选择/歧义拒绝回归，并改用官方from_ase精确输入协议。修正后基础5 passed/compileall通过，NequIP实际重跑待同步，不能记作已通过。

## 2026-11-03T00:58:14+08:00：官方默认选择及旧checkpoint迁移单元测试计划

- canonical六模型默认原始官方实现，缓存profile/来源/hash明确；缺资源明确报错，不回退到变体。显式implementation:legacy保留旧变体，原数值/梯度测试继续以显式legacy执行，不删或放宽断言。
- 旧checkpoint无official artifact时恢复legacy，并保留float64/适配器版本/训练配置兼容；新的官方自包含checkpoint重载不依赖cache。CLI切换官方模型时清掉旧模型专属checkpoint/构图尺寸，不把旧权重套到新模型。
- 示例配置删除隐藏10条限制，显式structures:null、batch_size/dtype；真实10结构验收脚本保留明确10条。验证YAML/JSON解析、CLI优先级、缓存SHA错误拒绝、不同checkpoint版本的实际旧数值重载和精确resume。所有实际训练/推理回归走Slurm，提交前先做对应解析/路由单元及静态检查。

- 2026-11-03T01:12:09+08:00: Migration routing/parser/analytic units: 14 passed; compileall src/scripts/tests and git diff --check passed. Published cache SHA constants cross-checked against the local download manifest. Full numerical legacy-resume/training regression planned on Slurm after sync. Official749 failed strict force parity (2.68e-5, tolerance unchanged); singleton inputs now preserve the original unbatched API and reference asserts every input tensor exactly. Official750 failed because Graph returns DGL while the reference used TorchGraph batching; reference now uses original dgl.batch. Official751 missing torch_sparse, binary-wheel installation planned in the isolated environment. These actual acceptance failures are not recorded as passed.

- 2026-11-03T01:26:27+08:00: Slurm754 core and755 MACE: 71 passed each on7257012, including old checkpoint numerics, CLI and exact optimizer continuation. Official753 ALIGNN passed original DGL Graph/model parity (feature and prediction error0),10-real-structure fine-tuning1.1865351947->0.9981914837, finite1/2 derivatives and self-contained reload. NequIP752 input keys/tensors all exactly match original calculator but force parity still fails at2.05e-5. Plan diagnostic original/native repeatability and JIT warmup on Slurm, keep acceptance tolerances unchanged; compile diagnostic before commit.

- 2026-11-03T01:53:53+08:00: Final actual checks: official758 NequIP exact feature/energy/force parity0 (single thread), loss2.21460177898->1.38769281656; official759 Equiformer original V1/source/state parity0, loss2.23675608635->1.21199294403, PyG2.0.4 build/install alsoSlurm. All6 finite1/2 input derivatives, updated original trunks and self-contained reload. CLI760 used documented flags/default profile with structures:null, batch32,f32; trained2/full-resumed3/inferred10. Third isolated environment full71 passed. Local archive SHA and55 file hashes/85 original source hashes checked; six cohorts share identical10IDs/geometry and data_fingerprint25dcd9c5e431f0cb70a0f0e577de9d99ccf96c3c8f3d334c994eb425af9e61f9. Final doc-only commit checks: local links/paths/config commands and diff formatting planned before commit.

- 2026-11-03T01:56:20+08:00: Final doc/config checks PASSED:30 local links resolve (including ignored evidence artifacts), every example selects all records and canonical configs have official/no variant architecture knobs, profile SHA metadata matches actual download manifest; diff --check passed. First direct parser invocation lacked src on sys.path; rerun with explicit src import path passed. New-env regression exact filenames confirmed defaults-equiformer-761.out/.err,71 passed with verified separate log hashes. No functional edits after the already-passed regressions.

- 2026-11-03T01:58:37+08:00: Final sync/cleanup integration PASSED: remote HEAD7724686,6 official validation JSONs passed,CLI structure_count10,new-env71-unit log present, queue empty, own proxy PID/creation identity checked, remote1080 released and SSH exit0. Cleanup record is documentation-only; diff --check and state-history preservation checked before final local commit.

- 2026-11-03T09:13:52+08:00: MACE forcefield recipe unit plan: parse YAML/schema; resolve documented training and inference configurations and verify official artifact path vs UGNN resume semantics; verify canonical E/F/S names and tensor units against existing implementation; check local Markdown links, referenced commands/paths, Python snippet syntax and git diff formatting. No model training or physical-label fabrication; parser/config checks only.

- 2026-11-03T09:18:38+08:00: MACE recipe checks PASSED: YAML/schema/all-data/batch4/f32/original .model path; documented CLI train/infer arguments parse and preserve backbone/task/dtype across checkpoint config merge; canonical E/F/S names/units match current scales/ForceFieldModel; native Python snippet parses; every Bash block bash-n passes;7 local links and diff --check pass. Initial helper assumed non-existent C:/Program Files/Git bash; locating actual PATH bash via shutil.which fixed the helper (no recipe change or weaker checks). No actual training/inference performed on an unspecified user dataset.

- 2026-11-03T09:26:26+08:00: Before implementation: validate default/E/F/S subsets and reject empty/unknown/duplicate/wrong-type declarations; canonical ordering and old-default checkpoint equivalence; changed supervision must reject full resume. Unit: forces-only data contain no E/S, unused binding keys ignored, selected-force label still required, loss/scale independent of unselected labels, nonzero mixed coordinate/parameter gradient through energy-derived forces. Integration on Slurm: force-only minibatches/resume/infer plus existing EFS regression; original MACE10 real structures with only source force labels, trunk update/decreased loss/checkpoint reload/input derivatives, no DFT. Keep original-head-vs-new-head distinction explicit.

- 2026-11-03T09:33:51+08:00: Local config/analytic units8 passed, including force-only missing E/S bindings, mixed coordinate/parameter derivative and unidentified energy offset; compileall passed. Config/CLI selection, doc links, Python and Bash syntax passed. Fixed only extra test-log EOF blank found by diff --check; no assertion/tolerance change. Full numeric training/resume/EFS regression and original MACE acceptance remain pending Slurm.

## 2026-11-03 09:36:17 +08:00：当前实现对照ALIGNN2.0静态检查

- 范围：当前训练/评测/模型接入/生成/工作流及最新证据；预期每项不足有代码或验收边界依据，区分功能未实现与未跑基准，保留其他正在进行任务。仅文档评估，无训练、推理或服务器连接；最终检查引用路径与diff。

- 实际结果：8/8本地引用存在；训练集evaluate/归一化损失、生成固定seed、官方context输出拼接、短FIRE/MD/Gamma、六官方带隙验收与历史变体矩阵逐项核对。论文3.3/3.6与官方复现入口已核实。任务记录git diff --check通过（仅换行提示）。本轮不执行计算测试，不挪用其他任务结果。

## 2026-11-03 09:42:17 +08:00：四类性质预测解耦专项核查

- 范围：PropertySpec/NativeFeatures、ScalarAdapter/EquivariantAdapter、PropertyReadout/ResponseReadout、ForceFieldModel与supervision、训练评估和官方证据。预期明确实际接口限制、物理语义和待验证项；不把可配置监督误判为缺失，不强加空间群或多任务要求。静态检查，不新增训练/服务器操作。

- 实际结果：7/7本地引用存在；逐项核对固定adapter/readout、q线性响应、谱shape、E/F/S计算与supervised_outputs选择、训练集evaluate及六官方带隙验收。读取相关既有单元仅作覆盖核查，不声称本轮重跑；任务记录git diff --check通过（仅换行提示），无模型计算。

- 2026-11-03T09:47:14+08:00: Actual source c0b31c2 Slurm762 core/763 MACE full regressions80 passed each.764 original MACE force-only4epochs/batch5/f32 passed: strict artifact load1.0, force loss1.13103690514->0.59997976743,trunkdelta0.40074819677; full continuation1->4 and streamed inference10 passed. Local independent audit checks13 file hashes and10 original-vs-force-only IDs/numbers/positions/cell/PBC/forces exactly; training targets contain ONLYforces. No fabricated E/S or newDFT. Documentation/evidence links and diff formatting checked before proof commit.

- 2026-11-03T09:50:23+08:00: Final force-only sync/cleanup integration passed: ef360c4 on server, actual80-test logs and764 force-only validation present, queue empty; only local proxy33236 with recorded name/startUTC2026-11-03T01:36:17.2531606Z stopped, same SSH confirmed remote1080 released and exit0. Closure-only docs diff/history preservation checked before commit; no code changes or extra tests after passed regressions.

## 2026-11-03 09:55:25 +08:00：组件解耦需求文档检查计划

- 检查新需求文档与计划索引的相对链接、引用源码路径、代码围栏、需求/验收编号、YAML示例语法及冻结/梯度/旧checkpoint语义一致性。预期所有示例明确为未来配置且范围限于性质预测；保留既有变更历史及其他任务。纯文档变更，无需新增模型单元或服务器计算；完成后记录实际结果。

- 实际结果：23条相对链接有效，47项需求编号和13项验收编号完整且唯一，4个YAML模板经PyYAML解析及关键语义检查通过；状态标记/代码围栏/新文件行尾空白检查通过。首轮检查器的中文状态断言受PowerShell管道编码影响，保持相同预期改用Unicode转义后全项通过，未降低文档标准。git diff --check通过（仅换行提示）。本轮仅文档检查，13项模型验收尚未执行。

## 2026-11-03 10:02:12 +08:00：原生特征直连readout需求修订检查计划

- 检查默认结构、维度优先级/冲突与首次前向、非标量表示边界、可选adapter及readout内部处理的训练归属是否一致；检查YAML示例不要求独立adapter、旧配置兼容和冻结几何梯度仍保留。核对相对链接、需求编号/验收引用、围栏/空白和diff；纯文档，无业务源码/实验/服务器操作。

- 实际结果：23条相对链接有效，50项需求定义唯一且显式引用均存在，13项验收完整；4份YAML均经PyYAML解析且不配置独立adapter/train_adapter。核对F=256声明与128首层、默认直连图、response内部feature_processing、force-only冻结示例、状态标记/围栏/行尾空白，全部通过；git diff --check通过（仅换行提示）。模型验收项仍未执行，本轮无源码/服务器操作。

- 2026-11-03T10:25:44+08:00: PRE-IMPLEMENTATION A-E/ACC01-13: static/native feature_dim discovery/assertion/missing declarations, runtime shape/mapping/dtype/geometry/semantic mismatch, non-scalar representation refusal; nativeF256/otherF linear+MLP+node energy, pooling-before/after nonlinear difference and batch separation; registry extension on2 feature specs; explicit scalar/geometry processing/no independent adapter and response rotation/parameter gradients. Controlled BN/dropout frozen params/buffers/modes, unique optimizer groups/all-frozen train error/infer allowed, frozen MACE mixed input/head gradients with force-only labels. Strict unknown config/version/scope/pooling/route/optimization errors including generation blocks. Legacy checkpoint numeric replay and EFS/force-only resume remain. New reconstruction/full resume equivalence, incompatible strategy/head rejection, explicit component-only warm-start provenance. Resolved configs/component audits/unused native heads. Real Slurm budget:CGCNN official bandgap and200-bin spectrum10 structures, frozen/full scalar modes; MACE official bandgap frozen/full plus frozen force-only10 real labels; response dielectric10 real with explicit small_response/basis2 (supported original provider), original native reference checks retained. dtype float32 actual official, float64 analytic finite differences/rotation; existing tolerances unchanged. No DFT or new generative/workflow requirements.

- 2026-11-03T10:58:00+08:00: Local pre-server checks:20 existing supervision/official parser tests passed;21 selected native-dimension/config/registry/pooling/all-frozen analytic cases passed (5 server-only deselected); compileall passed. Added runtime semantic/mapping/dtype corruption, explicit adapter ownership, persistent-buffer guard and checkpoint signature tests. Real official float32 finite differences predeclared step.002/rtol.02/atol.002; analytic f64 force/stress rtol2e-5/atol1e-9; old reference tolerances unchanged. Full suite and real harness are Slurm-only and pending.

- 2026-11-03T11:01:28+08:00: Expanded local static/analytic selection PASSED:28 passed,6 deselected (training/response/explicit adapter server-only). compileall src/new harness/tests passed; git diff --check passed (CRLF notices only). Earlier20 supervision/official parser tests passed. State-update stdin helper failed matching Chinese headings due PowerShell pipeline encoding; rerun from UTF8 .py file, no source or assertions changed.

- 2026-11-03T11:23:00+08:00: Slurm765 core114 passed/766 MACE114 passed on ae90d7e, including all34 new cases and80 old regressions. New local adapter-basis warm-start test caught refusal at state keys before semantic check (expected explicit basis reason); move semantic preflight before state-shape preflight, preserving refusal and every assertion. Four example doc-check initially lacked src import path; fixed helper only. Real jobs767/768 no stdout/failureJSON observed; stderr inspection pending, no acceptance claimed.

- 2026-11-03T11:24:41+08:00: Validation follow-up unit plan:resolve all effective new-path runtime/report/selection defaults after dataset count is known, record actual component modes during training separately from final eval audit; retain exact full-resume equality test. Warm-start adapter semantic preflight must reject incompatible basis before any mutation. Real harness launch fix:installed scripts package shadows repo namespace, so execute script file and import sibling validate_official, then verify --help locally before commit and rerun only failed real jobs; original model implementations unchanged.

- 2026-11-03T11:27:36+08:00: Precommit follow-up passed:adapter basis-semantic refusal unit1 passed after preflight ordering correction; effective-defaults analytic unit1 passed;4 example YAML normalized without adapter,30 local links and9 Bash blocks passed; standalone real-harness --help and compileall passed; diff --check passed. Training mode audit and expanded exact resume covered by next full Slurm rerun. Original765/766114-pass logs retained;767/768 launch failure retained and attributed to namespace shadowing.

- 2026-11-03T11:28:02+08:00: Additional non-scalar explicit-invariant processing/refusal and scalar-response fixed-frame guarantee analytic unit1 passed; no assertion/tolerance weakening. All checks for follow-up commit now passed locally; full latest-source Slurm regression remains planned.

- 2026-11-03T11:34:32+08:00: Final audit unit plan:explicit backbone warm-start must retain existing custom plugin source_sha256/factory checks across source/target, even when class/width/state keys match; reject before any target mutation and accept identical provenance. Add exact analytic new-forcefield batched-vs-singleton E/F/S comparison (rtol1e-10/atol1e-11), strengthening ACC07. Existing real771/77211cases passed and769/770117 passed per environment; archive160856B SHA c60039d13548c4c8a4d9eae2b9bd485d92fd91aee0b6fba396bcdcbe0543f7d6,51files. Final warm-start-only source correction will receive full core/MACE Slurm regression; no scientific provider changes.

- 2026-11-03T11:38:21+08:00: Final source-check unit PASSED:1 compatible/changed custom-source warm-start test, rejection verifies all target tensors unchanged.51 archived evidence hashes and11case configs/realIDs independently audited; force-only projection exactly matches original elements/PBC and coordinates/cell/forces after declaredf32 casting. CGCNN full backbone PARAMETER delta independently inferred0.11620/0.11342 (state deltas35.9 include BN counters); frozen whole state exactly0. MACE mixed head gradient0.00844374, force/stress FD abs errors4.15e-6/1.49e-5, tensor rotation1.91e-6. New exact force batch-separation assertions queued for final full Slurm rerun.

- 2026-11-03T11:53:10+08:00: Final scientific validation COMPLETE on a25095e:Slurm773 core118 passed15.25s /774 MACE118 passed15.80s, including exact E/F/S singleton-batch consistency and custom-source warm-start nonmutation. Final logs archive743B SHA250e8cec88b68e08ffdf4536fa6fdf92230a323c7b393e970a7f38a454bb02f0 independently verified. Real771/77251file/11case audit passed; frozen body state exact0. Local audit presentation correction initially applied branch to shape-check rather than parameter-delta block, causing a false positive frozen-parameter assertion; corrected branch, reran full hash/geometry/label/component audit successfully without changing any scientific tolerance or raw evidence. Final docs path/command/hash checks before commit pending.

- 2026-11-03T11:54:46+08:00: Final documentation precommit checks PASSED:4 example configs normalize correctly without independent adapter,60 relative links exist,9 Bash blocks bash-n pass,all YAML blocks parse,code fences balanced,hex digest lengths valid. Both documented archive SHA/byte counts exactly match local verified transfer metadata; git diff --check passed. No new source changes since final118/118 Slurm regression.

- 2026-11-03T11:58:30+08:00: Closure-only integration check passed:actual final healthHTTP200/git pull3019c8a,evidence paths present,queue empty,proxy PID/name/start matched before termination,sameSSH1080-release marker andexit0. Closure docs preserve history and diff/link format checks performed before final commit; no source changes or additional numeric tests after118/118 passed.

- 2026-11-03T12:42:13+08:00: Read-only portability check:rg verified capability metadata across every built-in/provider and ForceFieldModel all-three-capability gate; inspected geometry/strain/autograd path and explicit non-scalar processing contract. No numeric tests needed or rerun; no source/config/script changes.

- 2026-11-03T13:14:49+08:00: PRE-IMPLEMENTATION:five fixed official published artifacts in existing caches; ten real original force labels, no E/S labels or DFT. SingleCPU,float32,batch5,4epochs/headLR.001,fullLR.0001. Test-only candidate capability declarations scoped inside acceptance process allow investigation without weakening public guards. Required:original feature/native prediction parity; perturbed-geometry force6entries and strain3entries finite differences(step.002,rtol.02,atol.002 as prior MACE),nonzero finite mixed head/body gradients,total force,eval batch/singleton E/F/S agreement(rtol2e-4,atol2e-5),training-mode batch coupling separately reported. Frozen whole state exact,head updates,full params update,finite/decreased force loss,reload/inference. Catch/report each mode failure independently. Unit/static:CLI options,config source selection,scoped override/no global state leak,capability guard untouched. Full regression on relevant existing envs for production changes. Never relax numeric tolerances to mask failures.

- 2026-11-03T13:18:41+08:00: Harness precommit checks PASSED:2 local analytic/config tests (scoped override restored on exception; original factory/capabilities unchanged, explicit non-scalar conversion and force-only setup),compileall,new Slurm bash-n,and diff --check. No local model training or official model calculation. Production capability gate unchanged. Dedicated owned proxy50456 createdUTC2026-11-03T05:18:11.7676478Z; first health/pull/submission as recorded next.

- 2026-11-03T13:21:15+08:00: Source review found CGCNN independent CIFData parity helper reads task.property for its unused CSV label slot; forcefield config lacks property. Add reference-only deep-copy selector forces so slot uses first existing real-force component, no fake label and no change to training task; add nonmutation unit before correction commit. Wait775 actual results before rerunning only affected model(s).

- 2026-11-03T13:24:02+08:00: 775 finished:MEGNet frozen/full passed;NequIP at least frozen passed (full detailed archive pending);ALIGNN training both decreased but FD failed at h.002,need fixed-probe step convergence without relaxing rtol/atol;CGCNN failed pre-test property-slot now corrected/unit3passed;Equiformer original OCP arange sees requires-grad cell-derived discrete repetition Tensor. Next unit:separate original discrete graph construction from live continuous geometry using original supported precomputed-graph path if source confirms equivalence,with native parity and coordinate/strain gradients retained. Also actual ALIGNN profile reports512x0e,so documented prediction_bandgap assert256 is wrong:correct to512 and verify real config assembly onSlurm. New source edits remain local;no production capability changes until evidence.

- 2026-11-03T13:28:07+08:00: Correction precommit PASSED:4 local assessment/boundary units,including no_grad only on discrete topology while original live pos/cell and second mixed derivatives remain;compileall,diff formatting,and Slurm syntax checked. Added fixed-model FD sweep (h.002,.001,.0005,.0002,.0001) with unchanged rtol.02/atol.002;actual ALIGNN documented config512 first-layer assembly to be tested onSlurm. Production flags not yet changed. Archive77546files133008B SHAfc31bc7d67d9df9331093f6bfba8101dd287a1c0a841de47a11d9195144ee178 verified;MEGNet andNequIP BOTH frozen/full pass,original referenceerrors0.

- 2026-11-03T13:33:39+08:00: NEW corrective unit planned from actual780:CGCNN frozen all passed,default full train BN couples structures(E error.317,F2.038,S2.804) and final loss122->214. Add explicit optimization.backbone_eval=true (parameter training remains enabled),default absent retains old policy dictionaries/checkpoints;CGCNN new forcefields must reject full train mode unless explicit eval policy. Tests:bool parser/default equivalence,frozen stats with trainable backbone gradients/updates,optimizer groups,full-resume mode check. Capability declaration upgradesFalse->True must not break old supervised component checkpoints;allow only monotonic verified FeatureSpec.gradients upgrade with recorded paths,still reject downgrade/F/architecture changes. Test source/target compatibility including warm-start. ALIGNN FD782 h.0005/.0002/.0001 all pass existing tolerance,errors shrink;real documented512 config assembled.783/784122 tests each passed.781 Equiformer still running during archive2,wait before source pull.

- 2026-11-03T13:41:38+08:00: New policy/compatibility local checks PASSED:7 tests,1 optimizer/mixed-gradient training unit reservedSlurm;compileall passes. False/absent backbone_eval normalize identically;nonbool rejects;monotonic FeatureSpec capability upgrade replay is numerically exact and recorded;downgrade/F changes reject.781 now complete:Equiformer derivatives/parity/frozen training pass,full training decreases1.4198e6->2.3228e5 but train-mode batch comparison fails;no BN modules,source has stochastic alpha_drop. Extend explicit backbone_eval requirement toEquiformer and record unrestricted repeat/batch diagnostic separately from supported eval policy. Final norms never silently changed. Next fullSlurm126tests expected plusCGCNN/EQ eval-param andALIGNN converged step.0002.

- 2026-11-03T13:44:34+08:00: FINAL release integration plan before unit:after all five candidate modes pass,enable only proven provider derivative flags,then WITHOUT candidate factory overrides load each actual mode checkpoint,full-resume4->5 for10real force-only structures,and all-parameters-frozen streamed inference. Assert no assessment-only attrs exist in production instances. Additionally replay actual previous CGCNN771 supervised checkpoint with unverified metadata;require same predictions at old tolerance and explicit monotonic capability-update records. This distinguishes candidate experiments from ordinary supported user path;keep3environment126 full-suite results. Release script/parser syntax and bounded metadata/data/hash audit before docs commit.

- 2026-11-03T13:49:03+08:00: All candidate modes now PASSED:785CGCNN explicit-eval full loss122.0627->1.69569,frozen->9.84047;786Equiformer explicit-eval full1.4198e6->513790,frozen->396713;787ALIGNN h.0002 both passed after782convergence;775MEGNet/NQ prior both pass. 788/789/790 core/MACE/equiformer each126 passed. Archive4:110files305607B SHA77c264a30c1815e111dd0efcf0bd70286daf2b3fc9bddf3b0fa7d27d57280e23 verified. Enable proven provider flags now,then release integration must use NO candidate patch. Release script compileall/help passed;no scientific tolerance weakened.

- 2026-11-03T14:06:10+08:00: Production release COMPLETE:791-795 all5models/10modes plain constructors(no provisional attrs/override),full-resume4->5 and fully frozen derivative inference10records each passed.792actual old771 CGCNN checkpoint replay error0,6monotonic capability metadata updates recorded. Final archive158files439819B SHAde88b3e93ca3eb769414ddb68bd88827fecdcb3afdec18fab55ec425d5947e08 verified;independent local auditchecks all158hashes,5*10 originalfloat32 geometry/force projections,allmode configs/updates/FD/batch/labels,three126pass logs and production trace sourcecfeb989. Final docs/Slurm-default-step only changes remaining;no new model math.

- 2026-11-03T14:10:05+08:00: Final precommit docs checks PASSED:4 real-use YAMLs normalize,68 relative links exist,9 Bash code blocks bash-n and all YAML examples parse;fences/digest lengths valid. Updated assessment Slurm default chooses ALIGNN verifiedh.0002,bash-n passes. Documentation archive SHA/439819B/158files exactly match verified transfer;diff --check passed. No model math changes after126x3/10production-mode validation.

- 2026-11-03T14:13:08+08:00: Closure-only checks passed:sameSSH8965HTTP200/pulld36b948/queueempty,ownproxyPID/name/startidentitymatched,same-session1080releaseandexit0,localprocessabsent. Statehistoryprefixpreservationanddiffchecks beforelastlocalrecordcommit;no numerical/sourcechanges afterpassedvalidation.

- 2026-11-03T14:18:06+08:00: Read-only checks:catalog.py accepts explicit graph shape1 regression /shapeC classification;metrics.py usesMSE or CE byspec.kind;label requires per-structure class indices and outputs logits;bindings handle key/factor/per-atom/threshold;rg finds no classification accuracy/F1/AUC,probability postprocess,multilabel loss. Existing custom3-class CE unit is tests/test_plugins.py. No numerical tests rerun or source/config changes.

- 2026-11-03T14:30:06+08:00: PRE-IMPLEMENTATION head-mode unit plan:strict enum/version,defaultreset canonical equivalence with existingconfigs/checkpoints,native rejects custom readout/adapter/context/unsupported task or artifact. NativeTaskContract enforces property/shape/unit/outputkind and original normalization/pooling,not just F. Nonregistering component views partition native parameters/buffers/modes without aliases or duplicate optimizergroups;test shared-param refusal,head-only/backbone-only freeze withinputgrad,mixedforcegrad,strict viewstate andnative/reset bodywarmstart. Headmode change rejectsfullresume;native continuation/reload andexistingreset tests pass. RealSlurm:all6 original known-checkpoint physical prediction parity incl CGCNN/OCP denormalizers;actual native taskfine-tuning where realmatchinglabels exist (BG/formation/energy-force),no fake OC20 labels;MACE/NequIP original-energy force derivation checks. Auditmetadata/scales explicitly before enabling native paths.

- 2026-11-03T14:32:06+08:00: Native metadata inspector precommit compileall/CLI help passed. Inspection is bounded/no training,all actual artifact/model execution plannedSlurm. Owned dedicated proxy46820 createdUTC2026-11-03T06:31:13.8996266Z. Original six models/head paths/norm fields must be read before production native mode implementation.

- 2026-11-03T15:31:33+08:00: Local safe checks passed: 10 native configuration/contract/ownership/warm-start tests; 4 optimizer/mixed-gradient/continuation cases reserved Slurm. compileall passed; diff whitespace corrected. Full three-environment and original-artifact validation remain pending. Original metadata 796-800 complete;801 import failed before model execution, fixed inspector initialization using existing load_o3 compatibility scope.

- 2026-11-03T17:05:17+08:00: Slurm803/804/805 PASSED 139 tests each (core/MACE/Equiformer),including all native independent freeze/mixed-gradient/continuation cases.802 EQmetadata succeeded:IS2RE relaxed-energy task,targetmean-1.525913953781128,std2.279365062713623. New real-artifact harness compileall/help passed;two native configs parse and links checked. Harness exercises six original-model physical parities,independent freeze,actual ten-record matching-task fine-tune/reload/resume;EQ diagnostic only,no fabricated targets.

- 2026-11-03T17:14:29+08:00: Original-artifact acceptance806-811 all6 PASSED. Independent upstream feature/prediction error0 for six profiles;native physical scalar/energy/forces error0;max stress errorMACE3.04e-7 GPa,NQ4.01e-7 GPa. Both independent freeze policies each6 pass,nonzero active gradients,zero frozen gradients,state/buffers bitwise unchanged,no duplicate optimizer params. Five actual10-record matching tasks trained2epochs thenresume2->3,exact reload,allloss decreased;EQno matchinglabels and no fake target. Archive64files75607B SHA1857302efe46f3873c928e9595ea9d998816e540fb16fc355566f285609335b5 verified. Final integration unit planned:real-artifact native/reset body-only warmstarts bothdirections preserving targetheads,fully frozen streamed native inference,actual pre-headmode CG771/MACE old checkpoint prediction replay;runSlurm only.

- 2026-11-03T17:18:40+08:00: Final integration harness compileall/help and git whitespace checks passed;no production math changes since139x3 plus806-811. Original normalizers and force stress tolerances unchanged. Final real transfer/replay tests remain pending Slurm.

- 2026-11-03T17:32:08+08:00: Final Slurm812-817 all6PASSED:native/reset body transfers bothdirections bitwise exact,targethead initialization unchanged evenwhen resetunusedhead deliberatelyaltered;all-frozen10-recordJSONL inference each. ActualCG771 bandgap0error and MACE764 E/F/S0error. Final86files100186B SHA299c54eb42c47e272ffcc9f58a4b317543ab2a837b0082a61e9b1945fcf92201 verified. Independent local audit86hashes,all5x10 raw IDs/float32geometry/sourcehash/targetbindings,2->3continuation fingerprints,139x3 logs andzero-erroroldreplays PASSED. No production changes after9ab9aec numerical validation.

- 2026-11-03T17:33:42+08:00: Final documentation precommit PASSED:29relative links,3new YAML/Bash blocks,2native configs schema checks,archiveSHA/bytes/86-file count match,and git diff --check. State history prefix preserved. PersistentSSH84765 remains open at NATIVE_VALIDATION_READY;same-session synchronization and proxy cleanup next.
