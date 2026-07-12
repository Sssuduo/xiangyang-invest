"""
研判报告 HTML 生成服务

将 LLM 返回的 Markdown 文本解析后，嵌入纯静态 HTML 模板，
生成单个 HTML 文件，无需任何外部 CDN 依赖，可直接在任何设备打开。
"""
import re
import os
from datetime import datetime


def generate_assessment_html(lead_name, enterprise_name, assessment_text):
    """将 AI 研判结果生成纯静态 HTML 报告

    Args:
        lead_name: 项目名称
        enterprise_name: 企业名称
        assessment_text: LLM 返回的 Markdown 文本

    Returns:
        tuple: (file_url, file_name)
    """
    out_dir = _ensure_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', lead_name)[:40]
    file_name = f'{safe_name}_AI研判报告_{timestamp}.html'
    file_path = os.path.join(out_dir, file_name)

    # 解析 Markdown
    sections = _parse_markdown(assessment_text)

    # 提取金额数据（用于饼图纯 CSS 替代）
    chart_data = _extract_chart_data(sections)

    # 渲染 HTML
    body_html = _render_sections(sections)
    chart_html = _render_chart(chart_data) if chart_data else ''
    report_date = datetime.now().strftime('%Y年%m月%d日 %H:%M')

    html = _build_full_html(lead_name, enterprise_name, report_date, chart_html, body_html)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

    static_url = f'/static/assessments/{file_name}'
    return static_url, file_name


def _ensure_dir():
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'assessments')
    os.makedirs(base, exist_ok=True)
    return base


# ============================================================
# Markdown 解析
# ============================================================

def _parse_markdown(text):
    """将 Markdown 文本解析为结构化的 sections 列表"""
    lines = text.strip().split('\n')
    sections = []
    pending = []

    def flush():
        nonlocal pending
        if pending:
            sections.append({'type': 'paragraph', 'content': '\n'.join(pending)})
            pending = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        # 分隔线
        if re.match(r'^[━═\-*_]{5,}$', stripped):
            flush()
            sections.append({'type': 'separator', 'content': ''})
            continue

        # H1: # xxx 或 一、二、...
        if stripped.startswith('# ') and not stripped.startswith('## '):
            flush()
            sections.append({'type': 'h1', 'content': _strip_md(stripped[2:])})
            continue
        if re.match(r'^[一二三四五六七八九十]、', stripped):
            flush()
            sections.append({'type': 'h1', 'content': _strip_md(stripped)})
            continue

        # H2: ## xxx 或 1. **xxx**
        if stripped.startswith('## '):
            flush()
            sections.append({'type': 'h2', 'content': _strip_md(stripped[3:])})
            continue
        m = re.match(r'^\d+[\.\、]?\s*\*\*(.+)\*\*', stripped)
        if m and len(stripped) < 150:
            flush()
            sections.append({'type': 'h2', 'content': _strip_md(m.group(1))})
            continue
        # 数字编号 H2: **推荐等级** 等加粗短行
        if stripped.startswith('**') and len(stripped) < 80 and stripped.endswith('**'):
            flush()
            sections.append({'type': 'h2', 'content': _strip_md(stripped)})
            continue

        # 表格行
        if stripped.startswith('|') and stripped.endswith('|') and not re.match(r'^\|[-: ]+\|', stripped):
            flush()
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            sections.append({'type': 'table_row', 'content': cells})
            continue

        # 列表项: - xxx 或 * xxx
        if re.match(r'^[-*]\s+', stripped):
            pending.append(stripped)
            continue

        # 加粗小标题行（短行 + **包裹）
        if stripped.startswith('**') and len(stripped) < 120 and '**' in stripped[2:]:
            flush()
            sections.append({'type': 'bold_label', 'content': _strip_md(stripped)})
            continue

        pending.append(stripped)

    flush()

    # 合并连续 table_row 为 table
    merged = []
    temp_table = []
    for s in sections:
        if s['type'] == 'table_row':
            temp_table.append(s['content'])
        else:
            if temp_table:
                merged.append({'type': 'table', 'content': temp_table})
                temp_table = []
            merged.append(s)
    if temp_table:
        merged.append({'type': 'table', 'content': temp_table})

    return merged


