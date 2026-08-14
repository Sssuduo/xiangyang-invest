"""揭榜挂帅 — 内部端口 API（专班/业务用户使用）

包含：榜单项目 CRUD / 七步阶段流转 / 揭榜申请管理 / 里程碑 / 全周期时间线 / 揭榜方用户管理 / 看板统计
权限：@dual_login_required（admin + 业务）；写操作叠 @visitor_block；变更写 log_changes 审计
"""
import json
from datetime import date, datetime, timedelta

from flask import request, jsonify

from models import (
    BiddingProject, BiddingBid, BiddingMilestone, BiddingTimeline,
    BiddingUser, BiddingEnterprise, BiddingCategoryDict, Staff,
)
from extensions import db
from routes import admin_bidding_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes
from services.bidding_service import (
    STAGES, STAGE_NAME_MAP, TERMINAL_STAGES, validate_transition,
    transition_summary, BiddingTransitionError,
)


def _safe_date(val):
    """字符串 → date；失败返回 None"""
    if not val:
        return None
    if hasattr(val, 'strftime'):
        return val
    try:
        if isinstance(val, str) and len(val) == 7 and val[4] == '-':
            val = val + '-01'
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _safe_date_str(val):
    if not val:
        return ''
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    return str(val)[:10]


def _json_list(val):
    try:
        return json.loads(val) if val else []
    except (json.JSONDecodeError, TypeError):
        return []


def _record_by():
    info = get_current_user_info()
    if info:
        return f'{info[2]}（{"管理员" if info[0] == "admin" else "业务用户"}）'
    return '系统'


def _add_timeline(project, content, record_type='system', stage=None):
    """写入全周期时间线"""
    t = BiddingTimeline(
        project_id=project.id,
        stage=stage or project.current_stage,
        record_type=record_type,
        content=content,
        files='[]',
        record_by=_record_by(),
    )
    db.session.add(t)


# ============================================================
# 字典
# ============================================================

@admin_bidding_bp.route('/bidding/dicts', methods=['GET'])
@dual_login_required
def get_dicts():
    categories = BiddingCategoryDict.query \
        .filter_by(is_active=True) \
        .order_by(BiddingCategoryDict.sort_order).all()
    staff_list = Staff.query.filter_by(is_active=True).order_by(Staff.sort_order).all()
    return jsonify({'code': 0, 'data': {
        'categories': [d.to_dict() for d in categories],
        'stages': STAGES,
        'staff': [d.to_dict() for d in staff_list],
        'demand_sources': ['企业申报', '专班征集', '部门推荐', '其他'],
        'bidder_types': ['高校', '科研院所', '企业', '团队'],
        'eval_levels': ['优秀', '良好', '合格', '不合格'],
    }})


def _resolve_names(projects):
    """批量解析字典名称（领域/阶段/专班）"""
    cat_map = {d.code: d.name for d in BiddingCategoryDict.query.all()}
    staff_map = {s.id: s.name for s in Staff.query.all()}
    for p in projects:
        p._category_name = cat_map.get(p.category_code, p.category_code or '')
        p._stage_name = STAGE_NAME_MAP.get(p.current_stage, p.current_stage)
        leader_ids = _json_list(p.service_leader_ids)
        p._service_leader_names = [staff_map.get(sid, str(sid)) for sid in leader_ids]
    return projects


