"""
V12 数据迁移 — 导入脚本（在生产环境运行）

用法:
    python migration_v12_import.py [数据库路径]

默认数据库路径: instance/app.db（相对于 backend 目录）

功能:
    从 migration_v12_data.json 读取数据，写入生产环境 SQLite 数据库。

策略:
    - 字典表: INSERT OR REPLACE（基于 id）
    - 单位字典: INSERT OR IGNORE（只补不覆盖，保护生产环境已有的单位数据）
    - 导出模板/字段: 按自然键匹配（entity_type / template_id+field_key），不依赖自增ID
    - 在建项目主表/子表: INSERT OR REPLACE（基于 id）
    - 导入字段配置: INSERT OR REPLACE（基于 id）

安全措施:
    - 操作前自动备份原数据库（.backup 后缀）
    - 整个导入在一个事务内，失败自动回滚
    - 不会修改招商项目相关表
"""

import json
import os
import sys
import sqlite3
import shutil
from datetime import datetime


def backup_db(db_path):
    backup_path = db_path + f'.backup_v12_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy2(db_path, backup_path)
    return backup_path


def import_dict_table(cursor, table_name, columns, rows, use_ignore=False):
    """导入字典表 — INSERT OR REPLACE/IGNORE"""
    placeholders = ', '.join(['?' for _ in columns])
    cols_str = ', '.join(columns)
    action = 'OR IGNORE' if use_ignore else 'OR REPLACE'
    sql = f'INSERT {action} INTO {table_name} ({cols_str}) VALUES ({placeholders})'
    count = 0
    for row in rows:
        values = [row.get(c) for c in columns]
        cursor.execute(sql, values)
        count += 1
    return count


def import_export_template(cursor, rows):
    """导入导出模板 — 按 entity_type 匹配，不依赖 id"""
    count = 0
    for row in rows:
        name = row.get('name', '默认导出模板')
        entity_type = row.get('entity_type', 'construction')
        dev_id = row.get('id')

        # 检查生产环境是否已有同 entity_type 的模板
        existing = cursor.execute(
            'SELECT id FROM export_template WHERE entity_type = ?', (entity_type,)
        ).fetchone()

        if existing:
            prod_id = existing[0]
            cursor.execute(
                'UPDATE export_template SET name = ? WHERE id = ?',
                (name, prod_id)
            )
        else:
            # 尝试用开发环境的 id 插入
            cursor.execute(
                'INSERT OR REPLACE INTO export_template (id, name, entity_type) VALUES (?, ?, ?)',
                (dev_id, name, entity_type)
            )
            prod_id = dev_id

        # 返回 (dev_id → prod_id) 映射，供 field_config 使用
        row['_prod_id'] = prod_id
        count += 1
    return count


def import_export_field_config(cursor, rows):
    """导入导出字段配置 — 按 (template_id, field_key) 匹配"""
    count = 0

    # 先获取生产环境的 construction 模板 ID
    ct_template = cursor.execute(
        "SELECT id FROM export_template WHERE entity_type = 'construction'"
    ).fetchone()
    if not ct_template:
        print('    警告: 未找到 construction 导出模板，跳过字段配置导入')
        return 0

    prod_template_id = ct_template[0]

    cols = ['template_id', 'field_key', 'field_label', 'is_visible',
            'is_custom', 'column_width', 'sort_order']

    for row in rows:
        field_key = row.get('field_key', '')
        field_label = row.get('field_label', '')
        is_visible = row.get('is_visible', 1)
        is_custom = row.get('is_custom', 0)
        column_width = row.get('column_width', 120)
        sort_order = row.get('sort_order', 1)

        # 按 (template_id, field_key) 查找已存在的字段
        existing = cursor.execute(
            'SELECT id FROM export_field_config WHERE template_id = ? AND field_key = ?',
            (prod_template_id, field_key)
        ).fetchone()

        if existing:
            cursor.execute(
                'UPDATE export_field_config SET field_label=?, is_visible=?, is_custom=?, '
                'column_width=?, sort_order=? WHERE id=?',
                (field_label, is_visible, is_custom, column_width, sort_order, existing[0])
            )
        else:
            cursor.execute(
                f'INSERT INTO export_field_config ({", ".join(cols)}) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (prod_template_id, field_key, field_label, is_visible, is_custom, column_width, sort_order)
            )
        count += 1
    return count


