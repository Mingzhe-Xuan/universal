# 环境记录

## 2026-11-02 实现环境计划

- 本地：Python F:/Anaconda/python.exe；现有 torch 2.11.0、e3nn 0.4.4、mace-torch 0.3.16、
  numpy 1.26.4、pytest 9.0.2、ASE 3.26.0。用于编辑/静态及极小解析单元检查，不做训练推理矩阵。
- Guqq2：Python 3.10.12；待建立 /home/xmz/.venvs/universal，使用 python3 -m venv，
  不修改其他项目环境。安装前后记录版本。CPU/GPU wheel 选择以已有环境与存储诊断为准。
- 数据/权重缓存放 /home/xmz/universal/data 与模型目录，运行结果 runs/，均 Git ignored。
- 安装/下载显式使用已健康检查的登录节点 SOCKS 代理；计算作业不假设该回环代理可用。
- 所有训练/推理和实际评测用 Slurm，当前尚未配置/验收环境。

## 2026-11-02 14:49:31 +08:00：服务器环境建立前记录

- 服务器系统 Python 3.10.12 没有 torch/e3nn/MACE 等包，也未发现已检查路径下可复用 venv。
- 创建独立 /home/xmz/.venvs/universal。10 结构验收先用 torch 2.6.0 CPU wheel，避免 30 GiB 余量中引入完整 CUDA 依赖；计算仍提交 Slurm CPU 作业。
- curl 显式 SOCKS 引导 PySocks 后由该 venv pip 经代理下载 wheel；only-binary 禁止登录节点源码编译。依赖实际解析/安装版本待回填，不预先宣称成功。


- 2026-11-02 14:54:14 +08:00：系统 Python 缺 ensurepip，标准 venv 建立失败；使用 python3 -m venv --without-pip，在专用 venv site-packages 解包官方 pip/PySocks wheel 引导，不安装系统包或修改其他环境。

## 2026-11-02 15:18:20 +0800：依赖隔离与离线安装方案

- 任务 venv 已引导 pip 25.3/PySocks 1.7.1，Torch 远程下载两次因代理断开失败，未安装成功。
- 本地下载目标 cp310/Linux wheel；核心/NequIP 环境固定 torch 2.6.0+cpu、e3nn 0.5.8、NequIP 0.14.0（要求 e3nn>=0.5.6,<0.6）。MACE 0.3.16 需 e3nn==0.4.4，另建 /home/xmz/.venvs/universal-mace，不混装。
- 本地 wheelhouse 与服务器缓存只放 ignored 目录，采用 scp 资源传输；实际安装版本在完成后回填。

- 2026-11-02 15:24:53 +08:00：纯 Python antlr4-python3-runtime 4.9.3 在本地构建通用 wheel；下载 python-hostlist wheel，禁止仅因 binary-only 将 Hydra 静默回退到 0.11。NequIP 环境另固定 Hydra1.3.2/OmegaConf2.3.0。隐藏独立代理健康持续，改后台可续传 curl 官方 Torch wheel，避免 scp 低速长连接。

## 2026-11-02 15:36:57 +08:00：已有 Torch 只读复用方案

- /home/xmz/generate_md/.venv-mattergen 已有 Python3.10.12、Torch2.7.1+cu128、NumPy1.26.4、ASE3.27.0、pytest9.1.1。只读引用该环境 site-packages，不修改原环境。
- /home/xmz/.venvs/universal 与 universal-mace 各自在自己 site-packages 放入指向该依赖目录的 .pth；新装 e3nn/NequIP/MACE 写入子环境，避免 Torch 大包下载。两子环境分别固定 e3nn0.5.8 与0.4.4。
- 这是当前实际安装方案，替代尚未完成的 CPU Torch2.6 下载；训练先用 CPU Slurm，Torch CUDA 库来自已有安装。安装后记录版本，实际模型检查在 Slurm。