def _build_project_dict(p):
    return {
        'id': p.id,
        'order_no': p.order_no,
        'title': p.title,
        'category_code': p.category_code or '',
        'category_name': getattr(p, '_category_name', p.category_code or ''),
        'demander_name': p.demander_name or '',
        'demander_contact': p.demander_contact or '',
        'demander_phone': p.demander_phone or '',
        'demand_source': p.demand_source or '',
        'requirement_desc': p.requirement_desc or '',
        'expected_budget': p.expected_budget or 0.0,
        'expected_deadline': _safe_date_str(p.expected_deadline),
        'current_stage': p.current_stage,
        'stage_name': getattr(p, '_stage_name', p.current_stage),
        'service_leader_ids': _json_list(p.service_leader_ids),
        'service_leader_names': getattr(p, '_service_leader_names', []),
        'publish_status': p.publish_status or 'unpublished',
        'publish_date': _safe_date_str(p.publish_date),
        'deadline_date': _safe_date_str(p.deadline_date),
        'bounty_amount': p.bounty_amount or 0.0,
        'argument_status': p.argument_status or 'pending',
        'bid_status': p.bid_status or 'collecting',
        'task_status': p.task_status or 'unsigned',
        'process_status': p.process_status or 'ongoing',
        'eval_status': p.eval_status or 'unevaluated',
        'eval_level': p.eval_level or '',
        'bid_count': p.bids.count() if hasattr(p, 'bids') else 0,
        'is_deleted': p.is_deleted,
        'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else None,
        'updated_at': p.updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.updated_at else None,
        'last_updated_at': p.last_updated_at.strftime('%Y-%m-%d %H:%M:%S') if p.last_updated_at else None,
    }


# ============================================================
# 列表 / 创建 / 详情 / 编辑 / 删除
# ============================================================

# 申报表字段清单（企业概况/需求描述/合作意向）——创建与编辑共用
_DECLARATION_FIELDS = [
    'enterprise_address', 'industry_code', 'registered_capital', 'founded_year',
    'staff_size', 'enterprise_nature', 'main_products', 'last_year_revenue',
    'tech_difficulties', 'tech_indicators', 'research_content',
    'expert_intent', 'expert_names',
]
# 多选 JSON 字段
_DECLARATION_JSON_FIELDS = ['enterprise_qualifications', 'short_term_cooperation', 'long_term_cooperation']

# 企业档案字段（BiddingEnterprise 与项目内联企业字段的映射）
_ENTERPRISE_FIELDS = {
    'enterprise_address': 'enterprise_address',
    'enterprise_qualifications': 'enterprise_qualifications',
    'industry_code': 'industry_code',
    'registered_capital': 'registered_capital',
    'founded_year': 'founded_year',
    'staff_size': 'staff_size',
    'enterprise_nature': 'enterprise_nature',
    'main_products': 'main_products',
    'last_year_revenue': 'last_year_revenue',
    'contact_name': 'demander_contact',
    'contact_phone': 'demander_phone',
}


def _apply_declaration_fields(project, data, changes):
    """将申报表字段写入项目并记录变更（供创建/编辑复用）"""
    for field in _DECLARATION_FIELDS:
        if field in data and data.get(field) is not None:
            val = data.get(field)
            changes[field] = (getattr(project, field), val)
            setattr(project, field, val)
    for field in _DECLARATION_JSON_FIELDS:
        if field in data and data.get(field) is not None:
            val = data.get(field)
            changes[field] = ('…', '…')
            setattr(project, field, json.dumps(val, ensure_ascii=False))


def _sync_enterprise_to_project(project, enterprise):
    """把企业档案字段回填到项目内联字段（保持冗余一致，兼容旧查询）"""
    project.demander_name = enterprise.org_name
    for ent_field, proj_field in _ENTERPRISE_FIELDS.items():
        val = getattr(enterprise, ent_field)
        if ent_field == 'enterprise_qualifications':
            # 项目列存 TEXT JSON，需序列化
            q = json.loads(val) if val else []
            setattr(project, proj_field, json.dumps(q, ensure_ascii=False))
        else:
            setattr(project, proj_field, val if val is not None else '')


