"""产业链招商 —— 数据模型

农高区（襄州片区）企业产业链图谱分析：
- chain_nodes       产业链环节本体（层级 → 大类 → 环节 三级结构）
- chain_enterprises 企业主数据（90 家 = 襄州区属地 62 + 东津新区 28）
- chain_gaps        共性配套缺口（含优先级六因子得分）
- chain_targets     目标企业候选（联网采集，保留多个来源链接）
- chain_advice      招商建议（文字材料）
- chain_changelog   更新日志（修改内容 + 风险提示 + 下一步工作）

优先级六因子（总分 100）：
  F1 需求刚性 25 / F2 支撑企业数 20 / F3 本地缺失度 20
  F4 链主牵引 10 / F5 落地可行性 10 / F6 企业与承载实力 15
"""
from datetime import datetime

from extensions import db


class ChainNode(db.Model):
    """产业链环节本体（层级 → 大类 → 环节 三级结构）"""
    __tablename__ = 'chain_nodes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(128), nullable=False)
    layer = db.Column(db.String(32), nullable=False, default='上游')  # 上游/中游/下游/平台/其他
    group_name = db.Column(db.String(64), default='')   # 所属大类
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
            'group_name': self.group_name or '',
            'sort_order': self.sort_order,
            'description': self.description or '',
        }


class ChainChangelog(db.Model):
    """更新日志（每次更新的修改内容 + 风险提示 + 下一步工作）"""
    __tablename__ = 'chain_changelog'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version = db.Column(db.String(32), nullable=False)      # 版本号
    log_date = db.Column(db.String(16), default='')         # 更新日期
    title = db.Column(db.String(255), default='')           # 更新标题
    summary = db.Column(db.Text, default='')                # 总体说明
    changes = db.Column(db.Text, default='[]')              # 修改内容（JSON 数组）
    risks = db.Column(db.Text, default='[]')                # 风险提示（JSON 数组）
    next_steps = db.Column(db.Text, default='[]')           # 下一步工作（JSON 数组）
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json

        def _load(v):
            try:
                arr = json.loads(v) if v else []
                return arr if isinstance(arr, list) else []
            except Exception:
                return []

        return {
            'id': self.id,
            'version': self.version or '',
            'log_date': self.log_date or '',
            'title': self.title or '',
            'summary': self.summary or '',
            'changes': _load(self.changes),
            'risks': _load(self.risks),
            'next_steps': _load(self.next_steps),
            'sort_order': self.sort_order or 0,
        }


class ChainEnterprise(db.Model):
    """企业主数据（归类到产业链环节，含工商核实的企业实力五维）"""
    __tablename__ = 'chain_enterprises'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    seq = db.Column(db.Integer, default=0)                # 权威统计表序号
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(64), default='')        # 原表「产业」字段
    node_code = db.Column(db.String(64), default='', index=True)  # 产业链环节
    role = db.Column(db.String(32), default='一般')        # 链主/重点/一般
    is_hightech = db.Column(db.Boolean, default=False)     # 高企
    leader_level = db.Column(db.String(255), default='')   # 龙头/资质称号
    is_scale = db.Column(db.Boolean, default=False)        # 规上
    is_smei = db.Column(db.Boolean, default=False)         # 专精特新
    is_kexiao = db.Column(db.Boolean, default=False)       # 科小入库
    region = db.Column(db.String(128), default='')         # 属地
    basis = db.Column(db.Text, default='')                 # 环节归类依据
    source = db.Column(db.String(128), default='襄阳国家农高区企业情况统计表')
    review_status = db.Column(db.String(16), default='待复核')
    # ---- 企业实力五维（联网核实） ----
    district = db.Column(db.String(64), default='')        # 登记机关属地
    reg_capital = db.Column(db.Integer, default=0)         # 注册资本（万元）
    reg_capital_text = db.Column(db.String(128), default='')  # 注册资本原文
    establish_date = db.Column(db.String(32), default='')
    legal_person = db.Column(db.String(64), default='')
    address = db.Column(db.String(255), default='')
    main_business = db.Column(db.Text, default='')         # 主营业务
    revenue_3y = db.Column(db.String(255), default='')     # 近三年营收趋势
    netprofit_3y = db.Column(db.String(255), default='')   # 近三年净利润趋势
    funding = db.Column(db.Text, default='')               # 融资情况
    investments = db.Column(db.Text, default='')           # 对外投资情况
    signed_deal = db.Column(db.Text, default='')           # 投资签约情况
    highlights = db.Column(db.Text, default='')            # 其他亮点
    source_url = db.Column(db.String(512), default='')     # 来源链接
    confidence = db.Column(db.String(16), default='medium')  # 核实置信度
    strength = db.Column(db.Integer, default=0)           # 企业实力分 0-100
    strength_detail = db.Column(db.Text, default='{}')     # 实力分项（JSON）
    strength_trend = db.Column(db.String(32), default='')  # 财报趋势
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        try:
            sd = json.loads(self.strength_detail) if self.strength_detail else {}
        except Exception:
            sd = {}
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
            'is_smei': bool(self.is_smei),
            'is_kexiao': bool(self.is_kexiao),
            'region': self.region or '',
            'basis': self.basis or '',
            'source': self.source or '',
            'review_status': self.review_status or '待复核',
            'district': self.district or '',
            'reg_capital': self.reg_capital or 0,
            'reg_capital_text': self.reg_capital_text or '',
            'establish_date': self.establish_date or '',
            'legal_person': self.legal_person or '',
            'address': self.address or '',
            'main_business': self.main_business or '',
            'revenue_3y': self.revenue_3y or '',
            'netprofit_3y': self.netprofit_3y or '',
            'funding': self.funding or '',
            'investments': self.investments or '',
            'signed_deal': self.signed_deal or '',
            'highlights': self.highlights or '',
            'source_url': self.source_url or '',
            'confidence': self.confidence or 'medium',
            'strength': self.strength or 0,
            'strength_detail': sd,
            'strength_trend': self.strength_trend or '',
        }


