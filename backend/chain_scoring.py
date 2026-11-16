# -*- coding: utf-8 -*-
"""产业链招商评分公式（仓内唯一来源）

两套评分体系：

一、企业实力五维（0-100 分）—— 用于目标企业与本地企业的「企业实力」分，
   也作为缺口优先级 F6 因子的判断依据：
       注册资本 25 + 营收规模 25 + 财报趋势 15 + 融资与投资 20 + 投资签约 15

二、六因子百分制加权（0-100 分）—— 目标企业匹配总分：
       total = round(f1×0.25 + f2×0.20 + f3×0.20 + f4×0.10 + f5×0.10 + f6×0.15)

说明：
- 全部字段来自公开工商、年报与公开报道；查不到的字段一律按「无数据」档取值，
  不做推测、不填 0，避免与「确认为 0」混淆。
- 本文件与采集脚本 G:/123/chain_work/build_targets2.py 的实现保持一致，
  由 selftest_chain.py 回算库内全部记录比对差异（应为 0）。
"""

# 企业实力五维的上限
STRENGTH_MAX = {
    'capital': 25,   # 注册资本
    'revenue': 25,   # 营收规模
    'trend': 15,     # 财报趋势
    'funding': 20,   # 融资与投资
    'signed': 15,    # 投资签约
}

# 目标企业六因子在「匹配总分」中的加权系数
TARGET_WEIGHTS = {
    'f1': 0.25, 'f2': 0.20, 'f3': 0.20,
    'f4': 0.10, 'f5': 0.10, 'f6': 0.15,
}


def score_strength(rec):
    """企业实力五维评分（0-100 分）。

    rec 需具备：reg_capital / revenue_3y / netprofit_3y /
    funding / investments / signed_deal 六个字段。
    返回 (总分, 各维度得分字典)。
    """
    rc = rec.get('reg_capital')
    # 注册资本为 0 不是合法登记值，与「未披露」同义，统一记 8 分
    s_cap = 8 if (rc is None or rc <= 0) else 25 if rc >= 10000 else 21 if rc >= 5000 else \
        17 if rc >= 2000 else 13 if rc >= 1000 else 9 if rc >= 500 else 5
    rev = rec.get('revenue_3y')
    s_rev = 6
    if rev:
        nums = []
        for part in str(rev).split(';'):
            try:
                nums.append(float(part.split(':')[1].replace('万', '').replace('亿', '')))
            except Exception:
                pass
        if nums:
            top = max(nums)
            s_rev = 25 if top >= 100000 else 21 if top >= 50000 else 17 if top >= 10000 else \
                13 if top >= 3000 else 9 if top >= 1000 else 6
    s_trend = 10 if (rec.get('netprofit_3y') or rev) else 8
    s_fund = 5
    if rec.get('funding'):
        s_fund = 15
        if rec.get('investments'):
            s_fund = 20
    s_signed = 4
    if rec.get('signed_deal'):
        s_signed = 15
    elif rec.get('investments'):
        s_signed = 11
    total = s_cap + s_rev + s_trend + s_fund + s_signed
    return total, {'capital': s_cap, 'revenue': s_rev, 'trend': s_trend,
                   'funding': s_fund, 'signed': s_signed}


def target_scores(node_code, role, fit, ml, strength):
    """目标企业六因子百分制评分。

    role 链作用（补链/延链/强链）、fit 投资可行性（高/中/低）、
    ml 可对接本地链主列表、strength 企业实力五维总分。
    返回 (各因子得分字典, 匹配总分)。
    """
    f1 = {'补链': 90, '延链': 80, '强链': 86}.get(role, 76)
    f2 = 84 if fit == '高' else 72 if fit == '中' else 55
    f3 = {'补链': 88, '延链': 78, '强链': 84}.get(role, 76)
    f4 = 86 if len(ml) >= 2 else 80 if ml else 70
    f5 = {'高': 88, '中': 70, '低': 50}.get(fit, 65)
    f6 = strength
    total = round(f1 * 0.25 + f2 * 0.20 + f3 * 0.20 + f4 * 0.10 + f5 * 0.10 + f6 * 0.15)
    return {'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4, 'f5': f5, 'f6': f6}, total
