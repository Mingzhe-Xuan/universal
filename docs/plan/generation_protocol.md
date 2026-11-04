# 生成训练与独立质量评测协议

状态：2026-11-04实施中。纯std协议已发布为4859cc9，Slurm860实际通过9项测试，
并仅从Perov-5全部11,356条训练结构拟合出14.129232628696206 Å³/原子的初始体积。
下述训练器、独立质量评测及Torch/Pymatgen测试已实现，**尚未完成数值验收**。
它们不能作为正式生成结果。完整目标仍为[四模型六任务、两种初始化和三seed](arxiv_v1_experiments.md)。

## 模块边界

- [纯协议](../../src/universal_gnn/engine/generative/protocol.py)：训练seed、结构ID、epoch决定训练扰动，
  各评测phase/draw独立且固定；选择无放回测试条件，计算训练专属体积先验与经验一维W1。
- [训练入口](../../src/universal_gnn/engine/generation.py)：新训练默认`per_epoch_structure_v2`，
  保留原版本显式完整续训；按完整验证分区的固定噪声loss选best，只在结束后对完整test分区计算去噪指标。
  best/last沿用既有候选文件、哈希绑定和原子恢复协议。测试loss不参与选模。
- [独立去噪评分](../../src/universal_gnn/engine/generative/evaluation.py)：流式保存完整测试分区的
  每结构预测/噪声目标，记录其phase、计数、标量元素MAE/RMSE和best选择来源。
  去噪指标不是生成结构质量。
- [结构质量](../../src/universal_gnn/engine/generative/quality.py)：从last的验证历史定位并核验best，
  独立生成、流式保存样本并评分。不自动对完整训练集逐结构采样。

## 噪声、晶胞先验和续训

v2按稳定ID产生噪声，改变epoch会改变训练噪声；batch大小、shuffle顺序及续训段边界不改变某epoch的噪声。
验证与测试各有独立固定噪声命名空间。旧`per_structure_v1`仍保留原先`seed+1+index`的固定扰动，
但不能用于本轮正式矩阵；完整续训不能静默切换目标，未版本化旧目标需要显式weights-only初始化。
完整续训可继承省略的训练先验及其推导体积，仍重新核验训练指纹；采样步数、inner_steps、seed等显式设置不得改变。

默认用训练结构的`log(|det(cell)|/N)`均值定义采样初始体积，不读取留出集几何来拟合先验。
训练器将实际先验、训练数据fingerprint和计数写入resolved config/checkpoint。
独立准备器的raw JSONL先验使用原始float精度和分区身份指纹；训练器先验使用实际输入精度和训练几何指纹，
两类指纹有不同定义，不能混用。不同骨干/初始化必须使用相同数据与精度。
显式配置固定体积可用于一般调用，来源会被记录；本轮质量入口要求`train_fit`来源。

## 固定条件、采样及指标

默认采样1,000个结构：固定seed选择200个不同测试条件，每条件独立5次draw。
条件选择无放回，draw有独立seed。这样可同时观察相同组成/数量下的多样性。
两种初始化与所有骨干共用条件ID、draw和采样seed；采样步数/inner_steps必须在训练配置中预先明确。
条件仅含组成与原子数：传给sampler之前清除原始坐标、晶胞、图、标签和含原几何的metadata，
用训练先验构造占位晶胞。真实测试结构仅在生成完成后用于质量评分。

当前质量入口逐个样本采样（batch=1），此值和采样总数分别记录。OOM直接终止该次评测，
不会计为“无效科学样本”，也不减cutoff或裁剪结构。非有限采样的FloatingPointError则记录为无效样本。
默认1,000为本轮最低数量，低于它的自定义小测试明确标记`meets_v1_sample_count=false`。
完整训练分区覆盖另有独立标记，不能由采样数推断。

| 指标 | 明确定义 |
|---|---|
| 几何有效率 | 有限位置/晶胞、正体积、3D PBC、分数坐标在单胞范围内，含周期镜像的最小距离≥0.5 Å |
| 唯一性 | 有效样本中按StructureMatcher去重的比例，并记录组成组及重复组成样本数 |
| 新颖性 | 有效样本中与训练结构均不匹配的比例；另报训练已见组成内的新颖性，披露未见组成自动新颖 |
| 配对匹配率 | 与分配的测试参考结构匹配的样本数/全部采样数，另报有效样本分母版本 |
| 匹配RMS | 匹配样本的归一化RMS，长度按(V/N)^(1/3)归一化，不写成Å |
| 结构分布差异 | 有效生成结构相对全部选定参考结构的体积/原子、密度一维W1；单位分别Å³/atom及g/cm³ |

StructureMatcher固定`ltol=.3, stol=.5, angle_tol=10°`，`primitive_cell=false, scale=true,
attempt_supercell=false`，ElementComparator，双向匹配。上述几何/结构有效性不代表化学有效性或热力学稳定性。
本轮不调用新DFT，也不作能量/稳定性结论。

## 待数值验收后使用

生成配置使用标准dataset JSONL与split manifest，`dataset.partition: train`，`task.kind: generation`，
`generation_corruption: per_epoch_structure_v2`，`evaluation`仅配置patience/min_delta。
不设置`prediction`或`optimization`；`validate_sampling`为false。
`task.sampling`明确指定steps和inner_steps，默认体积由训练先验补入。

训练完成后，独立提交：

```bash
UGNN_GENERATION_CHECKPOINT=runs/<run>/checkpoint.pt \
UGNN_GENERATION_OUTPUT=results/generation/<run>/quality \
UGNN_VENV=/home/xmz/.venvs/universal-official \
sbatch --nodelist=node42 scripts/evaluate_generation.slurm
```

CGCNN/ALIGNN使用official环境，MACE用universal-mace，NequIP用universal。
输出目录必须全新，保存`samples.jsonl`与最终`metrics.json`；未写出完整metrics的目录不能标记评测完成。
Torch恢复及provider安装后先运行[数值回归](../../scripts/validate_generation_protocol.slurm)，
再逐官方骨干进行真实CUDA训练/导数、最坏图与采样容量预检，才能启动正式矩阵。
