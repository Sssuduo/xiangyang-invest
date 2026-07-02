"""在建项目库 — 管理端 API"""
import json
from datetime import date, datetime, timedelta
from flask import request, jsonify
from models import (
    ConstructionProject, WorkProgress, ProjectIssue, WorkRoadmapItem,
    ConstructionProjectTypeDict, DispatchStatusDict,
    IssueTypeDict, ResolutionStatusDict, OrganizationDict, Staff
)
from extensions import db
from routes import admin_construction_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes



def _safe_date_str(val):
    """安全转换为日期字符串（YYYY-MM-DD），兼容 date 对象和字符串"""
    if not val:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    return str(val)[:10] if val else ''


def _parse_date(val):
    """将日期字符串转为 date 对象，兼容 YYYY-MM 和 YYYY-MM-DD 格式"""
    if not val:
        return None
    try:
        # 月份选择器发送 "YYYY-MM" 格式，补齐为完整日期
        if isinstance(val, str) and len(val) == 7 and val[4] == '-':
            val = val + '-01'
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _renumber_projects():
    """将未删除项目的 order_no 从 1 开始连续编号（按当前 order_no 排序）"""
    projects = ConstructionProject.query \
        .filter_by(is_deleted=False) \
        .order_by(ConstructionProject.order_no.asc(),
                  ConstructionProject.id.asc()) \
        .all()
    for i, p in enumerate(projects, 1):
        p.order_no = i
    db.session.flush()


# ============================================================
# 字典
# ============================================================

@admin_construction_bp.route('/construction/dicts', methods=['GET'])
@dual_login_required
def get_dicts():
    """返回在建项目相关的所有字典"""
    project_types = ConstructionProjectTypeDict.query \
        .filter_by(is_active=True) \
        .order_by(ConstructionProjectTypeDict.sort_order) \
        .all()
    dispatch_statuses = DispatchStatusDict.query \
        .filter_by(is_active=True) \
        .order_by(DispatchStatusDict.sort_order) \
        .all()
    issue_types = IssueTypeDict.query \
        .filter_by(is_active=True) \
        .order_by(IssueTypeDict.sort_order) \
        .all()
    resolution_statuses = ResolutionStatusDict.query \
        .filter_by(is_active=True) \
        .order_by(ResolutionStatusDict.sort_order) \
        .all()
    organizations = OrganizationDict.query \
        .filter_by(is_active=True) \
        .order_by(OrganizationDict.sort_order) \
        .all()

    staff_list = Staff.query.filter_by(is_active=True).order_by(Staff.sort_order).all()

    return jsonify({'code': 0, 'data': {
        'project_types': [d.to_dict() for d in project_types],
        'dispatch_statuses': [d.to_dict() for d in dispatch_statuses],
        'issue_types': [d.to_dict() for d in issue_types],
        'resolution_statuses': [d.to_dict() for d in resolution_statuses],
        'organizations': [d.to_dict() for d in organizations],
        'staff': [d.to_dict() for d in staff_list]
    }})


# ============================================================
# 辅助：字典名称解析
# ============================================================

def _resolve_project_names(projects):
    """为项目列表批量解析字典 code → display_name"""
    if not projects:
        return

    # 预加载字典映射
    ptype_map = {d.code: d.name for d in ConstructionProjectTypeDict.query.all()}
    dispatch_map = {d.code: d.name for d in DispatchStatusDict.query.all()}
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}
    issue_type_map = {d.code: d.name for d in IssueTypeDict.query.all()}
    res_status_map = {d.code: d.name for d in ResolutionStatusDict.query.all()}

    # 预加载 staff 用于专班负责人名称解析
    from models import Staff
    all_leader_ids = set()
    for p in projects:
        if p.team_leader_ids:
            try:
                all_leader_ids.update(json.loads(p.team_leader_ids))
            except Exception:
                pass
    staff_map = {}
    if all_leader_ids:
        staff_map = {s.id: s.name for s in Staff.query.filter(Staff.id.in_(list(all_leader_ids))).all()}

    for p in projects:
        p._project_type_name = ptype_map.get(p.project_type_code, p.project_type_code)
        p._dispatch_status_name = dispatch_map.get(p.dispatch_status_code, p.dispatch_status_code)
        p._responsible_unit_name = org_map.get(p.responsible_unit_code, p.responsible_unit_code or '')
        # 专班负责人名称
        leader_ids = json.loads(p.team_leader_ids) if p.team_leader_ids else []
        p._team_leader_names = [staff_map.get(sid, str(sid)) for sid in leader_ids]
        for iss in (p.issues.all() if hasattr(p, 'issues') else []):
            iss._issue_type_name = issue_type_map.get(iss.issue_type_code, iss.issue_type_code or '')
            iss._resolution_status_name = res_status_map.get(iss.resolution_status_code, iss.resolution_status_code)
            iss._main_department_name = org_map.get(iss.main_department_code, iss.main_department_code or '')


