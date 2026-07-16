import json
from datetime import date, datetime, timedelta
from flask import request, jsonify
from models import InvestmentProject, InvestmentActivity, EnterpriseDemand
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict, Staff
from extensions import db
from routes import admin_investment_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes


def _renumber_investment_projects():
    """将招商项目序号重新编排为连续整数 1, 2, 3, ..."""
    projects = InvestmentProject.query.filter_by(is_deleted=False)\
        .order_by(InvestmentProject.order_no.asc(), InvestmentProject.id.asc()).all()
    for i, p in enumerate(projects, 1):
        if p.order_no != i:
            p.order_no = i
    # 注意：不在此处 commit，由调用方统一 commit


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
            'demand_types': [d.to_dict() for d in DemandTypeDict.query.filter_by(is_active=True).order_by(DemandTypeDict.sort_order).all()],
            'project_tags': [d.to_dict() for d in ProjectTagDict.query.filter_by(is_active=True).order_by(ProjectTagDict.sort_order).all()],
            'activity_tags': [d.to_dict() for d in ActivityTagDict.query.filter_by(is_active=True).order_by(ActivityTagDict.sort_order).all()],
            'staff': [d.to_dict() for d in Staff.query.filter_by(is_active=True).order_by(Staff.sort_order).all()]
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
    recent_activity_days = request.args.get('recent_activity_days', '').strip()

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
        codes = [c.strip() for c in follow_status.split(',') if c.strip()]
        if len(codes) == 1:
            q = q.filter_by(follow_status_code=codes[0])
        elif len(codes) > 1:
            q = q.filter(InvestmentProject.follow_status_code.in_(codes))
    if meeting_status:
        q = q.filter_by(meeting_status_code=meeting_status)
    if project_type:
        q = q.filter_by(project_type_code=project_type)

    # 近期更新筛选：项目自身 / 招商动态 / 企业诉求 任一在 N 天内有更新
    if recent_activity_days:
        try:
            days = int(recent_activity_days)
            cutoff = datetime.utcnow() - timedelta(days=days)
            q = q.filter(db.or_(
                InvestmentProject.last_updated_at >= cutoff,
                InvestmentProject.activities.any(InvestmentActivity.date >= cutoff),
                InvestmentProject.demands.any(EnterpriseDemand.updated_at >= cutoff)
            ))
        except (ValueError, TypeError):
            pass

    # 排序：重点跟进优先 → 顺序号升序
    q = q.order_by(
        db.case((InvestmentProject.follow_status_code == 'follow_focus', 0), else_=1),
        InvestmentProject.order_no.asc(),
        InvestmentProject.created_at.desc()
    )

    projects = q.all()
    result = []
    # 预加载 staff 映射用于专班负责人名称解析
    all_leader_ids = set()
    for p in projects:
        if p.team_leader_ids:
            try:
                ids = json.loads(p.team_leader_ids)
                all_leader_ids.update(ids)
            except Exception:
                pass
    staff_map = {}
    if all_leader_ids:
        from models import Staff
        staff_map = {s.id: s.name for s in Staff.query.filter(Staff.id.in_(list(all_leader_ids))).all()}
    for p in projects:
        d = p.to_dict()
        leader_ids = d.get('team_leader_ids', [])
        d['team_leader_names'] = [staff_map.get(sid, str(sid)) for sid in leader_ids]
        result.append(d)
    return jsonify({'code': 0, 'data': result})


