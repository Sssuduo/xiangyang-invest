"""招商业务模型：项目 / 线索 / 诉求 / 动态 / 台账 / 研判"""
import json
from datetime import datetime
from extensions import db


class InvestmentProject(db.Model):
    """招商对接项目"""
    __tablename__ = 'investment_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)
    project_name = db.Column(db.String(255), nullable=False)
    invest_enterprise = db.Column(db.String(255), nullable=False)
    enterprise_info = db.Column(db.Text, nullable=False)
    project_content = db.Column(db.Text, nullable=False)
    invest_amount = db.Column(db.Numeric(15, 2), nullable=False)  # 万元

    follow_status_code = db.Column(db.String(32), nullable=False)
    meeting_status_code = db.Column(db.String(32), nullable=False, default='not_meeting')
    recommend_unit_code = db.Column(db.String(32), default='')
    responsible_unit_code = db.Column(db.String(32), nullable=True, default='')
    project_type_code = db.Column(db.String(32), nullable=False)

    person_in_charge = db.Column(db.String(64), default='')
    person_in_charge_phone = db.Column(db.String(32), default='')
    project_doc = db.Column(db.Text, default='')
    investment_plan = db.Column(db.Text, default='')
    conclusion = db.Column(db.Text, default='')
    tags = db.Column(db.Text, default='[]')
    team_leader_ids = db.Column(db.Text, default='[]')  # JSON 数组
    first_contact_date = db.Column(db.Date)

    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    demands = db.relationship('EnterpriseDemand', backref='project', lazy='dynamic',
                              order_by='EnterpriseDemand.sort_order')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'project_name': self.project_name,
            'invest_enterprise': self.invest_enterprise,
            'enterprise_info': self.enterprise_info or '',
            'project_content': self.project_content or '',
            'invest_amount': float(self.invest_amount) if self.invest_amount else 0,
            'follow_status_code': self.follow_status_code,
            'meeting_status_code': self.meeting_status_code,
            'recommend_unit_code': self.recommend_unit_code or '',
            'responsible_unit_code': self.responsible_unit_code,
            'project_type_code': self.project_type_code,
            'person_in_charge': self.person_in_charge or '',
            'person_in_charge_phone': self.person_in_charge_phone or '',
            'project_doc': self.project_doc or '',
            'investment_plan': self.investment_plan or '',
            'conclusion': self.conclusion or '',
            'tags': json.loads(self.tags) if self.tags else [],
            'team_leader_ids': json.loads(self.team_leader_ids) if self.team_leader_ids else [],
            'first_contact_date': self.first_contact_date.isoformat() if self.first_contact_date else None,
            'is_deleted': self.is_deleted,
            'demands': [d.to_dict() for d in self.demands.all()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class InvestmentLead(db.Model):
    """招商线索研判"""
    __tablename__ = 'investment_leads'

    # === 与 InvestmentProject 字段完全一致 ===
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)
    project_name = db.Column(db.String(255), nullable=False)
    invest_enterprise = db.Column(db.String(255), nullable=False)
    enterprise_info = db.Column(db.Text, nullable=False)
    project_content = db.Column(db.Text, nullable=False)
    invest_amount = db.Column(db.Numeric(15, 2), nullable=False)
    follow_status_code = db.Column(db.String(32), nullable=False)
    meeting_status_code = db.Column(db.String(32), nullable=False, default='not_meeting')
    recommend_unit_code = db.Column(db.String(32), default='')
    responsible_unit_code = db.Column(db.String(32), nullable=True, default='')
    project_type_code = db.Column(db.String(32), nullable=False)
    person_in_charge = db.Column(db.String(64), default='')
    person_in_charge_phone = db.Column(db.String(32), default='')
    project_doc = db.Column(db.Text, default='')
    investment_plan = db.Column(db.Text, default='')
    conclusion = db.Column(db.Text, default='')
    tags = db.Column(db.Text, default='[]')
    team_leader_ids = db.Column(db.Text, default='[]')
    first_contact_date = db.Column(db.Date)

    # === 研判专用字段 ===
    ai_assessment_result = db.Column(db.Text, default='')
    ai_assessment_at = db.Column(db.DateTime)
    ai_assessment_status = db.Column(db.String(32), default='pending')  # pending / running / completed / failed
    ai_model_id = db.Column(db.Integer, db.ForeignKey('llm_models.id'), nullable=True)
    assessment_prompt_used = db.Column(db.Text, default='')
    converted_project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=True)

    # === 生命周期 ===
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    converted_project = db.relationship('InvestmentProject', foreign_keys=[converted_project_id])

    def to_dict(self):
        return {
            'id': self.id, 'order_no': self.order_no,
            'project_name': self.project_name, 'invest_enterprise': self.invest_enterprise,
            'enterprise_info': self.enterprise_info or '', 'project_content': self.project_content or '',
            'invest_amount': float(self.invest_amount) if self.invest_amount else 0,
            'follow_status_code': self.follow_status_code,
            'meeting_status_code': self.meeting_status_code,
            'recommend_unit_code': self.recommend_unit_code or '',
            'responsible_unit_code': self.responsible_unit_code,
            'project_type_code': self.project_type_code,
            'person_in_charge': self.person_in_charge or '',
            'person_in_charge_phone': self.person_in_charge_phone or '',
            'project_doc': self.project_doc or '', 'investment_plan': self.investment_plan or '',
            'conclusion': self.conclusion or '',
            'tags': json.loads(self.tags) if self.tags else [],
            'team_leader_ids': json.loads(self.team_leader_ids) if self.team_leader_ids else [],
            'first_contact_date': self.first_contact_date.isoformat() if self.first_contact_date else None,
            'ai_assessment_result': self.ai_assessment_result or '',
            'ai_assessment_at': self.ai_assessment_at.isoformat() if self.ai_assessment_at else None,
            'ai_assessment_status': self.ai_assessment_status or 'pending',
            'ai_model_id': self.ai_model_id,
            'converted_project_id': self.converted_project_id,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LeadAssessmentSession(db.Model):
    """AI 研判会话"""
    __tablename__ = 'lead_assessment_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('investment_leads.id'), nullable=False, index=True)
    model_id = db.Column(db.Integer, db.ForeignKey('llm_models.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False, default='AI 研判')
    knowledge_context = db.Column(db.Text, default='')  # 研判时检索的知识库上下文（用于反馈阶段复用）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = db.relationship('InvestmentLead', foreign_keys=[lead_id], backref='assessment_sessions')
    model = db.relationship('LLMModel', foreign_keys=[model_id])

    def to_dict(self):
        msg_count = LeadAssessmentMessage.query.filter_by(session_id=self.id).count()
        model_name = self.model.name if self.model else ''
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'model_id': self.model_id,
            'model_name': model_name,
            'title': self.title,
            'message_count': msg_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LeadAssessmentMessage(db.Model):
    """AI 研判会话消息"""
    __tablename__ = 'lead_assessment_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('lead_assessment_sessions.id'), nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False, default='user')  # user / assistant / system
    content = db.Column(db.Text, default='')
    file_path = db.Column(db.String(512), default='')
    file_name = db.Column(db.String(255), default='')
    html_file_path = db.Column(db.String(512), default='')
    html_file_name = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    session = db.relationship('LeadAssessmentSession', foreign_keys=[session_id], backref='messages')

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content or '',
            'file_url': f'/api/admin/lead/assessment-sessions/{self.session_id}/messages/{self.id}/download' if self.file_path else '',
            'file_name': self.file_name or '',
            'html_url': f'/api/admin/lead/assessment-sessions/{self.session_id}/messages/{self.id}/html' if self.html_file_path else '',
            'html_file_name': self.html_file_name or '',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EnterpriseDemand(db.Model):
    """企业诉求子表"""
    __tablename__ = 'enterprise_demands'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('investment_leads.id'), nullable=True)
    demand_type_code = db.Column(db.String(255), default='')
    demand_content = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text, default='')
    unit_code = db.Column(db.String(32), default='')
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending/processing/resolved
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'lead_id': self.lead_id,
            'demand_type_code': self.demand_type_code or '',
            'demand_content': self.demand_content,
            'resolution': self.resolution or '',
            'unit_code': self.unit_code or '',
            'status': self.status,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class InvestmentActivity(db.Model):
    """招商动态"""
    __tablename__ = 'investment_activities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=True)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')
    tags = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship('InvestmentProject', backref=db.backref('activities', lazy='dynamic'))

    # 多对多关联 EnterpriseDemand（通过 activity_demand_link 表）
    linked_demands = db.relationship(
        'EnterpriseDemand',
        secondary='activity_demand_link',
        lazy='dynamic',
        backref=db.backref('linked_activities', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'project_name': self.project.project_name if self.project else '',
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'content': self.content,
            'files': json.loads(self.files) if self.files else [],
            'tags': json.loads(self.tags) if self.tags else [],
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ActivityDemandLink(db.Model):
    """招商动态 ↔ 企业诉求 多对多关联"""
    __tablename__ = 'activity_demand_link'
    __table_args__ = (
        db.UniqueConstraint('activity_id', 'demand_id', name='uq_activity_demand'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('investment_activities.id', ondelete='CASCADE'), nullable=False)
    demand_id = db.Column(db.Integer, db.ForeignKey('enterprise_demands.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLedger(db.Model):
    """活动台账（未明确项目的活动记录，后续可关联到招商项目）"""
    __tablename__ = 'activity_ledger'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=True)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')
    tags = db.Column(db.Text, default='[]')
    linked_project_id = db.Column(db.Integer, db.ForeignKey('investment_projects.id'), nullable=True)
    linked_activity_id = db.Column(db.Integer, db.ForeignKey('investment_activities.id'), nullable=True)
    # 录音文件相关字段
    audio_file = db.Column(db.Text, nullable=True)       # 原始录音文件路径（可在线播放）
    audio_archive = db.Column(db.Text, nullable=True)     # 夜间压缩包路径（.zip，可下载，不可在线播放）
    audio_archive_size = db.Column(db.Integer, nullable=True) # 压缩包大小（字节）
    audio_transcript = db.Column(db.Text, nullable=True)  # 语音转文字结果
    audio_summary = db.Column(db.Text, nullable=True)     # 文字内容总结
    audio_status = db.Column(db.String(20), default=None) # pending/processing/completed/failed
    audio_duration = db.Column(db.Float, nullable=True)   # 录音时长(秒)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    linked_project = db.relationship('InvestmentProject', foreign_keys=[linked_project_id])
    linked_activity = db.relationship('InvestmentActivity', foreign_keys=[linked_activity_id])

    def to_dict(self):
        result = {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'content': self.content,
            'files': json.loads(self.files) if self.files else [],
            'tags': json.loads(self.tags) if self.tags else [],
            'linked_project_id': self.linked_project_id,
            'linked_project_name': self.linked_project.project_name if self.linked_project else '',
            'linked_activity_id': self.linked_activity_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
        # 录音相关字段（可选返回）
        if self.audio_file:
            result['audio_file'] = self.audio_file
            result['audio_transcript'] = self.audio_transcript
            result['audio_summary'] = self.audio_summary
            result['audio_status'] = self.audio_status
            result['audio_duration'] = self.audio_duration
        return result

    def to_detail_dict(self):
        """完整详情（含录音转写和总结）"""
        d = self.to_dict()
        d['audio_file'] = self.audio_file
        d['audio_archive'] = self.audio_archive
        d['audio_archive_size'] = self.audio_archive_size
        d['audio_transcript'] = self.audio_transcript
        d['audio_summary'] = self.audio_summary
        d['audio_status'] = self.audio_status
        d['audio_duration'] = self.audio_duration
        return d
