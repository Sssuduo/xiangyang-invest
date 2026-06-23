# V8.0 更新日志 — 项目/动态标签系统

> 提交：`f474306` | 日期：2026-06-23

---

## 一、标签字典系统

### 1.1 数据模型（`backend/models.py`）

新增两个字典模型：

| 模型 | 表名 | 字段 |
|---|---|---|
| `ProjectTagDict` | `project_tag_dict` | id, code, name, sort_order, is_active |
| `ActivityTagDict` | `activity_tag_dict` | id, code, name, sort_order, is_active |

`InvestmentProject` 和 `InvestmentActivity` 各增加 `tags` 字段（TEXT，存储 JSON 数组，默认 `[]`）。

### 1.2 字典注册（`backend/routes/admin_dict.py`）

`DICT_REGISTRY` 新增：
- `'project_tags': (ProjectTagDict, [...], False)` — 无颜色字段
- `'activity_tags': (ActivityTagDict, [...], False)` — 无颜色字段

两个类型复用泛型 CRUD API，无需额外端点。

### 1.3 种子数据（`backend/seed_data.py`）

| 字典 | code | name |
|---|---|---|
| 项目标签 | `tag_shipin` | 食品企业走进农高区 |
| 动态标签 | `activity_tag_waichu` | 外出考察 |
| 动态标签 | `activity_tag_daofang` | 到访接待 |
| 动态标签 | `activity_tag_shipin` | 食品企业走进农高区活动 |
| 动态标签 | `activity_tag_diaodu` | 调度推进 |

迁移 SQL：`ALTER TABLE investment_projects ADD COLUMN tags TEXT DEFAULT '[]'`  
迁移 SQL：`ALTER TABLE investment_activities ADD COLUMN tags TEXT DEFAULT '[]'`

---

## 二、标签 CRUD 集成

### 2.1 管理端 API（`backend/routes/admin_investment.py`）

- `GET /api/admin/investment/dicts` 返回值新增 `project_tags`、`activity_tags`
- `POST /api/admin/investment/projects` 接收 `tags` 列表 → JSON 序列化存库
- `PUT /api/admin/investment/projects/<id>` `updatable_fields` 增加 `tags`

### 2.2 动态 API（`backend/routes/admin_activity.py`）

- `POST /api/admin/activity/activities` 接收 `tags` 列表
- `PUT /api/admin/activity/activities/<id>` `updatable_fields` 增加 `tags`

### 2.3 公开 API（`backend/routes/api.py`）

- `GET /api/investment/projects` 返回每个项目附加 `tag_names`（已解析的标签名称数组）

---

## 三、标签筛选

### 3.1 后端

- `GET /api/admin/activity/activities?tags=code1,code2` — 多选并集（OR）筛选
- `GET /api/investment/activities?tags=code1,code2` — 同上（公开接口）

使用 LIKE 匹配 JSON 数组中的 code 值实现。

### 3.2 前端

- **ActivityList.vue**（管理端）— 筛选栏新增标签多选下拉框（`collapse-tags` 折叠显示），多选时以逗号拼接传参
- **ActivityView.vue**（公开端）— 同上

---

## 四、前端表单改动

所有项目/动态的创建/编辑表单均新增标签多选组件：

| 页面 | 组件 | 位置 |
|---|---|---|
| `InvestmentEdit.vue` | 管理端-项目编辑页 | "状态与分配"分区后 |
| `InvestmentList.vue` | 管理端-项目抽屉 | "对接信息"分区后 |
| `InvestmentView.vue` | 公开端-项目抽屉 | "对接信息"分区后 |
| `ActivityList.vue` | 管理端-动态抽屉 | 附件上传后 |
| `ActivityTimelineDrawer.vue` | 公开端-动态弹窗 | 附件上传后 |
| `ActivityView.vue` | 公开端-动态抽屉 | 附件上传后 |

模式：`el-select` + `multiple` + 从对应字典加载选项 + `collapse-tags` 折叠显示。

---

## 五、前端展示改动

### 5.1 列表列

| 页面 | 展示方式 |
|---|---|
| `InvestmentList.vue` | `resolveName('project_tags', code)` → el-tag |
| `InvestmentView.vue` | API 返回的 `tag_names` → el-tag |
| `ActivityList.vue` | `getTagName(code)` → el-tag |
| `ActivityView.vue` | `getTagName(code)` → el-tag |

### 5.2 详情抽屉

| 抽屉 | 展示方式 |
|---|---|
| `ProjectDrawer.vue` | 读取 `project._tagNames`（父组件预解析）→ el-tag 列表 |
| `ActivityDrawer.vue` | 读取 `activity._tagNames`（父组件预解析）→ el-tag 列表 |

### 5.3 字典配置

`DictConfig.vue` 新增两个 Tab：**项目标签**、**动态标签**，支持完整的增删改排序。

---

## 六、其他修复

- `responsible_unit_code` 从必填字段移除（`admin_investment.py` create_project），改为 `data.get('responsible_unit_code', '')`，与模型 `nullable=True` 和前端 `required: false` 保持一致

---

## 七、涉及文件清单

| 文件 | 变更类型 |
|---|---|
| `backend/models.py` | 新增 2 个模型 + 2 列 + to_dict |
| `backend/seed_data.py` | 迁移 + 种子数据 |
| `backend/routes/admin_dict.py` | DICT_REGISTRY 注册 |
| `backend/routes/admin_investment.py` | get_dicts / create / update |
| `backend/routes/admin_activity.py` | create / update / list 筛选 |
| `backend/routes/api.py` | 公开列表 + tag_names 解析 + 筛选 |
| `frontend/src/views/admin/DictConfig.vue` | 新增 Tab |
| `frontend/src/views/admin/InvestmentEdit.vue` | 标签选择器 |
| `frontend/src/views/admin/InvestmentList.vue` | 抽屉 + 列表列 + 详情 |
| `frontend/src/views/InvestmentView.vue` | 抽屉 + 列表列 + 详情 |
| `frontend/src/views/admin/ActivityList.vue` | 抽屉 + 列表列 + 详情 + 筛选 |
| `frontend/src/views/ActivityView.vue` | 抽屉 + 列表列 + 详情 + 筛选 |
| `frontend/src/components/investment/ActivityTimelineDrawer.vue` | 弹窗标签选择器 |
| `frontend/src/components/investment/ProjectDrawer.vue` | 标签展示 |
| `frontend/src/components/investment/ActivityDrawer.vue` | 标签展示 |

**共 17 个文件，+2996 行，-128 行。**
