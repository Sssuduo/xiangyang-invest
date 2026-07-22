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

本机 OpenSSH `known_hosts` 权限问题曾导致推送失败，已临时配置：

```
git config core.sshCommand "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
```

如遇推送报 `Permission denied (publickey)` 或 `known_hosts` 相关错误，先确认该配置存在。建议将其写入本机用户级 `~/.gitconfig` 而非仅仓库级，避免每次重配。

## 5. 部署保护约定

`scripts/deploy.sh` 含 `git reset --hard` 与 `rsync --delete`，**不得波及** `static/data`、`static/uploads`：

- 针对地图 404 的修复 `--exclude='data'` 必须随代码入库（经 review），否则下次部署会被 `git reset --hard origin/master` 还原而复发。
- 任何对 `deploy.sh` 的修改都需同步进入 `master`（经 `dev` 合并），不能只改生产磁盘。
- nginx `/static/uploads/` 别名属"带外修改"，应纳入仓库管理，避免服务器重置即丢失。
