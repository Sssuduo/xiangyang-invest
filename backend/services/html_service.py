"""
研判报告 HTML 生成服务

将 LLM 返回的 markdown 文本解析后，嵌入预定义的 HTML 模板，
生成可直接在浏览器中查看的高质量投资分析报告。
"""
import re
import os
from datetime import datetime


def generate_assessment_html(lead_name, enterprise_name, assessment_text):
    """将 AI 研判结果生成格式化的 HTML 报告

    Args:
        lead_name: 项目名称
        enterprise_name: 企业名称
        assessment_text: LLM 返回的 markdown 文本

    Returns:
        tuple: (file_url, file_name)
    """
    out_dir = _ensure_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', lead_name)[:40]
    file_name = f'{safe_name}_AI研判报告_{timestamp}.html'
    file_path = os.path.join(out_dir, file_name)

    # 解析 markdown
    sections = _parse_markdown(assessment_text)

    # 提取投资数据（用于图表）
    chart_data = _extract_chart_data(sections)

    # 渲染 HTML
    html = _render_template(lead_name, enterprise_name, sections, chart_data)

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
    """将 markdown 文本解析为结构化的 sections 列表

    每个 section 是一个 dict:
      { 'type': 'h1'|'h2'|'table'|'paragraph'|'separator',
        'content': str | list[list] }
    """
    lines = text.strip().split('\n')
    sections = []
    pending_paragraph = []

    def flush_paragraph():
        nonlocal pending_paragraph
        if pending_paragraph:
            sections.append({'type': 'paragraph', 'content': '\n'.join(pending_paragraph)})
            pending_paragraph = []

    for line in lines:
        stripped = line.strip()

        # 空行 → 提交段落
        if not stripped:
            flush_paragraph()
            continue

        # 分隔线
        if re.match(r'^[━═\-*_]{5,}$', stripped):
            flush_paragraph()
            sections.append({'type': 'separator', 'content': stripped})
            continue

        # Markdown H1 (# xxx)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            flush_paragraph()
            sections.append({'type': 'h1', 'content': stripped[2:]})
            continue

        # Markdown H2 (## xxx)
        if stripped.startswith('## '):
            flush_paragraph()
            sections.append({'type': 'h2', 'content': stripped[3:]})
            continue

        # 中文编号标题：一、二、...  或 1. xxx
        if re.match(r'^[一二三四五六七八九十]、', stripped):
            flush_paragraph()
            sections.append({'type': 'h1', 'content': stripped})
            continue

        # 数字编号标题（带 ** 或短标题）
        is_numbered = re.match(r'^\d+[\.\、]\s*\*\*(.+)\*\*', stripped)
        if is_numbered and len(stripped) < 120:
            flush_paragraph()
            sections.append({'type': 'h2', 'content': is_numbered.group(1)})
            continue

        # 表格行：| col1 | col2 | ... |
        if stripped.startswith('|') and stripped.endswith('|') and not re.match(r'^\|[-: ]+\|', stripped):
            flush_paragraph()
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            sections.append({'type': 'table_row', 'content': cells})
            continue

        # 普通段落
        pending_paragraph.append(stripped)

    flush_paragraph()

    # ---- 后处理：合并连续的 table_row 为 table ----
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


# ============================================================
# 数据提取（用于 Chart.js 图表）
# ============================================================

