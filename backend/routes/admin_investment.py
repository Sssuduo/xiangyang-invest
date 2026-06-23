from datetime import date
from flask import request, jsonify
from models import InvestmentProject, EnterpriseDemand
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict
from extensions import db
from routes import admin_investment_bp
from routes.business_auth import dual_login_required


def _parse_date(val):
    """将字符串或 None 转为 date 对象"""
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


# ============================================================
# 字典数据
# ============================================================

@admin_investment_bp.route('/investment/dicts', methods=['GET'])
@dual_login_required
def get_dicts():
    """获取所有字典数据"""
    return jsonify({
        'code': 0,
        'data': {
            'follow_statuses': [d.to_dict() for d in FollowStatusDict.query.order_by(FollowStatusDict.sort_order).all()],
            'meeting_statuses': [d.to_dict() for d in MeetingStatusDict.query.order_by(MeetingStatusDict.sort_order).all()],
            'organizations': [d.to_dict() for d in OrganizationDict.query.filter_by(is_active=True).order_by(OrganizationDict.sort_order).all()],
            'project_types': [d.to_dict() for d in ProjectTypeDict.query.filter_by(is_active=True).order_by(ProjectTypeDict.sort_order).all()],
            'demand_types': [d.to_dict() for d in DemandTypeDict.query.filter_by(is_active=True).order_by(DemandTypeDict.sort_order).all()]
        }
    })


@admin_investment_bp.route('/investment/max-order-no', methods=['GET'])
@dual_login_required
def get_max_order_no():
    """获取当前最大的顺序号"""
    max_no = db.session.query(db.func.max(InvestmentProject.order_no))\
        .filter_by(is_deleted=False).scalar() or 0
    return jsonify({'code': 0, 'data': {'max_order_no': max_no}})


# ============================================================
# 招商项目 CRUD
# ============================================================

@admin_investment_bp.route('/investment/projects', methods=['GET'])
@dual_login_required
def list_projects():
    """项目列表（含搜索/筛选）"""
    search = request.args.get('search', '').strip()
    follow_status = request.args.get('follow_status', '').strip()
    meeting_status = request.args.get('meeting_status', '').strip()
    project_type = request.args.get('project_type', '').strip()

    q = InvestmentProject.query.filter_by(is_deleted=False)

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            InvestmentProject.project_name.ilike(like),
            InvestmentProject.invest_enterprise.ilike(like),
            InvestmentProject.project_content.ilike(like),
            InvestmentProject.person_in_charge.ilike(like)
        ))

    if follow_status:
        q = q.filter_by(follow_status_code=follow_status)
    if meeting_status:
        q = q.filter_by(meeting_status_code=meeting_status)
    if project_type:
        q = q.filter_by(project_type_code=project_type)

    # 排序：重点跟进优先 → 顺序号升序
    q = q.order_by(
        db.case((InvestmentProject.follow_status_code == 'follow_focus', 0), else_=1),
        InvestmentProject.order_no.asc(),
        InvestmentProject.created_at.desc()
    )

    projects = q.all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in projects]})


