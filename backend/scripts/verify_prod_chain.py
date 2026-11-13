"""生产环境端到端验证：登录 → 拉取全量数据 → 导出 → 转线索闭环。

用法：python backend/scripts/verify_prod_chain.py [BASE_URL]
默认 BASE_URL = http://123.56.9.243
"""
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://123.56.9.243').rstrip('/')

jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def req(path, method='GET', body=None, raw=False):
    # URL 里的中文参数必须程序化编码（手拼会触发 ascii 编码错误）
    if '?' in path:
        base, qs = path.split('?', 1)
        parts = []
        for kv in qs.split('&'):
            if '=' in kv:
                k, v = kv.split('=', 1)
                parts.append(f'{urllib.parse.quote(k)}={urllib.parse.quote(v)}')
            else:
                parts.append(urllib.parse.quote(kv))
        path = base + '?' + '&'.join(parts)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        r.add_header('Content-Type', 'application/json')
    try:
        with opener.open(r, timeout=30) as resp:
            payload = resp.read()
            if raw:
                return resp.status, payload
            return resp.status, json.loads(payload.decode('utf-8'))
    except urllib.error.HTTPError as e:
        payload = e.read()
        if raw:
            return e.code, payload
        try:
            return e.code, json.loads(payload.decode('utf-8'))
        except Exception:
            return e.code, payload[:300]


print('=' * 60)
print('  生产环境产业链招商端到端验证')
print('  目标:', BASE)
print('=' * 60)

# 1. 登录
st, j = req('/api/auth/login', 'POST', {'username': 'demo', 'password': 'demo123'})
print(f'[登录] HTTP {st} code={j.get("code")} 用户={j.get("data", {}).get("display_name")}')
if j.get('code') != 0:
    print('  ✗ 登录失败，终止')
    sys.exit(1)
perms = j.get('data', {}).get('permissions', {})
print(f'  权限模块: {sorted(perms.keys())}')
print(f'  chain 权限: {perms.get("chain")}')

# 2. 全量数据
for path, label in [
    ('/api/chain/overview', '总览'),
    ('/api/chain/nodes', '环节'),
    ('/api/chain/enterprises', '企业'),
    ('/api/chain/gaps', '缺口'),
    ('/api/chain/targets', '目标企业'),
    ('/api/chain/advice', '招商建议'),
]:
    st, j = req(path)
    d = j.get('data')
    n = len(d) if isinstance(d, list) else 'obj'
    print(f'[接口] {label:6s} HTTP {st} code={j.get("code")} 条目={n}')
    if j.get('code') != 0:
        print('  ✗ 异常:', j)
        sys.exit(1)

# 3. 总览关键指标
st, j = req('/api/chain/overview')
ov = j['data']
print(f'\n[指标] 企业 {ov["enterprise_count"]} / 环节 {ov["node_count"]} / '
      f'缺口 {ov["gap_count"]} / 目标 {ov["target_count"]} / 市域内 {ov["local_target_count"]}')
print(f'[指标] 层级分布: ' + ' | '.join(
    f'{x["layer"]}{x["enterprise_count"]}家/{x["gap_count"]}缺口' for x in ov['layer_stats']))
print(f'[指标] 优先级分布: ' + ' | '.join(
    f'{x["level"]}{x["gap_count"]}缺口/{x["target_count"]}目标' for x in ov['level_stats']))
print(f'[指标] 规则: {len(ov["rules"]["factors"])} 因子 / {len(ov["rules"]["levels"])} 档 / 否决规则已下发')

# 4. 筛选
st, j = req('/api/chain/targets?is_local=1')
print(f'\n[筛选] 市域内已有目标企业 {len(j["data"])} 家')
st, j = req('/api/chain/enterprises?layer=中游')
print(f'[筛选] 中游企业 {len(j["data"])} 家')

# 5. 导出
print()
for ds in ['enterprises', 'gaps', 'targets']:
    st, body = req(f'/api/chain/export/{ds}.csv', raw=True)
    bom = body[:3] == b'\xef\xbb\xbf'
    print(f'[导出] {ds}.csv HTTP {st} {len(body)} bytes BOM={"✓" if bom else "✗"}')
    assert st == 200 and bom

st, body = req('/api/chain/export/word', raw=True)
print(f'[导出] word HTTP {st} {len(body)} bytes 头={body[:2]}')
assert st == 200 and body[:2] == b'PK'

# 6. 目标企业详情（找一条待复核的）
st, j = req('/api/chain/targets')
t = j['data'][0]
print(f'\n[目标] {t["name"]} | {t["region"]} | 匹配 {t["total_score"]} 分 | {t["gap_title"]}')
print(f'  来源: {t["source_url"][:70]}')
print(f'  依据: {t["evidence"][:80]}...')

# 7. 复核状态流转（只改一条，复原）
st, j = req(f'/api/chain/targets/{t["id"]}/review', 'PUT', {'review_status': '已复核'})
print(f'\n[复核] HTTP {st} code={j.get("code")} → {j.get("data", {}).get("review_status")}')
assert j.get('code') == 0
st, j = req(f'/api/chain/targets/{t["id"]}/review', 'PUT', {'review_status': '待复核'})
print(f'[复核] 复原 HTTP {st} → {j.get("data", {}).get("review_status")}')

# 8. 转线索闭环（用一个目标企业试，然后不再重复）
st, j = req(f'/api/chain/targets/{t["id"]}/convert', 'POST')
print(f'\n[转线索] HTTP {st} code={j.get("code")} msg={j.get("message")}')
if j.get('code') == 0:
    lead_id = j['data']['lead_id']
    st2, j2 = req(f'/api/admin/lead/leads/{lead_id}')
    print(f'[转线索] 回读线索 #{lead_id} HTTP {st2} 企业={j2.get("data", {}).get("invest_enterprise")}')
    st3, j3 = req('/api/admin/lead/leads?page=1&per_page=5')
    items = j3.get('data') if isinstance(j3.get('data'), list) else (j3.get('data') or {}).get('items', [])
    print(f'[转线索] 线索列表 HTTP {st3} 返回 {len(items)} 条')
elif j.get('code') == 409:
    print('  （已存在线索，属预期幂等行为）')

print('\n' + '=' * 60)
print('  生产端到端验证通过 ✓')
print('=' * 60)
