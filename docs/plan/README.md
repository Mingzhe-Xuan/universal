# 研究与工具设计计划

本目录保存研究问题、论文定位、实验设计和工具架构。文档中的假设和候选方案不代表已获得实验结果或完成实现；实施进度及检查记录见 [agents 记录](../agents/state.md)。

| 文档 | 内容 | 状态 |
| --- | --- | --- |
| [AFM 下游迁移研究](afm_transferability.md) | 比较物理目标专用 AFM、多任务 AFM 和多个专用 AFM 融合的迁移能力 | 研究定位与实验框架，待模型和数据审计 |
| [arXiv v1 全量实验与存储预算](arxiv_v1_experiments.md) | 四骨干×六任务×预训练/从头的48格矩阵；三seed144配置、资源预算与评测协议 | 全量数据及144配置准备完成；环境、原包scratch与数值预检待验收，正式训练0/144 |
| [不变/等变 GNN 下游任务工具箱](gnn_task_toolkit.md) | 首批 MACE、NequIP、Equiformer、ALIGNN、CGCNN、MEGNet；性质库响应默认求导，直接读出显式可选，兼容原生/几何基底 | 覆盖 ALIGNN 2.0 任务，不要求逐实现对齐；尚未实现 |
| [统一特征适配层](unified_feature_adapter.md) | 统一读出 API；区分 ALIGNN 风格不变轻量路线与共同等变 profile 路线，响应默认求导 | 详细设计，尚未实现或实测 |
| [性质预测组件解耦需求](prediction_decoupling_requirements.md) | 原生节点特征直连可替换readout；自动/显式feature_dim、显式处理、冻结及严格续训/暖启动 | A～E已实施；两个环境各118项回归及11组官方真实链通过，见验收记录 |

阅读研究计划时，应分别查看研究问题、相关工作边界、实验对照及结论所需证据；新增文档在此索引，具体实验结果保存在后续约定的结果目录中。
