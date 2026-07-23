# 代码管理规范 (AGENTS.md)

本文件约定本仓库的分支模型、发布流程与受保护资产。AI 编码助手与本人在改动仓库前应遵守。

## 1. 分支模型：简化 GitFlow

| 分支 | 角色 | 保护规则 |
|------|------|----------|
| `master` | 生产分支 | **受保护**：禁止直接 `commit`/`push`，只接受 `dev` 的 `merge --no-ff` 与发布 `tag`。`scripts/deploy.sh` 拉取 `origin/master` 部署。 |
| `dev` | 集成分支 | 日常合并目标。功能稳定后合入 `master`。 |
| `feature/*` | 功能分支 | 从 `dev` 切出，开发完 `merge` 回 `dev`。大重构可用 `git worktree` 隔离。 |

发布流程：`dev` 稳定 → `git merge --no-ff dev master` → 打 `vXX.XX` tag → 触发部署。

## 2. 废弃分支（保留、禁止写入）

- `worktree-audio-service-refactor`：**已废弃**。其顶端 `137a2fa` 已是 `master` 的祖先，全部内容（音频 service 重构、请求日志中间件等）已并入 `master`，该分支落后 `master` 31 个提交，无任何 `master` 没有的内容。**不要再向其写入新代码**，仅保留作历史参考。如需新功能，从 `dev` 切 `feature/*`。

## 3. 受保护资产（禁止删除 / 禁止 `git clean -fdX`）

以下路径被 `.gitignore` 忽略，但**磁盘上真实存在且有价值**，清理工作区时严禁使用 `git clean -fdX`（会误删）：

- `static/uploads/` —— 用户上传文件
- `*.db`、`backend/instance/`、`instance/` —— 数据库
- `backend/.env` —— 密钥/配置
- `backend/sensevoice/` —— 模型权重
- `backend/tests/` —— 测试代码
- `frontend-app/` —— Capacitor 构建产物（可从主 `frontend/` 重建，仅用 `.gitignore` 忽略，**非必要不手动删除**）

> 清理临时文件时，必须**精确删除**明确无用的诊断/探针文件（如 `carousel_*`、`scripts/_*`、`*_diag*.py`、`diag_*`、`plan*`、`sec_test.txt`），不得波及上表资产。

## 4. SSH 推送通道

本机有多把 SSH key，GitHub 实际信任的是默认 key `id_ed25519`（其公钥已加入 GitHub 账户 `Sssuduo`）。需用显式锁定避免 key 协商被干扰：

```
git config --global core.sshCommand "ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
```

> 注意：`id_ed25519_github` 命名虽意为 GitHub，但其公钥**未**被 GitHub 信任，勿用。Windows 上绝对路径的反斜杠会被 git config 吞掉，务必用 `~/.ssh/id_ed25519`。

## 5. 部署保护约定

`scripts/deploy.sh` 含 `git reset --hard` 与 `rsync --delete`，**不得波及** `static/data`、`static/uploads`：

- 针对地图 404 的修复 `--exclude='data'` 必须随代码入库（经 review），否则下次部署会被 `git reset --hard origin/master` 还原而复发。
- 任何对 `deploy.sh` 的修改都需同步进入 `master`（经 `dev` 合并），不能只改生产磁盘。
- nginx `/static/uploads/` 别名属"带外修改"，应纳入仓库管理，避免服务器重置即丢失。

## 6. 分布式 Git Hooks（强制执行流程）

仓库内置 hooks 于 `.githooks/`，随 git 分发，让任何 clone 并启用的 agent / 协作者都自动遵守上述流程。

启用（clone 后一次性）：

```bash
bash scripts/setup-hooks.sh
```

该脚本将 `core.hooksPath` 指向仓库内 `.githooks/`。

包含钩子：

- `pre-commit`：
  - 禁止在 `master` 直接提交（`master` 受保护，只接受 `dev` 的 `--no-ff` merge）。
  - 禁止向废弃分支 `worktree-*` 提交。
  - 安全网：阻止 `backend/.env`、`*.db`、`backend/sensevoice/`、`instance/` 等受保护/敏感文件被误暂存入库。
- `pre-push`：
  - 禁止直接 `push` 到 `master`（顶端必须是来自 `dev` 的 merge commit）。
  - 禁止推送废弃分支 `worktree-*` 到远程。

