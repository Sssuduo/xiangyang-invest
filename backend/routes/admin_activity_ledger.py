import json
from datetime import datetime
from flask import request, jsonify
from models import ActivityLedger, InvestmentActivity, InvestmentProject
from extensions import db
from routes import admin_activity_ledger_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes


def _parse_datetime(val):
    """将字符串或 None 转为 datetime 对象（精确到分钟）"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


# ============================================================
# 活动台账 CRUD
# ============================================================

@admin_activity_ledger_bp.route('/activity-ledger', methods=['GET'])
@dual_login_required
def list_ledger():
    """活动台账列表（含搜索/筛选）"""
    search = request.args.get('search', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    tags = request.args.get('tags', '').strip()
    linked = request.args.get('linked', '').strip()  # '1'=已关联, '0'=未关联
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    q = ActivityLedger.query

    if search:
        like = f'%{search}%'
        q = q.filter(ActivityLedger.content.ilike(like))

    if date_from:
        q = q.filter(ActivityLedger.date >= date_from)
    if date_to:
        q = q.filter(ActivityLedger.date <= date_to)
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if tag_list:
            tag_conds = [ActivityLedger.tags.like(f'%{t}%') for t in tag_list]
            q = q.filter(db.or_(*tag_conds))
    if linked == '1':
        q = q.filter(ActivityLedger.linked_project_id.isnot(None))
    elif linked == '0':
        q = q.filter(ActivityLedger.linked_project_id.is_(None))

    total = q.count()
    q = q.order_by(ActivityLedger.date.desc())
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({'code': 0, 'data': [item.to_dict() for item in items], 'total': total})


@admin_activity_ledger_bp.route('/activity-ledger', methods=['POST'])
@dual_login_required
@visitor_block
def create_ledger():
    """新建活动台账"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    if not data.get('content'):
        return jsonify({'code': 1, 'message': '活动内容为必填字段'}), 400

    item = ActivityLedger(
        date=_parse_datetime(data.get('date')),
        content=data['content'],
        files=json.dumps(data.get('files', []), ensure_ascii=False),
        tags=json.dumps(data.get('tags', []), ensure_ascii=False)
    )

    db.session.add(item)
    db.session.flush()

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        changes = {
            'date': (None, item.date.isoformat() if item.date else None),
            'content': (None, item.content),
            'files': (None, item.files),
            'tags': (None, item.tags)
        }
        log_changes('activity_ledger', item.id, changes, 'create', user_info)

    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': '活动台账创建成功'})


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>', methods=['GET'])
@dual_login_required
def get_ledger(item_id):
    """获取活动台账详情"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    return jsonify({'code': 0, 'data': item.to_dict()})


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_ledger(item_id):
    """更新活动台账"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = ['date', 'content', 'files', 'tags']

    # 审计日志：保存旧值
    user_info = get_current_user_info()
    old_values = {}
    if user_info:
        for field in updatable_fields:
            old_val = getattr(item, field)
            if field == 'date':
                old_val = old_val.isoformat() if old_val else None
            elif field in ('files', 'tags'):
                old_val = old_val if old_val else '[]'
            old_values[field] = old_val

    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == 'date':
                val = _parse_datetime(val)
            elif field in ('files', 'tags'):
                val = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val
            setattr(item, field, val)

    # 审计日志：对比变更
    if user_info:
        changes = {}
        for field in updatable_fields:
            old_val = old_values.get(field)
            new_val = getattr(item, field)
            if field == 'date':
                new_val = new_val.isoformat() if new_val else None
            elif field in ('files', 'tags'):
                new_val = new_val if new_val else '[]'
            if str(old_val) != str(new_val):
                changes[field] = (old_val, new_val)
        log_changes('activity_ledger', item_id, changes, 'update', user_info)

    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': '更新成功'})


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_ledger(item_id):
    """物理删除活动台账"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'code': 0, 'message': '活动台账已删除'})


@admin_activity_ledger_bp.route('/activity-ledger/batch-delete', methods=['POST'])
@dual_login_required
@visitor_block
def batch_delete_ledger():
    """批量删除活动台账"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'code': 1, 'message': '请提供要删除的ID列表'}), 400

    deleted = ActivityLedger.query.filter(ActivityLedger.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({'code': 0, 'message': f'成功删除 {deleted} 条', 'data': {'count': deleted}})


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/link', methods=['POST'])
@dual_login_required
@visitor_block
def link_to_project(item_id):
    """将活动台账关联到招商项目——写入投资动态表并建立关联"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if item.linked_project_id:
        return jsonify({'code': 1, 'message': '该记录已关联项目，请先取消关联'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    project_id = data.get('project_id')
    if not project_id:
        return jsonify({'code': 1, 'message': '请选择要关联的招商项目'}), 400

    # 校验项目存在
    project = InvestmentProject.query.filter_by(id=int(project_id), is_deleted=False).first()
    if not project:
        return jsonify({'code': 1, 'message': '所选项目不存在'}), 404

    # 写入招商动态表
    activity = InvestmentActivity(
        project_id=project.id,
        date=item.date,
        content=item.content,
        files=item.files,
        tags=item.tags
    )
    db.session.add(activity)
    db.session.flush()

    # 建立关联
    item.linked_project_id = project.id
    item.linked_activity_id = activity.id

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        log_changes('activity_ledger', item_id, {
            'linked_project_id': (None, project.id),
            'linked_activity_id': (None, activity.id)
        }, 'link', user_info)
        log_changes('investment_activities', activity.id, {
            'project_id': (None, activity.project_id),
            'date': (None, activity.date.isoformat() if activity.date else None),
            'content': (None, activity.content),
            'files': (None, activity.files),
            'tags': (None, activity.tags)
        }, 'create', user_info)

    db.session.commit()
    return jsonify({
        'code': 0,
        'data': item.to_dict(),
        'message': f'已关联至项目「{project.project_name}」并同步到招商动态'
    })


@admin_activity_ledger_bp.route('/activity-ledger/<int:item_id>/unlink', methods=['POST'])
@dual_login_required
@visitor_block
def unlink_from_project(item_id):
    """取消活动台账与项目的关联（保留招商动态记录）"""
    item = ActivityLedger.query.filter_by(id=item_id).first_or_404()

    if not item.linked_project_id:
        return jsonify({'code': 1, 'message': '该记录尚未关联项目'}), 400

    old_project_id = item.linked_project_id
    old_activity_id = item.linked_activity_id

    item.linked_project_id = None
    item.linked_activity_id = None

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        log_changes('activity_ledger', item_id, {
            'linked_project_id': (old_project_id, None),
            'linked_activity_id': (old_activity_id, None)
        }, 'unlink', user_info)

    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': '已取消关联（原招商动态记录保留）'})
