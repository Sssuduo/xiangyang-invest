import json
from flask import request, jsonify
from models import KnowledgeEntry
from extensions import db
from routes import admin_knowledge_bp
from routes.business_auth import dual_login_required, visitor_block

CATEGORY_MAP = {
    'industry_policy': '产业政策', 'park_info': '园区信息', 'supporting': '配套能力',
    'land_cost': '土地成本', 'case_study': '招商案例', 'demand_pattern': '企业诉求',
    'market_data': '市场数据', 'competitor': '周边竞争'
}

CATEGORY_OPTIONS = [
    {'code': k, 'name': v} for k, v in CATEGORY_MAP.items()
]


@admin_knowledge_bp.route('/knowledge/categories', methods=['GET'])
@dual_login_required
def list_categories():
    """获取分类列表及各分类条目数"""
    categories = []
    for code, name in CATEGORY_MAP.items():
        count = KnowledgeEntry.query.filter_by(category=code, is_active=True).count()
        categories.append({'code': code, 'name': name, 'count': count})
    # 额外统计停用条目
    inactive_count = KnowledgeEntry.query.filter_by(is_active=False).count()
    if inactive_count > 0:
        categories.append({'code': '_inactive', 'name': '已停用', 'count': inactive_count})
    return jsonify({'code': 0, 'data': categories})


@admin_knowledge_bp.route('/knowledge/entries', methods=['GET'])
@dual_login_required
def list_entries():
    """列表（搜索 + 分类筛选 + 分页）"""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    include_inactive = request.args.get('include_inactive', '0').strip() == '1'
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 15))

    q = KnowledgeEntry.query

    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            KnowledgeEntry.title.like(like),
            KnowledgeEntry.content.like(like),
            KnowledgeEntry.tags.like(like)
        ))

    if category:
        q = q.filter_by(category=category)

    if not include_inactive:
        q = q.filter_by(is_active=True)

    total = q.count()
    entries = q.order_by(KnowledgeEntry.sort_order.asc(), KnowledgeEntry.updated_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        'code': 0,
        'data': {
            'items': [e.to_dict() for e in entries],
            'total': total,
            'page': page,
            'page_size': page_size
        }
    })


@admin_knowledge_bp.route('/knowledge/entries/<int:entry_id>', methods=['GET'])
@dual_login_required
def get_entry(entry_id):
    """获取详情"""
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    return jsonify({'code': 0, 'data': entry.to_dict()})


@admin_knowledge_bp.route('/knowledge/entries', methods=['POST'])
@dual_login_required
@visitor_block
def create_entry():
    """创建知识条目"""
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    if not data.get('title', '').strip():
        return jsonify({'code': 1, 'message': '标题不能为空'}), 400
    if not data.get('content', '').strip():
        return jsonify({'code': 1, 'message': '内容不能为空'}), 400
    cat = data.get('category', '')
    if cat not in CATEGORY_MAP:
        return jsonify({'code': 1, 'message': f'无效的分类: {cat}'}), 400

    entry = KnowledgeEntry(
        title=data['title'].strip(),
        content=data['content'].strip(),
        category=cat,
        tags=json.dumps(data.get('tags', []), ensure_ascii=False),
        source=data.get('source', ''),
        attach_files=json.dumps(data.get('attach_files', []), ensure_ascii=False),
        is_active=data.get('is_active', True),
        sort_order=data.get('sort_order', 0)
    )
    db.session.add(entry)
    db.session.commit()

    # 异步向量化新条目
    _embed_entry_async(entry.id)

    return jsonify({'code': 0, 'data': entry.to_dict(), 'message': '知识条目创建成功'})


