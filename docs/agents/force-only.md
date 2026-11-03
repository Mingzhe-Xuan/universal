# 仅力监督实现与实际验收

配置 `task.supervised_outputs: [forces]` 即可只使用真实力标签训练。仍由标量能量函数通过
F=-dE/dR得到力，再对力损失反传到能量头和GNN参数。无需能量标签或应力标签，不构造虚假零值。
原MACE/GNN模块未改，变化位于监督项校验、数据绑定、尺度统计、损失选择与续训兼容检查。

省略该字段时保持旧E/F/S默认值；可选total_energy/forces/stress的任意非空无重复子集。
未选项的绑定和损失均跳过，选中项缺标签仍报错。监督集合改变时不能冒充完整优化器续训。
报告明确记录supervised_outputs；推理仍可计算E/F/S。仅力监督不能确定能量常数和元素参考能，
应力也没有直接监督。配置见 [mace_force_only.yaml](../../configs/mace_force_only.yaml)。

## Slurm真实数据验收

源码c0b31c2，Slurm764使用原官方MACE-MP small.model，对既有十个真实力场结构仅保留forces。
原权重SHA256为2ddb079cee0e131eaaf6912ba581b394551ead283e95c99cfe78c605d10b5736，
原模型类为mace.modules.models.ScaleShiftMACE，参数/buffer严格加载覆盖率均为1。
训练4轮、batch_size=5、float32、learning_rate=1e-4、单CPU线程：

- 归一化力训练损失1.1310369051 → 0.5999797674；这是训练损失，不是测试集力MAE。
- 原MACE主干参数变化范数0.4007481968，存在非零主干梯度。
- 先训练1轮再完整恢复到4轮，与连续训练的模型参数通过float32容差对照。
- 保存与重载检查通过，JSONL推理完成十个结构，每个原子都有三分量力。
- 本地独立审计确认训练文件只有forces标签；所有ID、原子、坐标、晶胞、PBC和力值与原数据
  逐元素一致，没有合成能量/应力标签或新DFT计算。

Slurm762 core与763 MACE环境完整回归均为80 passed。新增检查覆盖监督项配置拒绝、默认EFS与
旧checkpoint等价性、仅力数据绑定与损失、坐标/参数混合梯度、能量偏移无梯度、mini-batch、
精确续训及重载推理；原EFS数值/坐标梯度检查继续通过。

本地 [原始证据归档](../../results/force-only-764/evidence.tar.gz) 为37120字节、14个文件，SHA256：
`9ff65e7bf5d5144c5c51eddedf2a1ff7881fb3ff99fedcd6c12415b47139a782`。
[独立审计](../../results/force-only-764/local-audit.json) 核对全部文件hash、原始/训练几何与力标签、
训练监督项、续训轮数、推理条数及两环境回归日志。checkpoint保留于服务器
`runs/mace-real-force-only-764/{continuous,first,resumed}`，数据/权重/日志不进入Git。

这验证选定官方MACE与真实小样本的force-only执行通路，不代表已在用户未提供的模拟数据集上
训练，也不代表泛化精度或无监督能量/应力已得到校准。
