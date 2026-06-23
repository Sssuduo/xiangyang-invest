"""字典管理 API — 统一管理所有字典表"""
from flask import request, jsonify
from flask_login import login_required
from models import (
    FollowStatusDict, MeetingStatusDict, OrganizationDict,
    ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict
)
from extensions import db
from routes import admin_dict_bp

# 字典类型 → (模型类, 字段列表, 是否有颜色字段)
DICT_REGISTRY = {
    'follow_statuses': (FollowStatusDict, ['code', 'name', 'display_color', 'sort_order', 'is_active'], True),
    'meeting_statuses': (MeetingStatusDict, ['code', 'name', 'display_color', 'sort_order', 'is_active'], True),
    'organizations': (OrganizationDict, ['code', 'name', 'sort_order', 'is_active'], False),
    'project_types': (ProjectTypeDict, ['code', 'name', 'sort_order', 'is_active'], False),
    'demand_types': (DemandTypeDict, ['code', 'name', 'parent_code', 'sort_order', 'is_active'], False),
    'project_tags': (ProjectTagDict, ['code', 'name', 'sort_order', 'is_active'], False),
    'activity_tags': (ActivityTagDict, ['code', 'name', 'sort_order', 'is_active'], False),
}


def _get_model(dict_type):
    """根据字典类型获取模型类"""
    entry = DICT_REGISTRY.get(dict_type)
    if not entry:
        return None
    return entry[0]


def _get_fields(dict_type):
    """获取该字典类型的可编辑字段列表"""
    entry = DICT_REGISTRY.get(dict_type)
    if not entry:
        return []
    return entry[1]


# ============================================================
# 列表
# ============================================================

@admin_dict_bp.route('/dicts/<dict_type>', methods=['GET'])
@login_required
def list_dict(dict_type):
    """获取指定字典类型的所有条目"""
    model = _get_model(dict_type)
    if not model:
        return jsonify({'code': 1, 'message': f'未知的字典类型: {dict_type}'}), 400

    items = model.query.order_by(model.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [item.to_dict() for item in items]})


# ============================================================
# 新增
# ============================================================

@admin_dict_bp.route('/dicts/<dict_type>', methods=['POST'])
@login_required
def create_dict(dict_type):
    """新增字典条目"""
    model = _get_model(dict_type)
    if not model:
        return jsonify({'code': 1, 'message': f'未知的字典类型: {dict_type}'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    code = (data.get('code', '') or '').strip()
    name = (data.get('name', '') or '').strip()
    if not code or not name:
        return jsonify({'code': 1, 'message': '编码和名称不能为空'}), 400

    # 检查 code 唯一性
    if model.query.filter_by(code=code).first():
        return jsonify({'code': 1, 'message': f'编码 "{code}" 已存在'}), 400

    max_order = db.session.query(db.func.max(model.sort_order)).scalar() or 0

    kwargs = {
        'code': code,
        'name': name,
        'sort_order': max_order + 1,
        'is_active': data.get('is_active', True)
    }
    # 支持可选字段
    fields = _get_fields(dict_type)
    if 'display_color' in fields:
        kwargs['display_color'] = data.get('display_color', '#909399')
    if 'parent_code' in fields:
        kwargs['parent_code'] = data.get('parent_code', '')

    item = model(**kwargs)
    db.session.add(item)
    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': '创建成功'})


# ============================================================
# 更新
# ============================================================

@admin_dict_bp.route('/dicts/<dict_type>/<int:item_id>', methods=['PUT'])
@login_required
def update_dict(dict_type, item_id):
    """更新字典条目"""
    model = _get_model(dict_type)
    if not model:
        return jsonify({'code': 1, 'message': f'未知的字典类型: {dict_type}'}), 400

    item = model.query.get_or_404(item_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    fields = _get_fields(dict_type)
    for field in fields:
        if field in data:
            setattr(item, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': item.to_dict(), 'message': '更新成功'})


# ============================================================
# 删除
# ============================================================

@admin_dict_bp.route('/dicts/<dict_type>/<int:item_id>', methods=['DELETE'])
@login_required
def delete_dict(dict_type, item_id):
    """删除字典条目"""
    model = _get_model(dict_type)
    if not model:
        return jsonify({'code': 1, 'message': f'未知的字典类型: {dict_type}'}), 400

    item = model.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'code': 0, 'message': '删除成功'})


# ============================================================
# 批量排序
# ============================================================

@admin_dict_bp.route('/dicts/<dict_type>/reorder', methods=['POST'])
@login_required
def reorder_dict(dict_type):
    """批量更新排序（接收 id 列表，按顺序赋值 sort_order=1,2,3...）"""
    model = _get_model(dict_type)
    if not model:
        return jsonify({'code': 1, 'message': f'未知的字典类型: {dict_type}'}), 400

    data = request.get_json()
    ordered_ids = data.get('ids', []) if data else []
    if not ordered_ids:
        return jsonify({'code': 1, 'message': 'ids 不能为空'}), 400

    for i, item_id in enumerate(ordered_ids):
        item = model.query.get(item_id)
        if item:
            item.sort_order = i + 1

    db.session.commit()
    return jsonify({'code': 0, 'message': '排序已更新'})
