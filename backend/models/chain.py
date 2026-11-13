"""产业链招商 —— 数据模型

农高区（襄州片区）企业产业链图谱分析：
- chain_nodes       产业链环节本体（上游/中游/下游/平台支撑）
- chain_enterprises 企业主数据（本次分析范围：襄州片区企业统计表 62 家）
- chain_gaps        共性配套缺口（含优先级五因子得分）
- chain_targets     目标企业候选（联网采集，保留来源链接）
- chain_advice      招商建议（文字材料）
"""
from datetime import datetime

from extensions import db


class ChainNode(db.Model):
    """产业链环节本体"""
    __tablename__ = 'chain_nodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(128), nullable=False)
    layer = db.Column(db.String(32), nullable=False, default='上游')  # 上游/中游/下游/平台
    sort_order = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'layer': self.layer,
            'sort_order': self.sort_order,
            'description': self.description or '',
        }


class ChainEnterprise(db.Model):
    """企业主数据（归类到产业链环节）"""
    __tablename__ = 'chain_enterprises'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    seq = db.Column(db.Integer, default=0)                # 原表序号（49 起原表为空，此处顺延）
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(64), default='')        # 原表「产业」字段
    node_code = db.Column(db.String(64), default='', index=True)  # 产业链环节
    role = db.Column(db.String(32), default='一般')        # 链主/重点/一般
    is_hightech = db.Column(db.Boolean, default=False)     # 高企
    leader_level = db.Column(db.String(32), default='')    # 国家级/省级/市级
    is_scale = db.Column(db.Boolean, default=False)        # 规上
    region = db.Column(db.String(128), default='')         # 属地
    basis = db.Column(db.Text, default='')                 # 环节归类依据
    source = db.Column(db.String(128), default='襄州片区企业统计表')
    review_status = db.Column(db.String(16), default='待复核')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'seq': self.seq,
            'name': self.name,
            'industry': self.industry or '',
            'node_code': self.node_code or '',
            'role': self.role or '一般',
            'is_hightech': bool(self.is_hightech),
            'leader_level': self.leader_level or '',
            'is_scale': bool(self.is_scale),
            'region': self.region or '',
            'basis': self.basis or '',
            'source': self.source or '',
            'review_status': self.review_status or '待复核',
        }


class ChainGap(db.Model):
    """共性配套缺口（含优先级五因子得分）"""
    __tablename__ = 'chain_gaps'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_code = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    demand = db.Column(db.Text, default='')            # 共性配套需求描述
    supporters = db.Column(db.Text, default='[]')      # 支撑本地企业（JSON 数组）
    supporter_count = db.Column(db.Integer, default=0)
    evidence = db.Column(db.Text, default='[]')        # 诉求/依据摘录（JSON 数组）
    f1 = db.Column(db.Integer, default=0)              # 需求刚性 30
    f2 = db.Column(db.Integer, default=0)              # 支撑企业数 25
    f3 = db.Column(db.Integer, default=0)              # 本地缺失度 25
    f4 = db.Column(db.Integer, default=0)              # 链主牵引 10
    f5 = db.Column(db.Integer, default=0)              # 落地可行性 10
    total_score = db.Column(db.Integer, default=0)
    level = db.Column(db.String(16), default='中')      # 高/中/低
    analysis_note = db.Column(db.Text, default='')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        def _loads(v, default):
            try:
                return json.loads(v) if v else default
            except Exception:
                return default
        return {
            'id': self.id,
            'node_code': self.node_code,
            'title': self.title,
            'demand': self.demand or '',
            'supporters': _loads(self.supporters, []),
            'supporter_count': self.supporter_count or 0,
            'evidence': _loads(self.evidence, []),
            'factors': {
                'f1': self.f1 or 0, 'f2': self.f2 or 0, 'f3': self.f3 or 0,
                'f4': self.f4 or 0, 'f5': self.f5 or 0,
            },
            'total_score': self.total_score or 0,
            'level': self.level or '中',
            'analysis_note': self.analysis_note or '',
            'sort_order': self.sort_order or 0,
        }


class ChainTarget(db.Model):
    """目标企业候选（联网采集，保留来源链接）"""
    __tablename__ = 'chain_targets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gap_id = db.Column(db.Integer, db.ForeignKey('chain_gaps.id', ondelete='CASCADE'), index=True)
    name = db.Column(db.String(255), nullable=False)
    node_code = db.Column(db.String(64), default='')
    region = db.Column(db.String(128), default='')
    products = db.Column(db.Text, default='')
    scale = db.Column(db.String(255), default='')
    source_url = db.Column(db.String(512), default='')
    evidence = db.Column(db.Text, default='')          # 匹配理由
    scores = db.Column(db.Text, default='{}')          # 五因子分项（JSON）
    total_score = db.Column(db.Integer, default=0)
    is_local = db.Column(db.Boolean, default=False)     # 是否市域内已有（可联动）
    review_status = db.Column(db.String(16), default='待复核')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        try:
            sc = json.loads(self.scores) if self.scores else {}
        except Exception:
            sc = {}
        return {
            'id': self.id,
            'gap_id': self.gap_id,
            'name': self.name,
            'node_code': self.node_code or '',
            'region': self.region or '',
            'products': self.products or '',
            'scale': self.scale or '',
            'source_url': self.source_url or '',
            'evidence': self.evidence or '',
            'scores': sc,
            'total_score': self.total_score or 0,
            'is_local': bool(self.is_local),
            'review_status': self.review_status or '待复核',
        }


class ChainAdvice(db.Model):
    """招商建议（文字材料）"""
    __tablename__ = 'chain_advice'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gap_id = db.Column(db.Integer, default=0, index=True)  # 0 = 总体建议
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, default='')
    kv = db.Column(db.String(512), default='')           # 目标企业数 / 切入点 / 承载
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'gap_id': self.gap_id or 0,
            'title': self.title or '',
            'content': self.content or '',
            'kv': self.kv or '',
        }
