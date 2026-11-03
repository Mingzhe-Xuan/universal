# arXiv v1 全量数据验收记录

目标矩阵见[实验计划](../plan/arxiv_v1_experiments.md)。本文件记录数据准备结果，不代表训练、GPU预检或科学指标已经完成。

## GMTNet 介电：完成全原档转换

2026-11-04，源码 `b6e83d5b10b4198ed7724cedd874d1f76cd36485`，Slurm 851 / node42。
原档来自作者的 [jarvis_diele_piezo.pkl](https://raw.githubusercontent.com/YKQ98/GMTNet/main/data/jarvis_diele_piezo.pkl)，6,731,047 bytes。

| 项目 | 实测值 |
|---|---:|
| 遍历原始记录 | 5,000 |
| 有效介电张量与结构 | 4,999 |
| 排除记录 | 1，JVASP-192，source_index=3705，标签非有限值或非3×3格式 |
| 训练 / 验证 / 测试 | 3,998 / 502 / 499 |
| 最大原子数 | 88 |
| 分区seed | 0，与模型训练seed独立 |

原档SHA256：`2a57e081f0072b2ac7fca7769095adcded1d299d2cd971db5c93fd25eb66929d`。
转换JSONL SHA256：`e2f3ec9569e67e31d353bad3f1f05da6856da64e7f34cb0fd59589e3c3edaa77`。

保留原始 `dielectric` 字段的笛卡尔3×3分量，不加 `dielectric_ionic`，不做对称化、非零/特征值筛选或原子数限制。
精确几何及显式MP引用的连通组不跨分区；这不证明晶体等价判重完备，也不证明与预训练数据无重叠。
4,999是本次固定原档的实测有效数，不能写成论文报道的4,713或其他版本的4,998。

服务器目录：`data/arxiv-v1/gmtnet-dielectric/`，包含 `structures.jsonl`、`split.json`、`audit.json`、`exclusions.jsonl`。
本地证据：忽略目录 `results/paper-data-20261104/gmtnet-dielectric/` 中的审计及排除清单；数据、日志和结果不提交普通Git。
851随后在另一份JARVIS原档下载期间失败，不影响已完成且有独立审计/数据哈希的GMT转换；不能将851整个任务标为成功。
Slurm 847在转换前通过全部12项JARVIS/GMTNet fixture，包括实际NumPy1.26.4 pickle读入；数值模型/GPU验收另行记录。

## JARVIS 带隙与分类：完成全原档转换

Slurm 853 / node42，源码仍为 `b6e83d5`，实际转换用时15.445秒。
固定 [Figshare 38521619](https://ndownloader.figshare.com/files/38521619) 原档40,811,489 bytes，
SHA256：`d4c64660e9e1fa45c82bd8868a96ec10162195eed69636445972c05550d8d0d6`。

| 项目 | 实测值 |
|---|---:|
| 原始 / 有效记录 | 75,993 / 75,993 |
| 训练 / 验证 / 测试 | 60,823 / 7,590 / 7,580 |
| 最大原子数 | 140 |
| 分类0 / 分类1 | 53,202 / 22,791 |
| 分区seed | 0 |

两任务共用同一份JSONL和材料组划分。保留零带隙；分类0表示gap≤0.01 eV，分类1表示gap>0.01 eV。
没有选取前十条或平衡两个类别；类别失衡须在评测中同时报告F1/AUROC等指标。
JSONL SHA256：`e06ce343c1cc4c727664255dcef8f2ad09f65b1c50546294ae44e7d90793fd58`。
服务器目录 `data/arxiv-v1/jarvis-gap/`；本地审计证据 `results/paper-data-20261104/jarvis-gap/audit.json`。
已知/未知的预训练目标重叠仍须逐模型披露，随机任务头不能消除主干记忆。

## MLearn 与 Perov-5：完成本地原档下载

固定作者commit下载并逐文件校验长度、Git blob SHA1和本地SHA256，共15文件、41,310,943 bytes：

- [MLearn作者数据](https://github.com/materialyzeai/mlearn/tree/10c427a5480c6281c15c64efaf869b03be04818f/data)：Cu/Ge/Li/Mo/Ni/Si各自 `training.json`、`test.json`，12文件。
- [Perov-5作者划分](https://github.com/txie-93/cdvae/tree/f857f598d6f6cca5dc1ea0582d228f12dcc2c2ea/data/perov_5)：`train.csv`、`val.csv`、`test.csv`，3文件。

原档与下载收据在本地忽略目录 `data/downloads/arxiv-matrix-raw/`。
MLearn和Perov-5均已完成下述Slurm全量准备；原档下载条数与有效结构数分开核验。
MLearn应保留作者测试文件来源，验证集仅从作者训练数据中划出；Perov-5保留作者三个划分。
旧的 `tmp/mlearn-source.zip` 是截断ZIP，不能作为完整资源使用；新流程只下载以上12个固定Git blob。

## JARVIS 声子谱：完成全原档转换

Slurm 853 / node42，源码 `459535470f1d3ff440c507c0f1ee73db57e05bc8`；853整体已完成。
固定 Figshare 29216859 原档遍历55,659条，其中14,244条具有有限、长度200的 `pdos_elast`；
其余41,415条因标签缺失、非有限或长度不符而逐条写入排除清单。
训练/验证/测试为11,394 / 1,424 / 1,426，最大64原子，无原子数裁剪。
保留原向量顺序和尺度，不虚构频率轴或归一化。

JSONL SHA256：`d20b16ad37ddbb1bbab534b2e41c9f7f01e07a127b8fb74e133dd7baca86c891`。
服务器 `data/arxiv-v1/jarvis-phonon-dos/`；本地审计 `results/paper-data-20261104/jarvis-phonon-dos/audit.json`。
已按审计记录的4595354提交核对实际准备器源码SHA，不能拿后续工作树版本冒充当时执行版本。

## MLearn 力场：完成12原档全量转换

Slurm 855 / node42，源码4595354，全部1,566条原始记录有效，无排除。
训练/验证/测试为1,309 / 93 / 164，最大108原子。
保留作者全部164条测试帧；仅对作者training按元素、描述族及精确几何进行分组验证划分。
能量是结构总能量eV，力是有序N×3、eV/Å，不加入stress监督。

作者训练/测试文件共享AIMD描述族，审计明确列出重叠。
这里只能声称作者测试帧上的评测，不能声称轨迹独立的测试；训练与验证描述族已隔离。
实际1,566来自固定12原档，不以数据注册表的近似1,730替代。

JSONL SHA256：`0ca42ef08e9f627f8f851de6a75bd958bb7632ec73a7fbc09a460baba20fe417`。
服务器 `data/arxiv-v1/mlearn-forcefield/`；本地审计 `results/paper-data-20261104/mlearn-forcefield/audit.json`。
原档登记的12个大小/SHA/Git blob及两份准备源码SHA均已核对。
Slurm854实际通过19项MLearn/JARVIS/GMTNet fixture；855再次通过7项MLearn测试并完成全量转换。

## Perov-5 生成结构：完成三份作者CSV全量转换

Slurm 858先通过全部9项纯数据/真实ASE解析fixture；859再次通过9项并完成全量转换，
源码 `668b59a6fada25c90e6bf5f4ede43a2c8eebf07a` / node42，转换用时28.665秒。
18,928条全部有效，无排除；作者训练/验证/测试为11,356 / 3,787 / 3,785，全部5原子。
不按带隙或能量筛选，不做primitive reduction；ASE保留原始CIF的常规晶胞、位置和原子顺序。
输出性质标签为空，生成条件仅为给定组成与原子数；不能称无条件生成。

压缩传输包2,093,574 bytes，Slurm内校验后解压出原CSV，再按原始文件逐项核对大小、SHA256、Git blob。
CSV没有重新编码或改变划分；作者材料ID与精确几何检查未发现跨分区冲突。
精确Cartesian判重不代表完整晶体等价判重。

JSONL SHA256：`df69edd0cec94f6768be338f85513cd34187fd7d45602f67ac7e194afdc6ae29`。
服务器 `data/arxiv-v1/perov5/`；本地审计 `results/paper-data-20261104/perov5/audit.json`。
已对照审计记录的668b59a提交核验公共写入器与Perov-5准备器SHA。
数据准备不代表生成训练/独立验证选模/测试采样质量已验收；这些仍是正式实验的前置工作。

## 仍在进行

六类下游任务的主体数据现已准备：分类、带隙、介电、声子谱、力场和生成；生成工作流仍需改造与数值验收。
CUDA依赖由857继续断点传输，尚未安装，不能据数据就绪宣布可开展完整矩阵。
Vlab不稳定时保留分片；同时发生的大文件传输按数据优先串行调度。
没有对不支持的元素或大结构做静默剔除，也没有把样例或测试fixture计为全量科学实验。

## Perov-5训练晶胞先验（不是生成质量结果）

2026-11-04T05:03:13+08:00，Slurm860 / node42 / 4859cc9实际通过9项纯协议测试，
仅从11356条训练结构拟合初始体积14.129232628696206 Å³/atom，log体积/原子标准差0.21804047795081252。
验证3787与测试3785均未用于拟合。JSONL哈希沿用上述df69edd0…，canonical manifest SHA256为
`8aaa3c1453f4aa9f4d8bfec09d92e70f186a3bb185fad0c72f9ca82eee0eeb9b`。
服务器 `data/arxiv-v1/perov5/training-cell-prior.json`，本地忽略证据目录保留同名收据，
实际脚本与协议源码哈希均按4859cc9提交核验。训练器按其实际输入精度重新拟合时使用训练几何指纹，
与独立准备器的原档/划分身份指纹定义不同；不直接互换。该先验不代表模型已训练或采样有效。
