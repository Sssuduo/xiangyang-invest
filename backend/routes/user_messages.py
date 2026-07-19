"""用户消息 API — 业务端 inbox(消息中心)"""
import json
from flask import request, jsonify
from flask_login import current_user
from models import UserMessage, MessageRule
from extensions import db
from routes import api_bp


def _get_current_user_info():
    """返回 (user_id, user_type) 兼容 AdminUser 与 BusinessUser"""
    if current_user.is_authenticated:
        return current_user.id, 'admin'
    from flask import session
    biz_id = session.get('business_user_id')
    if biz_id:
        return int(biz_id), 'business'
    return None, None


@api_bp.route('/messages/inbox', methods=['GET'])
def list_inbox():
    """当前用户消息列表(分页 + 状态筛选)"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    status = request.args.get('status', 'pending')  # pending | snoozed | done | all
    page = int(request.args.get('page', 1))
    size = int(request.args.get('page_size', 20))

    q = UserMessage.query.filter_by(user_id=user_id, user_type=user_type)
    if status != 'all':
        q = q.filter_by(status=status)
    total = q.count()
    items = q.order_by(UserMessage.triggered_at.desc()) \
        .offset((page - 1) * size).limit(size).all()

    return jsonify({
        'code': 0,
        'data': {
            'total': total,
            'items': [m.to_dict() for m in items],
        }
    }), 200


@api_bp.route('/messages/unread-count', methods=['GET'])
def unread_count():
    """未读(待处理 + 已挂起)消息条数,供 Navbar badge 用"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 0, 'data': {'count': 0}}), 200

    count = UserMessage.query.filter(
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
        UserMessage.status.in_(['pending', 'snoozed']),
    ).count()
    return jsonify({'code': 0, 'data': {'count': count}}), 200


@api_bp.route('/messages/<int:message_id>/snooze', methods=['POST'])
def snooze_message(message_id):
    """挂起消息(仍显示,不再主动提醒)"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    msg = UserMessage.query.filter_by(id=message_id, user_id=user_id, user_type=user_type).first()
    if not msg:
        return jsonify({'code': 1, 'message': '消息不存在'}), 404

    msg.status = 'snoozed'
    db.session.commit()
    return jsonify({'code': 0, 'data': msg.to_dict(), 'message': '已挂起'}), 200


@api_bp.route('/messages/<int:message_id>/done', methods=['POST'])
def done_message(message_id):
    """已处理(不再提醒,历史保留)"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    msg = UserMessage.query.filter_by(id=message_id, user_id=user_id, user_type=user_type).first()
    if not msg:
        return jsonify({'code': 1, 'message': '消息不存在'}), 404

    from datetime import datetime
    msg.status = 'done'
    msg.handled_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'code': 0, 'data': msg.to_dict(), 'message': '已处理'}), 200


@api_bp.route('/messages/read-all', methods=['POST'])
def read_all():
    """全部标记已处理"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    from datetime import datetime
    UserMessage.query.filter(
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
        UserMessage.status.in_(['pending', 'snoozed']),
    ).update({'status': 'done', 'handled_at': datetime.utcnow()})
    db.session.commit()
    return jsonify({'code': 0, 'message': '已全部标记为已处理'}), 200
