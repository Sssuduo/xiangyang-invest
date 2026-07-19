"""消息提醒站:规则 / 用户消息 / 触发日志"""
import json
from datetime import datetime
from extensions import db


class MessageRule(db.Model):
    """消息提醒规则配置"""
    __tablename__ = 'message_rules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)  # 规则名称(如"新项目超15天未研判")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # 触发条件(结构化配置)
    condition_type = db.Column(db.String(32), nullable=False)
    # 枚举: 'project_no_meeting'(招商项目超期未研判) |
    #        'project_no_followup'(招商项目超期无动态) |
    #        'construction_delay'(在建项目超期) — 后续扩展
    threshold_days = db.Column(db.Integer, nullable=False)  # 阈值天数(如 15)

    # 消息对象
    target_type = db.Column(db.String(32), nullable=False, default='all')
    # 枚举: 'all'(全部用户) | 'specific_users'(指定用户) | 'project_leaders'(项目负责人)
    target_user_ids = db.Column(db.Text, default='[]')  # JSON 数组,specific_users 时

    # 消息体模板(变量占位符用 {var})
    title_template = db.Column(db.String(255), default='新消息提醒')
    body_template = db.Column(db.Text, nullable=False)
    # 例: "{username}您好,[{project_name}]距离首次对接[{first_contact_date}]已超过{threshold_days}天,需要进行研判"
    # 可用变量: {username} {project_name} {first_contact_date} {threshold_days} {project_id}

    # 跳转链接
    link_route = db.Column(db.String(128), default='/investment')
    link_query_template = db.Column(db.Text, default='{"focusProjectId": {project_id}}')

    # 时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_active': self.is_active,
            'condition_type': self.condition_type,
            'threshold_days': self.threshold_days,
            'target_type': self.target_type,
            'target_user_ids': json.loads(self.target_user_ids) if self.target_user_ids else [],
            'title_template': self.title_template,
            'body_template': self.body_template,
            'link_route': self.link_route,
            'link_query_template': self.link_query_template,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserMessage(db.Model):
    """用户收到的消息"""
    __tablename__ = 'user_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_type = db.Column(db.String(16), nullable=False)  # 'admin' | 'business'

    rule_id = db.Column(db.Integer, db.ForeignKey('message_rules.id'), nullable=True)
    source_type = db.Column(db.String(32))  # 'investment_project' | 'construction_project'
    source_id = db.Column(db.Integer)  # 项目 ID

    title = db.Column(db.String(255))
    body = db.Column(db.Text, nullable=False)  # 渲染后的消息体(含 HTML 链接)
    link_route = db.Column(db.String(128))
    link_query = db.Column(db.Text)  # JSON

    # 状态: pending(待处理) | snoozed(挂起) | done(已处理)
    status = db.Column(db.String(16), default='pending')

    # 时间
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    snoozed_until = db.Column(db.DateTime, nullable=True)
    handled_at = db.Column(db.DateTime, nullable=True)

    # 关系
    rule = db.relationship('MessageRule', backref=db.backref('messages', lazy='dynamic'))

    def to_dict(self):
        link_query_obj = {}
        if self.link_query:
            try:
                link_query_obj = json.loads(self.link_query)
            except Exception:
                pass
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_type': self.user_type,
            'rule_id': self.rule_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'title': self.title,
            'body': self.body,
            'link_route': self.link_route,
            'link_query': link_query_obj,
            'status': self.status,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'snoozed_until': self.snoozed_until.isoformat() if self.snoozed_until else None,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
        }


class MessageRuleLog(db.Model):
    """规则触发日志(防重复触发 + 审计)"""
    __tablename__ = 'message_rule_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('message_rules.id'), nullable=False)
    source_type = db.Column(db.String(32))
    source_id = db.Column(db.Integer)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_count = db.Column(db.Integer, default=0)

    # 关系
    rule = db.relationship('MessageRule', backref=db.backref('logs', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'user_count': self.user_count,
        }
