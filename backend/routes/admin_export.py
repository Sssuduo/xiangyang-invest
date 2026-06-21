import io
from datetime import date
from flask import request, jsonify, send_file
from flask_login import login_required
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from models import ExportFieldConfig, InvestmentProject
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict
from extensions import db
from routes import admin_export_bp


# ============================================================
# 导出字段配置 CRUD
# ============================================================

@admin_export_bp.route('/export/fields', methods=['GET'])
@login_required
def get_export_fields():
    """获取所有导出字段配置"""
    fields = ExportFieldConfig.query.order_by(ExportFieldConfig.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields]})


@admin_export_bp.route('/export/fields', methods=['PUT'])
@login_required
def update_export_fields():
    """批量更新导出字段配置"""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'code': 1, 'message': '请求数据格式错误'}), 400

    for item in data:
        field = ExportFieldConfig.query.get(item.get('id'))
        if field:
            if 'field_label' in item:
                field.field_label = item['field_label']
            if 'is_visible' in item:
                field.is_visible = bool(item['is_visible'])
            if 'column_width' in item:
                field.column_width = int(item['column_width'])
            if 'sort_order' in item:
                field.sort_order = int(item['sort_order'])

    db.session.commit()
    fields = ExportFieldConfig.query.order_by(ExportFieldConfig.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields], 'message': '配置已保存'})


# ============================================================
# 导出预览
# ============================================================

def _build_field_map():
    """构建 field_key -> field_label 的映射"""
    fields = ExportFieldConfig.query.filter_by(is_visible=True).order_by(ExportFieldConfig.sort_order).all()
    return {f.field_key: f for f in fields}


def _resolve_project_row(p):
    """将项目对象解析为展示用 dict（含字典名称）"""
    follow_map = {d.code: d.name for d in FollowStatusDict.query.all()}
    meeting_map = {d.code: d.name for d in MeetingStatusDict.query.all()}
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}
    type_map = {d.code: d.name for d in ProjectTypeDict.query.all()}

    return {
        'order_no': p.order_no,
        'project_name': p.project_name,
        'project_type_code': type_map.get(p.project_type_code, p.project_type_code),
        'invest_enterprise': p.invest_enterprise,
        'enterprise_info': p.enterprise_info or '',
        'project_content': p.project_content or '',
        'invest_amount': float(p.invest_amount) if p.invest_amount else 0,
        'follow_status_code': follow_map.get(p.follow_status_code, p.follow_status_code),
        'meeting_status_code': meeting_map.get(p.meeting_status_code, p.meeting_status_code),
        'recommend_unit_code': org_map.get(p.recommend_unit_code, p.recommend_unit_code or ''),
        'responsible_unit_code': org_map.get(p.responsible_unit_code, p.responsible_unit_code),
        'person_in_charge': p.person_in_charge or '',
        'project_doc': p.project_doc or '',
        'first_contact_date': p.first_contact_date.isoformat() if p.first_contact_date else '',
    }


@admin_export_bp.route('/export/preview', methods=['POST'])
@login_required
def export_preview():
    """导出预览：返回表头+前3条数据"""
    data = request.get_json() or {}
    project_ids = data.get('project_ids', [])
    fields = ExportFieldConfig.query.filter_by(is_visible=True).order_by(ExportFieldConfig.sort_order).all()

    headers = [{'field_key': f.field_key, 'field_label': f.field_label, 'column_width': f.column_width}
               for f in fields]

    q = InvestmentProject.query.filter_by(is_deleted=False)
    if project_ids:
        q = q.filter(InvestmentProject.id.in_(project_ids))
    projects = q.order_by(InvestmentProject.order_no.asc()).limit(3).all()

    rows = [_resolve_project_row(p) for p in projects]

    return jsonify({'code': 0, 'data': {'headers': headers, 'rows': rows, 'total': q.count()}})


@admin_export_bp.route('/export/download', methods=['GET'])
@login_required
def export_download():
    """生成并下载 Excel 文件"""
    ids_str = request.args.get('project_ids', '')
    project_ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()] if ids_str else []

    fields = ExportFieldConfig.query.filter_by(is_visible=True).order_by(ExportFieldConfig.sort_order).all()
    if not fields:
        return jsonify({'code': 1, 'message': '未配置导出字段'}), 400

    q = InvestmentProject.query.filter_by(is_deleted=False)
    if project_ids:
        q = q.filter(InvestmentProject.id.in_(project_ids))
    projects = q.order_by(InvestmentProject.order_no.asc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = '招商项目库'

    # 样式
    header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1A3A5C', end_color='1A3A5C', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_font = Font(name='微软雅黑', size=10)
    cell_align = Alignment(vertical='center', wrap_text=True)
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
        # 列宽（像素→字符近似：/7）
        ws.column_dimensions[get_column_letter(col_idx)].width = field.column_width / 7

    # 写入数据行
    for row_idx, p in enumerate(projects, 2):
        row_data = _resolve_project_row(p)
        for col_idx, field in enumerate(fields, 1):
            val = row_data.get(field.field_key, '')
            if isinstance(val, date):
                val = val.isoformat()
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = cell_font
            cell.alignment = cell_align
            cell.border = thin_border

    # 冻结首行
    ws.freeze_panes = 'A2'

    # 输出到 BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='招商项目库.xlsx'
    )
