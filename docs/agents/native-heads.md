# Native/reset 原头选择验收

实现与使用见 [用户说明](../native_heads.md)、[标准](../standards.md#官方预测头选择)。
生产实现提交 `9ab9aec`；实际官方模型验收脚本提交 `35a465f`。全程通过 Slurm，
未修改上游模型层、原始图构建规则或发布权重；无需 DFT。

## 自动测试

Slurm 803 / 804 / 805 在 core、MACE/e3nn0.4.4、Equiformer/PyG2.0.4 三个环境各通过
139 项测试。覆盖枚举/冲突/默认 reset、原任务规格、原模块路径不重复注册、共享参数拒绝、
冻结参数/持久缓冲区/模式、唯一优化器参数、混合力梯度、跨模式主干迁移、连续/分段续训一致、
切换模式拒绝完整 resume，以及既有格式1/2与旧任务回归。

## 六个官方原头

原始元数据 Slurm 796–800、802；801 因旧 e3nn 初始化顺序失败，保留失败日志，
通过现有 load_o3 兼容入口修复 inspector 后802通过，没有修改依赖或上游源码。

Slurm 806–811 的每个模型均通过两条真实结构上的独立上游 API 对照：

| 模型 / 作业 | 上游参考 | 原特征/预测最大误差 | 物理输出差异 |
|---|---|---|---|
| ALIGNN / 806 | 原 Graph.atom_dgl_multigraph + forward | 0 / 0 | 0 |
| CGCNN / 807 | 原 CIFData/collate_pool + forward | 0 / 0 | mean/std 还原后 0 |
| MEGNet / 808 | 原 MatGL predict_structure | 0 / 0 | inverse_transform 后 0 |
| MACE / 809 | 原 MACECalculator descriptors、ASE 能量/力/应力 | 0 / 0 | E/F 0；应力 ≤3.05e-7 GPa |
| NequIP / 810 | 原 NequIPCalculator + 原邻居/类型变换 | 0 / 0 | E/F 0；应力 ≤4.02e-7 GPa |
| Equiformer / 811 | 原 V1 构造/config/state + OCP AtomsToGraphs | 0 / 0 | OCP target denorm 后 0 |

CGCNN mean `2.353832203000784`、std `1.4802391239920374`。
Equiformer mean `-1.525913953781128`、std `2.279365062713623`，原任务明确为
“Relaxed state energy prediction from initial structure”。MEGNet 原包装已经反标准化；
MACE/NQ 的参考能与 scale/shift 由原网络执行。

六模型分别冻结主干、冻结原头，共12条梯度/更新检查全部通过：冻结部分梯度为0，
参数和缓冲区逐值不变，另一部分梯度非零，优化器参数无重复。MACE/NQ 用 forces
平方范数验证混合梯度；其他模型用输出平方范数作梯度诊断。这些诊断目标不充当数据标签。

## 实际标签训练与续训

每个任务10条真实记录，batch_size5，float32，learning_rate1e-5，只训练官方原头。
先训练2epoch，精确重载，再完整续训到3epoch。

| 模型 / 任务 | 初始损失 | 2epoch | 续训3epoch |
|---|---:|---:|---:|
| ALIGNN / JARVIS 带隙 | 0.00537697 | 0.00502906 | 0.00487559 |
| CGCNN / JARVIS 带隙迁移 | 12.06043 | 12.02487 | 12.00722 |
| MEGNet / 每原子形成能 | 0.122701 | 0.121805 | 0.121390 |
| MACE / force-only | 2.887692 | 2.883865 | 2.881891 |
| NequIP / force-only | 1.906916 | 1.900956 | 1.897866 |

损失为框架既定训练损失，仅证明执行、优化和续训链路，不作为独立测试集精度。
CGCNN 官方带隙训练来源与当前 JARVIS 标签不同，属于同任务迁移。
Equiformer 当前缺少匹配 OC20 IS2RE 标签，只完成预测与梯度诊断，未替换成其他性质标签训练。

## 证据

服务器 `runs/native-head-metadata`、`runs/native-heads/<model>`；本地忽略目录
`results/native-heads`。权重/checkpoint 留在服务器，不通过普通 Git 提交。
初次通过的验收包64文件、75607字节，SHA256
`1857302efe46f3873c928e9595ea9d998816e540fb16fc355566f285609335b5`。
每个文件的长度及 SHA256 已独立核对，失败元数据日志也保留。

最终验收包86文件、100186字节，SHA256
`299c54eb42c47e272ffcc9f58a4b317543ab2a837b0082a61e9b1945fcf92201`。
原始小数据、元数据、配置、训练报告、测试与失败日志、迁移报告都在包内。
本地 `local-audit.json` 独立核对86文件哈希、五任务各10条ID/float32几何/源文件与绑定、
续训指纹、三环境测试结果及历史回放；全部通过。

## 最终真实集成检查

脚本 [validate_native_transfer.py](../../scripts/validate_native_transfer.py)，源提交 `0b22593`，
Slurm 812–817（依次 ALIGNN、CGCNN、MEGNet、MACE、NequIP、Equiformer）全部通过：

- native→reset：只迁移原主干，原官方头及新建 UGNN 头都保持目标初始化。
- reset→native：有意改变 reset 中未使用的原头，再迁移主干；native 目标原头仍逐值不变。
- 原主干所有选定状态逐值相同，优化器重建，报告列出被排除的头状态键。
- 六模型均完成10结构全冻结 JSONL 推理，所有组件可训练参数数为0。
- 实际旧 CGCNN 771 checkpoint 不含 head_mode，带隙回放误差0。
- 实际旧 MACE force-only 764 checkpoint 不含 head_mode，E/F/S 回放误差均0。

服务器 `runs/native-transfers/<model>` 保留真实迁移 checkpoint、输出及报告。
Equiformer 在现有真实几何上执行推理/迁移检查，仍不声明拥有匹配 OC20 训练标签。