class ChainGap(db.Model):
    """共性配套缺口（含优先级六因子得分）"""
    __tablename__ = 'chain_gaps'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_code = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    demand = db.Column(db.Text, default='')            # 共性配套需求描述
    supporters = db.Column(db.Text, default='[]')      # 支撑本地企业（JSON 数组）
    supporter_count = db.Column(db.Integer, default=0)
    evidence = db.Column(db.Text, default='[]')        # 诉求/依据摘录（JSON 数组）
    f1 = db.Column(db.Integer, default=0)              # 需求刚性 25
    f2 = db.Column(db.Integer, default=0)              # 支撑企业数 20
    f3 = db.Column(db.Integer, default=0)              # 本地缺失度 20
    f4 = db.Column(db.Integer, default=0)              # 链主牵引 10
    f5 = db.Column(db.Integer, default=0)              # 落地可行性 10
    f6 = db.Column(db.Integer, default=0)              # 企业与承载实力 15
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
            'title': self.title or '',
            'demand': self.demand or '',
            'supporters': _loads(self.supporters, []),
            'supporter_count': self.supporter_count or 0,
            'evidence': _loads(self.evidence, []),
            'factors': {
                'f1': self.f1 or 0, 'f2': self.f2 or 0, 'f3': self.f3 or 0,
                'f4': self.f4 or 0, 'f5': self.f5 or 0, 'f6': self.f6 or 0,
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
    region = db.Column(db.String(128), default='')        # 地域描述
    province = db.Column(db.String(32), default='')        # 省份
    city = db.Column(db.String(64), default='')           # 城市
    region_type = db.Column(db.String(32), default='', index=True)  # 省外/湖北省内市域外/襄阳市域内
    is_xiangzhou_local = db.Column(db.Boolean, default=False)     # 是否襄州区属地（招商引资应排除）
    products = db.Column(db.Text, default='')
    scale = db.Column(db.String(255), default='')
    listed = db.Column(db.String(128), default='')         # 上市情况
    source_url = db.Column(db.String(512), default='')
    source_links = db.Column(db.Text, default='[]')         # 多个来源链接（JSON 数组，含小标题）
    evidence = db.Column(db.Text, default='')              # 匹配理由
    scores = db.Column(db.Text, default='{}')              # 六因子分项（JSON）
    total_score = db.Column(db.Integer, default=0)
    is_local = db.Column(db.Boolean, default=False)        # 是否襄阳市域内（可联动）
    review_status = db.Column(db.String(16), default='待复核')
    # ---- 产业链深度判据 ----
    chain_role = db.Column(db.String(16), default='补链', index=True)  # 补链/延链/强链
    match_local_chain = db.Column(db.Text, default='[]')   # 可对接本地链主（JSON 数组）
    landing_form = db.Column(db.String(128), default='')   # 建议落地形式
    invest_fit_level = db.Column(db.String(8), default='中', index=True)  # 高/中/低
    invest_fit_reason = db.Column(db.Text, default='')     # 投资可行性理由
    # ---- 企业实力五维 ----
    reg_capital = db.Column(db.Integer, default=0)
    revenue_3y = db.Column(db.String(255), default='')
    netprofit_3y = db.Column(db.String(255), default='')
    funding = db.Column(db.Text, default='')
    investments = db.Column(db.Text, default='')
    signed_deal = db.Column(db.Text, default='')
    strength = db.Column(db.Integer, default=0)
    confidence = db.Column(db.String(16), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        try:
            sc = json.loads(self.scores) if self.scores else {}
        except Exception:
            sc = {}
        try:
            ml = json.loads(self.match_local_chain) if self.match_local_chain else []
        except Exception:
            ml = []
        try:
            sl = json.loads(self.source_links) if self.source_links else []
        except Exception:
            sl = []
        if not sl and self.source_url:
            sl = [{'title': '信息来源', 'url': self.source_url}]
        return {
            'id': self.id,
            'gap_id': self.gap_id,
            'name': self.name,
            'node_code': self.node_code or '',
            'region': self.region or '',
            'province': self.province or '',
            'city': self.city or '',
            'region_type': self.region_type or '',
            'is_xiangzhou_local': bool(self.is_xiangzhou_local),
            'products': self.products or '',
            'scale': self.scale or '',
            'listed': self.listed or '',
            'source_url': self.source_url or '',
            'source_links': sl,
            'evidence': self.evidence or '',
            'scores': sc,
            'total_score': self.total_score or 0,
            'is_local': bool(self.is_local),
            'review_status': self.review_status or '待复核',
            'chain_role': self.chain_role or '补链',
            'match_local_chain': ml,
            'landing_form': self.landing_form or '',
            'invest_fit_level': self.invest_fit_level or '中',
            'invest_fit_reason': self.invest_fit_reason or '',
            'reg_capital': self.reg_capital or 0,
            'revenue_3y': self.revenue_3y or '',
            'netprofit_3y': self.netprofit_3y or '',
            'funding': self.funding or '',
            'investments': self.investments or '',
            'signed_deal': self.signed_deal or '',
            'strength': self.strength or 0,
            'confidence': self.confidence or 'medium',
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