- 2026-11-02 15:47:10 +08:00：实际 distribution.locate_file 查明：mattergen 自身通过 .pth 引用 .venv-smoacs-blackwell；子环境仅添加 mattergen 的路径不会递归处理其 .pth。正确只读依赖目录为 /home/xmz/generate_md/.venv-smoacs-blackwell/lib/python3.10/site-packages。修正后必须先用 metadata 断言 torch2.7.1+cu128/numpy1.26.4 可见，再安装 e3nn；显式固定已有Torch/NumPy以防意外重新下载。

- 2026-11-02 15:49:36 +08:00：核心独立环境安装成功：Torch2.7.1+cu128/NumPy1.26.4/ASE3.27.0来自只读 blackwell 依赖；本任务安装 e3nn0.5.8、opt_einsum3.4.0、opt_einsum_fx0.1.4，editable universal-gnn-tasks0.1.0。提交Slurm535执行已同步的13项测试。未修改父环境。

- 2026-11-02 16:28:31 +08:00：从pip HTTP缓存按官方URL和SHA恢复NequIP/Hydra/OmegaConf/Lightning等5个wheel，离线安装成功：nequip0.14.0、e3nn0.5.8、matscipy1.1.1、hydra-core1.3.2、omegaconf2.3.0、lightning2.5.6、pytorch-lightning2.6.6、torchmetrics1.9.0、lightning-utilities0.15.3。提交Slurm538检查真实NequIP后端。

- 2026-11-02 16:34:37 +08:00：MACE wheel包已完整传入6471680字节。独立MACE环境离线安装前，从本任务core环境仅复制已安装的opt_einsum3.4.0/opt_einsum_fx0.1.4及其dist-info（轻量第三方依赖，目标限定MACE site-packages）；不引用整个core路径，避免把NequIP/e3nn0.5带入MACE环境，不改core或blackwell。其余依赖仅使用缓存wheel。

- 2026-11-02 18:04:44 +0800：在已有 /home/xmz/.venvs/universal 中补充 abTEM 1.0.8、numba 0.61.2、llvmlite 0.44.0、dask/distributed 2024.12.1、zarr 2.18.3 及缺失依赖；本地下载 Linux cp310 wheel，服务器仅离线安装到该任务环境，保留已有共享科学包。MACE 仅通过独立 workflow 依赖路径共享新增模拟库，不暴露 core e3nn。

- 2026-11-02T18:23:28.430419+08:00：为避免MACE读取core的e3nn，计划另建 /home/xmz/.venvs/universal-workflow-deps（python venv --without-pip）；用core pip将25份已哈希验证任务wheel以--no-deps安装到该新venv site-packages，并为MACE添加仅指向此目录的.pth。该目录不含Torch/e3nn/NequIP，不替换MACE及共享科学包。

- 2026-11-02T18:30:31.461088+08:00：实际资源包SHA256 9ce398318398498a36e9ebbd7a358c374fe2ea1454f7c3fd6d3f037794ab5942通过；core新增24包、universal-workflow-deps25包离线安装成功，MACE.pth仅指向后者。abtem1.0.8,numba0.61.2,llvmlite0.44.0,dask/distributed2024.12.1,zarr2.18.3,numcodecs0.13.1,pyfftw0.15.0；原科学包未修改。

- 2026-11-02T18:37:15.642364+08:00：计划将core与workflow-deps两个任务前缀的abTEM从1.0.8降为官方1.0.6（Python>=3.9,<3.12、NumPy<2）；wheel SHA256 94bd000a9aa68410201a6130689ebd70ec8a31a39ed0b192d6d4203e598f5905。通过pip --python管理无pip的workflow-deps，避免--target升级遗留旧dist-info；不改共享环境。

- 2026-11-02T18:39:56.601886+08:00：实际两前缀均先准确卸载abTEM1.0.8再安装1.0.6成功，无旧dist-info残留；MACE继续e3nn0.4.4，core/NequIP继续0.5.8。

- 2026-11-02T20:43:36.089200+08:00：新CLI使用PyYAML>=6；服务器元数据确认已有PyYAML6.0.3（共享只读依赖），无需环境安装/修改，两个任务venv保持原版本。

