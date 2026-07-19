# 更新日志

## V15.6 (2026-07-19) — 录音转写与总结解耦（状态语义分离）

> 关联问题：活动台账「重新上传录音 → 重新识别」显示识别失败、且无切片进度提示。
> 根因之一为「总结失败被误报为识别失败」（另一根因为 ASR 服务未连接，已在上一轮修复）。

### 转写 / 总结正式解耦

- 后端 `run_async_processing` 转写完成后**不再自动串联总结**，状态停在 `asr_completed`，
  总结改由前端独立的「重新总结」按钮（`retry-summary` / `run_summary_only`）触发。
- 「重新识别」接口语义收敛为「仅重新转写」，与总结互不影响，可分别重试。

### 状态语义分离（修复「总结失败误报识别失败」）

| 状态 | 含义 |
|------|------|
| `asr_processing` | 转写中（含切片进度 `progress_message`：`正在识别 (N/M 段) · 约 X 分钟`）|
| `asr_completed` | 转写完成，等待用户点击「重新总结」|
| `summarizing` | 总结中 |
| `completed` | 总结完成（全流程结束）|
| `asr_failed` | 转写失败（如 ASR 服务未连接）|
| `summary_failed` | 总结失败（转写成功，仅 LLM/docx 失败）|
| `failed` | 兜底异常 |

- `apply_summary_to_item` / `run_summary_only` 总结失败由 `'failed'` 改为 `'summary_failed'`；
- `run_async_processing` 转写阶段失败（含 ASR 不可达、未捕获异常）归为 `'asr_failed'`。

### 前端适配

- 活动台账 `ActivityLedgerView.vue`：状态标签、转写内容展示、失败卡片、操作行、轮询终态分别识别
  `asr_completed` / `summary_failed` / `asr_failed`；`asr_completed` 提示「请点击重新总结」。
- 招商动态 `ActivityView.vue` + 共享 composable `useAudioRecording.js`：状态标签与轮询终态同步识别新状态。
- 修复：总结失败时不再显示「识别失败」，而是「总结失败」并提供「重新总结」按钮。

## V13.5 (2026-07-02) — 编辑侧滑页标签化 + 性能全面优化

### 招商项目编辑侧滑页标签化

编辑抽屉顶部新增三个标签切换：

| 标签 | 包含内容 |
|------|----------|
| **项目情况** | 基础信息 + 企业信息 + 项目详情（含文件上传） + 项目标签 |
| **对接情况** | 专班研判结论 + 对接信息 + 专班负责人 |
| **企业诉求** | 企业诉求卡片列表（独立） |

标签栏 sticky 固定在抽屉顶部，切换标签时表单数据保持。

### 企业诉求交互优化

- 默认**查看模式**：类型以灰色标签逐一展示、对接单位为带图标白色标签、状态彩色标签
- **卡片级编辑**：每张卡片头栏有独立的编辑/删除图标，点击编辑仅该卡片进入编辑模式
- 编辑完成后点击「完成」退出编辑

### 无变更不刷新 last_updated_at

`update_project` 逐字段比较新旧值，仅在值实际变更时才写入。无内容变更时 last_updated_at 保持不变，避免空保存污染"7日内更新/15日内更新"的筛选判定。

### 生产环境性能全面优化

**P0: N+1 查询消除**
- 企业诉求列表：`_enrich_demand_dict` 接受预加载参数 + 批量查 linked_activities（~550→~8 SQL）
- 招商动态列表：`_enrich_activity_dict` 批量查 linked_demands（~65→~6 SQL）
- 在建项目列表：`selectinload` 预加载子表（~155→~8 SQL）

**P1: SQLite 性能**
- WAL 模式 + synchronous=NORMAL + 8MB 缓存 + busy_timeout
- 16 个业务索引覆盖高频筛选/JOIN/ORDER BY

**P2: 启动加速 + 前端减负**
- app_config 版本号机制跳过已执行迁移（首次后 ~100→~20 SQL）
- ECharts 按需引入（1.1MB→700KB）

---

## V7.0 (2026-06-23) — 数据看板 + 登录管理系统

### 用户登录管理

- **BusinessUser 模型**：新建业务用户表，JSON 格式存储按钮级权限
- **双认证体系**：AdminUser（Flask-Login）与 BusinessUser（Session 认证）共存，`@dual_login_required` 装饰器
- **前台登录**：导航栏右上角登录弹窗，访客模式仅 3 个公开菜单
- **后台用户管理**：Admin 可创建/编辑/删除业务用户，配置 3 模块 × 3 操作的按钮权限
- **权限控制**：InvestmentView / ActivityView / DemandView 按钮按权限显隐

### 数据看板 (`/investment-dashboard`)