def _strip_md(text):
    """移除行内 Markdown 标记"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    return text


# ============================================================
# 数据提取
# ============================================================

_CHART_COLORS = [
    '#3b82f6', '#f59e0b', '#10b981', '#f43f5e', '#a855f7',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
    '#14b8a6', '#8b5cf6', '#e11d48', '#0ea5e9', '#d946ef'
]


def _extract_chart_data(sections):
    """从 sections 中提取金额数据用于 CSS 条形图"""
    for section in sections:
        if section['type'] != 'table' or len(section['content']) < 2:
            continue
        rows = section['content']
        header = rows[0] if rows else []
        header_text = ' '.join(header)
        has_amount = any(kw in header_text for kw in ['金额', '万元', '亿元', '投资', '占比'])
        has_name = any(kw in header_text for kw in ['项目', '序号', '事项', '类别', '名称'])
        if not (has_amount and has_name):
            continue

        labels = []
        values = []
        for row in rows[1:]:
            if len(row) < 2:
                continue
            first = str(row[0])
            if any(kw in first for kw in ['小计', '合计', '总计', '汇总']):
                continue
            amount = None
            for cell in reversed(row):
                cleaned = _clean_number(str(cell))
                if cleaned is not None:
                    amount = cleaned
                    break
            if amount is None:
                continue
            label = str(row[1]) if len(row) > 1 and not _clean_number(str(row[1])) else str(row[0])
            labels.append(label)
            values.append(amount)

        if len(labels) >= 2:
            return {'labels': labels, 'values': values, 'colors': _CHART_COLORS[:len(labels)]}
    return None


def _clean_number(cell):
    cell = cell.replace(',', '').replace('，', '').strip()
    m = re.match(r'^[\d.]+$', cell)
    if m:
        return float(m.group())
    m = re.match(r'^([\d.]+)\s*万', cell)
    if m:
        return float(m.group(1))
    m = re.match(r'^([\d.]+)\s*亿', cell)
    if m:
        return float(m.group(1)) * 10000
    return None


# ============================================================
# 纯 CSS 图表渲染
# ============================================================

def _render_chart(data):
    """渲染纯 CSS 水平条形图（无 JS 依赖）"""
    values = data['values']
    max_val = max(values) if values else 1
    bars = []
    for i, (label, val) in enumerate(zip(data['labels'], values)):
        pct = val / max_val * 100 if max_val > 0 else 0
        color = data['colors'][i]
        bars.append(f'''
            <div class="bar-row">
                <span class="bar-label">{_escape(label)}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{max(pct, 2):.0f}%;background:{color};"></div>
                </div>
                <span class="bar-value">{val:,.1f}</span>
            </div>''')
    return f'''
        <div class="chart-section">
            <h3 class="chart-title">投资构成分布</h3>
            <div class="bar-chart">{''.join(bars)}</div>
        </div>'''


# ============================================================
# 核心结论卡片提取
# ============================================================

def _extract_conclusion(sections):
    """尝试从 sections 中提取综合研判结论"""
    for i, s in enumerate(sections):
        if s['type'] == 'h1' and '综合研判' in s['content']:
            # 找到结论段落
            for j in range(i + 1, min(i + 15, len(sections))):
                sj = sections[j]
                if sj['type'] == 'paragraph':
                    text = sj['content']
                    # 提取推荐等级
                    stars = re.search(r'[★☆]{3,5}', text)
                    star_text = stars.group() if stars else ''
                    # 提取摘要
                    summary = text
                    if '推荐等级' in text:
                        summary = text.split('推荐等级')[0].strip()
                    return {'summary': summary[:200], 'stars': star_text, 'full': text}
                if sj['type'] in ('h1', 'h2'):
                    break
    return None


# ============================================================
# 段落渲染
# ============================================================

def _render_sections(sections):
    """将 sections 渲染为 HTML"""
    parts = []
    conclusion = _extract_conclusion(sections)
    # 列表项缓冲
    list_buffer = []
    in_list = False

    for section in sections:
        t = section['type']
        content = section['content']

        if t == 'h1':
            if in_list:
                parts.append(_flush_list(list_buffer))
                list_buffer = []
                in_list = False
            parts.append(
                f'<h2 class="section-title">{_escape(content)}</h2>'
            )

        elif t == 'h2':
            if in_list:
                parts.append(_flush_list(list_buffer))
                list_buffer = []
                in_list = False
            parts.append(
                f'<h3 class="sub-title">{_escape(content)}</h3>'
            )

        elif t == 'bold_label':
            if in_list:
                parts.append(_flush_list(list_buffer))
                list_buffer = []
                in_list = False
            parts.append(
                f'<p class="bold-label"><strong>{_escape(content)}</strong></p>'
            )

        elif t == 'separator':
            if in_list:
                parts.append(_flush_list(list_buffer))
                list_buffer = []
                in_list = False
            parts.append('<hr class="section-divider">')

        elif t == 'table':
            if in_list:
                parts.append(_flush_list(list_buffer))
                list_buffer = []
                in_list = False
            parts.append(_render_table(content))

        elif t == 'paragraph':
            text = content
            # 检测是否为列表项，连续列出
            lines = text.split('\n')
            all_list = all(re.match(r'^[-*]\s+', l.strip()) for l in lines if l.strip())
            if all_list:
                for l in lines:
                    stripped = l.strip()
                    if stripped:
                        item_text = re.sub(r'^[-*]\s+', '', stripped)
                        list_buffer.append(_strip_md(item_text))
                in_list = True
            else:
                if in_list:
                    parts.append(_flush_list(list_buffer))
                    list_buffer = []
                    in_list = False
                # 渲染为普通段落
                rendered = _render_paragraph(text)
                parts.append(f'<div class="content-block">{rendered}</div>')

    if in_list:
        parts.append(_flush_list(list_buffer))

    # 把结论卡片插入正文最前面
    body = '\n'.join(parts)
    if conclusion:
        star_html = ('<div class="conclusion-stars">' + conclusion['stars'] + '</div>') if conclusion['stars'] else ''
        body = (
            '<div class="conclusion-card">'
            '<div class="conclusion-header">综合研判结论</div>'
            + star_html +
            '<div class="conclusion-text">' + _escape(conclusion['summary']) + '</div>'
            '</div>'
        ) + body

    return body


def _flush_list(items):
    if not items:
        return ''
    lis = ''.join(f'<li>{_escape(item)}</li>' for item in items)
    return f'<ul class="styled-list">{lis}</ul>'


def _render_paragraph(text):
    """渲染段落，处理内联格式"""
    text = _escape(text)
    # 还原加粗
    text = re.sub(r'&lt;strong&gt;|&lt;b&gt;', '<strong>', text)
    text = re.sub(r'&lt;/strong&gt;|&lt;/b&gt;', '</strong>', text)
    return f'<p>{text}</p>'


def _render_table(rows):
    if not rows:
        return ''
    first_row = rows[0]
    has_header = all(not re.match(r'^[\d,.，。\s]+$', str(c)) for c in first_row)
    start = 1 if has_header else 0

    thead = ''
    if has_header:
        ths = ''.join(f'<th>{_escape(_strip_md(str(c)))}</th>' for c in first_row)
        thead = f'<thead><tr>{ths}</tr></thead>'

    tbody_rows = []
    for i, row in enumerate(rows[start:]):
        is_summary = any(kw in str(row[0]) for kw in ['小计', '合计', '总计', '汇总'])
        cls = ' class="summary-row"' if is_summary else ''
        tds = ''.join(f'<td>{_escape(_strip_md(str(c)))}</td>' for c in row)
        tbody_rows.append(f'<tr{cls}>{tds}</tr>')

    return f'''
    <div class="table-wrapper">
        <table class="report-table">
            {thead}
            <tbody>{"".join(tbody_rows)}</tbody>
        </table>
    </div>'''


def _escape(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ============================================================
# 完整 HTML 模板（纯静态，零外部依赖）
# ============================================================

def _build_full_html(lead_name, enterprise_name, report_date, chart_html, body_html):
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape(lead_name)} — AI 研判分析报告</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
            background: #f5f7fa;
            color: #303133;
            line-height: 1.75;
            font-size: 14px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 24px 60px;
        }}

        /* ===== 顶部标题 ===== */
        .report-header {{
            background: linear-gradient(135deg, #1a3a5c 0%, #2d6aa0 50%, #3b82c4 100%);
            color: #fff;
            padding: 40px 36px 32px;
            margin: 0 -24px 32px;
        }}
        .report-header h1 {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }}
        .report-header .subtitle {{
            font-size: 14px;
            opacity: 0.85;
            margin-bottom: 6px;
        }}
        .report-meta {{
            display: flex;
            gap: 24px;
            margin-top: 20px;
        }}
        .meta-item {{
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(4px);
            border-radius: 8px;
            padding: 12px 20px;
            min-width: 140px;
        }}
        .meta-item .meta-label {{
            font-size: 11px;
            opacity: 0.7;
            margin-bottom: 4px;
        }}
        .meta-item .meta-value {{
            font-size: 16px;
            font-weight: 600;
        }}

        /* ===== 核心结论卡片 ===== */
        .conclusion-card {{
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #bfdbfe;
            border-radius: 12px;
            padding: 28px 32px;
            margin-bottom: 32px;
        }}
        .conclusion-header {{
            font-size: 18px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 12px;
        }}
        .conclusion-stars {{
            font-size: 22px;
            color: #f59e0b;
            letter-spacing: 4px;
            margin-bottom: 12px;
        }}
        .conclusion-text {{
            font-size: 14px;
            color: #374151;
            line-height: 1.85;
        }}

        /* ===== 区块标题 ===== */
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1a3a5c;
            margin: 32px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #3b82f6;
        }}
        .sub-title {{
            font-size: 15px;
            font-weight: 600;
            color: #1e40af;
            margin: 20px 0 10px;
            padding-left: 10px;
            border-left: 3px solid #3b82f6;
        }}
        .bold-label {{
            margin: 12px 0 6px;
            font-size: 14px;
            color: #1e40af;
        }}
        .section-divider {{
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 24px 0;
        }}

        /* ===== 内容块 ===== */
        .content-block {{
            margin-bottom: 10px;
        }}
        .content-block p {{
            text-indent: 2em;
            margin-bottom: 6px;
            color: #4b5563;
        }}
        .styled-list {{
            padding-left: 24px;
            margin: 8px 0 16px;
        }}
        .styled-list li {{
            margin-bottom: 4px;
            color: #4b5563;
            font-size: 14px;
        }}

        /* ===== 表格 ===== */
        .table-wrapper {{
            overflow-x: auto;
            margin: 16px 0 24px;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .report-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .report-table thead th {{
            background: #eef2f7;
            font-weight: 600;
            color: #374151;
            padding: 10px 14px;
            text-align: left;
            border-bottom: 2px solid #d1d5db;
            white-space: nowrap;
        }}
        .report-table td {{
            padding: 9px 14px;
            color: #4b5563;
            border-bottom: 1px solid #f3f4f6;
        }}
        .report-table tbody tr:nth-child(even) td {{
            background: #f9fafb;
        }}
        .report-table .summary-row td {{
            font-weight: 700;
            background: #eff6ff !important;
            border-top: 1px solid #bfdbfe;
        }}

        /* ===== 条形图（纯 CSS） ===== */
        .chart-section {{
            margin: 24px 0 32px;
        }}
        .chart-title {{
            font-size: 16px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 16px;
        }}
        .bar-chart {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .bar-row {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .bar-label {{
            width: 140px;
            font-size: 13px;
            color: #4b5563;
            text-align: right;
            flex-shrink: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .bar-track {{
            flex: 1;
            height: 20px;
            background: #f3f4f6;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
            min-width: 2px;
        }}
        .bar-value {{
            width: 70px;
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            flex-shrink: 0;
        }}

        /* ===== 页脚 ===== */
        .report-footer {{
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            color: #9ca3af;
            font-size: 12px;
        }}

        /* ===== 打印适配 ===== */
        @media print {{
            body {{ background: #fff; font-size: 12px; }}
            .report-header {{
                background: #1a3a5c !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                padding: 24px 20px;
                margin: 0;
            }}
            .conclusion-card {{
                background: #eff6ff !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
                box-shadow: none;
            }}
            .table-wrapper {{ box-shadow: none; }}
            .report-table thead th {{
                background: #eef2f7 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .bar-fill {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .container {{ max-width: none; padding: 0 16px; }}
            @page {{ margin: 1.5cm; }}
        }}

        /* ===== 响应式 ===== */
        @media (max-width: 768px) {{
            .report-header {{ padding: 24px 16px; }}
            .report-header h1 {{ font-size: 18px; }}
            .report-meta {{ flex-direction: column; gap: 8px; }}
            .meta-item {{ min-width: auto; }}
            .conclusion-card {{ padding: 18px 16px; }}
            .bar-label {{ width: 80px; font-size: 12px; }}
            .table-wrapper {{ font-size: 12px; }}
            .report-table thead th, .report-table td {{ padding: 6px 8px; }}
        }}
    </style>
</head>
<body>
    <header class="report-header">
        <h1>{_escape(lead_name)}</h1>
        <p class="subtitle">招商线索研判分析报告</p>
        <div class="report-meta">
            <div class="meta-item">
                <div class="meta-label">目标企业</div>
                <div class="meta-value">{_escape(enterprise_name)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">报告生成时间</div>
                <div class="meta-value">{report_date}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">报告类型</div>
                <div class="meta-value">AI 智能研判</div>
            </div>
        </div>
    </header>

    <main class="container">
        {chart_html}
        {body_html}
    </main>

    <footer class="report-footer">
        <p>本报告由 AI 自动生成，仅供参考 | 生成时间：{report_date}</p>
        <p>襄阳农高区招商服务平台</p>
    </footer>
</body>
</html>'''
