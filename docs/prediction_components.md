# 配置性质预测组件

`prediction.version: 1` 启用原生特征读出，省略该段继续使用历史组装方式。
新路径为 `backbone → NativeFeatures[N,F] → readout → 输出`；省略 adapter 时不会创建独立模块。
官方模型保持原始图处理和主干层，新任务头随机初始化。

| 示例 | 主干 | 读出及训练方式 |
| --- | --- | --- |
| [带隙](../configs/prediction_bandgap.yaml) | 官方 ALIGNN | 原生512维 → graph_mlp，全参训练 |
| [200通道谱](../configs/prediction_spectrum.yaml) | 官方 CGCNN | 原生64维 → linear，冻结主干 |
| [介电响应](../configs/prediction_response.yaml) | 官方 MACE | response 内部 small_response / basis2，冻结主干 |
| [仅力监督](../configs/prediction_force_only.yaml) | 官方 MACE | node_mlp → sum 得能量 → 求导，冻结主干 |

预先准备 [官方依赖与权重](../src/universal_gnn/backbones/official/README.md) 和示例指定的真实数据。
Guqq2 上从仓库根目录执行，训练、推理通过 Slurm：

```bash
mkdir -p runs
sbatch scripts/ugnn.slurm --mode train --config configs/prediction_bandgap.yaml \
  --logging runs/native-gap --save checkpoints/native-gap.pt
sbatch scripts/ugnn.slurm --mode train --resume checkpoints/native-gap.pt --epochs 60 \
  --logging runs/native-gap-resumed --save checkpoints/native-gap-resumed.pt
sbatch scripts/ugnn.slurm --mode infer --resume checkpoints/native-gap-resumed.pt \
  --dataset data/acceptance/bandgap-10.json --logging runs/native-gap-infer \
  --results results/native-gap.jsonl
```

提交后等待上一作业成功完成，再提交依赖其 checkpoint 的下一作业，或使用 Slurm `--dependency=afterok:JOBID`。
默认处理全部数据并使用 mini-batch；示例不包含正式训练/验证/测试集划分。

读出选择与规格

`linear` 在图聚合后应用 `Linear(F,D)`；`graph_mlp` 在聚合后应用 MLP；
`node_mlp` 对每个节点应用 MLP 再聚合。后两者必须声明非空 `hidden_features`，激活为 silu。
节点任务使用 `pooling: none`；图任务的 sum/mean 必须与 `PropertySpec.reduction` 相同。
`graph_mlp` 仅支持图任务。输出宽度/形状由性质规格决定，不通过读出配置重复声明。

默认直接读出要求偶标量特征。非标量 irreps 可显式选择
`feature_processing: {name: scalar_invariants}`，再接普通 linear/MLP；维度变成标量不变量宽度，
不会隐式压缩至32。仅有 feature_dim 不能描述非标量表示。

`response` 保留辅助变量求导机制。`feature_processing: {name: equivariant, profile: small_response,
basis_version: 2}` 显式启用几何/等变表示处理，cutoff 默认来自主干，也可显式设置。
该 profile 的内部宽度由自身结构决定，与原生 F 分开记录。
不选择该处理时，偶标量输入仍可预测固定坐标系的张量分量，但不承诺旋转协变；
非标量输入则须明确选择等变处理或标量不变量处理。换主干不会自动切换路线。
Equiformer 目前声明 SO(3)，不能据此声称反射下的 O(3) 保证。
这里的求导不自动建立不同性质共享同一物理势的关系，也不施加晶体对称约束。

原生维度与自定义模型

维度依次从 `feature_spec`、`irreps`、模型 `feature_dim` 读取，配置 `backbone.feature_dim` 仅作回退或一致性断言。
例如带隙示例的512是该发布权重的输出规格断言，不修改官方隐藏层宽度。声明冲突在组装时拒绝；
实际节点 shape、映射、dtype/device、几何引用和表示语义在前向时校验。
自定义模型接口见 [标准](standards.md)，可直接使用现有 [KNN+GCN](../examples/custom_knn_gcn/README.md)。
声明了不变标量语义的模型允许只提供 feature_dim；等变非标量必须提供 irreps、basis、transformation。

