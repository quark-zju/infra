# pyinfra 两阶段语义与单机 DAG 并行分析

本文基于仓库中的 OpenCode Ansible role、实验性 pyinfra 3.10.0 移植，以及
`~/src/scratch/config-graph` POC。结论针对当前版本和单台 `opi`；性能数字若非明确标为实测，均为结构性估算。

## 结论

pyinfra 的两阶段模型很适合“读取初始状态，生成收敛命令，统一执行”，也是它在幂等运行中显著快于 Ansible 的主要原因。但需要“修改后重新观察，再根据结果决定后续操作”的逻辑时，普通 deploy 写法会变得不自然：可以退回 shell guard、`python.call`、嵌套即时 operation 或拆成多次 deploy，却会牺牲一部分计划可见性、changed/dry-run 精度或全局优化能力。

当前 OpenCode role 确实有这种需求。因此实验移植适合衡量已收敛性能，还不能视为完整的 first-install 替代。

pyinfra 3.10.0 原生并行主要面向多个 host。单 host 上 operation 仍线性执行；`--parallel` 不会让同一主机上的独立 operation 并发。内部虽然保存 command generator，但它不是稳定的“shell 命令列表”接口，而且产物还可能是上传、下载和 Python callback。直接提取后用多个 SSH 并发执行，会绕过 pyinfra 的 connector 参数、文件传输、重试、结果和 changed 语义。因此暂不实现这种并行原型；应先用阶段和逐 operation 计时确认潜在收益，再决定是否值得写 executor adapter。

## 两阶段模型的准确边界

典型执行过程是：连接主机，在 Prepare 阶段运行 deploy Python、收集显式 facts 并登记 operations，然后在 Execute 阶段依次调用 operation 的 command generator 并执行命令。

这里有一个细节：command generator 是惰性的。使用 `-y` 时 pyinfra 跳过 change detection，许多 operation 内部的检查直到 Execute 才发生；不使用 `-y` 时，为预测 changes，generator 可能在 Prepare 阶段先被迭代。无论哪种方式，deploy 顶层直接调用的 `host.get_fact(...)` 都发生在 Prepare，而且 facts 有缓存。因此不能把“所有检查一定先执行”或“所有检查一定按 operation 顺序执行”作为用户代码的稳定语义。

下面的初始快照判断很自然：

```python
installed = host.get_fact(File, path="/usr/bin/foo")
if not installed:
    files.download(...)
    files.unarchive(...)
```

而下面的链条存在两阶段问题：

```text
安装 foo -> 运行新安装的 foo 探测 -> 根据输出声明不同后续资源
```

可选做法及代价：

| 做法 | 能力 | 代价 |
|---|---|---|
| 一个 `server.shell` 内完成安装、探测和分支 | 控制流完整、round trip 少 | 内部节点、changed 和 dry-run 对 pyinfra 不透明 |
| 预先声明所有分支，命令内加 guard | 适合已知的有限分支 | 每条命令自行定义跳过、错误和 changed |
| `python.call` 中调用 `host.run_shell_command` | 可执行任意运行时 Python 控制流 | 退回 imperative 黑盒，不能参与全局计划优化 |
| Execute 阶段调用嵌套 operation | 能继续借用 operation utility | 即时顺序执行，仍不能回到全局图中重新调度 |
| 拆成多次 deploy | 每阶段重新观察，语义清楚 | 增加启动/SSH 成本，需要外部 orchestration |

所以问题不是最终“做不到”，而是无法同时保留：修改后观察、动态扩图、普通 operation 语义、准确 dry-run/changed，以及执行前全局优化。这与 config-graph 文档中的运行时扩图问题相同。

## 当前 OpenCode role 的具体实例

原 Ansible role 包含以下执行后依赖：

- 检查 pnpm 版本，必要时安装，再寻找实际 pnpm 路径。
- 安装 DSH 后根据 `deepseek_harness_install.changed` 清除 patch marker，再查找并修改新安装的 JS。
- 分别运行插件检查，根据每个返回码只安装缺失插件。
- 创建用户后读取 passwd/UID，再用 UID 渲染 systemd unit。
- 写环境文件或 unit 后，仅在内容改变时触发 reload/restart handler。
- Kimi 版本检查和 Git remote 检查允许命令失败，再根据 `rc/stdout` 分支。

实验移植通过初始状态和命令内 guard 绕开了部分问题，但有两个明确缺口：

1. `server.user(...)` 后顶层读取 `host.get_fact(Users)[USER]`。在已存在用户的 `opi` 上正常；在空白主机上 fact 先于创建用户，可能找不到 UID。
2. unit 可以安装并 daemon-reload，但没有 Ansible handler 那样的 change-aware restart，所以 unit 内容变化时不能精确重启对应服务。

生产化时宜把 DSH 安装/patch、插件收敛等过程封装成粗粒度 provider；少数本质过程式的迁移保留 callback escape hatch。用户 UID 可显式配置，或把创建身份与消费 UID 拆阶段。

## 单机并行的收益模型

已有已收敛实测：Ansible 中位数 142.55 秒；当前 pyinfra 中位数 21.64 秒，最好 19.34 秒。pyinfra 已经通过批处理和减少 module/SSH round trip 获得主要收益，DAG 并行属于第二层优化。

