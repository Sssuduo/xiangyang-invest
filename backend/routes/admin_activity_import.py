import io
import json
from datetime import datetime
from flask import request, jsonify, send_file
from flask_login import login_required
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from models import ImportFieldConfigActivity, InvestmentActivity, InvestmentProject
from extensions import db
from routes import admin_activity_import_bp


# ============================================================
# 导入字段配置 CRUD
# ============================================================

@admin_activity_import_bp.route('/activity-import/fields', methods=['GET'])
@login_required
def get_import_fields():
    fields = ImportFieldConfigActivity.query.order_by(ImportFieldConfigActivity.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields]})


@admin_activity_import_bp.route('/activity-import/fields', methods=['PUT'])
@login_required
def update_import_fields():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'code': 1, 'message': '格式错误'}), 400
    for item in data:
        f = ImportFieldConfigActivity.query.get(item.get('id'))
        if f:
            if 'field_label' in item:
                f.field_label = item['field_label']
            if 'is_enabled' in item:
                f.is_enabled = bool(item['is_enabled'])
            if 'is_required' in item:
                f.is_required = bool(item['is_required'])
            if 'sort_order' in item:
                f.sort_order = int(item['sort_order'])
    db.session.commit()
    fields = ImportFieldConfigActivity.query.order_by(ImportFieldConfigActivity.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields], 'message': '已保存'})


# ============================================================
# 下载导入模板
# ============================================================

@admin_activity_import_bp.route('/activity-import/template', methods=['GET'])
@login_required
def download_template():
    fields = ImportFieldConfigActivity.query.filter_by(is_enabled=True)\
        .order_by(ImportFieldConfigActivity.sort_order).all()
    if not fields:
        return jsonify({'code': 1, 'message': '未配置导入模板'}), 400

    wb = Workbook()
    ws = wb.active
    ws.title = '动态导入模板'

    header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='3A7ABD', end_color='3A7ABD', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0'),
    )

    # 写入表头
    for col_idx, field in enumerate(fields, 1):
        cell = ws.cell(row=1, column=col_idx, value=field.field_label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = 18

    # 写入示例数据行
    sample = {
        'project_name': '示例项目名称',
        'date': '2026-01-01 10:00',
        'content': '示例动态内容',
        'files': 'https://example.com/doc.pdf',
    }
    for col_idx, field in enumerate(fields, 1):
        val = sample.get(field.field_key, '')
        cell = ws.cell(row=2, column=col_idx, value=val)
        cell.font = Font(name='微软雅黑', size=10, color='909090')
        cell.border = thin_border

    # 必填标记（第3行说明）
    for col_idx, field in enumerate(fields, 1):
        mark = '（必填）' if field.is_required else '（选填）'
        cell = ws.cell(row=3, column=col_idx, value=mark)
        cell.font = Font(name='微软雅黑', size=9, color='C00000' if field.is_required else '909090')

    ws.freeze_panes = 'A4'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='招商动态导入模板.xlsx'
    )


# ============================================================
# 导入预览
# ============================================================

def _get_import_fields():
    return ImportFieldConfigActivity.query.filter_by(is_enabled=True)\
        .order_by(ImportFieldConfigActivity.sort_order).all()


def _resolve_project_id(project_name):
    """根据项目名称查找项目ID"""
    if not project_name:
        return None
    p = InvestmentProject.query.filter_by(project_name=project_name.strip(), is_deleted=False).first()
    return p.id if p else None


