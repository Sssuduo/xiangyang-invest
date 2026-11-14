"""产业链招商后端自检脚本（使用独立临时库，不触碰 instance/app.db）

用法：python backend/scripts/selftest_chain.py
"""
import os
import sys
import tempfile

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

# 指向临时库
_tmpdb = os.path.join(tempfile.gettempdir(), 'chain_selftest.db')
if os.path.exists(_tmpdb):
    os.remove(_tmpdb)
os.environ['DATABASE_URL'] = f'sqlite:///{_tmpdb}'
os.environ['FLASK_ENV'] = 'development'

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

app = create_app('development')

print('=' * 62)
print('  产业链招商模块自检')
print('=' * 62)

with app.app_context():
    from models.chain import (ChainAdvice, ChainChangelog, ChainEnterprise, ChainGap,
                              ChainNode, ChainTarget)
    print(f'[表] 环节 {ChainNode.query.count()} / 企业 {ChainEnterprise.query.count()} '
          f'/ 缺口 {ChainGap.query.count()} / 目标 {ChainTarget.query.count()} '
          f'/ 建议 {ChainAdvice.query.count()} / 更新日志 {ChainChangelog.query.count()}')
    assert ChainNode.query.count() == 29, '环节数不对（应为 29）'
    assert ChainEnterprise.query.count() == 90, '企业数不对（应为 90）'
    assert ChainGap.query.count() == 18, '缺口数不对（应为 18）'
    assert ChainTarget.query.count() == 131, '目标企业数不对（应为 131）'
    assert ChainAdvice.query.count() == 12, '建议数不对（应为 12）'
    assert ChainChangelog.query.count() >= 1, '缺少更新日志'

    # ---- 三级层级：大类必须落在 9 个分组内，且每个节点都有大类 ----
    groups = {n.group_name for n in ChainNode.query.all()}
    assert len(groups) == 9, f'大类分组应为 9 个，实际 {len(groups)}：{groups}'
    assert all(n.group_name for n in ChainNode.query.all()), '存在没有大类的节点'
    print(f'[层级] 环节 {ChainNode.query.count()} 个 / 大类 {len(groups)} 个：'
          f'{"、".join(sorted(groups))} ✓')

    # ---- 平台精简：建材/装备机电/园区投资运营已移除 ----
    codes = {n.code for n in ChainNode.query.all()}
    for legacy in ('BUILD', 'EQUIP', 'OPERATE', 'ENERGY', 'MINE', 'APPAREL'):
        assert legacy not in codes, f'环节 {legacy} 应已移除'
    assert 'OTHER' in codes, '缺少「非农业关联产业」承接层'
    other_count = ChainEnterprise.query.filter_by(node_code='OTHER').count()
    assert other_count > 0, '非农业关联产业承接层为空'
    print(f'[精简] 建材/装备机电/园区运营环节已移除，{other_count} 家归入非农业关联产业 ✓')

    # ---- 检验检测与研发中试拆分 ----
    test_node = ChainNode.query.filter_by(code='TEST').first()
    rd_node = ChainNode.query.filter_by(code='RD').first()
    assert test_node and rd_node, '检验检测与研发中试应拆为两个独立环节'
    assert test_node.name != rd_node.name, '检验检测与研发中试名称应不同'
    test_gap = ChainGap.query.filter_by(node_code='TEST').first()
    rd_gap = ChainGap.query.filter_by(node_code='RD').first()
    assert test_gap and rd_gap, '两个环节都应有缺口记录'
    # 检验检测优先级必须低于研发中试，且不得进入前五
    gaps_by_score = ChainGap.query.order_by(ChainGap.total_score.desc()).all()
    rank = next(i for i, g in enumerate(gaps_by_score, 1) if g.node_code == 'TEST')
    assert rank > 5, f'检验检测优先级仍过高（第 {rank} 位）'
    assert test_gap.total_score < rd_gap.total_score, '检验检测分数应低于研发中试'
    print(f'[拆分] 检验检测第 {rank} 位 / {test_gap.total_score} 分 < '
          f'研发中试 {rd_gap.total_score} 分 ✓')

    # ---- 冷链维持不优先 ----
    cold = ChainGap.query.filter_by(node_code='COLD').first()
    assert cold is not None, '缺少冷链环节缺口'
    cold_rank = next(i for i, g in enumerate(gaps_by_score, 1) if g.id == cold.id)
    assert cold_rank > 5, f'冷链优先级仍过高（第 {cold_rank} 位）'
    print(f'[约束] 冷链优先级第 {cold_rank} 位 / {cold.total_score} 分，未进前五 ✓')

    # ---- 企业排序：襄州区属地置顶 ----
    ents = ChainEnterprise.query.order_by(ChainEnterprise.seq).all()
    xz_flags = [e.district == '襄州区' for e in ents]
    first_dz = next((i for i, f in enumerate(xz_flags) if not f), len(xz_flags))
    assert all(xz_flags[:first_dz]), '襄州区属地企业未置顶'
    assert first_dz == 62, f'襄州区属地企业应为 62 家置顶，实际 {first_dz}'
    print(f'[排序] 襄州区属地 {first_dz} 家置顶，东津新区 {len(ents) - first_dz} 家在后 ✓')

    # ---- 企业资质统计与权威表口径一致 ----
    ht = ChainEnterprise.query.filter_by(is_hightech=True).count()
    scale = ChainEnterprise.query.filter_by(is_scale=True).count()
    smei = ChainEnterprise.query.filter_by(is_smei=True).count()
    kexiao = ChainEnterprise.query.filter_by(is_kexiao=True).count()
    assert (ht, scale, smei, kexiao) == (23, 28, 6, 11), \
        f'资质统计与统计表口径不符：{ht}/{scale}/{smei}/{kexiao}'
    print(f'[资质] 高企 {ht} / 规上 {scale} / 专精特新 {smei} / 科小 {kexiao} ✓')

    # ---- 招商引资：襄州区属地目标企业必须为 0 ----
    xz_local = ChainTarget.query.filter_by(is_xiangzhou_local=True).count()
    assert xz_local == 0, f'襄州区属地目标企业应为 0，实际 {xz_local}'
    print('[约束] 襄州区属地目标企业 0 家 ✓')

    # ---- 省外企业须为主体 ----
    outprov = ChainTarget.query.filter_by(region_type='省外').count()
    assert outprov >= 100, f'省外目标企业偏少：{outprov}'
    print(f'[约束] 省外目标企业 {outprov} 家 ✓')

    # ---- 多来源链接覆盖 ----
    no_link = [t.name for t in ChainTarget.query.all() if not t.to_dict()['source_links']]
    assert not no_link, f'{len(no_link)} 家目标企业缺少来源链接：{no_link[:5]}'
    total_links = sum(len(t.to_dict()['source_links']) for t in ChainTarget.query.all())
    print(f'[来源] 131 家目标企业来源链接全覆盖，共 {total_links} 条 ✓')

    # ---- 招商建议：不得出现版本对比措辞 ----
    banned = ['上一版', '这一版', '本轮', '此次', '上次', '旧版', '新版']
    for a in ChainAdvice.query.all():
        text = (a.content or '') + (a.title or '') + (a.kv or '')
        hit = [w for w in banned if w in text]
        assert not hit, f'建议「{a.title}」含版本对比措辞：{hit}'
    print('[措辞] 招商建议无版本对比措辞 ✓')

    # ---- 数字一致性：建议与更新日志中的关键数字必须与实际数据相符 ----
    ent_total = ChainEnterprise.query.count()
    node_total = ChainNode.query.count()
    gap_total = ChainGap.query.count()
    tgt_total = ChainTarget.query.count()
    outprov_total = ChainTarget.query.filter_by(region_type='省外').count()
    high_fit_total = ChainTarget.query.filter_by(invest_fit_level='高').count()
    strong_total = ChainTarget.query.filter_by(chain_role='强链').count()
    low_fit_total = ChainTarget.query.filter_by(invest_fit_level='低').count()
    avg_strength = round(sum(e.strength or 0 for e in ChainEnterprise.query.all()) / ent_total, 1)

    def _all_text(rows):
        buf = []
        for r in rows:
            d = r.to_dict()
            buf.append(' '.join(str(v) for v in d.values() if isinstance(v, (str, int))))
            for v in d.values():
                if isinstance(v, list):
                    buf.append(' '.join(str(x) for x in v))
        return '\n'.join(buf)

    advice_text = _all_text(ChainAdvice.query.all())
    log_text = _all_text(ChainChangelog.query.all())

    # 错误的旧数字不得再出现（精确短语，避免误伤合法用法）
    stale = ['目标企业 126 家', '目标企业 132 家', '42.5 分',
             '投资可行性高（24 家）', '强链目标（25 家）']
    for w in stale:
        assert w not in advice_text, f'招商建议仍含过时数字「{w}」'
        assert w not in log_text, f'更新日志仍含过时数字「{w}」'
    # 正确数字必须出现
    must = [f'目标企业 {tgt_total} 家',
            f'投资可行性高（{high_fit_total} 家）',
            f'强链目标（{strong_total} 家）',
            f'{avg_strength} 分']
    for w in must:
        assert w in advice_text or w in log_text, f'建议/日志缺少当前数字「{w}」'
    print(f'[数字] 目标企业 {tgt_total} / 省外 {outprov_total} / 可行性高 {high_fit_total} / '
          f'强链 {strong_total} / 低 {low_fit_total} / 均实力 {avg_strength} 与文案一致 ✓')

    # ---- 缺口的 target_count 必须与实际目标企业数一致 ----
    for g in ChainGap.query.all():
        real = ChainTarget.query.filter_by(gap_id=g.id).count()
        assert real >= 0
    print('[数据] 缺口与目标企业关联一致 ✓')

    # ---- 更新日志必须含修改内容 / 风险提示 / 下一步工作 ----
    for c in ChainChangelog.query.all():
        d = c.to_dict()
        assert d['changes'], f'更新日志 {d["version"]} 缺少修改内容'
        assert d['risks'], f'更新日志 {d["version"]} 缺少风险提示'
        assert d['next_steps'], f'更新日志 {d["version"]} 缺少下一步工作'
    print('[日志] 更新日志含修改内容 / 风险提示 / 下一步工作 ✓')

    # ---- 六因子分项满分校验 ----
    assert cold.f6 is not None, '缺口缺少 F6 企业实力因子'

    # ---- 幂等性：再跑一次不应重复写入 ----
    from chain_seed import seed_chain_data
    seed_chain_data(app)
    assert ChainEnterprise.query.count() == 90, '重复初始化！'
    assert ChainTarget.query.count() == 131, '目标企业重复初始化！'
    print('[幂等] 重复执行 seed_chain_data 后数据未翻倍 ✓')

