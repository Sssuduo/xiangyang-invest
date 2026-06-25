"""
V12 数据迁移 — 导出脚本（在开发环境运行）

将以下数据导出为 migration_v12_data.json：
  - 在建项目库字典（4张）
  - 单位字典（补充生产环境可能缺失的）
  - 在建项目主表 + 子表（工作进展/存在问题/工作路径图）
  - 导出模板/字段配置（仅 construction 类型）
  - 在建项目/工作进展导入字段配置

不导出招商项目相关数据（生产环境已有新数据）。
"""

import json
import sys
import os

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from sqlalchemy import text


def fetch_all(app, sql, cols=None):
    """执行查询，返回 dict 列表"""
    rows = db.session.execute(text(sql)).fetchall()
    if cols:
        return [dict(zip(cols, row)) for row in rows]
    return [dict(row._mapping) for row in rows]


def export_json(app):
    data = {}

    with app.app_context():
        # ============================================================
        # 1. 在建项目字典表
        # ============================================================
        data['construction_project_type_dict'] = fetch_all(app,
            'SELECT id, code, name, sort_order, is_active FROM construction_project_type_dict ORDER BY sort_order, id')

        data['dispatch_status_dict'] = fetch_all(app,
            'SELECT id, code, name, sort_order, is_active FROM dispatch_status_dict ORDER BY sort_order, id')

        data['issue_type_dict'] = fetch_all(app,
            'SELECT id, code, name, sort_order, is_active FROM issue_type_dict ORDER BY sort_order, id')

        data['resolution_status_dict'] = fetch_all(app,
            'SELECT id, code, name, display_color, sort_order, is_active FROM resolution_status_dict ORDER BY sort_order, id')

        # ============================================================
        # 2. 单位字典（共享表，只补不覆盖）
        # ============================================================
        data['organization_dict'] = fetch_all(app,
            'SELECT id, code, name, sort_order, is_active FROM organization_dict ORDER BY sort_order, id')

        # ============================================================
        # 3. 在建项目主表
        # ============================================================
        cols = [
            'id', 'order_no', 'project_name', 'project_type_code',
            'dispatch_status_code', 'construction_content', 'construction_unit',
            'responsible_unit_code', 'responsible_person', 'responsible_person_phone',
            'is_deleted', 'created_at', 'updated_at'
        ]
        data['construction_projects'] = fetch_all(app,
            f'SELECT {", ".join(cols)} FROM construction_projects WHERE is_deleted = 0 ORDER BY order_no, id',
            cols=cols)

        # ============================================================
        # 4. 在建项目子表
        # ============================================================
        wp_cols = ['id', 'project_id', 'start_date', 'end_date', 'content', 'files', 'created_at', 'updated_at']
        data['work_progress'] = fetch_all(app,
            f'SELECT {", ".join(wp_cols)} FROM work_progress ORDER BY id',
            cols=wp_cols)

        iss_cols = ['id', 'project_id', 'issue_type_code', 'issue_description',
                    'resolution_status_code', 'resolution_note', 'main_department_code',
                    'created_at', 'updated_at']
        data['project_issues'] = fetch_all(app,
            f'SELECT {", ".join(iss_cols)} FROM project_issues ORDER BY id',
            cols=iss_cols)

        wri_cols = ['id', 'project_id', 'sort_order', 'content', 'planned_date',
                    'actual_date', 'status', 'is_delayed', 'delay_reason', 'cancel_reason',
                    'created_at', 'updated_at']
        data['work_roadmap_items'] = fetch_all(app,
            f'SELECT {", ".join(wri_cols)} FROM work_roadmap_items ORDER BY project_id, sort_order, id',
            cols=wri_cols)

        # ============================================================
        # 5. 导出模板（仅 construction）
        # ============================================================
        data['export_template'] = fetch_all(app,
            "SELECT id, name, entity_type FROM export_template WHERE entity_type = 'construction' ORDER BY id")

        ct_ids = [t['id'] for t in data['export_template']]
        if ct_ids:
            placeholders = ','.join(str(i) for i in ct_ids)
            efc_cols = ['id', 'template_id', 'field_key', 'field_label', 'is_visible',
                        'is_custom', 'column_width', 'sort_order']
            data['export_field_config'] = fetch_all(app,
                f'SELECT {", ".join(efc_cols)} FROM export_field_config '
                f'WHERE template_id IN ({placeholders}) ORDER BY sort_order, id',
                cols=efc_cols)
        else:
            data['export_field_config'] = []

        # ============================================================
        # 6. 在建项目导入字段配置
        # ============================================================
        ic_cols = ['id', 'field_key', 'field_label', 'is_enabled', 'is_required',
                   'sort_order', 'created_at', 'updated_at']
        data['import_field_config_construction'] = fetch_all(app,
            f'SELECT {", ".join(ic_cols)} FROM import_field_config_construction ORDER BY sort_order, id',
            cols=ic_cols)

        data['import_field_config_work_progress'] = fetch_all(app,
            f'SELECT {", ".join(ic_cols)} FROM import_field_config_work_progress ORDER BY sort_order, id',
            cols=ic_cols)

    return data


def main():
    app = create_app()
    data = export_json(app)

    # 统计
    counts = {k: len(v) for k, v in data.items()}
    total = sum(counts.values())

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migration_v12_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f'导出完成 → {out_path}')
    print(f'共 {len(data)} 张表，{total} 条记录:')
    for tbl, cnt in counts.items():
        print(f'  {tbl}: {cnt} 条')


if __name__ == '__main__':
    main()