@admin_investment_bp.route('/investment/projects', methods=['POST'])
@dual_login_required
def create_project():
    """新建项目"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 必填字段校验
    required = ['project_name', 'invest_enterprise', 'enterprise_info', 'project_content',
                'follow_status_code', 'responsible_unit_code', 'project_type_code']
    for field in required:
        if not data.get(field):
            return jsonify({'code': 1, 'message': f'{field} 为必填字段'}), 400

    project = InvestmentProject(
        order_no=data.get('order_no', 0),
        project_name=data['project_name'],
        invest_enterprise=data['invest_enterprise'],
        enterprise_info=data['enterprise_info'],
        project_content=data['project_content'],
        invest_amount=data['invest_amount'],
        follow_status_code=data['follow_status_code'],
        meeting_status_code=data.get('meeting_status_code', 'not_meeting'),
        recommend_unit_code=data.get('recommend_unit_code', ''),
        responsible_unit_code=data['responsible_unit_code'],
        project_type_code=data['project_type_code'],
        person_in_charge=data.get('person_in_charge', ''),
        project_doc=data.get('project_doc', ''),
        investment_plan=data.get('investment_plan', ''),
        conclusion=data.get('conclusion', ''),
        first_contact_date=_parse_date(data.get('first_contact_date'))
    )

    db.session.add(project)
    db.session.flush()  # 获取 project.id

    # 创建企业诉求
    for i, d in enumerate(data.get('demands', []) or []):
        if d.get('demand_content', '').strip():
            db.session.add(EnterpriseDemand(
                project_id=project.id,
                demand_type_code=d.get('demand_type_code', ''),
                demand_content=d['demand_content'],
                resolution=d.get('resolution', ''),
                unit_code=d.get('unit_code', ''),
                status=d.get('status', 'pending'),
                sort_order=i + 1
            ))

    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_dict(), 'message': '项目创建成功'})


@admin_investment_bp.route('/investment/projects/<int:project_id>', methods=['GET'])
@dual_login_required
def get_project(project_id):
    """获取项目详情（含字典名称解析）"""
    project = InvestmentProject.query.filter_by(id=project_id, is_deleted=False).first_or_404()
    data = project.to_dict()

    # 解析字典名称
    follow_map = {d.code: d for d in FollowStatusDict.query.all()}
    meeting_map = {d.code: d for d in MeetingStatusDict.query.all()}
    org_map = {d.code: d for d in OrganizationDict.query.all()}
    type_map = {d.code: d for d in ProjectTypeDict.query.all()}
    demand_type_map = {d.code: d for d in DemandTypeDict.query.all()}
    demand_display_map = DemandTypeDict.build_display_name_map()

    fu = follow_map.get(project.follow_status_code)
    data['follow_status_name'] = fu.name if fu else ''
    data['follow_status_color'] = fu.display_color if fu else '#909399'
    mu = meeting_map.get(project.meeting_status_code)
    data['meeting_status_name'] = mu.name if mu else ''
    data['meeting_status_color'] = mu.display_color if mu else '#909399'
    ou = org_map.get(project.recommend_unit_code)
    data['recommend_unit_name'] = ou.name if ou else ''
    ou2 = org_map.get(project.responsible_unit_code)
    data['responsible_unit_name'] = ou2.name if ou2 else ''
    tu = type_map.get(project.project_type_code)
    data['project_type_name'] = tu.name if tu else ''

    # 诉求字典名称（二级显示：一级：二级）
    for d in data.get('demands', []) or []:
        d['demand_type_name'] = demand_display_map.get(d.get('demand_type_code'), '')
        du = org_map.get(d.get('unit_code'))
        d['unit_name'] = du.name if du else ''

    return jsonify({'code': 0, 'data': data})


@admin_investment_bp.route('/investment/projects/<int:project_id>', methods=['PUT'])
@dual_login_required
def update_project(project_id):
    """更新项目"""
    project = InvestmentProject.query.filter_by(id=project_id, is_deleted=False).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 检查 order_no 冲突
    new_order_no = data.get('order_no')
    force_reorder = data.pop('force_reorder', False)
    if new_order_no is not None and new_order_no != project.order_no:
        conflict = InvestmentProject.query.filter(
            InvestmentProject.id != project_id,
            InvestmentProject.order_no == new_order_no,
            InvestmentProject.is_deleted == False
        ).first()
        if conflict and not force_reorder:
            return jsonify({
                'code': 2,
                'message': f'顺序号 {new_order_no} 已被项目「{conflict.project_name}」使用',
                'data': {'conflict_project': conflict.project_name}
            })
        elif conflict and force_reorder:
            # 将当前顺序号 >= new_order_no 的其它项目整体下移
            targets = InvestmentProject.query.filter(
                InvestmentProject.id != project_id,
                InvestmentProject.order_no >= new_order_no,
                InvestmentProject.is_deleted == False
            ).order_by(InvestmentProject.order_no.desc()).all()
            for t in targets:
                t.order_no += 1

    updatable_fields = [
        'order_no', 'project_name', 'invest_enterprise', 'enterprise_info',
        'project_content', 'invest_amount', 'follow_status_code',
        'meeting_status_code', 'recommend_unit_code', 'responsible_unit_code',
        'project_type_code', 'person_in_charge', 'project_doc', 'investment_plan', 'conclusion', 'first_contact_date'
    ]
    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == 'first_contact_date':
                val = _parse_date(val)
            setattr(project, field, val)

    # 同步企业诉求：先删后建
    if 'demands' in data:
        EnterpriseDemand.query.filter_by(project_id=project_id).delete()
        for i, d in enumerate(data['demands'] or []):
            if d.get('demand_content', '').strip():
                db.session.add(EnterpriseDemand(
                    project_id=project_id,
                    demand_type_code=d.get('demand_type_code', ''),
                    demand_content=d['demand_content'],
                    resolution=d.get('resolution', ''),
                    unit_code=d.get('unit_code', ''),
                    status=d.get('status', 'pending'),
                    sort_order=i + 1
                ))

    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_dict(), 'message': '更新成功'})


@admin_investment_bp.route('/investment/projects/<int:project_id>', methods=['DELETE'])
@dual_login_required
def delete_project(project_id):
    """逻辑删除项目"""
    project = InvestmentProject.query.filter_by(id=project_id, is_deleted=False).first_or_404()
    project.is_deleted = True
    db.session.commit()
    return jsonify({'code': 0, 'message': '项目已删除'})


@admin_investment_bp.route('/investment/projects/batch-delete', methods=['POST'])
@dual_login_required
def batch_delete_projects():
    """批量删除项目"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'code': 1, 'message': '请提供要删除的项目ID列表'}), 400

    deleted = InvestmentProject.query.filter(
        InvestmentProject.id.in_(ids),
        InvestmentProject.is_deleted == False
    ).update({'is_deleted': True}, synchronize_session=False)
    db.session.commit()

    return jsonify({'code': 0, 'message': f'成功删除 {deleted} 个项目', 'data': {'count': deleted}})