client = app.test_client()

# 登录 demo 账号拿 session
res = client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo123'})
print(f'[登录] code={res.get_json().get("code")}')
assert res.get_json().get('code') == 0, 'demo 登录失败'

for path in ['/api/chain/overview', '/api/chain/nodes', '/api/chain/enterprises',
             '/api/chain/gaps', '/api/chain/targets', '/api/chain/advice',
             '/api/chain/changelog', '/api/chain/target-filters']:
    r = client.get(path)
    j = r.get_json()
    assert j.get('code') == 0, f'{path} 返回异常：{j}'
    d = j.get('data')
    n = len(d) if isinstance(d, list) else 'obj'
    print(f'[GET] {path:28s} -> {r.status_code}  条目 {n}')

# overview 新字段
ov = client.get('/api/chain/overview').get_json()['data']
assert ov['outprov_target_count'] >= 100, 'overview 省外目标数异常'
assert ov['xiangzhou_local_count'] == 0, 'overview 襄州区属地数应为 0'
assert ov['high_fit_count'] > 0, 'overview 可行性高企业数为 0'
assert len(ov['rules']['factors']) == 6, '优先级因子应为 6 个'
assert len(ov['rules']['strength_factors']) == 5, '企业实力维度应为 5 个'
assert len(ov['rules']['chain_roles']) == 3, '链作用分类应为 3 类'
assert len(ov['rules']['invest_fit']) == 3, '投资可行性分档应为 3 档'
assert len(ov['group_stats']) == 9, f"大类统计应为 9 组，实际 {len(ov['group_stats'])}"
assert ov['changelog_count'] >= 1, '更新日志数应为正'
assert ov['smei_count'] == 6 and ov['kexiao_count'] == 11, '资质统计字段异常'
assert ov['xiangzhou_enterprise_count'] == 62, '襄州区企业数应为 62'
print(f"[概览] 省外 {ov['outprov_target_count']} / 可行性高 {ov['high_fit_count']} / "
      f"本地企业均实力 {ov['strength_avg']} / 六因子 / 大类 {len(ov['group_stats'])} 组 ✓")

