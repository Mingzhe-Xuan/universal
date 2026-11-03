# 其他官方骨干的力场验收

2026-11-03。ALIGNN、CGCNN、MEGNet、NequIP、Equiformer均通过新式能量求导力场验收；
CGCNN/Equiformer全参训练要求显式eval主干，同时保留参数梯度。
测试使用各自已登记的原发布权重，原图规则、网络层及依赖版本保持。
这是 `prediction.version: 1` 的执行与导数验证，没有独立测试集或实用力场精度结论。

验证范围

共用10个已有DFPT真实结构，只保留原force标签，坐标/晶格/力按声明float32转换；没有伪造E/S标签或新增DFT。
数据源及哈希为已有 `data/acceptance/manifest.json` 中forcefield任务；原记录ID、单位、来源保留。
每模型测试冻结主干及主干参数可训练两种方式，`node_mlp([32], silu) → sum → E/F/S`，4 epochs、batch5、单CPU。
所有训练、推理、回归与数值诊断通过Slurm；NequIP使用core环境，Equiformer使用既有独立PyG2.0.4环境，其余使用official环境。

每种方式检查：原生10结构参考对照；扰动探针的6个力分量和3个应变分量有限差分；
有限且非零的混合参数梯度；总力、单结构/混合batch一致性；冻结参数和持久buffer不变；
原force-only标签训练、损失下降、主干/新头更新、严格重载及10条推理。
之后用完全普通的生产构造器，再验证4→5轮完整续训和全参数冻结后的力/应力推理，未使用候选能力覆盖。

| 主干 / 原生F | 冻结：初始→最终损失 | 参数可训练：初始→最终损失 | 生效模式 | 候选作业 / 普通入口作业 |
| --- | --- | --- | --- | --- |
| ALIGNN / 512 | 49.26022 → 2.46066 | 49.26022 → 4.76315 | 默认train | 787 / 791 |
| CGCNN / 64 | 122.06275 → 9.84047 | 122.06275 → 1.69569 | 显式backbone_eval | 785 / 792 |
| MEGNet / 64 | 17.46811 → 2.03364 | 17.46811 → 0.88539 | 默认train | 775任务2（778） / 793 |
| NequIP / 128 | 547.65725 → 10.63171 | 547.65725 → 417.74509 | 默认train | 775任务3（779） / 794 |
| Equiformer / 512 | 1419835.82051 → 396713.26068 | 1419835.82051 → 513790.10544 | 显式backbone_eval | 786 / 795 |

上述为按训练标签尺度归一化的训练MSE，不能比较不同骨干的泛化能力或把这些短训练结果直接当成已收敛力场。
所有五个模型的原生节点特征及原任务预测最大差异均为0，NequIP原生力差异也为0。
冻结主干的参数差分为0，训练器及验收同时检查其持久buffer；参数可训练模式下主干和新头均实际更新。
788/789/790在core、MACE、Equiformer三环境各 **126 passed**，源码df94bc8；
能力开放后791～795用cfeb989完成普通生产入口的10组续训/推理，均通过。

实际问题与处理

1. CGCNN默认训练模式的BN使不同结构相互影响：780中batch/单结构能量差0.3174、力差2.0382，应力差2.8045。
   新式力场全参模式要求显式 `optimization.backbone_eval: true`；BN统计固定，参数继续训练。
   修正后这些差异降到2.4e-7、2.5e-7、3.6e-6量级，原BN层与预训练权重均保留。
2. Equiformer原OCP构图将带应变梯度的晶胞重复次数传给arange，775任务4失败。
   适配器先在no_grad内调用**原radius_graph_pbc**只计算离散拓扑，再用原模型支持的预计算拓扑入口，
   让原距离/边向量计算继续消费live位置和晶胞。上游源码字节、邻居规则及模型层没有修改，独立原生对照仍为0误差。
3. Equiformer原检查点的alpha_drop=0.2：781中全参训练模式的同batch重复力差约0.029、应力差0.070。
   同样要求显式backbone_eval，关闭随机训练行为但保留所有主干参数的梯度；786确定性batch比较通过。
   原OC20检查点的元素、周期构图及训练域限制仍保留，不据此声称任意Equiformer版本/权重可互换。
4. ALIGNN在h=.002时的应力差分误差1.1326，不能通过原容差。782固定模型/固定探针扫h：
   .001→.3028，.0005→.0766，.0002→.01025，.0001→.00607，符合步长收敛。
   787采用h=.0002通过；其余模型h=.002。rtol=.02、atol=.002均未放宽。
   这些是固定邻居域的局部导数检查，不改变任何模型的原截断平滑性。
5. CGCNN参考CIFData必须有一个不参与预测的标量标签槽；首次775任务1因此缺property而失败。
   参考适配器改为取已有真实force的首分量填入该槽，训练任务仍只有原forces，未制造标签。
6. 当前发布ALIGNN特征实际512维；先前带隙示例误写256的一致性断言已修正。
   782在Slurm中直接构造修正后的配置，确认首层in_features=512。

能力与兼容

五个provider只有在候选验证通过后才将positions/strain/mixed声明为true。
临时声明只存在于候选验收进程的新实例；791～795普通入口未使用该覆盖，且确认生产实例无候选属性。
新增backbone_eval仅控制模式，不关闭参数或输入autograd；它属于完整续训策略，变更需显式暖启动。
absent/false保留历史策略规范化表示。

仅FeatureSpec.gradients由未验证false提升为已验证true时，组件重建允许记录性的元数据升级；
层、state键/shape、irreps、基底、策略和参数组仍严格核对，能力降级不被此例外放行。
792额外回放真实旧771 CGCNN带隙checkpoint，预测最大差异 **0**，并记录6条能力升级路径。
这是元数据兼容，不是把历史32维路径改造成原生直连。

用法与复验

已有 [force-only配置](../../configs/prediction_force_only.yaml) 可通过模型选择复用到这五个骨干；
替换数据时仍需满足所选原模型的元素、周期性和输入约束。
NequIP/Equiformer需使用 [环境记录](env.md) 中各自的解释器。
训练CGCNN或Equiformer主干参数时，在配置中显式写：

```yaml
optimization:
  train_backbone: true
  train_readout: true
  backbone_eval: true
```

冻结主干仅需train_backbone=false，默认已经eval。完整命令见 [组件用法](../prediction_components.md)。
重新运行候选验证可执行 `sbatch scripts/validate_other_forcefields.slurm`；
该入口固定ALIGNN已收敛的差分步长，保留所有数值容差。
普通入口验证脚本为 [validate_forcefield_release.py](../../scripts/validate_forcefield_release.py)，
它读取已通过的候选目录，恢复优化器再训练一轮并推理。

证据

服务器保存775初次失败/通过、780～787受影响项及步长诊断、788～790完整回归、791～795普通入口目录，未覆盖旧结果。
本地忽略目录 `results/other-forcefields/evidence` 保存158份配置、report、validation、JSONL、原数据及日志，
逐文件哈希见final-manifest.json。最终包439819字节，
SHA256 `de88b3e93ca3eb769414ddb68bd88827fecdcb3afdec18fab55ec425d5947e08`。
独立审计为 `results/other-forcefields/audit.json`，核对文件哈希、全部真实ID/几何/force投影、模式、更新、回放及续训结果。
权重、checkpoint及批量生成物均保持Git忽略。
