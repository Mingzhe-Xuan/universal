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

- 2026-11-03T17:36:20+08:00: Closurechecks PASSED:sameconnection finalHTTP200/gitpull4fc8796/queueempty,ownproxyidentity match,remote1080released,controllerexit0. No production/source changes after passed139x3/sixnative/sixtransfer suites. Final statehistory-preservation and whitespace checks apply to closure records only.

- 2026-11-03T17:52:00+08:00: Read-only consultation check:catalog.py has11entries;forcefield outputs total_energy/forces/stress;customspec supports graph/node regression/classification with explicitshape;CEsinglelabel;postprocess includesfinitewindowKK. Nativeprofilelimits checked against docs/native_heads andprovidercontracts. No numerical rerun warranted for answering current capabilities.

## 2026-11-03 18:10:53 +08:00：MACE/NequIP生成任务先例核查

- 检查论文方法与作者代码，预期给出可核实直接先例并明确模型承担角色；区分架构改造训练与原预训练权重复用，避免将弛豫/筛选误记为生成主干。仅文献核查，无模型执行。

- 实际结果：直接核对MACE扩散时间编码/坐标与元素去噪、SiMGen预训练节点特征及相似核；CHGGen作者声明和论文score网络、DM2方法中的定制NequIP及条件嵌入；GEODE附录C的MACE模板编码器。来源限定原论文/作者代码，部分出版站访问失败时使用作者托管PDF和已检索正文，未用二手综述替代。未运行数值测试。

- 2026-11-03T19:06:43+08:00: Connection-only check plan:local effectiveSSH hostname/user/port/forwarding;actual interactive auth prompts;confirm final remote shell/login without recording credentials in projectfiles. No numerical tests needed.

- 2026-11-03T19:08:59+08:00: Connectioncheck result:effectivealias xuanmingzhe@211.86.151.113:22,no proxyjump;attempt90195 anddiagnostic63159 bothremoteclose pre-auth,secondconfirmed kex_exchange_identification. Bothprocesses exited1,no password/OTPprompt reached,no credentials stored. Existing unrelatedSSHuntouched.

- 2026-11-03T19:10:41+08:00: Updatedconnectionplan:verifyeffectiveProxyJumpvlab thenactualSSHauthenticationpath/password/OTP/login. ExistingunrelatedSSHidentifiedanduntouched;no numericaltests.

- 2026-11-03T19:13:09+08:00: Connectiontestsuccessful:updatedProxyJumpvlab reachedtargetpasswordthenOTPthenhanhai22-01shell. No credentialvaluespersistedinproject. Accessrestrictiondiscoveredinloginbanner;onlyexitissued,no repositorywork/heavywork. Sessionterminationchecknext.

- 2026-11-03T19:13:48+08:00: Finalconnectioncheck:interactiveSSH2054 exited0;outputlogoutandtargetconnectionclosed. Jump/MFApathworks,post-loginusageblockedbyexplicitsitebannerrestriction. No unit/numericaltestsapplicable.

- 2026-11-03T19:16:20+08:00: Documentation-only plan: verify new access note links/paths, SSH example parsing and host alias, source attribution to this user clarification, absence of credential values, and unchanged historical state prefix. No numerical tests or server connection required.

- 2026-11-03T19:17:43+08:00: Documentation checks PASSED:5 relative links,Markdown fences,SSH example bash syntax,user-source attribution,and complete preexisting state-history prefix preservation. Trailing blank lines corrected. No secrets added to documentation;no source/config changes,unit tests or new SSH session.

- 2026-11-03T19:38:48+08:00: Planning/check scope:SSH proxyhealth and mandatorypull;df/inode/quota and Slurm top-levelresource query;Slurm1CPU recursive taskusage inventory crosschecked against df. Local static train/split/metric/config audit;officialdataset counts/splits/download sizes via primarysources. Planfile links,unit conversions,additive storage budgets and sourceattribution checked;no new modelnumerics.

- 2026-11-03T19:59:44+08:00: Planning evidence verified:818archive2636B SHA386cf01f6379441791b9b0a431e2d59696ffdd09f8910fcd833aff3ba89b13ff;allinventorycomplete,checkpoint count actual190. LocalZIPdirectoryheaders read only:no bulkconversion. Draft budgets add24-39GiB,29cells/seed87for3seeds. Next final docschecks+freshcapacityfind_spec diagnostics. Publisheddatasetcounts distinguishedfromactualcleanedN.

- 2026-11-03T20:04:07+08:00: Final planningchecksPASSED:12relative links,Markdownfences,4bashscripts bash-n,818archiveSHA/length/count190,localZIPheaders,final67.616GiBcapacity/find_spec facts. P1data upperbounds sum7GiB;corrected aggregatebudget24-40GiB so conservative67.577-40=27.577GiB>20reserve. 16main+13extension=29cells,3seeds87. OriginalHEADstatehistoryprefixpreserved. No numericaltests required for documentation-onlyplan.

## Guqq2 用户磁盘排名检查计划

- 验证本地 SSH 确实加载用户 Guqq2 别名；若配置权限阻塞，不将其误报为服务器故障。
- 通过健康检查与 git pull 门禁后方可进行业务查询；递归磁盘统计通过 Slurm，限制单 CPU，统计含隐藏目录且不跟随符号链接、不跨文件系统。
- 区分按家目录和按文件 UID 归属；记录无权读取、共享目录和系统占用，避免不完整排名误判全机最大用户。
- 结果报告时间、节点、单位、主要目录/文件及扫描覆盖限制。仅只读审计，不清理数据或操作其他用户进程。

## Guqq2 用户排名实际检查结果

- SSH 配置预检未通过：默认别名未解析，显式 -F 文件访问 Permission denied；受控提权被策略拒绝。
- 已确认不具备继续连接条件，未将本地访问问题误报服务器故障；未生成用户排名或宣称扫描完成。
- 既有 SSH 进程只读查看，未清理、重启代理或发起 Slurm 作业；经验记录已查。
- 本轮仅更新记录，未提交或改动科学源码。静态核对相关记录严格 UTF-8、无替换字符且新增状态/历史存在。

## 2026-11-03 Guqq2 可读范围存储审计实际验收

- SSH访问恢复后每次连接健康HTTP200和git pull均通过，复用用户既有代理；没有改动其他会话。
- Slurm819、820通过scontrol确认为COMPLETED、ExitCode0:0、node42、单CPU；末次squeue无作业。递归工作不在登录进程执行。
- 819明确10个home不可读；820仅可见文件按UID统计，记录354条访问/文件状态错误，不将作业成功视为全盘成功。
- 本地验证sum(owner.allocated_bytes)==visible_total_bytes通过；GiB、总目录和独立安装包大小换算通过；JSON可解析，含节点、时间、UID、统计口径与错误。
- 临时本地控制脚本及其内嵌Python语法检查通过；扫描不跟随符号链接、不跨设备、硬链接去重，只读取stat/目录元数据。
- 结果保存于忽略目录；无清理、模型计算或Git提交，既有其他未提交文档改动保留。

- 2026-11-03T20:17:06+08:00: Checkpoint consultation staticcheck:verified four officialprofile filenames/sourceURLs/hashentries against official-pretrained.md/native-head evidence andcurrent818 officialcachedirectory. Distinguish original task head from newdownstream readout andretainedweights fromcurrentlymissingTorch dependencies. No numerical rerun warranted.

- 2026-11-03T20:26:23+08:00: Documentation/staticcheckplan for48matrix:verify count48/144,per-model parametercount fromactualofficialmetadata and16byte/P FP32Adam estimate (notactivationVRAM),resourcehardware evidence,matching FT/scratchtaskheads/data/graph,cross-providerPBCcompatibility,andbounded disk retention math. No GPUprofilingpossible until missing shareddeps restored;do not label estimatesasmeasurements.

## Guqq 内存快照检查计划

- 核对SSH目标Guqq为211.86.155.221，不能沿用Guqq2的RAM/显存或磁盘快照。
- 读取MemTotal/MemAvailable、SwapTotal/SwapFree、缓存和短时swap活动/PSI，不把空闲少或可回收缓存视为内存耗尽。
- ps按RSS列进程与用户，标注共享页重复计数及权限限制，不以RSS简单求和等同物理RAM实际总占用。
- 轻量只读诊断不运行模型；主机、时间与原始结果保存本地，既有代理保持。

## Guqq 内存查询实际检查结果

- 目标身份通过：Guqq211.86.155.221，Guqq2不同。
- 连通诊断未通过：首连接255目标无响应；重试证据包含Vlab认证成功和目标banner exchange超时，stdout没有MemTotal或free/ps结果。
- 业务查询未完成，故不提供虚构的内存利用率/最大进程；未重启任何用户代理、清理缓存或终止旧会话。
- 原始日志与记录本地严格UTF-8检查；只读结果未提交Git，没有模型测试。

## Guqq内存再次重试检查计划

- 核对仍为Guqq211.86.155.221，连接/命令有超时；成功后只读检查MemAvailable/Swap/进程RSS并记录主机时间。
- 失败记录具体阶段，不将网络超时解释为内存不足；若达到三次失败查询lessons。
- 仓库与代理门禁通过后才执行业务指标；不碰旧会话、缓存或服务器设置。

- 2026-11-03T20:38:11+08:00: 48matrix documentation/static checks PASSED:4*6*2=48,3seeds144;actualofficialmetadata parametercounts96641/15909761/3847696/616360,FP32Adam16P estimate tablevalid (activationnotincluded). HostconfiguredRAM257787MiB=251.745GiB;singlebudget24-40,3seedbounded26-44GiB leaves23.577GiB atconservativefree67.577.10relative links/fences/whitespace pass. Scratchisnotheadreset;sharedforcePBCcompatibilitychecked. NoGPUpeakmeasurementsclaimed,no modelrun or newSSH.

- 2026-11-03T20:43:27+08:00: Documentation check plan: appended matrix must contain48 training checkboxes (4*6*2),144 runs for3seeds; verify relative links,shared dataset2-7GiB budget and separation of temporary peak,consistent FT/scratch definitions. No numerical or server checks needed.

## Guqq 内存重试实际检查结果

- 实际SSH/代理HTTP200和仓库浅clone成功；原始快照包含node221、20:40:25、MemTotal/MemAvailable、Swap、PSI、vmstat、ps与GPU元数据。
- 本地逐项换算字节/GiB、RSS KiB/GiB及可用比例：251.745/230.582/15.079GiB，91.59%可用；Swap1.710GiB；最大python4.716GiB。短时si/so和PSI0已核对，不夸大为长期监测结果。
- 收尾证据：身份匹配停止3052，最终cleanup-confirm.txt包含1080释放标记，诊断连接exit0；本地3052和53440不存在。初次清理token CRLF错误已如实保留，不将该退出2冒充成功。
- 本轮为短时管理操作，未运行模型/测试作业；生成物保存忽略目录，记录严格UTF-8且保留历史。

- 2026-11-03T20:44:20+08:00: Documentation checks passed: section11 has48 training checkboxes,12 per model across6tasks/twoinitializations;three seeds144. Relative links,Markdown fences/table shape/trailing whitespace valid. Dataset2-7GiB and temporary3-4GiB accounting retained from existing plan. No source/model/server tests needed.

- 2026-11-03T20:49:37+08:00: Doc/staticcheckscope:verifyproviderPBCguards/nativeinputboundaries,CGCNN originalforwarddynamicneighboraxis andpaddingmessages,ALIGNNgraph+linegraph requirements,geometryautogradandcheckpointcompatibility. Updateplan/48checklist to distinguish currentunsupportedinputfromarchitecturalimpossibility;futuremolecularnumeric/parity/forcechecks remainunrun.

- 2026-11-03T20:52:35+08:00: Molecular-input clarification checks PASSED:localbothnative_input PBCguards found;upstreamCGCNNmodel confirms tensorinput/dynamicM and unmaskedneighboraggregation (paddingnotinert);ALIGNNlocalprovider needsatom+linegraphs. Planlinks/fences/whitespaceand48/144count checked. ConditionalrMD17dataupperbounds~7.5GiB rounded8=>single41/three45GiBmax,67.58-45=22.58GiBreserve. No molecularmodelnumericsrun,newinputprofileunimplemented.

- 2026-11-03 20:52:50 +08:00：Equiformer力场静态核查：native_input的原OCP拓扑、attach_periodic_topology、live pos/cell与ForceFieldModel求导、backbone_eval模式和native IS2RE限制均与现有786/795记录核对；本轮未重跑模型，历史十结构执行不视为泛化/MD稳定性。任务记录diff检查通过后交付。

## 2026-11-03 21:00:07 +08:00：全量参数清理追加检查计划

- 纯文档变更：保存追加前内容指纹/前缀，检查既有正文完全保留；核对源码引用、相对链接、围栏/空白和diff。内容须区分默认全量已实现与十结构数据源、预测limit与report_structure_limit等不同语义，不将smoke参数或生成固定噪声当正式全量配置。未授权本轮修改源码或运行训练。

- 2026-11-03T21:00:35+08:00: Doc-onlychecks planned:new6A configuration parses,cutoffunit/strictdistance/PBCaxis/image conventions agreewithgeometry.py;noimplicitneighborcap;officialoriginalpreprocessingandRBFwidth preserved;newplanneddefaultsclearlyseparatefromcurrentcode andexplicitKNNexample. Checkrelative links/fences/whitespace;no newnumericaltestneeded.

