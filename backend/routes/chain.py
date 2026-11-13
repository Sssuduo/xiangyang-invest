"""产业链招商智能分析 API 路由

数据链路：企业统计表（62 家）→ 环节归类 → 共性缺口 → 五因子优先级 → 目标企业 → 招商建议

接口前缀：/api/chain
"""
import csv
import io
import json
import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request, send_file

from models.chain import ChainAdvice, ChainEnterprise, ChainGap, ChainNode, ChainTarget
from extensions import db
from routes.business_auth import business_login_required, visitor_block

logger = logging.getLogger(__name__)

chain_bp = Blueprint('chain', __name__, url_prefix='/api/chain')
bp = chain_bp

# 图例：环节层级配色（与前端统一）
LAYER_ORDER = ['上游', '中游', '下游', '平台']
LAYER_COLORS = {
    '上游': '#5b9bd5',
    '中游': '#2f7f5f',
    '下游': '#c98b2e',
    '平台': '#7b6fd4',
}
LEVEL_COLORS = {'高': '#f56c6c', '中': '#e6a23c', '低': '#909399'}

# 优先级五因子定义（供前端可视化规则表）
FACTOR_RULES = [
    {'key': 'f1', 'name': '需求刚性', 'max': 30, 'desc': '本地企业对配套环节的采购/使用需求是否不可替代'},
    {'key': 'f2', 'name': '支撑企业数', 'max': 25, 'desc': '提出该配套需求的企业数量与规模（支撑面）'},
    {'key': 'f3', 'name': '本地缺失度', 'max': 25, 'desc': '本地该环节供给空缺程度，越空缺得分越高'},
    {'key': 'f4', 'name': '链主牵引', 'max': 10, 'desc': '是否有本地链主企业明确提出并可带动配套落地'},
    {'key': 'f5', 'name': '落地可行性', 'max': 10, 'desc': '承载条件、市场半径、政策与建设时序的可操作性'},
]

LEVEL_RULES = [
    {'level': '高', 'range': '总分 ≥ 80', 'color': LEVEL_COLORS['高'], 'desc': '优先出手，重点跟进'},
    {'level': '中', 'range': '60 ≤ 总分 ≤ 79', 'color': LEVEL_COLORS['中'], 'desc': '纳入储备，服务先行'},
    {'level': '低', 'range': '总分 < 60', 'color': LEVEL_COLORS['低'], 'desc': '暂不招商，并入其他缺口一并解决'},
]

VETO_RULE = '否决规则：本地该环节已有 6 家及以上企业供给时，该环节优先级不得高于「中」'


def _perm(user, action, default=True):
    """读取业务用户模块权限。

    产业链模块为后加功能，历史账号的 permissions 中没有 chain 键，
    按向后兼容策略放行（default=True）；一旦后台显式配置，则严格按配置判定。
    """
    try:
        perms = user.get_permissions() if hasattr(user, 'get_permissions') else {}
    except Exception:
        perms = {}
    chain_perm = perms.get('chain')
    if chain_perm is None:
        return default
    value = chain_perm.get(action)
    if value is None:
        return default
    return bool(value)


def _node_map():
    return {n.code: n for n in ChainNode.query.order_by(ChainNode.sort_order).all()}


def _gap_map():
    return {g.id: g for g in ChainGap.query.order_by(ChainGap.total_score.desc()).all()}


# ===== 读取接口 =====