@admin_knowledge_bp.route('/knowledge/entries/<int:entry_id>', methods=['PUT'])
@dual_login_required
@visitor_block
def update_entry(entry_id):
    """更新知识条目"""
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    data = request.get_json()
    if not data:
        return jsonify({'code': 1, 'message': '请求数据不能为空'}), 400

    if 'title' in data:
        if not data['title'].strip():
            return jsonify({'code': 1, 'message': '标题不能为空'}), 400
        entry.title = data['title'].strip()
    if 'content' in data:
        if not data['content'].strip():
            return jsonify({'code': 1, 'message': '内容不能为空'}), 400
        entry.content = data['content'].strip()
    if 'category' in data:
        cat = data['category']
        if cat not in CATEGORY_MAP:
            return jsonify({'code': 1, 'message': f'无效的分类: {cat}'}), 400
        entry.category = cat
    if 'tags' in data:
        entry.tags = json.dumps(data['tags'], ensure_ascii=False)
    if 'source' in data:
        entry.source = data['source']
    if 'attach_files' in data:
        entry.attach_files = json.dumps(data['attach_files'], ensure_ascii=False)
    if 'is_active' in data:
        entry.is_active = data['is_active']
    if 'sort_order' in data:
        entry.sort_order = data['sort_order']

    db.session.commit()

    # 内容变更后重新向量化
    _embed_entry_async(entry_id)

    return jsonify({'code': 0, 'data': entry.to_dict(), 'message': '知识条目更新成功'})


@admin_knowledge_bp.route('/knowledge/entries/<int:entry_id>', methods=['DELETE'])
@dual_login_required
@visitor_block
def delete_entry(entry_id):
    """删除知识条目"""
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'code': 0, 'message': '知识条目已删除'})


@admin_knowledge_bp.route('/knowledge/entries/<int:entry_id>/embed', methods=['POST'])
@dual_login_required
@visitor_block
def embed_entry(entry_id):
    """手动触发单条知识条目的向量化"""
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    try:
        _embed_entry_sync(entry)
        db.session.commit()
        return jsonify({'code': 0, 'data': entry.to_dict(), 'message': '向量化成功'})
    except Exception as e:
        return jsonify({'code': 1, 'message': f'向量化失败: {str(e)}'}), 500


@admin_knowledge_bp.route('/knowledge/entries/batch-embed', methods=['POST'])
@dual_login_required
@visitor_block
def batch_embed_entries():
    """批量向量化所有未向量化的知识条目"""
    data = request.get_json() or {}
    ids = data.get('ids')
    if ids:
        entries = KnowledgeEntry.query.filter(KnowledgeEntry.id.in_(ids)).all()
    else:
        entries = KnowledgeEntry.query.filter(
            db.or_(KnowledgeEntry.embedding.is_(None), KnowledgeEntry.embedding == '')
        ).all()

    if not entries:
        return jsonify({'code': 1, 'message': '没有需要向量化的条目'}), 400

    count = _batch_embed_sync(entries)
    db.session.commit()
    return jsonify({'code': 0, 'data': {'count': count}, 'message': f'已向量化 {count} 条'})


# ---- embedding helpers ----

def _embed_entry_async(entry_id):
    """在后台线程中异步向量化单条知识条目"""
    import threading
    from flask import current_app
    app = current_app._get_current_object()
    thread = threading.Thread(target=_embed_in_context, args=(app, entry_id), daemon=True)
    thread.start()


def _embed_in_context(app, entry_id):
    """在应用上下文中执行向量化"""
    with app.app_context():
        entry = KnowledgeEntry.query.get(entry_id)
        if not entry:
            return
        try:
            _embed_entry_sync(entry)
            db.session.commit()
        except Exception:
            db.session.rollback()


def _embed_entry_sync(entry):
    """同步向量化单条知识条目"""
    from services.embedding_service import get_embedding
    from models import LLMModel

    model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
    if not model:
        raise ValueError('没有可用的 AI 模型')

    text = _build_entry_text(entry)
    model_config = _build_embedding_config(model)
    vec, model_name = get_embedding(text, model_config)
    entry.embedding = json.dumps(vec)
    entry.embedding_model = model_name or ''


def _batch_embed_sync(entries):
    """同步批量向量化知识条目"""
    from services.embedding_service import batch_embed_entries
    from models import LLMModel

    model = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.sort_order.asc()).first()
    if not model:
        raise ValueError('没有可用的 AI 模型')

    return batch_embed_entries(entries, _build_embedding_config(model))


def _build_embedding_config(model):
    """从 LLMModel 构建 embedding 服务所需的配置字典"""
    return {
        'api_base_url': model.api_base_url,
        'api_key': model.api_key,
        'model_name': model.model_name,
        'embedding_api_url': model.embedding_api_url or '',
        'embedding_api_key': model.embedding_api_key or '',
        'embedding_model_name': model.embedding_model_name or '',
    }