紧急绕过（需自知风险）：

```bash
ALLOW_PROTECTED_COMMIT=1 git commit ...   # 绕过 pre-commit
ALLOW_PROTECTED_PUSH=1   git push ...      # 绕过 pre-push
```

> 部署脚本 `scripts/deploy.sh` 另含受保护资产断言（§5）：同步 `dist` 前为 `static/data` 兜底备份，同步后校验 `static/data`、`static/uploads` 未被 `rsync --delete` 误删，缺失则自动从兜底备份恢复。

## 7. ASR 本地服务看门狗（运行时 hook）

`scripts/asr_watchdog.ps1` 是 ASR 语音识别链路的**运行时看门狗**，与上面 git 流程无关，但同样需随仓库分发、供其他 agent 启用。

行为：当 agent 在线时，每隔 30 分钟检查一次 ASR 本地服务（`localhost:5002/health`）与 SSH 反代隧道；若本地服务断线则重启 `asr_api.py`，若隧道断线则重建 `root@123.56.9.243:15002` 反向隧道。检测到断线会**立即**重建（无需再等一个周期）。

关键参数：

```powershell
-IntervalMinutes <int>   # 巡检周期，默认 30
-NoLoop                  # 只检查一次后退出（适合 git hook / 手动触发）
-RequireAgentOnline      # 仅当 scripts/agent_online.flag 存在时才工作（agent 离线则空转）
```

说明：

- **agent 在线判定**：默认进程在跑即视为在线；加 `-RequireAgentOnline` 后，仅在 `scripts/agent_online.flag` 文件存在时才执行检查（该 flag 由 agent/IDE 会话启动/退出时创建/删除）。
- 看门狗每轮写入 `scripts/asr_watchdog.online` 心跳时间戳，供外部判断其在线状态。
- 路径全部由 `$PSScriptRoot` 运行时派生（仓库根含中文），源码不含中文字面量，规避 Windows GBK/ANSI 误解析。
- 它**取代**原 `asr_monitor.ps1` 的 30 秒轮询；两者不可同时运行（会争抢同一远端端口 15002）。

启用（登录/解锁自动启动，需管理员 PowerShell）：

```powershell
# 重新注册计划任务指向新看门狗（覆盖旧 asr_monitor 任务）
Register-ScheduledTask -Xml (Get-Content "h:\项目1\scripts\asr_task.xml" | Out-String) -TaskName "ASR Tunnel Monitor" -Force
# 手动单次检查（不常驻）
powershell -ExecutionPolicy Bypass -File "h:\项目1\scripts\asr_watchdog.ps1" -NoLoop
```

> `scripts/asr_task.xml` 的 `Arguments` 已指向 `asr_watchdog.ps1`。若旧 `asr_monitor.ps1` 仍在运行，请先 `Unregister-ScheduledTask -TaskName "ASR Tunnel Monitor" -Confirm:$false` 再重新注册，避免双管理。

### 7.1 转写期细粒度监控（`asr_transcribe_monitor.ps1` + `boot_transcribe.ps1`）

看门狗（30min 周期）只判断 ssh 进程是否退出，**检测不到隧道僵死**（ssh 进程活着但远端 `15002` 实际不通），也无法收紧转写期的资源。为此新增两个脚本，专供**长时间批量转写**（如数百切片）期间使用，与看门狗形成「粗兜底 + 细粒度自愈」双保险：

- `scripts/boot_transcribe.ps1`：一键启动脚本（ASCII 文件名、用 `$PSScriptRoot` 推导 `backend` 目录，命令行本身不含 `asr_api`/`asr_transcribe_monitor` 等子串，避免 `Get-CimInstance ... LIKE` 自匹配杀到自身）。它：① 持久化 `ASR_INFER_WORKERS=1`（`[Environment]::SetEnvironmentVariable(...,'User')`，降低 funasr 加载模型的峰值内存，临睡/转写机器空闲内存紧张时必备）；② 杀掉旧的转写监控并重启 `asr_api`（`services/asr_api.py --port 5002`，单 worker）；③ 以后台独立进程拉起监控。启动后打印 `BOOT_DONE`。
- `scripts/asr_transcribe_monitor.ps1`：循环巡检脚本（每 60s 一轮），`while($true)` 整体包在 `try/catch` 中，**永不静默退出**。每一轮：
  1. 看门狗存活检测（仅 **ALERT**，不接管其管理）；
  2. 本地 `asr_api :5002` 进程存活 + `/health` 正常，**连续 2 次失败则杀进程并自愈重启（1 worker）**；
  3. 反代隧道**真连通探测**：`ssh` 到服务器 `curl localhost:15002/health`（只有这能抓到「ssh 进程存活但 15002 不通」的僵死），**连续 2 次不可达则重建隧道**；
  4. 活动快照（`SNAP` 行）：`api_pid`、CPU、`ws` 内存、`funasr_workers` 数（>0 即正在推理）、机器空闲内存（<1.5GB 标 `WARN`）。