- 2026-11-03T21:02:44+08:00: Graph-default docschecks PASSED:graph radius/cutoff6.0 YAML;18relative links/fences;source confirmsper-axisPBCimagebounds,strictdistance<cutoff/nozeroself,livepos/cellgeometry. Currentknn assembly/radiusclass4A verifiedandexplicitlymarkedpendingtransition. gitdiffwhitespacepasses. No defaultcodechange,numericaltestorserverconnection.

- 2026-11-03 21:03:56 +08:00：追加文档检查通过：第12节唯一、4个子节、10行配置表、6个准入项及6个源码相对链接有效，围栏配对/新增空白检查和git diff --check通过。首次严格前缀校验发现同期新增4行6Å构图说明；差异核查确认旧正文无删除或替换，改用逐行保留校验通过，未覆盖同期变更。源代码默认值核查完成；纯文档未运行模型/单元测试。

- 2026-11-03T21:15:55+08:00: Readiness staticchecks:rg/sourceinspection of backbonefactory/officialproviders,graphs.py,training.evaluate,metrics/generation andprepare_acceptanceCohorts. Confirm6Atargetnotimplemented,entirebackbonescratchnotheadreset,independentval/test/bestselectionmissing,generationseedfixedbyindex andsamplingdefaulttrue. LastresourceevidenceusedwithoutclaimingfreshSSH/GPUmeasurement. No codechange/numericaltestneeded forstatusanswer.

- 2026-11-03T21:39:18+08:00: Static/configchecks PASSED:parsedbandgap,spectrum,response,forcefield,mace-forcefield,prediction-force-only,generation,native-bandgap;batch32/32/5/32/4/5/32/16respectively,allmax_atomsNone. Verifiedbatchingdefault32 andForceField/ResponseReadout/sampleautogradpaths. NoGPU peakmeasurementsornewtestsrun.

- 2026-11-03T21:43:50+08:00: Doccheckplan:validatebackoffexamples32->16->8->4->2->1 andoddstart5->2->1;positiveintegertermination,minbatch1failurehonest,commonFT/scratchsafevalue;links/fences/whitespace. CheckOOM-onlyclassification,restartafterfailureandfinalconfig/metadatarequirements;no GPUOOMexperimentrun.

- 2026-11-03T21:45:48+08:00: OOMplan docchecks PASSED:12.5unique,fences,11relative links,32/5/1backoffexamplesandall1..100startsterminateat1,whitespace. Confirmedfulltrainingstep/worstcase/samplingcoverage,trainlabelonlyandfreshformalstart,commonFT/scratchsafeB,realOOMclassificationandbatch1failurelogging. No actualOOMsimulation/GPUrunorcodechange.

- 2026-11-03T21:48:37+08:00: Pre-unit execution plan: environment metadata/path/disk verification, task-ownedvenv packageversions, then Slurm139-test baseline in core/MACE profiles and CUDA basic/high-order probes. Subsequent split/evaluation unit: deterministicgroup-disjoint splits,train-onlyfit/valbest/testisolation,streamingtailmetrics/classification/tensor/force,strictresume. Preserve baseline compatibility; no tests executed yet for newunit.

- 2026-11-03T21:57:43 +08:00: Implementation unit: isolated CUDA batch preflight. Planned checks: 32->16->8 and odd5->2->1; B=1 OOM fails; typed CUDA OOM only, host kill/invalid-result/nonfinite errors never halve; every attempt fresh process and persisted attempt/report; resolved config only on success; real GPU full optimizer step, force mixed derivative and sampling covered through Slurm after environment repair. Local pure-stdlib control tests do not execute models.

- 2026-11-03T22:07:46 +08:00: Implementation unit: immutable group-disjoint split manifests. Plan pure-stdlib fixtures for deterministic seed assignment independent of input order/training seed, exact once-only coverage, group leakage/duplicate ID/out-of-range/source-hash rejection, official fixed partitions, corrupt manifest rejection and roundtrip. No local dataset preprocessing or model execution.

- 2026-11-03T22:12:17 +08:00: Implementation unit: streaming held-out evaluation primitives. Plan pure-stdlib tests for uneven update boundaries, masked targets, tensor Frobenius/zero-target policy, binary confusion/accuracy/F1 and exact tie-aware AUROC using disk-backed SQLite; reject invalid predictions/labels and stale spool files. Training/val-best integration and real model evaluation remain later Slurm checks.

- 2026-11-03T22:13:59 +08:00: Local checks PASSED for implementation units: 4 preflight-control tests (fresh child PIDs, halving32/5, batch1 failure, non-OOM/kill/timeout/malformed identity rejection); 4 split-manifest tests (deterministic groups/official partitions/hash/full coverage/counts); 4 streaming metric tests (masked/zero tensors, element weights, exact tied AUROC/single-class policy). compileall passed for new modules/tests. No model executed locally. Real Slurm worker/CUDA tests NOT run; base binary installation failed, diagnosis blocked by automatic approval timeout, not a scientific test failure.

- 2026-11-03T22:13:59 +08:00: Documentation checks PASSED: 5 affected/new Markdown files, paired fences and 15 relative links; previous state change history preserved verbatim. git diff whitespace and new-source compile checks rerun before commit.

- 2026-11-03T22:21:33 +08:00: Implementation unit: source-bound dataset partition selection and supervised/force held-out training integration. Plan deterministic partition/limited/random selection tests; train-only scales unaffected by held-out labels; validation-only best checkpoint/early stop; test visited once after training; streamed scalar/tensor/force/classification metrics include tail batches; resume retains best history and rejects split changes/missing prior-best; no-split legacy behavior preserved. Pure protocol checks may run locally; numerical integration and existing regression suite through Slurm after environment restoration.

- 2026-11-03T22:35:01 +08:00: Pre-test harness unit: prepare Slurm-only restored-env regression and CUDA full-step preflight acceptance. Scope scalar/classification/spectrum/response/force/generation train+sample, actual CUDA allocation OOM5->2 and always-OOM5->2->1 via disposable fixture plugin; every smoke report explicitly not full-data resource certification. Static source/shell checks locally; actual execution pending approval channel and restored environment.

- 2026-11-03T22:40:23 +08:00: Preparation local checks PASSED: 17 pure control/protocol/metric tests (4preflight+4split+4metric+5selection), including interrupted best/last commit recovery; compileall of edited engine/data and new Slurm helper/tests; bash-n Slurm entry; 14 relative links/fences. Initial inline doc checker failed because PowerShell interpreted backticks; reran from a source file with actual triple-backtick counting, passed without weakening checks. Numerical held-out integrations and actual CUDA allocation OOM remain NOT RUN pending Slurm.

- 2026-11-03T22:48:04 +08:00: Follow-up artifact/protocol check PASSED: 5 selection/crash-recovery tests, edited-source compileall,14doclinks/fences and bash syntax. Holdout metrics.json now retains selection/sourceSHA/commit/environment provenance, matching report.heldout; new numerical assertion prepared but not executed. Normative dataset/checkpoint documentation updated.

- 2026-11-03T23:00:40 +08:00: Operational unit: CPU Slurm protocol regression using system Python while Torch downloads. Plan bash syntax + existing17 pure tests; job must gate all four test modules with check=True and emit commit/Slurm/result JSON only on complete success. Separate artifact from pending numerical/CUDA/model acceptance.

- 2026-11-03T23:02:01 +08:00: CPU-protocol Slurm entry static bash-n and documentation checks PASSED; four pure modules previously17tests pass locally. Scientific/CUDA acceptance remains pending, not folded into protocol success.

- 2026-11-03T23:21:18 +08:00: Actual Slurm821 FAILED before split tests completed; preserve failure and inspect fulltrace. Candidate rootcause: data.__init__ eagerly imports geometry/Torch, contradicting intended metadata-only dependency isolation. Plan minimal lazy public exports preserving names/identities, isolated subprocess import guard forbidding any Torch import, then rerun same Slurm protocol tests plus new regression. No commit of fix until local corresponding checks pass; numerical model acceptance unchanged.

- 2026-11-03T23:24:59 +08:00: Red/green dependency regression verified locally: python-S importing data.splits failed with ModuleNotFoundError torch through data.__init__->geometry before fix; lazy exports now pass. All18 local protocol tests pass (4preflight,5split incl no-site subprocess,4metrics,5selection), source compile/bash syntax/diff checks pass. Slurm821 remains FAILED; full remote trace/retest pending healthy pull gate. Existing model/CUDA acceptance not marked passed.

- 2026-11-03T23:42:39 +08:00: Implementation unit: targeted offline wheel cache recovery. Test exact CacheControl URL keys; only explicit public wheel URLs, never scan cache; modern http-v2 body and legacy cc4 msgpack body hashes; hardlink/copy verified wheels; reject mismatched hash/path/name/destination; missing resources stay explicit, no installing partialsets; disk reserve. Full GB cache hash/extraction must run CPU Slurm with memory cap, not login. Local tests use tiny bytes and no scientific/model imports.

- 2026-11-03T23:47:13 +08:00: Targeted-cache unit checks PASSED:4tests modern/legacy recovery,exact URLkeys against pipCacheController,wrongdigest/missing/path/host/destination rejection,reserve and sourcepreservation. Initial test could not import namespace scripts due path shadowing; use explicit repo-file import, same assertions pass. Python compile/both Slurm shellsyntax/docs links passed. CPU cachejob also runs these4tests before GB extraction. Officialmetadata catalog16Torch/CUDA/triton files,2.799GB excludingTorch, rootSHA d6c3cba198dc93f93422a8545f48a6697890366e4b9701f54351fc27e2304bd3; nomodel execution.

- 2026-11-04T00:08:45 +08:00: Implementation unit: full JARVIS bandgap+classification and phonon-DOS preparation. Planned tiny fixtures test completeiteration(no10/12atomcap),finitegap includingzero,explicitclass threshold,200channelDOS,Cartesian/fractional geometry/PBC,invalidlabel/geometry audit,duplicate-ID conflict vs exactgeometry grouping,source/data hashes and fixed sharedsplit,strict streaming JSON/truncation,metadata-only(noTorch) imports. Actual40MB/154MB archive hash/convert/count must runSlurm; local only boundedfirstrecord format diagnostics and syntheticfixtures.

- 2026-11-04T00:22:51 +08:00: Implementation unit: approved loopback HTTP resource continuation + offline base installation Slurm. Test tiny partial transfers/resume, immutable SHA mismatch refusal, verified archive chunks/exact wheel members/extraction and destination protection; CLI download health inside actual allocated node (never assume login-loopback reachable). No install until complete rootTorch+15CUDA+49common hashes verified, preserve20GiBreserve; pipcheck before linking task-owned childenvs. Local unit IO only, realdownloads/hash/install in CPU Slurm.

- 2026-11-04T00:40:27 +08:00: Full JARVIS preparation checks PASSED:5tiny-fixturetests allrecords/zero+finite labels/24atomstructure/no10cap/cartesian+fractionalPBC/strictJSON/200channelvector/auditedinvalids/duplicateIDconflicts/transitiveMP+geometrygrouping/sharedsplit/sourcehash/elementcoverage. 119symboltable exactly compared toASE3.27.0official wheel AST; compile and Slurm Bashsyntax pass. No fullrawarchive conversion run locally. Realcounts/fullSlurm prepare pendingresources.

- 2026-11-04T01:00:52 +08:00: Resource-archive unit PASSED4tinytests:fullchunk/archive/member SHA,roundtrip/idempotence,corrupt ormissinginput refusal,unregisteredtarname/path/duplicate/conflictingoutput rejection,reserve. JARVIS5fixturetests rerunpass withsourcehash/executionmetadata/elementcoverage. NewSlurmrestore/install Bashsyntax and3Markdownfences/relativepaths checked. Realsharedbase installation andGPU/model acceptance NOT run.827/828 nowconfirmedterminal:common40,040,283B partialprogress,curl18;CUDAinitialhealthtimeout. PrivateHTTPproxy48663 confirmedVlabclosed; do notcall themrunning.

- 2026-11-04T01:29:11 +08:00: Operational driver plan: supervise ONLY approved wheel transfer with persistentpartials. Dryrun/compile commandquoting/embeddedPython; runtime must offlinepullf13 eachconnection, sourceHTTPhealth200, no activeCUDAjob before submit, stopon occupiedunknown1080 or freshproxyhealth failure, restartonly ownprocess actuallyterminal, neverkill userGuqq, retainedJSON/log sourcehash/bytes. Queue installation/regression only afterall16verified. Largehash/download staysSlurm.

- 2026-11-04T01:39:37.750987 +08:00: Implementation unit: full GMTNet dielectric preparation sharing JARVIS writer/grouping/audit. Planned bounded synthetic fixtures: complete iteration including >10records/>12atoms/zero labels, exact finite3x3 tensor order, reject malformed/nonfinite tensors, restricted pickle globals/hash/trailing objects, sharedID/geometry splits, no extra symmetry projection; existing5JARVIS tests unchanged. Real pickle full load/conversion only Slurm; numpy-specific full raw audit pending.

- 2026-11-04T01:43:44 +08:00: GMTNet writer unit local checks PASSED:6 bounded plain-data fixtures plus unchanged5 JARVIS fixtures; compileall/Bashsyntax/git whitespace passed. Seventh NumPy scalar/array/OrderedDict fixture explicitly Slurm-only (skipped locally); full authorpickle conversion not yet run. Supervisor compile/plan PASSED; real835 onward transfers preserve partialprogress, no scientific model executed.

