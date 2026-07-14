# 活动台账录音总结 UI 部署故障排查与修复记录

> 项目：襄阳农高区招商服务网站（项目1）
> 发生时间：2026-07-14
> 影响范围：活动台账录音转写/总结前端 UI 全部功能

---

## 一、故障时间线

| 时间 | 事件 |
|------|------|
| 16:30 | 首次部署 V15.1 前端修复到生产 |
| 16:35 | 部署后出现 UI 组件错位、按钮不对齐 |
| 16:47 | 后端 502 错误（`ImportError: cannot import name 'ClientChatSession'`） |
| 16:55 | 回滚到旧版本，恢复服务 |
| 17:00 | 重新部署，UI 修复仍未生效 |
| 17:05 | 用户反馈"完全没有生效" |
| 17:15 | 模型选择器 500 错误 |
| 17:20 | 定位根因：**Vite 旧缓存 + nginx 路径配置** |
| 17:30 | 修复完成，但按钮结构仍有问题 |
| 17:45 | 补全丢失的按钮 |
| 18:30 | 清除 Vite 缓存后重建 |
| 18:46 | 最终达到预期效果 |

---

## 二、根因分析

### 问题 1：Vite 旧缓存导致线上永远是旧代码

**现象**：本地修改 CSS 后提交、推送、部署，线上始终看不到变化。

**错误认知**：
- ❌ 以为是浏览器缓存（让用户清缓存、换浏览器、换网络）
- ❌ 以为是 deploy.sh 同步遗漏（反复检查 cp 命令）
- ❌ 以为是 git 合并丢失代码（反复检查 diff）

**真实根因**：服务器上 `frontend/node_modules/.vite/deps/` 保留了旧构建的缓存。当运行 `npm run build` 时，Vite 使用了缓存转换结果，不会用最新源码重新编译，输出的 CSS hash 和旧版本完全一致，导致旧 CSS 覆盖了已部署的新文件。

**修复命令**（关键）：

```bash
# 在服务器 frontend/ 目录执行
rm -rf node_modules/.vite .vite-temp dist
npm run build
```

### 问题 2：nginx root 目录配置导致 JS/CSS 404

**现象**：主页面 200，但 `/assets/*.js` 返回 404。

**根因**：
- Flask 的 `static_folder='../static'` → 对应服务器 `/www/wwwroot/invest-app/static/`
- nginx 的 `root` 设置为 `frontend/dist/`（从未被更新）
- deploy.sh 的执行 `cp frontend/dist/* static/` 实际写入了 `/static/`（uploads 软链的实体目录），但 nginx 不从这里取文件

**修复**：修改 nginx root 为 `/www/wwwroot/invest-app/static`：

```nginx
# /etc/nginx/conf.d/invest-app.conf
server {
    # root /www/wwwroot/invest-app/frontend/dist;  ← 旧配置（不更新）
    root /www/wwwroot/invest-app/static;           ← ← 新配置（与 deploy.sh 同步位置一致）
}
```

### 问题 3：API 路由 404（`/api/llm-models`）

**现象**：前端调用 `/api/llm-models` 返回 500。

**根因**：Flask 路由注册为 `/llm-models`（顶层），而前端 axios baseURL 为 `/api`，实际请求 `/api/llm-models`，在 Flask URL Map 中无匹配，返回 404（被 nginx 错误地报告为 500）。

**修复**：

```python
# backend/routes/__init__.py 顶部导入
from flask import jsonify
from routes.business_auth import dual_login_required

def _get_llm_models():
    from models.investment import LLMModel  # ← 这个导入路径也是错的，见问题 4
    ms = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order).all()
    return jsonify({"code": 0, "data": [{"id": m.id, "name": m.name, "provider": m.provider} for m in ms]})

app.add_url_rule("/api/llm-models", view_func=dual_login_required(_get_llm_models), methods=["GET"])
```

### 问题 4：LLMModel 导入路径错误

**现象**：`/api/llm-models` 500，`ImportError: cannot import name 'LLMModel' from 'models.investment'`。

**根因**：`LLMModel` 实际定义在 `models/ai.py`，但代码写成了 `from models.investment import LLMModel`。

**修复**：`from models.ai import LLMModel`

### 问题 5：client 蓝图导致 502 启动失败

**现象**：首次部署后，服务启动失败，502。

**根因**：`routes/__init__.py` 注册了 `client_bp` 蓝图，导致 import `routes/client.py`，该文件从 `models` 导入 `ClientChatSession`。但在 master 分支代码中，`models/__init__.py` 未导出 `ClientChatSession`（该模型类存在于未跟踪的 `models/client_app.py` 中，属安卓移动端代码，未上线）。

**修复**：注释掉 `routes/__init__.py` 中的 client 蓝图注册（待移动端上线时启用）。

