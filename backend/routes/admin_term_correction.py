"""术语校正 API

提供术语映射表的 CRUD 和应用到台账的接口。
"""
import logging
from flask import request, jsonify, current_app
from models import TermCorrection
from extensions import db
from routes import admin_term_correction_bp as _bp_alias  # 确保 routes/__init__.py 先完成 Blueprint 创建

import logging
from flask import request, jsonify, current_app
from models import TermCorrection
from extensions import db
from routes.business_auth import dual_login_required, visitor_block

logger = logging.getLogger(__name__)

# alias 兼容 routes 注册
admin_activity_ledger_bp = _bp_alias
admin_term_correction_bp = _bp_alias
from routes.business_auth import dual_login_required, visitor_block

logger = logging.getLogger(__name__)


@admin_activity_ledger_bp.route('/term-corrections', methods=['GET'])
@dual_login_required
def list_term_corrections():
    """列出全部术语校正。"""
    items = TermCorrection.query.order_by(TermCorrection.created_at.desc()).all()
    return jsonify({'code': 0, 'data': [c.to_dict() for c in items]})


@admin_activity_ledger_bp.route('/term-corrections', methods=['POST'])
@dual_login_required
@visitor_block
def create_term_correction():
    """新增术语校正。

    JSON body: { original, replacement, scope? }
    """
    data = request.get_json(silent=True) or {}
    original = (data.get('original') or '').strip()
    replacement = (data.get('replacement') or '').strip()
    scope = data.get('scope', 'all')
    if not original:
        return jsonify({'code': 1, 'message': '原文词汇不能为空'}), 400
    if scope not in ('all', 'summary', 'clean', 'segmented'):
        return jsonify({'code': 1, 'message': '无效的适用范围'}), 400
    from services.term_correction import create_or_update_correction
    from utils import get_current_user_info
    user = None
    try:
        user = get_current_user_info().get('username') if get_current_user_info() else None
    except Exception:
        pass
    try:
        item = create_or_update_correction(original, replacement, scope, user)
        return jsonify({'code': 0, 'message': '已保存', 'data': item.to_dict()})
    except Exception as e:
        logger.error(f'create_term_correction failed: {e}')
        return jsonify({'code': 1, 'message': f'保存失败: {str(e)[:200]}'}), 500


@admin_activity_ledger_bp.route('/term-corrections/<int:tc_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_term_correction(tc_id):
    """更新术语校正。

    JSON body: { original?, replacement?, scope?, is_active? }
    """
    item = TermCorrection.query.get(tc_id)
    if not item:
        return jsonify({'code': 1, 'message': '术语映射不存在'}), 404
    data = request.get_json(silent=True) or {}
    if 'original' in data:
        item.original = (data['original'] or '').strip()
    if 'replacement' in data:
        item.replacement = (data['replacement'] or '').strip()
    if 'scope' in data and data['scope'] in ('all', 'summary', 'clean', 'segmented'):
        item.apply_scope = data['scope']
    if 'is_active' in data:
        item.is_active = bool(data['is_active'])
    db.session.commit()
    return jsonify({'code': 0, 'message': '已更新', 'data': item.to_dict()})


@admin_activity_ledger_bp.route('/term-corrections/<int:tc_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_term_correction(tc_id):
    """删除术语校正。"""
    item = TermCorrection.query.get(tc_id)
    if not item:
        return jsonify({'code': 1, 'message': '术语映射不存在'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'code': 0, 'message': '已删除'})


@admin_activity_ledger_bp.route('/term-corrections/apply', methods=['POST'])
@dual_login_required
@visitor_block
def apply_term_corrections():
    """把术语校正应用到指定台账 (按 scope 替换所有相关字段)。

    JSON body: { item_id, scope? }
    """
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    scope = data.get('scope', 'all')
    if not item_id:
        return jsonify({'code': 1, 'message': 'item_id 必填'}), 400
    from models import ActivityLedger
    item = ActivityLedger.query.get(item_id)
    if not item:
        return jsonify({'code': 1, 'message': '台账不存在'}), 404
    from services.term_correction import apply_corrections_to_item
    try:
        n = apply_corrections_to_item(item, scope)
        return jsonify({'code': 0, 'message': f'已应用术语校正，替换 {n} 处', 'data': {'count': n}})
    except Exception as e:
        logger.error(f'apply_term_corrections failed: {e}')
        return jsonify({'code': 1, 'message': f'应用失败: {str(e)[:200]}'}), 500
