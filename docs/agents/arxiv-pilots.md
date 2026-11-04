# arXiv v1 实际小规模实验

本记录只统计诊断子集训练，不计入144次全量正式实验。

## 带隙：四原模型、两种初始化

代码 `6a179b1`；RTX5090，float32，seed123，固定64/16/16划分，三epoch，共同batch2。
配置来自Slurm895冻结矩阵，未按原子数/标签筛选；两种初始化使用相同数据、任务头和优化设置。
MACE/NequIP scratch的原生邻居归一化只从64个训练结构拟合。

| 模型 | Slurm | 微调测试MAE/eV | scratch测试MAE/eV |
|---|---|---:|---:|
| cgcnn | 912 | 0.640017 | 0.725621 |
| alignn | 913 | 0.298194 | 0.539878 |
| mace | 916 | 0.572190 | 0.594092 |
| nequip | 915 | 0.595268 | 0.616919 |

这些数值只作执行验收，16个测试结构不用于推断模型优劣或论文全量泛化排名。
每版均完成三轮全骨干训练、16条完整验证选模、validation-best的16条测试预测及checkpoint重载。
回传后独立核验全部测试ID与冻结manifest完全一致；保留合法零带隙标签。

每个模型先通过两结构的独立原包预测/特征对照，再扫描全部64训练图，
然后分别独立预检两种初始化，并以共同batch重新双侧预检。四个worker各测量100batch，
包含最坏满batch和普通batch，峰值CUDA内存及完成的最坏索引均有记录。
未将原包CPU数值对照、图扫描、预检的权重更新当作正式训练。
这些容量证据只覆盖当前64条诊断训练数据，不能替代全量训练集的最大图扫描。

所有八版的原冻结配置均保持；运行时新增的dataset.selection=first/selection_seed、
任务头bias/feature_processing/adapter版本及resolved_components为既有解析默认值/元数据。
数据/划分SHA、全部显式头与优化参数逐项保持；scratch统计单独记录且源/分区绑定。

## 原构造器与失败证据

Slurm910通过17项零skip兼容回归及CGCNN/ALIGNN原类、原状态布局、随机种子、BN和重载验收。
911通过MACE/NequIP各五项真实原生图、训练分区绑定、RNG/dtype隔离与fresh构造检查；
按实际执行Git blob核验五份源码SHA。

保留900/901/903/906的构造失败证据及902/904/907精确诊断：
CGCNN旧BN计数器使用原strict loader在隔离副本中迁移；MACE只canonical化已确认的六个结构bool；
NequIP用官方全局初始化并保留逐元素中性shift形状。未知状态/形状仍拒绝。
908/909在device=cuda索引解析处提前失败，914在临时对照脚本未cast float32处提前失败，均未训练。
没有修改原架构/cutoff、裁掉结构、降低精度或跳过非法状态来取得通过。

## 证据与后续范围

服务器结果：`runs/pilot-bandgap-912-cgcnn/`、`runs/pilot-bandgap-913-alignn/`、
`runs/pilot-bandgap-916-mace/`、`runs/pilot-bandgap-915-nequip/`；best/last均留在原目录。
本地忽略目录 `results/paper-pilots-20261104/bandgap/` 保存原始报告、图探针、容量worker结果、
完整测试预测与 `verified.json`；不把数据/权重/运行结果提交普通Git。

当前诊断8/48，正式0/144。下一批分类与声子谱；介电/力场另验导数和旋转，生成另验新训练/独立评测流程。
全量正式训练还须完整训练图扫描、共同batch、100–500batch资源预算及完整留出评测等原计划门禁。

- 2026-11-04T21:17:35+08:00????917?924????917/918/919???????????920 NequIP???????921?924????????8?????????????6?????????????14/48????0/144?

## 分类与声子谱：第二批16次真实pilot

代码532e8c6仅比已验收6a179b1增加文档，运行代码未变；917–920分类、921–924声子谱全部passed。
每模型两版均为seed123、64/16/16、三epoch、batch2。各自原包对照、完整64图、四次100batch容量、validation-best、重载及完整16条测试ID已回传独立核验；谱每版计3200个标量标签。
证据在忽略目录results/paper-pilots-20261104/scalar-spectrum/；所有显式冻结配置保持不变，仅补既有解析默认及训练绑定统计。累计24/48次诊断已核验，正式0/144。
分类原始报告含confusion matrix、F1、ROC-AUC，尚缺计划要求的balanced accuracy字段，正式评测前补齐并从原始计数回补，不能把已有字段当完整指标交付。
