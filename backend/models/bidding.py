"""揭榜挂帅模型：榜单项目 / 揭榜申请 / 里程碑 / 全周期时间线 / 揭榜方用户 / 技术领域字典"""
import json
from datetime import datetime
from extensions import db


class BiddingCategoryDict(db.Model):
    """技术领域字典"""
    __tablename__ = 'bidding_category_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active,
        }


class BiddingUser(db.Model):
    """揭榜方用户（对外端口注册，内部端可禁用）"""
    __tablename__ = 'bidding_users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    org_name = db.Column(db.String(255), default='')        # 单位/团队名称
    org_type = db.Column(db.String(32), default='')          # 高校/科研院所/企业/团队
    contact_name = db.Column(db.String(64), default='')      # 联系人
    contact_phone = db.Column(db.String(32), default='')
    email = db.Column(db.String(255), default='')            # 回执收件地址
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'org_name': self.org_name or '',
            'org_type': self.org_type or '',
            'contact_name': self.contact_name or '',
            'contact_phone': self.contact_phone or '',
            'email': self.email or '',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BiddingProject(db.Model):
    """揭榜挂帅榜单项目主表 — 一条记录贯穿七步工作法"""
    __tablename__ = 'bidding_projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.Integer, nullable=False, default=0)

    # === 基础信息（需求征集阶段登记） ===
    title = db.Column(db.String(255), nullable=False)          # 榜单/项目名称
    category_code = db.Column(db.String(32), default='')       # 技术领域（字典）
    demander_name = db.Column(db.String(255), default='')      # 发榜企业名称
    demander_contact = db.Column(db.String(64), default='')    # 企业联系人
    demander_phone = db.Column(db.String(32), default='')
    demand_source = db.Column(db.String(32), default='')       # 企业申报/专班征集/部门推荐
    requirement_desc = db.Column(db.Text, default='')          # 技术需求描述（兼容旧数据，新数据用下方三段式）
    requirement_attachment = db.Column(db.Text, default='[]')  # 需求附件 JSON 数组
    expected_budget = db.Column(db.Float, default=0.0)         # 预期投入（万元）
    expected_deadline = db.Column(db.Date, nullable=True)      # 期望解决时限

    # === 企业概况（企业需求申报表） ===
    enterprise_address = db.Column(db.String(255), default='')        # 企业地址
    enterprise_qualifications = db.Column(db.Text, default='[]')      # 资质/荣誉 多选 JSON
    industry_code = db.Column(db.String(64), default='')              # 所属行业
    registered_capital = db.Column(db.String(64), default='')         # 注册资本
    founded_year = db.Column(db.String(16), default='')               # 成立时间
    staff_size = db.Column(db.String(32), default='')                 # 人员规模
    enterprise_nature = db.Column(db.String(32), default='')          # 企业性质（国企/民营/其他）
    main_products = db.Column(db.Text, default='')                    # 主要产品/服务
    last_year_revenue = db.Column(db.String(64), default='')          # 上年度营业收入

    # === 需求描述（结构化：技术难点/指标/研究内容） ===
    tech_difficulties = db.Column(db.Text, default='')       # 主要技术难点
    tech_indicators = db.Column(db.Text, default='')         # 主要技术指标
    research_content = db.Column(db.Text, default='')        # 主要研究内容

    # === 合作意向 ===
    short_term_cooperation = db.Column(db.Text, default='[]')  # 拟短期合作方式 多选 JSON
    long_term_cooperation = db.Column(db.Text, default='[]')   # 拟长期合作方式 多选 JSON
    expert_intent = db.Column(db.String(16), default='no')     # 是否有意向合作专家 yes/no
    expert_names = db.Column(db.Text, default='')              # 意向专家及工作单位

    # === 流程主控 ===
    current_stage = db.Column(db.String(16), nullable=False, default='stage1')
    # stage1..stage7 / rejected(论证驳回) / failed(流标) / cancelled(终止)
    service_leader_ids = db.Column(db.Text, default='[]')      # 服务专班人员（全周期跟踪）

    # === 阶段2 专家论证 ===
    argument_status = db.Column(db.String(16), default='pending')  # pending/passed/rejected
    argument_experts = db.Column(db.Text, default='[]')            # JSON [{name, org, title}]
    argument_opinion = db.Column(db.Text, default='')              # 论证意见
    argument_result = db.Column(db.Text, default='')               # 论证结论
    argument_date = db.Column(db.Date, nullable=True)

    # === 阶段3 发榜公告 ===
    publish_status = db.Column(db.String(16), default='unpublished')  # unpublished/published/expired
    publish_date = db.Column(db.Date, nullable=True)
    deadline_date = db.Column(db.Date, nullable=True)                 # 揭榜截止
    bounty_amount = db.Column(db.Float, default=0.0)                  # 悬赏金额（万元）
    accept_conditions = db.Column(db.Text, default='')                # 揭榜条件

    # === 阶段4 揭榜评审 ===
    bid_status = db.Column(db.String(16), default='collecting')  # collecting/reviewing/selected/failed
    review_result = db.Column(db.Text, default='')               # 评审结论
    selected_bid_id = db.Column(db.Integer, db.ForeignKey('bidding_bids.id'), nullable=True)

    # === 阶段5 任务签订 ===
    task_status = db.Column(db.String(16), default='unsigned')  # unsigned/signed
    task_date = db.Column(db.Date, nullable=True)
    task_amount = db.Column(db.Float, default=0.0)               # 任务经费（万元）
    task_duration = db.Column(db.String(32), default='')         # 任务期限（如"24个月"）
    task_notes = db.Column(db.Text, default='')                  # 任务书备注

    # === 阶段6 过程管理 ===
    process_status = db.Column(db.String(16), default='ongoing')  # ongoing/completed/terminated
    process_notes = db.Column(db.Text, default='')

    # === 阶段7 绩效评价 ===
    eval_status = db.Column(db.String(16), default='unevaluated')  # unevaluated/evaluated
    eval_score = db.Column(db.Integer, nullable=True)              # 0-100
    eval_level = db.Column(db.String(16), default='')              # 优秀/良好/合格/不合格
    eval_report = db.Column(db.Text, default='')                   # 评价报告
    eval_date = db.Column(db.Date, nullable=True)

    # === 生命周期 ===
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系（selected_bid_id 使两表间存在双向 FK，必须显式指定 foreign_keys）
    bids = db.relationship('BiddingBid', backref='project', lazy='dynamic',
                           order_by='BiddingBid.submitted_at.desc()',
                           foreign_keys='BiddingBid.project_id')
    milestones = db.relationship('BiddingMilestone', backref='project', lazy='dynamic',
                                 order_by='BiddingMilestone.sort_order.asc()')
    timeline = db.relationship('BiddingTimeline', backref='project', lazy='dynamic',
                               order_by='BiddingTimeline.created_at.desc()')
    selected_bid = db.relationship('BiddingBid', foreign_keys=[selected_bid_id])

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'title': self.title,
            'category_code': self.category_code or '',
            'demander_name': self.demander_name or '',
            'demander_contact': self.demander_contact or '',
            'demander_phone': self.demander_phone or '',
            'demand_source': self.demand_source or '',
            'requirement_desc': self.requirement_desc or '',
            'requirement_attachment': json.loads(self.requirement_attachment) if self.requirement_attachment else [],
            'expected_budget': self.expected_budget or 0.0,
            'expected_deadline': self.expected_deadline.isoformat() if self.expected_deadline else None,
            # 企业概况（申报表）
            'enterprise_address': self.enterprise_address or '',
            'enterprise_qualifications': json.loads(self.enterprise_qualifications) if self.enterprise_qualifications else [],
            'industry_code': self.industry_code or '',
            'registered_capital': self.registered_capital or '',
            'founded_year': self.founded_year or '',
            'staff_size': self.staff_size or '',
            'enterprise_nature': self.enterprise_nature or '',
            'main_products': self.main_products or '',
            'last_year_revenue': self.last_year_revenue or '',
            # 需求描述（结构化）
            'tech_difficulties': self.tech_difficulties or '',
            'tech_indicators': self.tech_indicators or '',
            'research_content': self.research_content or '',
            # 合作意向
            'short_term_cooperation': json.loads(self.short_term_cooperation) if self.short_term_cooperation else [],
            'long_term_cooperation': json.loads(self.long_term_cooperation) if self.long_term_cooperation else [],
            'expert_intent': self.expert_intent or 'no',
            'expert_names': self.expert_names or '',
            'current_stage': self.current_stage,
            'service_leader_ids': json.loads(self.service_leader_ids) if self.service_leader_ids else [],
            'argument_status': self.argument_status or 'pending',
            'argument_experts': json.loads(self.argument_experts) if self.argument_experts else [],
            'argument_opinion': self.argument_opinion or '',
            'argument_result': self.argument_result or '',
            'argument_date': self.argument_date.isoformat() if self.argument_date else None,
            'publish_status': self.publish_status or 'unpublished',
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'deadline_date': self.deadline_date.isoformat() if self.deadline_date else None,
            'bounty_amount': self.bounty_amount or 0.0,
            'accept_conditions': self.accept_conditions or '',
            'bid_status': self.bid_status or 'collecting',
            'review_result': self.review_result or '',
            'selected_bid_id': self.selected_bid_id,
            'task_status': self.task_status or 'unsigned',
            'task_date': self.task_date.isoformat() if self.task_date else None,
            'task_amount': self.task_amount or 0.0,
            'task_duration': self.task_duration or '',
            'task_notes': self.task_notes or '',
            'process_status': self.process_status or 'ongoing',
            'process_notes': self.process_notes or '',
            'eval_status': self.eval_status or 'unevaluated',
            'eval_score': self.eval_score,
            'eval_level': self.eval_level or '',
            'eval_report': self.eval_report or '',
            'eval_date': self.eval_date.isoformat() if self.eval_date else None,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
        }

    def to_detail_dict(self):
        d = self.to_dict()
        d['bids'] = [b.to_dict() for b in self.bids.all()]
        d['milestones'] = [m.to_dict() for m in self.milestones.all()]
        d['timeline'] = [t.to_dict() for t in self.timeline.all()]
        d['selected_bid'] = self.selected_bid.to_dict() if self.selected_bid else None
        return d


