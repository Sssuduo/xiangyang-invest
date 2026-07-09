import json
import os
import threading
from datetime import date, datetime, timedelta
from flask import request, jsonify
from models import InvestmentLead, InvestmentProject, EnterpriseDemand
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict, Staff, LLMModel
from models import KnowledgeEntry, LeadAssessmentSession, LeadAssessmentMessage, KnowledgeDraft, KnowledgeUsageStat
from extensions import db
from routes import admin_lead_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes
from services.llm_service import call_llm, build_messages, call_llm_with_web_search
from services.word_service import generate_assessment_docx
from services.html_service import generate_assessment_html


def _renumber_leads():
    """将线索序号重新编排为连续整数"""
    leads = InvestmentLead.query.filter_by(is_deleted=False)\
        .order_by(InvestmentLead.order_no.asc(), InvestmentLead.id.asc()).all()
    for i, p in enumerate(leads, 1):
        if p.order_no != i:
            p.order_no = i


def _renumber_investment_projects():
    """重新编排招商项目序号"""
    projects = InvestmentProject.query.filter_by(is_deleted=False)\
        .order_by(InvestmentProject.order_no.asc(), InvestmentProject.id.asc()).all()
    for i, p in enumerate(projects, 1):
        if p.order_no != i:
            p.order_no = i


def _parse_date(val):
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

@admin_lead_bp.route('/lead/dicts', methods=['GET'])
@dual_login_required
def get_dicts():
    """获取所有字典数据（与 investment 相同的引用字典 + 诉求类型）"""
    return jsonify({
        'code': 0,
        'data': {
            'follow_statuses': [d.to_dict() for d in FollowStatusDict.query.order_by(FollowStatusDict.sort_order).all()],
            'meeting_statuses': [d.to_dict() for d in MeetingStatusDict.query.order_by(MeetingStatusDict.sort_order).all()],
            'organizations': [d.to_dict() for d in OrganizationDict.query.filter_by(is_active=True).order_by(OrganizationDict.sort_order).all()],
            'project_types': [d.to_dict() for d in ProjectTypeDict.query.filter_by(is_active=True).order_by(ProjectTypeDict.sort_order).all()],
            'demand_types': [d.to_dict() for d in DemandTypeDict.query.filter_by(is_active=True).order_by(DemandTypeDict.sort_order).all()],
            'project_tags': [d.to_dict() for d in ProjectTagDict.query.filter_by(is_active=True).order_by(ProjectTagDict.sort_order).all()],
            'staff': [d.to_dict() for d in Staff.query.filter_by(is_active=True).order_by(Staff.sort_order).all()]
        }
    })


@admin_lead_bp.route('/lead/max-order-no', methods=['GET'])
@dual_login_required
def get_max_order_no():
    max_no = db.session.query(db.func.max(InvestmentLead.order_no))\
        .filter_by(is_deleted=False).scalar() or 0
    return jsonify({'code': 0, 'data': {'max_order_no': max_no}})


# ============================================================
# 线索 CRUD
# ============================================================

@admin_lead_bp.route('/lead/leads', methods=['GET'])
@dual_login_required
def list_leads():
    """线索列表（含搜索/筛选）"""
    search = request.args.get('search', '').strip()
    follow_status = request.args.get('follow_status', '').strip()
    project_type = request.args.get('project_type', '').strip()
    converted_filter = request.args.get('converted', '').strip()  # 'yes' / 'no' / ''

    q = InvestmentLead.query.filter_by(is_deleted=False)

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            InvestmentLead.project_name.ilike(like),
            InvestmentLead.invest_enterprise.ilike(like),
            InvestmentLead.project_content.ilike(like),
            InvestmentLead.person_in_charge.ilike(like)
        ))

    if follow_status:
        codes = [c.strip() for c in follow_status.split(',') if c.strip()]
        if len(codes) == 1:
            q = q.filter_by(follow_status_code=codes[0])
        elif len(codes) > 1:
            q = q.filter(InvestmentLead.follow_status_code.in_(codes))

    if project_type:
        q = q.filter_by(project_type_code=project_type)

    if converted_filter == 'yes':
        q = q.filter(InvestmentLead.converted_project_id.isnot(None))
    elif converted_filter == 'no':
        q = q.filter(InvestmentLead.converted_project_id.is_(None))

    q = q.order_by(
        db.case((InvestmentLead.follow_status_code == 'follow_focus', 0), else_=1),
        InvestmentLead.order_no.asc(),
        InvestmentLead.created_at.desc()
    )

    leads = q.all()

    # 预加载字典名称映射
    follow_map = {d.code: d for d in FollowStatusDict.query.all()}
    org_map = {d.code: d for d in OrganizationDict.query.all()}
    type_map = {d.code: d for d in ProjectTypeDict.query.all()}

    # 预加载 staff 映射
    all_leader_ids = set()
    for p in leads:
        if p.team_leader_ids:
            try:
                ids = json.loads(p.team_leader_ids)
                all_leader_ids.update(ids)
            except Exception:
                pass
    staff_map = {}
    if all_leader_ids:
        staff_map = {s.id: s.name for s in Staff.query.filter(Staff.id.in_(list(all_leader_ids))).all()}

    # 预加载已转换项目名称
    converted_ids = [p.converted_project_id for p in leads if p.converted_project_id]
    converted_map = {}
    if converted_ids:
        projs = InvestmentProject.query.filter(InvestmentProject.id.in_(converted_ids)).all()
        converted_map = {p.id: p.project_name for p in projs}

    result = []
    for p in leads:
        d = p.to_dict()
        # 解析字典名称
        fu = follow_map.get(p.follow_status_code)
        d['follow_status_name'] = fu.name if fu else ''
        d['follow_status_color'] = fu.display_color if fu else '#909399'
        ou = org_map.get(p.recommend_unit_code)
        d['recommend_unit_name'] = ou.name if ou else ''
        ou2 = org_map.get(p.responsible_unit_code)
        d['responsible_unit_name'] = ou2.name if ou2 else ''
        tu = type_map.get(p.project_type_code)
        d['project_type_name'] = tu.name if tu else ''

        leader_ids = d.get('team_leader_ids', [])
        d['team_leader_names'] = [staff_map.get(sid, str(sid)) for sid in leader_ids]
        if p.converted_project_id:
            d['converted_project_name'] = converted_map.get(p.converted_project_id, '')
        result.append(d)

    return jsonify({'code': 0, 'data': result})