- 2026-11-02T21:39:30.996536+08:00：自定义KNN+GCN仅依赖现有Torch/ASE，无新增第三方图库或安装；服务器metadata确认ASE3.27.0和PyYAML6.0.3。G2原数据随ASE提供，在Slurm中提取标签/图，来源版本/SHA记录在数据集。

## 2026-11-02T23:05:12+08:00：官方模型依赖隔离计划（安装前）

- 新建任务专用 /home/xmz/.venvs/universal-official，以python3 -m venv --without-pip建立；只读复用blackwell实际site-packages、universal-mace和workflow-deps的已有科学包，避免改动其他项目/既有验收环境。显式确认Torch2.7.1、NumPy1.26.4和e3nn0.4.4的实际路径后安装。
- ALIGNN/CGCNN/MatGL-MEGNet/MACE在该新环境中固定官方包版本；MatGL计划v1.1.3、DGL1.1.3（避免DGL2.x GraphBolt对Torch二进制版本的绑定），CGCNN固定上游commit f42ab233c4ee0c416879d6bc2d22a264418413ad，MACE沿用0.3.16。ALIGNN精确版本按实际发布权重配置确定后回填。
- NequIP-OAM-S0.2为官方可训练package，另计划任务venv universal-official-nequip，复用core的e3nn0.5.8及科学包；需核对其package版本和ModelFromPackage兼容性后固定NequIP版本。Equiformer依赖与发布checkpoint仍在核查。
- 依赖下载/纯Python包安装可在登录节点，二进制只装兼容wheel；任何编译及模型加载后的计算/微调/推理均Slurm。安装过程保存pip日志和实际distribution版本/路径，禁止pip替换只读父环境。

- 2026-11-02T23:19:49+08:00：universal-official已创建，真实只读路径断言通过Torch2.7.1+cu128、NumPy1.26.4、e3nn0.4.4；原blackwell已有DGL1.1.3+cu121。初次pip因MatGL1.1.3声明dgl>=2而解析失败，没有执行包替换。计划调整为核对较早官方MatGL版本的依赖和模型schema兼容性，保留官方源实现，不用no-deps强行掩盖此冲突。NequIP下载包元数据为nequip0.15.0/e3nn0.5.6/Torch2.7.0，包含eager和compile模型；拟用官方0.15.0的eager加载器，避免编译依赖。

- 2026-11-02T23:32:20+08:00：PyPI官方依赖元数据确认MatGL1.0.0仅要求dgl（无>=2限制），将新环境MatGL计划从1.1.3调整为1.0.0，保留现有DGL1.1.3+cu121；模型schema1和原生MEGNet实现/权重兼容性仍须实际验证。新环境中任何替换均仅发生在新venv，原MACE/core/blackwell不变。

- 2026-11-02T23:43:52+08:00：MatGL1.0.0实际安装成功，且从官方tag获取的MEGNet源码SHA256与v1.1.3完全一致（083b1eede73795b7cf20b18de4fb4f6ea02dcfda52fcb249855fd1d28722b639）。已有父环境Pymatgen2025.6.14、PyG2.7.0、jarvis-tools2026.6.12、pydantic-settings2.15.0；缺CGCNN、ALIGNN、timm、torch-scatter、torch-cluster。下一仅新official前缀安装CGCNN原repo、ALIGNN2026.10.11、timm0.6.13及匹配Torch2.7/cu128的PyG二进制wheel。
- GitHub/git/trees API此前返回的是tree SHA，不能冒充commit SHA；CGCNN f42ab233...等均为原始内容tree引用。安装日志将保留实际Git commit，原文件内容hash及模型源URL继续保留，架构真实性以原包加载/严格state/独立参考实测证明。

