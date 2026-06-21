import json
from datetime import datetime
from flask import request, jsonify
from flask_login import login_required
from models import InvestmentActivity, InvestmentProject
from extensions import db
from routes import admin_activity_bp


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


# ============================================================
# 招商动态 CRUD
# ============================================================

@admin_activity_bp.route('/activity/activities', methods=['GET'])
@login_required
def list_activities():
    """动态列表（含搜索/筛选）"""
    search = request.args.get('search', '').strip()
    project_id = request.args.get('project_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

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

    q = q.order_by(InvestmentActivity.date.desc())
    activities = q.all()
    return jsonify({'code': 0, 'data': [a.to_dict() for a in activities]})


@admin_activity_bp.route('/activity/activities', methods=['POST'])
@login_required
def create_activity():
    """新建动态"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 必填字段校验
    required = ['project_id', 'date', 'content']
    for field in required:
        if not data.get(field):
            return jsonify({'code': 1, 'message': f'{field} 为必填字段'}), 400

    activity = InvestmentActivity(
        project_id=int(data['project_id']),
        date=_parse_datetime(data['date']),
        content=data['content'],
        files=json.dumps(data.get('files', []), ensure_ascii=False)
    )

    db.session.add(activity)
    db.session.commit()
    return jsonify({'code': 0, 'data': activity.to_dict(), 'message': '动态创建成功'})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['GET'])
@login_required
def get_activity(activity_id):
    """获取动态详情（含项目名称）"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    return jsonify({'code': 0, 'data': activity.to_dict()})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['PUT'])
@login_required
def update_activity(activity_id):
    """更新动态"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = ['project_id', 'date', 'content', 'files']
    for field in updatable_fields:
        if field in data:
            val = data[field]
            if field == 'project_id':
                val = int(val) if val else None
            elif field == 'date':
                val = _parse_datetime(val)
            elif field == 'files':
                val = json.dumps(val, ensure_ascii=False) if isinstance(val, list) else val
            setattr(activity, field, val)

    db.session.commit()
    return jsonify({'code': 0, 'data': activity.to_dict(), 'message': '更新成功'})


@admin_activity_bp.route('/activity/activities/<int:activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    """物理删除动态"""
    activity = InvestmentActivity.query.filter_by(id=activity_id).first_or_404()
    db.session.delete(activity)
    db.session.commit()
    return jsonify({'code': 0, 'message': '动态已删除'})