def _build_project_dict(p):
    """构建单个项目的完整字典（含子表）"""
    return {
        'id': p.id,
        'order_no': p.order_no,
        'project_name': p.project_name,
        'project_type_code': p.project_type_code,
        'project_type_name': getattr(p, '_project_type_name', p.project_type_code),
        'dispatch_status_code': p.dispatch_status_code,
        'dispatch_status_name': getattr(p, '_dispatch_status_name', p.dispatch_status_code),
        'construction_content': p.construction_content or '',
        'work_roadmap_items': [
            {
                'id': wri.id,
                'sort_order': wri.sort_order,
                'content': wri.content,
                'planned_date': wri.planned_date.isoformat() if wri.planned_date else None,
                'actual_date': wri.actual_date.isoformat() if wri.actual_date else None,
                'status': wri.status,
                'is_delayed': wri.is_delayed,
                'delay_reason': wri.delay_reason or '',
                'cancel_reason': wri.cancel_reason or '',
            } for wri in (p.work_roadmap_items.all() if hasattr(p, 'work_roadmap_items') else [])
        ],
        'construction_unit': p.construction_unit or '',
        'responsible_unit_code': p.responsible_unit_code or '',
        'responsible_unit_name': getattr(p, '_responsible_unit_name', p.responsible_unit_code or ''),
        'responsible_person': p.responsible_person or '',
        'responsible_person_phone': p.responsible_person_phone or '',
        'construction_location': p.construction_location or '',
        'start_date': _safe_date_str(p.start_date),
        'end_date': _safe_date_str(p.end_date),
        'funding_source': p.funding_source or '',
        'wuhua_platform': p.wuhua_platform or '',
        'team_leader_ids': json.loads(p.team_leader_ids) if p.team_leader_ids else [],
        'team_leader_names': getattr(p, '_team_leader_names', []),
        'is_deleted': p.is_deleted,
        'work_progresses': [
            {
                'id': wp.id,
                'start_date': wp.start_date.isoformat() if wp.start_date else None,
                'end_date': wp.end_date.isoformat() if wp.end_date else None,
                'content': wp.content,
                'created_at': wp.created_at.isoformat() if wp.created_at else None,
            } for wp in (p.work_progresses.all() if hasattr(p, 'work_progresses') else [])
        ],
        'issues': [
            {
                'id': iss.id,
                'issue_type_code': iss.issue_type_code or '',
                'issue_type_name': getattr(iss, '_issue_type_name', iss.issue_type_code or ''),
                'issue_description': iss.issue_description or '',
                'resolution_status_code': iss.resolution_status_code,
                'resolution_status_name': getattr(iss, '_resolution_status_name', iss.resolution_status_code),
                'resolution_note': iss.resolution_note or '',
                'main_department_code': iss.main_department_code or '',
                'main_department_name': getattr(iss, '_main_department_name', iss.main_department_code or ''),
                'created_at': iss.created_at.isoformat() if iss.created_at else None,
            } for iss in (p.issues.all() if hasattr(p, 'issues') else [])
        ],
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
    }


# ============================================================
# 最大序号
# ============================================================

@admin_construction_bp.route('/construction/max-order-no', methods=['GET'])
@dual_login_required
def max_order_no():
    """返回当前最大顺序号"""
    max_no = db.session.query(db.func.max(ConstructionProject.order_no)) \
        .filter_by(is_deleted=False).scalar()
    return jsonify({'code': 0, 'data': {'max_order_no': max_no or 0}})


# ============================================================
# 列表
# ============================================================

@admin_construction_bp.route('/construction/projects', methods=['GET'])
@dual_login_required
def list_projects():
    """查询在建项目列表"""
    q = ConstructionProject.query.filter_by(is_deleted=False)

    # 模糊搜索 — 项目名称 / 建设内容
    search = request.args.get('search', '').strip()
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            ConstructionProject.project_name.ilike(like),
            ConstructionProject.construction_content.ilike(like)
        ))

    # 建设单位模糊搜索
    construction_unit = request.args.get('construction_unit', '').strip()
    if construction_unit:
        q = q.filter(ConstructionProject.construction_unit.ilike(f'%{construction_unit}%'))

    # 调度状态筛选
    dispatch_status = request.args.get('dispatch_status', '').strip()
    if dispatch_status:
        q = q.filter(ConstructionProject.dispatch_status_code == dispatch_status)

    # 项目类型筛选
    project_type = request.args.get('project_type', '').strip()
    if project_type:
        q = q.filter(ConstructionProject.project_type_code == project_type)

    # 责任单位筛选
    responsible_unit = request.args.get('responsible_unit', '').strip()
    if responsible_unit:
        q = q.filter(ConstructionProject.responsible_unit_code == responsible_unit)

    # 近期更新筛选：项目自身 / 工作进展 任一在 N 天内有更新
    recent_progress_days = request.args.get('recent_progress_days', '').strip()
    if recent_progress_days:
        try:
            days = int(recent_progress_days)
            cutoff = datetime.utcnow() - timedelta(days=days)
            q = q.filter(db.or_(
                ConstructionProject.last_updated_at >= cutoff,
                ConstructionProject.work_progresses.any(WorkProgress.created_at >= cutoff)
            ))
        except (ValueError, TypeError):
            pass

    q = q.order_by(ConstructionProject.order_no.asc(),
                   ConstructionProject.created_at.desc())

    # 注意：lazy='dynamic' 的关系不支持 selectinload/joinedload 预加载，
    # 使用 .all() 会在序列化时按需查询子表，性能上会有 N+1 查询，
    # 但由于 ConstructionProject 规模可控（一般 < 500 条），影响可接受。
    projects = q.all()
    _resolve_project_names(projects)

    return jsonify({'code': 0, 'data': [_build_project_dict(p) for p in projects]})


# ============================================================
# 创建
# ============================================================

