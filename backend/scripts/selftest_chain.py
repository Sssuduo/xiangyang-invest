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
    from models.chain import ChainAdvice, ChainEnterprise, ChainGap, ChainNode, ChainTarget
    print(f'[表] 环节 {ChainNode.query.count()} / 企业 {ChainEnterprise.query.count()} '
          f'/ 缺口 {ChainGap.query.count()} / 目标 {ChainTarget.query.count()} '
          f'/ 建议 {ChainAdvice.query.count()}')
    assert ChainNode.query.count() == 26, '环节数不对（应为 26）'
    assert ChainEnterprise.query.count() == 62, '企业数不对（应为 62）'
    assert ChainGap.query.count() == 13, '缺口数不对（应为 13）'
    assert ChainTarget.query.count() == 102, '目标企业数不对（应为 102）'
    assert ChainAdvice.query.count() == 12, '建议数不对（应为 12）'

    # 招商引资：襄州区属地目标企业必须为 0
    xz_local = ChainTarget.query.filter_by(is_xiangzhou_local=True).count()
    assert xz_local == 0, f'襄州区属地目标企业应为 0，实际 {xz_local}'
    print('[约束] 襄州区属地目标企业 0 家 ✓')

    # 省外企业须为主体
    outprov = ChainTarget.query.filter_by(region_type='省外').count()
    assert outprov >= 60, f'省外目标企业偏少：{outprov}'
    print(f'[约束] 省外目标企业 {outprov} 家 ✓')

    # 六因子：冷链优先级必须被压低（不得进入前五）
    gaps_all = ChainGap.query.order_by(ChainGap.sort_order).all()
    cold = next((g for g in gaps_all if g.node_code == 'COLD'), None)
    assert cold is not None, '缺少冷链环节缺口'
    rank = next(i for i, g in enumerate(gaps_all, 1) if g.id == cold.id)
    assert rank > 5, f'冷链优先级仍过高（第 {rank} 位）'
    print(f'[约束] 冷链优先级第 {rank} 位 / {cold.total_score} 分，未进前五 ✓')

    # 六因子分项满分校验
    assert cold.f6 is not None, '缺口缺少 F6 企业实力因子'
    assert ChainGap.query.filter_by(node_code='COLD').first().f6 >= 0

    # 幂等性：再跑一次不应重复写入
    from chain_seed import seed_chain_data
    seed_chain_data(app)
    assert ChainEnterprise.query.count() == 62, '重复初始化！'
    assert ChainTarget.query.count() == 102, '目标企业重复初始化！'
    print('[幂等] 重复执行 seed_chain_data 后数据未翻倍 ✓')

client = app.test_client()

# 登录 demo 账号拿 session
res = client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo123'})
print(f'[登录] code={res.get_json().get("code")}')
assert res.get_json().get('code') == 0, 'demo 登录失败'

for path in ['/api/chain/overview', '/api/chain/nodes', '/api/chain/enterprises',
             '/api/chain/gaps', '/api/chain/targets', '/api/chain/advice',
             '/api/chain/target-filters']:
    r = client.get(path)
    j = r.get_json()
    assert j.get('code') == 0, f'{path} 返回异常：{j}'
    d = j.get('data')
    n = len(d) if isinstance(d, list) else 'obj'
    print(f'[GET] {path:28s} -> {r.status_code}  条目 {n}')

# overview 新字段
ov = client.get('/api/chain/overview').get_json()['data']
assert ov['outprov_target_count'] >= 60, 'overview 省外目标数异常'
assert ov['xiangzhou_local_count'] == 0, 'overview 襄州区属地数应为 0'
assert ov['high_fit_count'] > 0, 'overview 可行性高企业数为 0'
assert len(ov['rules']['factors']) == 6, '优先级因子应为 6 个'
assert len(ov['rules']['strength_factors']) == 5, '企业实力维度应为 5 个'
assert len(ov['rules']['chain_roles']) == 3, '链作用分类应为 3 类'
assert len(ov['rules']['invest_fit']) == 3, '投资可行性分档应为 3 档'
print(f"[概览] 省外 {ov['outprov_target_count']} / 可行性高 {ov['high_fit_count']} / "
      f"本地企业均实力 {ov['strength_avg']} / 六因子 ✓")

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
assert len(r['data']) >= 60, '省外筛选结果偏少'
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

# CSV 导出
for ds in ['enterprises', 'gaps', 'targets']:
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