可并行的主要分支包括 Node、Neovim、Codex 下载，DSH plugins Git 网络访问，网络/Rust probes，以及大量独立文件检查。必须排序或加锁的部分包括 APT，npm/pnpm 全局状态，DSH 安装→插件→patch，user/group→所属文件，repo→leash build，以及 unit→daemon reload→restart。

在没有逐 operation trace 前，已收敛运行的合理估算是：

| 方案 | 估计耗时 | 相对当前 pyinfra |
|---|---:|---:|
| 当前 pyinfra | 19–22 秒 | 1.0x |
| 保守的 4-worker DAG | 14–18 秒 | 1.2–1.5x |
| 完善连接复用的异步 executor | 10–14 秒 | 1.5–2.2x |
| 极理想下界 | 约 8–10 秒 | 约 2–2.7x |

第二次 pyinfra 测量曾达到 49.64 秒，疑似 Git/网络波动。并行只能把该请求与其他工作重叠；若它仍是最长关键路径，不能消除其尾延迟。first-install 因下载、clone、编译工作更多，可能有 1.5–3x 收益，但也更受带宽、CPU、磁盘和 package scripts 隐式副作用限制。

### 阶段计时实测

使用下述 `profile_stages.py` 在同一台已收敛 `opi` 上连续测量三轮；仍使用 `-y`，与原 benchmark 的 pyinfra 命令一致：

| 轮次 | Setup (s) | Connect (s) | Prepare (s) | Execute (s) | Total (s) |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.059 | 0.241 | 4.414 | 15.489 | 20.208 |
| 2 | 0.058 | 0.317 | 4.776 | 15.374 | 20.530 |
| 3 | 0.048 | 0.203 | 5.090 | 13.639 | 18.984 |
| 中位数 | **0.058** | **0.241** | **4.776** | **15.374** | **20.208** |

Execute 约占中位总时间的 76%，说明单机并行存在值得观察的空间，但不能把这 15.37 秒全部消除。仅用 Amdahl 式上界看：若整个 Execute 能理想加速 2 倍，总时间约为 12.5 秒（总加速 1.6x）；理想加速 4 倍约为 8.7 秒（2.3x）。真实 Execute 含 APT、systemd 和 DSH/Git 等串行关键路径，所以前表的 14–18 秒保守区间仍较可信。要进一步收紧估算，应加入逐 operation timing，而不是立刻改执行器。

## 为什么暂不直接提取命令并行 SSH

pyinfra 的 `StateOperationHostData` 保存 `command_generator`，执行器也能取得 `PyinfraCommand`，但这是内部执行表示，不等价于字符串数组：

- `StringCommand` 带 `_sudo`、环境、cwd、shell、timeout 等 connector 参数。
- 文件 operation 可能生成 upload/download 命令，而非远端 shell。
- `python.call` 生成 `FunctionCommand`，必须在 controller 内执行。
- operation 可能在 generator 被迭代时读取 fact；fact cache 与前序写入有关。
- `OperationMeta` 的 success/changed/output 在原执行器中完成回填。
- 当前 `State.get_op_order()` 将同一 host 的声明顺序构造成完整前驱链，并没有可供手工标注的单机 DAG 边。

因此“拿到 shell 后并发 ssh”实际上会开始重写半个 executor，而不是一个小实验。更安全的后续原型应在 pyinfra executor 层运行原生 `PyinfraCommand`，并显式加入依赖边和资源锁；不能只并发字符串。

## pyinfra 资产可重用程度

若 config-graph 负责 DAG 和 executor，而 pyinfra 继续承担部分 provider 工作：配置常量、URL、模板和静态文件几乎全部可复用；operation 参数和业务意图约 60–80% 可机械迁移。顶层 `host.get_fact` 条件必须改为 probe/ref/guard；pyinfra operation 与其全局 State/Host/fact cache 耦合，需要 adapter。

整体估计是 65–80% 的语义和配置资产可复用，但逐行不改的 Python 代码约 25–40%，调度/依赖代码基本不能复用。可行的长期边界是 config-graph 管 task/ref/DAG/锁，provider adapter 借用 pyinfra 的命令生成或 connector 能力；不宜把 pyinfra operation 当成完全独立、稳定的 provider API。

## 下一步判定标准

本目录的 `profile_stages.py` 通过包装 pyinfra 的 `StateStage` 记录 Setup、Connect、Prepare、Execute 的 wall time，不改变 operation 行为。运行方式：

```sh
python3 experiments/pyinfra-opencode/profile_stages.py \
  experiments/pyinfra-opencode/inventory.py \
  experiments/pyinfra-opencode/deploy.py --limit opi -y
```

三轮阶段时间已经记录在上文。下一步若继续，应先用 operation callbacks 记录 Execute 内各 operation 的关键路径候选。只有当独立慢 operation 足够多时，才值得实现带手工依赖与资源锁的 executor adapter；如果主要时间集中在单个网络关键路径，应优先修正 Git 的空闲路径。当前 pyinfra 没有安全、公开的单 host 手工 DAG 接口，因此本次按约定停在分析和计时，不改执行器。
