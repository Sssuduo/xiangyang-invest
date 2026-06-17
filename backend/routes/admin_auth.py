from flask import request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import AdminUser
from routes import admin_auth_bp


@admin_auth_bp.route('/login', methods=['POST'])
def login():
    """管理员登录"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 1, 'message': '请输入用户名和密码'}), 400

    user = AdminUser.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({'code': 1, 'message': '用户名或密码错误'}), 401

    login_user(user, remember=True)
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '登录成功'})


@admin_auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """管理员登出"""
    logout_user()
    return jsonify({'code': 0, 'message': '已登出'})


@admin_auth_bp.route('/check', methods=['GET'])
def check_login():
    """检查登录状态"""
    if current_user.is_authenticated:
        return jsonify({'code': 0, 'data': current_user.to_dict()})
    return jsonify({'code': 1, 'message': '未登录'}), 401