@bp.route('/overview', methods=['GET'])
@business_login_required
def get_overview():
    """总览：统计口径 + 层级分布 + 优先级分布"""
    nodes = ChainNode.query.all()
    enterprises = ChainEnterprise.query.all()
    gaps = ChainGap.query.all()
    targets = ChainTarget.query.all()

    node_map = _node_map()
    layer_stats = []
    for layer in LAYER_ORDER:
        layer_nodes = [n for n in nodes if n.layer == layer]
        codes = {n.code for n in layer_nodes}
        ents = [e for e in enterprises if e.node_code in codes]
        gaps_in_layer = [g for g in gaps if g.node_code in codes]
        layer_stats.append({
            'layer': layer,
            'color': LAYER_COLORS[layer],
            'node_count': len(layer_nodes),
            'enterprise_count': len(ents),
            'leader_count': len([e for e in ents if e.role == '链主']),
            'gap_count': len(gaps_in_layer),
            'target_count': len([t for t in targets if t.node_code in codes]),
        })

    level_stats = []
    for lv in ('高', '中', '低'):
        gs = [g for g in gaps if g.level == lv]
        level_stats.append({
            'level': lv,
            'color': LEVEL_COLORS[lv],
            'gap_count': len(gs),
            'target_count': sum(len([t for t in targets if t.gap_id == g.id]) for g in gs),
        })

    role_stats = []
    for role in ('链主', '重点', '一般'):
        role_stats.append({
            'role': role,
            'count': len([e for e in enterprises if e.role == role]),
        })

    return jsonify({'code': 0, 'data': {
        'node_count': len(nodes),
        'enterprise_count': len(enterprises),
        'gap_count': len(gaps),
        'target_count': len(targets),
        'advice_count': ChainAdvice.query.count(),
        'hightech_count': len([e for e in enterprises if e.is_hightech]),
        'scale_count': len([e for e in enterprises if e.is_scale]),
        'leader_count': len([e for e in enterprises if e.role == '链主']),
        'local_target_count': len([t for t in targets if t.is_local]),
        'layer_stats': layer_stats,
        'level_stats': level_stats,
        'role_stats': role_stats,
        'rules': {
            'factors': FACTOR_RULES,
            'levels': LEVEL_RULES,
            'veto': VETO_RULE,
        },
        'node_index': {n.code: n.name for n in nodes},
    }})


@bp.route('/nodes', methods=['GET'])
@business_login_required
def get_nodes():
    """环节本体（含企业数、支撑数、缺口标记）"""
    nodes = ChainNode.query.order_by(ChainNode.sort_order).all()
    enterprises = ChainEnterprise.query.all()
    gaps = ChainGap.query.all()
    targets = ChainTarget.query.all()

    result = []
    for n in nodes:
        ents = [e for e in enterprises if e.node_code == n.code]
        gap = next((g for g in gaps if g.node_code == n.code), None)
        result.append({
            'code': n.code,
            'name': n.name,
            'layer': n.layer,
            'sort_order': n.sort_order,
            'description': n.description or '',
            'color': LAYER_COLORS.get(n.layer, '#5b9bd5'),
            'enterprise_count': len(ents),
            'hightech_count': len([e for e in ents if e.is_hightech]),
            'scale_count': len([e for e in ents if e.is_scale]),
            'leader_count': len([e for e in ents if e.role == '链主']),
            'leader_names': [e.name for e in ents if e.role == '链主'],
            'has_gap': gap is not None,
            'gap_id': gap.id if gap else 0,
            'gap_level': gap.level if gap else '',
            'gap_score': gap.total_score if gap else 0,
            'target_count': len([t for t in targets if t.node_code == n.code]),
        })
    return jsonify({'code': 0, 'data': result})


@bp.route('/enterprises', methods=['GET'])
@business_login_required
def get_enterprises():
    """企业清单（支持按环节、层级、角色、关键字筛选）"""
    q = ChainEnterprise.query.order_by(ChainEnterprise.seq)
    node_code = request.args.get('node_code', '').strip()
    layer = request.args.get('layer', '').strip()
    role = request.args.get('role', '').strip()
    keyword = request.args.get('keyword', '').strip()

    node_map = _node_map()
    items = q.all()
    if node_code:
        items = [e for e in items if e.node_code == node_code]
    if layer:
        codes = {c for c, n in node_map.items() if n.layer == layer}
        items = [e for e in items if e.node_code in codes]
    if role:
        items = [e for e in items if e.role == role]
    if keyword:
        items = [e for e in items if keyword in e.name or keyword in (e.industry or '') or keyword in (e.region or '')]

    data = []
    for e in items:
        d = e.to_dict()
        node = node_map.get(e.node_code)
        d['node_name'] = node.name if node else ''
        d['layer'] = node.layer if node else ''
        d['layer_color'] = LAYER_COLORS.get(node.layer, '#5b9bd5') if node else '#5b9bd5'
        data.append(d)
    return jsonify({'code': 0, 'data': data, 'total': len(data)})


@bp.route('/gaps', methods=['GET'])
@business_login_required
def get_gaps():
    """共性配套缺口（含五因子得分与目标企业数）"""
    gaps = ChainGap.query.order_by(ChainGap.total_score.desc()).all()
    targets = ChainTarget.query.all()
    node_map = _node_map()
    data = []
    for g in gaps:
        d = g.to_dict()
        node = node_map.get(g.node_code)
        d['node_name'] = node.name if node else ''
        d['layer'] = node.layer if node else ''
        d['layer_color'] = LAYER_COLORS.get(node.layer, '#5b9bd5') if node else '#5b9bd5'
        d['level_color'] = LEVEL_COLORS.get(g.level, '#909399')
        d['target_count'] = len([t for t in targets if t.gap_id == g.id])
        data.append(d)
    return jsonify({'code': 0, 'data': data})


