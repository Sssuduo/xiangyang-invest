import os
import traceback
from flask import jsonify, current_app
from flask_login import login_required
from flask import Blueprint

admin_debug_bp = Blueprint('admin_debug', __name__, url_prefix='/api/admin')


def get_debug_mode_file():
    """获取 debug 模式标记文件路径"""
    return current_app.config.get('DEBUG_MODE_FILE',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', '.debug_mode'))


def is_debug_enabled():
    """检查 debug 模式是否开启"""
    try:
        return os.path.exists(get_debug_mode_file())
    except Exception:
        return False


def get_full_traceback(exc):
    """获取完整堆栈信息"""
    return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))


@admin_debug_bp.route('/debug/status', methods=['GET'])
@login_required
def debug_status():
    """获取 debug 模式状态"""
    return jsonify({
        'code': 0,
        'data': {
            'enabled': is_debug_enabled(),
            'app_debug': current_app.debug
        }
    })


@admin_debug_bp.route('/debug/toggle', methods=['POST'])
@login_required
def debug_toggle():
    """切换 debug 模式"""
    file_path = get_debug_mode_file()
    try:
        if is_debug_enabled():
            os.remove(file_path)
            return jsonify({'code': 0, 'data': {'enabled': False}, 'message': 'Debug 模式已关闭'})
        else:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write('1')
            return jsonify({'code': 0, 'data': {'enabled': True}, 'message': 'Debug 模式已开启'})
    except Exception as e:
        return jsonify({'code': 1, 'message': f'切换失败: {str(e)}'}), 500


def register_debug_routes(app):
    """注册 debug 相关路由和错误处理器"""
    app.register_blueprint(admin_debug_bp)

    # 全局错误处理 — 当 debug 模式开启时返回完整堆栈
    @app.errorhandler(500)
    def internal_error(e):
        if is_debug_enabled() or app.debug:
            return jsonify({
                'code': 1,
                'message': str(e) if str(e) else '服务器内部错误',
                'traceback': get_full_traceback(e) if hasattr(e, '__traceback__') else str(e)
            }), 500
        return jsonify({'code': 1, 'message': '服务器内部错误，请稍后重试'}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        if is_debug_enabled() or app.debug:
            return jsonify({
                'code': 1,
                'message': str(e),
                'traceback': get_full_traceback(e),
                'type': type(e).__name__
            }), 500
        # 始终记录错误日志，方便排查
        app.logger.error(f'Unhandled exception: {type(e).__name__}: {e}')
        app.logger.error(get_full_traceback(e))
        # 返回具体错误信息，便于前端排查
        msg = str(e) if str(e) else '请求处理失败'
        return jsonify({'code': 1, 'message': msg}), 500
