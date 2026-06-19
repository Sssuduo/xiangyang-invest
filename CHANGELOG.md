# 更新日志

## V2.0 (2026-06-19) — 国家农高区地图交互升级

### 地图功能

#### 省份点击聚焦放大
- 点击高亮省份（已配置高亮城市）→ 地图平滑过渡到该省份的城市级视图
- 省内城市绿色底色 `#5a9e6f`，高亮城市淡金色 `#d4a94e`
- 省外城市暗灰色 `#5a5a5a`（opacity 0.35），标签默认展示
- 省级地图自动居中到高亮城市坐标均值
- 地图缩放级别提升至 3.5~8.5 区间

#### 返回国家级地图
- 点击省外城市 → 返回
- 点击地图空白区域 → 返回
- 按 ESC 键 → 返回

#### 交互模型
| 操作 | 行为 |
|------|------|
| 悬浮省份 | 显示信息卡片（跟随鼠标） |
| 点击高亮省份 | 聚焦放大到省级地图 |
| 悬浮省内城市 | 卡片固定右侧展示 |
| 点击省外城市/空白/ESC | 退回全国视图 |

#### 视觉升级
- 国家级页面背景：浅蓝渐变 `#dce8f5 → #b0c8e8`
- 地图背景：中蓝 `#c2d8f0`
- 省级聚焦图例仅保留「国家级农高区」淡金色项

### 数据库
- 新增 `CityInfo` 表（省份子级城市高亮配置）
  - `id, province_id (FK), city_code, city_name, is_highlighted, card_title, card_content`
- `ProvinceInfo.to_dict()` 新增 `has_city_highlights` 字段

### API
- `GET /api/provinces/<id>/cities` — 公开城市查询
- `GET /api/admin/provinces/<id>/cities` — 管理端城市列表
- `PUT /api/admin/provinces/<id>/cities/<city_id>` — 更新城市
- `POST /api/admin/provinces/<id>/cities/batch` — 批量更新高亮
- `POST /api/admin/provinces/<id>/cities/seed` — 从 GeoJSON 初始化

### 数据文件
- `static/data/china_cities.json` — 全国 449 城市 GeoJSON（3.9 MB），DataV.GeoAtlas API 采集
- `scripts/download_city_geojson.py` — 数据下载脚本

### 新增页面
- 联系我们页面（`/contact`）
- 国家农高区页面（`/national`）
- 后台轮播配置页、联系我们配置页

---

## V1.0 (2026-06-10) — 初始版本
- Vue 3 + Vite 前端，Flask + SQLite 后端
- 首页可配置背景/标题/按钮
- 全屏轮播引擎（图文页 + 地图页）
- ECharts 全国/湖北省双级别 2D 地图
- 招商工具箱（LLM 多模型对话）
- 后台管理面板（省份/轮播/模型/提示词/首页配置）
- Element Plus UI 组件库