@admin_lead_bp.route('/lead/leads', methods=['POST'])
@dual_login_required
@visitor_block
def create_lead():
    """新建线索"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    required = ['project_name', 'invest_enterprise', 'enterprise_info', 'project_content',
                'project_type_code']
    for field in required:
        if not data.get(field):
            return jsonify({'code': 1, 'message': f'{field} 为必填字段'}), 400

    lead = InvestmentLead(
        order_no=data.get('order_no', 0),
        project_name=data['project_name'],
        invest_enterprise=data['invest_enterprise'],
        enterprise_info=data['enterprise_info'],
        project_content=data['project_content'],
        invest_amount=data.get('invest_amount', 0),
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

    db.session.add(lead)
    db.session.flush()

    # 创建企业诉求子数据
    for i, d in enumerate(data.get('demands', []) or []):
        if d.get('demand_content', '').strip():
            db.session.add(EnterpriseDemand(
                project_id=None,
                lead_id=lead.id,
                demand_type_code=d.get('demand_type_code', ''),
                demand_content=d['demand_content'],
                resolution=d.get('resolution', ''),
                unit_code=d.get('unit_code', ''),
                status=d.get('status', 'pending'),
                sort_order=i + 1
            ))

    user_info = get_current_user_info()
    if user_info:
        changes = {}
        for field in ['order_no', 'project_name', 'invest_enterprise', 'enterprise_info',
                      'project_content', 'invest_amount', 'follow_status_code',
                      'meeting_status_code', 'recommend_unit_code', 'responsible_unit_code',
                      'project_type_code', 'person_in_charge', 'person_in_charge_phone',
                      'project_doc', 'investment_plan', 'conclusion']:
            changes[field] = (None, getattr(lead, field))
        changes['first_contact_date'] = (None, lead.first_contact_date.isoformat() if lead.first_contact_date else None)
        changes['tags'] = (None, json.dumps(data.get('tags', []), ensure_ascii=False))
        changes['team_leader_ids'] = (None, json.dumps(data.get('team_leader_ids', []), ensure_ascii=False))
        log_changes('investment_leads', lead.id, changes, 'create', user_info)

    _renumber_leads()
    db.session.commit()
    return jsonify({'code': 0, 'data': lead.to_dict(), 'message': '线索创建成功'})


@admin_lead_bp.route('/lead/leads/<int:lead_id>', methods=['GET'])
@dual_login_required
def get_lead(lead_id):
    """获取线索详情（含字典名称解析 + 企业诉求）"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    data = lead.to_dict()

    # 解析字典名称
    follow_map = {d.code: d for d in FollowStatusDict.query.all()}
    meeting_map = {d.code: d for d in MeetingStatusDict.query.all()}
    org_map = {d.code: d for d in OrganizationDict.query.all()}
    type_map = {d.code: d for d in ProjectTypeDict.query.all()}

    fu = follow_map.get(lead.follow_status_code)
    data['follow_status_name'] = fu.name if fu else ''
    data['follow_status_color'] = fu.display_color if fu else '#909399'
    mu = meeting_map.get(lead.meeting_status_code)
    data['meeting_status_name'] = mu.name if mu else ''
    data['meeting_status_color'] = mu.display_color if mu else '#909399'
    ou = org_map.get(lead.recommend_unit_code)
    data['recommend_unit_name'] = ou.name if ou else ''
    ou2 = org_map.get(lead.responsible_unit_code)
    data['responsible_unit_name'] = ou2.name if ou2 else ''
    tu = type_map.get(lead.project_type_code)
    data['project_type_name'] = tu.name if tu else ''

    # 解析标签名称
    if data.get('tags'):
        tag_map = {d.code: d.name for d in ProjectTagDict.query.all()}
        data['tag_names'] = [tag_map.get(t, t) for t in data['tags']]

    # 解析专班负责人名称
    if data.get('team_leader_ids'):
        staff_map = {s.id: s.name for s in Staff.query.filter(Staff.id.in_(data['team_leader_ids'])).all()}
        data['team_leader_names'] = [staff_map.get(sid, str(sid)) for sid in data['team_leader_ids']]

    # 加载企业诉求
    demands = EnterpriseDemand.query.filter_by(lead_id=lead_id)\
        .order_by(EnterpriseDemand.sort_order).all()
    demand_type_map = {}
    all_demand_types = DemandTypeDict.query.all()
    for dt in all_demand_types:
        parent = dt.parent_code or ''
        if parent:
            demand_type_map[dt.code] = dt.name
    # 构建二级显示名
    parent_map = {d.code: d.name for d in all_demand_types if not d.parent_code}
    demand_display_map = {}
    for dt in all_demand_types:
        if dt.parent_code and dt.parent_code in parent_map:
            demand_display_map[dt.code] = f'{parent_map[dt.parent_code]}：{dt.name}'
        else:
            demand_display_map[dt.code] = dt.name

    data['demands'] = []
    for d in demands:
        dd = d.to_dict()
        codes = [c.strip() for c in (dd.get('demand_type_code') or '').split(',') if c.strip()]
        dd['demand_type_name'] = '、'.join([demand_display_map.get(c, c) for c in codes]) if codes else ''
        du = org_map.get(dd.get('unit_code'))
        dd['unit_name'] = du.name if du else ''
        data['demands'].append(dd)

    # 已转换项目名称
    if lead.converted_project_id:
        proj = InvestmentProject.query.get(lead.converted_project_id)
        if proj:
            data['converted_project_name'] = proj.project_name

    return jsonify({'code': 0, 'data': data})


