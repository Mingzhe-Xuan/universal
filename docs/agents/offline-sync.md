# 离线 Git 同步

2026-11-03，用户明确批准“允许离线 Git 同步”：当服务器代理无法访问 GitHub 时，允许先用
SCP 上传必要的 Git bundle，再由服务器 `git pull --ff-only` 更新源码。这是对
[AGENTS.md](../../AGENTS.md) 中 pull 前操作限制的明确例外；其他服务器计算、源码修改和数据规则继续适用。

本地先正常提交、推送，并核对 GitHub main 的精确 SHA。仅把已经发布的提交打入 bundle；
执行 `git bundle verify`，记录起点、终点、字节数和 bundle SHA256。Bundle属于忽略目录中的
传输资源，不进入普通 Git。后续更新可以继续使用同一流程，但须重新核验最新 refs 和摘要。

首个已审核传输：

- prerequisite：`656f2ab506dd670a6181861917fc8bb0088a924f`
- main：`4994468fc8ae2b3e797612fd80ef273a605664f0`
- bundle：6241 bytes
- SHA256：`6001ab6e16a6b08e40ca9b69e80b5a3c51a7d14eb529c32a9953dfa353f92887`

```bash
# 本地：先核对已发布main，再制作和验证增量bundle
git ls-remote origin refs/heads/main
git bundle create tmp/arxiv-offline-sync.bundle 656f2ab..main
git bundle verify tmp/arxiv-offline-sync.bundle
scp -O -o ClearAllForwardings=yes tmp/arxiv-offline-sync.bundle \
  Guqq2:/home/xmz/universal/models/official-install/arxiv-base-bootstrap/arxiv-offline-sync-4994468.bundle
```

普通工作连接继续使用 `ClearAllForwardings=yes`。先检查仓库存在，校验 bundle 的 SHA256、
prerequisite及ref，再执行下面的 pull；成功且 HEAD 对应预期提交后，才读取结果或提交作业：

```bash
cd /home/xmz/universal
git bundle verify models/official-install/arxiv-base-bootstrap/arxiv-offline-sync-4994468.bundle
git pull --ff-only models/official-install/arxiv-base-bootstrap/arxiv-offline-sync-4994468.bundle main
git rev-parse HEAD
```

不得把 bundle 解包后手工覆盖工作树，不改变 origin，不强制 reset/覆盖服务器已有修改；
有分叉、缺少 prerequisite 或摘要不符时停止并处理具体原因。只同步 Git 对象，不携带数据集、
权重、日志或结果文件。每次连接仍须提前记录在 [gpu.md](gpu.md)。

离线同步不需要新建互联网代理；已有任务代理断开后的残留清理仍按精确 UID/命令/启动时间
证据执行，不结束来源不明或用户仍在使用的会话。依赖或数据的本地下载、SCP资源传输继续使用
原有许可，重型校验/转换和所有模型计算仍通过 Slurm。

## 大资源的私有 HTTP 续传例外

2026-11-04，用户进一步明确批准“允许 HTTP 断点续传”。SCP资源包和单独4MiB分片均被
Vlab关闭/重置后，允许本次固定公开 wheel 资源经本机只读HTTP服务、SSH SOCKS反向代理下载。
这是对“本地大文件请使用scp”的明确例外；Git源码仍只通过上面的Git同步方式更新。

- HTTP仅监听本机 `127.0.0.1`，服务只暴露经过清单登记的公开资源路径，不开放公网端口。
- 仅维持一个专用SSH代理；普通工作连接禁用转发，不重启健康代理。
- 先通过离线gitpull门禁，再验证实际资源的端到端HEAD/Range；计算作业内必须再次验证计算节点路径。
- 下载保留 `.partial`/分片，Range续传；从官方PyPI/PyTorch摘要或已核验传输清单校验完整SHA256。
- 大文件哈希、组装/解包与后续模型测试都在Slurm中完成。资源齐备/核验完成之前不安装或宣称环境就绪。
- 共享base与模型特定环境的版本、路径、任务和结果记录在env.md；不改其他项目环境。
- 工作结束精确关闭任务HTTP服务和专用代理，核验1080释放，不结束来源不明/用户会话。