@admin_construction_bp.route('/construction/projects', methods=['POST'])
@dual_login_required
@visitor_block
def create_project():
    """创建在建项目"""
    data = request.get_json(silent=True) or {}

    # 必填校验
    project_name = (data.get('project_name') or '').strip()
    project_type_code = (data.get('project_type_code') or '').strip()
    if not project_name:
        return jsonify({'code': 1, 'message': '请输入项目名称'}), 400
    if not project_type_code:
        return jsonify({'code': 1, 'message': '请选择项目类型'}), 400

    # 自动分配序号（如果前端未指定或为 0）
    req_order_no = data.get('order_no', 0)
    if not req_order_no or req_order_no <= 0:
        max_no = db.session.query(db.func.max(ConstructionProject.order_no)) \
            .filter(ConstructionProject.is_deleted == False).scalar() or 0
        req_order_no = max_no + 1

    project = ConstructionProject(
        order_no=req_order_no,
        project_name=project_name,
        project_type_code=project_type_code,
        dispatch_status_code=(data.get('dispatch_status_code') or 'dispatching').strip(),
        construction_content=(data.get('construction_content') or '').strip(),
        construction_unit=(data.get('construction_unit') or '').strip(),
        responsible_unit_code=(data.get('responsible_unit_code') or '').strip(),
        responsible_person=(data.get('responsible_person') or '').strip(),
        responsible_person_phone=(data.get('responsible_person_phone') or '').strip(),
        construction_location=(data.get('construction_location') or '').strip(),
        start_date=((data.get('start_date') or '').strip()[:10] or ''),
        end_date=((data.get('end_date') or '').strip()[:10] or ''),
        funding_source=(data.get('funding_source') or '').strip(),
        wuhua_platform=(data.get('wuhua_platform') or '').strip(),
        team_leader_ids=json.dumps(data.get('team_leader_ids', []), ensure_ascii=False) if isinstance(data.get('team_leader_ids'), list) else (data.get('team_leader_ids') or ''),
    )
    db.session.add(project)
    db.session.flush()  # 获取 project.id

    # 子表：工作进展
    for wp_data in data.get('work_progresses') or []:
        start_date = _parse_date(wp_data.get('start_date'))
        end_date = _parse_date(wp_data.get('end_date'))
        content = (wp_data.get('content') or '').strip()
        if content and start_date and end_date:
            wp_files = wp_data.get('files') or []
            db.session.add(WorkProgress(
                project_id=project.id,
                start_date=start_date,
                end_date=end_date,
                content=content,
                files=json.dumps(wp_files, ensure_ascii=False)
            ))

    # 子表：存在问题
    for iss_data in data.get('issues') or []:
        iss_desc = (iss_data.get('issue_description') or '').strip()
        if iss_desc:
            db.session.add(ProjectIssue(
                project_id=project.id,
                issue_type_code=(iss_data.get('issue_type_code') or '').strip(),
                issue_description=iss_desc,
                resolution_status_code=(iss_data.get('resolution_status_code') or 'pending').strip(),
                resolution_note=(iss_data.get('resolution_note') or '').strip(),
                main_department_code=(iss_data.get('main_department_code') or '').strip()
            ))

    # 子表：工作路径图
    for wri_data in data.get('work_roadmap_items') or []:
        content = (wri_data.get('content') or '').strip()
        if content:
            db.session.add(WorkRoadmapItem(
                project_id=project.id,
                sort_order=wri_data.get('sort_order', 0),
                content=content,
                planned_date=_parse_date(wri_data.get('planned_date')),
                actual_date=_parse_date(wri_data.get('actual_date')),
                status=(wri_data.get('status') or 'pending').strip(),
                is_delayed=wri_data.get('is_delayed', False),
                delay_reason=(wri_data.get('delay_reason') or '').strip(),
                cancel_reason=(wri_data.get('cancel_reason') or '').strip(),
            ))

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        changes = {
            'order_no': (None, str(project.order_no)),
            'project_name': (None, project.project_name),
            'project_type_code': (None, project.project_type_code),
            'dispatch_status_code': (None, project.dispatch_status_code),
            'construction_content': (None, project.construction_content or ''),
            'construction_unit': (None, project.construction_unit or ''),
            'responsible_unit_code': (None, project.responsible_unit_code or ''),
            'responsible_person': (None, project.responsible_person or ''),
            'responsible_person_phone': (None, project.responsible_person_phone or ''),
            'construction_location': (None, project.construction_location or ''),
            'start_date': (None, str(project.start_date) if project.start_date else ''),
            'end_date': (None, str(project.end_date) if project.end_date else ''),
            'funding_source': (None, project.funding_source or ''),
            'wuhua_platform': (None, project.wuhua_platform or ''),
            'team_leader_ids': (None, project.team_leader_ids or ''),
        }
        log_changes('construction_projects', project.id, changes, 'create', user_info)

    db.session.commit()

    _resolve_project_names([project])
    return jsonify({'code': 0, 'data': _build_project_dict(project),
                    'message': '项目已创建'})


# ============================================================
# 详情
# ============================================================

@admin_construction_bp.route('/construction/projects/<int:project_id>', methods=['GET'])
@dual_login_required
def get_project(project_id):
    """获取单个在建项目详情"""
    project = ConstructionProject.query \
        .filter_by(id=project_id, is_deleted=False) \
        .first_or_404()
    _resolve_project_names([project])
    return jsonify({'code': 0, 'data': _build_project_dict(project)})


# ============================================================
# 更新
# ============================================================

