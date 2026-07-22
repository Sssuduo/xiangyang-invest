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