- 2026-11-02T23:54:13+08:00：CGCNN原仓库确实没有setup.py/pyproject.toml，pip安装在任何包修改前停止；pip日志与commits API均确认实际HEAD=f42ab233c4ee0c416879d6bc2d22a264418413ad。改将原始仓库作为只读vendor放models/official-src/cgcnn，新增official环境.pth引用，不改其源码。前述tree/commit性质提醒不替代本次commit明确核对。
- EquiformerV1原始OC20权重已从作者Dropbox目录下载并提取best_checkpoint.pt（36958765字节，SHA45a991aac88702003156a5fc3e45ee80f63ca5be4af6c385f033448cd43ce7e2）；配置内原模型graph_attention_transformer，原OCP提交b5a197f。已核对原生输入与完整可微距离/球谐路径，改采用V1，不修改V2的detach。Equiformer源码固定64cb7866f48b9aa156e74a9d6a2ef2663b367437，OCP固定b5a197fc3c79a9a5a787aabaa02979be53d296b7。

- 2026-11-03T00:27:08+08:00：official环境实际依赖安装成功：ALIGNN2026.10.11、timm0.6.13、torch-scatter2.1.2+pt27cu128、torch-cluster1.6.3+pt27cu128；MatGL1.0.0、DGL1.1.3+cu121及科学包保持原有只读来源。85文件原始源码资源包已核SHA/逐文件hash并写vendor .pth，CGCNN/Equiformer/OCP源码未修改。NequIP先在原core0.14.0/e3nn0.5.8环境实测官方可移植package，若兼容无需新增环境。

- 2026-11-03T01:12:09+08:00: Before next installation: universal-official already exists; install only matching torch-sparse binary wheel for Torch2.7/cu128 with pip --python into this task venv. Do not compile on login or change parent site-packages. Keep pip output under models/official-install; actual import/model execution goes through Slurm.

- 2026-11-03T01:31:03+08:00: torch-sparse0.6.18+pt27cu128 installed successfully OFFLINE into universal-official. Wheel5148348 bytes, SHA2b081081279c1ee456ba14c73a445bf11438afefcdd5867f5f1820f1ae3fbd06, official PyG Torch2.7/cu128 cp310 Linux x86_64. Guqq2 TLS/loopback transfer failed; local download plus prefix-verified one-pass SSH remainder succeeded. Parent environments unchanged; model import/execution is Slurm757.

- 2026-11-03T01:36:57+08:00: Before configuration: create task-only /home/xmz/.venvs/universal-equiformer via python -m venv --without-pip, read-only parent paths from universal-official. Install ORIGINAL PyG2.0.4 (sdist407534 bytes, SHAd64e4c7486fcf0c7fa82f0acbf5dd52035855469708bf89f8bc7fc607671c8b7) in the new venv, preserving nn.acts.swish required by original OCP. PyG2.1+ removed that module. Package metadata/source archives inspected; no torch._six use in2.0.4. Pure-Python wheel build/install AND model execution will be in Slurm. Leave passed official/core/MACE environments unchanged.

- 2026-11-03T01:53:53+08:00: Actual Slurm759: ORIGINAL PyG2.0.4 wheel built/installed in universal-equiformer, original parentPyG2.7 not uninstalled. Built wheel616664 bytes SHAd39ad9feb19830a439fa882f63824c78841a3d6edd44f47ea3390cfde8a4306f; all6 official validations passed. environment-metadata.json in local evidence records actual torch/e3nn/backend/binary versions. Use UGNN_PYTHON=/home/xmz/.venvs/universal-equiformer/bin/python for Equiformer.

- 2026-11-03T11:30:56+08:00: Prediction component validation reuses existing universal(core),universal-mace,universal-official venvs unchanged; no package or vendor source modifications. All units use2CPU; real official cases use1CPU with OMP/MKL/OPENBLAS1 for stable float32 derivative/reference parity. Source0cc5a98, jobs769-772; original environments/versions as prior official and force-only records.

