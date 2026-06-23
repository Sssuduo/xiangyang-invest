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

## 更新部署流程

代码在 GitHub：`https://github.com/Sssuduo/xiangyang-invest.git`

```bash
# SSH 连接服务器后
cd /www/wwwroot/invest-app
git pull

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
