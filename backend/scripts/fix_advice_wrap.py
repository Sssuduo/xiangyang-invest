"""清理 advice.json / changelog.json 正文中的「排版折行」。

问题：写作时为控制字数宽度手工折行，单个 \\n 落在句子中间（如「…正大食品（襄阳）、湖北卧龙神厨、
襄阳正大种业、\\n湖北腾龙种业、…」）。前端把 \\n 渲染成 <br /> 硬换行，导致 1447px 宽的正文
每行只占约 500px，右侧留下大片空白。

行级判定：
  HEAD_FULL  整行被 ** 包裹（「**这是当前投入产出比最高的一项补链。**」）→ 独立成块
  LABEL      以「**标签**：」开头（「**谈判切入点**：卧龙神厨…」）→ 开启新块，后续正文并入该块
  LIST       以「· 」「• 」或「1. 」「2、」等编号开头，或以空格缩进开头 → 列表项 / 列表续行
  PROSE      其余普通正文

块合并规则：
  · 段内含 LIST 行 → 列表块，保留换行结构（续行缩进 2 空格形成悬挂缩进）
  · 否则 → 逐块输出：HEAD 独占一行；LABEL 独占一行且其后正文并入；其余 PROSE 合并为一行

用法：python backend/scripts/fix_advice_wrap.py [--check]
"""
import io
import json
import os
import re
import sys

BASE = r'H:\项目1\backend\chain_data'
BULLET = re.compile(r'^\s*[·•]\s*')
NUMITEM = re.compile(r'^\s*\d+\s*[.、)）]\s*')
HEAD_FULL = re.compile(r'^\s*\*\*[^*]+\*\*\s*$')
LABEL_START = re.compile(r'^\s*\*\*[^*]+\*\*\s*[：:]')


def kind(line, idx):
    s = line.strip()
    if not s:
        return 'EMPTY'
    if BULLET.match(s) or NUMITEM.match(s):
        return 'LIST'
    if HEAD_FULL.match(s):
        return 'HEAD'
    if LABEL_START.match(s):
        return 'LABEL'
    if idx > 0 and re.match(r'^\s{2,}\S', line):
        return 'LIST'   # 列表续行
    return 'PROSE'


def clean_list_block(lines):
    """列表块：保留换行结构，续行缩进 2 空格形成悬挂缩进。"""
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        is_new_item = bool(BULLET.match(s) or NUMITEM.match(s))
        if is_new_item:
            out.append(s)
        elif out:
            out.append('  ' + s)   # 续行
        else:
            out.append(s)
    return '\n'.join(out)


def clean_prose_block(lines):
    """散文块：LABEL 标签独占一行并吸收其后正文；HEAD 独占一行；其余合并为一行。

    LABEL 形如「**谈判切入点**：卧龙神厨、盼盼…」（标签后带冒号），
    其后的续行属同一标签的正文，应并入该标签行；
    下一个 LABEL 开启新块。因此最终每个 LABEL 恰好一行。
    """
    blocks = []   # 每项 = [kind, [行...]]
    for ln in lines:
        k = kind(ln, 0)
        s = ln.strip()
        if k == 'LABEL':
            blocks.append(['LABEL', [s]])
        elif k == 'HEAD':
            blocks.append(['HEAD', [s]])
        else:
            if blocks:
                blocks[-1][1].append(s)
            else:
                blocks.append(['PROSE', [s]])
    out = []
    for bk, body in blocks:
        if bk == 'LABEL':
            # 标签行 + 其后正文合并为一行（去掉标签冒号后的换行）
            out.append(''.join(body))
        elif bk == 'HEAD':
            out.append(body[0])
            rest = ''.join(body[1:])
            if rest:
                out.append(rest)
        else:
            out.append(''.join(body))
    return '\n'.join(out)


def clean_para(para):
    raw = para.split('\n')
    kinds = [kind(ln, i) for i, ln in enumerate(raw)]
    lines = [(ln, k) for ln, k in zip(raw, kinds) if k != 'EMPTY']
    if not lines:
        return ''
    if any(k == 'LIST' for _, k in lines):
        return clean_list_block([ln for ln, _ in lines])
    return clean_prose_block([ln for ln, _ in lines])


def clean_text(text):
    paras = re.split(r'\n{2,}', text or '')
    cleaned = [clean_para(p) for p in paras]
    return '\n\n'.join([p for p in cleaned if p])


def main():
    check_only = '--check' in sys.argv
    changed_total = 0
    for fname in ('advice.json', 'changelog.json'):
        path = os.path.join(BASE, fname)
        data = json.load(io.open(path, encoding='utf-8'))
        items = data if isinstance(data, list) else data.get('data', [])
        changed = 0
        for it in items:
            for key in ('content', 'summary'):
                if key not in it:
                    continue
                old = it[key] or ''
                new = clean_text(old)
                if new != old:
                    it[key] = new
                    changed += 1
        single = 0
        bullets = 0
        for it in items:
            c = it.get('content', '') or ''
            for p in re.split(r'\n{2,}', c):
                single += p.count('\n')
                bullets += len([x for x in p.split('\n') if BULLET.match(x) or NUMITEM.match(x)])
        print(f'{fname}: 处理 {changed} 个字段，改后段内剩余换行 {single} 处，列表条目 {bullets} 条')
        changed_total += changed
        if not check_only and changed:
            with io.open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(items, ensure_ascii=False, indent=2))
    if check_only:
        print('（--check 模式，未写盘）')
    else:
        print(f'共处理 {changed_total} 个字段')


if __name__ == '__main__':
    main()
