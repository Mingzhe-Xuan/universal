# 官方预训练主干验收（2026-11-03）

六个标准模型名现默认使用官方原模型及登记的发布权重。图构建、元素编码、消息传递、归一化、
cutoff与原始buffer均保留；原权重严格加载后，在选定的读出边界提取节点表示，连接随机初始化
的新任务头，默认同时微调主干。旧实现仅显式 `implementation: legacy` 使用，旧checkpoint自动兼容。

## 实际验收

以下均在Slurm上对同一组十个真实JARVIS结构及其原始OptB88vdW带隙训练四轮，batch_size=5、
float32、learning_rate=1e-4。表中loss是按数据尺度归一化的训练损失，不是eV误差或测试集指标。

| 模型 | 实际发布资源 | Slurm | 初始loss → 最终loss | 原生特征最大差异 |
| --- | --- | --- | --- | --- |
| MACE | MACE-MP small128-L0 | 743 | 2.363605 → 2.133720 | 2.3842e-7 |
| CGCNN | 作者band-gap.pth.tar和atom_init | 744 | 1.444897 → 1.003017 | 0 |
| MEGNet | 作者MatGL MEGNet-MP-2018.6.1-Eform | 745 | 1.022462 → 0.882651 | 0 |
| ALIGNN | ALIGNN2 pure-Torch optb88vdw_bandgap_radius | 753 | 1.186535 → 0.998191 | 0 |
| NequIP | NequIP-OAM-S-0.2可训练package | 758 | 2.214602 → 1.387693 | 0 |
| Equiformer | 原始V1 OC20 IS2RE best_checkpoint | 759 | 2.236756 → 1.211993 | 0 |

每项均验证完整原始参数/buffer加载、独立官方入口对照、原主干参数实际更新、一阶/二阶坐标导数
有限，以及外部原权重路径故意不存在时的自包含重载。参数覆盖率与buffer覆盖率均为1。
MACE原能量对照差异为0；NequIP原能量/力对照也均为0。其余原预测对照差异均为0。

独立入口分别为MACECalculator、CGCNN CIFData/collate_pool、MatGL predict_structure、
ALIGNN Graph、NequIPCalculator和独立原始Equiformer构造/forward。CGCNN只适配文件读取，
直接提供同一真实Pymatgen结构以避免CIF写入舍入；原始预处理与模型层不变。

NequIP双线程float32的官方计算器自身有约2e-5的力重复性误差；756隔离确认关闭JIT也不消失。
758采用单线程，原严格容差不变，特征/能量/力对照均为0。没有为通过验收修改网络层或放宽断言。

## 实现与环境边界

- MACE使用原模型对象和AtomicData，并读取原forward提供的node_feats；关闭旧力/virial/stress求导。
- CGCNN、MEGNet、ALIGNN、NequIP、Equiformer使用原模块，在旧读出边界截取特征。
- NumPy预处理的几何量保留官方前向数值，导数通过等价Torch表达式连接；不改变离散邻居规则。
- Equiformer选原V1，保留SO(3)语义；不把V2中detach自行删除，也不宣称该权重具有反射等变性。
- 本次所选六个权重的最终节点特征均为标量表示；统一张量/向量读出需要时使用现有几何适配，
  不为增加irreps而改宽原模型。

`universal-official`使用Torch2.7.1、e3nn0.4.4、MACE0.3.16、ALIGNN2026.10.11、
MatGL1.0.0、DGL1.1.3；NequIP使用core0.14.0/e3nn0.5.8加载发布包自带的0.15源码。
`universal-equiformer`只隔离PyG2.0.4以保留原OCP所需接口；其余科学包及原始源码只读复用。
PyG构建/安装也在Slurm759执行，原父环境2.7.0未替换。完整版本和路径见 [env.md](env.md)。
MatGL模型版本提示保留；本次MEGNet主体源码与v1.1.3字节一致，严格state与原API实测通过。

## 默认行为、CLI与证据

训练省略structures或设null/all时使用全部数据；mini-batch默认32，新训练默认float32，均可配置。
标准JSONL按偏移索引读取，推理JSONL逐batch写出；旧checkpoint无dtype时按原float64解释。
13结构的全量/尾batch、随机子集、精度、原子预算、流式推理和精确续训均进入完整回归。
Slurm754/755两个环境各71 passed；新增Equiformer环境Slurm761也完成71项，其
[独立日志归档](../../results/official-pretrained-20261103/new-env-regression.json) 记录实际文件名与hash。

Slurm760直接运行文档的 `scripts/ugnn.slurm --mode ... --model alignn` 参数链，未提供
原checkpoint路径，由默认profile缓存初始化。实际训练2轮、完整续训到3轮、重载推理十条均通过。
配置为structures:null、batch_size:32、float32；新任务头随机初始化，主干来自原始发布权重。

本地 [证据归档](../../results/official-pretrained-20261103/evidence.tar.gz) 为33372字节，SHA256：
`37813959c777dd764f949c6bd33ea68fbd524e52fd3e2d918742cf1c96071185`。
[本地独立审计](../../results/official-pretrained-20261103/local-audit.json) 核对全部文件hash、
六模型同一组十个ID/几何、正主干参数变化、loss下降与CLI配置/恢复轮数/推理条数。
归档含六份validation与report、真实数据、日志、旧失败记录、环境元数据及85个原始源码文件的
hash清单；服务器现场也已逐文件复核85个源码hash一致。checkpoint保留于服务器对应runs目录。

这只证明所列官方格式/版本的加载与十结构微调执行，不代表任意官方checkpoint可互换、
所有任务已重新完成官方权重基准，或论文测试集精度。旧96格变体矩阵作为历史证据单独保留。
本轮没有运行DFT。
