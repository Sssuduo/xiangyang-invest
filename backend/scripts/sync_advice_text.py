# -*- coding: utf-8 -*-
"""同步招商建议文案：随目标企业库扩容更新家数与表述。

变更点：
  1. 缺口 1/3/4/9 目标企业由原 9/7/9/3 家扩至各 20 家 → 更新 kv 与正文表述
  2. 总体判断 kv 中「目标企业 131 家」→ 183 家
  3. 下一步工作中的「投资可行性高（25 家）与强链目标（26 家）」→ 55 / 33
  4. 修正建议条目与缺口的关联（方向九应对应纺织 gap 11，而非 gap 9）
     —— advice.gap_id 语义为「建议序号」，其中方向八合并两个缺口、方向九对应 TEXTILE，
        原值与缺口 id 存在错位，此处按语义重排为真实 gap_id
  5. 风险提示补充本轮新纳入标的中已核实的风险事项

用法：python backend/scripts/sync_advice_text.py [--check]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', 'chain_data'))
ADVICE = os.path.join(DATA, 'advice.json')
GAPS = os.path.join(DATA, 'gaps.json')
TARGETS = os.path.join(DATA, 'targets.json')


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(p, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    check = '--check' in sys.argv
    advice = load(ADVICE)
    gaps = load(GAPS)
    targets = load(TARGETS)

    gap_by_node = {g['node_code']: g for g in gaps}
    cnt_by_gap = {}
    for t in targets:
        cnt_by_gap[t['gap_id']] = cnt_by_gap.get(t['gap_id'], 0) + 1

    total = len(targets)
    high_fit = sum(1 for t in targets if t['invest_fit_level'] == '高')
    strong = sum(1 for t in targets if t['chain_role'] == '强链')
    outprov = sum(1 for t in targets if t.get('region_type') == '省外')

    changes = []

    # ---------- 1. 修正 gap_id 与缺口的关联 ----------
    # advice.gap_id 原本被当作「建议序号」使用，导致与缺口 id 错位：
    #   方向八合并 BIOMAT + BIOMED 两个缺口
    #   方向九对应 TEXTILE（gap 11），原值 9 指向 FUNC
    #   风险提示 / 下一步工作不对应具体缺口（用 -1 标记）
    FIX_GAP_ID = {8: 8, 9: 11, 10: -1, 11: -1}
    for a in advice:
        old = a['gap_id']
        if old in FIX_GAP_ID:
            new = FIX_GAP_ID[old]
            if new != old:
                changes.append('gap_id %d → %d（%s）' % (old, new, a['title'][:22]))
                a['gap_id'] = new

    # ---------- 1b. 显式排序字段 ----------
    # 原先 sort_order 直接取 gap_id，gap_id 改为 -1 后风险提示/下一步会排到最前。
    # 此处按 advice.json 中的原始出现顺序固定排序。
    for i, a in enumerate(advice):
        if a.get('sort_order') != i:
            a['sort_order'] = i
            changes.append('sort_order → %d（%s）' % (i, a['title'][:22]))

    # ---------- 2. kv 中的目标企业家数 ----------
    for a in advice:
        gid = a['gap_id']
        if gid in cnt_by_gap:
            n = cnt_by_gap[gid]
            old_kv = a.get('kv', '')
            new_kv = re.sub(r'目标企业 \d+ 家(?! /)', '目标企业 %d 家' % n, old_kv, count=1)
            # 「7 家 / 7 家」形式（方向八合并两个缺口）保持双数
            if new_kv != old_kv:
                changes.append('kv 家数：%s → %s' % (old_kv[:26], new_kv[:26]))
                a['kv'] = new_kv

    # ---------- 3. 总体判断 kv：目标企业总数 ----------
    for a in advice:
        if a['gap_id'] == 0:
            old = a.get('kv', '')
            new = re.sub(r'目标企业 \d+ 家', '目标企业 %d 家' % total, old)
            if new != old:
                changes.append('总体判断 kv：目标企业 → %d 家' % total)
                a['kv'] = new
            break

    # ---------- 4. 下一步工作：可行性高 / 强链家数 ----------
    for a in advice:
        if a['gap_id'] == -1 and '下一步工作' in a.get('title', ''):
            c = a.get('content', '')
            new = c
            new = re.sub(r'投资可行性高（\d+ 家）', '投资可行性高（%d 家）' % high_fit, new)
            new = re.sub(r'强链目标（\d+ 家）', '强链目标（%d 家）' % strong, new)
            if new != c:
                changes.append('下一步工作：可行性高 → %d 家，强链 → %d 家' % (high_fit, strong))
                a['content'] = new

    # ---------- 5. 风险提示：补充本轮新纳入标的的已核实风险 ----------
    risk_added = False
    for a in advice:
        if a['gap_id'] == -1 and '风险提示' in a.get('title', ''):
            c = a.get('content', '')
            extra = []
            # 四川美味源：2026 年两次超限量使用甜蜜素被罚
            if '四川美味源食品' not in c:
                extra.append(
                    '· **四川美味源食品**：2026 年 8 月、9 月两度因苗家酸汤复合调味料甜蜜素超限量被罚'
                    '（合计罚没约 14 万元）并召回涉事批次，同期因使用近似标识被罚 4.5 万元，'
                    '质量管控稳定性存疑；\n')
            # 田野创新：*ST 退市风险警示
            if '田野创新' not in c:
                extra.append(
                    '· **田野创新**：2026 年 4 月起股票简称变更为「*ST田野」，'
                    '2025 年度财报被出具无法表示意见、内控被出具否定意见，且因涉嫌信息披露违法违规被证监会立案，'
                    '存在终止上市风险；\n')
            if extra:
                marker = '**四项结构性风险：**'
                if marker in c:
                    c = c.replace(marker, ''.join(extra) + '\n' + marker, 1)
                    a['content'] = c
                    changes.append('风险提示：补充 2 家新纳入标的风险事项')
                    risk_added = True
            break

    # ---------- 6. 四个扩容缺口：正文补充新增标的线索 ----------
    NEW_HIGHLIGHT = {
        1: ('· **仲景食品**（300908.SZ）以香菇酱与调味配料双线运营，'
            '配料端以超临界二氧化碳萃取产出花椒油、辣椒油、藤椒精油等天然香辛料提取物，'
            '2025 年华中地区收入 3.93 亿元居各区域首位，可就地消化本地香辛料作物；\n'),
        3: ('· **上海雪榕**（300511.SZ）、**江苏华绿**、**山东七河**等工厂化食用菌企业已具备规模化种植与加工能力，'
            '可为本地菌菇原料提供从种植到深加工的成套输出；\n'),
        4: ('· **河南银金达彩印**、**四川美丰高分子**、**河南卫华包装**等具备食品级复合膜与塑料包装产能，'
            '其中银金达 2025 年营收约 30 亿元，具备在华中落位分厂的规模基础；\n'),
        9: ('· **仙乐健康**、**青岛蔚蓝生物**、**汤臣倍健**、**北京科拓恒通**等覆盖保健食品、益生菌、'
            '膳食纤维与功能糖醇，与本地果蔬、菌类原料形成功能化加工延伸；\n'),
    }
    for a in advice:
        gid = a['gap_id']
        if gid in NEW_HIGHLIGHT:
            c = a.get('content', '')
            if NEW_HIGHLIGHT[gid].split('**')[1] not in c:
                # 插到「谈判切入点」之前
                for marker in ('**谈判切入点**', '**承载条件**'):
                    if marker in c:
                        c = c.replace(marker, NEW_HIGHLIGHT[gid] + marker, 1)
                        changes.append('方向 %d：补充新增标的线索' % gid)
                        a['content'] = c
                        break

    print('目标企业 %d 家 / 省外 %d / 可行性高 %d / 强链 %d' % (
        total, outprov, high_fit, strong))
    print()
    for c in changes:
        print('  · %s' % c)
    if not changes:
        print('  （无变化）')

    # ---------- 校验 ----------
    errors = []
    for a in advice:
        if a['gap_id'] > 0:
            g = next((x for x in gaps if x['gap_id'] == a['gap_id']), None)
            if g is None:
                errors.append('建议「%s」关联的缺口 %d 不存在' % (a['title'][:20], a['gap_id']))
            else:
                # 标题中的分数应与缺口一致
                m = re.search(r'（(\d+) 分', a['title'])
                if m and int(m.group(1)) not in (g['total_score'],):
                    other = [x['total_score'] for x in gaps
                             if x['total_score'] == int(m.group(1))]
                    if not other:
                        errors.append('建议「%s」分数 %s 与缺口 %d 的 %d 分不一致' % (
                            a['title'][:20], m.group(1), a['gap_id'], g['total_score']))
        kv = a.get('kv', '')
        m = re.search(r'目标企业 (\d+) 家', kv)
        if m and a['gap_id'] in cnt_by_gap and int(m.group(1)) != cnt_by_gap[a['gap_id']]:
            errors.append('建议「%s」kv 家数 %s ≠ 实际 %d' % (
                a['title'][:20], m.group(1), cnt_by_gap[a['gap_id']]))

    print()
    if errors:
        print('校验未通过：')
        for e in errors:
            print('  ! %s' % e)
        sys.exit(1)
    print('校验通过 ✓')

    if check:
        print('\n[check] 未写入')
        return
    save(ADVICE, advice)
    print('\n已写入 %s' % ADVICE)


if __name__ == '__main__':
    main()
