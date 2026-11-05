# ustc-gpu 接入许可更新

2026-11-03 用户确认最新用户指南已允许 Codex 通过 SSH 接入，旧登录公告已经过时。
据旧横幅得出的“不能继续接入”判断已由此次用户说明更新；今后参考
[当前接入约定](ustc-gpu.md)，不要将下方历史退出记录当作现行禁止规则。

# 经验记录

## 2026-11-02：任务覆盖与模型前提优先

- 用户明确“覆盖任务而非实现对齐”、等变/可微/节点特征前提后，不能继续把原 ALIGNN 读出/边特征/导数机制当作必须满足的契约。当前设计已采用节点主接口、可替换读出和任务级验收。
- GMTNet 风格读出要区分可微张量网络、固定结构对称投影和离散空间群识别。用于扰动响应时，冻结高对称投影也可能消去真实导数，不能简单把预处理固定就声称解决所有求导问题。
- 在变胞生成中，分数坐标位移与概率 score 的坐标变换不同；需与噪声/损失的变量约定一起验证，而非将任意节点向量直接解释为 fractional score。

## 2026-11-02：ALIGNN 下游保留与接口解耦

- 用户要求保留既有下游时，应直接在固定版本上游内抽离 backbone 和工厂依赖；不能借通用化重建 trainer、改变输出头或升级张量/生成算法。
- ALIGNN 的监督模型类混合了 stem/消息传递、pooling/head、能量修正及导数；CSP 也把 GNN 与坐标/晶格/角头放在一起。解耦边界要依源码划定，以原 forward/loss/梯度/训练恢复行为回归证明保留。
- 当前有效设计已收敛到 docs/plan/gnn_task_toolkit.md 的上游 fork 方案；此前通用框架思路不是当前实施范围。

## 2026-11-02：通用 GNN 任务封装的边界

- 模型的张量输出形状、表示的旋转变换规律、坐标梯度连通性和 timestep 条件接口必须分别描述；形状匹配不代表能做保守力场、方向张量或扩散生成。
- 冻结模型参数不等于关闭输入 autograd。离线 frozen 特征适合固定输入读出，不能用于依赖坐标导数或采样中几何变化的任务。
- 共享框架不等于同一 checkpoint 支持全部能力。适配器与任务的能力声明应有小样本物理验证，模型原生后端与统一结构契约分别维护；长期设计见 docs/plan/gnn_task_toolkit.md。

## 2026-11-02：SSH 本地权限阻塞

- 当前执行环境中的 ssh.exe 未加载用户 Host 别名，显式 -F 访问 C:/Users/asus/.ssh/config 亦返回 Permission denied；这属于连接前的本地访问控制问题，不能据此判断服务器或网络故障。
- 多次失败后检查既有经验并停止重复连接；当受控提权通道明确返回 sandbox_approval=false 时，不复制私钥、不改配置或绕过控制。用户修改设置后仍须以实际执行结果确认权限是否在当前环境生效。

## 2026-11-01：数据存储估算

- Figshare item 的 Download all 和 HF 仓库总量可能同时包括同一数据的压缩/原始格式、JSON/JSONL、多个版本、划分和全量副本，应按任务所需文件去重。
- 估算中要区分未经压缩的 MPtrj JSON、压缩 OQMD SQL、导入后的数据库以及训练图缓存；不能对每项统一乘“解压倍率”。部分 Figshare API 不可抓取时，使用已成功读取的官方大文件元数据作为锚点，其余标区间，不反复重试或虚构精确总量。

## 2026-11-01：公开资源核查与网络限制

- 本环境普通 Python HTTP 请求遭 WinError 10013，web 工具对部分 Figshare/Hugging Face 链接也无法抓取。连续多个请求失败后停止同一路径重试，改查官方 Git 源码和作者补充仓库；不把访问受限判成资源不存在或私有。
- `git clone --filter=blob:none --no-checkout` 可查看完整路径，但后续 sparse checkout 可能触发额外网络请求而被当前环境限制；文件路径存在不等同于已经读取内容。
- ALIGNN 2.0 的主要模型仓库、Leaderboard 贡献与作者 CSP 消融仓库分别维护，不能仅查模型仓库就断言评测脚本或数据缺失。

## 2026-11-02 00:09:37 +08:00：Slurm 目录占用统计

- 本地磁盘目录须限定到存储所在节点；Guqq2 的 /home/xmz 位于 node42 本地根分区，本次通过 --nodelist=node42 保证路径一致。
- 集群若提示 Slurm accounting storage is disabled，可在作业记录仍保留时使用 scontrol show job 核对 JobState、ExitCode、NodeList 和日志路径，无需重复扫描。

## 2026-11-02：GMTNet 求导读出与对称模块分开

- 用户最终范围只采用辅助变量响应的 Jacobian 读出，不接空间群识别或晶体对称约束；此前关于该离散模块的困难不再适用于当前设计。
- 求导式读出要明确响应函数和求导变量，保留张量损失更新模型所需的计算图；不能只将其理解为普通输出头可微。

## 2026-11-02：张量换基与任务读出区分

- CartesianTensor 需要匹配目标 irreps 的系数，不将任意高维隐藏表示自动变成某种物理张量。应先做可学习等变映射，再换基。
- rank、l、parity 和 multiplicity 是不同概念；不附加指标约束的通用 polar rank-r 张量为 3^r 维，不能误用仅含最高阶谐波的表示或库文档的全对称示例。

## 2026-11-02：输出格式与构造操作分层

- 相同 shape 不足以确定表示：点/向量、晶格基向量组/二阶材料张量、采样网格轴/独立通道必须区分。性质名称可从核心移除，变换规则、单位与聚合等仍应显式配置。
- direct/derivative 是构造关系，生成/模拟是 workflow，不与张量阶数混为同一分类轴。架构边界与接口记录在 docs/plan/gnn_task_toolkit.md §3，后续模块 README 延续这一约定。
- 性质库可以承载名称、定义和默认规格，解析后仍交给通用核心；数据列/源单位属于 DatasetBinding，生成/模拟属于 workflow。目录登记与模型兼容、数据可用、评测完成应分别记录，避免将配置覆盖误报为已验证支持。

## 2026-11-02：等变架构与可训练特征接口分别验收

- 等变势最后一层可能已不变量化（当前 NequIP 构造器强制末层标量，TensorNet forward 将内部张量变成不变量）；适配器应允许选择中间层，不能把架构等变等同于最终输出保留全部表示。
- 原始 EquiformerV2 edge_rot_mat.py 返回 detached 旋转矩阵，独立 force head 也不等于能量负梯度；宣称几何全过程可微前须检查方向、距离及旋转路径。对具体实现的发现不能泛化为所有同名架构都不可微。
- 描述符/推理便捷接口可能返回 NumPy 或 detached embeddings；MACE/UMA 训练适配应接底层 Torch backbone，并单独验证参数、坐标/晶胞及所需高阶导数。

## 2026-11-02：不变骨干与方向性任务兼容

- 不变通道可用 Cx0e 纳入统一节点规格，但仅从 0e 做线性或张量积映射不能产生 l>0；几何基底、非标量输入条件或完整几何导数才提供方向来源。裸 MLP reshape 不能当作满足变换规则的一般张量读出。
- 不变能量可以产生等变力/应力，不要求隐藏表示本身包含向量；必须验证距离、角度和晶胞均在正确求导链中。ALIGNN 的预计算几何特征应与可微任务区分，不能将静态图中的角度常量误当作完整坐标依赖。
- Equiformer 与 EquiformerV2 是不同适配目标，某版实现的梯度限制不自动适用于整个家族。首批模型范围按用户选择记录在计划 §3.5/§3.6，后续模块 README 记录具体版本与能力。

## 2026-11-02：CGCNN/MEGNet 架构与数据/后端分开

