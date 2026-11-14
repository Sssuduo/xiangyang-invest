"""产业链招商 —— 种子数据与入库逻辑

数据来源：
1. 《襄阳国家农高区企业情况统计表》——本次分析的唯一企业范围（62 家）
2. 《襄阳现代农业及农产品精深加工产业图谱（一）》——作为环节划分的参考底图，
   但企业归属与上下游关系由综合判定形成（不照搬原图谱）
3. 公开渠道检索（企业官网/百科/工商公示/政务与行业媒体）——目标企业与承载条件

数据文件（backend/chain_data/）：
- ent62.json    62 家本地企业主数据（含注册资本/营收/融资/投资/签约五维核实结果）
- gaps.json    13 个共性配套缺口（六因子优先级评分）
- targets.json 102 家目标企业（省外 80 + 襄阳市域内 13 + 湖北省内市域外 9）
- advice.json  12 条招商建议

入库为幂等：当链环节本体结构与本版不一致（旧版数据）时自动重建。
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chain_data')

# ============================================================
# 产业链环节本体（综合判定版，26 个环节）
# 说明：本次按权威统计表重建后，删除本地无实际供给主体的纺织、服装、
#       能量、矿业四个环节，新增乳制品加工、低空经济与无人机、
#       生物医药与体外诊断、环保工程四个环节。
# ============================================================
NODES = []

# 旧版环节（仅用于日志说明；重建判定以下方节点集合精确比对为准，
# 因为部分环节码在不同版本中含义不同，列入本表会导致每次启动都误判重建）
LEGACY_NODE_CODES = ('APPAREL', 'ENERGY', 'MINE',
                      'BUILD', 'EQUIP', 'OPERATE')

# 当前版本应有的节点结构（层级 → 大类 → 环节）
EXPECTED_NODE_CODES = frozenset([
    'SEED', 'FEED', 'FERT', 'PEST', 'MACH', 'FARM', 'LIVE',
    'GRAIN', 'MEAT', 'VEG', 'ADDI', 'COTTON', 'TEXTILE',
    'SNACK', 'FROZEN', 'LOCAL', 'FUNC', 'WINE', 'DAIRY',
    'BIOMAT', 'BIOMED',
    'PACK', 'COLD', 'TEST', 'RD', 'AERO', 'ENV', 'IRRIGATE',
    'OTHER',
])

# 优先级六因子权重（与 gaps.json 中的分项上限一致）
FACTOR_WEIGHTS = {'f1': 25, 'f2': 20, 'f3': 20, 'f4': 10, 'f5': 10, 'f6': 15}


def _load(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f'产业链数据文件缺失: {path}')
    with open(path, encoding='utf-8') as fp:
        return json.load(fp)


def _need_rebuild():
    """判断库中是否已是本版结构。"""
    from models.chain import ChainNode
    existing = {n.code for n in ChainNode.query.all()}
    if not existing:
        return False
    if any(code in existing for code in LEGACY_NODE_CODES):
        return True
    # 节点集合必须与当前版本完全一致（缺失或新增都要重建）
    return existing != set(EXPECTED_NODE_CODES)


def _clear_all():
    """清空产业链全部表（重建前）。"""
    from models.chain import (ChainAdvice, ChainChangelog, ChainEnterprise, ChainGap,
                              ChainNode, ChainTarget)
    from extensions import db
    for model in (ChainTarget, ChainGap, ChainAdvice, ChainChangelog,
                  ChainEnterprise, ChainNode):
        model.query.delete()
    db.session.commit()


def seed_chain_data(app):
    """幂等写入产业链招商基础数据。"""
    from models.chain import (ChainAdvice, ChainChangelog, ChainEnterprise, ChainGap,
                              ChainNode, ChainTarget)
    from extensions import db

    try:
        if ChainNode.query.count() > 0:
            if not _need_rebuild():
                app.logger.info('[产业链招商] 基础数据已存在且结构一致，跳过初始化')
                return
            app.logger.info('[产业链招商] 检测到旧版产业链数据，开始重建')
            _clear_all()

        nodes = _load('nodes.json')
        enterprises = _load('ent90.json')
        gaps = _load('gaps.json')
        targets = _load('targets.json')
        advice = _load('advice.json')
        changelog = _load('changelog.json') if os.path.exists(
            os.path.join(DATA_DIR, 'changelog.json')) else []

        # --- 校验：缺口支撑企业必须存在于企业主数据中 ---
        ent_names = {e['name'] for e in enterprises}
        for g in gaps:
            missing = [s for s in g['supporters'] if s not in ent_names]
            if missing:
                raise ValueError(f"缺口「{g['title']}」的支撑企业不在 {len(ent_names)} 家主数据中: {missing}")

        for n in nodes:
            db.session.add(ChainNode(
                code=n['code'], name=n['name'], layer=n['layer'],
                group_name=n.get('group_name', ''),
                sort_order=n['sort_order'], description=n.get('desc', '')))

        for e in enterprises:
            db.session.add(ChainEnterprise(
                seq=e['seq'], name=e['name'], industry=e['industry'], node_code=e['node_code'],
                role=e['role'], is_hightech=e['is_hightech'], leader_level=e['leader_level'],
                is_scale=e['is_scale'], is_smei=e.get('is_smei', False),
                is_kexiao=e.get('is_kexiao', False),
                region=e['region'], basis=e['basis'],
                district=e.get('district', ''), reg_capital=e.get('reg_capital') or 0,
                reg_capital_text=e.get('reg_capital_text', ''),
                establish_date=e.get('establish_date', ''), legal_person=e.get('legal_person', ''),
                address=e.get('address', ''), main_business=e.get('main_business', ''),
                revenue_3y=e.get('revenue_3y') or '', netprofit_3y=e.get('netprofit_3y') or '',
                funding=e.get('funding') or '', investments=e.get('investments') or '',
                signed_deal=e.get('signed_deal') or '', highlights=e.get('highlights', ''),
                source_url=e.get('source_url', ''), confidence=e.get('confidence', 'medium'),
                strength=e.get('strength', 0),
                strength_detail=json.dumps(e.get('strength_detail', {}), ensure_ascii=False),
                strength_trend=e.get('strength_trend', ''),
                source='襄阳农高区企业统计表', review_status='待复核'))

        for g in gaps:
            db.session.add(ChainGap(
                node_code=g['node_code'], title=g['title'], demand=g['demand'],
                supporters=json.dumps(g['supporters'], ensure_ascii=False),
                supporter_count=len(g['supporters']),
                evidence=json.dumps(g['evidence'], ensure_ascii=False),
                f1=g['f1'], f2=g['f2'], f3=g['f3'], f4=g['f4'], f5=g['f5'], f6=g['f6'],
                total_score=g['total_score'], level=g['level'],
                analysis_note=g['analysis_note'], sort_order=g['gap_id']))

        for t in targets:
            db.session.add(ChainTarget(
                gap_id=t['gap_id'], name=t['name'], node_code=t['node_code'],
                region=f"{t['province']}{t['city']}".strip(),
                province=t['province'], city=t['city'], region_type=t['region_type'],
                is_xiangzhou_local=(t['region_type'] == '襄州区属地'),
                products=t['products'], scale=t['scale'], listed=t.get('listed', ''),
                source_url=t['source_url'],
                source_links=json.dumps(t.get('source_links') or [], ensure_ascii=False),
                evidence=t['evidence'],
                scores=json.dumps(t['scores'], ensure_ascii=False), total_score=t['total_score'],
                is_local=(t['region_type'] == '襄阳市域内'),
                chain_role=t['chain_role'],
                match_local_chain=json.dumps(t['match_local_chain'], ensure_ascii=False),
                landing_form=t['landing_form'],
                invest_fit_level=t['invest_fit_level'], invest_fit_reason=t['invest_fit_reason'],
                reg_capital=t.get('reg_capital') or 0,
                revenue_3y=t.get('revenue_3y') or '', netprofit_3y=t.get('netprofit_3y') or '',
                funding=t.get('funding') or '', investments=t.get('investments') or '',
                signed_deal=t.get('signed_deal') or '',
                strength=t.get('strength', 0), confidence=t.get('confidence', 'medium'),
                review_status='待复核'))

        for a in advice:
            db.session.add(ChainAdvice(
                gap_id=a['gap_id'], title=a['title'], content=a['content'],
                kv=a['kv'], sort_order=a['gap_id']))

        for i, c in enumerate(changelog, 1):
            db.session.add(ChainChangelog(
                version=c['version'], log_date=c['date'], title=c['title'], summary=c['summary'],
                changes=json.dumps(c.get('changes', []), ensure_ascii=False),
                risks=json.dumps(c.get('risks', []), ensure_ascii=False),
                next_steps=json.dumps(c.get('next_steps', []), ensure_ascii=False),
                sort_order=i))

        db.session.commit()
        outprov = len([t for t in targets if t['region_type'] == '省外'])
        app.logger.info(
            f'[产业链招商] 初始化完成：环节 {len(nodes)} / 企业 {len(enterprises)} / '
            f'缺口 {len(gaps)} / 目标企业 {len(targets)}（省外 {outprov}）/ '
            f'建议 {len(advice)} / 更新日志 {len(changelog)}')
    except Exception as exc:
        db.session.rollback()
        app.logger.warning(f'[产业链招商] 初始化失败: {exc}')
