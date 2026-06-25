import io
from datetime import date, datetime, timedelta
from flask import request, jsonify, send_file
from flask_login import login_required
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from models import ExportTemplate, ExportFieldConfig, InvestmentProject, EnterpriseDemand, InvestmentActivity
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict
from extensions import db
from routes import admin_export_bp


# ============================================================
# 模板 CRUD
# ============================================================

@admin_export_bp.route('/export/templates', methods=['GET'])
@login_required
def get_templates():
    """列出所有导出模板"""
    entity_type = request.args.get('entity_type', 'investment').strip()
    templates = ExportTemplate.query.filter_by(entity_type=entity_type)\
        .order_by(ExportTemplate.id.asc()).all()
    return jsonify({'code': 0, 'data': [t.to_dict() for t in templates]})


@admin_export_bp.route('/export/templates', methods=['POST'])
@login_required
def create_template():
    """新建导出模板"""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'code': 1, 'message': '模板名称不能为空'}), 400
    entity_type = data.get('entity_type', 'investment')
    template = ExportTemplate(name=data['name'].strip(), entity_type=entity_type)
    db.session.add(template)
    db.session.flush()

    # 从已有模板（排除自身）复制字段配置
    default_template = ExportTemplate.query.filter_by(entity_type=entity_type)\
        .filter(ExportTemplate.id != template.id)\
        .order_by(ExportTemplate.id.asc()).first()
    if default_template:
        default_fields = ExportFieldConfig.query.filter_by(template_id=default_template.id)\
            .order_by(ExportFieldConfig.sort_order).all()
        for f in default_fields:
            db.session.add(ExportFieldConfig(
                template_id=template.id,
                field_key=f.field_key,
                field_label=f.field_label,
                is_visible=True,
                column_width=f.column_width,
                sort_order=f.sort_order
            ))

    db.session.commit()
    return jsonify({'code': 0, 'data': template.to_dict(), 'message': '模板已创建'})


@admin_export_bp.route('/export/templates/<int:template_id>', methods=['PUT'])
@login_required
def update_template(template_id):
    """重命名模板"""
    tpl = ExportTemplate.query.get(template_id)
    if not tpl:
        return jsonify({'code': 1, 'message': '模板不存在'}), 404
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'code': 1, 'message': '模板名称不能为空'}), 400
    tpl.name = data['name'].strip()
    db.session.commit()
    return jsonify({'code': 0, 'data': tpl.to_dict(), 'message': '模板已更新'})


@admin_export_bp.route('/export/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """删除模板及其字段配置"""
    tpl = ExportTemplate.query.get(template_id)
    if not tpl:
        return jsonify({'code': 1, 'message': '模板不存在'}), 404
    # 至少保留一个模板
    remaining = ExportTemplate.query.filter_by(entity_type=tpl.entity_type).count()
    if remaining <= 1:
        return jsonify({'code': 1, 'message': '至少保留一个导出模板'}), 400
    ExportFieldConfig.query.filter_by(template_id=template_id).delete()
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({'code': 0, 'message': '模板已删除'})


# ============================================================
# 导出字段配置 CRUD
# ============================================================

def _get_default_template_id():
    """获取默认模板ID（entity_type='investment' 的第一个模板）"""
    tpl = ExportTemplate.query.filter_by(entity_type='investment').order_by(ExportTemplate.id).first()
    return tpl.id if tpl else 1


@admin_export_bp.route('/export/fields', methods=['GET'])
@login_required
def get_export_fields():
    """获取指定模板的导出字段配置"""
    template_id = request.args.get('template_id', 0, type=int) or _get_default_template_id()
    fields = ExportFieldConfig.query.filter_by(template_id=template_id)\
        .order_by(ExportFieldConfig.sort_order).all()
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields]})