def import_data_table(cursor, table_name, columns, rows):
    """导入数据表 — INSERT OR REPLACE"""
    placeholders = ', '.join(['?' for _ in columns])
    cols_str = ', '.join(columns)
    sql = f'INSERT OR REPLACE INTO {table_name} ({cols_str}) VALUES ({placeholders})'
    count = 0
    for row in rows:
        values = [row.get(c) for c in columns]
        cursor.execute(sql, values)
        count += 1
    return count


def import_data(db_path, data):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        cursor = conn.cursor()

        # ============================================================
        # 1. 字典表
        # ============================================================
        print('--- 字典表 ---')
        for tbl in ['construction_project_type_dict', 'dispatch_status_dict',
                     'issue_type_dict', 'resolution_status_dict']:
            rows = data.get(tbl, [])
            if rows:
                cols = list(rows[0].keys())
                cnt = import_dict_table(cursor, tbl, cols, rows)
                print(f'  [REPLACE] {tbl}: {cnt} 条')
            else:
                print(f'  [跳过] {tbl}: 无数据')

        # 单位字典 — IGNORE 模式
        print('\n--- 单位字典（共享表） ---')
        org_rows = data.get('organization_dict', [])
        if org_rows:
            cols = list(org_rows[0].keys())
            cnt = import_dict_table(cursor, 'organization_dict', cols, org_rows, use_ignore=True)
            print(f'  [IGNORE] organization_dict: {cnt} 条（已存在则跳过）')

        # ============================================================
        # 2. 导入字段配置
        # ============================================================
        print('\n--- 导入字段配置 ---')
        for tbl in ['import_field_config_construction', 'import_field_config_work_progress']:
            rows = data.get(tbl, [])
            if rows:
                cols = list(rows[0].keys())
                cnt = import_data_table(cursor, tbl, cols, rows)
                print(f'  [REPLACE] {tbl}: {cnt} 条')
            else:
                print(f'  [跳过] {tbl}: 无数据')

        # ============================================================
        # 3. 导出模板 + 字段（按自然键匹配）
        # ============================================================
        print('\n--- 导出配置 ---')
        et_rows = data.get('export_template', [])
        if et_rows:
            cnt = import_export_template(cursor, et_rows)
            print(f'  [UPSERT] export_template: {cnt} 条')

        efc_rows = data.get('export_field_config', [])
        if efc_rows:
            cnt = import_export_field_config(cursor, efc_rows)
            print(f'  [UPSERT] export_field_config: {cnt} 条')

        # ============================================================
        # 4. 在建项目主表
        # ============================================================
        print('\n--- 在建项目数据 ---')
        cp_rows = data.get('construction_projects', [])
        if cp_rows:
            cols = list(cp_rows[0].keys())
            cnt = import_data_table(cursor, 'construction_projects', cols, cp_rows)
            print(f'  [REPLACE] construction_projects: {cnt} 条')

        # ============================================================
        # 5. 在建项目子表
        # ============================================================
        for tbl in ['work_progress', 'project_issues', 'work_roadmap_items']:
            rows = data.get(tbl, [])
            if rows:
                cols = list(rows[0].keys())
                cnt = import_data_table(cursor, tbl, cols, rows)
                print(f'  [REPLACE] {tbl}: {cnt} 条')
            else:
                print(f'  [跳过] {tbl}: 无数据')

        conn.commit()
        print('\n迁移成功 — 所有数据已写入，未影响招商项目数据')

    except Exception as e:
        conn.rollback()
        print(f'\n迁移失败，已回滚: {e}')
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instance', 'app.db')

    if not os.path.exists(db_path):
        print(f'错误: 数据库文件不存在: {db_path}')
        sys.exit(1)

    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migration_v12_data.json')
    if not os.path.exists(data_path):
        print(f'错误: 数据文件不存在: {data_path}')
        print('请先在开发环境运行 migration_v12_export.py 生成数据文件')
        sys.exit(1)

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = sum(len(v) for v in data.values())
    print(f'数据文件: {os.path.basename(data_path)}')
    print(f'目标数据库: {db_path}')
    print(f'共 {len(data)} 张表，{total} 条记录\n')

    # 备份
    backup_path = backup_db(db_path)
    print(f'已备份 → {os.path.basename(backup_path)}\n')

    # 执行
    import_data(db_path, data)


if __name__ == '__main__':
    main()
