"""AI相关模型：大模型配置 / 快捷提示词 / 知识库"""
import json
from datetime import datetime
from extensions import db


class LLMModel(db.Model):
    """大模型配置"""
    __tablename__ = 'llm_models'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    provider = db.Column(db.String(64), nullable=False, default='custom')
    api_base_url = db.Column(db.String(512), nullable=False, default='')
    api_key = db.Column(db.String(512), nullable=False, default='')
    model_name = db.Column(db.String(128), nullable=False, default='')
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=4096)
    system_prompt = db.Column(db.Text, default='')

    # 独立 Embedding 配置
    embedding_api_url = db.Column(db.String(512), default='')
    embedding_api_key = db.Column(db.String(512), default='')
    embedding_model_name = db.Column(db.String(128), default='')

    # 关联搜索模型（GLM-4-Flash 等支持 Web Search 的模型），用于联网搜索阶段
    search_model_id = db.Column(db.Integer, db.ForeignKey('llm_models.id'), nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'api_base_url': self.api_base_url,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt or '',
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'embedding_api_url': self.embedding_api_url or '',
            'embedding_model_name': self.embedding_model_name or '',
            'search_model_id': self.search_model_id,
            # 不返回 api_key
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def to_admin_dict(self):
        """管理员视图（含 api_key 和 embedding_api_key）"""
        d = self.to_dict()
        d['api_key'] = self.api_key
        d['embedding_api_key'] = self.embedding_api_key or ''
        d['search_model_id'] = self.search_model_id
        return d

    def get_embedding_config(self):
        """获取 embedding 配置：优先独立配置，否则复用 chat 配置"""
        url = self.embedding_api_url or f"{self.api_base_url.rstrip('/')}/embeddings"
        key = self.embedding_api_key or self.api_key
        model = self.embedding_model_name or self.model_name
        return {
            'url': url,
            'key': key,
            'model': model
        }


class QuickPrompt(db.Model):
    """快捷提示词"""
    __tablename__ = 'quick_prompts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    button_text = db.Column(db.String(128), nullable=False)
    prompt_template = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(512), default='')
    category = db.Column(db.String(64), default='general')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'button_text': self.button_text,
            'prompt_template': self.prompt_template,
            'description': self.description or '',
            'category': self.category or 'general',
            'is_active': self.is_active,
            'sort_order': self.sort_order
        }


class KnowledgeEntryHistory(db.Model):
    """知识条目历史版本"""
    __tablename__ = 'knowledge_entry_histories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('knowledge_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False)
    tags = db.Column(db.Text, default='[]')
    source = db.Column(db.String(255), default='')
    attach_files = db.Column(db.Text, default='[]')
    version = db.Column(db.Integer, default=1)
    changed_by = db.Column(db.String(128), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'tags': json.loads(self.tags) if self.tags else [],
            'source': self.source or '',
            'attach_files': json.loads(self.attach_files) if self.attach_files else [],
            'version': self.version,
            'changed_by': self.changed_by or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeEntryChangeLog(db.Model):
    """知识条目变更审计日志"""
    __tablename__ = 'knowledge_entry_change_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('knowledge_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    action = db.Column(db.String(16), nullable=False)  # create / update / delete / toggle
    changed_by = db.Column(db.String(128), default='')
    changed_fields = db.Column(db.Text, default='')
    old_values = db.Column(db.Text, default='')
    new_values = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'action': self.action,
            'changed_by': self.changed_by or '',
            'changed_fields': json.loads(self.changed_fields) if self.changed_fields else [],
            'old_values': json.loads(self.old_values) if self.old_values else {},
            'new_values': json.loads(self.new_values) if self.new_values else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeEntry(db.Model):
    """本地招商知识库"""
    __tablename__ = 'knowledge_entries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False)
    tags = db.Column(db.Text, default='[]')
    source = db.Column(db.String(255), default='')
    attach_files = db.Column(db.Text, default='[]')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # 向量化字段
    embedding = db.Column(db.Text, default=None)
    embedding_model = db.Column(db.String(64), default='')
    search_count = db.Column(db.Integer, default=0)
    last_used_at = db.Column(db.DateTime, nullable=True)

    # 审计追溯
    created_by = db.Column(db.String(128), default='')
    updated_by = db.Column(db.String(128), default='')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'content': self.content,
            'category': self.category,
            'tags': json.loads(self.tags) if self.tags else [],
            'source': self.source or '',
            'attach_files': json.loads(self.attach_files) if self.attach_files else [],
            'is_active': self.is_active, 'sort_order': self.sort_order,
            'has_embedding': bool(self.embedding),
            'embedding_model': self.embedding_model or '',
            'search_count': self.search_count or 0,
            'created_by': self.created_by or '',
            'updated_by': self.updated_by or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class KnowledgeDraft(db.Model):
    """知识草稿（AI研判自动提炼，待人工审核）"""
    __tablename__ = 'knowledge_drafts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False)
    tags = db.Column(db.Text, default='[]')
    source = db.Column(db.String(255), default='AI研判自动提炼')
    source_session_id = db.Column(db.Integer, nullable=True)
    source_lead_id = db.Column(db.Integer, nullable=True)
    target_entry_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(32), default='draft')  # draft / approved / rejected
    reviewed_by = db.Column(db.String(64), default='')
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'tags': json.loads(self.tags) if self.tags else [],
            'source': self.source or '',
            'source_session_id': self.source_session_id,
            'source_lead_id': self.source_lead_id,
            'target_entry_id': self.target_entry_id,
            'status': self.status,
            'reviewed_by': self.reviewed_by or '',
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_note': self.review_note or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class KnowledgeUsageStat(db.Model):
    """知识使用统计（每次研判记录一条）"""
    __tablename__ = 'knowledge_usage_stats'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('knowledge_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.Integer, nullable=False, index=True)
    lead_id = db.Column(db.Integer, nullable=False)
    was_used = db.Column(db.Boolean, default=False)
    was_useful = db.Column(db.Boolean, nullable=True)
    relevance_score = db.Column(db.Float, default=0.0)
    accuracy_feedback = db.Column(db.Text, default='')
    needs_update = db.Column(db.Boolean, default=False)
    update_suggestion = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'session_id': self.session_id,
            'lead_id': self.lead_id,
            'was_used': self.was_used,
            'was_useful': self.was_useful,
            'relevance_score': self.relevance_score,
            'accuracy_feedback': self.accuracy_feedback or '',
            'needs_update': self.needs_update,
            'update_suggestion': self.update_suggestion or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
