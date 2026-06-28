"""
后台管理 — 专班工作人员（Staff）CRUD API
"""
from flask import request, jsonify
from models import Staff, BusinessUser
from extensions import db
from routes import admin_staff_bp
from flask_login import login_required


@admin_staff_bp.route('/staff', methods=['GET'])
@login_required
def list_staff():
    """列表：所有工作人员，按 sort_order 升序"""
    items = Staff.query.order_by(Staff.sort_order.asc()).all()
    # 预取关联业务用户信息
    biz_user_ids = [s.user_id for s in items if s.user_id]
    biz_user_map = {}
    if biz_user_ids:
        biz_users = BusinessUser.query.filter(BusinessUser.id.in_(biz_user_ids)).all()
        biz_user_map = {u.id: u for u in biz_users}

    result = []
    for s in items:
        d = s.to_dict()
        if s.user_id and s.user_id in biz_user_map:
            d['admin_username'] = biz_user_map[s.user_id].username
            d['admin_display_name'] = biz_user_map[s.user_id].display_name or biz_user_map[s.user_id].username
        else:
            d['admin_username'] = ''
            d['admin_display_name'] = ''
        result.append(d)
    return jsonify({'code': 0, 'data': result})


@admin_staff_bp.route('/staff/admins', methods=['GET'])
@login_required
def list_admins():
    """下拉用：所有业务用户账号列表"""
    biz_users = BusinessUser.query.filter_by(is_active=True).order_by(BusinessUser.id.asc()).all()
    return jsonify({
        'code': 0,
        'data': [{
            'id': u.id,
            'username': u.username,
            'display_name': u.display_name or u.username,
        } for u in biz_users]
    })


@admin_staff_bp.route('/staff', methods=['POST'])
@login_required
def create_staff():
    """新增工作人员"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据为空'}), 400
    name = (data.get('name', '') or '').strip()
    if not name:
        return jsonify({'code': 1, 'message': '姓名不能为空'}), 400

    staff = Staff(
        name=name,
        position=data.get('position', '') or '农高区创建专班工作人员',
        user_id=data.get('user_id') or None,
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(staff)
    db.session.commit()
    return jsonify({'code': 0, 'data': staff.to_dict(), 'message': '已添加'})


@admin_staff_bp.route('/staff/<int:staff_id>', methods=['PUT'])
@login_required
def update_staff(staff_id):
    """编辑工作人员"""
    staff = Staff.query.get_or_404(staff_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据为空'}), 400

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({'code': 1, 'message': '姓名不能为空'}), 400
        staff.name = name
    if 'position' in data:
        staff.position = data['position'] or ''
    if 'user_id' in data:
        staff.user_id = data['user_id'] or None
    if 'is_active' in data:
        staff.is_active = bool(data['is_active'])
    if 'sort_order' in data:
        staff.sort_order = int(data['sort_order'])

    db.session.commit()
    return jsonify({'code': 0, 'data': staff.to_dict(), 'message': '已更新'})


@admin_staff_bp.route('/staff/<int:staff_id>', methods=['DELETE'])
@login_required
def delete_staff(staff_id):
    """删除工作人员"""
    staff = Staff.query.get_or_404(staff_id)
    db.session.delete(staff)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})