- 2026-11-04T01:50:27 +08:00: Actual Slurm847 PASSED original5 JARVIS+all7GMT fixtures, including NumPy1.26 binary scalar/array/OrderedDict input; no skipped NumPy test. New operational supervisor/sourcebody compile, embeddedPythonAST and Bash-n passed after correcting PowerShell quoting from sourcefiles; full-resource install/GPU tests remain afterall16SHA gate.

- 2026-11-04T02:50:00 +08:00: Operationalgate revision checks: controllerPython/embeddedPythonAST/Bashquoteplan pass. Remove prematureGPUtest submission because actualprovider metadata shows unmetdeclaredrequirements beyondCUDA16. Provider59wheels62,873,601B officialPyPISHA verified; DGL79,870,014B fromofficialindex, locallyrecordedSHA (indexnohash); Torchvision8,730,539B officialindexSHA matched. Filesonly, no install/modelreadyclaim.

- 2026-11-04T02:52:50 +08:00: Actualfull-data artifacts PASSED localread-onlyprovenancechecks: GMTandgapcounts/splitcounts/IDexclusion/sourceSHA/datasetSHA/exactb6codeSHA/SlurmIDs; newdocumentationlinks/fences pass. GMTactualfullconvert1.567s, gap15.445s underSlurm. ProviderPyPISHA59 andTorchvisionofficialindexSHA pass; exactDGLofficialdownloadcompletewithlocallyrecordedSHA. DGLGPUcompatibility/numericaltests NOTRUN.

- 2026-11-04T02:57:52 +08:00: Implementation unit fullMLearnE/F preparation: stdlib streaming12 pinnedJSONs, receipt/blob/SHA integrity, homogeneous ordered sites/occupancy/PBC, finite totalEandNx3F, auditinvalids/noatomcap; releasedtestimmutable, group training/validation by explicit MDdescriptionfamily+exactgeometry, detectcross-releasedexactduplicate, disclose release-test trajectoryfamilyoverlap (bounded first Cu/Si records confirmsameAIMDfamily intrain/test). Tests bounded12file fixtures/zeroF/largeN/group roles/seed/digest/path/conflicts/unitsmetadata; unchangedJARVIS/GMT andmanifest regressions. Realfullsource conversion remainsSlurm.

- 2026-11-04T03:08:14 +08:00: MLearn localunit PASSED7 incl no-site/noTorch imports; original5JARVIS +6GMT(1NumPy-onlyskip) +5splitmanifest regressions pass. Sourcecompile,MLearnSlurmBashsyntax,affectedREADME/auditdoclinks/fences,gitwhitespace passed. Fullreleased12filepreparation NOTRUN yet, requiringSlurm.

- 2026-11-04T03:31:12 +08:00: ActualSlurm854 ALL19_MLEARN_JARVIS_GMT_FIXTURES_PASSED, including7MLearn+5Jarvis+7GMTwithNumPy; independentCPU. Full855 datajobpendingbehind853, notcountedcomplete. Direct-official-network draft AST/Bashsyntax passedbutNOTEXECUTED pendinguserexception. NequIPauthorpretrainconfig11565B matchespublishedMD51282055dbeb9d34db7c3220b8cdb9624 and existingcheckpointMD58190d6e0a323e40cca098e537a554075; no model loaded.

- 2026-11-04T03:40:35 +08:00: Implementationunit officialinitializationpolicy + CGCNN/ALIGNN freshconstructors: localstdlibfixtures verifystrictmodevalidation, no load/reset/copyin scratch, exactstatekeys/shapes inclBNbuffers, defaultpretrained strictload, unsupportedprovidersfailclosed, noTorchmetadataimport. Slurm-only realprofiles must comparekeys/shapes/featureirreps, same/differentseedhashes, freshBNmean0var1/counter0, nativehead rejection, warmstart conflict, strictresume/new-default compatibility andfreshUGNNstate restore. Pretrainedpathmustunchanged. MACE/NequIPfresh notclaimeduntilseparateconstructor/train-geometrynormcalibration andrealtests; no recursivepartialreset fallback.

### 2026-11-04T04:10:45+08:00 Perov-5 全量生成数据准备单元（实现前计划）
- 纯数据 fixture：固定三份CSV登记/大小/SHA/Git blob验证；遍历全部行，保留作者train/val/test与material_id；重复ID、跨分区相同几何、损坏CIF/无序占位均显式失败或审计；不使用性质标签筛选。
- CIF通过ASE3.27官方解析器，验证单结构、完整占位、周期三维晶胞、严格5原子；坐标/顺序与ASE读入结果一致，不做primitive/标准化/超胞。纯策略fixture可本地std库；真实ASE读CIF fixture和全量转换必须Slurm。
- 静态：compileall、bash -n、CLI无Slurm拒绝、git diff --check、文档链接/围栏。提交前记录实际结果；源码发布后经离线pull，独立CPU Slurm执行ASE集成与全量审计。

- 2026-11-04T04:15:53+08:00 Perov-5提交前实际检查：纯std数据fixture6/6、原MLearn7/7、JARVIS5/5通过；compileall、Slurm脚本bash -n、CLI无Slurm拒绝、Markdown围栏/路径及git diff --check通过。首次fixture失败源于测试ID区间相交，已修正fixture为互斥ID；同时将全原档校验前移到解析之前，损坏资源在依赖导入/输出创建前拒绝。未降低原有测试要求。真实ASE3项及全量转换未运行，提交后必须Slurm验收，不计为已通过。声子/MLearn回传审计计数、划分、数据SHA和实际4595354源码SHA核对通过。

- 2026-11-04T04:25:38+08:00：实际Slurm858通过全部9项Perov-5测试（包含3项ASE3.27 CIF解析）；859再次9/9通过并完成18928/18928转换，11356/3787/3785作者划分，最大5原子。回传audit与实际668b59a两份源码SHA、三原CSV的大小/SHA/Git blob登记均核验通过。没有把该阶段当作GPU/正式训练验收。

- 2026-11-04T04:31:07+08:00：实现前计划：generative协议用纯std测试覆盖epoch/ID/phase/draw隔离、batch/order独立、resume兼容和显式v1旧约定；晶胞先验只消费训练记录、对数体积/原子几何均值、非有限/退化拒绝、训练指纹绑定；固定条件无放回/稳定ID选择、Wasserstein解析样例。真实全Perov-5训练先验与源码/源数据/manifest SHA通过CPU Slurm计算；Torch训练、采样和val-best集成另需模型环境恢复后数值测试。

- 2026-11-04T04:34:35+08:00：生成协议提交前实际检查：9/9纯std测试通过；覆盖动态训练噪声/固定评测噪声、旧v1完整续训兼容拒绝、训练专属体积先验、无放回条件、W1解析结果、源身份/输出不可覆盖、CLI Slurm门禁及无Torch/site依赖。compileall、bash -n、README围栏/相对路径及git diff --check通过。真实11356训练结构先验待发布后CPU Slurm执行；生成训练器尚未接入，不宣称数值验收。

- 2026-11-04T05:03:13+08:00：实际Slurm860通过生成纯协议全部9测试，并从完整11356训练结构拟合先验14.129232628696206 Å³/atom，heldout fit使用0；收据已SCP回传，本地按4859cc9实际脚本/协议源码SHA、JSONL与manifest SHA、分区计数核对通过。生成Torch/Pymatgen两个新runtime文件共8测试尚未运行；其源文件compileall、两个Slurm脚本bash-n和质量CLI无Slurm拒绝已通过，不能把静态检查当数值验收。

- 2026-11-04T05:09:36+08:00：本地监督器真实控制循环故障注入通过：模拟状态SSH255后健康Popen仍保留、下一观察恢复、专用代理仅创建一次、仅显式stop才清理，无真实网络/外部进程。首次fixture仅因Windows当前目录在临时目录内导致清理失败，改为先退出cwd上下文再清理后通过；没有降低断言。实际64242后续观察确认862 RUNNING且native字节从321230147增长至329485635，分片未从零重传。

- 2026-11-04T05:12:56+08:00：实现前计划：预检解析仅允许注入生成默认噪声、训练先验与缺省采样体积；显式参数、骨干/图/cutoff/采样步数不得变更，畸形worker解析不得通过或触发减batch。现有纯控制4测试保持通过，并增加正确解析/拒绝篡改/失败留档的故障注入；Torch真实worker与训练对照待Slurm环境。provider缓存复用既有recover_environment_cache.py，仅60个官方SHA/URL定向键，在Slurm复跑4缓存测试及恢复，记录命中/缺失；不扫描任意缓存、不改变版本或误称环境就绪。

- 2026-11-04T05:41:10+08:00：新实现单元前计划：纯std蓝图测试验证MACE仅按shape重建零/一拟合统计、不读取源数值、不改变层宽/词表/cutoff；NequIP只提取官方GNN构造recipe，覆盖原seed42、shift/scale，跳过明确非persistent加速器，拒绝checkpoint loader/持久架构修改；统计必须绑定train全分区、dtype、source/manifest/ID指纹，区分MACE非零度与NequIP全节点分母。原始MACE/NequIP实际构造、模块/state/irreps布局、不同seed随机性和同seed头初始化对照留待Slurm，不以纯配置测试代替。

- 2026-11-04T06:06:12+08:00：提交前检查：原预检控制4项与新增生成解析4项纯std测试通过（含控制器真实子进程、篡改拒绝且不减batch）；蓝图/懒加载7项纯std测试通过；结构评分metadata独立导入测试通过，compileall和文档/差异检查通过。结构评分其余5项真实Pymatgen/ASE测试需发布后在base补齐provider依赖的Slurm中运行，当前尚未执行。Torch构造/生成/weighted-loss数值仍待环境，不计入已通过。Slurm863实际4/4缓存测试通过，60目标恢复22个47,426,518B，完整报告已回传按目录SHA核对；59个独立provider仍缺38个24,177,622B。

- 2026-11-04T06:27:18+08:00：既有provider恢复单元：本机Range 2–9实际返回206且字节一致、worker AST与完整提交脚本bash-n通过；监督器--plan通过、真实控制循环故障注入通过（SSH255保留健康代理、下轮恢复、只建一个代理）。计划Slurm校验ZIP大小/SHA、全部59轮大小/SHA、离线安装与pipcheck，随后实际运行结构质量6测试和蓝图7测试；尚未执行的数值测试不得计为通过。

- 2026-11-04T06:30:35+08:00：实现前计划：native邻居统计聚合单元接收原包建图后每结构的节点/有邻居节点/有向边计数，验证完整train覆盖、零度节点规则及每图物理计数一致性，绑定既有source/manifest/fingerprint/dtype/cutoff。纯std测试检查MACE排除零度节点、NequIP保留零度节点、顺序无关、缺/多结构拒绝、单图不一致及全孤立拒绝。此单元仅聚合已给定的计数；原包真实建图扫描与训练入口自动绑定另外在Slurm验收，不以聚合fixture代替。

- 2026-11-04T06:36:39+08:00：Slurm864实际complete：已存在资源包24,209,507B经私有HTTP续传，全部59轮校验/离线安装完成，pipcheck=0；真实ASE/Pymatgen结构评分6/6、纯蓝图7/7通过。四份收据已SCP回传，核对59项实际版本、13个测试与c095dd6源码提交；Torch/CUDA/DGL仍未就绪，正式训练0/144。

- 2026-11-04T06:36:39+08:00：本地native邻居计数聚合3/3纯std测试通过，原蓝图7/7回归通过，覆盖全train计数、两种零度分母、顺序不变和逐图畸形计数拒绝；原预检控制与生成解析8/8再次通过，compileall及git diff --check通过。未运行原包真实建图/模型数值，未宣称自动scratch入口完成。

- 2026-11-04T06:37:52+08:00：本次提交前最终检查通过：新邻居聚合3项及原蓝图7项纯std验收、compileall、文档链接/围栏、既有state历史逐字前缀保留、git diff --check；864的59项实际版本与13项Slurm测试日志收据核验完成。仅发布计数聚合与已完成阶段记录，未发布待数值验收的四模型/生成运行时。

- 2026-11-04T06:41:38+08:00：进入原包邻居统计扫描实现单元：输入必须完整indexed JSONL train分区，使用各原包native_input，不运行网络forward；CPU逐结构累计原始edge_index，不受batch/训练seed影响。缓存统计必须绑定数据/manifest/实际输入精度指纹、cutoff、原artifact和建图源码/包版本，任何不一致拒绝。纯std覆盖身份/分区/完整覆盖策略及缓存篡改拒绝，CLI验证Slurm门禁和不提前导入Torch；真实MACE/NequIP原图扫描、零度结构、RNG保留和复用验收需Torch环境后的Slurm。运行时原型不因静态检查而宣称已验收。

- 2026-11-04T06:51:20+08:00：native扫描原型的纯身份/缓存绑定3项测试通过，包含全train选择、数据/精度/图版本变化拒绝、CLI无Slurm和已有输出在Torch导入前拒绝；compileall和两个Slurm脚本bash-n通过。已从本地官方wheel源码核对MACE统计edge_index[1]的非零度receiver，NequIP统计edge_index[0]并为零度节点补零。真实原包图/RNG/无forward/缓存复用测试为每provider3项，共6项，尚未运行，位于scripts/validation_cases，由独立Slurm入口使用各自环境。未运行本地GNN、未发布此扫描/CLI/运行时集成。

- 2026-11-04T06:51:50+08:00：Slurm866实际通过计数聚合全部3项，收据/测试日志已回传并核对c8128af；Linux/Python3.10兼容验收完成。865实际RUNNING，磁盘可用64,806,625,280B，约60.36GiB，高于20GiB预留；这是快照而非独占配额。仍无正式训练，原图扫描6测试未运行。