- CGCNN 原数据管线在 NumPy 中展开距离；可微任务需要在目标张量框架中由坐标/晶胞和 PBC 镜像重算距离。模型 forward 对输入边特征可微，不等于原数据管线已经连通坐标梯度。
- MEGNet 的图级 state 输入和更新状态应保留为可选上下文/输出，不可只抽节点而静默丢弃其状态语义。原 TensorFlow/Keras 包与 MatGL 的 Torch 实现属于不同实现/权重目标，不能靠 NumPy 桥接声称梯度或 checkpoint 自动兼容。

## 2026-11-02：响应默认求导与配置展开

- 用户指定已支持响应性质默认求导，默认值应放在性质库响应条目中，展开为明确的响应源、辅助变量、阶数和参考点；不从 shape 推断，也不在梯度能力不足时静默退回直接读出。
- 辅助变量即使在零参考点，也需保留函数依赖后再求 Jacobian；响应监督要能反传到读出/骨干，并区分每样本导数与跨批交叉项。响应函数不必有独立标签或与力场共用能量，直接读出仅作为明确覆盖，架构约定见计划 §3.4/§5。

## 2026-11-02：统一读出前的特征适配边界

- native/geometry 差异前移到 UnifiedFeatureAdapter，固定 profile 后读出不再按模型分支；等变原生信息保留，不变骨干通过多方向几何耦合补充类型。相同维数不代表跨 backbone 语义对齐，共享已训练读出权重需另行联合训练/对齐。
- 单方向球谐只有自然 parity；构造一般张量类型需要不同通道/邻域矩的张量积，不能用同一向量自身叉乘补轴向信息。符号类型可达性不等于数值非零或表达完备性。
- 冻结节点缓存后用几何提升得到的梯度只包含新增几何分支，不包含原特征对几何的依赖，不能据此宣称已恢复完整能量/力梯度。接口与长期模块边界见 docs/plan/unified_feature_adapter.md，实施后写入 adapters/README。

## 2026-11-02：ALIGNN 分量读出与求导/等变保证分别说明

- 固定快照的 tensor recipe 是 D 维分量回归，不能因名称包含 response/tensor 就描述为辅助变量 Jacobian 读出。
- 若以 R(H,q)=A(H)q 构造求导响应，其 Jacobian 等价于 A(H)，不能声称仅包一层求导就新增旋转等变或热力学一致性。construction 与 transformation_guarantee 应分别记录，固定坐标分量与等变张量不能在评测中混称。
- 统一公共 API 可以保留不变标量/等变两类 backend；只有要求相同等变输入规格时才必须补全类型，不应把几何提升强加到全部标量或能量求导任务。可选模式边界见统一适配设计 §6。

## 2026-11-02：评审稿的架构与实施规格分开

- 新增可选路线后，必须同步默认值适用范围、配置示例和验收；共同等变 profile 中的 hybrid 建议不能被误读为不变轻量路线的全局默认。
- 固定坐标分量与等变响应按各自声明验收，不因共用 API 就混称同一变换保证。接口/版本、性质数据清单及完整生成配方未冻结时，应明确为可进入原型的架构稿，不声称已是最终实施规格。

## 2026-11-02：生成去噪接口与坐标类型

- 生成适配是条件去噪任务，不等同于把物性头输出维度改为 3；需在带噪结构/晶格上逐步重算特征，并记录时间/晶格条件的注入位置。
- 行向量 r=fL 下，位移满足 delta_r=delta_f L，固定 L 的概率 score 满足 s_f=s_r L^T；不能把两者按同一个矩阵规则转换。预测对象必须携带 target_kind/coordinate_basis/尺度与晶格参数化版本。
- wrapped-normal 的 scaled_score 与未包裹高斯噪声不是所有噪声区间都等价；生成 score 默认直接预测，不把响应默认 Jacobian 或物理能量梯度强加到去噪头。具体协议与未冻结项记录在主计划 §7。

## 2026-11-02 14:23:24 +08:00：本地执行工具初始化故障

- 普通 exec 多次在进程创建前返回 helper_unknown_error: setup refresh had errors，Node 文件接口亦出现相同沙箱初始化故障；这不是项目命令自身失败。停止重复普通调用，通过受控权限执行用户已授权的同一操作，并保持精确绝对路径及删除前后验证。

## 实现环境安装：ensurepip 与 SSH 代理

- Guqq2 系统 Python 无 ensurepip；使用任务 venv --without-pip 和官方 pip/PySocks wheel 引导，不改系统包。
- 现有健康代理可能由其他会话持有并在安装期间断开；pip 的 Connection refused 表示必须重新诊断监听/持有者，不能盲目重跑安装或假定新工作 SSH 接管转发。确认端口释放后新建本任务专用持有会话，限制 pip 自动重试。
- Windows SSH 传多行包含引号的远程 Python 代码会失真；固定脚本用 UTF-8/base64 经 stdin 解码到 bash 执行，不插入任何密钥内容。

- 2026-11-02 15:18:20 +0800：MACE 0.3.16 固定 e3nn 0.4.4，而 NequIP 0.14 需要 >=0.5.6，使用独立 venv。旧 e3nn 常量文件包含 builtin slice，Torch>=2.6 默认安全加载拒绝；仅在导入可信 e3nn 常量期间 scoped safe_globals([slice])，模型 checkpoint 继续 weights_only=True，不全局放宽反序列化。

- 2026-11-02 15:23:23 +08:00：连续两次远端 pip 下载和一次 scp 大包传输均被 Vlab 连接断开。已复查代理经验：本地公开 HTTPS 正常，源码短时 pull 成功，但不能据此假定大文件 SSH 长连接稳定。后续资源传输改用 SFTP reput 续传，先核对远端部分文件大小并最终按 manifest 校验；不得重启仍健康的独立代理，不重复从零传同一大文件。

- 2026-11-02 15:47:10 +08:00：只读复用环境应以 distribution.locate_file 取得真实包目录；将父 venv site-packages 加入 .pth 不会递归处理父目录中的 .pth。先断言关键分发版本/实际路径，再运行有约束的 pip，避免缺依赖识别导致大型Torch/CUDA重新解析。

