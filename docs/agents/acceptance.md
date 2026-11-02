# 十结构执行验收

六个 backbone 各 16 项任务配置，共 **96/96 格**真实十结构训练与 checkpoint 重载推理通过；
六模型各十结构的模拟流程 **6/6 组**通过。服务器与本地独立证据审计均为 passed，缺失与失败项为零。
本地默认单元 **34 passed**；服务器核心/NequIP、MACE 两环境各 **32 passed**（704/705，新增两项审计检查随后在本地通过）。
没有进行新的 DFT 计算。

| 模型 | 实际实现 | 训练/重载推理 | 十结构模拟 |
| --- | --- | --- | --- |
| CGCNN | 原生 Torch 架构变体 | 16/16 | 通过，725 |
| MEGNet | 原生 Torch 架构变体 | 16/16 | 通过，726 |
| ALIGNN | 原生 Torch 架构变体 | 16/16 | 通过，726 |
| Equiformer | e3nn 点积注意力变体 | 16/16 | 通过，726 |
| NequIP | 官方 0.14.0 卷积主干 | 16/16 | 通过，726 |
| MACE | 官方 0.3.16 interaction/product | 16/16 | 通过，726 |

16 项配置为形成能、带隙、分类、逐原子电荷、逐原子磁矩、电子 DOS、声子 DOS、
介电张量、压电张量、弹性张量、固定组成生成、E/F/S 力场、Born 电荷、同源 DFPT 介电张量、
Raman 曲线、光学介电曲线。介电的两项使用不同数据/适配路线，不能计作两种不同输出格式。

每格十个真实结构、30 epochs，检查有限 loss/梯度、backbone 梯度、参数更新、
最终 loss 低于初始值以及 checkpoint 重载输出一致；生成另含随机初态采样和数值几何检查。
默认分别训练各任务；联合多任务模型不在本轮实现范围。

## 运行版本与证据

| 内容 | 实际源码 | Slurm |
| --- | --- | --- |
| 首轮六模型各11项 | `70e5bb08364c09dd4c98463008f94d3196eaf939` | 539 / 583 / 595 |
| EFS / Born / DFPT介电18格、新基底等变张量9格 | `8b15e8366da2729f7ff101c09bd4d4e130b6bb9c` | 676 / 677 |
| Raman / 光学12格 | `48aa865a5e19906b15d776a337de415d0ba4d176` | 711 |
| 六模型模拟 | `6b86f460a3582f430266cde982221f1647225438` | 725 / 726 |

最终96格索引用新版9格张量记录覆盖相同任务的旧记录，保留所有原始报告。
旧66个 checkpoint 另在608/609/610逐一回放一致；格式版本正确恢复旧几何基底。
以上是分阶段实跑的版本，不把当前 HEAD 冒充全部训练的源码。

完整本地归档：`results/server-20261102-final/evidence.tar.gz`，2051712 bytes，
SHA256 `e7dd9d52cf4b599b85fc5aee4a6503c14daa61d405bb4ee5dd42ac0bae97eb30`。
已验证哈希与解包路径边界，310个文件。查看：

- [最终索引](../../results/server-20261102-final/evidence/results/acceptance-index.json)
- [本地独立审计](../../results/server-20261102-final/evidence/results/local-audit.json)
- [CGCNN模拟实例](../../results/server-20261102-final/evidence/runs/workflows/cgcnn/report.json)
- [数据清单](../../data/acceptance/manifest.json)

归档包含每格完整JSON、矩阵、实际显微图数组、数据清单与对应日志；checkpoint保留在服务器
`/home/xmz/universal/runs` 对应任务目录。数据、权重和生成报告均未提交 Git。
早期66格的独立归档仍保留 `results/server-20261102/evidence/index.json`；控制器已清理64条早期状态，
如实标为 not_retained，不伪造已清理的退出码。

## 数据与模拟定义

JARVIS/GMTNet/ALIGNN作者公开样本的URL、原文件SHA、记录索引、单位、Voigt顺序均随数据保存。
DFPT675从原始归档读出同一vasprun.xml的几何、VASP电子free_energy、力、ASE应力、Born和介电，
应力转为tensile-positive GPa，不施加ASR或空间群投影。

Raman使用 [CRD 1.0.1 原档](https://archive.materialscloud.org/records/0m9r0-g3486)，
发布MD5 `e2aaea03df70fda95dbd970c60456882` 已核对。
初选有部分条目的张量槽少于3N，703正确拒绝；保留剔除清单，重新选十条严格对齐样本，707整理成功。
使用原始张量与带符号频率生成200点50–1000 cm^-1曲线，Lorentz HWHM=5 cm^-1，逐结构峰归一化；
不把稀疏峰文本当完整标签，也不宣称该预处理与论文逐细节相同。

光学标签来自同一 [NIST材料XML](https://www.ctcms.nist.gov/~knc6/static/JARVIS-DFT/JVASP-10.xml)
的结构及TBmBJ三个对角虚部的迹平均；0.05–10 eV、200点线性插值，保留源数据符号。
KK实部是有限频窗主值积分，缺失频窗权重假定为零，端点不可靠。

模拟组合分别训练的力场/Born/介电模型：固定晶胞FIRE 3步、100 K初始化/0.25 fs的短MD 2步、
自动微分Gamma Hessian、IR/Born收缩、介电坐标导数Raman，以及自然丰度中子截面加权Gamma DOS。
虚频保持带符号并从正频展宽中剔除，不以绝对值伪装稳定。
STEM用真实abTEM1.0.6多层切片与环形探测器，对两帧MLFF-MD快照求平均；
有限簇置于共同正交真空盒，200 keV、20 mrad会聚角、25–60 mrad探测角、自适应势网格、8×8扫描。
60张保存图均通过有限性、正强度和非恒定检查。706的abTEM1.0.8/Py310兼容失败保留，未当作成功。

## 结论边界

这些结果验证小数据集上的优化、求导、序列化与模拟执行，不代表测试集精度。
部分loss下降很小；不声称模型收敛、生成结构质量或长时间MD稳定性。
短FIRE未收敛时如实记录；Gamma谱不是完整布里渊区结果，有限簇STEM不是周期体材料的完整显微基准。
不变模型的固定分量路线不承诺旋转协变；共同等变路线按其类型/梯度检查验收，不加晶体对称约束。
本轮未运行论文完整规模或CHIPS-FF/WBM/AtomBench全套基准。