---

## 三、关键处理规范（未来部署必读）

### 3.1 前端构建必须清缓存

```bash
# ✅ 正确：每次构建前清除 Vite 缓存
cd frontend
rm -rf node_modules/.vite .vite-temp dist
npm run build

# ❌ 错误：直接构建，可能使用旧缓存
cd frontend
npm run build
```

**验证**：构建后检查 `dist/assets/ActivityLedgerView-*.css` 的 hash 是否变化。比较线上请求的 hash 与本地构建结果，一致才表示同步成功。

### 3.2 部署后必须验证响应头

```bash
# 验证 cache-control
curl -sI http://123.56.9.243/assets/ActivityLedgerView-*.css | grep cache-control
# 期望输出：Cache-Control: no-cache

# 验证文件 HTTP 200
curl -s -o /dev/null -w "%{http_code}\n" http://123.56.9.243/assets/ActivityLedgerView-*.js

# 验证内容包含修复代码
curl -s http://123.56.9.243/assets/ActivityLedgerView-*.js | grep -c "追加录音文件"
# 期望：>= 1
```

### 3.3 部署脚本必须包含完整流程

```bash
#!/bin/bash
# deploy_frontend.sh - 前端部署流程（关键步骤）

APP_DIR="/www/wwwroot/invest-app"

# 1. 拉取代码
cd "$APP_DIR" && git pull origin master

# 2. 清除缓存（关键步骤）
cd frontend
rm -rf node_modules/.vite .vite-temp dist

# 3. 构建
npm run build

# 4. 同步到 nginx 静态目录（保留 uploads）
cd "$APP_DIR"
[ -d static/uploads ] && mv static/uploads /tmp/uploads_deploy_backup
rm -rf static/assets static/index.html static/favicon.svg static/icons.svg
cp -r frontend/dist/* static/
[ -d /tmp/uploads_deploy_backup ] && mv /tmp/uploads_deploy_backup static/uploads

# 5. 重启 nginx（invest-app 无需重启，因为是纯前端部署）
nginx -t && systemctl reload nginx
```

### 3.4 浏览器缓存的应急处理

当线上代码已更新但用户仍看到旧版本时：

1. **强制刷新**：`Ctrl + Shift + R`（Mac: `Cmd + Shift + R`）
2. **开发者工具清缓存**：F12 → Network → 勾选 **Disable cache** → 刷新
3. **服务器侧强制**：修改 nginx 响应头 `Cache-Control: no-cache`（对 `*.js` `*.css`）

但应用本文档 3.1 的规范后，hash 文件名会随内容变化，浏览器自然请求新文件，缓存问题不再存在。

---

## 四、修复后的效果

```
┌─ 录音文件 ────────────────────────────┐
│ [录音1.mp3 ▶________] [🗑]            │
│ [+ 追加录音] [重新识别] [删除全部]     │  ← 单行，垂直居中对齐
├────────────────────────────────────────┤
│ 📄 录音识别内容                        │
│ ┌─ 分段原文 │ 清洁版 │ 摘要版 ─┐      │
│ │                              │      │
│ │  (分段原文内容)              │      │
│ └──────────────────────────────┘      │
├────────────────────────────────────────┤
│ [选择模型 ▼] [重新总结] [术语校正]     │  ← 单行，垂直居中对齐
└────────────────────────────────────────┘
```

---

## 五、相关文件

| 文件 | 角色 |
|------|------|
| `frontend/src/views/ActivityLedgerView.vue` | 录音模块主组件 |
| `frontend/vite.config.js` | Vite 构建配置 |
| `scripts/deploy.sh` | 生产部署脚本 |
| `etc/nginx/conf.d/invest-app.conf` | nginx 站点配置 |
| `backend/routes/__init__.py` | Flask 路由注册（含 `/api/llm-models` 顶层注册） |
| `backend/models/ai.py` | `LLMModel` 模型定义 |

---

## 六、经验教训

1. **永远不要信任 Vite 缓存**：每次生产构建前必须 `rm -rf node_modules/.vite .vite-temp dist`。

2. **部署后必须验证 hash**：比较线上 CSS/JS 文件名与本地构建结果，不一致表示同步失败。

3. **nginx root 和 Flask static_folder 必须对齐**：两者指向同一目录。

4. **API 路由路径必须与前端 baseURL 匹配**：前端 baseURL=`/api` 时，Flask 注册 `/api/xxx`。

5. **启动 502 先看完整 Traceback**：`journalctl -u invest-app -n 50 --no-pager | grep -A10 Traceback` 能快速定位 ImportError。

6. **apps never work the first time when deploying to production**：多验证、多比较、多假设"我的代码没生效"是有原因的。
