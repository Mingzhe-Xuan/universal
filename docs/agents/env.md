# 环境记录

## 2026-11-02 实现环境计划

- 本地：Python F:/Anaconda/python.exe；现有 torch 2.11.0、e3nn 0.4.4、mace-torch 0.3.16、
  numpy 1.26.4、pytest 9.0.2、ASE 3.26.0。用于编辑/静态及极小解析单元检查，不做训练推理矩阵。
- Guqq2：Python 3.10.12；待建立 /home/xmz/.venvs/universal，使用 python3 -m venv，
  不修改其他项目环境。安装前后记录版本。CPU/GPU wheel 选择以已有环境与存储诊断为准。
- 数据/权重缓存放 /home/xmz/universal/data 与模型目录，运行结果 runs/，均 Git ignored。
- 安装/下载显式使用已健康检查的登录节点 SOCKS 代理；计算作业不假设该回环代理可用。
- 所有训练/推理和实际评测用 Slurm，当前尚未配置/验收环境。

## 2026-11-02 14:49:31 +08:00：服务器环境建立前记录

- 服务器系统 Python 3.10.12 没有 torch/e3nn/MACE 等包，也未发现已检查路径下可复用 venv。
- 创建独立 /home/xmz/.venvs/universal。10 结构验收先用 torch 2.6.0 CPU wheel，避免 30 GiB 余量中引入完整 CUDA 依赖；计算仍提交 Slurm CPU 作业。
- curl 显式 SOCKS 引导 PySocks 后由该 venv pip 经代理下载 wheel；only-binary 禁止登录节点源码编译。依赖实际解析/安装版本待回填，不预先宣称成功。


- 2026-11-02 14:54:14 +08:00：系统 Python 缺 ensurepip，标准 venv 建立失败；使用 python3 -m venv --without-pip，在专用 venv site-packages 解包官方 pip/PySocks wheel 引导，不安装系统包或修改其他环境。

## 2026-11-02 15:18:20 +0800：依赖隔离与离线安装方案

- 任务 venv 已引导 pip 25.3/PySocks 1.7.1，Torch 远程下载两次因代理断开失败，未安装成功。
- 本地下载目标 cp310/Linux wheel；核心/NequIP 环境固定 torch 2.6.0+cpu、e3nn 0.5.8、NequIP 0.14.0（要求 e3nn>=0.5.6,<0.6）。MACE 0.3.16 需 e3nn==0.4.4，另建 /home/xmz/.venvs/universal-mace，不混装。
- 本地 wheelhouse 与服务器缓存只放 ignored 目录，采用 scp 资源传输；实际安装版本在完成后回填。