def _extract_chart_data(sections):
    """从解析后的 sections 中尝试提取投资数据用于饼图渲染

    识别包含金额/百分比的表格，提取标签和数值。
    返回 {'labels': [...], 'values': [...], 'colors': [...]} 或 None
    """
    # 优先找"汇总"或"合计"相关的表格
    for section in sections:
        if section['type'] == 'table' and len(section['content']) >= 3:
            rows = section['content']
            labels = []
            values = []
            # 检测表头：包含"项目"、"金额"、"占比"等关键词
            header = rows[0] if rows else []
            header_text = ' '.join(header)
            has_amount = any(kw in header_text for kw in ['金额', '万元', '亿元', '投资'])
            has_name = any(kw in header_text for kw in ['项目', '序号', '事项', '名称'])

            if not (has_amount and has_name):
                continue

            for row in rows[1:]:
                if len(row) < 2:
                    continue
                # 跳过"小计""合计"行
                first = row[0]
                if any(kw in first for kw in ['小计', '合计', '总计']):
                    continue
                # 尝试解析金额（最后一个纯数字列）
                amount = None
                for cell in reversed(row):
                    cleaned = _clean_number(cell)
                    if cleaned is not None:
                        amount = cleaned
                        break
                if amount is None:
                    continue
                # 用第一个非数字列作为标签
                label = row[1] if len(row) > 1 and not _clean_number(row[1]) else row[0]
                labels.append(label)
                values.append(amount)

            if len(labels) >= 3:
                return {
                    'labels': labels,
                    'values': values,
                    'colors': _CHART_COLORS[:len(labels)]
                }

    return None


def _clean_number(cell):
    """从单元格中提取纯数字，处理逗号、万字、亿字"""
    cell = str(cell).replace(',', '').replace('，', '').strip()
    # 直接匹配数字
    m = re.match(r'^[\d.]+$', cell)
    if m:
        return float(m.group())
    # "xxx万" → 万元
    m = re.match(r'^([\d.]+)\s*万', cell)
    if m:
        return float(m.group(1))
    # "xxx亿" → 万元
    m = re.match(r'^([\d.]+)\s*亿', cell)
    if m:
        return float(m.group(1)) * 10000
    return None


_CHART_COLORS = [
    '#3b82f6', '#f59e0b', '#10b981', '#f43f5e', '#a855f7',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
    '#14b8a6', '#8b5cf6', '#e11d48', '#0ea5e9', '#d946ef'
]


# ============================================================
# HTML 模板渲染
# ============================================================

def _render_template(lead_name, enterprise_name, sections, chart_data):
    """将解析后的 sections 渲染为完整的 HTML 页面"""

    body_html = _render_sections(sections)

    chart_js = ''
    if chart_data:
        chart_js = f'''
    <div class="chart-container">
        <canvas id="investmentChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('investmentChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: {_json(chart_data['labels'])},
                datasets: [{{
                    data: {_json(chart_data['values'])},
                    backgroundColor: {_json(chart_data['colors'])},
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ padding: 20, usePointStyle: true, pointStyleWidth: 10, font: {{ size: 13 }} }}
                    }}
                }}
            }}
        }});
    </script>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape(lead_name)} — AI 研判分析报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Noto Sans SC', sans-serif; }}
        .gradient-header {{
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #06b6d4 100%);
        }}
        .section-card {{
            transition: all 0.3s ease;
        }}
        .section-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 20px -8px rgba(0,0,0,0.1);
        }}
        .highlight-row {{
            background: linear-gradient(90deg, #dbeafe 0%, #e0f2fe 100%);
        }}
        .chart-container {{
            max-width: 500px;
            margin: 24px auto;
            height: 420px;
        }}
        .report-table {{
            border-collapse: collapse;
        }}
        .report-table th {{
            background: #f8fafc;
            font-weight: 600;
            font-size: 13px;
            color: #334155;
            border-bottom: 2px solid #e2e8f0;
        }}
        .report-table td {{
            font-size: 13px;
            color: #475569;
            border-bottom: 1px solid #f1f5f9;
        }}
        .report-table tr:hover td {{
            background: #f8fafc;
        }}
        .table-wrapper {{
            overflow-x: auto;
            margin: 12px 0;
        }}
        .content-text {{
            font-size: 14px;
            line-height: 1.85;
            color: #374151;
            text-indent: 2em;
        }}
    </style>
</head>
<body class="bg-gray-50">
    <header class="gradient-header text-white py-10 px-6">
        <div class="max-w-5xl mx-auto">
            <h1 class="text-3xl font-bold mb-2">{_escape(lead_name)}</h1>
            <h2 class="text-xl font-light mb-4">招商线索研判分析报告</h2>
            <div class="flex flex-wrap gap-4 mt-6">
                <div class="bg-white/20 backdrop-blur rounded-lg px-5 py-3">
                    <p class="text-blue-100 text-xs mb-1">目标企业</p>
                    <p class="text-lg font-semibold">{_escape(enterprise_name)}</p>
                </div>
                <div class="bg-white/20 backdrop-blur rounded-lg px-5 py-3">
                    <p class="text-blue-100 text-xs mb-1">报告生成时间</p>
                    <p class="text-lg font-semibold">{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto px-6 py-10">
        {chart_js}

        <div class="bg-white rounded-2xl shadow-lg p-8">
            {body_html}
        </div>
    </main>

    <footer class="bg-gray-800 text-white py-8 px-6">
        <div class="max-w-5xl mx-auto text-center">
            <p class="text-gray-400 text-sm">本报告由 AI 自动生成，仅供参考 | 生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
        </div>
    </footer>
</body>
</html>'''


