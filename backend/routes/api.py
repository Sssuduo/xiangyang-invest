import json
from datetime import datetime, timedelta
from flask import request, jsonify
from models import CarouselPage, ProvinceInfo, CityInfo, LLMModel, QuickPrompt, HomepageConfig, ContactInfo
from models import InvestmentProject, FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict
from models import InvestmentActivity, EnterpriseDemand
from extensions import db
from routes import api_bp
from services.llm_service import call_llm, build_messages
from utils.image_upload import save_uploaded_image


# ============================================================
# 首页配置
# ============================================================
@api_bp.route('/homepage', methods=['GET'])
def get_homepage_config():
    """获取首页配置"""
    config = HomepageConfig.query.first()
    if not config:
        config = HomepageConfig()
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


# ============================================================
# 联系我们
# ============================================================
@api_bp.route('/contact', methods=['GET'])
def get_contact_info():
    """获取联系我们配置"""
    config = ContactInfo.query.first()
    if not config:
        config = ContactInfo()
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


# ============================================================
# 轮播页
# ============================================================
@api_bp.route('/carousel/pages', methods=['GET'])
def get_carousel_pages():
    """获取启用的轮播页列表"""
    pages = CarouselPage.query.filter_by(is_active=True)\
        .order_by(CarouselPage.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in pages]})


@api_bp.route('/carousel/pages/<int:page_id>', methods=['GET'])
def get_carousel_page(page_id):
    """获取单个轮播页详情"""
    page = CarouselPage.query.get_or_404(page_id)
    return jsonify({'code': 0, 'data': page.to_dict()})


# ============================================================
# 省份信息
# ============================================================
@api_bp.route('/provinces', methods=['GET'])
def get_provinces():
    """获取省份信息"""
    scope = request.args.get('scope', 'china')
    provinces = ProvinceInfo.query.filter_by(map_scope=scope).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in provinces]})


# ============================================================
# 城市信息（省份子级）
# ============================================================
@api_bp.route('/provinces/<int:province_id>/cities', methods=['GET'])
def get_province_cities(province_id):
    """获取省份下高亮的城市"""
    province = ProvinceInfo.query.get_or_404(province_id)
    cities = province.cities.filter_by(is_highlighted=True).all()
    return jsonify({'code': 0, 'data': [c.to_dict() for c in cities]})


# ============================================================
# 大模型
# ============================================================
@api_bp.route('/models', methods=['GET'])
def get_models():
    """获取启用的大模型列表"""
    models = LLMModel.query.filter_by(is_active=True)\
        .order_by(LLMModel.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [m.to_dict() for m in models]})


# ============================================================
# 快捷提示词
# ============================================================
@api_bp.route('/prompts', methods=['GET'])
def get_prompts():
    """获取启用的提示词列表"""
    prompts = QuickPrompt.query.filter_by(is_active=True)\
        .order_by(QuickPrompt.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in prompts]})


