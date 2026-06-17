from flask import request, jsonify
from flask_login import login_required
from models import ProvinceInfo
from extensions import db
from routes import admin_provinces_bp


@admin_provinces_bp.route('/provinces', methods=['GET'])
@login_required
def list_provinces():
    """获取省份信息列表"""
    scope = request.args.get('scope', 'china')
    provinces = ProvinceInfo.query.filter_by(map_scope=scope)\
        .order_by(ProvinceInfo.region_code.asc()).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in provinces]})


@admin_provinces_bp.route('/provinces/<int:province_id>', methods=['GET'])
@login_required
def get_province(province_id):
    """获取单个省份详情"""
    province = ProvinceInfo.query.get_or_404(province_id)
    return jsonify({'code': 0, 'data': province.to_dict()})


@admin_provinces_bp.route('/provinces/<int:province_id>', methods=['PUT'])
@login_required
def update_province(province_id):
    """更新省份信息"""
    province = ProvinceInfo.query.get_or_404(province_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = ['card_title', 'card_content', 'is_highlighted', 'region_name']
    for field in updatable_fields:
        if field in data:
            setattr(province, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': province.to_dict(), 'message': '更新成功'})


@admin_provinces_bp.route('/provinces/batch', methods=['POST'])
@login_required
def batch_update_highlights():
    """批量更新高亮状态"""
    data = request.get_json()
    if not data or 'highlight_ids' not in data:
        return jsonify({'code': 1, 'message': '请提供高亮ID列表'}), 400

    highlight_ids = data['highlight_ids']
    scope = data.get('scope', 'china')

    # 先取消该 scope 下所有高亮
    ProvinceInfo.query.filter_by(map_scope=scope).update({'is_highlighted': False})

    # 设置新高亮
    if highlight_ids:
        ProvinceInfo.query.filter(ProvinceInfo.id.in_(highlight_ids))\
            .update({'is_highlighted': True}, synchronize_session=False)

    db.session.commit()
    return jsonify({'code': 0, 'message': '批量更新成功'})
