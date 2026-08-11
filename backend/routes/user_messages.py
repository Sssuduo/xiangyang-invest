"""用户消息 API — 业务端 inbox(消息中心)"""
import json
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_login import current_user
from models import UserMessage, MessageRule, InvestmentProject, AdminUser, BusinessUser
from extensions import db
from routes import api_bp


def _get_current_user_info():
    """返回 (user_id, user_type) 兼容 AdminUser 与 BusinessUser

    业务端优先（消息站是业务端功能）：先查 session 的 business_user_id，
    再查 Flask-Login 的 current_user。suduo 等用户同时存在于两张表时，
    以业务登录身份为准，避免查到 admin 身份的重复消息。
    """
    from flask import session
    biz_id = session.get('business_user_id')
    if biz_id:
        return int(biz_id), 'business'
    if current_user.is_authenticated:
        return current_user.id, 'admin'
    return None, None


def _get_display_name(user_id, user_type):
    """取用户显示名（协同处理时记录处理人）"""
    if user_type == 'admin':
        u = AdminUser.query.get(user_id)
    else:
        u = BusinessUser.query.get(user_id)
    if u:
        return getattr(u, 'display_name', None) or getattr(u, 'username', str(user_id))
    return str(user_id)


def _utc_to_beijing(dt):
    """UTC 时间转北京时间（+8h），消息显示用"""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=__import__('datetime').timezone.utc)
    return dt.astimezone(__import__('datetime').timezone(timedelta(hours=8)))


def _serialize(msg):
    """序列化消息：时间转北京时间 + 附带项目已处理协同信息 + 提醒类型"""
    d = msg.to_dict()
    d['triggered_at'] = _utc_to_beijing(msg.triggered_at).isoformat() if msg.triggered_at else None
    d['handled_at'] = _utc_to_beijing(msg.handled_at).isoformat() if msg.handled_at else None

    # 提醒类型（按规则映射，供前端筛选）
    if msg.rule_id == 1:
        d['alert_type'] = 'no_meeting'
    elif msg.rule_id == 3:
        d['alert_type'] = 'no_followup'
    else:
        d['alert_type'] = 'other'

    # 协同处理：本项目若有其他用户已处理，本用户该项目的消息标为 handled_by_other
    if msg.status != 'done' and msg.source_type == 'investment_project' and msg.source_id:
        other_done = UserMessage.query.filter(
            UserMessage.source_type == 'investment_project',
            UserMessage.source_id == msg.source_id,
            UserMessage.status == 'done',
            UserMessage.handled_by.isnot(None),
        ).order_by(UserMessage.handled_at.desc()).first()
        if other_done:
            d['handled_by_other'] = other_done.handled_by
            d['handled_by_other_at'] = _utc_to_beijing(other_done.handled_at).isoformat() if other_done.handled_at else None
    return d


@api_bp.route('/messages/inbox', methods=['GET'])
def list_inbox():
    """当前用户消息列表(分页 + 状态筛选)"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    status = request.args.get('status', 'pending')  # pending | snoozed | done | superseded | all
    page = int(request.args.get('page', 1))
    size = int(request.args.get('page_size', 100))

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
            'items': [_serialize(m) for m in items],
        }
    }), 200


@api_bp.route('/messages/unread-count', methods=['GET'])
def unread_count():
    """待处理消息数（pending + 挂起），供 Navbar badge 用

    角标 = 待处理数量（打开抽屉不清零，处理消息后才减少）
    """
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 0, 'data': {'count': 0}}), 200

    count = UserMessage.query.filter(
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
        UserMessage.status.in_(['pending', 'snoozed']),
    ).count()
    return jsonify({'code': 0, 'data': {'count': count}}), 200


@api_bp.route('/messages/mark-read', methods=['POST'])
def mark_read():
    """打开抽屉时调用：将当前用户所有待处理消息标记为已读（角标清零）"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    UserMessage.query.filter(
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
        UserMessage.status.in_(['pending', 'snoozed']),
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'code': 0, 'message': '已全部标记为已读'}), 200


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
    msg.is_read = True
    db.session.commit()
    return jsonify({'code': 0, 'data': _serialize(msg), 'message': '已挂起'}), 200


@api_bp.route('/messages/<int:message_id>/done', methods=['POST'])
def done_message(message_id):
    """已处理：记录处理人与处理时间；同项目其他用户的消息标记为已处理"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    msg = UserMessage.query.filter_by(id=message_id, user_id=user_id, user_type=user_type).first()
    if not msg:
        return jsonify({'code': 1, 'message': '消息不存在'}), 404

    handler = _get_display_name(user_id, user_type)
    now = datetime.utcnow()

    # 同项目所有 pending/snoozed 消息（含其他用户）→ done + 处理人
    q = UserMessage.query.filter(
        UserMessage.source_type == 'investment_project',
        UserMessage.source_id == msg.source_id,
        UserMessage.status.in_(['pending', 'snoozed']),
    )
    rows = q.all()
    for m in rows:
        m.status = 'done'
        m.handled_at = now
        m.handled_by = handler
        m.is_read = True
    db.session.commit()

    # 刷新后返回当前用户最新的消息状态
    updated = UserMessage.query.filter(
        UserMessage.id.in_([r.id for r in rows]) if rows else [msg.id],
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
    ).all() if rows else [msg]
    return jsonify({'code': 0, 'data': [_serialize(m) for m in updated], 'message': '已处理，同项目其他用户将同步显示'}), 200


@api_bp.route('/messages/read-all', methods=['POST'])
def read_all():
    """全部标记已处理"""
    user_id, user_type = _get_current_user_info()
    if not user_id:
        return jsonify({'code': 1, 'message': '请先登录'}), 401

    now = datetime.utcnow()
    handler = _get_display_name(user_id, user_type)
    UserMessage.query.filter(
        UserMessage.user_id == user_id,
        UserMessage.user_type == user_type,
        UserMessage.status.in_(['pending', 'snoozed']),
    ).update({'status': 'done', 'handled_at': now, 'handled_by': handler, 'is_read': True})
    db.session.commit()
    return jsonify({'code': 0, 'message': '已全部标记为已处理'}), 200
