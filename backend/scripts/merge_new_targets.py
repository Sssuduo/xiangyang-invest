# -*- coding: utf-8 -*-
"""将新增采集的目标企业并入 targets.json。

用途：把缺口 1（食品添加与调味）/ 3（果蔬与食用菌深加工）/ 4（食品级高端包装）/
9（功能性营养食品）四个缺口的候选企业扩充到各 20 家。

步骤：
  1. 读取已入库 targets.json 作为基线
  2. 读取本轮采集的 5 个批次文件
  3. 规范化链主名称（与 ent90.json 对齐）、修正个别注册资本、剔除跨缺口重复项
  4. 复用 build_targets2 的实力评分与六因子评分（与库内 131 家口径完全一致）
  5. 每个目标缺口按总分保留前 N 家，其余保留原样
  6. 写回 targets.json 并打印校验报告

用法：
    python backend/scripts/merge_new_targets.py [--dry-run]
"""
import json
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', 'chain_data'))
WORK = r'G:/123/chain_work'
sys.path.insert(0, WORK)

from build_targets2 import score_strength, target_scores  # noqa: E402

TARGETS = os.path.join(DATA, 'targets.json')
ENT90 = os.path.join(DATA, 'ent90.json')
GAPS = os.path.join(DATA, 'gaps.json')

# 本轮采集批次：文件名 → 目标缺口（按 node_code 归属）
BATCHES = {
    'new_addi_11.json': 'ADDI',
    'new_veg_13.json': 'VEG',
    'new_pack_11.json': 'PACK',
    'new_func_17.json': 'FUNC',
    'new_func_extra.json': 'FUNC',
}

# 目标缺口 → 期望家数
TARGET_COUNT = {1: 20, 3: 20, 4: 20, 9: 20}

# 链主名称对齐（ent90.json 中的规范名称）
NAME_FIX = {
    '襄阳市郭襄食品有限公司': '湖北郭襄食品有限公司',
    '襄阳郭襄食品有限公司': '湖北郭襄食品有限公司',
    '湖北正大农牧食品有限公司': '襄阳正大农牧食品有限公司',
    '襄阳市乐峰粮油有限公司': '襄阳乐峰粮油有限公司',
    '湖北三珍生态农业有限公司': '襄阳三珍生态农业有限公司',
    '湖北华中农食科技集团有限公司': '华中农食（湖北省）生物科技有限公司',
}

# 个别注册资本修正（采集时取值有误，按工商信息订正）
CAPITAL_FIX = {
    '青岛海德包装股份有限公司': 6451,   # 工商登记 6451 万元（原稿误填 0）
}