- 2026-11-02 16:31:45 +08:00：Vlab下SFTP方式scp出现部分文件后无响应；legacy scp -O的小gzip数据包成功。大量漂亮JSON应先gzip，624640字节tar压成102730字节。已下载的pip wheel可按官方URL的CacheControl键从http-v2/*.body恢复，必须先核对官方SHA256，再进入任务wheelhouse；仅查找明确列出的包，不扫描/改写其他项目缓存。持续普通工作会话先pull后复用，可减少握手开销。

- 2026-11-02 17:09:09 +08:00：Hugging Face元数据可取，但MatPES range、Tiny HDF5 curl和SDK HTTP回退连续遇到CDN TLS EOF/超时。复查网络经验后停止重试同一路径；改取小型公开provenance下载清单，直接访问其原始Figshare DFPT文件。仍以原文件哈希、记录ID和同一几何标签核对，不因第三方镜像声明跳过核验。

- 2026-11-02T18:11:15.739246+08:00：abTEM离线61.9MiB依赖包经legacy scp和两次SFTP连续中断；关闭普通连接仍失败，排除简单第三连接冲突。专用代理进程仍在；不重启代理。下一步改用PTY持有SFTP并限制速率进行断点传输，以区分工具管道生命周期与链路故障。禁止为诊断直接打印整份SSH配置（包含无关主机信息）；后续仅读取指定Host必要字段。

- 2026-11-02T18:26:16.239271+08:00：大包SCP/SFTP三次中断后，反向SOCKS可访问本地127.0.0.1上的任务专用HTTP服务，已实传31.87MB；速率约0.25MiB/s，120秒上限不足。采用显式Range端点和curl续传，仍核完整SHA256，不重启健康代理或把端口对外公开。普通SSH有限命令成功，诊断时不以无提示交互bash判断连接失败。

- 2026-11-02T18:35:43.907268+08:00：abTEM1.0.8虽允许pip在Py310安装，实际直接from typing import Self导致6工作流同因失败；不反复重跑或全局monkeypatch typing。回查官方PyPI后改选支持>=3.9,<3.12的1.0.6，并先检查wheel源码/API与依赖再Slurm复核。

- 2026-11-02T18:52:18.363550+08:00：CRD原始raman_tensors并非每条都有3N槽，不能将短列表按频率顺序强行对齐或补None推测；筛选同时验证3N频率、3N槽与实际张量，保留被剔除原ID。Raman本轮严格十条从同一已核MD5原档取得，源索引和预处理明确记录。

- 2026-11-02T20:39:40.893380+08:00：CLI只改变调用协议，不应靠复制matrix配置冒充参数支持。续训需恢复Adam/epoch/RNG并核数据指纹，旧文件缺优化器只能明示暖启动；CPU checkpoint不得因为机器有GPU而调用get_rng_state_all初始化未分配设备。配置与运行状态的长期接口见engine/README。

- 2026-11-02T21:34:39.952470+08:00：插件源码SHA不能搭配可能陈旧的mtime+文件大小pyc缓存使用；按源码指纹命名模块并对该命名空间从源码编译，避免同长度/同mtime修改读到旧helper。空图JSON丢失[E,F]列数，edge_features_width保留零边的F，索引/shift需恢复整数形状。长期协议以docs/standards.md为准。

- 2026-11-02 22:15:14 +08:00（生态设计建议，尚未实施）：外部原子模型接入应允许端到端预测、特征提取及原生训练器分能力提供，现有BaseGNN节点接口可作为完整集成路径；不强制所有提供方重写构图或暴露中间层。跨环境冻结特征/结果交换与兼容环境内端到端反传需要分开声明。

- 2026-11-02T22:47:29+08:00：Windows PowerShell经管道传多行SSH脚本时，末尾CRLF可使bash把最后一个文件名读作含CR；使用远端tr去除stdin中的CR后再交bash，避免误把脚本存在性当故障。沙箱内网络/SSH配置受限时用任务授权的提权通道，不重复未授权网络探测。

- 2026-11-02T22:48:24+08:00：需要后续write_stdin的SSH工作会话必须以exec_command tty=true启动；普通pipes返回session ID也不代表stdin可写。连续遇到引号/CR/stdin问题后，应改为PTY持有的单一工作连接并复查实际handle，不重复短命pipes连接。

- 2026-11-02T22:50:00+08:00：tr接持续stdin时默认块缓冲，短命令不会及时交给bash。已停止该无任务输出的工作会话；本任务改回已验证的有限stdin脚本，并在最后加注释行吸收PowerShell附加CR，不再探索持久shell。科学作业实际只确认741提交，未把echo输入当执行证据。

- 2026-11-03T00:08:57+08:00：CGCNN原仓库没有Python安装元数据，pip git URL能clone但不可安装；可用固定commit的未修改源码目录+.pth，不应为安装便利改写其层。服务器Git大包TLS失败时，改固定官方archive→逐文件校验的小型源码资源包，经任务资源目录传输，避免重新下载权重/日志和修改tracked源码。新增源码下载脚本必须兼容服务器Python3.10，不能使用3.11新增hashlib.file_digest。

- 2026-11-03T00:20:19+08:00：Path.write_text在Windows默认会把LF转为CRLF；read_bytes直接发bash会使set-e/health/cd全部解析失败，不能只防PowerShell管道末尾CR。SSH发送前规范CRLF为LF并断言无CR，优先对实际发送bytes做bash-n；归档payload独立解码后核hash，不改其内容。本次仅产生一个空的home/models/official-install+CR缓存叶目录，精确空目录清理，不递归删除或覆盖未知路径。

- 2026-11-03T00:43:04+08:00：99MB资源传输与第三条SSH控制连接重叠时reset，proxy仍健康，不能据此重启代理。后续大传输期间只保留代理+该传输，不并发新工作SSH；对同一任务partial先核长度和本地前缀SHA再append，末尾全包与逐文件SHA通过才解包，禁止盲目从头传或使用不完整文件。因果尚未单独隔离，作为操作约束避免链路竞争。

- 2026-11-03T00:50:06+08:00：第二次校验前缀后单独SSH资源续传仍被Vlab关闭，说明第三连接不是充分解释；复查18:26已成功的本地loopback HTTP+SOCKS Range方案，改复用健康proxy承载HTTP下载，并保留partial/完整hash门禁。不再重复大文件SSHstdin协议。恢复offset非MiB对齐时，进度应按阈值递增，不能用sent%8MiB==0判断，否则会漏报。

- 2026-11-03T01:12:09+08:00: Original model parity includes input keys and batching convention, not only architecture/state keys. ALIGNN Graph.atom_dgl_multigraph can return DGL for pure_torch when DGL is installed; use its corresponding original batch API. NequIP singleton ASE inference is unbatched; adding a batch field changes its force-output execution path. Diagnose exact inputs first and preserve strict output tolerances rather than relaxing force checks.

- 2026-11-03T01:26:27+08:00: NequIP force parity failed three consecutive validations746/749/752 (first was container selection). Reviewed prior lessons; singleton batching fix alone does not resolve numeric force disagreement:752 verifies all original calculator input keys/tensors exactly. Do not claim batching is the proven cause. Next isolate original-model repeatability, JIT warmup and equal state before editing adapters or considering any precision change.

- 2026-11-03T01:53:53+08:00: NequIP756 disproved batching/JIT as the numeric force error cause: unmodified original calculator itself varied around2e-5 under dual CPU threads. Single-thread758 gives exact feature/energy/force parity without relaxing tolerance. For old Equiformer/OCP imports, isolate ORIGINAL PyG2.0.4 in its own venv; build/install on Slurm, preserve parent2.7 and all original model source bytes. One-pass small binary SSH transfer with prefix/fullSHA succeeded where double-pass loopback/SOCKS/public TLS was interrupted by Vlab; do not generalize this to blind huge-file retransmission.

- 2026-11-03T09:18:38+08:00: For prediction tasks, loading an official backbone does not restore original predictions when the unified task head is randomly initialized; usage must distinguish original-head inference from backbone-transfer fine-tuning. Current forcefield scales check all E/F/S labels even at zero loss weight. Local Bash syntax checks must discover bash from PATH rather than assume C:/Program Files/Git; this workspace uses F:/mingw/usr/bin/bash.exe.

- 2026-11-03 09:38:42 +08:00：基准证据需按主干来源、任务头和源码版本拆分。原始模型加载/前向一致只证明provider保真，接随机新头后的任务精度仍需独立测试；旧变体跨任务矩阵不能转记为新官方主干基准。新头/池化/导数路线差异需作独立对照，避免将差异全部归因于GNN。

- 2026-11-03 09:43:36 +08:00（解耦设计核查）：任务输出的旋转变换保证应显式声明并在换主干时保持可检查，不能只根据backbone.kind自动切换语义。辅助变量线性响应求导是一种输出参数化，并不自行保证与另一个能量/极化模型物理一致；监督项选择与所请求的计算输出也需要分别描述。此为后续设计建议，未新增实现。

- 2026-11-03T09:47:14+08:00: Choose supervision independently of computed forcefield outputs: filtering only the final loss is insufficient if eager bindings/scales still require unselected E/S labels. Validate the selected canonical set once, filter bindings/scales/losses consistently, and include it in optimizer-resume compatibility. Force-only mixed parameter/coordinate gradients train an energy-derived conservative force, while energy offsets remain unidentified; tested against analytic gradient and real original-MACE fine-tuning.

- 2026-11-03 10:00:49 +08:00（已记录于解耦需求评审稿）：组件解耦应同时约定pooling位置、FeatureSpec语义、冻结模块的buffer/eval策略和输入梯度链；只切requires_grad或换线性层不足以保证力场和续训正确。旧配置保持原构造，新组合显式启用，避免identity新默认改变历史checkpoint。具体要求见docs/plan/prediction_decoupling_requirements.md，尚未实施。

- 2026-11-03 10:06:03 +08:00（需求修订已采纳）：第一版基础链使用原生节点特征直接接readout，首层按自动读取或显式声明的F建立可学习映射，无需统一32维adapter或额外reshape。F只描述大小，非标量仍需irreps/基底/映射；必要转换可归readout内部，独立adapter仅在复用价值明确时显式采用。需求/配置/训练归属及验收必须同步修订。

- 2026-11-03T11:20:31+08:00: Prediction task diagnostics reviewed after repeated helper failures:existing lessons cover Slurm accounting disabled, PowerShell Chinese pipeline encoding, and server-only dependency imports. Guard optional sacct with explicit fallback to queue/log evidence; do not let missing accounting abort result collection. Local standalone scripts need src on sys.path (pytest pythonpath config does not install the package). Keep UTF8 helpers in files for Chinese edits. Network reset was separate from computation; confirmed own PID gone and1080 free before one replacement holder, which passed HTTP200.

- 2026-11-03T11:24:41+08:00: Real prediction767/768 failed BEFORE harness startup:environment contains an installed scripts package, shadowing repo namespace when running python -m scripts.validate_prediction_components. Use python scripts/validate_prediction_components.py and sibling import validate_official; validate help/import path before Slurm resubmission. Optional accounting unavailability and rg absence were discovered here; use actual logs and standard-library read-only fallback, not a passing-job assumption.

- 2026-11-03T11:34:32+08:00: Warm-start parameter keys/shape and root class alone do not establish custom plugin identity:two source folders can expose the same qualified class and dimensions. Reuse existing extension source_sha256/factory verification for selected backbone before strict loading, and test rejection leaves every target tensor unchanged. Component state delta includes persistent buffers; for full-training capacity evidence distinguish it from parameter delta and report the underlying parameter-gradient evidence.

- 2026-11-03T11:53:10+08:00: PowerShell semicolon-separated checks report the last command status, potentially hiding a failed intermediate Python helper. Gate mutations on each returned check result and inspect stdout, or use explicit exit handling; do not treat final git diff --check exit0 as evidence every earlier command passed. Digest documentation should be checked against transfer metadata to avoid manual copy-length typos.

- 2026-11-03T13:24:02+08:00: Reviewed lessons after first assessment failures across3models:preserve native forward/tolerances,diagnose exact boundary. CGCNN reference label-slot is independent of predictions and must use an existing label;ALIGNN FD at h.002 may have truncation error so assess convergence rather than relax accuracy;OCP integer cell-repeat bounds are topology and can be detached independently while live distance/cell gradients remain. Existing config assertion guessed ALIGNN F256 but published artifact actually512:dimension assertions must be checked against actual loaded profile.

- 2026-11-03T14:10:05+08:00: Five-backbone forcefield evidence:BN training and parameter training are separate controls. CGCNN rawtrain repeat is deterministic but mixes graphs;Equiformer alpha_drop.2 changes same-batch repeat. Explicit trainable-eval mode preserves original layers/parameters while fixing deterministic per-structure energy derivatives. OCP cell-repeat bounds are discrete;only topology selection belongs in no_grad,live continuous pos/cell must reach original distance code. FD h convergence identified ALIGNN truncation error without changing tolerance. Upgrading derivative verification metadata must be recorded without invalidating unchanged old tensor architectures;actual oldCGCNN replay error0 verifies the exception.

- 2026-11-03T16:56:51+08:00: Two local Git schannel TLS handshakes failed; git -c http.sslBackend=openssl push succeeded with normal certificate verification. Task proxy46820 disappeared locally and remote1080 was free; only then started replacement. Native NequIP energy must use original energy network before ForceStressOutput so head-only force training retains mixed gradients; derivative wrapper consumes graph in eval.

- 2026-11-03 18:12:27 +08:00：生成先例应分为改造架构训练score/denoiser、预训练表示驱动生成、生成系统中的编码器、以及力场弛豫/筛选四类。架构生成先例不自动证明现成官方力场checkpoint无需结构/目标调整即可用作生成器；SiMGen才是明确的预训练MACE特征复用实例。

- 2026-11-03T19:13:48+08:00: ustc-gpu(Hanhai22)canauthenticateviaProxyJumpvlabwithkeyboard-interactivepasswordthenOTP,butloginbanner explicitlyprohibitsCodexandrelatedservicesconnectinglogin/computenodesandanyproxyprogram. Do not reuseGuqq2proxy/workflowsorcontinueagentSSHbusinessworkonthissystem. On discoveringrestrictionduringauthenticationtest,exitonly;credentialsneverinprojectlogs.

- 2026-11-03T19:17:43+08:00: Update to earlier ustc-gpu conclusion: user confirms newer user guide permits Codex SSH access and supersedes old login banner. Use current ustc-gpu.md note rather than treating the historical banner-based exit as an ongoing prohibition. Attribute the guide permission to user clarification; no guide URL/version supplied or independently verified.
# 2026-11-03 全量任务规划经验

只读引用其他项目site-packages的子venv会在父目录移走或删除后失效，子venv自身仍存在并不代表Torch/CUDA和科学包可用。
本次Guqq2四环境的共享父目录不存在，环境恢复必须纳入存储/就绪预算；pip缓存应先检查能否复用再考虑清理。
工具论文还须区分完整数据与完整评测：mini-batch及structures=all不会自动提供独立验证/测试、val选模或预训练标签重叠审计。
`head_mode: reset`只换头，不能消除主干已见测试标签的问题。峰值预算要包含内嵌官方artifact、优化器和原子保存临时文件。

## 2026-11-03：Windows 控制消息与 SSH 清理协议

- Windows subprocess text=True 写入远端stdin时可能将换行转为CRLF，Bash read得到的严格token会多出CR。跨SSH控制消息优先发送二进制LF，或在远端明确去除末尾CR；代理实际关闭与端口释放分别取证，不能用控制器退出码代替二者。

## 2026-11-03：小规模验收与全量实验配置边界

全量适配应分别核对数据覆盖、训练预算、设备资源和执行路径。structures=null/all不代表输入文件不是十条子集；report_structure_limit只限制报告内容，不能当成训练/推理样本上限。固定扰动、训练集evaluate和末尾全量采样等执行逻辑不能仅靠增加epochs修复。模型cutoff、邻居及特征协议应按实验定义保持一致，不能作为隐式缩减数据成本的开关。

- 2026-11-03T21:58:03 +08:00: Git HTTPS smart protocol may return 405 to HEAD while PyPI proxy works. Do not infer proxy failure from unsupported HEAD method; use bounded GET of repository info/refs before pull. Preserve existing live user-owned proxy.

- 2026-11-03T22:13:59 +08:00: Automatic approval deadlines can expire before a remote command is created. Treat this separately from SSH login/network rejection; after one retry, ask user for guidance and continue independent local work. Preserve existing user-owned proxy and do not infer remote installation success from a started SSH command. capacity probe success is not full-training coverage certification; fixed split helpers and metrics alone do not implement val-best evaluation.

- 2026-11-03T22:54:23 +08:00: Empty pip --python target needs its own PySocks even when controller uses an existing pip. Curl/download a verified universalwheel, offline bootstrap target first. A healthy user-held proxy can disappear independently; use the mandated dedicated holder for long downloads after proving the old proxy gone, and preserve exact owner PID. Do not restart merely on listener or transient TLS evidence.

- 2026-11-03T22:59:49 +08:00: Scratch constructor audit (source/ZIP metadata only, no model execution): MACE0.3.16 extract_config_mace_model copies atomic energies and scale/shift, so a fresh constructor must replace learned normalization/reference values rather than silently inherit them. Published NequIP-OAM-S package config.training_module.model nests ModelFromCheckpoint pointing to an absent upstream checkpoint, not a self-contained fresh architecture config. Need infer/validate canonical builder args from packaged module metadata/state shapes under Slurm, using official fresh constructors and full key/shape/irreps checks; no recursive partial reset fallback.

- 2026-11-04T00:36:37 +08:00: Slurm sbatch --wrap generates a sh wrapper: set-euo pipefail requires explicit Bash, even when submission connection usesbash. Use Pythonshlex.quote to wrap the whole multiline body as execbash-c; validate quote roundtrip and retainfailedjoblogs. An emptyqueue plus explicit shellerror proves stopped; do not infer failure solelyfrom pollingtimeout.

- 2026-11-04T01:43:44 +08:00: Vlab repeatedly closes task proxy after a few MB while local resource service remains healthy. Consulted prior SSH lessons after3failures. Persist Range partials and distinguish actual queue/log terminal state from stale running JSON; never retransfer verified files or start duplicate active jobs. Current supervisor makes progress but pipeline/runtime must not be presented as restored or full experiments.

- 2026-11-04T02:52:50 +08:00: Resourceverification: ZIPPKprefixdoesnotprovefullarchive; old10,424,580Bmlearn-source.zip is truncated, replacedby12pinnedauthorJSONblobs. Exactcurl97UnabletoreceiveinitialSOCKS5response istransientgreetingEOF; retryonlythatmessagewithboundedwindow, neverblanketall97policydenials. PrimaryPyTorchindex links canlegitimatelyuseexactdownload-r2.pytorch.org; preservepublishedSHAverificationwhitelistingthatknownofficialhost.

- 2026-11-04T03:08:14 +08:00: MLearn publishedtrain/test firstCuandSi records shareexplicitAIMDdescriptionfamily (different snapshotindices). Preserveauthorbenchmarksplit, enforcefamiliesonlybetween training/validation andexplicitlydiscloseauthor-test correlation. Do notclaimfulltrajectorydisjointness. Prepareddataaudit codehash isboundtoitsrecordedgitcommit, notnecessarilycurrentworktreeafteranewpreparer isimplemented.

- 2026-11-04T03:31:12 +08:00: Update earlierNequIPpackageconfig limitation: embeddedconfigstillreferencesmissingbasecheckpoint, butZenodo23472045 separatelypublishesNequIP-OAM-S_pretrain_config.yaml (11565B,SHA256d61e684aa85e3cad83578042fa485df9fb9ab8d8a3f6fe56b8b20564d7f6f076). ItsnativeNequIPGNNModel usesfeaturewidths[128,64],typeembed32,2layers,lmax1,rmax4.5,trainablebessels8 andZBL. Do notguesslegacywidth. Freshmustoverridefixedseed42 withrunseed, resetper-typeenergyshifts/scales, fitavg_num_neighborsfromtraininggeometryonly ratherthanreusefittedpretraining25.59111819081615. Inspectnativebuilderversioncompatibility andfullstate/irrep/layout underSlurmbeforedeclaringfreshready.

- 2026-11-04T04:25:38+08:00：Windows本会话Stop-Process即使PID/命令行匹配也发生内部NullReferenceException，进程与端口仍在，不能据命令exit0宣称清理完成。重查CIM所有权后用.NET Process.GetProcessById(PID).Kill()精确终止自有三个已完成HTTP进程，Get-NetTCPConnection核对三个监听实际释放。该经验属于环境操作，不写入业务代码。

- 2026-11-04T04:54:06+08:00：监督器新代理刚Popen时，普通工作SSH有时先于专用SSH完成握手；健康curl7明确为1080连接拒绝，本地wheel HTTP仍200。不能当作TLS或资源服务故障。对同一新代理的端到端HEAD增加最多5次/20秒的connection-refused重试，仅适用于启动就绪竞态；仍不得重启健康代理、忽略其他失败或用监听代替端到端健康。旧64108实际已终止且finally核对1080释放后才启动替代监督器。

- 2026-11-04T04:54:06+08:00：PowerShell不会为rg展开tests/test_*.py等参数；重复不存在路径会浪费诊断回合。先rg --files确认目录，用rg PATTERN tests -g " *.py\过滤，不能假定模块目录/单文件布局。

- 2026-11-04T05:00:08+08:00：Vlab会在普通状态SSH上返回255（202.38.75.226主动关闭），即使刚验证的专用代理仍live、cleanup下一连接又可成功。不能因只读观察失败而在finally拆掉正在服务数据的健康代理。监督器改为每30秒重试同一观察路径，保留现有Popen，不据未知状态重交sbatch；fresh健康的SSH观察最多三次/间隔30秒，curl非255失败仍停止。去掉3秒密集SSH重试，普通连接超时45秒；变更仅本地控制器，工作body SHA不变。

- 2026-11-04T09:36:13+08:00：rg --files的-g模式主要匹配文件名，不能靠*properties*发现properties目录里的__init__.py/catalog.py。目录布局不确定时直接rg --files具体目录，再按实际输出读文件；不要将包猜成同名.py或猜library.py。该经验属于查找工具，不写入业务代码。

- 2026-11-04T09:58:49+08:00：no-progress周期必须查真正worker。此次867确因连续curl7和保留断点而failed，无digest/磁盘/策略错误；health页成功不能替代固定wheel本身的Range检查。确认旧进程与监听已释放、实际队列空、具体断点8B来源可读且Vlab banner正常后才恢复一次监督，不放宽代理策略或删除partial。

- 2026-11-04T10:17:11+08:00：PowerShell向python stdin传递含中文的检查脚本时应显式配置UTF-8输出编码，或优先保存UTF-8脚本再执行，避免分隔符变为问号造成伪失败。元数据helper的无依赖测试应直接测试生产helper，不为导入完整contracts/Torch调用链而模拟科学依赖；完整API留在真实环境集成测试。

- 2026-11-04T10:32:01+08:00：本次Vlab超时后，本地专用SSH已终止而远端1080监听仍在；不能据此重建第二代理。先核实本地精确PID不存在，再核对当前用户sshd启动：唯一无notty的3420794始于10:19:34，与已记录本任务唯一代理10:19:30握手对应，其他工作会话均@notty；端到端健康失败后再复核UID/完整启动时间/命令/唯一性，仅TERM该PID并确认端口释放。若归属不唯一或健康，则不清理。该经验属运维流程，不改业务代码。

- 2026-11-04T11:01:44+08:00：不能只在SSH断开后按时间猜归属。新增专用-N前保存1080空闲及当前用户无notty的sshd集合，健康后绑定唯一新增者的PID/UID/boot_id/start_ticks/命令。后续必须先有自己Popen实际terminal，并在失败健康检查前后两次比对完整身份，通过pidfd固定目标再发TERM，防止PID复用；健康、歧义、boot/UID变化和缺pidfd均不结束进程。sshd非dumpable时/proc目录owner可能为root，实际UID应从ps euid取得，不能用proc目录属主代替。远端保护用显式异常而非可被优化禁用的assert；归属观察失败不能为记录元数据而终止健康代理。

- 2026-11-04T11:34:02+08:00：原包native_input的图不是完整任务的全部图：现有EquivariantAdapter还为response/generation建radius graph，native边数和其max_neighbors不足以估计完整下游开销。CGCNN dense neighbor slots含padding，应按分配槽位报告，不能标成物理键；ALIGNN还需line-graph三体数。生成clean训练图的全量扫描也不能证明所有噪声状态/随机采样轨迹的显存，预检需标记实际状态覆盖。该长期扫描接口约定写入benchmarks/probes/README，不混入业务数学注释。

- 2026-11-04T12:04:42+08:00：PowerShell调用rg时，不要把未展开的readouts/*.py等glob作为路径；用真实目录加-g "*.py"。也应先rg --files确认generation是generation.py还是子包，避免凭习惯猜model.py。此类路径经验只记运维文档，不加到GNN业务数学里。

- 2026-11-04T12:31:02+08:00：879表明HEAD与GET分别重开curl时，成功HEAD不能证明下一条SOCKS连接可建立；880同一curl后两次num_connects=0，两组5MiB约22s完整，第三组部分也为正确prefix，且一次初始connect10.27s超过原5s。用-C -配合显式有限Range头与--next可以连续append同一partial并复用HTTP/SOCKS连接，--fail-early防止中间片失败后跳过缺口；仍需验证CR/长度和完整SHA。Windows curl JSON含UTF-8路径，subprocess text须显式UTF-8，不能依赖默认GBK。

- 2026-11-04T12:56:51+08:00：纠正早先概括：response的额外图来自EquivariantAdapter；生成实际走tasks/generation.py的DirectionReadout，仅native_polar为false时才建额外radius graph。完整扫描应检查实际模型模块和启用分支，不对所有带cutoff的模块一律重复计数。882的CLI资源报告compute_node_proxy_health_exit为0不保证整个后续长传输持续可用；应关联具体curl错误、实际断点增长和对应代理SSH日志，不能把它判成SHA/协议故障。

- 2026-11-04T15:09:33+08:00：不能从NequIP作者num_features列表直接推断逐层width。本任务原package的type_embed32、layer0.feature_irreps_hidden=128x0e+64x1e、layer1=128x0e，readout输入128x0e；0.14以及官方0.15的简化builder仅单一整数且自己传type_embed，直接传作者recipe将失败。应从原包模块读取明确layout，使用同包FullNequIPGNNModel完整builder并严格比较state/布局及数值；不能猜[128,64]为128→64，不能放宽state检查或换架构。

- 2026-11-04T16:00:46+08:00：下载进度应区分Torch根wheel与其CUDA依赖。本任务根wheel1039365846B早已完整；后续反复续传主要是cuBLAS等。用户授权服务器直连后，计算节点实际4MiB官方下载18.16秒/HTTP206/TLS验证通过，精确offset SHA与本机固定源相同。直连作业还在1080无监听时增长，证明无需本机中转。不能用历史默认代理规则拒绝用户已明确授权的新下载路径；也不能仅据HEAD成功声称完整传输或安装完成。

- 2026-11-04T17:36:31+08:00: Pip dependency isolation must account for every legacy .pth parent. universal-official intentionally inherited universal-mace/e3nn0.4.4; installing an own0.5.8 while MACE remains visible creates a real pip-check conflict. Preserve the documented provider pins and check effective distribution roots, not only child-owned packages. Do not suppress pip check or uninstall a package whose root belongs to a parent.

- 2026-11-04T18:25:52+08:00??CGCNN????checkpoint??BatchNorm num_batches_tracked???PyTorch?strict loader???????????????????????strict??????????????????strict????canonical?????scratch??????????NequIP??Full builder???????global_state????????Torch/Python/NumPy RNG???dtype??????isolate_rng?dtype?????????????????????import?patch factory??????Mock?????????????????

- 2026-11-04T18:31:09+08:00?MACE0.3.16????????????????*_zeroed bool buffer?????module artifact???????????????????????????????bool false???????????????canonical????????/??????????????buffer??????904???????????register_buffer?not keep???????shape????

- 2026-11-04T18:46:16+08:00???torch.device("cuda")?index?None?torch.cuda.set_device???????????????Slurm???????index???cuda:N????????cuda:0 fixture?????device=cuda????????NequIP???E0??????????0??????/????89x1??1x1???????????????????state?

- 2026-11-04T19:05:57+08:00??????????????????.to(dtype=model_dtype(config))?MACE??artifact???float64?build_model????????MACECalculator?????float32???provider?double???tensordot????dtype?????????CUDA/??????float32??????????????????????

- 2026-11-04T21:41:39+08:00：unittest形式不代表标准库控制测试。结构质量测试通过延迟导入Pymatgen/ASE/NumPy进行实际物理评分，应与Torch测试一起走Slurm；只有metadata/CLI guard可在-S本地检查。先阅读测试调用依赖再分类，导入失败时移动到正确执行环境并保留完整验收要求，不以安装本地科学栈或跳过测试替代。

- 2026-11-04T22:16:43+08:00：pytest当前版本会把unittest成功subTest加入JUnit tests总计数，但不为每个成功子测试写独立testcase节点。925实际40主测试+16子测试、40个节点、汇总56。固定主测试覆盖应核对唯一classname/name节点及分组完整性，另要求汇总和节点均无error/failure/skipped并保留原总计数；不能据汇总计数误报科学失败，也不能绕过失败的作业收据。

- 2026-11-04T22:49:21+08:00：原全矩阵测试曾照着recipe断言supervised_outputs=[energy,forces]，和运行时只允许total_energy的协议脱节。数值force-only smoke未覆盖energy监督，直到真实FF入口暴露。定义测试必须跨到实际监督输出协议，并校验输出名、loss_weights、binding输出名一致且源标签仍可为energy。旧冻结定义不可覆盖，应记录revision与修正前后指纹；未验真实配置不能宣称全矩阵可运行。

- 2026-11-04T23:03:37+08:00：931/938/940三个真实物理/生成路径在GPU重载预测校验处连续失败，量级约1–4e-6。942已证明ALIGNN保存/加载全部参数与buffer逐项相等，普通CUDA重复推理也有同量级差异；确定性算法后所有64记录逐元素相同。不能把GPU归约顺序的数值波动直接判作权重损坏，也不能先放宽标准。验证应同时严格检查状态并在可复现的比较作用域运行，保留数学模型、训练过程及原容差；同时保存诊断与恢复控制测试。

- 2026-11-04T23:35:27+08:00：955真实CGCNN应力FD揭示固定有限h可跨最近邻选择的离散边界：.002和.001的正00拓扑改变，.0005保持拓扑且力/应力同过原容差。选择差分步长需要收敛证据，不能把有限步跨图边界误判解析导数错误；过小h又有float32消减误差。采用预声明步长梯度并要求相邻估计彼此及解析值均满足原标准，保留所有尝试。955的后半float64诊断另因旧helper zeros默认float32失败，应修正参考零的dtype/device，不能关闭dtype检查或宣称整个job成功。
- 2026-11-05 01:30 +08:00：959 CGCNN scratch和963 NequIP最坏完整输入的float32能量差分在步长缩小时出现消减/量化，确定性算法未能修复。964同一参数解析力精确复现，float64副本通过全部验收、解析力只差2.8e-6。独立有限差分宜提升相同参数和已选择坐标的运算精度，而不是只缩小h或放宽容差；必须保留实际训练dtype解析导数及混合/几何/分批验收，并用大常量能量偏置、错误力拒绝和原模型状态不变测试防止验收失真。
- 2026-11-05 01:55 +08:00：NequIP官方 eager embedding 的_output_dtype是显式Python属性，Module.double只转换参数/buffer，不更新该属性；970的实际参考副本因此在MLP触发float/double matmul错误。974证明仅同步深拷贝参考的已知SphericalHarmonicEdgeAttrs/BesselEdgeLengthEncoding输出dtype，两个完整最坏输入模式均通过且原状态不变。此类独立数值参考兼容应放在validation中，避免改backbone文件而无谓失效已冻结的图/训练统计来源hash，也不能把临时CPU诊断当CUDA验收。
- 2026-11-05 02:40 +08:00：外层验收不可假设rglob(result.json)恰好四文件：paired controller有两次独立+两次共同检查，但typed-OOM尝试和共同batch再缩小都会合法增加文件/成功轮次。应沿capacity.trials和preflight.attempts的SHA/身份链验收，要求只有exit42+cuda_out_of_memory才减半、所有最坏输入及完整测量完成、末轮两模式确实在相同batch复验。不要为了满足固定计数丢弃OOM失败记录，也不能把其他错误放宽为重试。
- 2026-11-05 03:02 +08:00：pytest部署环境不能依赖无包标识的tests目录通过tests.xxx导入共享fixture；982在Linux虚拟环境收集阶段报ModuleNotFoundError，而本地python -S unittest未暴露。同目录测试资源用__file__解析并明确加载，或放入正式可导入fixture包；增加已占用tests命名空间的隔离控制，保留全部原断言。失败控制门禁必须先于hold/cancel/提交，982确实挡住后续动作，避免未验收代码进入全量作业。
- 2026-11-05 03:08 +08:00：多层JS工具字符串写入Python正则时，括号转义在生成过程中丢失，UserId检查因此报unterminated subpattern。精确固定Slurm字段直接比较UserId=xmz(令牌，避免不必要正则；AST检查不能发现正则语义错误。新增完整控制器check-only/owner正反例与全部请求bash检查，动作前置门禁保证错误未进入hold/cancel/submit。已查既有PowerShell/转义经验，不盲目重连或重提。

- 2026-11-05T04:08:23+08:00：原包数据读取对照可能要求训练目标之外的CSV标量字段（CGCNN CIFData）。只对独立reference输入副本提供读取器槽，不改真实下游标签、任务或官方头；必须同时检查原特征和原预测等价。带Tensor的targets字典不能直接用==检查不变性（992收尾断言失败），应逐字段torch.testing.assert_close(rtol=0,atol=0)；994通过。失败请求/日志保留，修复仅任务请求适配，不因此更改官方骨干。

- 2026-11-05T04:30:53+08:00：张量零/非零需要明确分组对象：介电张量整体范数可能全部非零，但非对角分量有大量精确零标签。只报整张量分组会漏掉这些分量误差；后评测同时提供whole-tensor groups和component-label groups，精确零不拟合阈值，空组null，完全缺失不误判零。具体长期接口和输出定义放assessment/README。

- 2026-11-05T04:51:13+08:00：检查缓存源码的Git身份前必须先确认目录自身有.git；git -C在非仓库子目录会向上找到本任务根仓库，不能用其HEAD/remote冒充该第三方快照版本。此次ALIGNN静态源码目录没有独立.git，仅以文件内容/hash及官方在线登记说明身份；权重包的发布ID清单以固定ZIP SHA和内部文件SHA为准。

- 2026-11-05T05:13:02+08:00：发布的train/test材料ID清单不能假定互斥：固定ALIGNN包存在两个跨角色ID。默认完整性拒绝要保留；需要继续审计时，显式报告多角色成员关系和互斥=false，训练/选模曝光按原成员关系计算，不能按最后出现角色覆盖、静默去重分配、删除样本或声称干净留出。原始清单、固定SHA、独立诊断和失败门禁均保留。

- 2026-11-05T05:57:04+08:00: Generation capacity has two independent batch contracts: training config must retain its paired training batch while sampling exports its own paired batch. A clean graph scan cannot bound evolving diffusion graphs; actual corrupted-training and full-step sampling probes are required. Current scientific quality streams one sample at a time, so throughput measured at sampling batch4 is not an observed1000-sample evaluation cost. Long-term interface is documented in benchmarks/generation/README.md.

- 2026-11-05T09:06:45+08:00: Native baseline evaluations must keep original head/pooling/normalization and freeze every persistent component, with complete state hashes before/after; parameter freeze does not disable input autograd needed by force/stress. Same units alone do not align target definitions, absolute energy zeros or pretraining exposure. Report raw unshifted metrics and limitations without fitting offsets to heldout labels; keep native evaluations outside formal reset/scratch counts. Long-term API and boundary are in benchmarks/native_heads/README.md.

- 2026-11-05T09:37:02+08:00: NequIP clean topology reference may carry only the public package, while whole-backbone scratch also carries the pinned author constructor blueprint. Artifact comparison must require identical package hashes and exactly that registered blueprint addition; comparing entire artifact dictionaries for equality falsely rejects valid fresh construction. No extra arbitrary artifact or changed digest is allowed. This orchestration rule is documented in benchmarks/execution/README.md.

- 2026-11-05T09:53:22+08:00: Windows PowerShell legacy pipeline encoding can turn embedded non-ASCII Python heredoc strings into literal question marks before Python receives them, even when write_text uses UTF-8. Use apply_patch for Unicode prose or ASCII-safe generation; verify the resulting snapshot text, not only Markdown syntax. The corrupted current-state snapshot was repaired while retaining all prior change-history text; no model/config/data was affected.

- 2026-11-05T10:51:57+08:00: Generation quality must receive the last checkpoint containing validation-selection history and then load its verified best; retain both files until quality and independent evaluation finish. Separate quality Slurm jobs avoid consuming the training allocation budget. Keep failed attempt directories, use exact owning-job claims, and do not treat absent progress or a stale lock as proof that a job stopped. Full sample-batch probe time times1000 is a conservative planning estimate for the current single-sample evaluator, never measured trained quality throughput.

- 2026-11-05T11:05:58+08:00: A legacy result can legitimately predate newer audit instrumentation. Confirm its actual execution commit and preserve raw evidence; never invent audit fields or weaken new formal validation to force compatibility. Report current-format acceptance and explicit legacy rejection separately.1042 caught the unsupported assumption that all8 historical generation diagnostics had exact reload markers;1043 kept strict code and tested4 current/4 legacy outcomes, plus real full predictive gates.

- 2026-11-05T11:34:57+08:00: Independent saved-generation assessment must reconstruct raw geometry at the original training dtype before fingerprint/prior and StructureMatcher scoring. A float64 reparse of a float32 runtime reference can change the fingerprint and near-boundary matching; require original source/version identity and per-attempt plus aggregate comparisons. This is independent process/data replay of the original scorer, not an independent implementation or repeated sampling; numerical-failure events remain observed invalid attempts.

- 2026-11-05T11:40:58+08:00: For python -c followed by runpy.run_path with a literal script path, sys.argv initially begins with -c; runpy replaces argv[0] while leaving subsequent arguments. Do not also pass the script filename as argv[1], which becomes an unexpected CLI argument. Check the exact -c/runpy argument vector with a stdlib probe before submitting guarded runtime tests.

- 2026-11-05T12:12:10+08:00: Supplemental elastic ordinarySFTP, full compressed legacySCP and the small-chunk continuation all encountered Vlab closure/timeout, while6x128KiB chunks completed. Reviewed prior large-transfer/timeout lessons; preserve verified1.77MiB prefix and every complete chunk, inspect server bytes before retry and do not infer remote file failure from client timeout. Local matching-process inventory is authoritative for orphan cleanup; none remained, so no process was terminated. Any retry must skip validated chunks and be bounded; this is transport failure, not data/model failure.

- 2026-11-05T12:35:32+08:00: Supplemental tensor source audit1048 shows5000 piezo records (2297 exact zero tensors) and14500 elastic raw records (1 invalid label). Author magnitude filters2/19 cases and symmetry preprocessing are not generic validity criteria; preserve/explain full finite-label cohorts and count zeros separately. New related-property splits must inherit existing material roles by ID AND cross-source geometry/reference keys; no observed shared-ID conflict alone proves complete cross-source grouping. Keep benchmark-specific dataset orchestration separate from immutable runtime loaders, and never change primary144 definitions to fit new auxiliary cohorts.

- 2026-11-05T13:16:15+08:00: Slurm sbatch reading an entire script from stdin requires a #! interpreter first line; bash -n alone does not prove sbatch format acceptance. A --wrap command need not contain shebang, but converting a controller from --wrap to stdin requires adding and checking it. Preserve explicit rejected request artifacts and use a new attempt claim; do not confuse this with an ambiguous RPC receipt.

- 2026-11-05T13:24:15+08:00: When archiving server evidence with byte SHA on Windows, write exact UTF8 bytes (write_bytes or newline="") instead of default write_text, which translates LF to CRLF. Verify both saved local bytes and original server/hash receipt. Restore from the retained original response, never recompute expected scientific hash to fit transformed bytes. Restrict current-state replacements to the header before the history marker; compare the whole committed history prefix before each documentation commit.

- 2026-11-05T14:38:06+08:00: Guqq2 purges terminal jobs from scontrol quickly, including exact confirmedCANCELLED gates and completed controls. Preserve authoritative terminal owner/name/state/exit records at first observation and bind them to exact request/source/report hashes. A missing later handle does not undo verified completion or authorize resubmission. Use retained completed-control proof for acceptance preconditions; do not submit new afterok dependencies on a purged completed ID. Pending/running jobs still need a live current handle, and an unknown/unverified terminal result still requires accounting/artifact reconciliation.

- 2026-11-05T16:05:59+08:00: Campaign scope changes should use a separate source-bound active-case manifest instead of rewriting a frozen matrix already referenced by job/config/result hashes. Cancel excluded launch controllers before their preparations, after exact owner/name/source/request checks, and retain immediate terminal receipts. Preserve every completed scientific proof and report one-seed metrics without cross-seed uncertainty. A cancellation SSH timeout is ambiguous: inspect intent/terminal/queue state before retry; compact SHA-bound references to existing remote receipts and compressed metadata avoid resending large redundant JSON. In this case the first timeout left no intent and all96 stillPENDING; only then was a new compact attempt made.

- 2026-11-05T16:43:03+08:00: Independent validator source is distinct from the training commit: older MACE trainings preceded the accepted high-precision energy-reference FD update, while their993/1024 trained-best post reports already useddfea7b0. Preserve model/training compatibility, record current validator hashes, and require post-to-independent source identity instead of falsely requiring validation helpers to equal the older training tree. Existing thresholds stay fixed. When replaying diagnostics, select exact source jobs from the verified48-case index: globbing every report includes replaced ALIGNN931/952 duplicates and misses CGCNN973 under reference-failure-recheck. Consult exact scripts/rg file inventory before choosing temporary paths.

- 2026-11-05T17:11:00+08:00: Saved heldout row metadata is task-specific: engine/evaluation/heldout.py records natoms only for forcefields, which need E/atom and per-node force shapes. Graph-level scalar/class/tensor/spectrum rows carry id/predictions/targets, with atom counts available in the SHA-bound raw source. Fixtures must reflect emitted records; a universal synthetic natoms field hides invalid reader assumptions. Preserve mandatory force counts and reject any inconsistent optional graph count.

- 2026-11-05T19:14:56+08:00: A post-dispatch fingerprint must exclude changing Slurm runtime/state fields. Keep current observations separately, bind stable original job/token/request and dependency semantics, and preserve a known existing post dependency when a completed training handle is later purged. Rebuild legacy request bytes using its pinned source directory; default request_script formatting must remain byte-compatible. A missing-handle fallback is allowed only after complete source-bound training artifacts validate; wrong owner/token never falls back. Windows metadata fixtures must use the same Path.absolute interpreter normalization as the real producer.

- 2026-11-05T19:34:10+08:00: Saved-proof aggregation must inspect the actual archive schema before mutation. The first MACE proof groups formal/pilot hashes in nested maps; later case proofs use flat relative file names. A strict recursive leaf verifier preserves all original hashes without treating a directory as a file or rewriting old proofs. Three local CG996 acceptance-script failures were metadata-schema assumptions (saved_entry versus entry; nested legacy archives), not failed science or Slurm jobs; formal index remains unchanged until all original/new hashes pass.

- 2026-11-05T20:24:43+08:00: Temporary-script discovery must be adaptive: run rg --files or Get-ChildItem first, inspect the returned basename, then issue a separate exact read. Do not append a guessed read to the same inventory call. Existing GPU allocation script is slurm_allocation_gpu_control_job.py; omitting control repeatedly caused avoidable lookup failures. Unknown generated script names are not evidence of missing implementation.

- 2026-11-05T21:24:08+08:00: Slurm WorkDir and executed source checkout are distinct provenance fields for older --wrap jobs:997 was submitted from the repository root but its SHA-bound body changes into dfea7b0. Check the exact original request/submitter and both identities; do not require equality blindly or allow arbitrary alternate directories. Also convert server-bound paths with Path.as_posix() when preparing arguments on Windows. Bash syntax validation alone accepts literal Windows backslashes and cannot prove a Linux path resolves.

- 2026-11-05T22:19:54+08:00: PowerShell default stdin encoding can replace Unicode literals before Python sees them, even when Python writes UTF8. Use apply_patch or an explicit UTF8 transport for new nonASCII text; archive/history verification should use a savedUTF8 script or Unicode escapes for markers. The newly appended plan section was repaired before commit and original history bytes were preserved. Shared primary/supplement executors should keep separate closed selectors and explicit device/rank physics schemas; a CPU numerical report must never satisfy a CUDA preparation contract.

- 2026-11-05T22:43:45+08:00: Reusing a fixture helper requires inspecting its filesystem behavior, not just its name: prediction-assessment.write assumes parent directories already exist, whereas new terminal telemetry fixtures need nested output creation. Initial141 regression run and isolated11 controls exposed8 identical missing-parent fixture errors; provide a test-local mkdir-capable writer, preserve every original failure/success assertion and rerun. No server/source/science acceptance was attempted before tests passed.

- 2026-11-06T00:21:26+08:00: Untrained generation sampling capacity and complete denoising training readiness are distinct evidence claims. A failed sample probe must not be relabelled complete, nor used as measured throughput; preserve its exact bytes and report unqualified sampling. Any staged training release still requires complete unchanged source/graphs/paired100-batch evidence and mandatory trained-best full-quality plus independent assessment. Known geometry-domain failures may count as invalid attempts only under an explicit common policy; never swallow CUDA OOM/unknown programming errors or retry until valid.

- 2026-11-06T00:30:02+08:00: Capacity trial report_sha256 is canonical_digest(parsed JSON), as defined by pairing/capacity.py and pairing/evidence.py; it is not a file-byte digest. New consumers must inspect producer semantics before comparing hashes. Preserve the canonical parent/trial identity check and exact path, and record a separate raw file SHA in the new gate so subsequent replay also binds current bytes. CPU1446 exposed this mismatch after189/1082 successful controls; preserve that failed terminal and fix source/fixtures before reacceptance, never rewrite original scientific evidence.

- 2026-11-06T00:40:39+08:00: Original full-generation runtime wrapper adds git_commit/source/control stamps only after its public preparation subprocess succeeds. Failed paired-sampling parents therefore lack a source stamp even though graph and training workers retain executed commits. Staged readiness must bind the original parent job/path/provider to saved original request/control receipts, request hashes, clean pinned source and actual graph scan job/commit, retaining that proof separately. Never substitute currentHEAD or edit the failed parent to invent provenance.1448 caught this success-only metadata boundary after full189/1082 controls and unchanged source/graph/training evidence were checked.

- 2026-11-06T01:10:29+08:00: Read-only preflight jobs can be purged before a later submission helper executes. Retain authoritative terminal owner/name/workdir/resources/exit and exact request/source/output hashes immediately. For a genuinely purged ID, revalidate unchanged artifacts/source and explicitly record the retained proof and current missing-handle limitation; do not depend on a purged completed Slurm ID or repeat the scientific job. Any current wrong identity/failure must refuse fallback. Managed submit_stage returns a transient reused=False field beyond persisted launch.json; compare with that exact documented addition, preserving all saved fields.

- 2026-11-06T02:00:45+08:00: A frozen pretrained ablation has one initialization; do not fabricate a pretrained/scratch pair to reuse capacity evidence. Reuse complete source-bound clean graph rows because freezing changes optimization only, but run independent100-batch frozen CUDA probes and frozen input-derivative/geometry checks. Frozen parameters/buffers/eval modes/optimizer exclusion must remain exact while readout parameters update; disabling input autograd is incorrect. A scoped wrapper can observe the unchanged worker/Adam steps with byte-state and RNG comparison controls, preserving old preparation compatibility. Keep original reference common batch for a one-flag ablation; reduced exploratory probes are not automatically matched scientific evidence.

- 2026-11-06T02:12:36+08:00: e3nn0.4.4 CartesianTensor is tuple-like but its constructor expects a formula string; generic deepcopy of a tensor-readout model reconstructs it from a tuple and can fail before inference. Independent numerical oracle models should be rebuilt through the same public configuration/factory and strict state_dict loading, then assert exact initial tensor state. Preserve bitwise final-state/RNG and finite-difference checks; do not patch e3nn or weaken comparisons to hide a test setup limitation.