def _resolve_enterprise(data):
    """根据提交数据解析/更新企业档案，返回 (enterprise 或 None, 是否需要新增到 session)。

    逻辑：
    - data.enterprise_id 有值 → 关联已有企业档案，并应用提交的企业字段更新档案（选择模式可编辑）
    - 无 enterprise_id 但提供了 org_name → 新建企业档案（同名企业已存在则复用并更新其字段）
    """
    ent_id = data.get('enterprise_id')
    org_name = (data.get('org_name') or '').strip()
    if ent_id:
        ent = db.session.get(BiddingEnterprise, int(ent_id))
        if ent:
            # 选择模式：应用提交字段更新档案（用户可编辑带出字段）
            if org_name and org_name != ent.org_name:
                ent.org_name = org_name
            for ent_field in _ENTERPRISE_FIELDS:
                val = data.get(ent_field)
                if val is not None:
                    setattr(ent, ent_field, val)
            if data.get('contact_name') is not None:
                ent.contact_name = data.get('contact_name')
            if data.get('contact_phone') is not None:
                ent.contact_phone = data.get('contact_phone')
            return ent, False
    if not org_name:
        return None, False
    # 新建模式：同名企业存在则复用
    ent = BiddingEnterprise.query.filter_by(org_name=org_name).first()
    if ent is None:
        ent = BiddingEnterprise(org_name=org_name)
    # 用提交的企业字段更新档案
    for ent_field in _ENTERPRISE_FIELDS:
        val = data.get(ent_field)
        if val is not None:
            setattr(ent, ent_field, val)
    ent.contact_name = data.get('contact_name') or ent.contact_name
    ent.contact_phone = data.get('contact_phone') or ent.contact_phone
    return ent, True


@admin_bidding_bp.route('/bidding/projects', methods=['GET'])
@dual_login_required
def list_projects():
    q = BiddingProject.query.filter_by(is_deleted=False)

    search = request.args.get('search', '').strip()
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            BiddingProject.title.ilike(like),
            BiddingProject.demander_name.ilike(like),
            BiddingProject.requirement_desc.ilike(like),
            BiddingProject.tech_difficulties.ilike(like),
            BiddingProject.main_products.ilike(like),
        ))

    stage = request.args.get('stage', '').strip()
    if stage:
        q = q.filter(BiddingProject.current_stage == stage)

    category = request.args.get('category', '').strip()
    if category:
        q = q.filter(BiddingProject.category_code == category)

    q = q.order_by(BiddingProject.order_no.asc(), BiddingProject.created_at.desc())
    projects = _resolve_names(q.all())
    return jsonify({'code': 0, 'data': [_build_project_dict(p) for p in projects]})


@admin_bidding_bp.route('/bidding/projects', methods=['POST'])
@dual_login_required
@visitor_block
def create_project():
    """新建榜单（需求征集登记，含企业需求申报表字段 + 企业档案关联）"""
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'code': 1, 'message': '榜单名称不能为空'}), 400

    # 企业档案解析（选择已有 / 新建）
    enterprise, ent_new = _resolve_enterprise(data)
    if enterprise is None and not (data.get('demander_name') or '').strip():
        return jsonify({'code': 1, 'message': '请选择或填写发榜企业名称'}), 400

    max_no = db.session.query(db.func.max(BiddingProject.order_no)).scalar() or 0
    project = BiddingProject(
        order_no=max_no + 1,
        title=title,
        category_code=data.get('category_code', ''),
        demander_name=(data.get('demander_name') or '').strip(),
        demander_contact=data.get('demander_contact', ''),
        demander_phone=data.get('demander_phone', ''),
        demand_source=data.get('demand_source', ''),
        requirement_desc=data.get('requirement_desc', ''),
        requirement_attachment=json.dumps(data.get('requirement_attachment', []), ensure_ascii=False),
        expected_budget=data.get('expected_budget') or 0.0,
        expected_deadline=_safe_date(data.get('expected_deadline')),
        service_leader_ids=json.dumps(data.get('service_leader_ids', []), ensure_ascii=False),
        current_stage='stage1',
    )
    # 企业档案：新增/更新 + 关联
    if enterprise is not None:
        if ent_new:
            db.session.add(enterprise)
            db.session.flush()
        project.enterprise_id = enterprise.id
        _sync_enterprise_to_project(project, enterprise)

    # 申报表字段
    changes = {'title': ('', title)}
    _apply_declaration_fields(project, data, changes)

    db.session.add(project)
    db.session.flush()

    user_info = get_current_user_info()
    log_changes('bidding_projects', project.id, changes, 'create', user_info)
    _add_timeline(project, '【系统】需求征集登记：榜单「%s」已创建' % title, record_type='system')
    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_dict(), 'message': '需求已登记'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>', methods=['GET'])
