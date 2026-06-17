# 襄阳农高区招商服务网站

简洁风格的招商服务网站，为襄阳农高区提供在线招商信息展示和 AI 智能招商工具。

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 一键启动（Windows）

双击项目根目录下的 `run.bat` 文件，自动完成依赖安装和服务启动。

### 手动启动

#### 1. 启动后端 API 服务

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端启动在 `http://localhost:5000`，首次运行自动创建数据库和初始数据。

#### 2. 启动前端开发服务器

```bash
cd frontend
npm install --registry https://registry.npmmirror.com
npm run dev
```

前端启动在 `http://localhost:5173`，自动代理 API 请求到后端。

### 访问地址

| 页面 | 地址 |
|------|------|
| 首页 | `http://localhost:5173/` |
| 农高区介绍（轮播） | `http://localhost:5173/intro` |
| 招商工具箱 | `http://localhost:5173/toolbox` |
| 管理后台登录 | `http://localhost:5173/admin/login` |

### 默认管理员账号

- 用户名：`admin`
- 密码：`changeme123`

**首次登录后请立即修改密码！**

## 功能说明

### 前台功能

1. **首页** — 可配置的背景图、标题和两个入口按钮
2. **农高区介绍** — 全屏 PPT 式轮播，支持图文页和地图页两种类型
3. **招商工具箱** — AI 智能对话工具，支持多模型选择和快捷提示词

### 后台管理

登录后台后可管理：

- **首页配置** — 更换背景图、修改标题和按钮文字
- **轮播页管理** — 创建/编辑/删除/排序轮播页，支持图文页和地图页
- **省份信息** — 编辑全国省份和湖北城市的信息卡片，设置地图高亮
- **大模型管理** — 配置多个 AI 大模型的 API Key 和参数，支持测试连接
- **提示词管理** — 创建/编辑前台快捷提示词模板

### 地图功能

- **全国地图** — 展示 34 个省级行政区，可高亮重点省份
- **湖北省地图** — 展示 17 个地市州
- 鼠标悬停高亮区域时弹出信息卡片（标题 + 详细内容）

### AI 对话

支持所有 OpenAI 兼容 API 格式的大模型厂商：

- OpenAI (GPT-4o, GPT-3.5)
- DeepSeek (deepseek-chat, deepseek-reasoner)
- 智谱AI (GLM-4)
- 月之暗面 (Moonshot)
- 硅基流动 (SiliconFlow)
- 自定义 API 地址（支持 Ollama 等本地模型）

## 项目结构

```
├── backend/                 # Flask 后端 API
│   ├── app.py              # 应用入口
│   ├── config.py           # 配置文件
│   ├── models.py           # 数据库模型
│   ├── seed_data.py        # 初始数据
│   ├── routes/             # API 路由
│   ├── services/           # 业务逻辑（LLM 调用等）
│   └── utils/              # 工具函数（图片上传等）
│
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 可复用组件
│   │   ├── router/         # 路由配置
│   │   ├── api/            # API 请求封装
│   │   ├── stores/         # 状态管理
│   │   └── assets/         # 静态资源
│   └── ...
│
├── static/                 # Flask 静态文件服务
│   ├── data/               # GeoJSON 地图数据
│   └── uploads/            # 上传的图片
│
└── run.bat                 # 一键启动脚本
```

## 技术栈

- **前端**：Vue 3 + Vite + Element Plus + ECharts
- **后端**：Python Flask + SQLAlchemy
- **数据库**：SQLite（可切换至 PostgreSQL）
- **地图**：ECharts + GeoJSON（离线可用）
- **富文本**：Quill.js

## 后续升级

1. 将 SQLite 切换为 PostgreSQL（修改 `config.py` 一行配置）
2. 部署至云服务器
3. 添加用户登录和权限系统
4. 移动端适配
