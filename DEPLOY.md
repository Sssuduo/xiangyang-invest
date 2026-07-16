# 生产环境部署文档

> 部署日期：2026-06-23 | 服务器：阿里云轻量应用服务器 | 公网 IP：123.56.9.243

---

## 访问地址

**http://123.56.9.243**

---

## 服务器信息

| 项目 | 值 |
|---|---|
| 公网 IP | 123.56.9.243 |
| 操作系统 | Alibaba Cloud Linux 3 (OpenAnolis) |
| 管理面板 | 宝塔 Linux 面板 11.1.0 |
| Python | 3.11.13 |
| Node.js | v20.20.2 |
| nginx | 1.24.0 |
| 数据库 | SQLite |
| 项目路径 | `/www/wwwroot/invest-app/` |

---

## 部署架构

```
用户浏览器
    │
    ▼
nginx (:80) ─────────── 静态文件 (/www/wwwroot/invest-app/frontend/dist/)
    │                    上传文件 (/www/wwwroot/invest-app/static/)
    │
    ├─ location /        → try_files $uri /index.html (SPA fallback)
    ├─ location /api     → proxy_pass http://127.0.0.1:8000
    └─ location /static  → alias /www/wwwroot/invest-app/static
                              │
                              ▼
                         gunicorn (:8000, 2 workers)
                              │
                              ▼
                         Flask app
                              │
                              ▼
                         SQLite (instance/app.db)
```

---

## 服务管理

### 后端（invest-app）

```bash
systemctl start invest-app     # 启动
systemctl stop invest-app      # 停止
systemctl restart invest-app   # 重启
systemctl status invest-app    # 查看状态
systemctl enable invest-app    # 开机自启（已启用）
journalctl -u invest-app -f    # 实时日志
```

服务文件：`/etc/systemd/system/invest-app.service`

### nginx

```bash
systemctl restart nginx        # 重启
nginx -t                       # 检查配置
```

配置文件：`/etc/nginx/conf.d/invest-app.conf`

---

## 目录结构

```
/www/wwwroot/invest-app/
├── backend/               # Flask 后端
│   ├── app.py             # 入口（工厂模式）
│   ├── config.py          # 配置（.env 覆盖）
│   ├── .env               # 生产环境变量
│   ├── models.py          # 数据模型
│   ├── routes/            # API 路由
│   ├── seed_data.py       # 种子数据 + 迁移
│   └── requirements.txt   # Python 依赖
├── frontend/              # Vue.js 前端
│   ├── dist/              # 构建产物（nginx 直接服务）
│   ├── src/               # 源代码
│   └── vite.config.js     # Vite 配置
├── instance/              # SQLite 数据库
│   └── app.db
└── static/                # 上传文件
    └── uploads/
```

---

## 环境变量（backend/.env）

```
FLASK_ENV=production
SECRET_KEY=xynq2026-invest-secret-key-prod
DATABASE_URL=sqlite:////www/wwwroot/invest-app/instance/app.db
```

---

## 分支策略

| 分支 | 用途 | 部署环境 |
|------|------|----------|
| `master` | 生产分支，稳定版本 | 生产服务器 (123.56.9.243) |
| `dev` | 测试分支，日常开发 | 本地开发环境 |

**工作流程：**
1. 所有代码修改在 `dev` 分支上进行
2. 本地验证通过后，提交到 `dev` 分支并 push 到 GitHub
3. 确认功能稳定后，将 `dev` 合并到 `master`
4. 生产服务器从 `master` 分支拉取部署

## 更新部署流程

代码在 GitHub：`https://github.com/Sssuduo/xiangyang-invest.git`

### 测试环境（本地）
```bash
git checkout dev
# ... 开发修改 ...
git add . && git commit -m "描述修改内容"
git push origin dev
```

### 生产环境（服务器）
```bash
# SSH 连接服务器后
cd /www/wwwroot/invest-app
git checkout master
git pull origin master

# 后端依赖更新
pip3.11 install -r backend/requirements.txt

# 前端重新构建
cd frontend
npm install
npm run build

# 重启服务
systemctl restart invest-app
```

---

## ⚠️ 上传文件持久化（关键约定,违反会导致历史图片 404）

**问题根因**:过去部署把 `static/uploads/` 当作代码目录,每次 `git pull` 或重建后目录被清空/从未带走,导致 DB 记录的图片文件在磁盘上找不到,所有历史动态的在线图 404。

**约定**:上传文件(`static/uploads/` 下的图片/文档/视频)是**持久化运行时数据**,绝不与代码一起被覆盖。

### 0) 红线（部署脚本/CI 必须遵守,违反即事故）

- **部署脚本里严禁出现** `rm -rf .../uploads`、`git clean`、`npm run clean`、`rm -rf static` 等会波及 uploads 的命令。
- **部署包不能包含 uploads 内容**:只推 `backend/`、`frontend/src/`、`static/`(除 uploads 外)和配置文件,** uploads 目录不进入部署包**。
- **每次部署前必须跑前置脚本** `scripts/deploy_prepare.sh`(详见下方),它保证 `static/uploads` 是指向 `data/uploads` 的软链,且目录可写。
- **部署后必须验收**(三步,任一项不通过即回滚):
  1. `ls -ld /www/wwwroot/invest-app/static/uploads` 必须是软链指向 `data/uploads`。
  2. 任选一张图 `curl -I /static/uploads/<该图>` 必须 200。
  3. 管理员登录访问 `GET /api/uploads/health`,`data.missing_count` 必须 ≤ 部署前。

