"""消息提醒规则管理 API — 后台配置消息规则"""
import json
from flask import request, jsonify
from flask_login import login_required
from models import MessageRule, UserMessage, MessageRuleLog
from extensions import db
from routes import admin_message_bp


# ============================================================
# 规则 CRUD
# ============================================================

@admin_message_bp.route('/message-rules', methods=['GET'])
@login_required
def list_message_rules():
    """获取所有消息规则"""
    rules = MessageRule.query.order_by(MessageRule.created_at.desc()).all()
    return jsonify({'code': 0, 'data': [r.to_dict() for r in rules]}), 200


@admin_message_bp.route('/message-rules/<int:rule_id>', methods=['GET'])
@login_required
def get_message_rule(rule_id):
    """获取单条规则"""
    rule = MessageRule.query.get(rule_id)
    if not rule:
        return jsonify({'code': 1, 'message': '规则不存在'}), 404
    return jsonify({'code': 0, 'data': rule.to_dict()}), 200


@admin_message_bp.route('/message-rules', methods=['POST'])
@login_required
def create_message_rule():
    """创建消息规则"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    name = (data.get('name') or '').strip()
    body_template = (data.get('body_template') or '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '规则名称不能为空'}), 400
    if not body_template:
        return jsonify({'code': 1, 'message': '消息体模板不能为空'}), 400

    rule = MessageRule(
        name=name,
        is_active=data.get('is_active', True),
        condition_type=data.get('condition_type', 'project_no_meeting'),
        threshold_days=int(data.get('threshold_days') or 15),
        target_type=data.get('target_type', 'all'),
        target_user_ids=json.dumps(data.get('target_user_ids', []), ensure_ascii=False),
        title_template=(data.get('title_template') or '新消息提醒').strip(),
        body_template=body_template,
        link_route=data.get('link_route', '/investment'),
        link_query_template=data.get('link_query_template', '{"focusProjectId": {project_id}}'),
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({'code': 0, 'data': rule.to_dict(), 'message': '创建成功'}), 200


@admin_message_bp.route('/message-rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_message_rule(rule_id):
    """更新消息规则"""
    rule = MessageRule.query.get(rule_id)
    if not rule:
        return jsonify({'code': 1, 'message': '规则不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable = ['name', 'is_active', 'condition_type', 'threshold_days',
                 'target_type', 'target_user_ids', 'title_template',
                 'body_template', 'link_route', 'link_query_template']
    for field in updatable:
        if field not in data:
            continue
        val = data[field]
        if field == 'target_user_ids':
            val = json.dumps(val or [], ensure_ascii=False)
        setattr(rule, field, val)

    db.session.commit()
    return jsonify({'code': 0, 'data': rule.to_dict(), 'message': '更新成功'}), 200


@admin_message_bp.route('/message-rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_message_rule(rule_id):
    """删除消息规则"""
    rule = MessageRule.query.get(rule_id)
    if not rule:
        return jsonify({'code': 1, 'message': '规则不存在'}), 404
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'code': 0, 'message': '删除成功'}), 200


@admin_message_bp.route('/message-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_message_rule(rule_id):
    """启用/禁用规则"""
    rule = MessageRule.query.get(rule_id)
    if not rule:
        return jsonify({'code': 1, 'message': '规则不存在'}), 404
    rule.is_active = not rule.is_active
    db.session.commit()
    return jsonify({'code': 0, 'data': rule.to_dict(), 'message': '操作成功'}), 200


# ============================================================
# 规则触发日志
# ============================================================

@admin_message_bp.route('/message-rules/<int:rule_id>/logs', methods=['GET'])
@login_required
def list_rule_logs(rule_id):
    """获取规则触发日志"""
    logs = MessageRuleLog.query.filter_by(rule_id=rule_id) \
        .order_by(MessageRuleLog.triggered_at.desc()).limit(50).all()
    return jsonify({'code': 0, 'data': [log.to_dict() for log in logs]}), 200