# 明确不并入的采集项：已在其它缺口入库，或与本轮口径不符
SKIP_NAMES = {
    # 已作为 gap 8 生物基材料入库（DIOMAT 链主，功能糖/膳食纤维归生物基环节更准确）
    '山东百龙创园生物科技股份有限公司',
    # 已作为 gap 10 乳制品入库
    '君乐宝乳业集团股份有限公司',
}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    dry = '--dry-run' in sys.argv

    targets = load(TARGETS)
    ent_names = {e['name'] for e in load(ENT90)}
    gaps = load(GAPS)
    gap_of_node = {g['node_code']: g['gap_id'] for g in gaps}

    by_name = {t['name']: t for t in targets}
    print('基线已入库目标企业：%d 家' % len(targets))

    added = []
    skipped_dup = []
    for fn, node in BATCHES.items():
        path = os.path.join(WORK, fn)
        if not os.path.exists(path):
            print('  ! 批次文件缺失，跳过：%s' % fn)
            continue
        batch = load(path)
        for rec in batch:
            name = rec['name']
            if name in SKIP_NAMES:
                skipped_dup.append((name, '已在其它缺口入库'))
                continue
            if name in by_name:
                skipped_dup.append((name, '与已入库重复'))
                continue
            if rec.get('node_code') != node:
                skipped_dup.append((name, 'node_code 不符'))
                continue
            if rec.get('region_type') != '省外':
                skipped_dup.append((name, '非省外企业'))
                continue
            t = dict(rec)
            t['gap_id'] = gap_of_node[node]
            # 链主名称对齐
            ml = []
            for m in (t.get('match_local_chain') or []):
                fixed = NAME_FIX.get(m, m)
                if fixed not in ent_names:
                    print('  ! 链主不存在，已剔除：%s / %s' % (name, fixed))
                    continue
                ml.append(fixed)
            t['match_local_chain'] = ml
            # 注册资本订正
            if name in CAPITAL_FIX:
                t['reg_capital'] = CAPITAL_FIX[name]
            t.pop('is_xiangzhou_local', None)
            t.setdefault('confidence', 'medium')
            by_name[name] = t
            added.append(t)

    print('新增候选：%d 家' % len(added))
    for name, why in skipped_dup:
        print('  - 跳过 %s（%s）' % (name, why))

    # 评分（与库内 131 家完全一致的公式）
    for t in added:
        st, detail = score_strength(t)
        t['strength'] = st
        t['strength_detail'] = detail
        sc, total = target_scores(t['node_code'], t.get('chain_role') or '补链',
                                  t.get('invest_fit_level') or '中',
                                  t.get('match_local_chain') or [], st)
        t['scores'] = sc
        t['total_score'] = total

    # 合并池：已有 + 新增
    pool = list(targets) + added
    added_names = {t['name'] for t in added}

    # 目标缺口保留全部存量企业（部分已在招商建议文案中被点名），
    # 新增企业按总分排序补足到目标家数；其余缺口原样保留
    keep = []
    drop = []
    pool_by_gap = collections.defaultdict(list)
    for t in pool:
        pool_by_gap[t['gap_id']].append(t)
    for gid, items in pool_by_gap.items():
        if gid in TARGET_COUNT:
            exist = [t for t in items if t['name'] not in added_names]
            fresh = [t for t in items if t['name'] in added_names]
            fresh.sort(key=lambda x: (-x['total_score'], x['name']))
            need = TARGET_COUNT[gid] - len(exist)
            keep.extend(exist)
            keep.extend(fresh[:need])
            drop.extend(fresh[need:])
        else:
            keep.extend(items)

    keep.sort(key=lambda x: (-x['total_score'], x['name']))

    print()
    print('合并后总数：%d 家（淘汰 %d 家）' % (len(keep), len(drop)))
    for t in drop:
        print('  - 落选 %s（%s，总分 %d）' % (t['name'][:26], t['gap_id'], t['total_score']))

    # ---------- 校验 ----------
    errors = []
    gc = collections.Counter(t['gap_id'] for t in keep)
    for gid, want in TARGET_COUNT.items():
        if gc.get(gid, 0) != want:
            errors.append('缺口 %d 期望 %d 家，实际 %d 家' % (gid, want, gc.get(gid, 0)))
    names = [t['name'] for t in keep]
    if len(names) != len(set(names)):
        dup = [n for n, c in collections.Counter(names).items() if c > 1]
        errors.append('存在重名企业：%s' % dup)
    # 新增企业必须全部为省外；存量企业沿用原有地域分类不动
    added_names = {t['name'] for t in added}
    for t in keep:
        if t['name'] in added_names:
            if t.get('region_type') != '省外':
                errors.append('新增 %s 非省外' % t['name'])
            if t.get('is_xiangzhou_local'):
                errors.append('新增 %s 标记为襄州区属地' % t['name'])
        if len(t.get('source_links') or []) < 3:
            errors.append('%s 来源链接不足 3 条' % t['name'])
        for m in (t.get('match_local_chain') or []):
            if m not in ent_names:
                errors.append('%s 链主不存在：%s' % (t['name'], m))
        for k in ('scores', 'strength_detail'):
            if not t.get(k):
                errors.append('%s 缺字段 %s' % (t['name'], k))
        if not t.get('total_score'):
            errors.append('%s 总分为 0' % t['name'])
    # 评分公式回算校验
    for t in keep:
        st, det = score_strength(t)
        sc, total = target_scores(t['node_code'], t.get('chain_role') or '补链',
                                  t.get('invest_fit_level') or '中',
                                  t.get('match_local_chain') or [], st)
        if sc != t['scores'] or total != t['total_score']:
            errors.append('%s 评分不一致' % t['name'])
            break

    print()
    if errors:
        print('校验未通过：')
        for e in errors[:20]:
            print('  ! %s' % e)
    else:
        print('校验通过 ✓')

    print()
    print('各缺口目标企业数：')
    for g in gaps:
        print('  #%2d %-24s %2d 家' % (g['gap_id'], g['title'][:24], gc.get(g['gap_id'], 0)))
    print()
    print('四个目标缺口前 5：')
    for gid in sorted(TARGET_COUNT):
        print('  缺口 %d：' % gid)
        for t in sorted(pool_by_gap[gid], key=lambda x: -x['total_score'])[:5]:
            print('    %3d %-30s %-4s 强链%-3d %s' % (
                t['total_score'], t['name'][:30], t.get('chain_role'),
                t['strength'], t.get('province')))

    if dry:
        print('\n[dry-run] 未写入文件')
        return
    if errors:
        print('\n存在校验错误，拒绝写入')
        return

    with open(TARGETS, 'w', encoding='utf-8') as f:
        json.dump(keep, f, ensure_ascii=False, indent=1)
    print('\n已写入 %s' % TARGETS)


if __name__ == '__main__':
    main()