@admin_export_bp.route('/export/fields', methods=['PUT'])
@login_required
def update_export_fields():
    """批量更新导出字段配置"""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'code': 1, 'message': '请求数据格式错误'}), 400

    template_id = None
    saved_ids = set()
    for item in data:
        field_id = item.get('id')
        if field_id and field_id > 0:
            saved_ids.add(field_id)
            field = ExportFieldConfig.query.get(field_id)
            if field:
                template_id = field.template_id
        elif item.get('_new') and item.get('template_id'):
            # 新建字段（自定义列）
            template_id = int(item['template_id'])
            field = ExportFieldConfig(
                template_id=template_id,
                field_key=item.get('field_key', ''),
                field_label=item.get('field_label', ''),
                is_visible=item.get('is_visible', True),
                is_custom=item.get('is_custom', True),
                column_width=item.get('column_width', 120),
                sort_order=item.get('sort_order', 0)
            )
            db.session.add(field)
            continue

        if field:
            if 'field_label' in item:
                field.field_label = item['field_label']
            if 'is_visible' in item:
                field.is_visible = bool(item['is_visible'])
            if 'column_width' in item:
                field.column_width = int(item['column_width'])
            if 'sort_order' in item:
                field.sort_order = int(item['sort_order'])

    # 删除在前端被移除的自定义字段
    if template_id:
        existing_ids = {f.id for f in ExportFieldConfig.query.filter_by(template_id=template_id).all()}
        to_delete = existing_ids - saved_ids
        if to_delete:
            ExportFieldConfig.query.filter(ExportFieldConfig.id.in_(to_delete)).delete(synchronize_session=False)

    db.session.commit()
    fields = ExportFieldConfig.query.filter_by(template_id=template_id)\
        .order_by(ExportFieldConfig.sort_order).all() if template_id else []
    return jsonify({'code': 0, 'data': [f.to_dict() for f in fields], 'message': '配置已保存'})


# ============================================================
# 导出预览
# ============================================================

def _aggregate_activities(project, activity_range=''):
    """聚合项目招商动态，按日期倒序，序号分段"""
    q = InvestmentActivity.query.filter_by(project_id=project.id)
    if activity_range == 'last1m':
        since = datetime.utcnow() - timedelta(days=30)
        q = q.filter(InvestmentActivity.date >= since)
    elif activity_range == 'last3m':
        since = datetime.utcnow() - timedelta(days=90)
        q = q.filter(InvestmentActivity.date >= since)

    q = q.order_by(InvestmentActivity.date.desc())
    if activity_range == 'last5':
        activities = q.limit(5).all()
    else:
        activities = q.all()

    if not activities:
        return ''

    lines = []
    for i, a in enumerate(activities, 1):
        content = a.content or ''
        lines.append(f'{i}、{content}')
    return '\n'.join(lines)


def _aggregate_demands(project):
    """聚合企业诉求，按 sort_order，序号分段"""
    demands = EnterpriseDemand.query.filter_by(project_id=project.id)\
        .order_by(EnterpriseDemand.sort_order.asc()).all()
    if not demands:
        return ''

    type_map = DemandTypeDict.build_display_name_map()
    lines = []
    for i, d in enumerate(demands, 1):
        codes = [c.strip() for c in (d.demand_type_code or '').split(',') if c.strip()]
        type_name = '、'.join([type_map.get(c, c) for c in codes]) if codes else (d.demand_type_code or '诉求')
        content = d.demand_content or ''
        lines.append(f'{i}、[{type_name}] {content}')
    return '\n'.join(lines)


def _aggregate_resolution(project):
    """聚合解决措施，按 sort_order，仅含 resolution 非空的诉求"""
    demands = EnterpriseDemand.query.filter_by(project_id=project.id)\
        .filter(EnterpriseDemand.resolution != '')\
        .filter(EnterpriseDemand.resolution.isnot(None))\
        .order_by(EnterpriseDemand.sort_order.asc()).all()
    if not demands:
        return ''

    lines = []
    for i, d in enumerate(demands, 1):
        lines.append(f'{i}、{d.resolution}')
    return '\n'.join(lines)


