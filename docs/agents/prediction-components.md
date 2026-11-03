# 性质预测组件解耦验收

需求：[prediction_decoupling_requirements.md](../plan/prediction_decoupling_requirements.md)。
实现与用法见 [配置组件](../prediction_components.md)、[格式标准](../standards.md)。
2026-11-03，A～E已实施，ACC-01～13验收通过；下表真实链与最后源码回归均已完成。

组装改动

- `prediction.version: 1` 显式启用原生 `[N,F]` 直连；linear、graph_mlp、node_mlp、response统一注册。
- FeatureSpec发现/断言维度，逐次前向验证表示与映射；必要转换显式放在读出内部，独立adapter可选。
- 按组件冻结参数及模式，检查持久buffer不变，保留坐标和混合导数；优化器参数组互斥。
- 完整续训核对规格、策略及有序参数映射；组件暖启动逐一严格加载，复用官方artifact和自定义源码检查。
- 旧配置及format1/2不自动迁移，原32维adapter与state_dict键保持。新配置保存可选components.version1。

测试与原生对照

| 证据 | 源码 | 结果 |
| --- | --- | --- |
| Slurm765 / 766 | ae90d7e | core / MACE 各114 passed |
| Slurm769 / 770 | 0cc5a98 | core / MACE 各117 passed |
| Slurm773 / 774 | a25095e | 最终core / MACE各118 passed，含自定义源码暖启动非突变检查及新式力场E/F/S批次独立性 |
| Slurm771 | 0cc5a98 | CGCNN原发布权重；10结构原生特征及原预测误差均0；5个新组合通过 |
| Slurm772 | 0cc5a98 | MACE原发布权重；10结构特征最大误差2.3842e-7，原能量误差0；6个新组合通过 |

core沿用Torch2.7.1/e3nn0.5.8/NequIP0.14；MACE及官方真实链沿用Torch2.7.1/e3nn0.4.4/MACE0.3.16。
真实链使用既有universal-official环境及原CGCNN源码。未安装新依赖或改写官方图/层，环境详情见 [env.md](env.md)。
本次MACE small的读出前256维均为0e，满足直接头的偶标量要求；含非标量通道的其他模型仍须显式合法转换。
完整训练、推理及回归均通过Slurm；本地仅进行小型解析/梯度、配置/文档和文件证据检查。

真实链结果

各组合使用10个真实结构、4 epochs、batch5、float32、单CPU；训练/重载预测遍历全部10条。
带隙使用JARVIS optb88vdw_bandgap，谱使用200通道pdos_elast，张量/力使用已有DFPT记录。
原始来源URL、文件哈希、记录索引和单位保留于数据metadata及验收manifest，无新增DFT计算。

| 主干 / 原生F | 读出 | 主干策略 | 初始→最终归一化训练损失 |
| --- | --- | --- | --- |
| CGCNN / 64 | linear | 全参 | 82.31377 → 13.97130 |
| CGCNN / 64 | linear | 冻结 | 82.31377 → 27.63631 |
| CGCNN / 64 | graph_mlp | 全参 | 2.95887 → 0.81710 |
| CGCNN / 64 | graph_mlp | 冻结 | 2.95887 → 0.71050 |
| CGCNN / 64 | graph_mlp，200通道谱 | 冻结 | 388.11007 → 140.26922 |
| MACE / 256 | linear | 全参 | 0.94557 → 0.82579 |
| MACE / 256 | linear | 冻结 | 0.94557 → 0.52520 |
| MACE / 256 | graph_mlp | 全参 | 1.86223 → 1.75865 |
| MACE / 256 | graph_mlp | 冻结 | 1.86223 → 1.11024 |
| MACE / 256 | response，介电，内部small_response/basis2 | 冻结 | 1.46010 → 0.24124 |
| MACE / 256 | node_mlp+sum，仅力监督 | 冻结 | 1.28138 → 0.34194 |

所有冻结主干的完整state（参数和持久buffer）差分范数为0；训练中主干保持eval、读出为train。
全参CGCNN的纯参数差分约0.11620/0.11342，MACE约0.55687/0.56211。
CGCNN完整state差分约35.9还包含BN计数，不将其误称为参数更新量；纯参数值由报告总参数差分与无buffer的直接头差分独立分解获得。