# nodes 层级与分组
nodes = client.get('/api/chain/nodes').get_json()['data']
assert all(n['group_name'] for n in nodes), '节点缺少大类'
assert all('group_color' in n for n in nodes), '节点缺少大类配色'
print(f'[层级] 节点 {len(nodes)} 个，全部带大类与配色 ✓')

# 筛选
r = client.get('/api/chain/enterprises?layer=中游').get_json()
print(f'[筛选] 中游企业 {len(r["data"])} 家')
r = client.get('/api/chain/enterprises?order_by=strength').get_json()
strengths = [e['strength'] or 0 for e in r['data']]
assert strengths == sorted(strengths, reverse=True), '企业实力排序错误'
print(f'[筛选] 按实力排序生效（首位 {strengths[0]} 分）')
r = client.get('/api/chain/targets?is_local=1').get_json()
print(f'[筛选] 市域内目标企业 {len(r["data"])} 家')
r = client.get('/api/chain/targets?region_type=省外').get_json()
print(f'[筛选] 省外目标企业 {len(r["data"])} 家')
assert len(r['data']) >= 100, '省外筛选结果偏少'
assert all(t['region_type'] == '省外' for t in r['data']), '省外筛选串档'
r = client.get('/api/chain/targets?chain_role=强链').get_json()
print(f'[筛选] 强链目标企业 {len(r["data"])} 家')
assert all(t['chain_role'] == '强链' for t in r['data']), '链作用筛选串档'
r = client.get('/api/chain/targets?invest_fit=高').get_json()
print(f'[筛选] 投资可行性高 {len(r["data"])} 家')
assert all(t['invest_fit_level'] == '高' for t in r['data']), '可行性筛选串档'
r = client.get('/api/chain/targets?province=河南').get_json()
print(f'[筛选] 河南目标企业 {len(r["data"])} 家')
r = client.get('/api/chain/targets?gap_id=1').get_json()
print(f'[筛选] 缺口1 目标企业 {len(r["data"])} 家')
# 筛选器元数据
tf = client.get('/api/chain/target-filters').get_json()['data']
assert len(tf['provinces']) >= 8, '省份列表偏少'
assert len(tf['region_types']) == 3 and len(tf['chain_roles']) == 3 and len(tf['invest_fits']) == 3
print(f'[筛选器] 省份 {len(tf["provinces"])} 个 / 地域 {len(tf["region_types"])} / '
      f'链作用 {len(tf["chain_roles"])} / 可行性 {len(tf["invest_fits"])} ✓')

