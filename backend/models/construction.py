"""在建项目模型：项目 / 工作进展 / 存在问题 / 工作路径图"""
import json
from datetime import datetime
from extensions import db


class ConstructionProject(db.Model):
    """在建项目"""
    __tablename__ = 'construction_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)
    project_name = db.Column(db.String(255), nullable=False)
    project_type_code = db.Column(db.String(32), nullable=False)
    dispatch_status_code = db.Column(db.String(32), nullable=False, default='dispatching')
    construction_content = db.Column(db.Text, default='')
    construction_location = db.Column(db.String(255), default='')
    total_investment = db.Column(db.Float, default=0.0)   # 总投资（亿元）
    start_date = db.Column(db.String(10), default='')    # 年-月-日 格式
    end_date = db.Column(db.String(10), default='')      # 年-月-日 格式
    funding_source = db.Column(db.String(255), default='')
    wuhua_platform = db.Column(db.String(8), default='')  # 是 / 否
    construction_unit = db.Column(db.String(255), default='')
    responsible_unit_code = db.Column(db.String(32), default='')
    responsible_person = db.Column(db.String(64), default='')
    responsible_person_phone = db.Column(db.String(32), default='')
    team_leader_ids = db.Column(db.Text, default='[]')    # JSON 数组
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    work_progresses = db.relationship('WorkProgress', backref='project', lazy='dynamic',
                                       order_by='WorkProgress.start_date.desc()')
    issues = db.relationship('ProjectIssue', backref='project', lazy='dynamic',
                              order_by='ProjectIssue.created_at.desc()')
    work_roadmap_items = db.relationship('WorkRoadmapItem', backref='project', lazy='dynamic',
                                          order_by='WorkRoadmapItem.sort_order.asc()')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'project_name': self.project_name,
            'project_type_code': self.project_type_code,
            'dispatch_status_code': self.dispatch_status_code,
            'construction_content': self.construction_content or '',
            'construction_location': self.construction_location or '',
            'total_investment': self.total_investment or 0.0,
            'start_date': self.start_date or '',
            'end_date': self.end_date or '',
            'funding_source': self.funding_source or '',
            'wuhua_platform': self.wuhua_platform or '',
            'work_roadmap_items': [wri.to_dict() for wri in self.work_roadmap_items.all()],
            'construction_unit': self.construction_unit or '',
            'responsible_unit_code': self.responsible_unit_code or '',
            'responsible_person': self.responsible_person or '',
            'responsible_person_phone': self.responsible_person_phone or '',
            'team_leader_ids': json.loads(self.team_leader_ids) if self.team_leader_ids else [],
            'is_deleted': self.is_deleted,
            'work_progresses': [wp.to_dict() for wp in self.work_progresses.all()],
            'issues': [iss.to_dict() for iss in self.issues.all()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkProgress(db.Model):
    """工作进展"""
    __tablename__ = 'work_progress'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')  # JSON array of file URLs
    import_user_id = db.Column(db.Integer, nullable=True)
    import_user_name = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        _files = []
        try:
            _files = json.loads(self.files or '[]')
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            'id': self.id,
            'project_id': self.project_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'content': self.content,
            'files': _files,
            'import_user_id': self.import_user_id,
            'import_user_name': self.import_user_name or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectIssue(db.Model):
    """存在问题"""
    __tablename__ = 'project_issues'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    issue_type_code = db.Column(db.String(32), default='')
    issue_description = db.Column(db.Text, default='')
    resolution_status_code = db.Column(db.String(32), nullable=False, default='pending')
    resolution_note = db.Column(db.Text, default='')
    main_department_code = db.Column(db.String(32), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'issue_type_code': self.issue_type_code or '',
            'issue_description': self.issue_description or '',
            'resolution_status_code': self.resolution_status_code,
            'resolution_note': self.resolution_note or '',
            'main_department_code': self.main_department_code or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WorkRoadmapItem(db.Model):
    """工作路径图子项"""
    __tablename__ = 'work_roadmap_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('construction_projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    content = db.Column(db.Text, nullable=False)
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='pending')
    is_delayed = db.Column(db.Boolean, nullable=False, default=False)
    delay_reason = db.Column(db.Text, default='')
    cancel_reason = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'sort_order': self.sort_order,
            'content': self.content,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'status': self.status,
            'is_delayed': self.is_delayed,
            'delay_reason': self.delay_reason or '',
            'cancel_reason': self.cancel_reason or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
