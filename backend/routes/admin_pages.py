from flask import request, jsonify
from flask_login import login_required
from models import CarouselPage
from extensions import db
from routes import admin_pages_bp


@admin_pages_bp.route('/pages', methods=['GET'])
@login_required
def list_pages():
    """获取所有轮播页（含未启用的）"""
    pages = CarouselPage.query.order_by(CarouselPage.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [p.to_dict() for p in pages]})


@admin_pages_bp.route('/pages/<int:page_id>', methods=['GET'])
@login_required
def get_page(page_id):
    """获取单个轮播页详情"""
    page = CarouselPage.query.get_or_404(page_id)
    return jsonify({'code': 0, 'data': page.to_dict()})


@admin_pages_bp.route('/pages', methods=['POST'])
@login_required
def create_page():
    """新建轮播页"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    page = CarouselPage(
        title=data.get('title', '未命名页面'),
        page_type=data.get('page_type', 'image_text'),
        map_scope=data.get('map_scope', 'china'),
        sort_order=data.get('sort_order', 0),
        is_active=data.get('is_active', True),
        background_image=data.get('background_image', ''),
        rich_text_content=data.get('rich_text_content', ''),
        text_position_x=data.get('text_position_x', 10.0),
        text_position_y=data.get('text_position_y', 10.0),
        text_width=data.get('text_width', 40.0),
        text_height=data.get('text_height', 80.0)
    )
    db.session.add(page)
    db.session.commit()
    return jsonify({'code': 0, 'data': page.to_dict(), 'message': '创建成功'})


@admin_pages_bp.route('/pages/<int:page_id>', methods=['PUT'])
@login_required
def update_page(page_id):
    """更新轮播页"""
    page = CarouselPage.query.get_or_404(page_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    # 更新字段
    updatable_fields = [
        'title', 'page_type', 'map_scope', 'sort_order', 'is_active',
        'background_image', 'rich_text_content',
        'text_position_x', 'text_position_y', 'text_width', 'text_height'
    ]
    for field in updatable_fields:
        if field in data:
            setattr(page, field, data[field])

    db.session.commit()
    return jsonify({'code': 0, 'data': page.to_dict(), 'message': '更新成功'})


@admin_pages_bp.route('/pages/<int:page_id>', methods=['DELETE'])
@login_required
def delete_page(page_id):
    """删除轮播页"""
    page = CarouselPage.query.get_or_404(page_id)
    db.session.delete(page)
    db.session.commit()
    return jsonify({'code': 0, 'message': '删除成功'})


@admin_pages_bp.route('/pages/reorder', methods=['PUT'])
@login_required
def reorder_pages():
    """批量排序轮播页"""
    data = request.get_json()
    if not data or 'orders' not in data:
        return jsonify({'code': 1, 'message': '请提供排序数据'}), 400

    orders = data['orders']  # [{id: 1, sort_order: 0}, {id: 2, sort_order: 1}]
    for item in orders:
        page = CarouselPage.query.get(item['id'])
        if page:
            page.sort_order = item['sort_order']

    db.session.commit()
    return jsonify({'code': 0, 'message': '排序更新成功'})
