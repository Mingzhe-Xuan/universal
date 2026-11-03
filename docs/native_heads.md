# 选择官方原头或新建读出

在 `prediction.version: 1` 中设置 `head_mode`：

| 参数 | 行为 |
|---|---|
| `native` | 保留官方原头及权重、原任务、池化、归一化 |
| `reset` | 保留加载的官方 backbone，随机初始化配置中的 UGNN readout |

省略 `head_mode` 默认 `reset`。完全省略 `prediction` 时仍走历史组装路径，保证旧 checkpoint 兼容。
`reset` 不重置 backbone。官方原头可能仍保存在 backbone 的状态中，但不参与 reset 的预测路径。

```yaml
prediction: {version: 1, head_mode: native}
optimization: {train_backbone: false, train_readout: true}
```

这个示例只微调原头。将 `train_backbone` 改为 `true` 可联合微调；将 `train_readout` 改为
`false` 可冻结原头。两者都为 `false` 时支持推理。冻结保留输入求导，不能用 `no_grad` 包住冻结主干。
`native` 拒绝额外 `readout`、`adapter` 和条件输入，避免意外改变原任务路径。

```yaml
prediction:
  version: 1
  head_mode: reset
  readout: {name: graph_mlp, pooling: mean, hidden_features: [128, 64]}
optimization: {train_backbone: false, train_readout: true}
```

换任务通常用这个配置。`train_readout` 只控制训练，不选择头；
`--warm-start-components readout` 只复用兼容 UGNN checkpoint 的头，也不选择官方原头。

## 已登记原任务

| 默认官方 artifact | `task.property` | 原输出 | 可作为原生力场 |
|---|---|---|---|
| ALIGNN | `bandgap` | JARVIS optb88vdw 带隙，eV | 否 |
| CGCNN | `bandgap` | MP 带隙，eV | 否 |
| MEGNet | `formation_energy` | MP 每原子形成能，eV/atom | 否 |
| MACE | `total_energy` | 含原子参考能与 scale/shift 的总能，eV | 是 |
| NequIP | `total_energy` | 含每元素 scale/shift 的总能，eV | 是 |
| Equiformer | `oc20_relaxed_energy` | OC20 IS2RE 松弛能量，eV | 否 |

这张表针对仓库中已校验哈希的六个发布权重，不代表任意同名模型的 checkpoint 都有相同任务。
未知 artifact 在 native 模式下明确报错；需要补充其原任务协议后使用。自定义 provider 可实现
`native_task_contract()` 返回 `NativeTaskContract`，以及 `native_prediction(batch, contract)`。
任务名称、形状、单位、归约和输出类型都必须匹配协议，相同输出维数不能替代任务匹配。

## 输出和力场

原头保持数学运算与物理输出值；返回接口统一包装为 UGNN 格式。标量 `[B,1]`，力场返回
`total_energy` `[B,1]`、`forces` `[N,3]`、`stress` `[B,3,3]`。力的单位 eV/angstrom，
应力使用 UGNN 的拉伸正号 GPa；官方 eV/angstrom³ 应力对应乘 `160.21766208`。
需要原始包的返回字典时，provider 的 `native_forward` 继续提供官方前向接口。

CGCNN 和 OCP 的标准化输出按原 checkpoint 的 mean/std 还原；MEGNet 原前向已经做
inverse_transform，不能再次还原。MACE/NequIP 的参考能、scale/shift 和求和均保留。
原生力场从同一个官方能量求导得到力和应力，支持仅有 forces 标签的训练；不需要新增 DFT。
Equiformer 这个 IS2RE 原头预测松弛终态能量，不能解释为当前位置的势能。要训练新力场请选 reset。

## 运行与 checkpoint

ALIGNN 原头示例见 [native_bandgap.yaml](../configs/native_bandgap.yaml)；MACE force-only
示例见 [native_mace_force_only.yaml](../configs/native_mace_force_only.yaml)。在 Guqq2 上通过 Slurm：

```bash
sbatch scripts/ugnn.slurm train configs/native_bandgap.yaml --output runs/native-bandgap
sbatch scripts/ugnn.slurm train configs/native_mace_force_only.yaml --output runs/native-mace
```

先准备对应依赖、已登记官方权重和实际数据文件。MACE 示例的数据路径需改成自己的模拟数据。
原头可以用其他来源的同任务真实标签微调，但应自行判断标签定义和理论方法是否适合迁移。

完整续训要求 head_mode 不变。切换模式须显式用 `--warm-start-components backbone`：
只加载原主干的参数和缓冲区，保留目标的头初始化，重建优化器。不能把原头混入主干迁移。
同模式原头的复用仍须通过完整任务、实现、状态与归一化语义检查。
原头不重新挂载，不改变原模型状态路径；优化器按原模块路径分组，每个参数只出现一次。

验证范围、三环境测试和六个官方模型的实际结果见 [验收记录](agents/native-heads.md)。
