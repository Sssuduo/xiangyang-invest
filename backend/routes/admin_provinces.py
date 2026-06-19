from flask import request, jsonify
from flask_login import login_required
from models import ProvinceInfo, CityInfo
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


# ============================================================
# 城市高亮配置（省份子级）
# ============================================================
@admin_provinces_bp.route('/provinces/<int:province_id>/cities', methods=['GET'])
@login_required
def list_province_cities(province_id):
    """获取省份下所有城市"""
    province = ProvinceInfo.query.get_or_404(province_id)
    cities = province.cities.order_by(CityInfo.city_code.asc()).all()
    return jsonify({'code': 0, 'data': [c.to_dict() for c in cities]})


@admin_provinces_bp.route('/provinces/<int:province_id>/cities/<int:city_id>', methods=['PUT'])
@login_required
def update_city(province_id, city_id):
    """更新单个城市信息"""
    city = CityInfo.query.filter_by(id=city_id, province_id=province_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    updatable_fields = ['is_highlighted', 'card_title', 'card_content']
    for field in updatable_fields:
        if field in data:
            setattr(city, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': city.to_dict(), 'message': '更新成功'})


@admin_provinces_bp.route('/provinces/<int:province_id>/cities/batch', methods=['POST'])
@login_required
def batch_update_city_highlights(province_id):
    """批量更新城市高亮"""
    data = request.get_json()
    if not data or 'highlight_ids' not in data:
        return jsonify({'code': 1, 'message': '请提供高亮ID列表'}), 400

    CityInfo.query.filter_by(province_id=province_id).update({'is_highlighted': False})
    if data['highlight_ids']:
        CityInfo.query.filter(CityInfo.id.in_(data['highlight_ids']))\
            .update({'is_highlighted': True}, synchronize_session=False)

    db.session.commit()
    return jsonify({'code': 0, 'message': '批量更新成功'})


@admin_provinces_bp.route('/provinces/<int:province_id>/cities/seed', methods=['POST'])
@login_required
def seed_cities_from_geojson(province_id):
    """从 GeoJSON 数据初始化该省份的城市记录"""
    import json
    import os

    province = ProvinceInfo.query.get_or_404(province_id)

    # 读取城市 GeoJSON
    geojson_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'static', 'data', 'china_cities.json'
    )
    if not os.path.exists(geojson_path):
        return jsonify({'code': 1, 'message': 'china_cities.json 文件不存在，请先生成数据'}), 400

    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    province_code = province.region_code
    created = 0

    for feature in data.get('features', []):
        props = feature.get('properties', {})
        parent_adcode = str(props.get('parent', {}).get('adcode', ''))

        if parent_adcode == province_code:
            city_code = str(props.get('adcode', ''))
            city_name = props.get('name', '')
            if not city_code or not city_name:
                continue

            existing = CityInfo.query.filter_by(
                province_id=province_id, city_code=city_code
            ).first()
            if not existing:
                city = CityInfo(
                    province_id=province_id,
                    city_code=city_code,
                    city_name=city_name,
                    is_highlighted=False
                )
                db.session.add(city)
                created += 1

    db.session.commit()
    return jsonify({
        'code': 0,
        'message': f'已为 {province.region_name} 初始化 {created} 个城市数据'
    })