@dual_login_required
def get_project(project_id):
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    return jsonify({'code': 0, 'data': project.to_detail_dict()})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_project(project_id):
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404

    data = request.get_json(silent=True) or {}
    # 通用字段编辑（不包含阶段流转字段）
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'code': 1, 'message': '榜单名称不能为空'}), 400

    changes = {'title': (project.title, title)}
    project.title = title
    # 企业档案：允许切换/新建（表单提交 org_name/enterprise_id 时处理）
    if 'enterprise_id' in data or (data.get('org_name') or '').strip():
        enterprise, ent_new = _resolve_enterprise(data)
        if enterprise is not None:
            if ent_new:
                db.session.add(enterprise)
                db.session.flush()
            if project.enterprise_id != enterprise.id:
                changes['enterprise_id'] = (project.enterprise_id, enterprise.id)
            project.enterprise_id = enterprise.id
            _sync_enterprise_to_project(project, enterprise)
    for field in ('category_code', 'demander_name', 'demander_contact', 'demander_phone',
                  'demand_source', 'requirement_desc'):
        val = data.get(field)
        if val is not None:
            changes[field] = (getattr(project, field), val)
            setattr(project, field, val)
    # 申报表字段（企业概况/需求描述/合作意向）
    _apply_declaration_fields(project, data, changes)
    if 'requirement_attachment' in data:
        changes['requirement_attachment'] = ('…', '…')
        project.requirement_attachment = json.dumps(data.get('requirement_attachment', []), ensure_ascii=False)
    if 'expected_budget' in data:
        val = data.get('expected_budget') or 0.0
        changes['expected_budget'] = (project.expected_budget, val)
        project.expected_budget = val
    if 'expected_deadline' in data:
        val = _safe_date(data.get('expected_deadline'))
        changes['expected_deadline'] = (_safe_date_str(project.expected_deadline), _safe_date_str(val))
        project.expected_deadline = val
    if 'service_leader_ids' in data:
        changes['service_leader_ids'] = ('…', '…')
        project.service_leader_ids = json.dumps(data.get('service_leader_ids', []), ensure_ascii=False)

    project.last_updated_at = datetime.utcnow()
    log_changes('bidding_projects', project.id, changes, 'update', get_current_user_info())
    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_dict(), 'message': '已保存'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_project(project_id):
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    project.is_deleted = True
    log_changes('bidding_projects', project.id, {'is_deleted': (False, True)}, 'update', get_current_user_info())
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ============================================================
# 七步阶段流转
# ============================================================