- 2026-11-03T14:06:10+08:00: Other forcefield validation reused all prior task venvs unchanged:no installs or upstream vendor edits. Official(ALIGNN/CGCNN/MEGNet),core(NequIP),equiformer(originalPyG2.0.4) each singleCPU for actualnumeric tests,OMP/MKL/OPENBLAS1;fullregressions2CPU126each. All recorded versions/source hashes remain in actualreport. Temporary dataset/ckpt/results taskscoped andignored.
# 2026-11-03 全量实验前环境复查

本轮只读检查发现，之前四个任务venv共同引用的
`/home/xmz/generate_md/.venv-smoacs-blackwell/lib/python3.10/site-packages` 已不存在。
四个环境的distribution元数据均查不到Torch、NumPy、ASE、pytest，部分任务专属包仍在。
旧环境通过139项测试的历史记录保留，但不能当作当前环境完整可运行的证明。
后续先建立并记录任务自有共同基础环境，再验证e3nn/PyG隔离和RTX5090 CUDA执行；本轮没有安装或修改依赖。
详细证据在忽略目录 `results/paper-storage-20261103/environment-check.json`，预算见
[arXiv v1实验计划](../plan/arxiv_v1_experiments.md)。

- 2026-11-03T21:49:41+08:00: BEFORE restoration:create task-owned /home/xmz/.venvs/universal-base using python3 -m venv --without-pip;reuse existing core pip only to manage newprefix. Planned sharedbase pinnedTorch2.7.1+cu128/NumPy1.26.4/ASE3.27.0/PyYAML6.0.3/pytest9.1.1 and prior compatible scientificdeps. Preserve model-specific e3nn and originalsource profiles;addreadonly commonbase pathonlyafter metadata checks. No installation into system/otherprojects. Savepackageversions/locations and build-only viaSlurm.

- 2026-11-03T22:13:59 +08:00: universal-base creation verified empty after successful pull. Binary Torch install command exited1; later log read did not execute because automatic approval timed out, including one retry. Do not record Torch/scientific packages as restored until logs and installed metadata are checked. Existing user proxy unchanged; latest measured available69190582272B before install.

- 2026-11-03T22:39:33 +08:00: Diagnosed first Torch install: pip targetbase lacked PySocks (Missing dependencies for SOCKS support). Plan curl universal PySocks1.7.1 wheel+PyPI digest, no-index bootstrap into universal-base, then pinned binary-only retry. This modifies only task-ownedbase; package presence still pending confirmation.

- 2026-11-03T22:48:04 +08:00: PySocks wheel scp completed; remote SHA256 matched2725bd0a9925919b9b51739eea5f9e2bae91e83288108a9ad338b2e3a4435ee5; offline target-base install and import verified PySocks1.7.1. Pinned binary Torch/scientific installation remains live in SSH exec session25239; do not restart merely on a polling timeout.

- 2026-11-03T22:48:45 +08:00: Correction to preceding live-install note: latest poll of session25239 returned terminal exit1, so installation is stopped, not a verified wait. PySocks1.7.1 import was verified before that failure; Torch success remains unproven. Next inspect logs before any install retry.

- 2026-11-03T22:54:23 +08:00: Owned dedicated proxy PID25840(exec73725) started only after local old holder absent/remote1080 free, verified end-to-end GitGET and pull. Previous pip failure traced to proxy disappearing mid NVRTC88MB download (2.5MB received); no Torch restore claimed. PySocks remains verified. Inspect cache/precise URLs before retry.

- 2026-11-03T23:19:42 +08:00: Network-source adjustment planned only after active-process audit: Torch exact officialdownload-r2 URL unchanged2.7.1cu128; dependencies resolved from PyPI instead of CUDA-only index linking slowpypi.nvidia.com. NVRTC PyPI SHA equalsoriginala0fa9c2a21583105550ebd871bd76e2037205d56f33f128e69f6d2a55e0af9ed. No matching complete exact NVRTC cachebody found at either publicURL key. Base still not declared restored.

