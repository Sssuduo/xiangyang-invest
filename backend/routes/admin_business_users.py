from flask import request, jsonify
from flask_login import login_required
from models import BusinessUser
from extensions import db
from routes import admin_business_users_bp


@admin_business_users_bp.route('/business-users', methods=['GET'])
@login_required
def list_users():
    """获取业务用户列表"""
    users = BusinessUser.query.order_by(BusinessUser.created_at.desc()).all()
    return jsonify({'code': 0, 'data': [u.to_dict() for u in users]})


@admin_business_users_bp.route('/business-users', methods=['POST'])
@login_required
def create_user():
    """创建业务用户"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    display_name = data.get('display_name', '').strip()

    if not username or not password:
        return jsonify({'code': 1, 'message': '用户名和密码为必填项'}), 400

    if BusinessUser.query.filter_by(username=username).first():
        return jsonify({'code': 1, 'message': f'用户名「{username}」已存在'}), 409

    user = BusinessUser(
        username=username,
        display_name=display_name or username,
        is_active=data.get('is_active', True)
    )
    user.set_password(password)

    # 权限配置
    permissions = data.get('permissions', {})
    if isinstance(permissions, dict):
        user.set_permissions(permissions)

    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '用户创建成功'})


@admin_business_users_bp.route('/business-users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """获取单个业务用户详情"""
    user = BusinessUser.query.get_or_404(user_id)
    return jsonify({'code': 0, 'data': user.to_dict()})


@admin_business_users_bp.route('/business-users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """更新业务用户"""
    user = BusinessUser.query.get_or_404(user_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 用户名
    new_username = data.get('username', '').strip()
    if new_username and new_username != user.username:
        if BusinessUser.query.filter_by(username=new_username).first():
            return jsonify({'code': 1, 'message': f'用户名「{new_username}」已存在'}), 409
        user.username = new_username

    # 显示名称
    if 'display_name' in data:
        user.display_name = data['display_name'].strip() or user.username

    # 启用状态
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    # 密码（仅当提供时才修改）
    new_password = data.get('password', '')
    if new_password:
        user.set_password(new_password)

    # 权限配置
    if 'permissions' in data:
        permissions = data['permissions']
        if isinstance(permissions, dict):
            user.set_permissions(permissions)

    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '用户更新成功'})


@admin_business_users_bp.route('/business-users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """删除业务用户"""
    user = BusinessUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 0, 'message': '用户已删除'})
