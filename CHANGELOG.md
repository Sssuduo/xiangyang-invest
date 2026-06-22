# 更新日志

## V4.0 (2026-06-22) — 招商动态导入智能拆分 + 批量管理

### 动态导入：智能文本拆分

导入预览时自动识别动态内容中的日期，拆分为独立记录：

#### 拆分算法
- 正则匹配日期模式：`X月X日` / `X月X号` / `XXXX年X月X日` 等
- 按换行 + 编号标记（`1、` `2.` `（1）` `①` 等）分割句段
- 含日期的句段 → 新记录起点；无日期句段 → 归入上方最近分组
- **保留完整原始语句**（含日期本身），不做加工修饰
- **自动去除编号前缀**（`1、` `2、` 等），只留纯净内容

#### 示例
```
输入：1、5月27日下午，已在农高区汇报...
     2、5月28日日上午，区政协主席调研...
     3、6月3日，陪同企业实地考察...
     4、6月10日，企业与集团座谈...

输出：4 条独立动态，各自携带 date + 完整 content
```

#### 年/月日分离
- 预览表新增「年份」列（默认带入当前年份，全局/逐行可改）
- 新增「月日」列（从文本中提取，如 `5月27日`）
- 导入时组合 `2026年5月27日` → `datetime(2026-05-27)`

### 动态导入：模板下载弹窗

点击「下载导入模板」→ 弹出对话框：

| 功能 | 说明 |
|------|------|
| 跟进状态筛选 | 下拉选择跟进状态 → 查询匹配项目 |
| 项目预览表格 | 显示项目名称、跟进状态、投资企业 |
| 行删除 | 移除不需要的项目 |
| 下载含项目模板 | 项目ID + 项目名称预填到 Excel 第 1~2 列 |
| Excel 下拉验证 | 项目名列含数据验证下拉（隐藏工作表方案，无公式长度限制） |

### 动态导入：项目ID精确匹配

修复项目名称匹配导致的重复导入 bug：

| 变更 | 说明 |
|------|------|
| 新增 `项目ID` 列 | 导入字段配置首位（sort_order=0），模板自动填入数据库主键 |
| 导入匹配优先级 | `project_id` 有效 → 直接用ID查项目；否则回退名称匹配 |
| `InvestmentActivity.date` | 改为 `nullable=True`，日期可选，精确到天 |

### 批量删除

| 位置 | 功能 |
|------|------|
| 业务端 `/investment-activity` | 复选框 +「批量删除 (N)」按钮 |
| 后台 `/admin/activity` | 复选框 + 表头「批量删除 (N)」按钮 |
| API `POST /admin/activity/activities/batch-delete` | `{ids: [1,2,3]}` 批量物理删除 |

### 其他优化

- 日期选择器从 `datetime` 改为 `date-only`（编辑抽屉 + 后台管理）
- 动态内容列改为 3 行截断 + hover tooltip 完整展示（600px 宽，pre-wrap）
- 预览弹窗加宽至 1080px，适配新增列
- 导入预览统计显示拆分信息（原始 N 行 → 拆分后 M 行）

### 新增 API

| 端点 | 说明 |
|------|------|
| `GET /api/admin/activity-import/projects-for-template?follow_status=xxx` | 模板项目列表 |
| `GET /api/admin/activity-import/template?project_ids=1,2,3` | 含项目ID的模板下载 |
| `POST /api/admin/activity/activities/batch-delete` | 批量删除动态 |

### 修改文件统计

| 层 | 文件数 | 关键变更 |
|----|--------|----------|
| 后端 | 5 | `admin_activity_import.py` 核心重写（+474/-190） |
| 前端 | 9 | `ActivityView.vue` 模板弹窗 + 预览重构（+298） |
| 合计 | 15 | +1295 / -190 行 |

---

## V3.0 (2026-06-21) — 招商对接项目库 + 导入导出系统 + 招商动态模块

### 招商对接项目库

基于 5 表结构的完整投资项目管理模块：

#### 数据模型
- `FollowStatusDict` — 跟进状态字典（跟进中 / 暂缓 / 已签约 / 已落地 / 已取消，带颜色标识）
- `MeetingStatusDict` — 上会状态字典（未上会 / 推荐上会 / 已上会，带颜色标识）
- `OrganizationDict` — 单位字典（推介单位 & 责任单位共用，含市/区两级共 19 个单位）
- `ProjectTypeDict` — 项目类型字典（9 种类型：畜禽粪污循环利用 / 养殖种植 / 农业灌溉装备 / 秸秆综合利用 / 设施农业 / 红薯精深加工 / 食品加工 / 农机装备制造 / 智慧农业）
- `InvestmentProject` — 招商对接项目主表（项目名称、投资商、企业简介、项目内容、投资金额、跟进/上会状态、推介/责任单位、责任人、项目文档、首次对接时间，软删除）
- `EnterpriseDemand` — 企业诉求子表（诉求内容、解决方案、状态流转 pending→processing→resolved）