# ============================================================
# LLM 对话
# ============================================================
@api_bp.route('/chat', methods=['POST'])
def chat():
    """调用大模型对话"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    user_input = data.get('user_input', '').strip()
    model_id = data.get('model_id')
    prompt_id = data.get('prompt_id')
    custom_question = data.get('custom_question', False)

    if not user_input:
        return jsonify({'code': 1, 'message': '请输入内容'}), 400

    if not model_id:
        return jsonify({'code': 1, 'message': '请选择一个大模型'}), 400

    # 查找模型配置
    model = LLMModel.query.get(model_id)
    if not model or not model.is_active:
        return jsonify({'code': 1, 'message': '所选模型不存在或已禁用'}), 400

    # 构建消息
    prompt_template = None
    if prompt_id and not custom_question:
        prompt = QuickPrompt.query.get(prompt_id)
        if prompt and prompt.is_active:
            prompt_template = prompt.prompt_template

    messages = build_messages(
        user_input=user_input,
        prompt_template=prompt_template,
        system_prompt=model.system_prompt
    )

    # 如果选了提示词但是自定义提问模式，或者没选提示词 -> 直接使用原始输入
    if custom_question or not prompt_id:
        messages = build_messages(
            user_input=user_input,
            prompt_template=None,
            system_prompt=model.system_prompt
        )

    # 调用 LLM
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
        return jsonify({
            'code': 0,
            'data': {
                'response_text': result,
                'model_name': model.name
            }
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': f'调用大模型失败：{str(e)}'}), 500


# ============================================================
# 图片上传
# ============================================================
@api_bp.route('/upload', methods=['POST'])
def upload_image():
    """上传图片"""
    from flask import current_app

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '未找到上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 1, 'message': '未选择文件'}), 400

    try:
        url = save_uploaded_image(file, current_app.config['UPLOAD_FOLDER'])
        return jsonify({'code': 0, 'data': {'url': url}})
    except ValueError as e:
        return jsonify({'code': 1, 'message': str(e)}), 400


# ============================================================
# 招商对接项目（公开）
# ============================================================
@api_bp.route('/investment/projects', methods=['GET'])
def list_public_projects():
    """公开项目列表（树形表格用）"""
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
        db.case(
            (InvestmentProject.follow_status_code == 'follow_focus', 0),
            else_=1
        ),
        InvestmentProject.order_no.asc(),
        InvestmentProject.created_at.desc()
    )

    projects = q.all()

    # 返回带字典名称的数据（前台直接使用）
    follow_map = {d.code: d for d in FollowStatusDict.query.all()}
    meeting_map = {d.code: d for d in MeetingStatusDict.query.all()}
    org_map = {d.code: d for d in OrganizationDict.query.all()}
    type_map = {d.code: d for d in ProjectTypeDict.query.all()}
    demand_type_map = {d.code: d for d in DemandTypeDict.query.all()}
    demand_display_map = DemandTypeDict.build_display_name_map()
    tag_map = {d.code: d.name for d in ProjectTagDict.query.all()}

    result = []
    for p in projects:
        d = p.to_dict()
        fu = follow_map.get(p.follow_status_code)
        d['follow_status_name'] = fu.name if fu else ''
        d['follow_status_color'] = fu.display_color if fu else '#909399'
        mu = meeting_map.get(p.meeting_status_code)
        d['meeting_status_name'] = mu.name if mu else ''
        d['meeting_status_color'] = mu.display_color if mu else '#909399'
        ou = org_map.get(p.recommend_unit_code)
        d['recommend_unit_name'] = ou.name if ou else ''
        ou2 = org_map.get(p.responsible_unit_code)
        d['responsible_unit_name'] = ou2.name if ou2 else ''
        tu = type_map.get(p.project_type_code)
        d['project_type_name'] = tu.name if tu else ''
        # 标签名称解析
        d['tag_names'] = [tag_map.get(tc, tc) for tc in (json.loads(p.tags) if p.tags else [])]
        # 专班负责人名称解析
        from models import Staff
        leader_ids = json.loads(p.team_leader_ids) if p.team_leader_ids else []
        staff_list = Staff.query.filter(Staff.id.in_(leader_ids)).all() if leader_ids else []
        staff_map = {s.id: s.name for s in staff_list}
        d['team_leader_names'] = [staff_map.get(sid, str(sid)) for sid in leader_ids]
        # 诉求字典名称（二级显示：一级：二级）
        for dd in d.get('demands', []) or []:
            codes = [c.strip() for c in (dd.get('demand_type_code') or '').split(',') if c.strip()]
            dd['demand_type_name'] = '、'.join([demand_display_map.get(c, c) for c in codes]) if codes else ''
            du = org_map.get(dd.get('unit_code'))
            dd['unit_name'] = du.name if du else ''
        result.append(d)

    return jsonify({'code': 0, 'data': result})


# ============================================================
# 招商动态（公开）
# ============================================================
@api_bp.route('/investment/activities', methods=['GET'])
def list_public_activities():
    """公开招商动态列表"""
    search = request.args.get('search', '').strip()
    project_id = request.args.get('project_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    tags = request.args.get('tags', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    q = InvestmentActivity.query.join(InvestmentProject)

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            InvestmentProject.project_name.ilike(like),
            InvestmentActivity.content.ilike(like)
        ))

    if project_id:
        q = q.filter(InvestmentActivity.project_id == int(project_id))
    if date_from:
        q = q.filter(InvestmentActivity.date >= date_from)
    if date_to:
        q = q.filter(InvestmentActivity.date <= date_to)
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if tag_list:
            tag_conds = [InvestmentActivity.tags.like(f'%{t}%') for t in tag_list]
            q = q.filter(db.or_(*tag_conds))

    total = q.count()
    q = q.order_by(InvestmentActivity.date.desc())
    activities = q.offset((page - 1) * page_size).limit(page_size).all()

    # 解析标签 code → 名称
    tag_map = {d.code: d.name for d in ActivityTagDict.query.all()}
    result = []
    for a in activities:
        item = a.to_dict()
        raw_tags = item.get('tags', []) or []
        item['tag_names'] = [tag_map.get(tc, tc) for tc in raw_tags]
        result.append(item)
    return jsonify({'code': 0, 'data': result, 'total': total})


# ============================================================
# 企业诉求（公开）
# ============================================================
@api_bp.route('/investment/demands', methods=['GET'])
def list_public_demands():
    """公开企业诉求列表"""
    search = request.args.get('search', '').strip()
    project_id = request.args.get('project_id', '').strip()
    demand_type = request.args.get('demand_type', '').strip()
    project_type = request.args.get('project_type', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    q = EnterpriseDemand.query.join(InvestmentProject)

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            InvestmentProject.project_name.ilike(like),
            EnterpriseDemand.demand_content.ilike(like)
        ))

    if project_id:
        q = q.filter(EnterpriseDemand.project_id == int(project_id))
    if project_type:
        q = q.filter(InvestmentProject.project_type_code == project_type)
    if demand_type:
        codes = [c.strip() for c in demand_type.split(',') if c.strip()]
        if len(codes) == 1:
            q = q.filter(EnterpriseDemand.demand_type_code == codes[0])
        else:
            q = q.filter(EnterpriseDemand.demand_type_code.in_(codes))
    if status:
        q = q.filter(EnterpriseDemand.status == status)

    total = q.count()
    q = q.order_by(EnterpriseDemand.created_at.desc())
    demands = q.offset((page - 1) * page_size).limit(page_size).all()

    # 解析字典名称
    type_map = DemandTypeDict.build_display_name_map()
    org_map = {d.code: d.name for d in OrganizationDict.query.all()}

    result = []
    for d in demands:
        item = d.to_dict()
        item['project_name'] = d.project.project_name if d.project else ''
        # 支持逗号分隔的多值编码
        codes = [c.strip() for c in (d.demand_type_code or '').split(',') if c.strip()]
        item['demand_type_name'] = '、'.join([type_map.get(c, c) for c in codes]) if codes else ''
        item['unit_name'] = org_map.get(d.unit_code, '')
        result.append(item)

    return jsonify({'code': 0, 'data': result, 'total': total})


# ============================================================
# 企业诉求字典（公开）
# ============================================================
@api_bp.route('/investment/demand-dicts', methods=['GET'])
def get_demand_dicts():
    """获取企业诉求相关字典（需求类型 + 对接单位 + 跟进状态 + 项目类型 + 项目标签 + 动态标签）"""
    demand_types = DemandTypeDict.query.filter_by(is_active=True)\
        .order_by(DemandTypeDict.sort_order).all()
    organizations = OrganizationDict.query.filter_by(is_active=True)\
        .order_by(OrganizationDict.sort_order).all()
    follow_statuses = FollowStatusDict.query.filter_by(is_active=True)\
        .order_by(FollowStatusDict.sort_order).all()
    project_types = ProjectTypeDict.query.filter_by(is_active=True)\
        .order_by(ProjectTypeDict.sort_order).all()
    project_tags = ProjectTagDict.query.filter_by(is_active=True)\
        .order_by(ProjectTagDict.sort_order).all()
    activity_tags = ActivityTagDict.query.filter_by(is_active=True)\
        .order_by(ActivityTagDict.sort_order).all()
    return jsonify({
        'code': 0,
        'data': {
            'demand_types': [d.to_dict() for d in demand_types],
            'organizations': [o.to_dict() for o in organizations],
            'follow_statuses': [f.to_dict() for f in follow_statuses],
            'project_types': [p.to_dict() for p in project_types],
            'project_tags': [t.to_dict() for t in project_tags],
            'activity_tags': [t.to_dict() for t in activity_tags]
        }
    })