冻结与求导

`optimization.train_backbone`、`train_readout` 默认 true。冻结组件参数不进优化器，且在全局 train 后仍为 eval；
训练器检查参数和持久缓冲区没有被修改。冻结不关闭输入 autograd，因此仅力训练和响应求导仍可工作。
读出内部 feature_processing 随 train_readout 管理。只有配置了实际独立 adapter 才允许 train_adapter：

```yaml
prediction:
  version: 1
  adapter: {name: equivariant, profile: small_response, basis_version: 2}
  readout: {name: response, pooling: mean}
optimization: {train_backbone: false, train_adapter: false, train_readout: true}
```

同一种转换不能在独立 adapter 和读出内部重复选择。省略 prediction 的旧路径中，原有 adapter 是实际组件，
因此仍可独立冻结。全部组件冻结时允许推理，训练拒绝空优化器。

新式力场要求 `node_mlp + sum`，并要求主干声明已验证的 positions/strain/mixed 导数能力。
六个已登记官方发布权重均已完成该声明；五个新增主干的测试及适用设置见 [力场验收](agents/forcefield-backbones.md)。
CGCNN、Equiformer训练主干参数时必须显式使用：

```yaml
optimization:
  train_backbone: true
  train_readout: true
  backbone_eval: true
```

这会保留主干参数梯度，同时固定BN运行统计并关闭随机训练层，保证本框架要求的结构独立、确定性力场执行。
其余三个新主干ALIGNN、MEGNet、NequIP的默认全参模式通过。冻结主干时本来就保持eval，无需该额外设置。
从已保存的其他训练策略切换到该设置仍须显式组件暖启动，不能直接复用旧优化器状态。
仅力监督不需要能量/应力标签；能量、力、应力仍由同一新能量头计算。仅力标签不能确定绝对能量偏置。

续训、换头与迁移

`--resume` 完整恢复要求相同的读出、内部 profile、pooling、输出规格、冻结策略和参数组；可以增加总 epochs。
更换头或冻结策略时，准备完整目标配置并显式初始化兼容组件：

```bash
sbatch scripts/ugnn.slurm --mode train --config configs/prediction_spectrum.yaml \
  --warm-start checkpoints/cgcnn-gap.pt --warm-start-components backbone \
  --logging runs/cgcnn-spectrum-warm --save checkpoints/cgcnn-spectrum.pt
```

源 checkpoint 必须也是相同官方 CGCNN 架构和原始 artifact；例如用带隙配置改为 CGCNN 先训练。
目标配置不会从暖启动源自动合并。选中的组件逐一严格检查并加载，其余组件保持目标配置的新初始化，
优化器重新建立；不会用全模型 `strict=False` 隐藏不匹配。源路径/SHA、加载键、忽略/新初始化组件写入 report.initialization。
`--warm-start` 不与 `--resume` 混用。官方原始 `.model` 仍放在 `backbone.checkpoint`，不是 UGNN 暖启动文件。

`schema_version=1`、checkpoint format1/2 和 training_state.version1 不变；新 checkpoint 额外保存
`components.version=1`，用于规格/参数组验证。旧文件缺此字段仍按旧构造重放；从旧32维路径改成新路径必须显式暖启动。
仅将已验证导数能力元数据从false提升为true，不改变网络/权重结构，允许旧监督checkpoint回放并记录
`checkpoint_capability_updates`；能力降级、形状、表示或训练策略变化仍会拒绝。
推理可在 override 配置中关闭参数梯度，所有组件仍为 eval，并保留输出所需的输入求导。

查看 `config.resolved.json` 的 prediction、optimization、resolved_components，以及 report.components，
可确认原生 F、处理后的规格、聚合位置、变换保证、实际组件参数和冻结模式。
已知未使用的官方原任务头单列，报告的容量上界不等于有效任务参数量。

扩展读出在 `readouts` 注册工厂即可，不需修改 provider 和通用训练循环；接口见
[readouts README](../src/universal_gnn/readouts/README.md)。generation 不接受 prediction/optimization，
本次扩展范围为性质预测。

已执行的118项回归及11组官方真实数据链，见 [验收记录](agents/prediction-components.md)。