- **6 个统计卡片**：总诉求、待处理、处理中、已解决、涉及项目、解决率
- **诉求类型分布**（柱状图）：
  - 默认一级字典聚合 + 点击下钻到二级分类
  - 处理状态下拉筛选 + 项目类型下拉筛选
  - 按类型名独立着色（HSL 黄金角度算法）
  - 悬停显示二级明细 + 关联项目列表
- **对接单位分布**（横向柱状图）：
  - 点击单位下钻到该单位的二级分类分布
  - 单位悬停：一级分组 + 二级圆点缩进 + 关联项目
  - 下钻悬停：展示该类型关联的项目名称
- **后端统计 API** `GET /api/admin/demand-stats`：
  - 6 组聚合统计（概览/按类型/按状态/按单位/按项目/月度趋势）
  - 支持 `project_type` 筛选参数
  - 每个类型/单位含关联项目列表（用于悬停提示）

### 关键文件

| 文件 | 操作 |
|------|------|
| `backend/models.py` | 新增 BusinessUser |
| `backend/routes/business_auth.py` | 新建 — 前台登录/登出/状态检查 |
| `backend/routes/admin_business_users.py` | 新建 — 后台用户 CRUD |
| `backend/routes/admin_demand.py` | 追加 `demand-stats` 统计 API |
| `frontend/src/stores/businessAuth.js` | 新建 — Pinia 登录状态管理 |
| `frontend/src/api/auth.js` | 新建 — 认证 API |
| `frontend/src/api/businessUsers.js` | 新建 — 用户管理 API |
| `frontend/src/api/dashboard.js` | 新建 — 数据看板 API |
| `frontend/src/views/DashboardView.vue` | 新建 — ECharts 数据看板 |
| `frontend/src/views/admin/BusinessUserList.vue` | 新建 — 用户权限配置页 |
| `frontend/src/components/common/BusinessNavbar.vue` | 登录入口 + 菜单显隐 |
| `frontend/src/router/index.js` | 新增登录守卫 + 看板路由 |

## V6.1 (2026-06-23) — 诉求类型 el-cascader 级联 + 字典数据配置 + 筛选增强

### 诉求类型级联选择器

- **编辑抽屉**：诉求类型从两个独立 `el-select` 联动改为 Element Plus 原生 `<el-cascader>`（`expandTrigger: 'click'`），点击一级项后右侧滑出二级子面板
- **筛选栏**：诉求类型筛选同样改为 cascader，支持选中一级时自动匹配父级 + 所有子级数据
- **后端支持**：`demand_type` 参数改为逗号分隔多 code，`IN` 查询匹配

### 诉求类型字典数据配置

- 用地保障 → 工业用地、设施农用地、涉及使用林地
- 生产要素保障 → 供热供汽、生产污水处理、厂房场地租赁、原材料保供
- 政府政策支持（原"政策支持"改名）→ 产品销售支持、风电绿电指标、设备购置补贴、落地全流程服务、科研人才支持、农业类政策支持、科技类政策支持
- 平台公司对接 → 产业基金投资、入股参与、项目贷款、金融账期服务

### 表单布局 + 表格列宽

- 编辑抽屉：诉求类型 `span=12→16`，对接单位 `span=12→8`
- 表格：诉求类型 `110px→240px`，项目 `170px→200px`

### 项目类型筛选

- 诉求管理页筛选栏新增「项目类型」下拉框
- 后端 `list_demands` API 支持 `project_type` 参数
- `demand-dicts` 公共 API 新增 `project_types` 返回

## V6.0 (2026-06-23) — 导出增强 + 专班研判结论 + 诉求类型二级字典 + 展开卡片折叠

### 导出系统增强

- **模板名称作为文件名**：Excel 文件名使用模板名；前端 `fetch` 下载方式从 `Content-Disposition` 响应头提取文件名（优先 RFC 5987 `filename*=UTF-8''`）
- **首行标题行**：Excel 第 1 行合并单元格，居中加粗显示模板名称，浅灰底色；表头移至第 2 行，数据从第 3 行开始；冻结窗格 `A3`
- **招商动态去日期前缀**：聚合导出不再拼接 `日期：`，只保留序号 + 原始内容（`1、内容`）
- **企业诉求导出模式**：新增「聚合导出」/「按行导出」选项
  - 聚合导出：诉求合并为一个单元格，`[类型] 内容` 换行
  - 按行导出：诉求拆为独立行，「诉求类型」「对接部门」「诉求内容」「解决措施」分列，项目信息列纵向合并单元格
- **导出字段列表固定宽度**：`.admin-main` 加 `min-width: 0` 阻止 flex 子项被预览表格撑宽
- **字段上移/下移**：导出字段列表每行新增 ↑ ↓ 按钮，交换数组元素实现排序

### 专班研判结论