- 2026-11-04T06:53:59+08:00：实现前计划：训练/生成/容量worker在MACE/NequIP官方scratch构造前自动完成完整train原图统计；预训练和其他骨干路径不触发校准。完整resume只在调用方省略统计时继承保存值，显式变更仍拒绝且需按当前数据重新绑定验证。成功容量worker仅可返回与实际模型load_report一致的零权重覆盖统计，控制器只能补该字段，dtype/任务/图/显式统计不变；畸形结果不当OOM减batch。纯std测试选择/继承/回执策略与真实子进程controller，Torch集成测试通过Slurm另验。此前goal回合为progress：864安装+13测试、866三测试及c8128af发布/同步均有实际收据；本回合已poll3780确认监督器live，865续传继续。

- 2026-11-04T08:45:50+08:00：五个既有补充wheel仅暂存验收：Slurm验证1,553,197B ZIP的固定SHA、精确六member白名单、各轮大小/SHA和name/version；冲突文件不覆盖，输出staged收据且明确environment_installed=false。不安装Torch依赖未齐的包，不以暂存或元数据满足当作runtime通过；worker AST/完整Bash脚本静态检查后才提交。

- 2026-11-04T08:58:10+08:00：实现前计划：补充官方子环境离线安装入口，复用现有CUDA base installer建立的ugnn-common-base.pth，不重建父子环境、不复制Torch、不改MACE e3nn0.4.4。先验证七个固定wheel（868五个+DGL+Torchvision）的全部大小/SHA和路径，再验证共享Torch2.7.1cu128来源；任何缺失/冲突在pip install之前失败。仅向universal-official安装七个原已准备wheel，no-index/no-deps，三环境pipcheck及Torch来源/e3nn版本再验；报告明确尚非GPU/模型验收。纯std假runner测试覆盖缺资源、错误父环境/链接拒绝及正确离线目标、不发生本机安装或Torch导入；静态CLI Slurm门禁及bash-n。实际安装需等CUDA和DGL资源就绪，当前不提交必失败安装作业。

- 2026-11-04T09:07:22+08:00：本次独立环境安装入口提交前检查：3项纯std假runner测试通过，覆盖缺失/损坏资源、冲突共享pth、错误Torch及外来e3nn路径在install前拒绝、仅official环境执行no-index/no-deps安装、MACE版本隔离、CLI Slurm门禁；compileall、bash-n通过。实际环境安装未运行，不能将假runner或metadata检查当CUDA/模型通过。868真实完成五轮大小/SHA暂存，收据回传核验通过；四模型静态词表覆盖五份完整审计，超词表0，没有本机模型执行。

- 2026-11-04T09:07:22+08:00：未发布的native校准运行时更新：监督/生成训练与容量worker已本地自动接完整train统计，resume仅继承省略字段；native成功回执控制4项、原生成解析4项和原容量控制4项纯std共12/12通过，身份/缓存3/3通过。新增原包图/构造10项（每provider5项）和训练路由5项待Slurm；新增推理重建图来源校验，并修正校准加载源包时不混用保存的fresh类来源，原artifact不变。Torch/生成实际数值尚未验收，运行时不在本次提交范围。

- 2026-11-04T09:08:43+08:00：环境流水线提交前最终检查：3/3纯std安装门禁测试通过（含已有report拒绝、防外来e3nn来源），compileall、Slurm bash-n、相关Markdown链接/围栏、state变更历史逐字保留及git diff --check通过。提交范围仅独立环境脚本/测试与实际868/元数据/词表记录；未发布尚无Torch数值验收的backbone、生成或校准运行时。实际pip安装未运行，正式训练0/144。

- 2026-11-04T09:19:00+08:00：Slurm869实际通过离线installer全部3项纯std测试；收据/日志已回传，按ed2a646的Git blob核对脚本SHA 6e91bb1f328ed84eb8fad4d69dadffcb61707d24329d36f7d42c3bf6f876bd8a。这验证Linux/Python3.10门禁兼容，不代表实际pip安装或模型/CUDA验收。NequIP作者YAML已在服务器模型缓存通过11565B/SHA轻量核验，未改源码。

- 2026-11-04T09:36:13+08:00：实现前计划：正式144配置准备单元。data/identity.py与splits/loading.py可选强制source SHA和canonical manifest SHA，覆盖缺/错/格式变化、无manifest/插件误用及复用indexed source hash，不导入Torch。benchmarks/experiments/registry.py按五份完整已发布source SHA/实际计数扫描JSONL ID并验证manifest和官方资源，输出冻结身份；recipes.py生成四骨干×六任务×两初始化×三seed144配置，所有structures=all/float32/CUDA，reset头/全骨干训练，生成不混入prediction/optimization，保留相同成对任务设置和待验收门禁。只生成配置不提交训练。纯std测试覆盖完整笛卡尔积、固定seed/划分/单位/导数路径、无native graph或宽度覆写、构造/微调成对设置一致、污染或不完整registry拒绝和已有输出不可覆盖。完整数据读取/哈希和实际144生成在Slurm执行；运行时读出规范验证待Torch，不能把配置生成当训练或GPU通过。

- 2026-11-04T10:17:11+08:00：全量配置单元提交前实际检查：144配置/成对一致性6项、新source/canonical split身份4项、既有manifest5项纯std测试均通过，共15项；compileall、Slurm bash-n、README/计划相对链接和围栏、state历史逐字保留通过。初次将全API配置解析放入-S测试因contracts包导入Torch失败，现将真正生产使用的metadata合并函数独立为resolve_dataset_settings并实际测试；完整resolve_config和外部推理绑定保留真实Torch测试待Slurm，未作依赖mock或降低数值断言。初次本地历史检查的PowerShell管道编码导致分隔符查找失败，已改为UTF-8文件脚本重查通过。

- 2026-11-04T10:32:01+08:00：Slurm872实际通过source身份4、manifest5、144配置6，共15项；真实完整输入生成144配置/72对完成。matrix及日志已SCP回传；本地按执行be3d579的三个Git blob SHA、五source/manifest摘要及计数、所有config摘要重建通过，matrix SHA256 6bc44462768be3c3a9aaebd8819d97c0fb29f4e94f4f62c7a89c9c6550bedeb5。首次跨平台重建只因Windows运行目录元数据使用反斜线不同，核对器仅统一该路径分隔符，其余case/配置/摘要保持严格一致。没有运行Torch/API/数值或GPU验收。873定向四键缓存检查实际missing，无下载/安装/新环境。

- 2026-11-04T10:32:01+08:00：本次仅记录实际872/873与代理诊断的文档提交前检查：相关相对链接、路径、围栏和state原变更历史逐字保留通过；数据计数、摘要与源码对应验证依上述本地verification-872.json，相关真实Slurm检查全通过。未提交待Torch验收的运行时代码或用户未跟踪文档。

- 2026-11-04T10:36:58+08:00：实现前计划：benchmarks/pairing成对容量控制器以同seed/任务/数据/精度/读出/冻结设置的pretrained与scratch配置为输入，先各自干净进程减batch，再取共同较小值重新验证双方；复验若再次OOM则共同下调并再次双侧复验，其他错误立即失败。只使用既有run_preflight，不改physics/样本/图/步数/学习率；不重用预检权重。纯std子进程fixture验证不等上限、复验容量波动、多轮共同batch、batch1失败、未知错误不回退、输入/输出拒绝、调用者对象不变、进程独立和matrix case摘要/配对身份。CLI先检查Slurm，再读矩阵/启动worker；运行时真实GPU仍待环境，fixture不计显存或科学验收。发布后CPU Slurm复跑控制检查，不提交正式训练。

- 2026-11-04T10:46:17+08:00：成对容量提交前：10项纯std真实子进程控制测试通过，包含不同初始/可容纳batch、共同复验再次OOM并双侧重验、batch1失败、未知错误不回退、任务/seed/源/精度/非train分区拒绝、scratch统计边界、矩阵摘要/歧义拒绝、日志/输入/最终配置摘要、独立PID及CLI Slurm/无Torch门禁。另从已发布HEAD完整源码临时展开，仅覆盖本次pairing新文件，以同10项检查验证无需未发布preflight/resolution/运行时代码，全通过。compileall、相关文档链接/围栏/历史和git diff --check通过；没有本机模型执行。真实GPU/全图/导数/吞吐仍未验收。

- 2026-11-04T10:52:29+08:00：运维辅助单元补记测试范围：已初稿代理归属记录，现补计划并在继续完善前落实检查；本单元应当先记录再实现，后续按该顺序。新专用代理必须先观察1080空闲与既有非命令sshd集合，健康后绑定唯一新增PID/UID/boot/start_ticks/命令；终止只允许已记录远端身份、实际本机Popen terminal、同一UID/主机、端到端失败，再通过pidfd固定进程以避免PID复用。未知归属/多个候选/健康/元数据观察失败均不得kill或重开第二代理。纯std故障注入检验新增/歧义/重启/UID边界、PIDfd路径与旧观察255保留健康代理；脚本AST/bash-n，不做真实进程结束。真实旧孤立代理另按现有精确启动时间证据人工复核清理后才能启动新版；不改变下载资源、SHA、来源或no-progress停止规则。

- 2026-11-04T11:01:44+08:00：Slurm875/node42实际通过成对容量编排10/10控制测试（1.671秒），收据/日志已回传，按执行a7b127c的capacity.py、当时preflight.py与测试三个Git blob核对SHA通过。没有实际GPU/模型计算。运维归属5项检查通过，直接在stub OS/ps/Path/健康/signal下执行实际远端清理程序，覆盖成功、健康、boot/UID改变、start_ticks/PID复用、命令改变、缺pidfd七场景；除唯一对应的已终止且不健康代理外全部0信号。实际监督器故障注入证明SSH255保留健康连接、已记录孤立恢复、歧义不清理不重开。AST、bash-n、--plan通过；下载体SHA 572340444abe338dc9311ecdc7b04304a21a990ec71b4e9097cbfdcd58ec661d不变。

- 2026-11-04T11:01:44+08:00：本次实际875/安全续传记录文档提交前，相关链接/路径/围栏、state全部既有变更记录逐字保留和git diff --check通过；仅提交已核验阶段记录，不发布待Torch数值验收的运行时。

- 2026-11-04T11:09:24+08:00：实现前计划：原GPU容量worker只在两个step使用worst池，小batch/5次采样时可能未测全部worst。新增纯std调度模块，warmup后每个worst以同质满batch单独测至少一次，剩余测量轮转普通probe；测量次数不足时增至worst数量，明确requested/actual，不能丢worst或减采样步数。测试batch1与多个worst、batch大于worst数、100次训练预算和5次采样预算、完整phase分离、普通循环、确定性/调用方不变及重复/非法index/计数拒绝。GPU worker接入调度与元数据静态检查；实际模型/导数/峰值验收仍待恢复，不本机跑GNN。纯模块发布后CPU Slurm验证全部控制测试，实际worker仍保留待数值验收的运行时发布单元。

- 2026-11-04T11:19:18+08:00：worst覆盖单元提交前实际检查：6项纯std调度测试通过，覆盖batch1且7个worst/只请求5次、每个worst同质满batch、100次预算/普通循环、默认与确定性/输入不变、非法集合/计数拒绝及-S导入scheduler和worker不加载Torch。另将已发布HEAD全部src展开，仅加入本单元scheduler和从HEAD提取的worker调度改动，独立运行同6项全通过；compileall、相关链接/围栏、state历史保留和git diff --check通过。两次文档补丁因匹配行换行不符未应用，读取实际上下文后已正确应用，最终检查通过；未降低测试。没有实际GPU/模型或导数执行。

- 2026-11-04T11:34:02+08:00：Slurm878实际通过调度6/6，JSON和日志已SCP回传，按实际8fdea11的schedule.py、仅调度修改的probe_worker.py及测试三Git blob SHA核对通过；没有以工作树中未发布native/生成改动代替执行源码。只验证纯调度、输入检查和无Torch导入；实际GPU/导数/完整训练图仍未验证。监督器真实预绑定孤立释放3429696/3432817/3435302均有返回released和新身份记录，未人工重启健康代理；工作SSH超时已回收并重试，早先“疑似僵住”被实际回执排除。

- 2026-11-04T11:34:02+08:00：本次878及扫描范围的文档提交前检查：相关链接/路径/围栏、全部既有state历史逐字保留及git diff --check通过；只提交真实阶段证据和扫描要求，不混入未验收运行时。

- 2026-11-04T11:45:38+08:00：资源传输诊断前计划：单CPU Slurm从现有固定CuDNN wheel私有HTTP端点只读Range，1MiB/4MiB×max-time8/30秒×两次，最多请求20MiB；每次先做同路径HEAD健康检查，失败留档且不把它当吞吐样本。记录curl返回码/HTTP206/连接/首字节/总耗时/字节/速度及收到前缀SHA；完成后本地与已有固定wheel前缀逐项比对。并发主续传不取消、不重启健康代理，因此比较应标注真实背景负载及链路波动，不凭单样本断言优化有效。没有新CPU二进制/公网下载或模型计算；AST/bash-n后才提交，正式训练不计。

- 2026-11-04T11:58:25+08:00：续传连接复用验证前计划：879无有效payload，不能断言8/30秒吞吐差异。先用既有本机只读CuDNN端点验证同一个curl进程以--next、--continue-at -及显式有限Range头连续append两个8B片，核对本机固定wheel前16B及HTTP206/num_connects。只是16B本地协议fixture，不运行GNN/安装包/公网下载。若成功再单CPU Slurm做有界同连接分片实验，核对固定源完整/部分前缀；证据充分后才考虑替换原8秒源，不改健康SSH代理、官方wheel或SHA/断点/空间门禁。