@admin_bidding_bp.route('/bidding/projects/<int:project_id>/transition', methods=['POST'])
@dual_login_required
@visitor_block
def transition(project_id):
    """阶段流转：body = {action, ...payload}"""
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404

    data = request.get_json(silent=True) or {}
    action = data.get('action', '')
    try:
        to_stage = validate_transition(project.current_stage, action)
    except BiddingTransitionError as e:
        return jsonify({'code': 1, 'message': str(e)}), 400

    changes = {'current_stage': (project.current_stage, to_stage)}
    extra = ''

    if action == 'submit_argument':
        project.argument_status = 'pending'
    elif action == 'argument_pass':
        project.argument_status = 'passed'
        project.argument_experts = json.dumps(data.get('argument_experts', []), ensure_ascii=False)
        project.argument_opinion = data.get('argument_opinion', '')
        project.argument_result = data.get('argument_result', '')
        project.argument_date = _safe_date(data.get('argument_date')) or date.today()
        extra = '论证通过'
    elif action == 'argument_reject':
        project.argument_status = 'rejected'
        project.argument_opinion = data.get('argument_opinion', '')
        project.argument_result = data.get('argument_result', '')
        project.argument_date = _safe_date(data.get('argument_date')) or date.today()
        extra = data.get('argument_result', '')[:100]
    elif action == 'publish':
        project.publish_status = 'published'
        project.publish_date = _safe_date(data.get('publish_date')) or date.today()
        project.deadline_date = _safe_date(data.get('deadline_date'))
        project.bounty_amount = data.get('bounty_amount') or 0.0
        project.accept_conditions = data.get('accept_conditions', '')
        if not project.deadline_date:
            return jsonify({'code': 1, 'message': '发布公告必须填写揭榜截止日期'}), 400
        extra = '揭榜截止 %s' % _safe_date_str(project.deadline_date)
    elif action == 'expire':
        project.publish_status = 'expired'
        project.bid_status = 'collecting'
    elif action == 'select_bid':
        bid_id = data.get('bid_id')
        bid = BiddingBid.query.filter_by(id=bid_id, project_id=project.id).first() if bid_id else None
        if not bid:
            return jsonify({'code': 1, 'message': '请选择要确定的揭榜申请'}), 400
        project.bid_status = 'selected'
        project.selected_bid_id = bid.id
        project.review_result = data.get('review_result', '')
        # 中选申请置 selected，其余置 rejected
        for b in project.bids.all():
            b.status = 'selected' if b.id == bid.id else 'rejected'
        extra = '揭榜方：%s' % (bid.bidder_name or '')
    elif action == 'fail_bid':
        project.bid_status = 'failed'
        project.review_result = data.get('review_result', '')
        extra = data.get('review_result', '')[:100]
    elif action == 'sign':
        project.task_status = 'signed'
        project.task_date = _safe_date(data.get('task_date')) or date.today()
        project.task_amount = data.get('task_amount') or 0.0
        project.task_duration = data.get('task_duration', '')
        project.task_notes = data.get('task_notes', '')
        project.process_status = 'ongoing'
        extra = '任务经费 %s 万元' % (project.task_amount or 0)
    elif action == 'complete':
        project.process_status = 'completed'
        project.process_notes = data.get('process_notes', '')
    elif action == 'terminate':
        project.process_status = 'terminated'
        project.process_notes = data.get('process_notes', '')
        extra = data.get('process_notes', '')[:100]
    elif action == 'evaluate':
        project.eval_status = 'evaluated'
        project.eval_score = data.get('eval_score')
        project.eval_level = data.get('eval_level', '')
        project.eval_report = data.get('eval_report', '')
        project.eval_date = _safe_date(data.get('eval_date')) or date.today()
        if project.eval_score is None or not project.eval_level:
            return jsonify({'code': 1, 'message': '绩效评价必须填写评分与等级'}), 400
        extra = '评分 %s / %s' % (project.eval_score, project.eval_level)
    elif action == 'cancel':
        extra = data.get('reason', '')[:100]

    project.current_stage = to_stage
    project.last_updated_at = datetime.utcnow()
    log_changes('bidding_projects', project.id, changes, 'update', get_current_user_info())
    _add_timeline(project, transition_summary(action, extra), record_type='system')
    db.session.commit()
    return jsonify({'code': 0, 'data': project.to_detail_dict(),
                    'message': transition_summary(action, extra).replace('【系统】', '')})


# ============================================================
# 揭榜申请（内部全量管理 + 代录）
# ============================================================