class BiddingBid(db.Model):
    """揭榜申请（user_id 为空 = 内部代录）"""
    __tablename__ = 'bidding_bids'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('bidding_projects.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('bidding_users.id'), nullable=True)  # 外部提交者
    bidder_name = db.Column(db.String(255), default='')    # 揭榜方名称（单位/团队）
    bidder_type = db.Column(db.String(32), default='')     # 高校/科研院所/企业/团队
    team_leader = db.Column(db.String(64), default='')     # 团队负责人
    team_leader_phone = db.Column(db.String(32), default='')
    tech_solution = db.Column(db.Text, default='')         # 技术方案
    team_advantage = db.Column(db.Text, default='')        # 团队优势/业绩
    expected_amount = db.Column(db.Float, default=0.0)     # 揭榜报价（万元）
    status = db.Column(db.String(16), nullable=False, default='submitted')
    # submitted/reviewing/selected/rejected
    score = db.Column(db.Float, nullable=True)             # 评审评分
    score_note = db.Column(db.Text, default='')            # 评审意见
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('BiddingUser', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'is_external': self.user_id is not None,
            'bidder_name': self.bidder_name or '',
            'bidder_type': self.bidder_type or '',
            'team_leader': self.team_leader or '',
            'team_leader_phone': self.team_leader_phone or '',
            'tech_solution': self.tech_solution or '',
            'team_advantage': self.team_advantage or '',
            'expected_amount': self.expected_amount or 0.0,
            'status': self.status,
            'score': self.score,
            'score_note': self.score_note or '',
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if self.submitted_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class BiddingMilestone(db.Model):
    """任务书里程碑（过程管理核查点）"""
    __tablename__ = 'bidding_milestones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('bidding_projects.id'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    content = db.Column(db.String(255), nullable=False)     # 里程碑内容
    planned_date = db.Column(db.Date, nullable=True)        # 计划完成时间
    actual_date = db.Column(db.Date, nullable=True)         # 实际完成时间
    status = db.Column(db.String(16), nullable=False, default='pending')
    # pending/in_progress/done/delayed/cancelled
    result_note = db.Column(db.Text, default='')            # 完成情况说明
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
            'result_note': self.result_note or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }


class BiddingTimeline(db.Model):
    """全周期服务跟踪时间线（贯穿七步的档案）"""
    __tablename__ = 'bidding_timeline'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('bidding_projects.id'), nullable=False, index=True)
    stage = db.Column(db.String(16), default='')            # 所属阶段 stage1..stage7
    record_type = db.Column(db.String(16), default='service')
    # system(自动流转) / service(服务记录) / notice(通知)
    content = db.Column(db.Text, nullable=False)
    files = db.Column(db.Text, default='[]')                # 附件 JSON
    record_by = db.Column(db.String(128), default='')       # 记录人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'stage': self.stage,
            'record_type': self.record_type,
            'content': self.content,
            'files': json.loads(self.files) if self.files else [],
            'record_by': self.record_by or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
        }