- 2026-11-04T12:01:38+08:00：本机16B协议fixture实际通过：同一curl的两个-C -加有限Range操作append结果逐字节匹配固定wheel，HTTP206/206、num_connects1/0；未执行模型。接下来Slurm三组同连接64KiB/1MiB/4MiB，合计上限15925248B，20秒connect/30秒operation，fail-early遇错停止后续片段，记录每operation连接数/状态和整体前缀SHA。本机与服务器curl版本不同，因此仍须Linux真实结果；与879同时改变连接预算，不据此单独归因timeout效应。源码AST/bash-n后提交；失败或零字节如实记不可用，不以HTTP HEAD成功代替数据传输。

- 2026-11-04T12:04:42+08:00：实现前计划：probes/selection.py纯std单遍聚合全train图规模，逐项比对源顺序train的index/source_index/ID，绑定source/canonical split/dtype/graph definition摘要；只保留每维top-k和固定ID哈希普通样本，区分native边、line triplets、额外readout边与最大度，不把CGCNNpadding槽位当物理边。覆盖不漏全train/重复或缺行拒绝、非连续source indices与selected index区别、各指标极值覆盖/稳定tie、样本不受标签影响、候选数量有界、非法计数/身份/binding拒绝、固定行摘要；聚合只声明完整计数，verified_full_training_scan保持false，真实native_scan另验。同步补调度边界：worst数占满请求测量预算时仍至少执行一个普通batch，以满足计划12.5的worst+普通要求；更新6项纯调度测试的边界预期，100次常规预算不变。没有Torch/本机GNN执行。

- 2026-11-04T12:22:50+08:00：实现前计划：新离线CUDA资源续传器复用已验证curl -C -+有限Range+--next/--fail-early协议，连接预算20秒、操作30秒、每连接最多8个1MiB片，保持固定catalog/SHA/原URL与20GiB余量。Linux880两组5.06MiB约22秒完整、第三组部分前缀正确；connect实际10.27秒超过原5秒，连接num_connects1/0/0证明复用；不将其当严格8/30因果对照。单测覆盖尾片/从非对齐断点续、部分网络失败后无丢失续片、真实loopback curl连接复用、Content-Range/字节计数异常回滚本次未验证追加、最终SHA失败不发布、已验证文件跳过/冲突不覆盖、无进展超时及SOCKS规则拒绝不绕过、CLI先Slurm门禁。旧资源作业只在新工具本地及CPU Slurm通过后，持有健康代理不变、暂停旧模板重交、确认旧作业终止后从原partial接续；不修改模型、数据或官方版本。

- 2026-11-04T12:31:02+08:00：同连接续传器提交前实际9/9通过，含真实loopback curl连续四片仅一个连接、非对齐旧断点、网络半片后正确续、CR/字节/JSON异常回滚新追加而保留旧prefix、最终SHA拒绝、已有冲突不覆盖/验证缓存跳过、20GiB门禁、无进展时间预算与ruleset不重试、CLI Slurm先于catalog/posix导入。首次真实curl测试暴露Windows默认GBK解码UTF-8 metrics失败，现显式UTF-8并重新完整9项通过；未降低断言。compileall、README链接/围栏、state旧历史保留与git diff --check通过。仅发布资源工具及对应测试，不混入selection/调度或模型运行时待发布改动；Linux真实9测试需发布后Slurm。

- 2026-11-04T12:43:30+08:00：Slurm881实际9/9通过、两源码Git blob校验通过后，配置下一次资源任务模板为已发布179925a的脚本；旧40620/53648已actual terminal/CIM不存在、1080已释放。更新本地监督器lint兼容外部脚本模板，只允许精确命令且脚本字节匹配published Git blob；旧模板留备份，仍以真实queue门禁提交。新模板body SHA 8ae00a2496d3fbf0973bcf562b3c7191c43a7ca4eff6e51cd42cd3040fa65687；启动前复跑三控制故障场景/--plan/bash-n，并先查询旧877是否结束，必要时只取消其精确作业保留partial，不改健康代理。

- 2026-11-04T12:51:17+08:00：提交前检查：selection六项和调度六项纯std全部通过，包括完整源顺序身份、各维极值、固定ID哈希普通候选、单遍有界、行摘要、padding语义和不冒充实际图扫描；worst占满预算仍增一普通batch，普通池排除worst，100次预算不变。881九项Linux实际通过且两执行Git blob已核验。新监督器五项ownership、观察中断和孤立身份场景、--plan/bash-n已通过，882从65712455B断点继续且观察增长；没有NN或正式训练验收。

- 2026-11-04T12:56:51+08:00：Slurm883与884各六项全部通过；回传收据/日志按dd0fcb0实际三源Git blob核验，无skip、没有Torch数值验收或正式训练。文档提交前检查：state原历史逐字保留、源路径/结果本地文件存在、git diff --check通过。

- 2026-11-04T12:59:19+08:00：实现前测试计划：完整图扫描分为probes/native_scan.py（Slurm门禁、完整train身份/图元数据、四原包图计数、实际适配层分支、禁止模型forward、原子发布/失败证据）和scripts/scan_training_graphs.py（JSON配置CLI）。纯std控制测试验证门禁先于Torch、拒绝裁剪/非train/非official/自定义graph、完整扫描调用顺序和不漏行、失败不发布verified probe、CGCNN padding与ALIGNN triplets/两轴degree语义、真实分支元数据和源绑定；实际Torch/provider/CUDA图构造作为单独Slurm集成验收，不在本机运行模型。始终记录clean geometry范围，不签发生成全轨迹容量保证；源码/配置/图定义/source/canonical split/dtype/device/官方artifact摘要绑定，reference采用相同original预训练拓扑而非伪scratch。

- 2026-11-04T14:51:38+08:00：native_scan提交前七项纯std控制通过，另与已发布HEAD src/scripts/tests隔离后同七项通过，证明不依赖工作树中未发布scratch/生成改动；移除initialization/neighbor_statistics/NequIP仅fresh的architecture只作用reference副本。已有selection六项+调度六项回归通过。AST/py_compile、相关README链接/命令/围栏、state历史保留及git diff --check通过。五个CUDA图格式/实际radius/active分支/eager与scripted forward guard检查仅写好未执行；真实四provider全扫描也未执行。

- 2026-11-04T14:56:17+08:00：Slurm886七项扫描控制全部通过、零skip；收据与stderr回传后按6072d4c实际native_scan/selection/两CLI/测试共五Git blob核验。无Torch数值或真实provider图执行。文档提交前检查计划新增链接、命令路径、围栏及state历史逐字保留、git diff --check通过。

- 2026-11-04T14:56:49+08:00：文档检查器首次将既有standards.md#anchor整体当文件路径，检查失败；已按Markdown链接语义分别核验目标文件和标题锚点，并对计划、扫描README及scripts README全部本地链接重新检查通过。此处修正检查器，不降低文件/锚点要求；886实际验收不受影响。

- 2026-11-04T15:03:37+08:00：实现前计划：作者NequIP YAML shorthand与0.14/0.15简化builder不兼容，新增纯元数据explicit-full构造参数准备，输入必须来自原package层级/irreps和作者冻结recipe；测试独立type embed32、第一层128x0e+64x1e/末层128x0e，不把[128,64]当逐层width；保持rmax/type/MLP/Bessel/ZBL/trainable flags，仅seed和训练统计重置，拒绝缺失/冲突布局/未知recipe/层数/irreps；原helper行为兼容。cached wheel和pickle opcode只读、不反序列化/不执行Tensor或GNN；实际FullNequIPGNNModel/state/输出和导数对照须Slurm单独验证，不能凭元数据宣称通过。

- 2026-11-04T15:09:33+08:00：NequIP full blueprint五项与既有七项纯std在本地、仅已发布HEAD加本单元两文件的隔离目录均通过；实际author checkpoint以不执行GLOBAL/REDUCE的pickletools opcode数据解释确认type_embed32、hidden128x0e+64x1e/128x0e。AST、README路径/围栏和state历史保留、git diff --check通过。仅发布metadata参数转换；official/nequip runtime改动和native_neighbors数值断言暂不发布，真实构造/键形状/前向导数仍未执行。

- 2026-11-04T15:21:30+08:00：Slurm887五项NequIP Full参数控制全部通过、零skip，收据与stderr回传后按4c4616c的blueprints.py/新测试/原fixture共三Git blob核验。文档提交前README路径/围栏、state历史逐字保留和git diff --check通过；没有模型/导数数值验收。网络一次恢复前真实确认73597 terminal、旧PID不存在和1080释放，新诊断固定8B206/GitHub HEAD200/Vlab SSH banner/887 SCP成功；新68162端到端健康已通过，沿用885不重交。

- 2026-11-04T15:30:10+08:00：启动生命周期修复前计划：将新专用代理的归属绑定提前到首次HTTP健康检查之前，监听仅用于归属不宣称网络健康；端口未就绪/观察中断不猜PID，健康仍需完整curl。纯控制测试首次health失败时已绑定精确身份并可安全finally清理、观察失败不终止健康代理、歧义不绑定、不触碰用户会话；复跑既有ownership五项和观察/孤立控制场景。先完成本次无归属监听的只读核对，不批量kill。

- 2026-11-04T15:51:00+08:00：直连下载实现前验证计划：固定catalog SHA、官方CuBLAS当前偏移最多4MiB，真实Slurm记录curl HTTP/连接/速度/响应Content-Range/接收SHA及错误；本地与既有原wheel相同offset字节核对。若直连可用才停止仍活跃的已知旧writer并接原partial下载剩余固定资源，最终SHA发布；不安装或启动暂停的实验。AST/bash-n通过后提交。

- 2026-11-04T15:55:10+08:00：889实际完成4194304B，offset165498715，与本机已有固定CuBLAS片段SHA一致；18.16s/231150Bps，HTTP206、ssl_verify_result0。直连续传wrapper AST/bash-n及真实函数隔离注入检查通过：每个--next段单独带noproxy/HTTPS约束、清理代理env并拒绝显式proxy；使用已发布续传器/原SHA/20GiB/单writer锁，等待实际下载与完整SHA结果，不宣称完成安装。

- 2026-11-04T16:00:46+08:00：直连切换本阶段实际验收：889四MiB官方Range与已有原文件偏移SHA一致；直接runner对每个--next段明确noproxy/HTTPS-only，curlrc禁用，代理环境清除，注入拒绝proxy与AST/bash-n通过。890首个只读观察RUNNING，资源partial191086427>165498715，1080无监听，environment_installed=false/experiment_goal_status=paused。旧HTTP工具句柄live、CIM52372命令/54339 OwningProcess一致后仅Kill自身服务，监听释放已确认。仅文档提交前检查state历史逐字保留、相关路径和git diff --check。

- 2026-11-04T16:16:33+08:00：小规模准备实现前计划：DGL下载固定79870014B/SHA f32a1907431544ee1085b11deb373fa277534e41a46e5d5d0188c447fa9bae07，直连HTTPS/noproxy，最终SHA后仅资源complete；安装afterok依赖890与DGL，不跳过pipcheck和隔离Torch/e3nn来源。GPU诊断使用已有graph_scan五项、batching/checkpoint/geometry/heldout定向回归及validate_preflight_cuda六类完整训练步/OOM，失败阻断后续。真实pilot数据纯std准备逐一验证冻结matrix/source/split摘要，确定性ID哈希从每个原分区取64/16/16，输出新JSONL/manifest/audit及48配置，不改原全量定义；测试选择不漏/不串分区、分类共享split、无原子数裁剪、尾batch/初始化成对设置、数据变更拒绝、结果诊断标注及不启动训练。

- 2026-11-04T16:50:12+08:00：pilot准备单元提交前七项纯std通过，已发布HEAD加本单元三文件的隔离目录同七项通过，证明不依赖未发布original scratch/生成运行时。覆盖固定分区内ID哈希、不以原子数/标签筛选、完整父source/source-ordered ID及canonical split绑定、来源变更不发布、不可覆盖、同一数据/头/优化下两初始化pair与3epoch/batch2预算、禁止旧统计和CLI Slurm先行。AST/py_compile、计划及模块README全部本地链接/锚点/围栏、state历史保留与git diff --check通过。完整真实数据48配置生成需发布后Slurm，仍无NN或正式训练验收。

- 2026-11-04T17:36:31+08:00: Implementation plan for official dependency repair: stdlib fixture tests must preserve shared Torch and NequIP0.5.8/MACE0.4.4, restore only an exact own official e3nn0.5.8 overlay to its documented MACE0.4.4 parent, reject unexpected roots/versions before install, and keep all existing offline SHA/Slurm gates. Run fixture tests and AST/diff checks before publishing; repeat controls and actual pip checks through Slurm, then GPU readiness. Failed893 and blocked894 remain evidence; do not accept skipped or pending jobs.

- 2026-11-04T17:38:10+08:00: Official dependency repair: all five stdlib control tests passed, including exact own-overlay recovery, rejection of both unexpected0.4.4 and0.5.8 roots without uninstall/install, preserved offline input guards and Slurm guard. An initial overly specific error-message assertion was corrected to test both version/root rejection branches; no acceptance was removed. AST parsing, README fences, state history preservation and targeted git diff --check passed. Actual install and GPU acceptance remain pending.