@admin_investment_bp.route('/investment/projects', methods=['POST'])
@dual_login_required
@visitor_block
def create_project():
    """新建项目"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 必填字段校验
    required = ['project_name', 'invest_enterprise', 'enterprise_info', 'project_content',
                'follow_status_code', 'project_type_code']
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
        responsible_unit_code=data.get('responsible_unit_code', ''),
        project_type_code=data['project_type_code'],
        person_in_charge=data.get('person_in_charge', ''),
        person_in_charge_phone=data.get('person_in_charge_phone', ''),
        project_doc=data.get('project_doc', ''),
        investment_plan=data.get('investment_plan', ''),
        conclusion=data.get('conclusion', ''),
        tags=json.dumps(data.get('tags', []), ensure_ascii=False),
        team_leader_ids=json.dumps(data.get('team_leader_ids', []), ensure_ascii=False),
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

    # 审计日志：项目创建
    user_info = get_current_user_info()
    if user_info:
        changes = {}
        for field in ['order_no', 'project_name', 'invest_enterprise', 'enterprise_info',
                      'project_content', 'invest_amount', 'follow_status_code',
                      'meeting_status_code', 'recommend_unit_code', 'responsible_unit_code',
                      'project_type_code', 'person_in_charge', 'person_in_charge_phone', 'project_doc', 'investment_plan',
                      'conclusion']:
            changes[field] = (None, getattr(project, field))
        changes['first_contact_date'] = (None, project.first_contact_date.isoformat() if project.first_contact_date else None)
        changes['tags'] = (None, json.dumps(data.get('tags', []), ensure_ascii=False))
        changes['team_leader_ids'] = (None, json.dumps(data.get('team_leader_ids', []), ensure_ascii=False))
        log_changes('investment_projects', project.id, changes, 'create', user_info)

    _renumber_investment_projects()
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
        codes = [c.strip() for c in (d.get('demand_type_code') or '').split(',') if c.strip()]
        d['demand_type_name'] = '、'.join([demand_display_map.get(c, c) for c in codes]) if codes else ''
        du = org_map.get(d.get('unit_code'))
        d['unit_name'] = du.name if du else ''

    return jsonify({'code': 0, 'data': data})


@admin_investment_bp.route('/investment/projects/<int:project_id>', methods=['PUT'])
@dual_login_required
@visitor_block
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
        'project_type_code', 'person_in_charge', 'person_in_charge_phone', 'project_doc', 'investment_plan', 'conclusion', 'tags', 'team_leader_ids', 'first_contact_date'
    ]

    # 排除字段：这些字段的变更不触发 last_updated_at 刷新（不视为"更新"）
    # 包括：序号、项目类型、推介/责任单位、跟进/上会状态
    excluded_from_update_flag = {
        'order_no', 'project_type_code', 'recommend_unit_code',
        'responsible_unit_code', 'follow_status_code', 'meeting_status_code'
    }

    # 审计日志：保存旧值
    user_info = get_current_user_info()
    old_values = {}
    if user_info:
        for field in updatable_fields:
            old_val = getattr(project, field)
            if field == 'first_contact_date':
                old_val = old_val.isoformat() if old_val else None
            elif field == 'tags':
                old_val = json.dumps(json.loads(old_val) if old_val else [], ensure_ascii=False) if old_val else '[]'
            elif field == 'team_leader_ids':
                old_val = json.dumps(json.loads(old_val) if old_val else [], ensure_ascii=False) if old_val else '[]'
            old_values[field] = old_val

    # 标记是否有实际内容变更（用于跳过时间戳刷新）
    project_changed = False
    has_non_excluded_change = False

    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == 'first_contact_date':
                val = _parse_date(val)
            elif field == 'tags':
                val = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val
            elif field == 'team_leader_ids':
                val = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val

            # 比较新旧值，仅在实际变更时写入（避免无变更时刷新 last_updated_at）
            old_val = getattr(project, field)
            if field == 'first_contact_date':
                old_cmp = old_val.isoformat() if old_val else None
                new_cmp = val.isoformat() if val else None
                changed = (old_cmp != new_cmp)
            elif field in ('tags', 'team_leader_ids'):
                old_str = json.dumps(json.loads(old_val) if old_val else [], ensure_ascii=False) if old_val else '[]'
                new_str = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
                changed = (old_str != new_str)
            else:
                changed = (str(old_val or '') != str(val or ''))
            if changed:
                setattr(project, field, val)
                project_changed = True
                if field not in excluded_from_update_flag:
                    has_non_excluded_change = True

    # 审计日志：对比新旧值
    if user_info:
        changes = {}
        for field in updatable_fields:
            old_val = old_values.get(field)
            new_val = getattr(project, field)
            if field == 'first_contact_date':
                new_val = new_val.isoformat() if new_val else None
            elif field == 'tags':
                new_val = json.dumps(json.loads(new_val) if new_val else [], ensure_ascii=False) if new_val else '[]'
            elif field == 'team_leader_ids':
                new_val = json.dumps(json.loads(new_val) if new_val else [], ensure_ascii=False) if new_val else '[]'
            if str(old_val) != str(new_val):
                changes[field] = (old_val, new_val)
        log_changes('investment_projects', project_id, changes, 'update', user_info)

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

    _renumber_investment_projects()

    # 只有非排除字段变更时，才刷新 last_updated_at（标记为"更新"）
    if has_non_excluded_change:
        project.last_updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_dict(), 'message': '更新成功'})


@admin_investment_bp.route('/investment/projects/<int:project_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_project(project_id):
    """逻辑删除项目"""
    project = InvestmentProject.query.filter_by(id=project_id, is_deleted=False).first_or_404()
    project.is_deleted = True
    _renumber_investment_projects()
    db.session.commit()
    return jsonify({'code': 0, 'message': '项目已删除'})


@admin_investment_bp.route('/investment/projects/batch-delete', methods=['POST'])
@dual_login_required
@visitor_block
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
    _renumber_investment_projects()
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
@visitor_block
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
    db.session.flush()

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        changes = {
            'project_id': (None, demand.project_id),
            'demand_content': (None, demand.demand_content),
            'resolution': (None, demand.resolution or ''),
            'status': (None, demand.status),
            'sort_order': (None, demand.sort_order)
        }
        log_changes('enterprise_demands', demand.id, changes, 'create', user_info)

    db.session.commit()
    return jsonify({'code': 0, 'data': demand.to_dict(), 'message': '诉求已添加'})


@admin_investment_bp.route('/investment/projects/<int:project_id>/demands/<int:demand_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_demand(project_id, demand_id):
    """更新企业诉求"""
    demand = EnterpriseDemand.query.filter_by(id=demand_id, project_id=project_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 审计日志：保存旧值
    user_info = get_current_user_info()
    old_values = {}
    if user_info:
        for field in ['demand_content', 'resolution', 'status', 'sort_order']:
            old_values[field] = getattr(demand, field)

    for field in ['demand_content', 'resolution', 'status', 'sort_order']:
        if field in data:
            setattr(demand, field, data[field])

    # 审计日志：对比变更
    if user_info:
        changes = {}
        for field in ['demand_content', 'resolution', 'status', 'sort_order']:
            old_val = old_values.get(field)
            new_val = getattr(demand, field)
            if str(old_val) != str(new_val):
                changes[field] = (old_val, new_val)
        log_changes('enterprise_demands', demand_id, changes, 'update', user_info)

    db.session.commit()
    return jsonify({'code': 0, 'data': demand.to_dict(), 'message': '更新成功'})


@admin_investment_bp.route('/investment/projects/<int:project_id>/demands/<int:demand_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_demand(project_id, demand_id):
    """删除企业诉求"""
    demand = EnterpriseDemand.query.filter_by(id=demand_id, project_id=project_id).first_or_404()
    db.session.delete(demand)
    db.session.commit()
    return jsonify({'code': 0, 'message': '诉求已删除'})


# ============================================================
# 数据看板 — 招商项目统计
# ============================================================

@admin_investment_bp.route('/investment-stats', methods=['GET'])
@dual_login_required
def investment_stats():
    """招商项目统计数据（按项目类型分布，支持跟进状态/上会状态筛选）"""
    from sqlalchemy import func

    follow_status = request.args.get('follow_status', '').strip()
    meeting_status = request.args.get('meeting_status', '').strip()

    # 基础过滤条件
    base_filters = [InvestmentProject.is_deleted == False]
    if follow_status:
        codes = [c.strip() for c in follow_status.split(',') if c.strip()]
        if len(codes) == 1:
            base_filters.append(InvestmentProject.follow_status_code == codes[0])
        elif len(codes) > 1:
            base_filters.append(InvestmentProject.follow_status_code.in_(codes))
    if meeting_status:
        codes = [c.strip() for c in meeting_status.split(',') if c.strip()]
        if len(codes) == 1:
            base_filters.append(InvestmentProject.meeting_status_code == codes[0])
        elif len(codes) > 1:
            base_filters.append(InvestmentProject.meeting_status_code.in_(codes))

    # 按 project_type_code 分组统计项目数量
    rows = db.session.query(
        InvestmentProject.project_type_code,
        func.count(InvestmentProject.id)
    ).filter(*base_filters).group_by(
        InvestmentProject.project_type_code
    ).all()

    # 解析项目类型名称
    type_dicts = {
        d.code: d.name
        for d in ProjectTypeDict.query.all()
    }

    # 获取符合条件的项目，用于按类型聚合项目清单（含投资金额）
    all_projects = InvestmentProject.query.filter(*base_filters).with_entities(
        InvestmentProject.id, InvestmentProject.project_name,
        InvestmentProject.project_type_code, InvestmentProject.invest_amount,
        InvestmentProject.team_leader_ids
    ).order_by(InvestmentProject.order_no).all()

    # 按类型分组项目清单
    projects_by_type = {}
    for p in all_projects:
        code = p.project_type_code
        if code not in projects_by_type:
            projects_by_type[code] = []
        projects_by_type[code].append({
            'id': p.id,
            'name': p.project_name,
            'invest_amount': p.invest_amount or '',
        })

    by_project_type = []
    for code, count in rows:
        by_project_type.append({
            'code': code,
            'name': type_dicts.get(code, code),
            'count': count,
            'projects': projects_by_type.get(code, []),
        })

    # 按数量降序排列
    by_project_type.sort(key=lambda x: x['count'], reverse=True)

    total_projects = sum(item['count'] for item in by_project_type)

    # 按专班负责人统计
    from models import Staff
    leader_stats = {}
    for p in all_projects:
        try:
            leader_ids = json.loads(getattr(p, 'team_leader_ids', '[]') or '[]')
        except (json.JSONDecodeError, TypeError):
            leader_ids = []
        if not leader_ids:
            continue
        for sid in leader_ids:
            if sid not in leader_stats:
                leader_stats[sid] = {'staff_id': sid, 'count': 0, 'projects': []}
            leader_stats[sid]['count'] += 1
            leader_stats[sid]['projects'].append({
                'id': p.id,
                'name': p.project_name,
                'invest_amount': float(p.invest_amount) if p.invest_amount else 0
            })
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
            'total_projects': total_projects,
            'by_project_type': by_project_type,
            'by_team_leader': by_team_leader,
        }
    })
