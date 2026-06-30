import json
from datetime import datetime
from flask import request, jsonify
from models import InvestmentActivity, InvestmentProject, EnterpriseDemand, ActivityDemandLink
from extensions import db
from routes import admin_activity_bp
from routes.business_auth import dual_login_required, visitor_block
from utils import get_current_user_info, log_changes


def _parse_datetime(val):
    """将字符串或 None 转为 datetime 对象（精确到分钟）"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # 支持 YYYY-MM-DD HH:MM 或 ISO 格式
        return datetime.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


def _sync_activity_demands(activity, demand_ids):
    """同步活动关联的诉求：先清旧关联，再批量插入新关联"""
    ActivityDemandLink.query.filter_by(activity_id=activity.id).delete()
    if demand_ids:
        for did in demand_ids:
            db.session.add(ActivityDemandLink(activity_id=activity.id, demand_id=int(did)))


def _enrich_activity_dict(item):
    """为活动 dict 添加 linked_demands 字段"""
    activity = InvestmentActivity.query.get(item['id'])
    if activity:
        item['linked_demands'] = [
            {
                'id': d.id,
                'demand_content': d.demand_content[:80] if d.demand_content else '',
                'status': d.status
            }
            for d in activity.linked_demands.all()
        ]
    else:
        item['linked_demands'] = []
    return item


# ============================================================
# 招商动态 CRUD
# ============================================================

@admin_activity_bp.route('/activity/activities', methods=['GET'])
@dual_login_required
def list_activities():
    """动态列表（含搜索/筛选）"""
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
    result = [_enrich_activity_dict(a.to_dict()) for a in activities]
    return jsonify({'code': 0, 'data': result, 'total': total})


@admin_activity_bp.route('/activity/activities', methods=['POST'])
@dual_login_required
@visitor_block
def create_activity():
    """新建动态"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 必填字段校验（date 改为选填）
    required = ['project_id', 'content']
    for field in required:
        if not data.get(field):
            return jsonify({'code': 1, 'message': f'{field} 为必填字段'}), 400

    activity = InvestmentActivity(
        project_id=int(data['project_id']),
        date=_parse_datetime(data['date']),
        content=data['content'],
        files=json.dumps(data.get('files', []), ensure_ascii=False),
        tags=json.dumps(data.get('tags', []), ensure_ascii=False)
    )

    db.session.add(activity)
    db.session.flush()

    # 同步关联诉求
    demand_ids = data.get('demand_ids', [])
    if demand_ids:
        _sync_activity_demands(activity, demand_ids)

    # 审计日志
    user_info = get_current_user_info()
    if user_info:
        changes = {
            'project_id': (None, activity.project_id),
            'date': (None, activity.date.isoformat() if activity.date else None),
            'content': (None, activity.content),
            'files': (None, activity.files),
            'tags': (None, activity.tags),
            'demand_ids': (None, json.dumps(demand_ids))
        }
        log_changes('investment_activities', activity.id, changes, 'create', user_info)

    db.session.commit()
    result = _enrich_activity_dict(activity.to_dict())
    return jsonify({'code': 0, 'data': result, 'message': '动态创建成功'})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['GET'])
@dual_login_required
def get_activity(activity_id):
    """获取动态详情（含项目名称 + 关联诉求）"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    result = _enrich_activity_dict(activity.to_dict())
    return jsonify({'code': 0, 'data': result})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_activity(activity_id):
    """更新动态"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = ['project_id', 'date', 'content', 'files', 'tags']

    # 审计日志：保存旧值
    user_info = get_current_user_info()
    old_values = {}
    if user_info:
        for field in updatable_fields:
            old_val = getattr(activity, field)
            if field == 'date':
                old_val = old_val.isoformat() if old_val else None
            elif field in ('files', 'tags'):
                old_val = old_val if old_val else '[]'
            old_values[field] = old_val

    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == 'project_id':
                val = int(val) if val else None
            elif field == 'date':
                val = _parse_datetime(val)
            elif field in ('files', 'tags'):
                val = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val
            setattr(activity, field, val)

    # 同步关联诉求
    if 'demand_ids' in data:
        _sync_activity_demands(activity, data['demand_ids'])

    # 审计日志：对比变更
    if user_info:
        changes = {}
        for field in updatable_fields:
            old_val = old_values.get(field)
            new_val = getattr(activity, field)
            if field == 'date':
                new_val = new_val.isoformat() if new_val else None
            elif field in ('files', 'tags'):
                new_val = new_val if new_val else '[]'
            if str(old_val) != str(new_val):
                changes[field] = (old_val, new_val)
        if 'demand_ids' in data:
            old_dids = [link.demand_id for link in ActivityDemandLink.query.filter_by(activity_id=activity_id).all()]
            new_dids = data['demand_ids']
            if sorted(old_dids) != sorted(new_dids):
                changes['demand_ids'] = (old_dids, new_dids)
        if changes:
            log_changes('investment_activities', activity_id, changes, 'update', user_info)

    db.session.commit()
    result = _enrich_activity_dict(activity.to_dict())
    return jsonify({'code': 0, 'data': result, 'message': '更新成功'})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_activity(activity_id):
    """物理删除动态"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    db.session.delete(activity)
    db.session.commit()
    return jsonify({'code': 0, 'message': '动态已删除'})


@admin_activity_bp.route('/activity/activities/batch-delete', methods=['POST'])
@dual_login_required
@visitor_block
def batch_delete_activities():
    """批量删除动态"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'code': 1, 'message': '请提供要删除的动态ID列表'}), 400

    deleted = InvestmentActivity.query.filter(InvestmentActivity.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({'code': 0, 'message': f'成功删除 {deleted} 条动态', 'data': {'count': deleted}})