- 2026-11-04T17:44:08+08:00: Installation acceptance extension planned: GPU Slurm operator smoke checks in existing three provider envs. Verify pinned Torch/CUDA, e3nn differentiable linear layers, original NequIP/MACE/ALIGNN/CGCNN imports and actual DGL graph message-passing/gradient plus PyG cluster/scatter/sparse CUDA kernels. This detects binary/device mismatches hidden by metadata; does not count as original model pilot training.

- 2026-11-04T17:48:05+08:00：实际Slurm896安装修复五项全部通过，收据按640da1d两个Git blob核验；897成功完成离线安装/三个环境pip check，898与899均COMPLETED/0:0。898：图格式/半径图/活动分支/模型前向阻断五项通过；batching/checkpoint/geometry/heldout共18项通过，failures/errors/skipped均0；CUDA预检九场景通过，包括六任务完整训练步、生成采样、真实OOM时batch5→2成功、始终OOM时5→2→1后按预期拒绝。899：NequIP0.5.8、MACE0.4.4、official0.4.4三个环境RTX5090 CUDA/e3nn前反向与四模型包导入通过，DGL/PyG扩展CUDA算子通过。收据已回传；本地仅stdlib解析核对16资源/固定版本/图检查Git SHA/测试计数/实际OOM序列，没有本地NN计算。文档提交前核查state历史完整前缀保留、相关链接/路径、Markdown表格与围栏和git diff --check。未把基础验收记作原模型pilot或正式训练。

- 2026-11-04T18:12:37+08:00：原模型初始化单元实施计划：复核并运行六项初始化policy、三项统计绑定及既有blueprint纯std测试；候选按已发布HEAD隔离运行，AST/Slurm bash语法/README链接与历史保留检查后发布。实际数值仅Slurm：初始化/官方兼容回归，CGCNN/ALIGNN同原类/状态形状/RNG/BN/scratch重载与native拒绝；MACE/NequIP各五项真实原生图/训练全覆盖/禁止GNN forward/RNG/统计绑定/实际fresh构造测试。任何构造或state布局差异都修复原构造适配，不放宽strict或换架构。自动训练入口与生成改动不混入本单元；测试按验收边界分文件保留。

- 2026-11-04T18:15:12+08:00???????????????21??std???policy6?binding3?fresh blueprints7?NequIP full5?????HEAD????30????????21????????/??Python AST??Slurm??bash-n????????README/???????????state??????????git diff --check???Torch/??????????????????Slurm????????????

- 2026-11-04T18:15:53+08:00???????????staged diff???????????????????????21????????????????????????staged diff????????????????

- 2026-11-04T18:25:52+08:00???????????902??CGCNN????BN???num_batches_tracked???strict??????????????????????strict loader?????????canonical???fresh????????????????????903??NequIP Full builder???set_global_state???????????/??dtype????isolate_rng?dtype?????????????/RNG?????????MACE????????????????????Python/NumPy/Torch RNG?dtype???????????import?mock?????factory???????????21????????Slurm????????

- 2026-11-04T18:31:09+08:00?904????????MACE?????/?????????????scalar bool contraction *_zeroed?????????path_weight???????????canonical?????products/??????????????bool??false?????????????????????????canonical?/?????????????????????????RNG/dtype?????????????????missing/unexpected keys?

- 2026-11-04T18:32:21+08:00?????????policy6/binding3?std????????Python??AST???git diff --check????????????unknown/true/wrong-dtype/non-scalar/missing-counterpart flags????Slurm???????????Torch?CGCNN?????NequIP??API?904??/??wheel????????canonical strict???

- 2026-11-04T18:40:46+08:00：真实带隙pilot执行前验收计划：只对905已通过的CGCNN/ALIGNN，固定895矩阵canonical SHA与每项配置/实际文件，严格64/16/16、seed123/三epoch/初始batch2。先两真实训练结构的独立原包native预测/特征对照，扫描全部64原生训练图并禁止GNN前向；最坏满batch+普通共100测量batch，成对独立及共同batch重新预检，失败停止。通过后才三epoch真实训练两初始化，检查全骨干梯度、实际64训练/16验证/16测试、validation-best、checkpoint重载及16条唯一ID测试预测；全流程仅Slurm，状态/失败记录保留，不计正式144。独立CPU Slurm诊断906剩余NequIP精确形状，不猜统计布局。

- 2026-11-04T18:46:16+08:00??????????907??NequIP??shape???shifts[1,1]??[89,1]?????????shift/scale???/?????/????????std????????????/?????dtype/seed/??????908/909??????device=cuda?index?set_device?????????worker?????????????????????????????cuda:N?????AST/???/staged?????????GPU???device=cuda????17??/???????MACE????????????pilot????

- 2026-11-04T18:48:24+08:00???shape/CUDA??????????blueprint8+Full5?13???????HEAD???????CUDA???worker?????13?????7??20???????Python AST???worker????calibration/??????????905??17????CGCNN/ALIGNN??accepted?906 MACE5???/NequIP4??1shape???907???shifts[1,1]?[89,1]?908/909?????????????????????Slurm??????device=cuda??GPU???????fixtures???????

- 2026-11-04T18:54:42+08:00：真实带隙pilot执行前验收计划：只对905已通过的CGCNN/ALIGNN，固定895矩阵canonical SHA与每项配置/实际文件，严格64/16/16、seed123/三epoch/初始batch2。先两真实训练结构的独立原包native预测/特征对照，扫描全部64原生训练图并禁止GNN前向；最坏满batch+普通共100测量batch，成对独立及共同batch重新预检，失败停止。通过后才三epoch真实训练两初始化，检查全骨干梯度、实际64训练/16验证/16测试、validation-best、checkpoint重载及16条唯一ID测试预测；全流程仅Slurm，状态/失败记录保留，不计正式144。独立CPU Slurm诊断906剩余NequIP精确形状，不猜统计布局。

- 2026-11-04T19:01:01+08:00：MACE/NequIP真实带隙pilot执行计划：沿用已冻结895相同64/16/16、三epoch/初始batch2及CGCNN/ALIGNN的完整原包parity→64训练图→100batch成对容量→两初始化训练/验证选模/16测试预测流程。911实际两个provider各五项零skip通过为前置门禁；scratch只在完整64训练分区拟合原生邻居统计，原矩阵/配置不覆盖，解析统计单列记录。均用各自固定e3nn环境。AST/bash-n通过，不缩原架构、不隐式更改graph/精度，不计正式144。

- 2026-11-04T19:05:57+08:00?914?native parity????????????build_model??float32??cast???MACE artifact?float64?main run_training???to(dtype)?????????model_dtype?????float32?????????????????/????/64???/100batch????/????????????????????

- 2026-11-04T19:05:57+08:00：MACE/NequIP真实带隙pilot执行计划：沿用已冻结895相同64/16/16、三epoch/初始batch2及CGCNN/ALIGNN的完整原包parity→64训练图→100batch成对容量→两初始化训练/验证选模/16测试预测流程。911实际两个provider各五项零skip通过为前置门禁；scratch只在完整64训练分区拟合原生邻居统计，原矩阵/配置不覆盖，解析统计单列记录。均用各自固定e3nn环境。AST/bash-n通过，不缩原架构、不隐式更改graph/精度，不计正式144。

- 2026-11-04T19:22:37+08:00：首批真实带隙验收实际结果：912/913/916/915四管线均passed，每模型两版三epoch，共8次。回传四份64图scan/probe、各四worker（共1600测量batch）容量结果/正CUDA峰值/最坏索引、8份训练报告与16条测试预测；所有测试ID与manifest完全一致，history3/全骨干梯度>0/reload通过。冻结配置逐项相等；只补既有明确默认selection/seed、bias/adapter/feature_processing版本、resolved_components及绑定scratch统计。最初收据检查把已有默认字段当配置变更，已按原解析器明确默认规范化后做完整字典精确比较，未忽略任何显式设置或未知新增参数。910的17项零skip与911两provider各5项、五Git源码SHA均核验。

- 2026-11-04T19:25:08+08:00???????????????pilot?????/??/????README?????????????????????????/?????state???????????git diff --check????????/?????????????????????????????????

- 2026-11-04T21:06:58+08:00：第二批真实pilot计划：冻结895 classification/spectrum各四模型×两初始化共16训练，64/16/16、三epoch、初始batch2。复用已验收6a运行代码，532e8c6仅文档差异必须由Git验证；沿用910/911原构造证据且每模型重新做真实原包对照、完整64训练图、四次100batch成对容量、完整验证/测试与重载。MACE/NequIP各任务重新只拟合64训练图统计，模型对照显式按配置float32 cast。8请求AST/bash-n和16冻结case身份/参数检查通过；没有复用带隙训练权重或其诊断源统计，不计正式144。

- 2026-11-04T21:23:35+08:00：生成与自动解析单元计划：保留旧显式噪声协议，验证epoch/ID决定新噪声且batch/shuffle无关、train-only先验、val-best与完整test、精确resume、默认不全训练集采样、独立质量评测擦除参考几何且OOM不计科学无效样本。训练/生成/容量对MACE/NequIP scratch自动拟合/继承严格绑定统计，非法结果不触发OOM减batch。先运行协议/原生/生成解析与既有控制/成对控制纯std测试、隔离HEAD候选及AST/bash/README；发布后CPU Slurm运行真实Torch/Pymatgen/ASE及续训/回归/接线数值测试，随后实际CUDA任务/四原模型pilot与独立采样。不会在923/924活动时更新服务器checkout，也不把纯控制或去噪loss当生成质量。

- 2026-11-04T21:41:39+08:00：隔离候选执行结果：纯协议10、预检4、生成解析4、原生解析4、成对控制10共32项通过。一次误将test_structure_quality.py的六项Pymatgen/ASE数值测试列入-S本地纯控制；八个子场景在首次Pymatgen导入前即ModuleNotFoundError，未执行数值评分。已依据测试实际依赖重新归类，全部六项加入强制Slurm数值验收，预期总数40项零skip；不安装本地科学依赖、不删测试或降低标准。重建隔离候选复核32项与脚本AST/bash。

- 2026-11-04T21:55:37+08:00：生成/自动解析提交前：完整HEAD隔离候选32项纯std通过（协议10、预检4、生成解析4、原生解析4、成对10），新Python AST及Slurm bash-n通过，README/标准/协议的链接与围栏检查通过。Torch质量/结构评分全部迁至Slurm40项门禁，不宣称已过；新增相同函数内完整resume改变采样steps必须拒绝的数值断言。917–924的16版已回传并独立核验exact16测试ID、3200谱元素、四次100batch、全64图与所有显式配置保持，累计24版。

- 2026-11-04T22:04:03+08:00：分类指标补齐单元计划：新增严格2x2非负整数计数的balanced accuracy，定义为正负两类召回平均，缺一真实类别返回null。用13/3不平衡且总预测多数类的真实形状fixture验证accuracy=.8125而balanced=.5，并覆盖不同两类召回、非法矩阵与单类；SQLite真实累积流程仍保持原AUROC/F1。提供Slurm补算入口，只读已有8份classification report的confusion，校验16计数/来源SHA，另存补充JSON，原报告/预测/权重不改。纯std本地及隔离候选通过后发布；实际8版补算在Slurm，与原混淆矩阵和预测ID证据绑定。
- 2026-11-04：安装交付复核通过。普通 SSH 先校验并 pull 已发布 eda97a7 bundle，再读取 Slurm897 安装和899 GPU原始收据；安装状态 complete、GPU状态 passed，三个任务环境 Python 路径均存在。三个环境均为 Torch2.7.1+cu128/CUDA12.8，899实际设备RTX5090；复核未重复运行数值测试、安装或提交新作业。本次仅补充交付记录，未提交尚在独立验证的其他源码修改。

- 2026-11-04T22:16:43+08:00：生成验收收据修复计划：925的真实pytest输出为40 passed、16 subtests passed，JUnit只有40个testcase节点而tests汇总56，零failure/error/skipped；原固定tests=40断言错误。改为严格40个唯一主testcase、各文件期望覆盖10/4/5/4/6/5/5/1、全部主/子测试零错误零跳过，保留JUnit实际总计数；用925真实XML验证，并注入缺失用例/重复/失败/跳过检验均拒绝。修复后重新Slurm运行完整数值套件，925原失败不覆盖、不冒充作业成功。分类指标单元仍按已登记5项SQLite/非法/单类用例和隔离源码检查，新增回补脚本guard/只读来源检查。

- 2026-11-04T22:18:35+08:00：提交前检查通过：分类SQLite指标5项本地及HEAD隔离候选5项均通过；回补CLI在无Slurm且无科学依赖时先拒绝。修订收据逻辑接受925原始40主/16子测试JUnit，分别拒绝缺失/重复/主测试失败/跳过/汇总错误五种损坏证据，全部Python AST和Slurm bash-n通过。实际925因旧计数收据失败需重跑；926 Linux32项通过。尚未将回补代码或本地XML检查当8版真实Slurm补算/新数值作业完成。

- 2026-11-04T22:24:43+08:00：物理任务单元计划：新增可复用导数/几何验收，使用真实冻结配置的模型、device/dtype、原图与两初始化；在Slurm上检查响应对辅助场的独立中心差分、力/应力对几何的中心差分、混合参数梯度、平移/旋转、eval分批一致性和力场实际train模式。固定坐标不变模型张量仅承诺固定分量，不强行要求协变；等变路径按其O3/SO3承诺验收。固定FD h=.002、rtol=.02/atol=.002，几何rtol=.001/atol=.0002，不因真实失败放宽。另补force-field test energy_per_atom MAE/RMSE，保持原能量损失/权重不变；以2/4原子、原能量误差2/4验证每原子误差均1，覆盖batch1/2与force-only无伪能量指标。提交前AST/Slurm guard/文档检查；数值全部发布后Slurm，再真实四模型64/16/16试跑，不以合成用例替代真实物理验收。

