from flask import request, jsonify
from flask_login import login_required
from models import ContactInfo
from extensions import db
from routes import admin_contact_bp


@admin_contact_bp.route('/contact', methods=['GET'])
@login_required
def get_contact():
    """获取联系我们配置"""
    config = ContactInfo.query.first()
    if not config:
        config = ContactInfo()
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


@admin_contact_bp.route('/contact', methods=['PUT'])
@login_required
def update_contact():
    """更新联系我们配置"""
    config = ContactInfo.query.first()
    if not config:
        config = ContactInfo()
        db.session.add(config)

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = [
        'name', 'title', 'phone', 'email', 'intro', 'wechat_qr_image'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(), 'message': '联系我们配置更新成功'})