- `investment_projects` 表新增 `conclusion TEXT` 列
- 新建/编辑项目抽屉加宽至 **780px**，新增「专班研判结论」分区（位于项目投资计划书之后、对接信息之前），4 行文本框
- 查看项目抽屉展示结论（`v-if` 有内容时显示）
- 展开卡片中结论高亮显示（金色渐变背景 + 金色左边框）
- 导出字段新增 `conclusion`、`investment_plan` 映射

### 诉求类型二级字典

- `demand_type_dict` 表新增 `parent_code VARCHAR(32)` 列
- 字典配置页：新增/编辑对话框支持选择父级（一级节点）
- 表格展示：子级显示为 `一级：二级`，蓝色缩进
- 项目表单选择器：`<el-option-group>` 分组下拉，一级为组标签，二级 `└ 名称` 缩进
- 全系统诉求类型显示统一为 `一级名称：二级名称`（后端 `build_display_name_map()` 方法）

### 展开卡片交互重构

- **默认折叠**：展开行默认只显示专班研判结论（高亮置顶）、项目文档、企业诉求摘要
- **顶部切换**：「展开/收起基础信息」按钮位于卡片顶部
- **企业诉求摘要卡片**：「企业诉求共 X 条，涉及 Y 个部门，已解决 Z 条，处理中 W 条，待处理 V 条」，彩色数字
- **独立折叠**：诉求明细独立展开/收起，与基础信息互不影响

### Bug 修复

- **导出模板创建失败**：`export_field_config` 表实际 schema 为 `UNIQUE(field_key)` 单列约束，与模型 `UNIQUE(template_id,field_key)` 复合约束不一致，导致新模板复制字段时 IntegrityError。已重建表修复。
- **创建模板后端**：`default_template` 查询排除自身 + 加 `order_by`
- **创建模板前端**：完善错误处理，`loadTemplates` 不再覆盖当前选中模板
- **导出弹窗模板列表**：校验选中模板是否存在，不存在则自动回退

### 数据库变更

| 表 | 变更 |
|---|---|
| `export_field_config` | 约束改为 `UNIQUE(template_id, field_key)`（重建） |
| `investment_projects` | +conclusion TEXT |
| `demand_type_dict` | +parent_code VARCHAR(32) |

## V5.0 (2026-06-23) — 导出模板多配置 + 聚合字段 + 分页 + 诉求导入增强

### 导出系统重构：多模板 + 聚合字段 + 自定列

- **多模板支持**：新增 `ExportTemplate` 模型，`ExportFieldConfig` 通过 `template_id` 关联模板，不同模板独立配置
- **模板管理**：后台导出配置页支持新建/重命名/删除模板，新建时自动复制默认模板字段
- **聚合导出字段**：新增 4 个导出字段
  - `投资金额(亿元)` — invest_amount / 10000
  - `招商动态` — 项目动态按日期倒序聚合，序号分段换行（1、日期：内容）
  - `企业诉求` — 诉求按 sort_order 聚合，含类型标签（1、[类型] 内容）
  - `解决措施` — 非空 resolution 聚合（1、措施内容）
- **自定义列**：支持添加数据库不存在的占位列（`custom_N`），用于对齐报表格式
- **导出弹窗**：业务系统导出时弹出选择框：选择模板 + 导出动态范围（全部/最近5条/1个月/3个月），范围过滤仅影响动态聚合列

### 企业诉求导入增强

- **诉求导入配置**：新增 `DemandImportConfig.vue` 后台配置页（导入配置 → 企业诉求导入），路由 `/admin/demand-import-config`
- **按项目ID导入**：模板新增 `项目ID` 列，导入时优先按 ID 匹配项目，`项目名称` 作为回退
- **模板项目预加载**：下载模板时弹出项目选择对话框，默认全选、支持筛选跟进状态、删除/取消勾选，底部显示"已勾选 N/M 个项目"
- **字典下拉校验**：模板中诉求类型、对接单位、状态列添加下拉数据验证

### 分页管理

- **后台分页**：招商动态管理 / 企业诉求管理 — 后端支持 `page`/`page_size` 参数返回 `total`，前端 `el-pagination`（10/20/50/100）
- **业务系统分页**：招商动态 / 企业诉求列表 — 同步添加分页
- 筛选/搜索时自动回到第 1 页

### 样式与交互优化

- 移除全部表格 `stripe` 隔行变色效果，保留 hover 聚焦加深
- `row-focus`（重点跟进行）hover 时显示黄色背景（`#fef7e8` / `#fdf0d5`）
- 移除展开图标右侧多余小点
- 责任单位字段改为非必填（前端验证 + 后端 nullable）

### 数据库变更

| 表 | 变更 |
|---|---|
| `export_template` | 新建 |
| `export_field_config` | +template_id, +is_custom，移除 field_key 唯一约束 |
| `import_field_config_demand` | +project_id 字段 |
| `investment_projects` | responsible_unit_code nullable |
| `demand-dicts` API | 新增返回 follow_statuses |

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
