from functools import wraps
from flask import request, jsonify, session
from models import BusinessUser
from routes import business_auth_bp


def business_login_required(f):
    """业务用户登录验证装饰器（使用 Flask session）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('business_user_id')
        if not user_id:
            return jsonify({'code': 1, 'message': '请先登录'}), 401
        user = BusinessUser.query.get(int(user_id))
        if not user or not user.is_active:
            session.pop('business_user_id', None)
            return jsonify({'code': 1, 'message': '用户不存在或已禁用'}), 401
        return f(*args, **kwargs)
    return decorated


def dual_login_required(f):
    """
    双重登录验证装饰器：
    - 已登录的 AdminUser（Flask-Login）→ 放行
    - 已登录的 BusinessUser（session）→ 放行
    - 否则 → 401
    """
    from flask_login import current_user

    @wraps(f)
    def decorated(*args, **kwargs):
        # 先检查 AdminUser（Flask-Login）
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        # 再检查 BusinessUser（session）
        user_id = session.get('business_user_id')
        if user_id:
            user = BusinessUser.query.get(int(user_id))
            if user and user.is_active:
                return f(*args, **kwargs)
            session.pop('business_user_id', None)

        return jsonify({'code': 1, 'message': '请先登录'}), 401
    return decorated


@business_auth_bp.route('/login', methods=['POST'])
def login():
    """业务用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 1, 'message': '请输入用户名和密码'}), 400

    user = BusinessUser.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({'code': 1, 'message': '用户名或密码错误'}), 401

    if not user.is_active:
        return jsonify({'code': 1, 'message': '账号已被禁用，请联系管理员'}), 403

    session['business_user_id'] = user.id
    session.permanent = True
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '登录成功'})


@business_auth_bp.route('/logout', methods=['POST'])
def logout():
    """业务用户登出"""
    session.pop('business_user_id', None)
    return jsonify({'code': 0, 'message': '已登出'})


@business_auth_bp.route('/check', methods=['GET'])
def check_login():
    """检查业务用户登录状态"""
    user_id = session.get('business_user_id')
    if user_id:
        user = BusinessUser.query.get(int(user_id))
        if user and user.is_active:
            return jsonify({'code': 0, 'data': user.to_dict()})
        session.pop('business_user_id', None)
    return jsonify({'code': 1, 'message': '未登录'}), 401
