from flask import request, jsonify
from flask_login import login_required
from models import LLMModel
from extensions import db
from routes import admin_models_bp
from services.llm_service import call_llm


@admin_models_bp.route('/models', methods=['GET'])
@login_required
def list_models():
    """获取所有大模型（含 API Key）"""
    models = LLMModel.query.order_by(LLMModel.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [m.to_admin_dict() for m in models]})


@admin_models_bp.route('/models/<int:model_id>', methods=['GET'])
@login_required
def get_model(model_id):
    """获取单个大模型详情"""
    model = LLMModel.query.get_or_404(model_id)
    return jsonify({'code': 0, 'data': model.to_admin_dict()})


@admin_models_bp.route('/models', methods=['POST'])
@login_required
def create_model():
    """新建大模型"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    model = LLMModel(
        name=data.get('name', ''),
        provider=data.get('provider', 'custom'),
        api_base_url=data.get('api_base_url', ''),
        api_key=data.get('api_key', ''),
        model_name=data.get('model_name', ''),
        temperature=data.get('temperature', 0.7),
        max_tokens=data.get('max_tokens', 4096),
        system_prompt=data.get('system_prompt', ''),
        embedding_api_url=data.get('embedding_api_url', ''),
        embedding_api_key=data.get('embedding_api_key', ''),
        embedding_model_name=data.get('embedding_model_name', ''),
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0)
    )
    db.session.add(model)
    db.session.commit()
    return jsonify({'code': 0, 'data': model.to_admin_dict(), 'message': '创建成功'})


@admin_models_bp.route('/models/<int:model_id>', methods=['PUT'])
@login_required
def update_model(model_id):
    """更新大模型"""
    model = LLMModel.query.get_or_404(model_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = [
        'name', 'provider', 'api_base_url', 'api_key', 'model_name',
        'temperature', 'max_tokens', 'system_prompt', 'is_active', 'sort_order',
        'embedding_api_url', 'embedding_api_key', 'embedding_model_name'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(model, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': model.to_admin_dict(), 'message': '更新成功'})


@admin_models_bp.route('/models/<int:model_id>', methods=['DELETE'])
@login_required
def delete_model(model_id):
    """删除大模型"""
    model = LLMModel.query.get_or_404(model_id)
    db.session.delete(model)
    db.session.commit()
    return jsonify({'code': 0, 'message': '删除成功'})


@admin_models_bp.route('/models/<int:model_id>/test', methods=['POST'])
@login_required
def test_model(model_id):
    """测试大模型连接"""
    model = LLMModel.query.get_or_404(model_id)

    try:
        result = call_llm(
            model_config={
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name
            },
            messages=[{'role': 'user', 'content': '请回复"连接测试成功"，不要回复其他内容。'}],
            temperature=0.1,
            max_tokens=50
        )
        return jsonify({'code': 0, 'data': {'response': result}, 'message': '连接测试成功'})
    except Exception as e:
        return jsonify({'code': 1, 'message': f'连接测试失败：{str(e)}'}), 500
