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
NODES = [
    # 上游：农业生产投入品与原料
    ('SEED', '种子种苗与育种', '上游', 1, '育种研发、种子生产与经营、种苗供应、品种权与种子加工检测'),
    ('FEED', '饲料与动物营养', '上游', 2, '畜禽配合饲料、预混料、饲料添加剂'),
    ('FERT', '肥料与土壤改良', '上游', 3, '有机肥、生物菌肥、复合肥、水溶肥、土壤调理剂'),
    ('PEST', '农药与植保服务', '上游', 4, '生物农药制剂、绿色防控、统防统治、天敌与信息素'),
    ('MACH', '农业机械与农技服务', '上游', 5, '农机装备、农机服务、植保托管、农技服务'),
    ('FARM', '种植、园艺与水产养殖', '上游', 6, '粮食、棉花、食用菌、辣椒等种植与初加工，淡水养殖与苗木果木'),
    ('LIVE', '畜禽养殖', '上游', 7, '生猪、禽类、肉牛等规模化养殖'),
    # 中游：初加工
    ('GRAIN', '米面粮油加工', '中游', 8, '大米、面粉、食用油等粮油初加工'),
    ('MEAT', '肉禽蛋加工', '中游', 9, '屠宰分割、肉禽蛋制品加工'),
    ('VEG', '果蔬与食用菌加工', '中游', 10, '芝麻与淀粉制品、净菜、脱水、菌菇制品等加工'),
    ('DAIRY', '乳制品加工', '中游', 11, '液态奶、酸奶、奶酪与乳基原料加工'),
    ('ADDI', '食品添加与调味', '中游', 12, '食品添加剂、复合调味料、香辛料、稳定增稠剂'),
    # 下游：精深加工与终端
    ('SNACK', '休闲食品与烘焙', '下游', 13, '膨化休闲、烘焙糕点、炒货、休闲零食'),
    ('FROZEN', '速冻调理与速食', '下游', 14, '速冻调理食品、预制菜、速食'),
    ('LOCAL', '地方特色食品', '下游', 15, '襄阳牛肉面等地方特色与区域品牌食品'),
    ('BIOMAT', '生物基新材料', '下游', 16, '生物基材料、特种淀粉、可降解材料、功能性原料'),
    ('BIOMED', '生物医药与体外诊断', '下游', 17, '诊断试剂与设备、生物制造、中草药生物技术、辐照灭菌'),
    # 平台：支撑配套
    ('PACK', '包装制品与印刷', '平台', 18, '纸箱、软包装复合、食品级包材、彩印'),
    ('COLD', '冷链仓储与物流', '平台', 19, '产地预冷、冷库仓储、冷链配送、集配中心'),
    ('TEST', '检测认证与研发中试', '平台', 20, '食品检测、认证服务、中试熟化、成果转化'),
    ('BUILD', '建材与园区建设', '平台', 21, '防水材料、装配式建筑、建设工程、园区配套'),
    ('EQUIP', '装备机电与汽车电子', '平台', 22, '机电装备、航空电机、汽车电子、精密零部件'),
    ('AERO', '低空经济与无人机', '平台', 23, '无人机整机制造与飞控、飞防服务、低空运营与教培研考'),
    ('ENV', '环保工程与生态治理', '平台', 24, '环境监测、污染治理、固废资源化、节水与土壤修复'),
    ('IRRIGATE', '节水灌溉与水肥一体化', '平台', 25, '智能灌溉设备、水肥一体化、灌溉工程与高标准农田'),
    ('OPERATE', '园区投资与运营', '平台', 26, '园区开发、交通投资、基础设施运营'),
]

# 旧版环节（存在即说明库中为上一版数据，需要重建）
LEGACY_NODE_CODES = ('TEXTILE', 'APPAREL', 'ENERGY', 'MINE')

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
    return len(existing) != len(NODES)


def _clear_all():
    """清空产业链全部表（重建前）。"""
    from models.chain import ChainAdvice, ChainEnterprise, ChainGap, ChainNode, ChainTarget
    from extensions import db
    for model in (ChainTarget, ChainGap, ChainAdvice, ChainEnterprise, ChainNode):
        model.query.delete()
    db.session.commit()


def seed_chain_data(app):
    """幂等写入产业链招商基础数据。"""
    from models.chain import ChainAdvice, ChainEnterprise, ChainGap, ChainNode, ChainTarget
    from extensions import db

    try:
        if ChainNode.query.count() > 0:
            if not _need_rebuild():
                app.logger.info('[产业链招商] 基础数据已存在且结构一致，跳过初始化')
                return
            app.logger.info('[产业链招商] 检测到旧版产业链数据，开始重建')
            _clear_all()

        enterprises = _load('ent62.json')
        gaps = _load('gaps.json')
        targets = _load('targets.json')
        advice = _load('advice.json')

        # --- 校验：缺口支撑企业必须存在于企业主数据中 ---
        ent_names = {e['name'] for e in enterprises}
        for g in gaps:
            missing = [s for s in g['supporters'] if s not in ent_names]
            if missing:
                raise ValueError(f"缺口「{g['title']}」的支撑企业不在 62 家主数据中: {missing}")

        for code, name, layer, order, desc in NODES:
            db.session.add(ChainNode(code=code, name=name, layer=layer, sort_order=order, description=desc))

        for e in enterprises:
            db.session.add(ChainEnterprise(
                seq=e['seq'], name=e['name'], industry=e['industry'], node_code=e['node_code'],
                role=e['role'], is_hightech=e['is_hightech'], leader_level=e['leader_level'],
                is_scale=e['is_scale'], region=e['region'], basis=e['basis'],
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
                source='襄阳国家农高区企业情况统计表', review_status='待复核'))

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
                source_url=t['source_url'], evidence=t['evidence'],
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

        db.session.commit()
        outprov = len([t for t in targets if t['region_type'] == '省外'])
        app.logger.info(
            f'[产业链招商] 初始化完成：环节 {len(NODES)} / 企业 {len(enterprises)} / '
            f'缺口 {len(gaps)} / 目标企业 {len(targets)}（省外 {outprov}）/ 建议 {len(advice)}')
    except Exception as exc:
        db.session.rollback()
        app.logger.warning(f'[产业链招商] 初始化失败: {exc}')