- 2026-11-04T22:30:53+08:00：物理单元提交前静态检查通过：六份Python AST、Slurm bash-n及内嵌Python AST、CLI在-S无科学依赖/非Slurm时先拒绝、三份README链接/围栏正常。14项数值测试（4验收器正反例含CUDA、4 E/atom/force-only/不同batch、6既有完整留出/续训）全部指定发布后Slurm，未在本地跑Torch。927/928实际收据已回传核验：927八Git blob一致、40主/16子零错误零跳过；928八个原报告SHA使用observation保存的原始LF字节匹配，避免Windows落盘CRLF误报，并从原混淆计数独立重算全部指标。
- 2026-11-04：物理CLI发布前复审修正：邻居校准仅适用于official MACE/NequIP scratch，其他模型/初始化直接使用配置；此前CLI无条件调用会被校准器正确拒绝。已增加与训练路径一致的条件，AST和差异检查通过。尚未同步此单元或提交数值作业，14项真实数值门禁保持不变。

- 2026-11-04T22:39:16+08:00：929实际14项数值全部通过、零skip，GPU为RTX5090，五Git blob已核验回传。剩余24真实诊断请求检查：12管线/24冻结895 case，完整64/16/16、3epoch、batch2起步、generation100steps×2 inner保持；原构造代码自6a未变，每模型重新native parity；完整64原图/四次100batch成对CUDA→真实物理FD/几何→两版训练/全部测试ID/重载。生成另外每版8次独立留出条件采样，仅执行诊断、不冒称正式1000样本。12请求AST/bash及配置静态核验通过。请求完整内容和SHA保存在忽略claim，不直接修改远程源码。

- 2026-11-04T22:49:21+08:00：力场定义修复单元计划：实际runtime supervised_outputs只接受total_energy/forces/stress；旧recipes/tests共同写成energy，24份正式及8份诊断FF配置均无法执行。改为总能量输出total_energy、loss_weights同名、dataset.bindings.total_energy.key仍energy，原数据/单位/权重/结构划分和架构不变。新增跨模块测试，直接调用真实纯stdlib supervision函数验全部24格输出/绑定/权重合法，避免只镜像recipe；保留原定义/失败证据，新定义显式revision2。运行定义全套、pilot控制及隔离发布候选；发布后Slurm重建新的完整144定义并实际验证FF。不会修改运行中cf58checkout。另准备独立GPU重载诊断，先验证保存/重载参数buffer逐项完全相等，再比较同模型重复前向与双加载，保留当前预测容差，不因931失败放宽。

- 2026-11-04T22:54:18+08:00：FF定义修复提交前：7项定义控制和7项pilot控制在本地/隔离候选通过；直接实际监督协议验证24份FF输出/权重/绑定合法、拒绝旧energy输出。与冻结872逐项比较144份完整配置：120份完全相同、24份只更正输出/损失/绑定目标名，source标签energy和全部数据/划分/架构/预算完全保持。新增方法首次插入位置造成IndentationError已修正并完整重跑7项通过，未删断言或降低标准。AST、README及git diff检查通过。当前cf58远程作业仍运行；本修复仅本地提交，等待其全部终态再同步/Slurm重建新revision2定义。

- 2026-11-04T23:03:37+08:00：重载验收修复单元计划：942真实ALIGNN全部参数/buffer与checkpoint逐项相同；原CUDA模式同模型重复前向存在数e-6差异，deterministic algorithms=True在全部64记录均严格差异0。保持原float32 rtol1e-5/atol1e-6和float64标准，新增仅在重载比较作用域启用确定性计算、前置逐项state/dtype/shape完全相等检查，退出含异常恢复旧deterministic/warn_only；训练更新路径不改。训练入口在CUDA使用前setdefault CUBLAS_WORKSPACE_CONFIG，尊重显式环境值。Slurm测试参数/buffer/类型/布局损坏必须拒绝、RNG不变与异常恢复、实际CUDA对照；再跑完整heldout/force/generation/CLI回归，不用放宽容差消除失败。实际943/944诊断终态及结果需确认后才能同步/重新真实任务。

- 2026-11-04T23:08:04+08:00：重载作用域修复提交前：四Python AST、两Slurm bash/内嵌Python AST、README链接/围栏及Git差异通过。942/943/944原始报告已回传，三者参数/buffer state_exact=true、32batch/64记录，确定性阶段重复与双加载所有分量max_abs=0；普通CGCNN有46/50处重复/重载越原容差，MACE有2/3处。该证据支持确定性验证而非改变标准。新增7项状态/策略/CUDA测试及18项既有heldout/force/generation/CLI共25项将发布后Slurm；同时重跑40项生成套件并准备revision2全量矩阵。此处不宣称新代码数值验收或正式训练成功。

- 2026-11-04T23:17:08+08:00：945实际25项、946实际40主+16子数值均零错/零skip；947实际14控制与完整输入重核验/144定义revision2通过，三份收据源码SHA已核对Git blob。新7对/14次诊断请求AST/bash通过：从已冻结947父配置和895固定子集用公共pilot_config推导，逐字典证明仅FF三处输出/损失/绑定名称修正，其余参数不变。原13个未完成格加1个ALIGNN介电预训练重复对照；总唯一目标仍48，不按49累计。重做原包对照/全64图/4x100batch/物理与完整16测试/独立8采样；不复用预检权重、不减原100x2采样步。

- 2026-11-04T23:26:46+08:00:948实际CGCNN stress FD失败，00分量analytic=-.59258 vsnumeric=-.64313，其他力/几何/混合梯度通过。保持原rtol/atol，计划CPU Slurm对同一初始化和真实Cu帧以.002/.001/.0005/.0002/.0001做收敛，原生get_all_neighbors只观察不改结果，比较中心/正负应变12邻居索引与周期镜像；另将同一float32参数和几何复制为float64诊断以区分量化误差，不改变正式float32训练设置或图。数值全部Slurm，不先改测试标准。

- 2026-11-04T23:35:27+08:00：有限差分收敛单元计划：955的float32五步扫描实际证明CGCNN正00应变h=.002/.001改变原12邻居拓扑且误差.05055/.09854，h=.0005拓扑一致且F/stress原容差全部通过（应力误差.0004896）；更小h力出现量化误差。955整体FAILED因为后续float64旧helper的零张量dtype不匹配，保留失败，不把partial当整作业成功。改为统一预声明h=[.002,.001,.0005,.00025,.000125]，力/应力分别要求相邻两个中心差分均匹配解析值且彼此一致，仍rtol=.02/atol=.002；选最大的收敛步长对，不按模型手工放宽。纯std测试包含跨离散边界但局部可微函数、错误解析值/仅单步偶然匹配/不收敛必须拒绝、非有限/非法步长。修复旧数值helper的typed zero且增加float64实际回归。发布后Slurm19主测试、两个真实不变骨干两初始化与原协议比较；不改官方图/参数、训练dtype或数据。

- 2026-11-04T23:50:16+08:00：生成数值失败类型单元计划：954 pretrained三epoch训练/完整留出/重载已通过，但独立采样在实际MACE NativeFeatures.validate因Nonfinite node output抛ValueError终止，未进入scratch。只将非有限数值特征明确归类FloatingPointError，保持维度/语义/设备等结构契约ValueError与OOM原样致命，不捕获所有ValueError、不更改采样步数/参数或丢弃条件。新增通过真实NativeFeatures.validate触发节点/图特征非有限错误的端到端质量测试，完整2次尝试均记录为无效且指标0；错误shape仍终止且无完成收据。原OOM测试保持。质量用例4增至7，生成全套40增至43主用例，严格各模块覆盖/零skip；发布后Slurm及真实954采样续评验证。

- 2026-11-05T00:06:38+08:00：FD收敛与数值失败两单元提交前：12文件隔离候选建立，4项纯std收敛控制本地/隔离均通过；相关Python AST、两Slurm bash/内嵌Python AST、README链接/围栏及Git差异通过。原rtol/.atol、图、权重、训练dtype和采样100x2不变；新19主物理回归及43主生成回归必须发布后Slurm，尚不宣称数值通过。原955FAILED及float32完整五步/拓扑证据原样归档。954采样失败保留，新增真实NativeFeatures非有限/形状/OOM分类测试不放宽形状契约、不丢条件。旧948–955均已终态，允许同步。

- 2026-11-05T00:28:40+08:00：长作业版本隔离计划：根仓库仍每次连接先校验/pull已推送提交；对该已确认本地Git remote仅做git clone --shared到新runs/source-checkouts/COMMIT，不用编辑器/patch改服务器源码。确认data/models/runs均不在Git受管树后只链接共享忽略数据/模型/结果，cache受管源必须HEAD固定且git status clean，已有目录不覆盖。后续Slurm显式cd缓存/PYTHONPATH缓存src并验证实际包路径，保护长训练不受根仓库后续pull影响。现阶段仅Git/路径轻量检查，GPU导入/数值仍须Slurm。

- 2026-11-05T00:33:09+08:00：956物理19主/6子、957生成43主/16子零错/零skip，源码SHA与8dba196 Git blob一致；958完成原float64五步诊断，h=.0005及更小F/stress原标准通过且拓扑稳定。固定8d源码缓存Git克隆/HEAD/clean/三共享数据链接检查通过，受管源无服务器编辑。新3对请求AST/bash通过，使用snapshot cwd/PYTHONPATH并在Slurm验证实际包源路径，来自947+895的全部科学配置保持；只有CGCNN/ALIGNN力场和MACE生成各两版，MACE pretrained重跑不重复累计已有训练。

- 2026-11-05T00:57:05+08:00：全量MLearn预检执行前计划：MACE/NequIP各seed123从947冻结完整144中选两初始化，严格1309train/93val/164test、float32、300epoch/patience30预算、初始batch4/max_atoms null、真实total_energy+forces绑定。已通过950/951小规模两版及956/957当前数值门禁；在固定8dGit缓存验证包路径，复做两真实完整训练输入的原包对照，扫描全部1309原生图，再两种初始化独立+共同batch共4x100真实完整训练步（仅预检，权重不留），只有真实OOM减batch。之后两mode分别在扫描选出的最坏结构做导数/几何/分批验收，scratch统计必须1309来源绑定。所有显式配置除batch/已核验train-only统计不变；20GiB预留；全部证据成功才发布可训练准备收据。该阶段不启动正式训练、不计144完成。请求AST/bash及4份冻结完整配置检查通过。

- 2026-11-05T01:12:50+08:00:959CGCNN scratch力FD不收敛，h越小误差越大且数字量化（.000125时步进约.061），stress及几何检查通过；960/961两版完整管线通过。计划只读GPU诊断同一seed/完整配置，先预热模块再重设123构建，复制相同参数分别确定性float32/float64验证，和959解析力对照以确认复现同一实例。原训练dtype不改、误差标准不变，clone inside任务固定8d缓存；全部计算Slurm。
- 2026-11-05 01:18 +08:00：用户要求继续安装并在完成后告知。本轮先核对既有安装证据，预期897安装complete、898/899作业COMPLETED且0:0、898报告passed、899三个环境均passed并报告Torch2.7.1+cu128/CUDA12.8；实际纯stdlib断言全部通过。所需依赖此前已安装，未重复安装或在登录节点运行数值测试；初次只读查看把892包清单误当对象的辅助命令已改为按实际结构化验收报告检查，最终验证退出0。环境路径与版本记录见env.md。
- 2026-11-05 01:25 +08:00：差分参考精度实现单元计划：964同一959参数解析力完全重现，确定性float32仍失败，而参数副本float64全检查通过、解析力仅差2.8e-6；963 NequIP完整最坏输入同类力FD失败。保留实际float32模型的解析导数、混合梯度及几何/分批检查，仅对独立能量差分使用相同参数值的float64深拷贝和原输入坐标的无损提升，记录两种dtype、不放宽误差/相邻收敛标准。测试包含能量大常量偏置的float32消减控制、错误力仍拒绝、原模型状态/dtype不变、已有float64路径；全部数值在Slurm。MACE962已完整通过，另准备从原947定义和962配置直接调用既有run_training的两份正式Slurm请求，不改完整划分/300epoch/early stopping预算。
- 2026-11-05 01:34 +08:00：独立差分参考精度提交前检查完成：4项纯控制在工作树与独立Git归档候选各通过；修改Python AST、Slurm bash/内嵌Python AST、README路径/围栏及正式MACE请求AST通过。新GPU回归将由19主增至22主（大偏置float32/float64、错误力大偏置拒绝），尚未运行，不宣称数值成功。实现仅复制独立能量参考到float64，实际训练/解析/几何/分批精度不变，rtol .02/atol .002及相邻收敛不变。962 MACE已经通过原19项和完整输入验收，长训练将固定8d源码而非随根仓库更新。

- 2026-11-05T01:29:56+08:00：长作业版本隔离计划：根仓库仍每次连接先校验/pull已推送提交；对该已确认本地Git remote仅做git clone --shared到新runs/source-checkouts/COMMIT，不用编辑器/patch改服务器源码。确认data/models/runs均不在Git受管树后只链接共享忽略数据/模型/结果，cache受管源必须HEAD固定且git status clean，已有目录不覆盖。后续Slurm显式cd缓存/PYTHONPATH缓存src并验证实际包路径，保护长训练不受根仓库后续pull影响。现阶段仅Git/路径轻量检查，GPU导入/数值仍须Slurm。