def _build_entry_text(entry):
    """构建用于向量化的文本"""
    parts = [entry.title]
    if entry.tags:
        try:
            tags = json.loads(entry.tags)
            if tags:
                parts.extend(tags)
        except Exception:
            pass
    parts.append(entry.content or '')
    return ' '.join(parts)


# ============================================================
# 知识沉淀草稿管理
# ============================================================

@admin_knowledge_bp.route('/knowledge/drafts', methods=['GET'])
@dual_login_required
def list_drafts():
    """获取知识草稿列表"""
    from models import KnowledgeDraft
    status = request.args.get('status', '').strip()
    q = KnowledgeDraft.query
    if status:
        q = q.filter_by(status=status)
    drafts = q.order_by(KnowledgeDraft.created_at.desc()).limit(100).all()
    return jsonify({'code': 0, 'data': [d.to_dict() for d in drafts]})


@admin_knowledge_bp.route('/knowledge/drafts/<int:draft_id>/approve', methods=['POST'])
@dual_login_required
@visitor_block
def approve_draft(draft_id):
    """批准草稿 → 创建/更新 KnowledgeEntry，生成向量"""
    from models import KnowledgeDraft
    draft = KnowledgeDraft.query.get_or_404(draft_id)
    if draft.status != 'draft':
        return jsonify({'code': 1, 'message': '该草稿已被处理'}), 400

    data = request.get_json() or {}
    # 支持修改后批准
    title = data.get('title', draft.title).strip()
    content = data.get('content', draft.content).strip()
    category = data.get('category', draft.category)
    if category not in CATEGORY_MAP:
        return jsonify({'code': 1, 'message': f'无效的分类: {category}'}), 400
    if not title or not content:
        return jsonify({'code': 1, 'message': '标题和内容不能为空'}), 400

    # 如果有关联的 target_entry_id，更新已有条目；否则创建新条目
    if draft.target_entry_id:
        entry = KnowledgeEntry.query.get(draft.target_entry_id)
        if entry:
            entry.title = title
            entry.content = content
            entry.category = category
            if data.get('tags'):
                entry.tags = json.dumps(data['tags'], ensure_ascii=False)
        else:
            draft.target_entry_id = None

    if not draft.target_entry_id or not KnowledgeEntry.query.get(draft.target_entry_id):
        # 安全获取 tags
        if isinstance(draft.tags, list):
            tag_list = draft.tags
        elif draft.tags:
            try:
                tag_list = json.loads(draft.tags) if isinstance(draft.tags, str) else list(draft.tags)
            except (json.JSONDecodeError, TypeError):
                tag_list = []
        else:
            tag_list = []
        tags_to_use = data.get('tags', tag_list)

        entry = KnowledgeEntry(
            title=title,
            content=content,
            category=category,
            tags=json.dumps(tags_to_use, ensure_ascii=False),
            source=draft.source or 'AI研判自动提炼',
            is_active=True,
            sort_order=99
        )
        db.session.add(entry)
        db.session.flush()

    # 异步向量化
    _embed_entry_async(entry.id)

    # 更新草稿状态
    draft.status = 'approved'
    draft.target_entry_id = entry.id
    draft.reviewed_at = datetime.utcnow()
    draft.reviewed_by = getattr(request, 'current_user_name', '') or 'admin'
    db.session.commit()

    return jsonify({'code': 0, 'data': {'entry_id': entry.id}, 'message': '草稿已批准，知识条目已生成'})


@admin_knowledge_bp.route('/knowledge/drafts/<int:draft_id>/reject', methods=['POST'])
@dual_login_required
@visitor_block
def reject_draft(draft_id):
    """拒绝草稿"""
    from models import KnowledgeDraft
    draft = KnowledgeDraft.query.get_or_404(draft_id)
    if draft.status != 'draft':
        return jsonify({'code': 1, 'message': '该草稿已被处理'}), 400

    data = request.get_json() or {}
    draft.status = 'rejected'
    draft.review_note = data.get('note', '')
    draft.reviewed_at = datetime.utcnow()
    draft.reviewed_by = getattr(request, 'current_user_name', '') or 'admin'
    db.session.commit()

    return jsonify({'code': 0, 'message': '草稿已拒绝'})


# 需要 datetime 导入
from datetime import datetime
