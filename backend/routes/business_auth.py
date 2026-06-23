from functools import wraps
from flask import request, jsonify, session
from models import BusinessUser
from extensions import db
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


@business_auth_bp.route('/profile', methods=['PUT'])
@business_login_required
def update_profile():
    """修改显示名称"""
    user_id = session.get('business_user_id')
    user = BusinessUser.query.get(int(user_id))
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    display_name = (data.get('display_name', '') or '').strip()
    if not display_name:
        return jsonify({'code': 1, 'message': '显示名称不能为空'}), 400

    user.display_name = display_name
    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '显示名称已更新'})


@business_auth_bp.route('/password', methods=['PUT'])
@business_login_required
def change_password():
    """修改密码（修改后强制重新登录）"""
    user_id = session.get('business_user_id')
    user = BusinessUser.query.get(int(user_id))
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'code': 1, 'message': '请填写原密码和新密码'}), 400
    if len(new_password) < 6:
        return jsonify({'code': 1, 'message': '新密码至少6位'}), 400
    if not user.check_password(old_password):
        return jsonify({'code': 1, 'message': '原密码错误'}), 400

    user.set_password(new_password)
    db.session.commit()
    session.pop('business_user_id', None)
    return jsonify({'code': 0, 'message': '密码已修改，请重新登录'})
