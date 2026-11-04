# arXiv v1 预训练来源与重叠审计

2026-11-05。对象为[固定144实验定义](../plan/arxiv_v1_experiments.md)实际登记的四份权重，
不是同名模型的所有版本。主干、任务头和整个模型scratch按既有定义区分；reset任务头不能消除预训练曝光。

## 权重来源

| 骨干／固定资源 | 作者声明的数据与目标 | 本轮可验证的训练ID |
|---|---|---|
| CGCNN `band-gap.pth.tar` | Materials Project带隙，见[固定作者说明](https://raw.githubusercontent.com/txie-93/cgcnn/f42ab233c4ee0c416879d6bc2d22a264418413ad/pre-trained/README.md) | 尚未取得与该权重对应的完整训练ID；不能报告交集为0 |
| ALIGNN `optb88vdw_bandgap_radius.zip` | JARVIS OptB88vdW带隙；固定Figshare文件67163492。作者[下载入口](https://raw.githubusercontent.com/atomgptlab/alignn/main/alignn/pretrained.py)说明包内包含三划分ID | 固定ZIP内实际含44569训练、5572验证、5572测试ID；SHA与配置计数核验后执行本次数据交集 |
| MACE `small.model` | MPTrj上的MACE-MP-0 small；[作者登记](https://raw.githubusercontent.com/ACEsuit/mace-foundations/main/README.md)的small链接与本项目固定下载资源一致 | 本轮未重建完整训练几何／材料ID交集；未知，不代表数据不公开 |
| NequIP `NequIP-OAM-S-0.2.nequip.zip` | OMat24预训练，再用sAlex与MPTrj微调，见[该固定版本发布页](https://zenodo.org/records/23472045)；包内训练配置列出能量／力／应力项 | 本轮未重建与该权重对应的完整训练ID交集；不能以MP-only模型替代OAM版本说明 |

资源SHA取自受管的[profiles.py](../../src/universal_gnn/backbones/official/profiles.py)，
并与947完整输入注册表绑定。NequIP作者预训练YAML亦有固定SHA，不能把它单独当成OAM最终微调数据清单。
本次不下载百万／亿帧势能训练库；这项选择意味着相关几何交集仍未知，不能宣称不存在。

## ALIGNN已发布ID的比较方法

[独立审计模块](../../src/universal_gnn/benchmarks/audits/README.md)只读取固定ZIP中的JSON文本，
不加载模型或反序列化权重。确认ZIP SHA、ID文件SHA、各清单内部唯一且与config计数一致，并登记跨清单冲突后，
对完整标准数据逐行验证源SHA、有序ID和冻结划分SHA。

本轮比较JARVIS带隙／派生分类、GMTNet介电、JARVIS声子DOS；它们使用相同JVASP命名空间。
每个本次train/validation/test分别统计落入原权重train、validation、test、not_listed的ID，
不把原验证曝光并入训练，也不忽略其选模作用。不对MLearn或Perov-5的其他命名空间假算“0交集”。

带隙属于同目标字段，分类由相同带隙派生；介电和声子DOS属于不同目标字段。
1008的6主/17子控制实际通过，但严格参考清单完整性门禁拒绝继续；失败报告/JUnit/日志保留。
独立Slurm1009核验固定包后确认各清单内部无重复，原train/test共有两个ID：
`JVASP-113961`、`JVASP-116461`，原train/validation及validation/test无交集。
原清单合计55713个条目，对应55711个唯一ID；这只是发布清单证据，不单独证明实际训练加载器如何处理这两个条目。

默认strict模式仍拒绝跨角色ID，原拒绝测试不变。显式`--reference-policy report_ambiguity`
允许继续**报告**这个事实：增加`multiple_roles`组，逐ID保留全部发布角色，标记
`mutually_disjoint=false`。训练/选模验证曝光合计按原角色成员关系统计，含多角色ID，
不选择一个角色覆盖另一个、不删除样本，也不把原测试清单解释为干净材料留出。
坏SHA、角色内重复、缺少清单、配置计数不符、命名空间不符仍拒绝。

各行`metadata.label_field`必须与声明关系一致。Slurm1010现已完成实际全源审计，
7主/17子共24JUnit零失败/错误/skip；七执行源按b51a781 Git blob独立核验。
三份源合计95236条数据记录，带隙与分类共享源后共核对171229条审计记录，包含76054个唯一当前材料ID。
每行SHA/有序ID/冻结分区经公共CLI核验，再在Slurm中用独立集合交集与逐行角色校验复查。

本次独立test分区的材料ID曝光如下（角色单独出现才计入前三列，多角色另列）：

| 当前任务 | test材料 | 原train | 原validation | 原test | 多角色 | 未列出 |
|---|---:|---:|---:|---:|---:|---:|
| 带隙／派生分类 | 7580 | 4405 | 586 | 528 | 0 | 2061 |
| 介电 | 499 | 385 | 66 | 42 | 0 | 6 |
| 声子DOS | 1426 | 1147 | 148 | 131 | 0 | 0 |

两个原train/test冲突ID均落在本次JARVIS带隙／分类train；该分区的原train单角色35680、
多角色2，合计训练曝光35682，不漏掉多角色。当前validation的训练曝光4482。
完整三分区、每ID角色与原始参考SHA见忽略目录 `results/paper-pretraining-overlap-20261105/1010/`，
全量逐ID清单在服务器 `runs/pretraining-id-audit-1010/<task>/id-overlap.jsonl`，SHA已随报告保存。

本次带隙／分类预训练对照不能称无泄漏泛化排名：4405个当前test材料命中参数训练清单，
586个命中选模验证清单。数值标签版本／几何是否字节相同仍未重建，不把ID命中夸大成数值标签完全一致。
介电／谱可报告跨目标迁移，同时披露上述高材料曝光；未列出仍不代表等价几何未见。
CGCNN/MACE/NequIP以及跨命名空间交集维持unknown，不以本项ALIGNN审计代替它们的交集。


## 解释与论文呈现

- 材料ID命中证明发布清单中的材料曝光；不单独证明当时几何和目标数值与本次字节完全相同。
- `not_listed`仅表示不在该ID清单，不能证明等价晶体、别名ID或其他预训练数据中未见。
- 原验证集标签可能影响模型选择，应与参数训练曝光分别披露。原测试ID也不自动等于本次完全独立材料组。
- ALIGNN带隙及派生分类若命中预训练train/validation，需明确标为已有材料／目标上的迁移适配；不作无泄漏泛化排名。
- 介电／谱可以报告跨目标迁移，同时披露材料曝光。其标签未用于这份带隙模型，不等于结构未见。
- CGCNN、MACE、NequIP及跨命名空间交集暂为unknown，不能把未取得清单写成0。
- 144主体定义保持不变。整体scratch版不加载官方已学参数，并按训练分区重新拟合所需统计；与预训练版分别报告。

对完整数据的ID审计必须通过Slurm；原始ID清单、逐条交集、JSON报告均为忽略生成物，
与训练完成数分开计数。没有更改数据、排除重叠样本或重新划分测试集。