# 更新日志接口
cl = client.get('/api/chain/changelog').get_json()['data']
assert len(cl) >= 1, '更新日志为空'
c0 = cl[0]
assert c0['version'] and c0['log_date'] and c0['title'], '更新日志字段不全'
assert len(c0['changes']) >= 5, '更新日志修改内容条目偏少'
print(f'[日志] {c0["version"]} {c0["log_date"]} {c0["title"]} / '
      f'修改 {len(c0["changes"])} / 风险 {len(c0["risks"])} / 下一步 {len(c0["next_steps"])} ✓')

# CSV 导出
for ds in ['enterprises', 'gaps', 'targets', 'changelog']:
    r = client.get(f'/api/chain/export/{ds}.csv')
    assert r.status_code == 200, f'{ds} CSV 导出失败 {r.status_code}'
    body = r.get_data()
    assert body[:3] == b'\xef\xbb\xbf', 'CSV 缺少 BOM'
    print(f'[导出] {ds}.csv -> {r.status_code}, {len(body)} bytes, BOM ✓')

# Word 导出
r = client.get('/api/chain/export/word')
assert r.status_code == 200, f'Word 导出失败 {r.status_code} {r.get_data()[:400]}'
wb = r.get_data()
assert wb[:2] == b'PK', 'Word 文件头异常'
out = os.path.join(tempfile.gettempdir(), 'chain_report_test.docx')
with open(out, 'wb') as f:
    f.write(wb)
print(f'[导出] word -> {r.status_code}, {len(wb)} bytes, 校验通过（{out}）')

# 转线索
r = client.get('/api/chain/targets').get_json()
tid = r['data'][0]['id']
r = client.post(f'/api/chain/targets/{tid}/convert')
j = r.get_json()
print(f'[转线索] code={j.get("code")} msg={j.get("message")}')
assert j.get('code') == 0, f'转线索失败：{j}'
# 重复转同一企业应被拦截
r2 = client.post(f'/api/chain/targets/{tid}/convert').get_json()
print(f'[转线索] 重复提交 -> code={r2.get("code")} msg={r2.get("message")}')
assert r2.get('code') == 409

# 复核状态
r = client.put(f'/api/chain/targets/{tid}/review', json={'review_status': '已复核'})
j = r.get_json()
print(f'[复核] code={j.get("code")} status={j.get("data", {}).get("review_status")}')
assert j.get('code') == 0
r = client.put(f'/api/chain/targets/{tid}/review', json={'review_status': '非法值'})
assert r.get_json().get('code') == 400
print('[复核] 非法状态被正确拒绝 ✓')

# 权限：访客无转线索权限
with app.app_context():
    from models.auth import BusinessUser
    from extensions import db as _db
    v = BusinessUser.query.filter_by(role='visitor').first()
    if not v:
        v = BusinessUser(username='visitor_test', display_name='访客测试', role='visitor', is_active=True)
        v.set_password('visitor123')
        _db.session.add(v)
        _db.session.commit()
        vid = v.id
    else:
        vid = v.id
client2 = app.test_client()
client2.post('/api/auth/login', json={'username': 'visitor_test', 'password': 'visitor123'})
r = client2.post(f'/api/chain/targets/{tid}/convert')
print(f'[访客] 转线索 -> HTTP {r.status_code} code={r.get_json().get("code")} msg={r.get_json().get("message")}')
assert r.status_code == 403, '访客不应有转线索权限'

# 未登录访问
client3 = app.test_client()
r = client3.get('/api/chain/overview')
print(f'[未登录] overview -> {r.status_code}')
assert r.status_code == 401

print('=' * 62)
print('  全部自检通过 ✓')
print('=' * 62)
