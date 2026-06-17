from flask import request, jsonify
from flask_login import login_required
from models import QuickPrompt
from extensions import db
from routes import admin_prompts_bp


@admin_prompts_bp.route('/prompts', methods=['GET'])
@login_required
def list_prompts():
    """获取所有提示词"""
    prompts = QuickPrompt.query.order_by(QuickPrompt.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in prompts]})


@admin_prompts_bp.route('/prompts/<int:prompt_id>', methods=['GET'])
@login_required
def get_prompt(prompt_id):
    """获取单个提示词详情"""
    prompt = QuickPrompt.query.get_or_404(prompt_id)
    return jsonify({'code': 0, 'data': prompt.to_dict()})


@admin_prompts_bp.route('/prompts', methods=['POST'])
@login_required
def create_prompt():
    """新建提示词"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    prompt = QuickPrompt(
        button_text=data.get('button_text', ''),
        prompt_template=data.get('prompt_template', ''),
        description=data.get('description', ''),
        category=data.get('category', 'general'),
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0)
    )
    db.session.add(prompt)
    db.session.commit()
    return jsonify({'code': 0, 'data': prompt.to_dict(), 'message': '创建成功'})


@admin_prompts_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
@login_required
def update_prompt(prompt_id):
    """更新提示词"""
    prompt = QuickPrompt.query.get_or_404(prompt_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = [
        'button_text', 'prompt_template', 'description',
        'category', 'is_active', 'sort_order'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(prompt, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': prompt.to_dict(), 'message': '更新成功'})


@admin_prompts_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
@login_required
def delete_prompt(prompt_id):
    """删除提示词"""
    prompt = QuickPrompt.query.get_or_404(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    return jsonify({'code': 0, 'message': '删除成功'})