- 2026-11-05T01:33:08+08:00: 正式MACE两版请求验收计划：947冻结完整配置/962全量通过门禁、1309/93/164、300epoch/30patience、B4、f32、全部骨干更新，唯一case全局claim；固定8d缓存，epoch逐次保存及事件记录，实际全量训练和精确164测试ID/val-best/Eatom/原状态重载/梯度/资源收据验收。两份请求AST/bash通过；22主物理965必须真实passed才提交本批，先运行两个短GPU实际失败输入复查再释放正式作业。CGCNN仅训练缺失scratch三epoch，复用959全部未变模型/训练/数据源的4x100和64图；NequIP只复查963最坏导数两模式，不重复全图容量。

- 2026-11-05T01:37:41+08:00: 966/967在计算前把README当作Python源码差异而失败，没有生成root或训练。修正请求为严格核对src下.py变更仅derivatives，已在本地实际Git差异通过；AST及四请求bash通过。追加CPU相同输入诊断与GPU验收两组，CPU不训练、不充当CUDA通过；保持失败请求与日志。968实际运行且首epoch完整验证已见，不中断；969若仍PENDING且精确jobname/归属匹配，只调整调度依赖，让短GPU复查先于scratch，科学配置不变。

- 2026-11-05T01:45:42+08:00: 970实证NequIP能量副本double后内部固定float32输出导致matmul dtype失败；971CGCNN CPU同输入物理全部通过。只读本机既有官方NequIP zip源码定位BesselEdgeLengthEncoding/SphericalHarmonicEdgeAttrs/AddRadialCutoffToData的_output_dtype显式转换（不执行本地模型）。计划CPU Slurm以局部mock只在深拷贝的能量参考同步这三类输出dtype，再比较真实完整最坏输入两模式/原参数buffer严格不变；这是诊断，不计CUDA通过。AST/bash通过。
- 2026-11-05 01:53 +08:00：NequIP参考精度兼容单元计划：974实际完整最坏输入的pretrained/scratch CPU检查均通过，仅在深拷贝能量参考把两个官方embedding的_output_dtype从float32同步为float64，原参数buffer完全不变。实现放入validation/precision.py，按官方artifact provider及三类已核对NequIP embedding限定策略，不修改backbone源文件（保留既有全图/训练统计来源hash）。新增已知cast只改副本/参数数值精确提升、其他provider同名属性不改两项测试；原模型实际解析/训练dtype不变，完整回归22增至24主。当前965的22主及源码SHA已独立验收，新增13报告去重后47/48诊断、64独立生成样本已核验；初次联合计数发现旧bandgap摘要没有task字段，按其文件明确的bandgap作用域补齐后重新全部断言通过，不改变科学结果。
- 2026-11-05 01:57 +08:00：NequIP兼容提交前检查：validation精度helper、调用、两项provider边界/状态测试AST与24主Slurm bash/内嵌Python AST通过；4项步长控制在工作树和新独立候选各通过，README链接/围栏检查通过。965原22主/6子GPU报告及8个执行源码Git blob SHA独立复核成功；974实际两模式CPU通过和原状态精确保留已回传，仅为新兼容策略直接证据。新增24主回归仍待发布后Slurm；未运行的测试不宣称通过。正式968正在固定8d缓存训练，源码发布不改变该缓存或共享环境。

- 2026-11-05T01:52:35+08:00：长作业版本隔离计划：根仓库仍每次连接先校验/pull已推送提交；对该已确认本地Git remote仅做git clone --shared到新runs/source-checkouts/COMMIT，不用编辑器/patch改服务器源码。确认data/models/runs均不在Git受管树后只链接共享忽略数据/模型/结果，cache受管源必须HEAD固定且git status clean，已有目录不覆盖。后续Slurm显式cd缓存/PYTHONPATH缓存src并验证实际包路径，保护长训练不受根仓库后续pull影响。现阶段仅Git/路径轻量检查，GPU导入/数值仍须Slurm。

- 2026-11-05T01:54:03+08:00: 发布7b兼容后完整24主回归分别CPU立即与GPU排队，NequIP完整最坏输入两模式分别afterok对应回归；CPU报告/实际设备严格单列，不能计CUDA验收。脚本沿用已提交的GPU验收器，仅CPU任务显式切换设备/报告路径/设备断言；数值标准和24主分组不变。固定7b缓存、AST/bash通过。969仅调整调度依赖至973及新NequIP GPU句柄，968不变。

- 2026-11-05T01:55:54+08:00: CGCNN/ALIGNN完整MLearn预检计划：沿用已验收962完整准备流程与947冻结seed123两模式配置，1309/93/164/300ep/初始B4/f32；原包对照、全部1309原生图、4x100完整更新容量及最坏导数，只有typed OOM降batch。依赖新97624主GPU通过，CGCNN另依赖973最后scratch；旧959/新973分别明确pretrained/scratch证据，不伪称旧959全部passed。仅复用未变backbone/engine/tasks/data等源，实际Git差异门禁；配置语义与数据不变，全部预检不计正式训练。请求AST/bash通过。
- 2026-11-05 01:58 +08:00：新增24主/6子CPU回归975零错/零skip，按7b3f872逐项Git blob SHA核验全部9源文件；977实际NequIP完整最坏输入两模式CPU全部物理检查通过，actual float32/reference float64，只有两个已知embedding参考dtype调整，1309完整准备/容量来源963保持绑定。证据已回传results/paper-environment-20261104/nequip-reference-compatibility/verified.json。GPU976/978仍排队，不计CUDA验收。968实际RUNNING23:42，完整36epoch及best/last更新可见；969 PENDING等待973/978/979/980；全部句柄已有权威队列证据，不重启。当前47/48诊断/64样本、正式完成0/144、提交2/144。
- 2026-11-05 02:03 +08:00：标量均值基线单元计划（计划第5节必需）：新benchmarks/baselines模块、独立README与Slurm CLI，以固定完整标准JSONL及manifest为输入，两遍流式核验数据原始SHA/全部有序ID/清单SHA，只在train拟合一个均值，再对全部val/test写预测和原单位MAE/RMSE。不得复用模型训练的归一化或测试统计。测试覆盖留出极值不影响拟合、精确预测计数/误差、源字节/ID/manifest变更拒绝、非有限标量拒绝及既有输出不覆盖；纯stdlib小fixture与静态检查在本地，完整75993数据只在Slurm CPU执行。此前目标轮为progress：已启动正式968/969、47诊断独立核验并实现/验收数值参考；本轮新观察968为RUNNING、42epoch，不重启已有句柄。
- 2026-11-05 02:06 +08:00：标量基线提交前：6项纯stdlib控制在工作树与隔离Git归档候选各通过；覆盖训练均值不含留出极值、val/test全计数及原单位误差、源字节SHA、manifest SHA与有序ID、非有限/非标量标签、既有结果保护和拒绝部分选择。CLI无Slurm门禁实际触发，所有新增Python AST、Slurm bash及模块README检查通过。完整75,993源及60,823训练均值尚未执行，不计正式训练。使用Python float64原始存储标签运算并明确记录，既有模型训练/数据/缓存不变。

- 2026-11-05T02:09:38+08:00：长作业版本隔离计划：根仓库仍每次连接先校验/pull已推送提交；对该已确认本地Git remote仅做git clone --shared到新runs/source-checkouts/COMMIT，不用编辑器/patch改服务器源码。确认data/models/runs均不在Git受管树后只链接共享忽略数据/模型/结果，cache受管源必须HEAD固定且git status clean，已有目录不覆盖。后续Slurm显式cd缓存/PYTHONPATH缓存src并验证实际包路径，保护长训练不受根仓库后续pull影响。现阶段仅Git/路径轻量检查，GPU导入/数值仍须Slurm。

- 2026-11-05T02:11:13+08:00: 完整标量基线执行计划：Slurm CPU1/4GiB/20min先6主unit零skip，再CLI对947固定全量JARVIS75,993源拟合60,823train均值，完整7,590val/7,580test。独立fsum复算训练均值并核验全部15,170留出ID/role/原标签/恒定预测及MAE/RMSE，记录6源SHA、代码版本、CPU成本与共享24个bandgap主配置。全部实际数据处理Slurm，无GPU、不改变正式968/969及队列。请求AST/bash通过。
- 2026-11-05 02:20 +08:00：Slurm981完整基线passed并独立回传核验：6主/8子控制零错误/零skip，六个执行源SHA按da3ba0e Git blob逐项一致；完整源75,993、train60,823、val7,590/test7,580及15,170预测唯一ID/角色/原单位全部验证。Slurm用独立fsum均值/误差复算通过；train均值0.6134805090179745eV，test MAE0.9069491664922338/RMSE1.3388291888967387eV。完整原始收据/JUnit/预测及SHA索引保存在results/paper-baselines-20261105/scalar-981/，不计144训练。最近正式968 RUNNING44:51、完整69epoch；所有其他GPU句柄仍PENDING，未重启。
- 2026-11-05 02:24 +08:00：本轮结果文档提交前检查：计划所有本地链接/精确Markdown围栏、状态三分区与追加历史、表中均值及test MAE/RMSE文本与981 verified.json逐项一致；git diff --check通过。仅更新实际阶段记录及已完成准备项，无新数值代码，不重复运行已通过6主控制或改变队列。
- 2026-11-05 02:26 +08:00：最新记录b0f337e已推送并离线pull到根仓库；只读复核968仍RUNNING52:46、完整82epoch且best/last更新，969/973/976/978/979/980仍PENDING。固定缓存/科学配置不变，没有重提或取消新作业；981完整基线证据保持通过。
- 2026-11-05 02:32 +08:00：容量证据/正式启动单元计划：当前968 RUNNING56:46、88epoch；上一轮为progress（完整981基线通过）。静态复审证实外层full_forcefield_prepare_job和formal wrapper的rglob(result.json)固定len=4会把合法typed CUDA OOM重试当失败，与用户batch递减要求冲突。新增pairing/evidence.py按capacity.trials及每个preflight.attempts验证SHA链、exit42+cuda_out_of_memory、严格减半、最终成功完整100batch/最坏覆盖及末轮两模式共同batch；未知错误/未完成/错误身份/遗漏最坏/篡改SHA拒绝。纯metadata fixture含OOM后成功、多轮共同batch重试、无OOM和损坏变体；本地/隔离控制及静态检查后发布，不改GNN、图、物理误差或训练预算。仅精确核对并替换仍PENDING的979/980，更新969依赖，968不动。随后提交NequIP/ALIGNN/CGCNN各两版正式案例，afterok实际全量门禁并等待现有MACE两版，防重复全局case claim。
- 2026-11-05 02:40 +08:00：容量证据提交前：6主/8子纯metadata控制在工作树与独立Git归档候选各通过，实际调用原paired controller/disposable subprocess生成typed-OOM与重复共同轮次证据（不执行模型、不计CUDA通过）。保留32→16→8及scratch32→16→8→4等全部失败尝试、正确共同4/2；未知错误/非42/非typed/测量不足/最坏遗漏/phase或request错配/父SHA与共同batch篡改全部拒绝。新helper在原样回传962/963全目录布局也接受各4成功worker/common4，未改变NequIP整体FD仍未通过的事实。AST通过；README示例改用947有效定义。新helper不更改任何模型或数值算法。

- 2026-11-05T02:45:46+08:00：长作业版本隔离计划：根仓库仍每次连接先校验/pull已推送提交；对该已确认本地Git remote仅做git clone --shared到新runs/source-checkouts/COMMIT，不用编辑器/patch改服务器源码。确认data/models/runs均不在Git受管树后只链接共享忽略数据/模型/结果，cache受管源必须HEAD固定且git status clean，已有目录不覆盖。后续Slurm显式cd缓存/PYTHONPATH缓存src并验证实际包路径，保护长训练不受根仓库后续pull影响。现阶段仅Git/路径轻量检查，GPU导入/数值仍须Slurm。

- 2026-11-05T02:53:39+08:00: 新容量控制982实际passed及5源SHA匹配后才执行本批。两份完整预检/六份正式任务请求AST与bash通过；case精确947配置、1309/93/164、300epoch/30patience/f32、全局launch claim均预检。正式请求用新evidence验收全部合法重试，NequIP复用963容量+978新GPU物理门禁，并要求模型/训练/图Python源和依赖版本与既有准备完全一致；CGCNN/ALIGNN用替换后的新完整准备。仅typed OOM改batch，科学设置不变。六正式均afterok对应全量门禁且afterany969，仍0完成；不把条件提交当准备通过。
- 2026-11-05 03:00 +08:00：982实际pytest收集失败：tests.test_paired_capacity包导入在服务器不可解析，未执行容量fixture，控制报告未生成；后续提交器在首个报告门禁停止，已读权威队列/日志确认remaining-forcefields claim不存在、未hold/cancel或提交六case。修正为按__file__同目录runpy加载既有fixture，不依赖tests包解析；保持6主/8子和全部标准。计划在隔离候选中加入被占用tests包的模拟加载/完整六项运行，之后新Slurm作业，不覆盖982。现有968仍RUNNING1:23:16、其他原句柄未变。
- 2026-11-05 03:02 +08:00：fixture导入修复提交前：在新独立Git归档候选中人为占用sys.modules['tests']并提供空包路径，按真实文件加载后完整6主/8子全部通过；无删测/跳过/放宽断言。Python AST及git差异检查通过。982失败JUnit/日志已保留，新的Linux Slurm复验仍待同步；六个正式case尚未提交，原979/980未更换、968保持运行。