@admin_lead_bp.route('/lead/leads/<int:lead_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_lead(lead_id):
    """更新线索"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    new_order_no = data.get('order_no')
    force_reorder = data.pop('force_reorder', False)
    if new_order_no is not None and new_order_no != lead.order_no:
        conflict = InvestmentLead.query.filter(
            InvestmentLead.id != lead_id,
            InvestmentLead.order_no == new_order_no,
            InvestmentLead.is_deleted == False
        ).first()
        if conflict and not force_reorder:
            return jsonify({
                'code': 2,
                'message': f'顺序号 {new_order_no} 已被线索「{conflict.project_name}」使用',
                'data': {'conflict_project': conflict.project_name}
            })
        elif conflict and force_reorder:
            targets = InvestmentLead.query.filter(
                InvestmentLead.id != lead_id,
                InvestmentLead.order_no >= new_order_no,
                InvestmentLead.is_deleted == False
            ).order_by(InvestmentLead.order_no.desc()).all()
            for t in targets:
                t.order_no += 1

    updatable_fields = [
        'order_no', 'project_name', 'invest_enterprise', 'enterprise_info',
        'project_content', 'invest_amount', 'follow_status_code',
        'meeting_status_code', 'recommend_unit_code', 'responsible_unit_code',
        'project_type_code', 'person_in_charge', 'person_in_charge_phone',
        'project_doc', 'investment_plan', 'conclusion', 'tags', 'team_leader_ids',
        'first_contact_date'
    ]

    user_info = get_current_user_info()
    old_values = {}
    if user_info:
        for field in updatable_fields:
            old_val = getattr(lead, field)
            if field == 'first_contact_date':
                old_val = old_val.isoformat() if old_val else None
            elif field == 'tags':
                old_val = json.dumps(json.loads(old_val) if old_val else [], ensure_ascii=False) if old_val else '[]'
            elif field == 'team_leader_ids':
                old_val = json.dumps(json.loads(old_val) if old_val else [], ensure_ascii=False) if old_val else '[]'
            old_values[field] = old_val

    project_changed = False
    for field in updatable_fields:
        if field not in data:
            continue
        val = data[field]
        if field == 'first_contact_date':
            val = _parse_date(val)
            old_cmp = old_values.get(field) if user_info else None
            new_cmp = val.isoformat() if val else None
            changed = (old_cmp != new_cmp)
        elif field in ('tags', 'team_leader_ids'):
            old_str = old_values.get(field, '[]') if user_info else '[]'
            new_str = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            changed = (old_str != new_str)
        else:
            changed = (str(old_values.get(field) or '') != str(val or '')) if user_info else True

        if user_info and not changed:
            continue
        setattr(lead, field, val)
        project_changed = True

    if user_info:
        changes = {}
        for field in updatable_fields:
            old_val = old_values.get(field)
            new_val = getattr(lead, field)
            if field == 'first_contact_date':
                new_val = new_val.isoformat() if new_val else None
            elif field == 'tags':
                new_val = json.dumps(json.loads(new_val) if new_val else [], ensure_ascii=False) if new_val else '[]'
            elif field == 'team_leader_ids':
                new_val = json.dumps(json.loads(new_val) if new_val else [], ensure_ascii=False) if new_val else '[]'
            if str(old_val) != str(new_val):
                changes[field] = (old_val, new_val)
        log_changes('investment_leads', lead_id, changes, 'update', user_info)

    # 同步企业诉求：先删后建
    if 'demands' in data:
        EnterpriseDemand.query.filter_by(lead_id=lead_id).delete()
        for i, d in enumerate(data['demands'] or []):
            if d.get('demand_content', '').strip():
                db.session.add(EnterpriseDemand(
                    project_id=None,
                    lead_id=lead_id,
                    demand_type_code=d.get('demand_type_code', ''),
                    demand_content=d['demand_content'],
                    resolution=d.get('resolution', ''),
                    unit_code=d.get('unit_code', ''),
                    status=d.get('status', 'pending'),
                    sort_order=i + 1
                ))

    _renumber_leads()
    db.session.commit()
    return jsonify({'code': 0, 'data': lead.to_dict(), 'message': '更新成功'})


@admin_lead_bp.route('/lead/leads/<int:lead_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_lead(lead_id):
    """逻辑删除线索"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    lead.is_deleted = True
    _renumber_leads()
    db.session.commit()
    return jsonify({'code': 0, 'message': '线索已删除'})


@admin_lead_bp.route('/lead/leads/batch-delete', methods=['POST'])
@dual_login_required
@visitor_block
def batch_delete_leads():
    """批量删除线索"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'code': 1, 'message': '请提供要删除的线索ID列表'}), 400

    InvestmentLead.query.filter(
        InvestmentLead.id.in_(ids),
        InvestmentLead.is_deleted == False
    ).update({'is_deleted': True}, synchronize_session=False)
    _renumber_leads()
    db.session.commit()
    return jsonify({'code': 0, 'message': f'已删除 {len(ids)} 条线索'})


# ============================================================
# AI 研判
# ============================================================

def _build_lead_context(lead):
    """构建线索信息文本块（V3：含企业诉求，不含推介单位）"""
    parts = []
    parts.append(f'【企业名称】{lead.invest_enterprise}')
    parts.append(f'【项目名称】{lead.project_name}')
    parts.append(f'【企业简介】{lead.enterprise_info}')
    parts.append(f'【项目内容】{lead.project_content}')

    invest_amount = float(lead.invest_amount) if lead.invest_amount else 0
    parts.append(f'【投资金额】{invest_amount} 万元')

    # 项目类型名称
    ptype = ProjectTypeDict.query.filter_by(code=lead.project_type_code).first()
    parts.append(f'【项目类型】{ptype.name if ptype else lead.project_type_code}')

    if lead.first_contact_date:
        parts.append(f'【首次对接日期】{lead.first_contact_date.isoformat()}')

    # 附件文档
    if lead.project_doc:
        try:
            docs = json.loads(lead.project_doc)
            if docs:
                doc_names = [os.path.basename(d) for d in docs]
                parts.append(f'【附件文档】{", ".join(doc_names)}')
        except Exception:
            pass

    if lead.investment_plan:
        try:
            plans = json.loads(lead.investment_plan)
            if plans:
                plan_names = [os.path.basename(p) for p in plans]
                parts.append(f'【投资计划书】{", ".join(plan_names)}')
        except Exception:
            pass

    # 企业诉求
    demands = EnterpriseDemand.query.filter_by(lead_id=lead.id)\
        .order_by(EnterpriseDemand.sort_order).all()
    if demands:
        parts.append('')
        parts.append('【企业诉求】')
        demand_type_map = {}
        for dt in DemandTypeDict.query.all():
            if dt.parent_code:
                parent = next((d.name for d in DemandTypeDict.query.all() if d.code == dt.parent_code), '')
                demand_type_map[dt.code] = f'{parent}：{dt.name}' if parent else dt.name
            else:
                demand_type_map[dt.code] = dt.name
        for i, d in enumerate(demands, 1):
            codes = [c.strip() for c in (d.demand_type_code or '').split(',') if c.strip()]
            type_names = [demand_type_map.get(c, c) for c in codes]
            type_display = '、'.join(type_names) if type_names else '未分类'
            parts.append(f'{i}. [{type_display}] {d.demand_content}')
            if d.resolution:
                parts.append(f'   └ 拟解决措施：{d.resolution}')

    return '\n'.join(parts)


def _build_lead_search_text(lead):
    """构建用于知识库语义搜索的查询文本"""
    parts = []
    if lead.invest_enterprise:
        parts.append(lead.invest_enterprise)
    if lead.project_name:
        parts.append(lead.project_name)
    if lead.project_content:
        # 取前 300 字作为搜索 query（向量化有 token 限制）
        parts.append(lead.project_content[:300])
    if lead.project_type_code:
        ptype = ProjectTypeDict.query.filter_by(code=lead.project_type_code).first()
        if ptype:
            parts.append(ptype.name)
    return ' '.join(parts)


def _build_embedding_config(model):
    """从 LLMModel 构建 embedding 服务所需的配置字典"""
    return {
        'api_base_url': model.api_base_url,
        'api_key': model.api_key,
        'model_name': model.model_name,
        'embedding_api_url': model.embedding_api_url or '',
        'embedding_api_key': model.embedding_api_key or '',
        'embedding_model_name': model.embedding_model_name or '',
    }


def _build_assessment_messages(lead_context, knowledge_context, prompt_template, system_prompt):
    """构建 OpenAI 兼容 messages 数组"""
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    full_prompt = prompt_template.replace('{{lead_context}}', lead_context)
    full_prompt = full_prompt.replace('{{knowledge_context}}', knowledge_context)
    messages.append({'role': 'user', 'content': full_prompt})
    return messages


CATEGORY_NAMES = {
    'industry_policy': '产业政策', 'park_info': '园区信息', 'supporting': '配套能力',
    'land_cost': '土地成本', 'case_study': '招商案例', 'demand_pattern': '企业诉求',
    'market_data': '市场数据', 'competitor': '周边竞争'
}


def _search_knowledge(lead):
    """V2：向量语义检索 + LIKE 关键词回退"""
    from services.embedding_service import search_by_embedding
    from datetime import datetime

    # 选择可用的 LLM 模型（用于向量化）
    model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
    model_config = None
    if model:
        model_config = _build_embedding_config(model)

    entries = KnowledgeEntry.query.filter_by(is_active=True).all()
    if not entries:
        return '（暂无相关知识库条目）'

    # 分离已向量化和未向量化的条目
    vec_entries = [e for e in entries if e.embedding]
    raw_entries = [e for e in entries if not e.embedding]

    # 主路径：向量语义搜索
    scored = []
    if model_config and vec_entries:
        try:
            query_text = _build_lead_search_text(lead)
            scored = search_by_embedding(query_text, vec_entries, model_config, top_k=5, min_score=0.3)
        except Exception:
            scored = []

    # 回退路径：LIKE 关键词搜索（兜底未向量化的条目 + 向量结果不足时补充）
    if len(scored) < 5 and raw_entries:
        keyword_results = _keyword_search(lead, raw_entries, len(raw_entries))
        # 给 LIKE 结果一个默认较低的分数
        for i, entry in enumerate(keyword_results):
            default_score = 0.5 - (i * 0.05)
            if not any(e.id == entry.id for e, _ in scored):
                scored.append((entry, default_score))

    # 限制返回 5 条
    scored = scored[:5]

    # 如果向量和关键词都没搜到，兜底返回前几条活跃条目
    if not scored:
        default_entries = KnowledgeEntry.query.filter_by(is_active=True)\
            .order_by(KnowledgeEntry.sort_order).limit(3).all()
        for e in default_entries:
            scored.append((e, 0.3))

    # 更新检索计数和使用时间
    now = datetime.utcnow()
    for entry, _ in scored:
        entry.search_count = (entry.search_count or 0) + 1
        entry.last_used_at = now
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return _format_knowledge_entries(scored)


def _keyword_search(lead, entries, limit=5):
    """原有的 LIKE 关键词搜索（作为兜底）"""
    keywords = []
    if lead.project_name:
        keywords.append(lead.project_name)
    if lead.invest_enterprise:
        keywords.append(lead.invest_enterprise)
    if lead.project_type_code:
        ptype = ProjectTypeDict.query.filter_by(code=lead.project_type_code).first()
        if ptype:
            keywords.append(ptype.name)
    if lead.project_content:
        keywords.append(lead.project_content[:100])

    keywords = [k for k in keywords if len(k) >= 2]

    if not keywords:
        return sorted(entries, key=lambda e: e.sort_order)[:limit]

    results = []
    for entry in entries:
        text = f'{entry.title} {entry.content or ""} {entry.tags or ""}'.lower()
        match_count = 0
        for kw in keywords:
            if kw.lower() in text:
                match_count += 1
        if match_count > 0:
            results.append((entry, match_count))

    results.sort(key=lambda x: x[1], reverse=True)
    return [e for e, _ in results[:limit]]


def _format_knowledge_entries(scored):
    """格式化知识条目为 prompt 文本，含相关性评分"""
    parts = []
    for i, (entry, score) in enumerate(scored, 1):
        parts.append(f'### [{i}] {entry.title}')
        parts.append(f'【相关性评分】{score:.2f}  |  【分类】{CATEGORY_NAMES.get(entry.category, entry.category)}  |  【来源】{entry.source or "内部资料"}')
        parts.append(entry.content)
        parts.append('')
    return '\n'.join(parts)


def _run_assessment_async(app, lead_id, model_id):
    """在后台线程中执行 AI 研判"""
    with app.app_context():
        lead = InvestmentLead.query.get(lead_id)
        if not lead or lead.ai_assessment_status == 'running':
            return

        try:
            lead.ai_assessment_status = 'running'
            db.session.commit()

            # 选择模型
            if model_id:
                model = LLMModel.query.get(model_id)
            else:
                model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
            if not model:
                lead.ai_assessment_status = 'failed'
                db.session.commit()
                return

            # 加载提示词模板
            row = db.session.execute(
                db.text("SELECT value FROM app_config WHERE key='lead_assessment_prompt'")
            ).fetchone()
            if row:
                prompt_template = row[0]
            else:
                from seed_data import DEFAULT_LEAD_ASSESSMENT_PROMPT
                prompt_template = DEFAULT_LEAD_ASSESSMENT_PROMPT

            system_prompt = model.system_prompt or '你是一个专业的招商分析助手。请根据提供的企业信息进行客观、全面的分析。'
            lead_context = _build_lead_context(lead)
            knowledge_context = _search_knowledge(lead)
            messages = _build_assessment_messages(lead_context, knowledge_context, prompt_template, system_prompt)

            # 旧版异步研判也支持两阶段搜索
            if model.search_model_id:
                search_model = LLMModel.query.get(model.search_model_id)
            else:
                search_model = None

            if search_model and search_model.api_key:
                resp = call_llm_with_web_search(
                    main_config={
                        'api_base_url': model.api_base_url,
                        'api_key': model.api_key,
                        'model_name': model.model_name,
                        'provider': model.provider
                    },
                    search_config={
                        'api_base_url': search_model.api_base_url,
                        'api_key': search_model.api_key,
                        'model_name': search_model.model_name
                    },
                    messages=messages,
                    temperature=model.temperature,
                    max_tokens=model.max_tokens,
                    lead_context=lead_context
                )
                result = resp['result']
            else:
                result = call_llm(
                    model_config={
                        'api_base_url': model.api_base_url,
                        'api_key': model.api_key,
                        'model_name': model.model_name,
                        'provider': model.provider
                    },
                    messages=messages,
                    temperature=model.temperature,
                    max_tokens=model.max_tokens
                )

            lead.ai_assessment_result = result
            lead.ai_assessment_at = datetime.utcnow()
            lead.ai_model_id = model.id
            lead.assessment_prompt_used = prompt_template
            lead.ai_assessment_status = 'completed'
            db.session.commit()

        except Exception:
            lead.ai_assessment_status = 'failed'
            db.session.commit()


@admin_lead_bp.route('/lead/leads/<int:lead_id>/assess', methods=['POST'])
@dual_login_required
@visitor_block
def assess_lead(lead_id):
    """异步 AI 评估招商线索"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()

    # 防止重复触发
    if lead.ai_assessment_status == 'running':
        return jsonify({'code': 1, 'message': '该线索正在研判中，请稍后再试'}), 400

    data = request.get_json() or {}
    model_id = data.get('model_id')

    # 标记为 pending（即将启动）
    lead.ai_assessment_status = 'pending'
    db.session.commit()

    # 启动后台线程执行研判
    from flask import current_app
    app = current_app._get_current_object()
    thread = threading.Thread(target=_run_assessment_async, args=(app, lead_id, model_id), daemon=True)
    thread.start()

    return jsonify({
        'code': 0,
        'data': {'status': 'pending'},
        'message': '研判已开始，完成后将自动保存结果'
    })


@admin_lead_bp.route('/lead/leads/<int:lead_id>/assessment-status', methods=['GET'])
@dual_login_required
def get_assessment_status(lead_id):
    """查询研判状态（供前端轮询）"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    result = {'status': lead.ai_assessment_status or 'pending'}
    if lead.ai_assessment_status == 'completed':
        result['assessment_result'] = lead.ai_assessment_result or ''
        result['assessed_at'] = lead.ai_assessment_at.isoformat() if lead.ai_assessment_at else None
        result['model_id'] = lead.ai_model_id
    return jsonify({'code': 0, 'data': result})


@admin_lead_bp.route('/lead/leads/<int:lead_id>/prompt-preview', methods=['GET'])
@dual_login_required
def get_prompt_preview(lead_id):
    """获取研判提示词预览（供前端复制），支持 model_id 参数"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()

    # 加载提示词模板
    row = db.session.execute(
        db.text("SELECT value FROM app_config WHERE key='lead_assessment_prompt'")
    ).fetchone()
    if row:
        prompt_template = row[0]
    else:
        from seed_data import DEFAULT_LEAD_ASSESSMENT_PROMPT
        prompt_template = DEFAULT_LEAD_ASSESSMENT_PROMPT

    # 选择模型（可选传入 model_id，否则取默认活跃模型）
    model_id = request.args.get('model_id', type=int)
    if model_id:
        model = LLMModel.query.get(model_id)
    else:
        model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()

    system_prompt = ''
    if model:
        system_prompt = model.system_prompt or '你是一个专业的招商分析助手。请根据提供的企业信息进行客观、全面的分析。'

    lead_context = _build_lead_context(lead)
    knowledge_context = _search_knowledge(lead)
    full_prompt = prompt_template.replace('{{lead_context}}', lead_context)
    full_prompt = full_prompt.replace('{{knowledge_context}}', knowledge_context)

    return jsonify({
        'code': 0,
        'data': {
            'prompt_text': full_prompt,
            'lead_name': lead.project_name,
            'knowledge_count': len(knowledge_context) if knowledge_context else 0,
            'system_prompt': system_prompt,
            'model_name': model.name if model else ''
        }
    })


# ============================================================
# AI 研判会话管理（V3：独立侧滑页 + Word文档 + 对话追问）
# ============================================================

def _build_assessment_messages_full(session_id):
    """从会话历史构建完整的 messages 数组"""
    msgs = LeadAssessmentMessage.query.filter_by(session_id=session_id)\
        .order_by(LeadAssessmentMessage.created_at.asc()).all()
    messages = []
    for m in msgs:
        messages.append({'role': m.role, 'content': m.content})
    return messages


def _run_session_assessment(lead, session, model, messages):
    """执行研判并生成 Word 文档，追加 assistant 消息到会话"""
    result = call_llm(
        model_config={
            'api_base_url': model.api_base_url,
            'api_key': model.api_key,
            'model_name': model.model_name
        },
        messages=messages,
        temperature=model.temperature,
        max_tokens=model.max_tokens
    )

    # 生成 Word 文档
    file_url, file_name = generate_assessment_docx(
        lead.project_name,
        lead.invest_enterprise,
        result
    )

    # 追加 assistant 消息
    msg = LeadAssessmentMessage(
        session_id=session.id,
        role='assistant',
        content=result,
        file_path=file_url,
        file_name=file_name
    )
    db.session.add(msg)
    session.updated_at = datetime.utcnow()
    db.session.commit()

    return msg


@admin_lead_bp.route('/lead/leads/<int:lead_id>/assessment-sessions', methods=['POST'])
@dual_login_required
@visitor_block
def create_assessment_session(lead_id):
    """创建研判会话并执行首次研判"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    data = request.get_json() or {}
    model_id = data.get('model_id')

    # 选择模型
    if model_id:
        model = LLMModel.query.get(model_id)
    else:
        model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
    if not model:
        return jsonify({'code': 1, 'message': '没有可用的 AI 模型，请先配置模型'}), 400

    # 加载提示词模板
    row = db.session.execute(
        db.text("SELECT value FROM app_config WHERE key='lead_assessment_prompt'")
    ).fetchone()
    if row:
        prompt_template = row[0]
    else:
        from seed_data import DEFAULT_LEAD_ASSESSMENT_PROMPT
        prompt_template = DEFAULT_LEAD_ASSESSMENT_PROMPT

    system_prompt = model.system_prompt or '你是一个专业的招商分析助手。请根据提供的企业信息进行客观、全面的分析。'
    lead_context = _build_lead_context(lead)
    knowledge_context = _search_knowledge(lead)
    messages = _build_assessment_messages(lead_context, knowledge_context, prompt_template, system_prompt)

    # 创建会话
    session = LeadAssessmentSession(
        lead_id=lead_id,
        model_id=model.id,
        title=f'AI 研判 · {lead.project_name}'
    )
    db.session.add(session)
    db.session.flush()

    # 保存用户消息（完整提示词）
    user_content = messages[-1]['content'] if messages else ''
    user_msg = LeadAssessmentMessage(
        session_id=session.id,
        role='user',
        content=user_content
    )
    db.session.add(user_msg)
    db.session.commit()

    try:
        # 判断是否有关联的搜索模型
        search_model = None
        if model.search_model_id:
            search_model = LLMModel.query.get(model.search_model_id)

        # 使用两阶段管线（联网搜索 → DeepSeek 合成）
        if search_model and search_model.api_key:
            main_config = {
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name
            }
            search_config = {
                'api_base_url': search_model.api_base_url,
                'api_key': search_model.api_key,
                'model_name': search_model.model_name
            }
            resp = call_llm_with_web_search(
                main_config=main_config,
                search_config=search_config,
                messages=messages,
                temperature=model.temperature,
                max_tokens=model.max_tokens,
                lead_context=lead_context
            )
            result = resp['result']
        else:
            result = call_llm(
                model_config={
                    'api_base_url': model.api_base_url,
                    'api_key': model.api_key,
                    'model_name': model.model_name
                },
                messages=messages,
                temperature=model.temperature,
                max_tokens=model.max_tokens
            )

        # 生成 Word 文档
        file_url, file_name = generate_assessment_docx(
            lead.project_name,
            lead.invest_enterprise,
            result
        )

        # 生成 HTML 报告
        html_url, html_file_name = generate_assessment_html(
            lead.project_name,
            lead.invest_enterprise,
            result
        )

        # 追加 assistant 消息
        assistant_msg = LeadAssessmentMessage(
            session_id=session.id,
            role='assistant',
            content=result,
            file_path=file_url,
            file_name=file_name,
            html_file_path=html_url,
            html_file_name=html_file_name
        )
        db.session.add(assistant_msg)
        session.updated_at = datetime.utcnow()

        # 同步更新 InvestmentLead 的研判结果（向后兼容）
        lead.ai_assessment_result = result
        lead.ai_assessment_at = datetime.utcnow()
        lead.ai_assessment_status = 'completed'
        lead.ai_model_id = model.id
        lead.assessment_prompt_used = prompt_template

        db.session.commit()

        # 异步启动知识沉淀分析
        _run_knowledge_feedback_async(session.id, lead_id)

        return jsonify({
            'code': 0,
            'data': {
                'session_id': session.id,
                'message': assistant_msg.to_dict()
            }
        })

    except Exception as e:
        # 失败时仍保留会话和用户消息
        session.updated_at = datetime.utcnow()
        lead.ai_assessment_status = 'failed'
        db.session.commit()
        return jsonify({'code': 1, 'message': f'AI 研判失败：{str(e)}'}), 500


@admin_lead_bp.route('/lead/leads/<int:lead_id>/assessment-sessions', methods=['GET'])
@dual_login_required
def list_assessment_sessions(lead_id):
    """获取线索的所有研判会话"""
    _ = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()
    sessions = LeadAssessmentSession.query.filter_by(lead_id=lead_id)\
        .order_by(LeadAssessmentSession.created_at.desc()).all()
    return jsonify({
        'code': 0,
        'data': [s.to_dict() for s in sessions]
    })


@admin_lead_bp.route('/lead/assessment-sessions/<int:session_id>/messages', methods=['GET'])
@dual_login_required
def get_session_messages(session_id):
    """获取会话消息列表"""
    session = LeadAssessmentSession.query.get_or_404(session_id)
    messages = LeadAssessmentMessage.query.filter_by(session_id=session_id)\
        .order_by(LeadAssessmentMessage.created_at.desc()).all()
    return jsonify({
        'code': 0,
        'data': {
            'session': session.to_dict(),
            'messages': [m.to_dict() for m in messages]
        }
    })


@admin_lead_bp.route('/lead/assessment-sessions/<int:session_id>/messages', methods=['POST'])
@dual_login_required
@visitor_block
def send_follow_up_message(session_id):
    """发送追加提问"""
    session = LeadAssessmentSession.query.get_or_404(session_id)
    lead = InvestmentLead.query.filter_by(id=session.lead_id, is_deleted=False).first_or_404()
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    model_id = data.get('model_id')

    if not question:
        return jsonify({'code': 1, 'message': '请输入提问内容'}), 400

    # 选择模型（优先使用本次选中的，否则用会话的模型，最后用默认）
    if model_id:
        model = LLMModel.query.get(model_id)
    elif session.model_id:
        model = LLMModel.query.get(session.model_id)
    else:
        model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
    if not model:
        return jsonify({'code': 1, 'message': '没有可用的 AI 模型'}), 400

    # 更新会话模型
    session.model_id = model.id

    # 构建完整对话历史
    history = _build_assessment_messages_full(session_id)
    system_prompt = model.system_prompt or '你是一个专业的招商分析助手。请根据提供的企业信息进行客观、全面的分析。'

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.extend(history)
    messages.append({'role': 'user', 'content': question})

    # 保存用户消息
    user_msg = LeadAssessmentMessage(
        session_id=session_id,
        role='user',
        content=question
    )
    db.session.add(user_msg)
    db.session.commit()

    try:
        result = call_llm(
            model_config={
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name
            },
            messages=messages,
            temperature=model.temperature,
            max_tokens=model.max_tokens
        )

        # 生成 Word 文档
        file_url, file_name = generate_assessment_docx(
            lead.project_name,
            lead.invest_enterprise,
            result
        )

        # 生成 HTML 报告
        html_url, html_file_name = generate_assessment_html(
            lead.project_name,
            lead.invest_enterprise,
            result
        )

        assistant_msg = LeadAssessmentMessage(
            session_id=session_id,
            role='assistant',
            content=result,
            file_path=file_url,
            file_name=file_name,
            html_file_path=html_url,
            html_file_name=html_file_name
        )
        db.session.add(assistant_msg)
        session.updated_at = datetime.utcnow()

        # 同步更新 lead 研判结果（最新一次）
        lead.ai_assessment_result = result
        lead.ai_assessment_at = datetime.utcnow()
        lead.ai_assessment_status = 'completed'

        db.session.commit()

        return jsonify({
            'code': 0,
            'data': {
                'message': assistant_msg.to_dict()
            }
        })

    except Exception as e:
        session.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'code': 1, 'message': f'AI 研判失败：{str(e)}'}), 500


# ---- 知识沉淀分析 ----

def _run_knowledge_feedback_async(session_id, lead_id):
    """在后台线程中异步执行知识沉淀分析"""
    from flask import current_app
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_analyze_knowledge_feedback,
        args=(app, session_id, lead_id),
        daemon=True
    )
    thread.start()


def _analyze_knowledge_feedback(app, session_id, lead_id):
    """研判后分析：让 LLM 自评知识库使用效果 + 提取可沉淀内容"""
    with app.app_context():
        try:
            session = LeadAssessmentSession.query.get(session_id)
            if not session:
                return
            lead = InvestmentLead.query.get(lead_id)
            if not lead:
                return

            # 获取最新的 assistant 消息
            assistant_msg = LeadAssessmentMessage.query.filter_by(
                session_id=session_id, role='assistant'
            ).order_by(LeadAssessmentMessage.id.desc()).first()
            if not assistant_msg or not assistant_msg.content:
                return

            # 获取关联的知识条目（从 _search_knowledge 的检索缓存中获取）
            knowledge_context = _search_knowledge(lead)

            # 构建元分析 prompt
            analysis_prompt = f"""你对以下招商线索进行了研判分析。现在请你复盘本次分析过程：

【线索信息】
{_build_lead_context(lead)[:3000]}

【本次匹配的知识库条目】
{knowledge_context[:3000]}

【你的研判报告摘要】
{assistant_msg.content[:2000]}

请完成以下三项任务，以 JSON 格式返回（**只输出 JSON，不要 Markdown 包裹，不要代码块标记**）：

{{
  "used_entries_feedback": [
    {{
      "entry_title": "条目标题",
      "was_useful": true,
      "accuracy_note": "该条知识与研判结果一致，数据准确",
      "needs_update": false,
      "update_suggestion": null
    }}
  ],
  "new_knowledge_candidates": [
    {{
      "title": "候选知识标题",
      "content": "详细内容...",
      "category": "case_study",
      "tags": ["标签1", "标签2"],
      "relevance_reason": "为什么值得沉淀"
    }}
  ],
  "search_suggestions": [
    "建议在知识库中补充xxx方面的内容",
    "建议更新xxx数据"
  ]
}}

category 必须从以下值中选择：industry_policy / park_info / supporting / land_cost / case_study / demand_pattern / market_data / competitor
如果没有值得沉淀的新知识，new_knowledge_candidates 返回空数组 []。
如果没有需要更新的条目，used_entries_feedback 返回空数组 []。"""

            # 使用同一模型进行轻量分析
            model = LLMModel.query.get(session.model_id) if session.model_id else LLMModel.query.filter_by(is_active=True).first()
            if not model:
                return

            messages = [{'role': 'user', 'content': analysis_prompt}]
            response = call_llm(
                model_config={
                    'api_base_url': model.api_base_url,
                    'api_key': model.api_key,
                    'model_name': model.model_name
                },
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )

            # 解析 JSON
            feedback = _parse_feedback_json(response)
            if not feedback:
                return

            # 保存知识使用统计
            used_entries = feedback.get('used_entries_feedback', [])
            for fe in used_entries:
                if isinstance(fe, dict) and fe.get('entry_title'):
                    # 尝试匹配已有条目
                    entry = KnowledgeEntry.query.filter_by(title=fe['entry_title']).first()
                    if entry:
                        stat = KnowledgeUsageStat(
                            entry_id=entry.id,
                            session_id=session_id,
                            lead_id=lead_id,
                            was_used=True,
                            was_useful=fe.get('was_useful'),
                            relevance_score=0.5,
                            accuracy_feedback=fe.get('accuracy_note', ''),
                            needs_update=fe.get('needs_update', False),
                            update_suggestion=fe.get('update_suggestion') or ''
                        )
                        db.session.add(stat)

            # 保存新知识草稿
            candidates = feedback.get('new_knowledge_candidates', [])
            for c in candidates:
                if isinstance(c, dict) and c.get('title') and c.get('content'):
                    category = c.get('category', 'case_study')
                    if category not in CATEGORY_NAMES:
                        category = 'case_study'
                    draft = KnowledgeDraft(
                        title=c['title'][:255],
                        content=c['content'][:10000],
                        category=category,
                        tags=json.dumps(c.get('tags', []), ensure_ascii=False),
                        source='AI研判自动提炼',
                        source_session_id=session_id,
                        source_lead_id=lead_id,
                        status='draft'
                    )
                    db.session.add(draft)

            # 保存搜索建议
            suggestions = feedback.get('search_suggestions', [])
            if suggestions:
                for s in suggestions:
                    if isinstance(s, str) and s.strip():
                        draft = KnowledgeDraft(
                            title=f'[搜索建议] {s.strip()[:200]}',
                            content=s.strip(),
                            category='case_study',
                            tags=json.dumps(['搜索建议', '待补充'], ensure_ascii=False),
                            source='AI研判自动提炼',
                            source_session_id=session_id,
                            source_lead_id=lead_id,
                            status='draft'
                        )
                        db.session.add(draft)

            db.session.commit()

            draft_count = len(candidates) + len(suggestions)
            if draft_count > 0 or len(used_entries) > 0:
                print(f'[知识沉淀] 会话 {session_id}: 生成 {draft_count} 条草稿, {len(used_entries)} 条使用统计')

        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f'[知识沉淀] 会话 {session_id} 分析失败: {e}')


def _parse_feedback_json(response):
    """从 LLM 返回中解析 JSON，处理各种格式"""
    import re
    # 移除可能的 markdown 代码块
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:]
    if response.startswith('```'):
        response = response[3:]
    if response.endswith('```'):
        response = response[:-3]
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # 尝试用正则提取 JSON 块
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


@admin_lead_bp.route('/lead/assessment-sessions/<int:session_id>/messages/<int:message_id>/download', methods=['GET'])
@dual_login_required
def download_assessment_file(session_id, message_id):
    """下载研判 Word 文档"""
    msg = LeadAssessmentMessage.query.filter_by(id=message_id, session_id=session_id).first_or_404()
    if not msg.file_path:
        return jsonify({'code': 1, 'message': '该消息没有关联文件'}), 404

    # file_path 格式如 /static/assessments/xxx.docx
    from flask import send_file, current_app
    relative = msg.file_path
    if relative.startswith('/static/'):
        relative = relative[8:]  # 去掉 /static/ 前缀

    # 优先在 backend/static/ 下查找（word_service 实际生成位置）
    import os as _os
    backend_static = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'static')
    file_path = _os.path.join(backend_static, relative)
    if not _os.path.exists(file_path):
        # 回退：在 current_app.static_folder 下查找
        file_path = _os.path.join(current_app.static_folder, relative)

    if not _os.path.exists(file_path):
        return jsonify({'code': 1, 'message': '文件不存在或已被删除'}), 404

    download_name = msg.file_name or f'研判报告_{message_id}.docx'
    return send_file(file_path, as_attachment=True, download_name=download_name)


@admin_lead_bp.route('/lead/assessment-sessions/<int:session_id>/messages/<int:message_id>/html', methods=['GET'])
@dual_login_required
def view_assessment_html(session_id, message_id):
    """在线查看研判 HTML 报告"""
    msg = LeadAssessmentMessage.query.filter_by(id=message_id, session_id=session_id).first_or_404()
    if not msg.html_file_path:
        return jsonify({'code': 1, 'message': '该消息没有 HTML 报告'}), 404

    from flask import send_file, current_app
    relative = msg.html_file_path
    if relative.startswith('/static/'):
        relative = relative[8:]

    import os as _os
    backend_static = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'static')
    file_path = _os.path.join(backend_static, relative)
    if not _os.path.exists(file_path):
        file_path = _os.path.join(current_app.static_folder, relative)

    if not _os.path.exists(file_path):
        return jsonify({'code': 1, 'message': '文件不存在或已被删除'}), 404

    return send_file(file_path, mimetype='text/html; charset=utf-8')


# ============================================================
# 转为招商项目
# ============================================================

@admin_lead_bp.route('/lead/leads/<int:lead_id>/convert', methods=['POST'])
@dual_login_required
@visitor_block
def convert_lead(lead_id):
    """将招商线索转为正式项目"""
    lead = InvestmentLead.query.filter_by(id=lead_id, is_deleted=False).first_or_404()

    if lead.converted_project_id:
        return jsonify({'code': 1, 'message': '该线索已转换为项目'}), 400

    # 创建 InvestmentProject，复制线索数据
    project = InvestmentProject(
        order_no=lead.order_no,
        project_name=lead.project_name,
        invest_enterprise=lead.invest_enterprise,
        enterprise_info=lead.enterprise_info,
        project_content=lead.project_content,
        invest_amount=lead.invest_amount,
        follow_status_code=lead.follow_status_code,
        meeting_status_code=lead.meeting_status_code,
        recommend_unit_code=lead.recommend_unit_code,
        responsible_unit_code=lead.responsible_unit_code,
        project_type_code=lead.project_type_code,
        person_in_charge=lead.person_in_charge,
        person_in_charge_phone=lead.person_in_charge_phone,
        project_doc=lead.project_doc,
        investment_plan=lead.investment_plan,
        conclusion=lead.conclusion or '',
        tags=lead.tags,
        team_leader_ids=lead.team_leader_ids,
        first_contact_date=lead.first_contact_date
    )

    # AI 研判结果补充到项目结论
    if lead.ai_assessment_result and not project.conclusion:
        project.conclusion = f'[AI 研判结果]\n{lead.ai_assessment_result}'

    db.session.add(project)
    db.session.flush()

    # 复制企业诉求数据
    lead_demands = EnterpriseDemand.query.filter_by(lead_id=lead_id)\
        .order_by(EnterpriseDemand.sort_order).all()
    for d in lead_demands:
        db.session.add(EnterpriseDemand(
            project_id=project.id,
            lead_id=None,
            demand_type_code=d.demand_type_code,
            demand_content=d.demand_content,
            resolution=d.resolution,
            unit_code=d.unit_code,
            status=d.status,
            sort_order=d.sort_order
        ))

    lead.converted_project_id = project.id
    _renumber_investment_projects()

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        log_changes('investment_leads', lead_id,
                     {'converted_project_id': (None, str(project.id))},
                     'update', user_info)
        log_changes('investment_projects', project.id,
                     {'project_name': (None, project.project_name)},
                     'create', user_info)

    db.session.commit()
    return jsonify({
        'code': 0,
        'data': {'lead_id': lead.id, 'project_id': project.id},
        'message': '线索已成功转换为招商项目'
    })