- 2026-11-03T23:40:26 +08:00: Offlinepull4994468 succeeded; full821trace confirms eagerTorch import, corrected18-protocol Slurm822 submitted. Actualbase contains onlyPySocks1.7.1, ownbase-pip process auditempty: prior31548 stopped; log shows PyPI cuBLAS609.6MB download failed13.8MB whenproxy vanished. No1080 listener remains. Prepare exact Torch/CUDA officialURL/SHA catalog locally (metadata only); Slurm will check only specified cachekeys and hardlink verified wheels, then SCP only missing resources. No newproxy/no duplicatepip install.

- 2026-11-03T23:51:20 +08:00: Prepare local offline common-dependency wheel download only (no local install/model). PinsTorch-independent base NumPy1.26.4/SciPy1.15.3/ASE3.27.0/PyYAML6.0.3/pytest9.1.1/PyG2.7.0 and Torch genericdeps inclsympy1.14.0>=1.13.3; reuse existing Linuxwheels. Isolated pip downloader explicitly evaluates Linux/CPython3.10 markers because --platform alone does not. Full Guqq2base pipcheck and numerical Slurm remain mandatory. Pymatgen/Jarvis/provider extras follow after sharedbase; no claimall restored.

- 2026-11-04T00:18:07 +08:00: USER EXPLICITLY APPROVED HTTP resumable transfer for large fixed wheel resources after SCP failures. Local read-only loopback service52372/session6866 port54339, whitelist42public-resource paths, local Range/HEAD/404 tests passed. Before any servertransfer: offlinepull90cf140, check1080free and localSSHholders; create exactlyone dedicatedproxy, then end-to-end HEAD localresourcehealth before resourcecurl. No publiclisten/no trackedsourcewrites. All fullhash/assembly viaSlurm, no duplicatepip.

- 2026-11-04T01:43:44 +08:00: Actual Slurm832 installed49 common dependencies into task-owned universal-base; pipcheck passed. NumPy1.26.4/SciPy1.15.3/ASE3.27.0/PyG2.7.0/pytest9.1.1. Torch/CUDA/providerextras still not installed; no childbase link or GPU-readiness claim. 830 common archive25parts SHA verified before install.

- 2026-11-04T02:52:50 +08:00: PreparedbutNOTINSTALLED providerdependencies:59PyPI wheels62,873,601B, pinnedPymatgen2025.6.14/Jarvis2026.6.12/Spglib2.6/Sklearn1.7.2/Pandas2.3.3/Setuptools80.9.0(pkg_resourcespayloadverified). PlusnativeDGL1.1.3cu12179,870,014B andTorchvision0.22.1cu1288,730,539B; total151,474,154B. Allunderlocaltmp/arxiv-linux-base; provider/native-provider manifests holdURLs/hashes/ABI. GPUregressionmustwaitforproviderinstallandchildpipcheckafterCUDA16.

- 2026-11-04T03:31:12 +08:00: ReadonlyfixedsystemSDKlibrarymetadata shows /usr/local/cuda->CUDA12.4 libs plus /usr/lib CUDA11; noCuDNNfoundatcheckedfixedpaths. No librarycopied/importedorenvironmentchanged. These cannotbeclaimedasmatchinglockedCUDA12.8runtime. Provider151MBlocalmanifestreadybutupload/installpending.

- 2026-11-04T06:06:12+08:00：Slurm863定向恢复provider缓存22资源47,426,518B（含Torchvision CUDA8,730,539B）；59个Torch独立provider缺38个24,177,622B。本地原59wheel仍完整，计划通过已有回环HTTP/SOCKS补齐38个，在既有自有universal-base安装59项并pipcheck，再跑Pymatgen/ASE结构评分；不需新下载CPU Torch。另7个CPU验证wheel的本机HTTPS下载两次被自动审批拒绝，已异步请求明确许可，未创建新CPU环境、未下载其资产，待答后再办。

## 2026-11-04T06:36:39+08:00：Slurm864独立provider安装实测