#### API
- `GET/POST /api/admin/investment` — 项目列表/创建
- `GET/PUT/DELETE /api/admin/investment/<id>` — 项目详情/更新/软删除
- `GET/POST /api/admin/investment/<id>/demands` — 企业诉求列表/新增
- `PUT/DELETE /api/admin/investment/demands/<id>` — 诉求更新/删除
- `GET /api/admin/dict/organizations` — 单位字典查询
- `GET /api/admin/dict/project-types` — 项目类型字典查询
- `GET /api/admin/dict/follow-statuses` — 跟进状态字典查询
- `GET /api/admin/dict/meeting-statuses` — 上会状态字典查询

#### 前端页面
- **业务端** — `/investment` 招商项目展示页（表格列表 + 抽屉详情）
- **后台** — `/admin/investment` 项目列表页（搜索/筛选/批量操作/软删除恢复）
- **后台** — 抽屉式项目编辑表单（双分栏 + 企业诉求增删改）

### 导入导出系统

#### 招商项目导出
- `ExportFieldConfig` 模型 — 14 个字段的可见性/列宽/排序配置
- `GET /api/admin/export/config` — 获取导出配置
- `PUT /api/admin/export/config` — 更新导出配置
- `GET /api/admin/export/download` — 按配置生成并下载 Excel（openpyxl）

#### 招商项目导入
- `ImportFieldConfig` 模型 — 14 个字段的启用/必填/排序配置
- `GET /api/admin/import/config` — 获取导入配置
- `PUT /api/admin/import/config` — 更新导入配置
- `GET /api/admin/import/template` — 下载 Excel 导入模板
- `POST /api/admin/import/preview` — 上传 Excel 预览解析结果
- `POST /api/admin/import/execute` — 执行导入（含数据校验/字典匹配）

#### 招商动态导入导出
- 与项目导入导出对称的 4 个配置页面和 API

#### 前端页面
- `/admin/export-config` — 导出字段配置（拖拽排序/可见性切换/列宽调整）
- `/admin/import-config` — 导入字段配置（启用/必填/排序）
- `/admin/activity-export-config` — 动态导出配置
- `/admin/activity-import-config` — 动态导入配置

### 招商动态模块

#### 数据模型
- `InvestmentActivity` — 招商动态（所属项目、日期、内容、附件）

#### API
- `GET /api/activities` — 公开动态列表（按项目筛选）
- `GET/POST /api/admin/activities` — 管理端列表/新增
- `GET/PUT/DELETE /api/admin/activities/<id>` — 详情/更新/删除
- `GET /api/admin/activities/export/download` — 导出 Excel
- `GET/PUT /api/admin/activities/import/*` — 导入配置/模板/预览/执行

#### 前端页面
- **业务端** — `/investment-activity` 招商动态展示页
- **后台** — `/admin/activity` 动态管理列表
- **公共组件** — `ActivityDrawer` 动态抽屉组件

### 其他新增/优化

#### 联系我们
- `ContactInfo` 模型 — 个人名片（姓名/职务/电话/邮箱/简介/微信二维码）
- `/contact` 联系方式展示页
- `/admin/contact` 后台配置页

#### 业务端导航
- `BusinessNavbar` 组件 — 招商项目 / 招商动态导航栏

#### 首页 & 国家农高区优化
- 首页内容结构更新
- 国家农高区页面交互调整

#### 字典值扩充
- 单位字典新增：市委台办、市委老干局、市人社局、市农业农村局、区城管局、区农业农村局、襄州国投、襄北监狱
- 人大 → 区人大常委会，政协 → 区政协
- 项目类型新增：红薯精深加工、食品加工、农机装备制造、智慧农业
- 种子数据改为幂等更新机制（exist-then-update）

#### 内容数据迁移
- `migrate_content.py` — 国家农高区/襄阳农高区介绍/联系我们内容迁移脚本

### 技术统计
- **后端**：新增 10 个路由模块、5 个数据模型、7 个字典/配置表
- **前端**：新增 6 个 API 模块、12 个页面/组件
- **依赖**：`openpyxl` Excel 读写（已纳入 requirements.txt）

---

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