def _render_sections(sections):
    """将 sections 列表渲染为 HTML"""
    html_parts = []

    for section in sections:
        t = section['type']
        content = section['content']

        if t == 'h1':
            html_parts.append(
                f'<h3 class="text-xl font-bold text-gray-800 mt-8 mb-4 pb-2 border-b-2 border-blue-500">{_escape(_strip_md(content))}</h3>'
            )

        elif t == 'h2':
            html_parts.append(
                f'<h4 class="text-lg font-semibold text-gray-700 mt-6 mb-3 pl-3 border-l-4 border-blue-400">{_escape(_strip_md(content))}</h4>'
            )

        elif t == 'separator':
            html_parts.append('<hr class="my-6 border-gray-200">')

        elif t == 'table':
            html_parts.append(_render_table(content))

        elif t == 'paragraph':
            # 处理段落内的 markdown 格式
            text = _strip_md(content)
            # 如果段落较短且包含冒号，可能是键值对
            if len(text) < 200 and '：' in text and '\n' not in text:
                html_parts.append(f'<p class="text-sm text-gray-600 my-2">{_escape(text)}</p>')
            else:
                html_parts.append(f'<p class="content-text my-3">{_escape(text)}</p>')

    return '\n'.join(html_parts)


def _render_table(rows):
    """渲染 HTML 表格"""
    if not rows:
        return ''

    # 检测是否有表头（第一行不含数字）
    first_row = rows[0]
    has_header = all(not re.match(r'^[\d,.，。\s]+$', str(c)) for c in first_row)

    start = 1 if has_header else 0

    thead = ''
    if has_header:
        ths = ''.join(
            f'<th class="px-4 py-3 text-left">{_escape(_strip_md(str(c)))}</th>'
            for c in first_row
        )
        thead = f'<thead><tr>{ths}</tr></thead>'

    tbody_parts = []
    for i, row in enumerate(rows[start:]):
        is_last = (i == len(rows) - start - 1)
        is_summary = any(kw in str(row[0]) for kw in ['小计', '合计', '总计', '汇总'])
        row_class = 'highlight-row' if is_summary else ''
        # 对于合计行加粗
        cell_class = 'font-bold' if is_summary else ''
        tds = ''.join(
            f'<td class="px-4 py-3 text-sm {cell_class}">{_escape(_strip_md(str(c)))}</td>'
            for c in row
        )
        tbody_parts.append(f'<tr class="{row_class}">{tds}</tr>')

    tbody = '\n'.join(tbody_parts)

    return f'''
    <div class="table-wrapper my-4">
        <table class="report-table w-full">
            {thead}
            <tbody>{tbody}</tbody>
        </table>
    </div>'''


def _strip_md(text):
    """移除 markdown 标记"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _escape(text):
    """HTML 转义"""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _json(obj):
    """安全 JSON 序列化"""
    import json as _json
    return _json.dumps(obj, ensure_ascii=False)
