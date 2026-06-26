import os
from flask import request, jsonify, current_app
from models import PromoVideo
from extensions import db
from routes import admin_promo_video_bp
from routes.business_auth import dual_login_required


# ============================================================
# 公开接口 — 前台视频列表
# ============================================================

@admin_promo_video_bp.route('/promo-videos', methods=['GET'])
def public_list_videos():
    """公开：获取视频列表（按 sort_order 排序）"""
    videos = PromoVideo.query.order_by(PromoVideo.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [_enrich_video_with_size(v.to_dict()) for v in videos]})


# ============================================================
# 管理接口 — CRUD
# ============================================================

@admin_promo_video_bp.route('/promo-videos/manage', methods=['GET'])
@dual_login_required
def admin_list_videos():
    """管理：获取视频列表"""
    videos = PromoVideo.query.order_by(PromoVideo.sort_order.asc()).all()
    return jsonify({'code': 0, 'data': [_enrich_video_with_size(v.to_dict()) for v in videos]})


@admin_promo_video_bp.route('/promo-videos/manage', methods=['POST'])
@dual_login_required
def admin_create_video():
    """管理：新增视频"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '数据为空'}), 400

    title = (data.get('title') or '').strip()
    file_path = (data.get('file_path') or '').strip()

    if not title:
        return jsonify({'code': 1, 'message': '请输入视频标题'}), 400
    if not file_path:
        return jsonify({'code': 1, 'message': '请上传视频文件'}), 400

    max_order = db.session.query(db.func.max(PromoVideo.sort_order)).scalar() or 0
    video = PromoVideo(
        title=title,
        file_path=file_path,
        sort_order=max_order + 1
    )
    db.session.add(video)
    db.session.commit()

    # 生成缩略图
    _generate_thumbnail(video)

    return jsonify({'code': 0, 'data': video.to_dict(), 'message': '已添加'})


@admin_promo_video_bp.route('/promo-videos/manage/<int:video_id>', methods=['PUT'])
@dual_login_required
def admin_update_video(video_id):
    """管理：编辑视频"""
    video = PromoVideo.query.get(video_id)
    if not video:
        return jsonify({'code': 1, 'message': '视频不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '数据为空'}), 400

    title = (data.get('title') or '').strip()
    file_path = (data.get('file_path') or '').strip()

    if not title:
        return jsonify({'code': 1, 'message': '请输入视频标题'}), 400

    video.title = title
    path_changed = False
    if file_path:
        # 如果新上传了视频，删除旧文件
        old_path = video.file_path
        if old_path and old_path != file_path:
            _try_delete_file(old_path)
            # 同时删除旧缩略图
            _try_delete_file(_thumb_path_for(old_path))
        video.file_path = file_path
        path_changed = True

    db.session.commit()

    # 新视频生成缩略图
    if path_changed:
        _generate_thumbnail(video)

    return jsonify({'code': 0, 'data': video.to_dict(), 'message': '已更新'})


@admin_promo_video_bp.route('/promo-videos/manage/<int:video_id>', methods=['DELETE'])
@dual_login_required
def admin_delete_video(video_id):
    """管理：删除视频"""
    video = PromoVideo.query.get(video_id)
    if not video:
        return jsonify({'code': 1, 'message': '视频不存在'}), 404

    file_path = video.file_path
    db.session.delete(video)
    db.session.commit()

    # 删除视频文件和缩略图
    _try_delete_file(file_path)
    _try_delete_file(_thumb_path_for(file_path))

    # 重新整理序号
    _renumber_videos()

    return jsonify({'code': 0, 'message': '已删除'})


@admin_promo_video_bp.route('/promo-videos/manage/sort', methods=['PUT'])
@dual_login_required
def admin_sort_videos():
    """管理：批量更新排序"""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'code': 1, 'message': '格式错误'}), 400

    for item in data:
        video = PromoVideo.query.get(item.get('id'))
        if video:
            video.sort_order = int(item.get('sort_order', 0))

    db.session.commit()
    return jsonify({'code': 0, 'message': '排序已更新'})


# ============================================================
# 辅助函数
# ============================================================

def _get_file_size_bytes(file_path):
    """获取文件大小（字节），失败返回 -1"""
    if not file_path:
        return -1
    try:
        static_dir = current_app.static_folder or os.path.join(current_app.root_path, '..', 'static')
        abs_path = os.path.join(static_dir, file_path.replace('/static/', '').replace('\\', '/'))
        if os.path.exists(abs_path):
            return os.path.getsize(abs_path)
    except Exception:
        pass
    return -1


def _enrich_video_with_size(video_dict):
    """为视频字典添加文件大小字段"""
    video_dict['file_size'] = _get_file_size_bytes(video_dict.get('file_path', ''))
    return video_dict


def _thumb_path_for(file_path):
    """从视频路径计算缩略图路径（纯路径，不检查存在性）"""
    if not file_path:
        return None
    base, ext = os.path.splitext(file_path)
    return f'{base}_thumb.jpg'


def _generate_thumbnail(video):
    """使用 ffmpeg 提取视频第 1 帧作为缩略图"""
    import subprocess
    try:
        static_dir = current_app.static_folder or os.path.join(current_app.root_path, '..', 'static')
        video_rel = video.file_path.replace('/static/', '').replace('\\', '/')
        video_abs = os.path.join(static_dir, video_rel)
        if not os.path.exists(video_abs):
            return

        thumb_rel = _thumb_path_for(video_rel)
        thumb_abs = os.path.join(static_dir, thumb_rel)

        # 已存在则跳过
        if os.path.exists(thumb_abs):
            return

        # ffmpeg 提取第 1 帧：快速 seek + 1 帧 + 低质量 JPEG
        subprocess.run([
            'ffmpeg', '-y',
            '-ss', '1',           # 跳过开头黑屏，取 1 秒处
            '-i', video_abs,
            '-vframes', '1',
            '-q:v', '5',          # 质量 2-5，越小越好
            '-vf', 'scale=480:-2', # 缩略图宽度 480px
            thumb_abs
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except Exception:
        pass  # 缩略图生成失败不影响主流程


def _try_delete_file(file_path):
    """尝试删除文件（不存在则忽略）"""
    if not file_path:
        return
    try:
        static_dir = current_app.static_folder or os.path.join(current_app.root_path, '..', 'static')
        abs_path = os.path.join(static_dir, file_path.replace('/static/', '').replace('\\', '/'))
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception:
        pass


def _renumber_videos():
    """重新整理视频序号"""
    videos = PromoVideo.query.order_by(PromoVideo.sort_order.asc()).all()
    for i, v in enumerate(videos, 1):
        v.sort_order = i
    db.session.commit()