@admin_bidding_bp.route('/bidding/projects/<int:project_id>/bids', methods=['POST'])
@dual_login_required
@visitor_block
def create_bid(project_id):
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    data = request.get_json(silent=True) or {}
    bidder_name = (data.get('bidder_name') or '').strip()
    if not bidder_name:
        return jsonify({'code': 1, 'message': '揭榜方名称不能为空'}), 400

    bid = BiddingBid(
        project_id=project.id,
        user_id=None,  # 内部代录
        bidder_name=bidder_name,
        bidder_type=data.get('bidder_type', ''),
        team_leader=data.get('team_leader', ''),
        team_leader_phone=data.get('team_leader_phone', ''),
        tech_solution=data.get('tech_solution', ''),
        team_advantage=data.get('team_advantage', ''),
        expected_amount=data.get('expected_amount') or 0.0,
        status='submitted',
    )
    db.session.add(bid)
    db.session.flush()
    _add_timeline(project, '【服务】内部代录揭榜申请：%s' % bidder_name, record_type='service')
    db.session.commit()
    return jsonify({'code': 0, 'data': bid.to_dict(), 'message': '揭榜申请已登记'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/bids/<int:bid_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_bid(project_id, bid_id):
    bid = BiddingBid.query.filter_by(id=bid_id, project_id=project_id).first()
    if not bid:
        return jsonify({'code': 1, 'message': '揭榜申请不存在'}), 404
    data = request.get_json(silent=True) or {}
    for field in ('bidder_name', 'bidder_type', 'team_leader', 'team_leader_phone',
                  'tech_solution', 'team_advantage', 'score_note'):
        if field in data and data.get(field) is not None:
            setattr(bid, field, data.get(field))
    if 'expected_amount' in data:
        bid.expected_amount = data.get('expected_amount') or 0.0
    if 'score' in data:
        bid.score = data.get('score')
    if 'status' in data:
        bid.status = data.get('status')
    db.session.commit()
    return jsonify({'code': 0, 'data': bid.to_dict(), 'message': '已保存'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/bids/<int:bid_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_bid(project_id, bid_id):
    bid = BiddingBid.query.filter_by(id=bid_id, project_id=project_id).first()
    if not bid:
        return jsonify({'code': 1, 'message': '揭榜申请不存在'}), 404
    project = db.session.get(BiddingProject, project_id)
    if project and project.selected_bid_id == bid.id:
        return jsonify({'code': 1, 'message': '该申请已被确定为揭榜方，不能删除'}), 400
    bidder_name = bid.bidder_name
    db.session.delete(bid)
    if project:
        _add_timeline(project, '【服务】删除揭榜申请：%s' % bidder_name, record_type='service')
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ============================================================
# 里程碑（任务书 / 过程管理核查）
# ============================================================

@admin_bidding_bp.route('/bidding/projects/<int:project_id>/milestones', methods=['POST'])
@dual_login_required
@visitor_block
def create_milestone(project_id):
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'code': 1, 'message': '里程碑内容不能为空'}), 400
    max_sort = db.session.query(db.func.max(BiddingMilestone.sort_order)) \
        .filter_by(project_id=project.id).scalar() or 0
    m = BiddingMilestone(
        project_id=project.id,
        sort_order=max_sort + 1,
        content=content,
        planned_date=_safe_date(data.get('planned_date')),
        actual_date=_safe_date(data.get('actual_date')),
        status=data.get('status', 'pending'),
        result_note=data.get('result_note', ''),
    )
    db.session.add(m)
    db.session.flush()
    _add_timeline(project, '【服务】新增里程碑：%s' % content, record_type='service')
    db.session.commit()
    return jsonify({'code': 0, 'data': m.to_dict(), 'message': '已添加'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/milestones/<int:mid>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_milestone(project_id, mid):
    m = BiddingMilestone.query.filter_by(id=mid, project_id=project_id).first()
    if not m:
        return jsonify({'code': 1, 'message': '里程碑不存在'}), 404
    data = request.get_json(silent=True) or {}
    if data.get('content') is not None:
        m.content = data['content']
    if 'planned_date' in data:
        m.planned_date = _safe_date(data.get('planned_date'))
    if 'actual_date' in data:
        m.actual_date = _safe_date(data.get('actual_date'))
    if 'status' in data:
        m.status = data.get('status')
    if 'result_note' in data:
        m.result_note = data.get('result_note')
    if 'sort_order' in data:
        m.sort_order = int(data.get('sort_order') or 0)
    db.session.commit()
    return jsonify({'code': 0, 'data': m.to_dict(), 'message': '已保存'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/milestones/<int:mid>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_milestone(project_id, mid):
    m = BiddingMilestone.query.filter_by(id=mid, project_id=project_id).first()
    if not m:
        return jsonify({'code': 1, 'message': '里程碑不存在'}), 404
    project = db.session.get(BiddingProject, project_id)
    db.session.delete(m)
    if project:
        _add_timeline(project, '【服务】删除里程碑：%s' % m.content, record_type='service')
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/milestones/<int:mid>/status', methods=['POST'])
@dual_login_required
@visitor_block
def update_milestone_status(project_id, mid):
    """过程管理核查：更新里程碑完成状态并写时间线"""
    m = BiddingMilestone.query.filter_by(id=mid, project_id=project_id).first()
    if not m:
        return jsonify({'code': 1, 'message': '里程碑不存在'}), 404
    data = request.get_json(silent=True) or {}
    status = data.get('status', '')
    if status not in ('pending', 'in_progress', 'done', 'delayed', 'cancelled'):
        return jsonify({'code': 1, 'message': '无效的状态'}), 400
    m.status = status
    if status == 'done':
        m.actual_date = _safe_date(data.get('actual_date')) or date.today()
    if data.get('result_note') is not None:
        m.result_note = data.get('result_note')

    project = BiddingProject.query.get(project_id)
    status_names = {'pending': '待完成', 'in_progress': '进行中', 'done': '已完成',
                    'delayed': '已延期', 'cancelled': '已取消'}
    _add_timeline(project, '【服务】里程碑「%s」更新为：%s' % (m.content, status_names.get(status, status)),
                  record_type='service')
    db.session.commit()
    return jsonify({'code': 0, 'data': m.to_dict(), 'message': '已更新'})


# ============================================================
# 全周期服务跟踪时间线
# ============================================================

@admin_bidding_bp.route('/bidding/projects/<int:project_id>/timeline', methods=['POST'])
@dual_login_required
@visitor_block
def add_timeline(project_id):
    """追加人工服务/跟踪记录（任何阶段可用）"""
    project = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'code': 1, 'message': '记录内容不能为空'}), 400
    t = BiddingTimeline(
        project_id=project.id,
        stage=data.get('stage') or project.current_stage,
        record_type=data.get('record_type', 'service'),
        content=content,
        files=json.dumps(data.get('files', []), ensure_ascii=False),
        record_by=_record_by(),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'code': 0, 'data': t.to_dict(), 'message': '已记录'})


@admin_bidding_bp.route('/bidding/projects/<int:project_id>/timeline/<int:tid>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_timeline(project_id, tid):
    t = BiddingTimeline.query.filter_by(id=tid, project_id=project_id).first()
    if not t:
        return jsonify({'code': 1, 'message': '记录不存在'}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


# ============================================================
# 揭榜方用户管理
# ============================================================

@admin_bidding_bp.route('/bidding/users', methods=['GET'])
@dual_login_required
def list_users():
    users = BiddingUser.query.order_by(BiddingUser.created_at.desc()).all()
    # 附带各用户申请数
    data = []
    for u in users:
        d = u.to_dict()
        d['bid_count'] = BiddingBid.query.filter_by(user_id=u.id).count()
        data.append(d)
    return jsonify({'code': 0, 'data': data})


@admin_bidding_bp.route('/bidding/users/<int:user_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_user(user_id):
    user = BiddingUser.query.get(user_id)
    if not user:
        return jsonify({'code': 1, 'message': '用户不存在'}), 404
    data = request.get_json(silent=True) or {}
    if 'is_active' in data:
        user.is_active = bool(data.get('is_active'))
    if data.get('org_name') is not None:
        user.org_name = data.get('org_name')
    if data.get('contact_name') is not None:
        user.contact_name = data.get('contact_name')
    if data.get('contact_phone') is not None:
        user.contact_phone = data.get('contact_phone')
    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '已保存'})


# ============================================================
# 企业档案管理（1 企业可发布多个需求）
# ============================================================

@admin_bidding_bp.route('/bidding/enterprises', methods=['GET'])
@dual_login_required
def list_enterprises():
    search = request.args.get('search', '').strip()
    q = BiddingEnterprise.query
    if search:
        q = q.filter(BiddingEnterprise.org_name.ilike(f'%{search}%'))
    enterprises = q.order_by(BiddingEnterprise.updated_at.desc()).all()
    return jsonify({'code': 0, 'data': [e.to_dict() for e in enterprises]})


@admin_bidding_bp.route('/bidding/enterprises', methods=['POST'])
@dual_login_required
@visitor_block
def create_enterprise():
    data = request.get_json(silent=True) or {}
    org_name = (data.get('org_name') or '').strip()
    if not org_name:
        return jsonify({'code': 1, 'message': '企业名称不能为空'}), 400
    existing = BiddingEnterprise.query.filter_by(org_name=org_name).first()
    if existing:
        return jsonify({'code': 1, 'message': f'企业「{org_name}」已存在，请直接选择'}), 400
    ent = BiddingEnterprise(org_name=org_name)
    for field in _ENTERPRISE_FIELDS:
        val = data.get(field)
        if val is not None:
            setattr(ent, field, val)
    ent.contact_name = data.get('contact_name', '')
    ent.contact_phone = data.get('contact_phone', '')
    db.session.add(ent)
    db.session.commit()
    return jsonify({'code': 0, 'data': ent.to_dict(), 'message': '企业档案已创建'})


@admin_bidding_bp.route('/bidding/enterprises/<int:ent_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_enterprise(ent_id):
    ent = db.session.get(BiddingEnterprise, ent_id)
    if not ent:
        return jsonify({'code': 1, 'message': '企业不存在'}), 404
    data = request.get_json(silent=True) or {}
    if data.get('org_name') is not None:
        org_name = (data.get('org_name') or '').strip()
        if not org_name:
            return jsonify({'code': 1, 'message': '企业名称不能为空'}), 400
        ent.org_name = org_name
    for field in _ENTERPRISE_FIELDS:
        val = data.get(field)
        if val is not None:
            setattr(ent, field, val)
    if data.get('contact_name') is not None:
        ent.contact_name = data.get('contact_name')
    if data.get('contact_phone') is not None:
        ent.contact_phone = data.get('contact_phone')
    db.session.commit()
    return jsonify({'code': 0, 'data': ent.to_dict(), 'message': '企业档案已更新'})


# ============================================================
# 看板统计
# ============================================================

@admin_bidding_bp.route('/bidding/stats', methods=['GET'])
@dual_login_required
def stats():
    """七步漏斗统计 + 超期榜单 + 待办清单"""
    projects = BiddingProject.query.filter_by(is_deleted=False).all()
    _resolve_names(projects)

    stage_counts = {}
    for s in STAGES:
        stage_counts[s['key']] = 0
    terminal_counts = {'rejected': 0, 'failed': 0, 'cancelled': 0}
    for p in projects:
        if p.current_stage in stage_counts:
            stage_counts[p.current_stage] += 1
        elif p.current_stage in terminal_counts:
            terminal_counts[p.current_stage] += 1

    today = date.today()

    # 超期：已发布且超过截止日期仍未截止（still stage3 published）
    overdue_publish = []
    # 超期：里程碑 planned_date 已过且未完成
    overdue_milestones = []
    for p in projects:
        if p.current_stage == 'stage3' and p.publish_status == 'published' \
                and p.deadline_date and p.deadline_date < today:
            d = _build_project_dict(p)
            d['overdue_days'] = (today - p.deadline_date).days
            overdue_publish.append(d)
        for m in p.milestones.all():
            if m.status in ('pending', 'in_progress') and m.planned_date and m.planned_date < today:
                overdue_milestones.append({
                    'project_id': p.id,
                    'project_title': p.title,
                    'milestone_id': m.id,
                    'content': m.content,
                    'planned_date': _safe_date_str(m.planned_date),
                    'overdue_days': (today - m.planned_date).days,
                    'status': m.status,
                })

    return jsonify({'code': 0, 'data': {
        'total': len(projects),
        'stage_counts': stage_counts,
        'terminal_counts': terminal_counts,
        'stages': STAGES,
        'overdue_publish': overdue_publish[:20],
        'overdue_milestones': overdue_milestones[:20],
        'projects': [_build_project_dict(p) for p in projects],
    }})
