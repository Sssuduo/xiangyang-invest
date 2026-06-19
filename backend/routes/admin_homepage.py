from flask import request, jsonify
from flask_login import login_required
from models import HomepageConfig
from extensions import db
from routes import admin_homepage_bp


@admin_homepage_bp.route('/homepage', methods=['GET'])
@login_required
def get_homepage():
    """获取首页配置"""
    config = HomepageConfig.query.first()
    if not config:
        config = HomepageConfig()
        db.session.add(config)
        db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict()})


@admin_homepage_bp.route('/homepage', methods=['PUT'])
@login_required
def update_homepage():
    """更新首页配置"""
    config = HomepageConfig.query.first()
    if not config:
        config = HomepageConfig()
        db.session.add(config)

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = [
        'background_image', 'title_text', 'subtitle_text',
        'carousel_interval', 'carousel_display_mode',
        'carousel_width', 'carousel_height',
        'presentation_interval', 'carousel_autoplay', 'presentation_autoplay'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': config.to_dict(), 'message': '首页配置更新成功'})