仅力链的新能量头混合参数/坐标梯度范数为0.00844374，主干无参数梯度。
真实float32力/应力有限差分绝对误差分别4.15e-6、1.49e-5（step.002，预先登记rtol.02、atol.002）；
解析float64单元保持rtol2e-5、atol1e-9。张量旋转误差1.91e-6，未放宽已有原生参考容差。
仅力链另验证1→4轮完整续训与连续训练一致、全参数冻结后对10条进行保留输入求导的JSONL推理。

验收映射

| ID | 具体证据 |
| --- | --- |
| ACC-01 | test_prediction_components：两种F、缺失/冲突/实际错宽、原生首层；771/772确认64/256且无独立adapter |
| ACC-02 | 显式独立adapter与内部处理归属、重复转换拒绝；非标量标量化/反射不变单元；response内部处理旋转测试 |
| ACC-03 | linear/graph_mlp/node_mlp在F8/256、5通道谱与node输出；非线性聚合次序差异、混合大小batch独立性；真实200通道谱 |
| ACC-04 | 注册最小自定义头在两个原生F构造/前向，无provider/trainer专用分支 |
| ACC-05 | 受控BN/dropout模块：冻结参数/buffer/modes、冻结读出向上游反传、互斥参数组、全冻结训练拒绝/推理允许 |
| ACC-06 | 冻结主干force-only解析混合梯度与772真实新头优化；缺E/S标签不重新绑定 |
| ACC-07 | node_mlp+sum限制；解析力/应力有限差分、总力与E/F/S批次独立；772真实力/应力差分 |
| ACC-08 | 显式response profile、旋转/参数梯度；偶标量等变主干也不自动切换fixed-frame保证 |
| ACC-09 | 四份YAML规范化；未知字段/版本/宽度/聚合、冲突route、错误scope/construction、无adapter写train_adapter及generation块拒绝 |
| ACC-10 | 原80项回归、format1/2数值回放、旧force-only/EFS与生成路径保持 |
| ACC-11 | 新重载、连续/分段完全一致、变头/冻结拒绝resume、显式暖启动记录；adapter基底和自定义源码冲突拒绝且目标不变 |
| ACC-12 | 完整resolved配置、实际训练/最终模式、组件参数与未用原头；51份证据文件独立hash/ID/标签审计 |
| ACC-13 | 771/772共11组官方真实链；原生对照保持，力场冻结和显式profile张量均通过 |

具体测试见 [test_prediction_components.py](../../tests/test_prediction_components.py) 和
[原有checkpoint回放](../../tests/test_checkpoints.py)；执行器为
[validate_prediction_components.py](../../scripts/validate_prediction_components.py)。

证据位置与边界

- 服务器：`runs/prediction-cgcnn-real2-771`、`runs/prediction-mace-real2-772`，保存配置、report、validation、checkpoint和force-only投影。
- 本地忽略目录：`results/prediction-components/evidence`，已归档51份JSON/JSONL/日志/数据及逐文件manifest。
  传输包160856字节，SHA256 `c60039d13548c4c8a4d9eae2b9bd485d92fd91aee0b6fba396bcdcbe0543f7d6`。
- 最终回归日志另归档 `results/prediction-components/final-unit-evidence.tar.gz`，743字节，
  SHA256 `250e8cec88b68e08ffdf4536fa6fdf92230a323c7b393e970a7f38a454bb02f0`，对应773/774。
- 独立审计：`results/prediction-components/audit.json`；原始ID/元素/PBC精确一致，坐标/晶格/力与原记录经声明的float32转换后精确一致，投影仅含forces。
  权重和生成结果均不进入Git。
- 历史767/768在模型启动前因已安装scripts包遮蔽而失败；改用脚本文件入口后771/772通过，旧日志保留。
- 真实11组在0cc5a98执行。最终源码补充仅为自定义暖启动源码核对及更严格的解析批次测试，不影响这些真实链的前向和训练；用最终完整回归验证此补充。

这些是小样本执行、求导与重建验收，没有独立测试集或泛化精度结论。
本次原始验收的官方力场范围为MACE；后续五个官方主干及其模式约束已单独完成验证，见
[力场骨干验收](forcefield-backbones.md)。
本轮不要求任意checkpoint全组合、生成扩展、联合多任务或额外晶体对称约束。