@bp.route('/targets', methods=['GET'])
@business_login_required
def get_targets():
    """目标企业候选库"""
    q = ChainTarget.query.order_by(ChainTarget.total_score.desc())
    gap_id = request.args.get('gap_id', '').strip()
    node_code = request.args.get('node_code', '').strip()
    is_local = request.args.get('is_local', '').strip()
    keyword = request.args.get('keyword', '').strip()

    items = q.all()
    if gap_id and gap_id != '0':
        items = [t for t in items if t.gap_id == int(gap_id)]
    if node_code:
        items = [t for t in items if t.node_code == node_code]
    if is_local in ('1', '0'):
        items = [t for t in items if bool(t.is_local) == (is_local == '1')]
    if keyword:
        items = [t for t in items if keyword in t.name or keyword in (t.products or '')
                 or keyword in (t.region or '') or keyword in (t.evidence or '')]

    gap_map = _gap_map()
    node_map = _node_map()
    data = []
    for t in items:
        d = t.to_dict()
        gap = gap_map.get(t.gap_id)
        d['gap_title'] = gap.title if gap else ''
        d['gap_level'] = gap.level if gap else ''
        d['gap_score'] = gap.total_score if gap else 0
        node = node_map.get(t.node_code)
        d['node_name'] = node.name if node else ''
        d['layer'] = node.layer if node else ''
        d['layer_color'] = LAYER_COLORS.get(node.layer, '#5b9bd5') if node else '#5b9bd5'
        data.append(d)
    return jsonify({'code': 0, 'data': data, 'total': len(data)})


@bp.route('/advice', methods=['GET'])
@business_login_required
def get_advice():
    """招商建议（总体判断 + 五个方向 + 风险提示）"""
    items = ChainAdvice.query.order_by(ChainAdvice.sort_order).all()
    gaps = ChainGap.query.all()
    gap_map = {g.id: g for g in gaps}
    node_map = _node_map()

    data = []
    for a in items:
        d = a.to_dict()
        gap = gap_map.get(a.gap_id)
        d['gap_score'] = gap.total_score if gap else 0
        d['gap_level'] = gap.level if gap else ''
        d['node_name'] = node_map.get(gap.node_code).name if gap and gap.node_code in node_map else ''
        d['target_count'] = len(ChainTarget.query.filter_by(gap_id=a.gap_id).all()) if a.gap_id else 0
        data.append(d)
    return jsonify({'code': 0, 'data': data})


# ===== 导出接口 =====

CSV_DATASETS = {
    'enterprises': ('环节供给总表', [
        '序号', '企业名称', '产业', '所属环节', '层级', '角色', '高企', '龙头级别', '规上', '属地', '归类依据',
    ]),
    'gaps': ('产业链缺口表', [
        '优先级', '分档', '环节', '缺口标题', '需求刚性(30)', '支撑企业数(25)', '本地缺失度(25)',
        '链主牵引(10)', '落地可行性(10)', '总分', '支撑本地企业数', '共性配套需求', '分析研判',
    ]),
    'targets': ('目标企业清单', [
        '对应缺口', '优先级分档', '目标企业', '所属环节', '所在地', '主营产品', '规模',
        '是否市域内已有', '匹配总分', '匹配理由', '来源链接', '复核状态',
    ]),
}


