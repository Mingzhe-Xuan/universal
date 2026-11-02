# 实现与 10-structure 验收

最终范围为六模型及主计划下游，不以少数模型/标量通过替代完成。
代码本地提交和 push，Guqq2 先 pull；训练、推理、评测与明显计算通过 Slurm。

## 模块与顺序

src/universal_gnn 按 contracts、data、backbones、adapters、properties、readouts、tasks、
workflows、engine 划分，每目录附 README；scripts 管资源/Slurm，tests 管单元/集成。
先公共类型/PBC 几何，再三类不变模型及 MACE/NequIP/Equiformer，随后响应/EFS/生成与派生流程。

## 完整验收矩阵

每类模型对应结构回归/分类、节点标量、谱、二/三/四阶响应 Jacobian、E/F/S、
固定组成生成的训练与推理；calculator、弛豫、短 MD、声子及谱学/显微流程单列资产/运行状态。
每格使用 10 个真实结构并记录标签来源/单位、结构 ID/哈希、数据角色、Git commit/依赖、
loss/参数更新、所需梯度、输出、checkpoint 重载一致性、Slurm 作业/日志。
10 结构仅是执行通路验收，不声称泛化。单元解析/合成标签不得冒充真实数据验收。
缺数据、实现或实跑项保留 pending；不以 mock、配置存在或静态检查判通过。

## 验证步骤

1. 结构/批次、完整 cutoff 周期镜像、可微几何/应变和字段/单位检查。
2. 六类真实架构的节点抽取、条件接入和表示检查。
3. 标量/节点/谱及求导响应训练和重载推理。
4. 能量/力/应力训练与有限差分、模拟接口。
5. 固定组成去噪训练和周期/晶格一致的采样。
6. 真实数据全矩阵及派生流程审计，逐格证据齐备后才完成目标。