# ============================================================
# 企业诉求 CRUD（项目子表）
# ============================================================

@admin_investment_bp.route('/investment/projects/<int:project_id>/demands', methods=['GET'])
@dual_login_required
def list_demands(project_id):
    """获取项目的企业诉求列表"""
    demands = EnterpriseDemand.query.filter_by(project_id=project_id)\
        .order_by(EnterpriseDemand.sort_order).all()
    return jsonify({'code': 0, 'data': [d.to_dict() for d in demands]})


@admin_investment_bp.route('/investment/projects/<int:project_id>/demands', methods=['POST'])
@dual_login_required
def create_demand(project_id):
    """新增企业诉求"""
    data = request.get_json()
    if not data or not data.get('demand_content'):
        return jsonify({'code': 1, 'message': '诉求内容不能为空'}), 400

    # 自动取当前最大 sort_order + 1
    max_order = db.session.query(db.func.max(EnterpriseDemand.sort_order))\
        .filter_by(project_id=project_id).scalar() or 0

    demand = EnterpriseDemand(
        project_id=project_id,
        demand_content=data['demand_content'],
        resolution=data.get('resolution', ''),
        status=data.get('status', 'pending'),
        sort_order=max_order + 1
    )
    db.session.add(demand)
    db.session.commit()
    return jsonify({'code': 0, 'data': demand.to_dict(), 'message': '诉求已添加'})


@admin_investment_bp.route('/investment/projects/<int:project_id>/demands/<int:demand_id>', methods=['PUT'])
@dual_login_required
def update_demand(project_id, demand_id):
    """更新企业诉求"""
    demand = EnterpriseDemand.query.filter_by(id=demand_id, project_id=project_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    for field in ['demand_content', 'resolution', 'status', 'sort_order']:
        if field in data:
            setattr(demand, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': demand.to_dict(), 'message': '更新成功'})


@admin_investment_bp.route('/investment/projects/<int:project_id>/demands/<int:demand_id>', methods=['DELETE'])
@dual_login_required
def delete_demand(project_id, demand_id):
    """删除企业诉求"""
    demand = EnterpriseDemand.query.filter_by(id=demand_id, project_id=project_id).first_or_404()
    db.session.delete(demand)
    db.session.commit()
    return jsonify({'code': 0, 'message': '诉求已删除'})
