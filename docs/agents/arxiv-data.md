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
这里只做文件下载和校验、首记录格式诊断；尚未完成服务器传输、全量转换、有效样本/元素统计及冻结分区验收。
MLearn应保留作者测试文件来源，验证集仅从作者训练数据中划出；Perov-5保留作者三个划分。
旧的 `tmp/mlearn-source.zip` 是截断ZIP，不能作为完整资源使用；新流程只下载以上12个固定Git blob。

## 仍在进行

JARVIS DOS固定原档的服务器续传、完整声子DOS转换正在Slurm中推进；带隙/分类已完成。
853从851保留的partial继续，已完成GMT输出仅在原档/JSONL哈希核验后复用。
Vlab不稳定时保留分片；同时发生的大文件传输按数据优先串行调度。
没有对不支持的元素或大结构做静默剔除，也没有把样例或测试fixture计为全量科学实验。