@admin_construction_bp.route('/construction/projects/<int:project_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_project(project_id):
    """更新在建项目"""
    project = ConstructionProject.query \
        .filter_by(id=project_id, is_deleted=False) \
        .first_or_404()

    data = request.get_json(silent=True) or {}

    # 必填校验
    project_name = (data.get('project_name') or '').strip()
    project_type_code = (data.get('project_type_code') or '').strip()
    if not project_name:
        return jsonify({'code': 1, 'message': '请输入项目名称'}), 400
    if not project_type_code:
        return jsonify({'code': 1, 'message': '请选择项目类型'}), 400

    # 序号冲突检测
    new_order_no = data.get('order_no', project.order_no)
    if new_order_no != project.order_no:
        conflict = ConstructionProject.query \
            .filter_by(is_deleted=False) \
            .filter(ConstructionProject.id != project.id,
                    ConstructionProject.order_no == new_order_no) \
            .first()
        if conflict:
            if not data.get('force_reorder'):
                return jsonify({
                    'code': 2,
                    'message': f'序号 {new_order_no} 已被项目「{conflict.project_name}」占用',
                    'data': {'conflict_project': conflict.project_name}
                })
            # 强制重排：将 >= 新序号的项目序号 +1
            ConstructionProject.query \
                .filter_by(is_deleted=False) \
                .filter(ConstructionProject.order_no >= new_order_no,
                        ConstructionProject.id != project.id) \
                .update({'order_no': ConstructionProject.order_no + 1},
                        synchronize_session=False)

    # 记录旧值（审计）
    old_values = {
        'order_no': str(project.order_no),
        'project_name': project.project_name,
        'project_type_code': project.project_type_code,
        'dispatch_status_code': project.dispatch_status_code,
        'construction_content': project.construction_content or '',
        'construction_unit': project.construction_unit or '',
        'responsible_unit_code': project.responsible_unit_code or '',
        'responsible_person': project.responsible_person or '',
        'responsible_person_phone': project.responsible_person_phone or '',
        'construction_location': project.construction_location or '',
        'start_date': str(project.start_date) if project.start_date else '',
        'end_date': str(project.end_date) if project.end_date else '',
        'funding_source': project.funding_source or '',
        'wuhua_platform': project.wuhua_platform or '',
        'team_leader_ids': project.team_leader_ids or '',
    }

    # 更新字段
    project.order_no = new_order_no
    project.project_name = project_name
    project.project_type_code = project_type_code
    project.dispatch_status_code = (data.get('dispatch_status_code') or project.dispatch_status_code).strip()
    project.construction_content = (data.get('construction_content') or '').strip()
    project.construction_unit = (data.get('construction_unit') or '').strip()
    project.responsible_unit_code = (data.get('responsible_unit_code') or '').strip()
    project.responsible_person = (data.get('responsible_person') or '').strip()
    project.responsible_person_phone = (data.get('responsible_person_phone') or '').strip()
    project.construction_location = (data.get('construction_location') or '').strip()
    # start_date/end_date 存储为 YYYY-MM-DD 字符串（列类型 String(10)），非必填
    if 'start_date' in data:
        val = (data.get('start_date') or '').strip()
        project.start_date = val[:10] if val else ''
    if 'end_date' in data:
        val = (data.get('end_date') or '').strip()
        project.end_date = val[:10] if val else ''
    project.funding_source = (data.get('funding_source') or '').strip()
    project.wuhua_platform = (data.get('wuhua_platform') or '').strip()
    if 'team_leader_ids' in data:
        val = data['team_leader_ids']
        project.team_leader_ids = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val

    # 同步子表：先删后建
    for wp in WorkProgress.query.filter_by(project_id=project.id).all():
        db.session.delete(wp)
    for iss in ProjectIssue.query.filter_by(project_id=project.id).all():
        db.session.delete(iss)
    for wri in WorkRoadmapItem.query.filter_by(project_id=project.id).all():
        db.session.delete(wri)

    for wp_data in data.get('work_progresses') or []:
        start_date = _parse_date(wp_data.get('start_date'))
        end_date = _parse_date(wp_data.get('end_date'))
        content = (wp_data.get('content') or '').strip()
        if content and start_date and end_date:
            wp_files = wp_data.get('files') or []
            db.session.add(WorkProgress(
                project_id=project.id,
                start_date=start_date,
                end_date=end_date,
                content=content,
                files=json.dumps(wp_files, ensure_ascii=False)
            ))

    for iss_data in data.get('issues') or []:
        iss_desc = (iss_data.get('issue_description') or '').strip()
        if iss_desc:
            db.session.add(ProjectIssue(
                project_id=project.id,
                issue_type_code=(iss_data.get('issue_type_code') or '').strip(),
                issue_description=iss_desc,
                resolution_status_code=(iss_data.get('resolution_status_code') or 'pending').strip(),
                resolution_note=(iss_data.get('resolution_note') or '').strip(),
                main_department_code=(iss_data.get('main_department_code') or '').strip()
            ))

    # 子表：工作路径图
    for wri_data in data.get('work_roadmap_items') or []:
        content = (wri_data.get('content') or '').strip()
        if content:
            db.session.add(WorkRoadmapItem(
                project_id=project.id,
                sort_order=wri_data.get('sort_order', 0),
                content=content,
                planned_date=_parse_date(wri_data.get('planned_date')),
                actual_date=_parse_date(wri_data.get('actual_date')),
                status=(wri_data.get('status') or 'pending').strip(),
                is_delayed=wri_data.get('is_delayed', False),
                delay_reason=(wri_data.get('delay_reason') or '').strip(),
                cancel_reason=(wri_data.get('cancel_reason') or '').strip(),
            ))

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        new_values = {
            'order_no': str(project.order_no),
            'project_name': project.project_name,
            'project_type_code': project.project_type_code,
            'dispatch_status_code': project.dispatch_status_code,
            'construction_content': project.construction_content or '',
            'construction_unit': project.construction_unit or '',
            'responsible_unit_code': project.responsible_unit_code or '',
            'responsible_person': project.responsible_person or '',
            'responsible_person_phone': project.responsible_person_phone or '',
            'construction_location': project.construction_location or '',
            'start_date': str(project.start_date) if project.start_date else '',
            'end_date': str(project.end_date) if project.end_date else '',
            'funding_source': project.funding_source or '',
            'wuhua_platform': project.wuhua_platform or '',
            'team_leader_ids': project.team_leader_ids or '',
        }
        changes = {}
        for k in old_values:
            if old_values[k] != new_values[k]:
                changes[k] = (old_values[k], new_values[k])
        if changes:
            log_changes('construction_projects', project.id, changes, 'update', user_info)

    _renumber_projects()
    db.session.commit()

    _resolve_project_names([project])
    return jsonify({'code': 0, 'data': _build_project_dict(project),
                    'message': '项目已更新'})


# ============================================================
# 删除（软删除）
# ============================================================

@admin_construction_bp.route('/construction/projects/<int:project_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_project(project_id):
    """软删除在建项目"""
    project = ConstructionProject.query \
        .filter_by(id=project_id, is_deleted=False) \
        .first_or_404()
    project.is_deleted = True
    _renumber_projects()
    db.session.commit()

    user_info = get_current_user_info()
    if user_info:
        log_changes('construction_projects', project.id,
                    {'is_deleted': ('False', 'True')}, 'delete', user_info)

    return jsonify({'code': 0, 'message': '项目已删除'})


# ============================================================
# 批量删除
# ============================================================

@admin_construction_bp.route('/construction/projects/batch-delete', methods=['POST'])
@dual_login_required
@visitor_block
def batch_delete_projects():
    """批量软删除在建项目"""
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []

    if not ids:
        return jsonify({'code': 1, 'message': '请选择要删除的项目'}), 400

    deleted = ConstructionProject.query \
        .filter(ConstructionProject.id.in_(ids),
                ConstructionProject.is_deleted == False) \
        .update({'is_deleted': True}, synchronize_session=False)
    _renumber_projects()
    db.session.commit()

    return jsonify({'code': 0, 'message': f'已删除 {deleted} 个项目',
                    'data': {'count': deleted}})


# ============================================================
# 工作进展 CRUD
# ============================================================

def _build_progress_dict(wp):
    """构建工作进展字典（含项目名称）"""
    _files = []
    try:
        _files = json.loads(wp.files or '[]')
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        'id': wp.id,
        'project_id': wp.project_id,
        'project_name': getattr(wp, '_project_name', ''),
        'start_date': wp.start_date.isoformat() if wp.start_date else None,
        'end_date': wp.end_date.isoformat() if wp.end_date else None,
        'content': wp.content,
        'files': _files,
        'created_at': wp.created_at.isoformat() if wp.created_at else None,
        'updated_at': wp.updated_at.isoformat() if wp.updated_at else None,
    }


@admin_construction_bp.route('/construction/progress', methods=['GET'])
@dual_login_required
def list_progress():
    """查询工作进展列表"""
    q = WorkProgress.query.join(
        ConstructionProject,
        WorkProgress.project_id == ConstructionProject.id
    ).filter(ConstructionProject.is_deleted == False)

    project_id = request.args.get('project_id', '').strip()
    if project_id:
        q = q.filter(WorkProgress.project_id == int(project_id))

    search = request.args.get('search', '').strip()
    if search:
        from models import ConstructionProject as CP
        q = q.filter(db.or_(
            WorkProgress.content.ilike(f'%{search}%'),
            CP.project_name.ilike(f'%{search}%')
        ))

    q = q.order_by(WorkProgress.start_date.desc())
    items = q.all()

    # 批量解析项目名称
    project_ids = list(set(wp.project_id for wp in items))
    project_map = {}
    if project_ids:
        projects = ConstructionProject.query.filter(
            ConstructionProject.id.in_(project_ids)
        ).all()
        project_map = {p.id: p.project_name for p in projects}

    for wp in items:
        wp._project_name = project_map.get(wp.project_id, '')

    return jsonify({'code': 0, 'data': [_build_progress_dict(wp) for wp in items]})


@admin_construction_bp.route('/construction/progress', methods=['POST'])
@dual_login_required
@visitor_block
def create_progress():
    """创建工作进展"""
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    start_date = _parse_date(data.get('start_date'))
    end_date = _parse_date(data.get('end_date'))
    content = (data.get('content') or '').strip()

    if not project_id:
        return jsonify({'code': 1, 'message': '请选择所属项目'}), 400
    if not content:
        return jsonify({'code': 1, 'message': '请输入工作进展内容'}), 400
    if not start_date or not end_date:
        return jsonify({'code': 1, 'message': '请选择起止日期'}), 400

    files = data.get('files') or []
    wp = WorkProgress(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        content=content,
        files=json.dumps(files, ensure_ascii=False)
    )
    db.session.add(wp)
    db.session.commit()

    project = ConstructionProject.query.get(project_id)
    wp._project_name = project.project_name if project else ''
    return jsonify({'code': 0, 'data': _build_progress_dict(wp),
                    'message': '工作进展已创建'})


@admin_construction_bp.route('/construction/progress/<int:progress_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_progress(progress_id):
    """更新工作进展"""
    wp = WorkProgress.query.get_or_404(progress_id)
    data = request.get_json(silent=True) or {}

    start_date = _parse_date(data.get('start_date'))
    end_date = _parse_date(data.get('end_date'))
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({'code': 1, 'message': '请输入工作进展内容'}), 400

    if start_date:
        wp.start_date = start_date
    if end_date:
        wp.end_date = end_date
    wp.content = content

    if 'files' in data:
        wp.files = json.dumps(data.get('files') or [], ensure_ascii=False)

    # 支持修改所属项目
    new_project_id = data.get('project_id')
    if new_project_id and new_project_id != wp.project_id:
        wp.project_id = new_project_id

    db.session.commit()

    project = ConstructionProject.query.get(wp.project_id)
    wp._project_name = project.project_name if project else ''
    return jsonify({'code': 0, 'data': _build_progress_dict(wp),
                    'message': '工作进展已更新'})


@admin_construction_bp.route('/construction/progress/<int:progress_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_progress(progress_id):
    """删除工作进展"""
    wp = WorkProgress.query.get_or_404(progress_id)
    db.session.delete(wp)
    db.session.commit()
    return jsonify({'code': 0, 'message': '工作进展已删除'})


# ============================================================
# 调度问题 CRUD
# ============================================================

def _build_issue_dict(iss):
    """构建问题字典（含名称解析）"""
    issue_type_name = getattr(iss, '_issue_type_name', iss.issue_type_code or '')
    res_status_name = getattr(iss, '_resolution_status_name', iss.resolution_status_code)
    main_dept_name = getattr(iss, '_main_department_name', iss.main_department_code or '')
    return {
        'id': iss.id,
        'project_id': iss.project_id,
        'project_name': getattr(iss, '_project_name', ''),
        'issue_type_code': iss.issue_type_code or '',
        'issue_type_name': issue_type_name,
        'issue_description': iss.issue_description or '',
        'resolution_status_code': iss.resolution_status_code,
        'resolution_status_name': res_status_name,
        'resolution_note': iss.resolution_note or '',
        'main_department_code': iss.main_department_code or '',
        'main_department_name': main_dept_name,
        'created_at': iss.created_at.isoformat() if iss.created_at else None,
        'updated_at': iss.updated_at.isoformat() if iss.updated_at else None,
    }


@admin_construction_bp.route('/construction/issues', methods=['GET'])
@dual_login_required
def list_issues():
    """查询存在问题列表"""
    q = ProjectIssue.query.join(
        ConstructionProject,
        ProjectIssue.project_id == ConstructionProject.id
    ).filter(ConstructionProject.is_deleted == False)

    project_id = request.args.get('project_id', '').strip()
    if project_id:
        q = q.filter(ProjectIssue.project_id == int(project_id))

    issue_type = request.args.get('issue_type', '').strip()
    if issue_type:
        q = q.filter(ProjectIssue.issue_type_code == issue_type)

    res_status = request.args.get('resolution_status', '').strip()
    if res_status:
        q = q.filter(ProjectIssue.resolution_status_code == res_status)

    search = request.args.get('search', '').strip()
    if search:
        from models import ConstructionProject as CP
        q = q.filter(db.or_(
            ProjectIssue.issue_description.ilike(f'%{search}%'),
            CP.project_name.ilike(f'%{search}%')
        ))

    q = q.order_by(ProjectIssue.created_at.desc())
    items = q.all()

    # 批量解析
    project_ids = list(set(iss.project_id for iss in items))
    project_map = {}
    if project_ids:
        projects = ConstructionProject.query.filter(
            ConstructionProject.id.in_(project_ids)
        ).all()
        project_map = {p.id: p.project_name for p in projects}

    issue_type_map = {d.code: d.name for d in IssueTypeDict.query.all()}
    res_status_map = {d.code: d.name for d in ResolutionStatusDict.query.all()}
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}

    for iss in items:
        iss._project_name = project_map.get(iss.project_id, '')
        iss._issue_type_name = issue_type_map.get(iss.issue_type_code, iss.issue_type_code or '')
        iss._resolution_status_name = res_status_map.get(iss.resolution_status_code, iss.resolution_status_code)
        iss._main_department_name = org_map.get(iss.main_department_code, iss.main_department_code or '')

    return jsonify({'code': 0, 'data': [_build_issue_dict(iss) for iss in items]})


@admin_construction_bp.route('/construction/issues', methods=['POST'])
@dual_login_required
@visitor_block
def create_issue():
    """创建存在问题"""
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    iss_desc = (data.get('issue_description') or '').strip()

    if not project_id:
        return jsonify({'code': 1, 'message': '请选择所属项目'}), 400
    if not iss_desc:
        return jsonify({'code': 1, 'message': '请输入问题描述'}), 400

    iss = ProjectIssue(
        project_id=project_id,
        issue_type_code=(data.get('issue_type_code') or '').strip(),
        issue_description=iss_desc,
        resolution_status_code=(data.get('resolution_status_code') or 'pending').strip(),
        resolution_note=(data.get('resolution_note') or '').strip(),
        main_department_code=(data.get('main_department_code') or '').strip()
    )
    db.session.add(iss)
    db.session.commit()

    project = ConstructionProject.query.get(project_id)
    iss._project_name = project.project_name if project else ''
    return jsonify({'code': 0, 'data': _build_issue_dict(iss),
                    'message': '问题已创建'})


@admin_construction_bp.route('/construction/issues/<int:issue_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_issue(issue_id):
    """更新存在问题"""
    iss = ProjectIssue.query.get_or_404(issue_id)
    data = request.get_json(silent=True) or {}

    iss_desc = (data.get('issue_description') or '').strip()
    if not iss_desc:
        return jsonify({'code': 1, 'message': '请输入问题描述'}), 400

    iss.issue_type_code = (data.get('issue_type_code') or iss.issue_type_code).strip()
    iss.issue_description = iss_desc
    iss.resolution_status_code = (data.get('resolution_status_code') or iss.resolution_status_code).strip()
    iss.resolution_note = (data.get('resolution_note') or '').strip()
    iss.main_department_code = (data.get('main_department_code') or '').strip()

    new_project_id = data.get('project_id')
    if new_project_id and new_project_id != iss.project_id:
        iss.project_id = new_project_id

    db.session.commit()

    project = ConstructionProject.query.get(iss.project_id)
    iss._project_name = project.project_name if project else ''
    return jsonify({'code': 0, 'data': _build_issue_dict(iss),
                    'message': '问题已更新'})


@admin_construction_bp.route('/construction/issues/<int:issue_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_issue(issue_id):
    """删除存在问题"""
    iss = ProjectIssue.query.get_or_404(issue_id)
    db.session.delete(iss)
    db.session.commit()
    return jsonify({'code': 0, 'message': '问题已删除'})


# ============================================================
# 数据看板 — 统计
# ============================================================

@admin_construction_bp.route('/construction/stats', methods=['GET'])
@dual_login_required
def construction_stats():
    """在建项目数据统计（数据看板）"""
    from sqlalchemy import func

    # 项目类型筛选参数
    project_type = request.args.get('project_type', '').strip()
    dispatch_status = request.args.get('dispatch_status', '').strip()

    # 构建项目查询基类（可选按项目类型 / 调度状态过滤）
    def project_query():
        q = ConstructionProject.query.filter_by(is_deleted=False)
        if project_type:
            codes = [c.strip() for c in project_type.split(',') if c.strip()]
            if len(codes) == 1:
                q = q.filter(ConstructionProject.project_type_code == codes[0])
            elif len(codes) > 1:
                q = q.filter(ConstructionProject.project_type_code.in_(codes))
        if dispatch_status:
            codes = [c.strip() for c in dispatch_status.split(',') if c.strip()]
            if len(codes) == 1:
                q = q.filter(ConstructionProject.dispatch_status_code == codes[0])
            elif len(codes) > 1:
                q = q.filter(ConstructionProject.dispatch_status_code.in_(codes))
        return q

    # ---- 总体概览 ----
    total_projects = project_query().count()
    dispatching_count = project_query().filter(
        ConstructionProject.dispatch_status_code == 'dispatching'
    ).count()
    completed_count = project_query().filter(
        ConstructionProject.dispatch_status_code == 'completed'
    ).count()

    # 涉及责任单位数（去重，非空）
    responsible_units = db.session.query(func.count(func.distinct(
        project_query().with_entities(ConstructionProject.responsible_unit_code).filter(
            ConstructionProject.responsible_unit_code.isnot(None),
            ConstructionProject.responsible_unit_code != ''
        ).subquery().c.responsible_unit_code
    ))).scalar() or 0

    # 工作进展总数（关联 project 表过滤）
    progress_q = WorkProgress.query.join(
        ConstructionProject,
        WorkProgress.project_id == ConstructionProject.id
    ).filter(ConstructionProject.is_deleted == False)
    if project_type:
        progress_q = progress_q.filter(ConstructionProject.project_type_code == project_type)
    total_progress = progress_q.count()

    # 待解决问题数
    issues_q = ProjectIssue.query.join(
        ConstructionProject,
        ProjectIssue.project_id == ConstructionProject.id
    ).filter(ConstructionProject.is_deleted == False)
    if project_type:
        issues_q = issues_q.filter(ConstructionProject.project_type_code == project_type)
    pending_issues = issues_q.filter(ProjectIssue.resolution_status_code == 'pending').count()

    overview = {
        'total_projects': total_projects,
        'dispatching_count': dispatching_count,
        'completed_count': completed_count,
        'responsible_units': responsible_units,
        'total_progress': total_progress,
        'pending_issues': pending_issues
    }

    # ---- 按项目类型分布 ----
    ptype_map = {d.code: d.name for d in ConstructionProjectTypeDict.query.all()}
    dispatch_map = {d.code: d.name for d in DispatchStatusDict.query.all()}

    # 按类型 + 调度状态分组统计
    type_rows = project_query().with_entities(
        ConstructionProject.project_type_code,
        ConstructionProject.dispatch_status_code,
        func.count(ConstructionProject.id)
    ).group_by(
        ConstructionProject.project_type_code,
        ConstructionProject.dispatch_status_code
    ).all()

    # 汇总为 { code: { dispatching: n, completed: n, other: n, count: total } }
    type_stats = {}
    for code, status, cnt in type_rows:
        code = code or '__empty__'
        if code not in type_stats:
            type_stats[code] = {'dispatching': 0, 'completed': 0, 'other': 0, 'count': 0}
        if status == 'dispatching':
            type_stats[code]['dispatching'] += cnt
        elif status == 'completed':
            type_stats[code]['completed'] += cnt
        else:
            type_stats[code]['other'] += cnt
        type_stats[code]['count'] += cnt

    # 查询各类型关联的项目列表（用于悬停提示）
    type_project_rows = project_query().with_entities(
        ConstructionProject.project_type_code,
        ConstructionProject.id,
        ConstructionProject.project_name
    ).filter(
        ConstructionProject.project_type_code.isnot(None),
        ConstructionProject.project_type_code != ''
    ).all()

    type_projects = {}
    for code, pid, pname in type_project_rows:
        if code not in type_projects:
            type_projects[code] = []
        if len(type_projects[code]) < 15:
            if not any(p['id'] == pid for p in type_projects[code]):
                type_projects[code].append({'id': pid, 'name': pname})

    by_type = []
    for code, s in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        clean_code = code if code != '__empty__' else ''
        by_type.append({
            'code': clean_code,
            'name': ptype_map.get(clean_code, '未分类') if code != '__empty__' else '未分类',
            'count': s['count'],
            'dispatching': s['dispatching'],
            'completed': s['completed'],
            'other': s['other'],
            'projects': type_projects.get(clean_code, [])
        })

    # ---- 按责任单位分布（Top 15）----
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}
    unit_rows = project_query().with_entities(
        ConstructionProject.responsible_unit_code,
        func.count(ConstructionProject.id)
    ).filter(
        ConstructionProject.responsible_unit_code.isnot(None),
        ConstructionProject.responsible_unit_code != ''
    ).group_by(ConstructionProject.responsible_unit_code).order_by(
        func.count(ConstructionProject.id).desc()
    ).limit(15).all()

    # 查询各单位的项目类型明细
    unit_codes = [code for code, _ in unit_rows]
    unit_type_rows = []
    if unit_codes:
        unit_type_rows = project_query().with_entities(
            ConstructionProject.responsible_unit_code,
            ConstructionProject.project_type_code,
            func.count(ConstructionProject.id)
        ).filter(
            ConstructionProject.responsible_unit_code.in_(unit_codes)
        ).group_by(
            ConstructionProject.responsible_unit_code,
            ConstructionProject.project_type_code
        ).order_by(
            ConstructionProject.responsible_unit_code,
            func.count(ConstructionProject.id).desc()
        ).all()

    unit_types = {}
    for code, ptype, cnt in unit_type_rows:
        ptype = ptype or '__empty__'
        if code not in unit_types:
            unit_types[code] = []
        unit_types[code].append({
            'name': ptype_map.get(ptype, '未分类') if ptype != '__empty__' else '未分类',
            'code': ptype if ptype != '__empty__' else '',
            'count': cnt
        })

    by_unit = []
    for code, cnt in unit_rows:
        by_unit.append({
            'code': code,
            'name': org_map.get(code, code),
            'count': cnt,
            'types': unit_types.get(code, [])
        })

    # ---- 月度趋势（最近12个月）----
    now = datetime.utcnow()
    twelve_months_ago = now - timedelta(days=365)

    month_rows = project_query().with_entities(
        func.strftime('%Y-%m', ConstructionProject.created_at).label('month'),
        func.count(ConstructionProject.id)
    ).filter(
        ConstructionProject.created_at >= twelve_months_ago
    ).group_by('month').order_by('month').all()

    # 补全缺失的月份为 0
    month_dict = {m: c for m, c in month_rows}
    by_month = []
    cursor = datetime(twelve_months_ago.year, twelve_months_ago.month, 1)
    end = datetime(now.year, now.month, 1)
    while cursor <= end:
        key = cursor.strftime('%Y-%m')
        by_month.append({'month': key, 'count': month_dict.get(key, 0)})
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    # ---- 按调度状态分布（环形图）----
    dispatch_rows = project_query().with_entities(
        ConstructionProject.dispatch_status_code,
        func.count(ConstructionProject.id)
    ).group_by(ConstructionProject.dispatch_status_code).all()

    by_dispatch_status = []
    for code, cnt in dispatch_rows:
        by_dispatch_status.append({
            'code': code,
            'name': dispatch_map.get(code, code),
            'count': cnt
        })

    # ---- 按专班负责人分布 ----
    from models import Staff
    leader_projects = project_query().with_entities(
        ConstructionProject.id,
        ConstructionProject.project_name,
        ConstructionProject.team_leader_ids
    ).all()
    leader_stats = {}
    for pid, pname, tids in leader_projects:
        try:
            leader_ids = json.loads(tids or '[]')
        except (json.JSONDecodeError, TypeError):
            leader_ids = []
        if not leader_ids:
            continue
        for sid in leader_ids:
            if sid not in leader_stats:
                leader_stats[sid] = {'staff_id': sid, 'count': 0, 'projects': []}
            leader_stats[sid]['count'] += 1
            leader_stats[sid]['projects'].append({'id': pid, 'name': pname, 'invest_amount': 0})
    staff_map = {s.id: s.name for s in Staff.query.filter(Staff.id.in_(list(leader_stats.keys()))).all()} if leader_stats else {}
    by_team_leader = []
    for sid, stats in leader_stats.items():
        by_team_leader.append({
            'staff_id': stats['staff_id'],
            'name': staff_map.get(sid, str(sid)),
            'count': stats['count'],
            'projects': stats['projects']
        })
    by_team_leader.sort(key=lambda x: x['count'], reverse=True)

    return jsonify({
        'code': 0,
        'data': {
            'overview': overview,
            'by_type': by_type,
            'by_unit': by_unit,
            'by_month': by_month,
            'by_dispatch_status': by_dispatch_status,
            'by_team_leader': by_team_leader
        }
    })