沿用已有Python3.10.12 `/home/xmz/.venvs/universal-base`；没有创建新的CPU验证环境。资源仅来自本机此前已下载的wheel；恢复缓存后补传38项24,177,622B，ZIP共24,209,507B，SHA256 `06bbf6f4d6834f9f51d261a1f619620a199dffd3e6726263cc93ca2eefa23d12`。在Slurm内校验全部59项后执行 `python -m pip install --no-index --no-deps --no-cache-dir --only-binary=:all: <59个已验证wheel>`；`python -m pip check` 实际返回0。以下是安装后完整distribution版本清单，来自实际pip list，不代表其中需要Torch的包已经可执行；Torch/CUDA、DGL及子环境仍待恢复。

```text
aiohappyeyeballs==2.7.1
aiohttp==3.14.5
aiosignal==1.4.0
annotated-types==0.8.0
anyio==4.16.0
ase==3.27.0
asttokens==3.0.2
async-timeout==5.0.1
attrs==26.1.0
bibtexparser==2.1.0
certifi==2026.10.23
charset-normalizer==3.5.2
click==8.5.0
cloudpickle==3.1.2
contourpy==1.3.2
cycler==0.12.1
decorator==5.3.1
exceptiongroup==1.3.1
executing==2.3.0
filelock==4.1.0
flake8==7.4.1
fonttools==4.65.0
frozenlist==1.8.0
fsspec==2026.9.0
h11==0.16.0
hf-xet==1.8.0
httpcore2==2.14.0
httpx2==2.14.0
huggingface_hub==2.4.0
idna==3.20
iniconfig==2.3.1
ipython==8.39.0
jarvis-tools==2026.6.12
jedi==0.20.1
Jinja2==3.1.6
joblib==1.6.0
kiwisolver==1.5.1
lmdb==3.0.0
MarkupSafe==3.0.4
matplotlib==3.10.9
matplotlib-inline==0.2.2
mccabe==0.7.0
monty==2025.3.3
mpmath==1.3.0
msgpack==1.2.4
multidict==7.1.0
narwhals==2.28.0
networkx==3.4.2
numpy==1.26.4
orjson==3.13.0
packaging==26.3
palettable==3.3.3
pandas==2.3.3
parso==0.8.7
pexpect==4.9.0
pillow==12.3.0
pip==25.3
plotly==7.1.0
pluggy==1.7.0
prompt_toolkit==3.0.53
propcache==0.5.4
psutil==7.2.2
ptyprocess==0.7.0
pure_eval==0.2.4
pycodestyle==2.15.0
pydantic==2.14.2
pydantic_core==2.50.2
pydantic-settings==2.15.0
pydocstyle==6.3.0
pyflakes==4.0.3
Pygments==2.21.0
pylatexenc==2.11
pymatgen==2025.6.14
pyparsing==3.3.3
PySocks==1.7.1
pytest==9.1.1
python-dateutil==3.0.0
python-dotenv==1.2.4
pytz==2026.6
PyYAML==6.0.3
requests==2.34.2
ruamel.yaml==0.19.1
scikit-learn==1.7.2
scipy==1.15.3
setuptools==80.9.0
six==1.17.0
snowballstemmer==3.1.1
spglib==2.6.0
stack-data==0.6.3
sympy==1.14.0
tabulate==0.10.0
threadpoolctl==3.7.0
tomli==2.5.0
toolz==1.2.0
torch-geometric==2.7.0
tqdm==4.70.1
traitlets==5.16.1
truststore==0.10.5
typing_extensions==4.16.0
typing-inspection==0.4.4
tzdata==2026.6
uncertainties==3.2.3
urllib3==2.8.0
wcwidth==0.9.4
wheel==0.45.1
xmltodict==1.0.4
xxhash==4.0.2
yarl==1.25.1
```

实际执行代码：`c095dd6a8fbd2bb30aeb71e1f4a6527dad64366c`；结构评分6测试、蓝图7测试均在Slurm通过。回传文件保存在忽略目录 `results/paper-environment-20261104/`，SHA256：