@bp.route('/export/<dataset>.csv', methods=['GET'])
@business_login_required
def export_csv(dataset):
    """导出 CSV（带 BOM，Excel 直接打开不乱码）"""
    if dataset not in CSV_DATASETS:
        return jsonify({'code': 400, 'message': f'不支持的数据集：{dataset}'}), 400

    title, headers = CSV_DATASETS[dataset]
    node_map = _node_map()
    gap_map = _gap_map()

    rows = []
    if dataset == 'enterprises':
        for e in ChainEnterprise.query.order_by(ChainEnterprise.seq).all():
            node = node_map.get(e.node_code)
            rows.append([
                e.seq, e.name, e.industry, node.name if node else '', node.layer if node else '',
                e.role, '是' if e.is_hightech else '否', e.leader_level or '', '是' if e.is_scale else '否',
                e.region, e.basis,
            ])
    elif dataset == 'gaps':
        for g in ChainGap.query.order_by(ChainGap.total_score.desc()).all():
            node = node_map.get(g.node_code)
            rows.append([
                g.total_score, g.level, node.name if node else '', g.title,
                g.f1, g.f2, g.f3, g.f4, g.f5, g.total_score, g.supporter_count,
                g.demand, g.analysis_note,
            ])
    else:
        for t in ChainTarget.query.order_by(ChainTarget.total_score.desc()).all():
            gap = gap_map.get(t.gap_id)
            node = node_map.get(t.node_code)
            rows.append([
                gap.title if gap else '', gap.level if gap else '', t.name,
                node.name if node else '', t.region, t.products, t.scale,
                '市域内已有' if t.is_local else '待引进', t.total_score, t.evidence,
                t.source_url, t.review_status,
            ])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f'襄阳农高区（襄州片区）产业链招商分析 — {title}'])
    writer.writerow([f'导出时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)

    buf = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    return send_file(
        buf,
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'产业链招商-{title}.csv',
    )


@bp.route('/export/word', methods=['GET'])
@business_login_required
def export_word():
    """导出招商建议材料（Word）"""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt
    except ImportError:
        return jsonify({'code': 500, 'message': '服务器未安装 python-docx，无法导出 Word'}), 500

    node_map = _node_map()
    gap_map = _gap_map()
    gaps = ChainGap.query.order_by(ChainGap.total_score.desc()).all()

    def set_font(run, name, size=None, bold=None):
        """统一设置中西文字体（避免 rPr/rFonts 为 None 时报错）"""
        run.font.name = name
        if size:
            run.font.size = size
        if bold is not None:
            run.bold = bold
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn('w:rFonts'))
        if rfonts is None:
            rfonts = OxmlElement('w:rFonts')
            rpr.insert(0, rfonts)
        rfonts.set(qn('w:eastAsia'), name)
        rfonts.set(qn('w:ascii'), name)
        rfonts.set(qn('w:hAnsi'), name)

    doc = Document()
    style = doc.styles['Normal']
    style.font.name = '仿宋'
    style.font.size = Pt(16)  # 三号
    style.element.get_or_add_rPr()
    srpr = style.element.rPr
    srfonts = srpr.find(qn('w:rFonts'))
    if srfonts is None:
        srfonts = OxmlElement('w:rFonts')
        srpr.insert(0, srfonts)
    srfonts.set(qn('w:eastAsia'), '仿宋')

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('襄阳农高区（襄州片区）产业链招商分析报告')
    set_font(run, '方正小标宋简体', Pt(22), True)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run(f'分析范围：襄州片区企业 {ChainEnterprise.query.count()} 家　　'
                     f'生成时间：{datetime.now().strftime("%Y年%m月%d日")}')
    set_font(r2, '楷体', Pt(12))

    def add_heading(text, level=1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(text)
        set_font(r, '黑体' if level == 1 else '楷体', Pt(16 if level == 1 else 15), True)
        return p

    def add_body(text):
        for line in (text or '').split('\n'):
            if not line.strip():
                continue
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(32)
            p.paragraph_format.line_spacing = 1.5
            r = p.add_run(line.strip())
            set_font(r, '仿宋', Pt(16))

    for advice in ChainAdvice.query.order_by(ChainAdvice.sort_order).all():
        add_heading(advice.title)
        if advice.kv:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(32)
            r = p.add_run(advice.kv)
            set_font(r, '楷体', Pt(14))
        add_body(advice.content)

    add_heading('附表一：产业链缺口与优先级一览')
    table = doc.add_table(rows=1, cols=6)
    table.style = 'Table Grid'
    hdr = ['优先级', '分档', '环节', '缺口标题', '支撑企业数', '目标企业数']
    for i, h in enumerate(hdr):
        cell = table.rows[0].cells[i]
        cell.text = h
        for pp in cell.paragraphs:
            for rr in pp.runs:
                set_font(rr, '黑体', Pt(11), True)
    for g in gaps:
        node = node_map.get(g.node_code)
        row = table.add_row().cells
        row[0].text = str(g.total_score)
        row[1].text = g.level
        row[2].text = node.name if node else ''
        row[3].text = g.title
        row[4].text = str(g.supporter_count)
        row[5].text = str(len(ChainTarget.query.filter_by(gap_id=g.id).all()))
        for cell in row:
            for pp in cell.paragraphs:
                for rr in pp.runs:
                    set_font(rr, '仿宋', Pt(10.5))

    add_heading('附表二：目标企业候选清单')
    table2 = doc.add_table(rows=1, cols=5)
    table2.style = 'Table Grid'
    hdr2 = ['对应缺口', '目标企业', '所在地', '匹配总分', '匹配理由']
    for i, h in enumerate(hdr2):
        cell = table2.rows[0].cells[i]
        cell.text = h
        for pp in cell.paragraphs:
            for rr in pp.runs:
                set_font(rr, '黑体', Pt(11), True)
    for t in ChainTarget.query.order_by(ChainTarget.total_score.desc()).all():
        gap = gap_map.get(t.gap_id)
        row = table2.add_row().cells
        row[0].text = gap.title if gap else ''
        row[1].text = t.name
        row[2].text = t.region
        row[3].text = str(t.total_score)
        row[4].text = t.evidence
        for cell in row:
            for pp in cell.paragraphs:
                for rr in pp.runs:
                    set_font(rr, '仿宋', Pt(10.5))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='襄阳农高区产业链招商分析报告.docx',
    )


# ===== 闭环：目标企业转招商线索 =====

@bp.route('/targets/<int:target_id>/convert', methods=['POST'])
@business_login_required
@visitor_block
def convert_target(target_id):
    """将目标企业转为招商线索（进入「招商线索研判」流程）"""
    if not _perm(g.user, 'convert'):
        return jsonify({'code': 403, 'message': '没有产业链转线索权限'}), 403

    target = ChainTarget.query.get(target_id)
    if target is None:
        return jsonify({'code': 404, 'message': '目标企业不存在'}), 404

    from models.investment import InvestmentLead

    gap = ChainGap.query.get(target.gap_id) if target.gap_id else None
    node = ChainNode.query.filter_by(code=target.node_code).first()

    existing = InvestmentLead.query.filter(
        InvestmentLead.is_deleted.is_(False),
        InvestmentLead.invest_enterprise == target.name,
    ).first()
    if existing:
        return jsonify({'code': 409, 'message': f'该企业已存在线索（编号 {existing.order_no}），未重复创建'}), 409

    max_order = db.session.query(db.func.max(InvestmentLead.order_no)).scalar() or 0
    lead = InvestmentLead(
        order_no=max_order + 1,
        project_name=f'{target.name} 招商对接',
        invest_enterprise=target.name,
        enterprise_info=f'所在地：{target.region}；主营：{target.products}；规模：{target.scale}；'
                        f'对应环节：{node.name if node else target.node_code}'
                        + (f'；对应缺口：{gap.title}' if gap else ''),
        project_content=f'【产业链配套缺口招商】{gap.title if gap else ""}\n'
                        f'{gap.demand if gap else ""}\n\n'
                        f'【匹配理由】{target.evidence}\n'
                        f'【信息来源】{target.source_url}',
        invest_amount=0,
        follow_status_code='follow_focus',
        meeting_status_code='not_meeting',
        project_type_code='type_shipin',
        person_in_charge='',
        conclusion=f'由产业链招商分析自动生成，匹配总分 {target.total_score}，待专班复核。',
        tags=json.dumps(['产业链招商'], ensure_ascii=False),
    )
    db.session.add(lead)
    db.session.commit()

    return jsonify({'code': 0, 'data': {'lead_id': lead.id, 'order_no': lead.order_no},
                    'message': f'已转为招商线索（编号 {lead.order_no}）'})


@bp.route('/targets/<int:target_id>/review', methods=['PUT'])
@business_login_required
@visitor_block
def update_review(target_id):
    """更新目标企业复核状态"""
    if not _perm(g.user, 'edit'):
        return jsonify({'code': 403, 'message': '没有产业链复核权限'}), 403

    target = ChainTarget.query.get(target_id)
    if target is None:
        return jsonify({'code': 404, 'message': '目标企业不存在'}), 404

    data = request.get_json(silent=True) or {}
    status = (data.get('review_status') or '').strip()
    if status not in ('待复核', '已复核', '已排除'):
        return jsonify({'code': 400, 'message': '复核状态仅支持：待复核 / 已复核 / 已排除'}), 400

    target.review_status = status
    db.session.commit()
    return jsonify({'code': 0, 'data': target.to_dict(), 'message': '复核状态已更新'})