def _resolve_project_row(p, activity_range=''):
    """将项目对象解析为展示用 dict（含字典名称 + 聚合字段）"""
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
        'invest_amount_yi': round(float(p.invest_amount) / 10000, 4) if p.invest_amount else 0,
        'follow_status_code': follow_map.get(p.follow_status_code, p.follow_status_code),
        'meeting_status_code': meeting_map.get(p.meeting_status_code, p.meeting_status_code),
        'recommend_unit_code': org_map.get(p.recommend_unit_code, p.recommend_unit_code or ''),
        'responsible_unit_code': org_map.get(p.responsible_unit_code, p.responsible_unit_code),
        'person_in_charge': p.person_in_charge or '',
        'project_doc': p.project_doc or '',
        'investment_plan': p.investment_plan or '',
        'conclusion': p.conclusion or '',
        'first_contact_date': p.first_contact_date.isoformat() if p.first_contact_date else '',
        # 聚合字段
        'activities': _aggregate_activities(p, activity_range),
        'demands': _aggregate_demands(p),
        'resolution': _aggregate_resolution(p),
    }


@admin_export_bp.route('/export/preview', methods=['POST'])
@login_required
def export_preview():
    """导出预览：返回表头+前3条数据"""
    data = request.get_json() or {}
    project_ids = data.get('project_ids', [])
    template_id = data.get('template_id', 0) or _get_default_template_id()

    fields = ExportFieldConfig.query.filter_by(template_id=template_id, is_visible=True)\
        .order_by(ExportFieldConfig.sort_order).all()

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

    template_id = request.args.get('template_id', 0, type=int) or _get_default_template_id()
    activity_range = request.args.get('activity_range', '').strip()
    demand_mode = request.args.get('demand_mode', 'aggregate').strip()  # 'aggregate' | 'row'

    template = ExportTemplate.query.get(template_id)
    template_name = template.name if template else '招商项目库'

    fields = ExportFieldConfig.query.filter_by(template_id=template_id, is_visible=True)\
        .order_by(ExportFieldConfig.sort_order).all()
    if not fields:
        return jsonify({'code': 1, 'message': '未配置导出字段'}), 400

    q = InvestmentProject.query.filter_by(is_deleted=False)
    if project_ids:
        q = q.filter(InvestmentProject.id.in_(project_ids))
    projects = q.order_by(InvestmentProject.order_no.asc()).all()

    # 字典映射
    follow_map = {d.code: d.name for d in FollowStatusDict.query.all()}
    meeting_map = {d.code: d.name for d in MeetingStatusDict.query.all()}
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}
    demand_type_map = DemandTypeDict.build_display_name_map()

    # ---- 样式定义 ----
    title_font = Font(name='微软雅黑', size=14, bold=True, color='1A3A5C')
    title_align = Alignment(horizontal='center', vertical='center')
    header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1A3A5C', end_color='1A3A5C', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_font = Font(name='微软雅黑', size=10)
    cell_align = Alignment(vertical='top', wrap_text=True)
    cell_align_center = Alignment(horizontal='center', vertical='top', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0'),
    )
    title_fill = PatternFill(start_color='F5F7FA', end_color='F5F7FA', fill_type='solid')

    wb = Workbook()
    ws = wb.active
    ws.title = template_name[:31]

    if demand_mode == 'row':
        # ---- 按行导出：诉求拆分为独立行 ----
        project_fields = [f for f in fields if f.field_key not in ('demands', 'resolution')]
        demand_cols = [
            {'field_key': 'demand_type', 'field_label': '诉求类型', 'column_width': 120},
            {'field_key': 'demand_unit', 'field_label': '对接部门', 'column_width': 140},
            {'field_key': 'demand_content', 'field_label': '诉求内容', 'column_width': 400},
            {'field_key': 'demand_resolution', 'field_label': '解决措施', 'column_width': 400},
        ]
        total_cols = len(project_fields) + len(demand_cols)

        # 第1行：标题行（合并单元格）
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
        title_cell = ws.cell(row=1, column=1, value=template_name)
        title_cell.font = title_font
        title_cell.alignment = title_align
        title_cell.fill = title_fill
        for c in range(1, total_cols + 1):
            ws.cell(row=1, column=c).border = thin_border

        # 第2行：表头
        for col_idx, f in enumerate(project_fields, 1):
            cell = ws.cell(row=2, column=col_idx, value=f.field_label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = f.column_width / 7
        for col_idx, dc in enumerate(demand_cols, len(project_fields) + 1):
            cell = ws.cell(row=2, column=col_idx, value=dc['field_label'])
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = dc['column_width'] / 7

        # 数据行 + 合并单元格
        current_row = 3
        for p in projects:
            project_row = _resolve_project_row(p, activity_range=activity_range)
            demands = EnterpriseDemand.query.filter_by(project_id=p.id)\
                .order_by(EnterpriseDemand.sort_order.asc()).all()

            if not demands:
                # 无诉求：一行，项目字段正常填，诉求字段留空
                for col_idx, f in enumerate(project_fields, 1):
                    val = _fmt_cell(project_row.get(f.field_key, ''))
                    cell = ws.cell(row=current_row, column=col_idx, value=val)
                    cell.font = cell_font
                    cell.alignment = cell_align
                    cell.border = thin_border
                for col_idx in range(len(project_fields) + 1, total_cols + 1):
                    cell = ws.cell(row=current_row, column=col_idx, value='')
                    cell.font = cell_font
                    cell.alignment = cell_align_center
                    cell.border = thin_border
                current_row += 1
            else:
                start_row = current_row
                for d in demands:
                    # 项目字段
                    for col_idx, f in enumerate(project_fields, 1):
                        val = _fmt_cell(project_row.get(f.field_key, ''))
                        cell = ws.cell(row=current_row, column=col_idx, value=val)
                        cell.font = cell_font
                        cell.alignment = cell_align
                        cell.border = thin_border
                    # 诉求字段
                    dt_codes = [c.strip() for c in (d.demand_type_code or '').split(',') if c.strip()]
                    demand_data = {
                        'demand_type': '、'.join([demand_type_map.get(c, c) for c in dt_codes]) if dt_codes else '',
                        'demand_unit': org_map.get(d.unit_code, d.unit_code or ''),
                        'demand_content': d.demand_content or '',
                        'demand_resolution': d.resolution or '',
                    }
                    for col_idx, dc in enumerate(demand_cols, len(project_fields) + 1):
                        val = demand_data.get(dc['field_key'], '')
                        cell = ws.cell(row=current_row, column=col_idx, value=val)
                        cell.font = cell_font
                        cell.alignment = cell_align_center if col_idx <= len(project_fields) + 2 else cell_align
                        cell.border = thin_border
                    current_row += 1

                # 合并项目字段单元格（纵向）
                if current_row - start_row > 1:
                    for col_idx in range(1, len(project_fields) + 1):
                        ws.merge_cells(
                            start_row=start_row, start_column=col_idx,
                            end_row=current_row - 1, end_column=col_idx
                        )

        ws.freeze_panes = 'A3'
    else:
        # ---- 聚合导出（原有逻辑） ----
        total_cols = len(fields)

        # 第1行：标题行（合并单元格）
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
        title_cell = ws.cell(row=1, column=1, value=template_name)
        title_cell.font = title_font
        title_cell.alignment = title_align
        title_cell.fill = title_fill
        for c in range(1, total_cols + 1):
            ws.cell(row=1, column=c).border = thin_border

        # 第2行：表头
        for col_idx, field in enumerate(fields, 1):
            cell = ws.cell(row=2, column=col_idx, value=field.field_label)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = field.column_width / 7

        # 数据行
        for row_idx, p in enumerate(projects, 3):
            row_data = _resolve_project_row(p, activity_range=activity_range)
            for col_idx, field in enumerate(fields, 1):
                val = row_data.get(field.field_key, '')
                val = _fmt_cell(val)
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = cell_font
                cell.alignment = cell_align
                cell.border = thin_border

        ws.freeze_panes = 'A3'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{template_name}.xlsx'
    )


def _fmt_cell(val):
    """格式化单元格值"""
    if isinstance(val, date):
        return val.isoformat()
    return val
