from flask import request, jsonify
from models import CarouselPage, ProvinceInfo, CityInfo, LLMModel, QuickPrompt, HomepageConfig, ContactInfo
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