def _parse_activity_datetime(val):
    """将字符串解析为 datetime（支持 YYYY-MM-DD HH:MM）"""
    if not val:
        return None
    s = str(val).strip()
    try:
        # 尝试 ISO 格式
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        try:
            # 尝试 YYYY-MM-DD HH:MM
            return datetime.strptime(s, '%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return None


def _validate_activity_row(row_data, field_configs, existing_project_names, row_idx):
    """校验单行数据，返回错误列表"""
    errors = []
    for f in field_configs:
        val = row_data.get(f.field_key, '')
        if f.is_required and (val is None or str(val).strip() == ''):
            errors.append(f'第{row_idx}行：{f.field_label} 为必填项')

    # 校验所属项目是否存在
    pname = str(row_data.get('project_name', '') or '').strip()
    if pname and pname not in existing_project_names:
        errors.append(f'第{row_idx}行：项目「{pname}」在数据库中不存在')

    # 校验日期格式
    date_val = row_data.get('date', '')
    if date_val and str(date_val).strip():
        dt = _parse_activity_datetime(date_val)
        if dt is None:
            errors.append(f'第{row_idx}行：日期格式有误，应为 YYYY-MM-DD HH:MM')

    return errors


@admin_activity_import_bp.route('/activity-import/preview', methods=['POST'])
@login_required
def import_preview():
    """上传 Excel 并返回预览数据"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '未找到上传文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'code': 1, 'message': '未选择文件'}), 400

    try:
        wb = load_workbook(file, read_only=True)
        ws = wb.active
    except Exception:
        return jsonify({'code': 1, 'message': '无法读取文件，请确认是有效的 Excel 文件'}), 400

    # 读取表头
    headers = []
    for cell in ws[1]:
        if cell.value is not None:
            headers.append(str(cell.value).strip())

    # 获取配置的导入字段
    import_fields = _get_import_fields()
    expected_headers = [f.field_label for f in import_fields]

    # 校验表头是否一致
    if headers != expected_headers:
        return jsonify({
            'code': 1,
            'message': '模板有误，请选择正确的导入模板',
            'data': {'expected': expected_headers, 'actual': headers}
        }), 400

    # 构建 field_label -> field_key 映射
    field_map = {f.field_label: f.field_key for f in import_fields}

    # 获取已存在的项目名称
    existing_project_names = set(
        p.project_name for p in InvestmentProject.query.filter_by(is_deleted=False).all()
    )

    # 读取数据行（跳过表头、示例行、标记行）
    rows = []
    all_errors = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
        # 跳过完全空行
        if all(v is None or str(v).strip() == '' for v in row):
            continue

        row_data = {}
        for col_idx, val in enumerate(row):
            if col_idx < len(headers):
                field_label = headers[col_idx]
                field_key = field_map.get(field_label, '')
                str_val = str(val).strip() if val is not None else ''
                row_data[field_key] = str_val

        # 校验
        row_errors = _validate_activity_row(row_data, import_fields, existing_project_names, row_idx)

        all_errors.extend(row_errors)
        rows.append({
            'row': row_idx,
            'data': row_data,
            'errors': row_errors,
            '_valid': len(row_errors) == 0
        })

    # 统计
    valid_count = sum(1 for r in rows if r['_valid'])
    error_count = len(rows) - valid_count

    return jsonify({
        'code': 0,
        'data': {
            'headers': expected_headers,
            'rows': rows,
            'total': len(rows),
            'valid_count': valid_count,
            'error_count': error_count,
            'all_errors': all_errors
        }
    })


# ============================================================
# 执行导入
# ============================================================

@admin_activity_import_bp.route('/activity-import/execute', methods=['POST'])
@login_required
def import_execute():
    """将预览通过的数据写入数据库"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '数据为空'}), 400

    rows = data.get('rows', [])
    if not rows:
        return jsonify({'code': 1, 'message': '无数据可导入'}), 400

    valid_rows = [r for r in rows if r.get('_valid')]
    if not valid_rows:
        return jsonify({'code': 1, 'message': '没有有效数据行'}), 400

    # 预加载项目名称->ID映射
    project_map = {
        p.project_name: p.id
        for p in InvestmentProject.query.filter_by(is_deleted=False).all()
    }

    imported = 0
    for row in valid_rows:
        row_data = row['data']
        project_id = project_map.get(row_data.get('project_name', '').strip())

        if not project_id:
            continue

        activity = InvestmentActivity(
            project_id=project_id,
            date=_parse_activity_datetime(row_data.get('date', '')),
            content=row_data.get('content', ''),
            files=json.dumps(
                [u.strip() for u in str(row_data.get('files', '')).split(',') if u.strip()],
                ensure_ascii=False
            ) if row_data.get('files', '').strip() else '[]'
        )
        db.session.add(activity)
        imported += 1

    db.session.commit()
    return jsonify({'code': 0, 'message': f'成功导入 {imported} 条记录', 'data': {'count': imported}})