### 0.1) 部署前置脚本 `scripts/deploy_prepare.sh`

作用:
- 创建 `data/uploads`(如果不存在)
- 把 `static/uploads` 转型为 → `data/uploads` 的软链(实体目录时先 rsync 再转,已是软链时校验目标)
- 校验写权限
- 打印文件数量 + nginx 抽样访问一个图片 URL

用法:
```bash
# 默认 APP_DIR=/www/wwwroot/invest-app
./scripts/deploy_prepare.sh
# 强制再同步一次存量文件(幂等,仅补缺)
./scripts/deploy_prepare.sh --force-sync
# 仅检查,不做任何写操作(可在 CI 中作准入)
./scripts/deploy_prepare.sh --check-only
```

**建议在 `scripts/deploy.sh` 把它作为正式 `git pull` 前的第一步**(已在下文的「标准部署流程」列出)。

### 1) 代码侧:UPLOAD_FOLDER 环境变量覆盖

`backend/config.py` 已支持环境变量 `UPLOAD_FOLDER` 覆盖默认路径(默认 `project_root/static/uploads/`,开发不受影响)。

- **方式 A(推荐:不改代码,nginx 做 symlink)**:部署前置脚本会自动把 `static/uploads` 做成软链,无需改 Python 代码,已有 DB 记录(`/static/uploads/xxx`)均不动。
- **方式 B(改代码)**:在服务器 `backend/.env` 加 `UPLOAD_FOLDER=/www/wwwroot/invest-app/data/uploads`。

### 2) 部署后:启动期自动扫描 + 管理接口

`backend/app.py` 在每次启动后会**自动**调用 `utils.upload_health.log_missing_report`,扫描:`investment_activities.files`、`activity_ledger.files`、`activity_ledger.audio_files`,缺失文件会以 `WARNING` 级日志打印(前 20 条),提示从备份恢复或在管理员后台查看。

管理员接口:`GET /api/uploads/health`(需登录)返回完整缺失清单:
```json
{ "code": 0, "data": {
    "upload_folder": "/.../data/uploads",
    "total_referenced": 120,
    "present_count": 117,
    "missing_count": 3,
    "missing": [ { "table": "investment_activities", "field": "files", "id": 157, "label": "招商动态", "url": "/static/uploads/xxx.jpg", "expected_path": "/.../data/uploads/xxx.jpg" } ]
} }
```

### 3) nginx 配置:为 uploads 单独 alias(配合方式 A 的软链)

在 `location /static` 内部为 uploads 子路径单独 alias 到持久化目录,这样即使其他静态目录重建,uploads 也隔离:

```nginx
# /etc/nginx/conf.d/invest-app.conf
server {
    ...
    location /static/uploads/ {
        alias /www/wwwroot/invest-app/data/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    location /static/ {
        alias /www/wwwroot/invest-app/static/;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
    location / {
        try_files $uri /index.html;
    }
}
```

改完务必 `nginx -t && systemctl reload nginx`。

### 4) 标准部署流程(红线总结)

按顺序执行,任意一步失败立即人工介入,不要继续:
1. `sqlite3 instance/app.db ".backup backups/app_deploy_$(date +%Y%m%d_%H%M%S).db"` — 备份数据库
2. `./scripts/deploy_prepare.sh` — 保证 `static/uploads` 是软链 + 可写
3. `git fetch && git checkout master && git reset --hard origin/master` — 拉代码
4. `pip install -r backend/requirements.txt` / `cd frontend && npm i && npm run build`
5. `systemctl restart invest-app && systemctl reload nginx`
6. 验收(红线 0 的 3 步):软链 + URL 200 + /api/uploads/health 的 missing_count 不上升

### 5) 监控与巡检

- 建议把 `/api/uploads/health` 接入简单监控(比如宝塔/云监控定时请求,missing_count 上升即告警)。
- 订阅 `data/uploads` 分区磁盘空间告警(`MAX_CONTENT_LENGTH` 上限 2GB,堆积会爆盘)。
- 备份策略:备份 `instance/app.db` 时 **同步备份 `data/uploads/`** 目录,否则有 DB 没文件,恢复后仍然 404。

> 违反以上任一条,都可能让"DB 引用但磁盘无文件"再次出现 → 历史图片/附件 404。

---

## 端口与防火墙

| 端口 | 用途 | 开放范围 |
|---|---|---|
| 80 | HTTP（网站访问） | 公网 |
| 22 | SSH | 公网 |
| 8888 | 宝塔面板 | 公网 |

阿里云轻量服务器控制台 → 防火墙 → 确认 80 端口已放行。

---

## 依赖清单

```
Flask==3.1.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.1.0
Flask-Login==0.6.3
Flask-CORS==5.0.1
Werkzeug==3.1.3
requests==2.32.3
python-dotenv==1.1.0
gunicorn==23.0.0
openpyxl==3.1.5
```

---

## 故障排查

| 现象 | 检查 |
|---|---|
| 网站打不开 | `systemctl status nginx invest-app` |
| API 500 错误 | `journalctl -u invest-app -f` 查看错误日志 |
| 静态文件 404 | 检查 `/www/wwwroot/invest-app/static/` 目录权限 |
| 数据库锁定 | SQLite 单写，高并发时可能锁表，考虑升级 MySQL |