日志写入 `scripts/asr_transcribe_monitor.log`（UTF8、全英文路径），异常行打 `[ALERT]`。监控进程独立后台运行，**不随 IDE 会话结束而退出**；转写结束需手动 `Stop-Process` 对应 powershell 进程收尾。

启用（转写开始前运行一次即可）：

```powershell
powershell -NoProfile -File "h:\项目1\scripts\boot_transcribe.ps1"
```

> 注意：监控与看门狗**可同时运行**（职责互补，不争抢 15002）；监控的隧道重建逻辑会先 `fuser -k 15002/tcp` 清掉服务器侧端口残留，再起新 ssh，因此看门狗旧隧道若僵死会被自然接管，无需手动清理。转写期间笔记本**保持唤醒、勿注销/睡眠**，否则隧道与监控进程会断。

### 7.2 ASR 本地服务启用 GPU 转写（RTX 3050 Ti）

本机 GPU（RTX 3050 Ti Laptop GPU，4GB）闲置，已将 SenseVoice 推理从 CPU 搬到 GPU，速度提升数倍到数十倍（已验证上线）。

**运行时（已装）**：CUDA 12.6 toolkit + cuDNN 9.x（通过 PyPI 官方 wheel `nvidia-cudnn-cu12` 安装，等价于 GitHub `NVIDIA/cudnn` releases 的 zip 内容）+ `onnxruntime-gpu` 1.19.2（替换原 CPU 版 `onnxruntime`）。`funasr_onnx` 的 `SenseVoiceSmall` 原生支持 `device_id`：非 `-1` 且 CUDA EP 可用时自动用 `CUDAExecutionProvider`，否则回退 CPU 并打印 `RuntimeWarning`（代码侧零改动，仅 `backend/services/asr_api.py` 的 `get_model` 把环境变量 `ASR_DEVICE_ID` 透传给 `device_id`）。

**启用方式**：环境变量 `ASR_DEVICE_ID`（默认 `-1`=CPU；置 `0`=GPU 0）。`scripts/boot_transcribe.ps1` 已固化：持久化 `ASR_DEVICE_ID=0`、把 `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin` 与 `G:\123\lib\site-packages\nvidia\cudnn\bin` **注入进程 PATH**（onnxruntime 加载 CUDA EP 必须能搜到 `cudart64_12` / `cudnn64_9` 等 DLL；用户级 PATH 修改需重启 IDE/电脑才对所有进程生效，故 boot 在进程内显式注入并由此传递给 `asr_api` 及其子进程与监控自愈），并以 `INFER_WORKERS=2` 启动（每 worker 各加载一份模型到 GPU，约 1.1GB/worker，4GB 显存可提到 3）。

**性能（实测）**：稳态 GPU 推理约 120ms / 10s 音频（asr_api HTTP 端到端约 600ms，含切片/HTTP/进程池开销），比 CPU 快约 5–40 倍。**注意每段、每个 worker 的首次推理有约 28s 的 cuDNN 算法 autotune 一次性开销**，之后才进入稳态；240 段批量转写时仅前 1–2 段显著偏慢。

**排错**：若 `asr_api` 启动后 GPU 显存为 0 且推理慢，通常是 CUDA/cuDNN DLL 未进入进程 PATH——查 `scripts/asr_api_mon_err.log` 有无 `CUDAExecutionProvider is not avaiable` 回退警告，确认 boot 注入是否生效。用 `nvidia-smi` 看 `asr_api` 进程显存占用即可确认是否真在 GPU 上跑。`onnxruntime-gpu` 1.19.2 要求 cuDNN 9.* + CUDA 12.*，且 cuDNN 8/9 不兼容，升级/重装时需保证三者版本匹配。