- `provider-independent-864.json`：`024d19514c2fe7a9df7cbd611770240c11610618b58bbc6c1cf9f9149f469d83`
- `provider-independent-864.err`：`c7bba29cb47769beb19614dddafffe103be09246cd277b2559eca03b5adf1071`
- `provider-before-864.json`：`60ce9665d9eb9bee8a356f0108b0b1a7ff540ce8121cdede8e10bbc57f59b989`
- `provider-after-864.json`：`344e374d5e56d0c20edd7a057da064996ea65cd66fac2698aa71bae0b8bfab8e`

provider只读HTTP进程50152/54974已按CIM精确核对所有权后关闭，监听释放已确认；主wheel54339与唯一SSH代理继续服务CUDA865。新的7个CPU验证wheel本机HTTPS下载仍待明确许可，没有执行被拒绝的下载。

## 2026-11-04T09:07:22+08:00：子环境元数据与官方环境补充资源

使用各任务Python的stdlib distribution元数据，按“本环境site-packages优先、universal-base其次”检查预期共享路径；未导入Torch/GNN、未创建新环境、未改写当前pth。这不是当前子环境已正确继承base或已经能运行的证明。结果在忽略目录 `results/paper-environment-20261104/child-environment-metadata.json`。

| 环境 | 合并可见distribution数 | 元数据发现的缺口 |
|---|---:|---|
| universal | 144 | torch |
| universal-mace | 124 | torch |
| universal-official | 115 | dgl, lightning-utilities, torch, torchmetrics, torchvision |
| universal-equiformer | 108 | 仅108共同依赖，未据此确认原模型/扩展已恢复 |

Slurm868已核验并暂存五个原本就在本机的wheel到 `models/official-install/official-extra-wheelhouse/`，没有安装。归档1,553,197B，SHA256 `4f5261b75f7f065c6b966d44b942b6aecaf7aaa230da1371ed53c4067bf06bbf`。

- `e3nn==0.5.8`，450056B，SHA256 `551b886a0761bce8022df242271c0397bcf5ee689834ddcb402c99ab985cbc58`
- `opt_einsum==3.4.0`，71932B，SHA256 `69bb92469f86a1565195ece4ac0323943e83477171b91d24c35afe028a90d7cd`
- `opt-einsum-fx==0.1.4`，13213B，SHA256 `85f489f4c7c31fd88d5faf9669c09e61ec37a30098809fdcfe2a08a9e42f23c9`
- `torchmetrics==1.9.0`，983384B，SHA256 `bfdcbff3dd1d96b3374bb2496eb39f23c4b28b8a845b6a18c313688e0d2d9ca1`
- `lightning-utilities==0.15.3`，31906B，SHA256 `6c55f1bee70084a1cbeaa41ada96e4b3a0fea5909e844dd335bd80f5a73c5f91`

新增[官方补充环境安装入口](../../scripts/install_official_extras.slurm)接在现有CUDA base安装完成之后，并要求DGL1.1.3cu121、已缓存的Torchvision0.22.1cu128和上述五轮全部就绪。全部七轮固定大小/SHA及共享Torch来源通过之前不会安装；仅向universal-official离线安装，检查三个环境的pip依赖、共享Torch路径和各自e3nn路径/版本。MACE保持0.4.4，其余两环境为0.5.8，不复制三份Torch。当前未提交该安装作业：CUDA未齐，DGL的服务器暂存仍待完成。安装报告显式numerical_acceptance=false，之后仍须原包、CUDA和导数验收。

- 2026-11-04T09:19:00+08:00：Slurm869实际通过离线installer全部3项纯std测试；收据/日志已回传，按ed2a646的Git blob核对脚本SHA 6e91bb1f328ed84eb8fad4d69dadffcb61707d24329d36f7d42c3bf6f876bd8a。这验证Linux/Python3.10门禁兼容，不代表实际pip安装或模型/CUDA验收。NequIP作者YAML已在服务器模型缓存通过11565B/SHA轻量核验，未改源码。
