"""
录音总结 PDF 导出服务 — 公文格式版

将活动台账/招商动态的录音总结（分段原文/清洁版/摘要版）导出为 PDF。
支持多版本合并导出（一个 PDF 包含多个版本）。

公文格式（GB/T 9704-2012）：
- 正标题：方正小标宋简体，2号字（22pt）
- 一级标题：黑体，3号字（16pt），如"一、"
- 二级标题：楷体GB2312，3号字（16pt），如"（一）"或"1."
- 三级标题：仿宋GB2312，3号字加粗（16pt）
- 正文：仿宋GB2312，3号字（16pt）
- 页边距：上3cm，下2.5cm，左右2.5cm
- 段落：固定值28磅（行距）
- 标题与正文间隔1行
"""
import os
import re
import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

# reportlab 依赖（懒加载，避免无 reportlab 时模块导入失败）
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak)
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False

# ===================== 公文字体配置 =====================
# 字体文件路径（/usr/share/fonts/office/ 下）
_FONT_PATHS = {
    'xiaobiaosong': '/usr/share/fonts/office/方正小标宋简体.ttf',   # 正标题
    'simhei': '/usr/share/fonts/office/黑体.ttf',                   # 一级标题
    'kaiti': '/usr/share/fonts/office/楷体_GB2312.ttf',             # 二级标题/落款
    'fangsong': '/usr/share/fonts/office/仿宋_GB2312.ttf',          # 正文
}

# 字体注册名（reportlab 内使用）
_FONT_NAMES = {
    'xiaobiaosong': 'XiaoBiaoSong',
    'simhei': 'SimHei',
    'kaiti': 'KaiTi',
    'fangsong': 'FangSong',
}

# 字号（pt）：公文 2号=22pt, 3号=16pt
_FONT_SIZE_TITLE = 22    # 2号字：正标题
_FONT_SIZE_H1 = 16       # 3号字：一级标题
_FONT_SIZE_H2 = 16       # 3号字：二级标题
_FONT_SIZE_BODY = 16     # 3号字：正文
_FONT_SIZE_NOTE = 14     # 4号字：落款/时间

# 行距：固定值28磅
_LINE_SPACING = 28

# 页面设置（cm → mm）：上3，下2.5，左右2.5
_PAGE_TOP = 30 * mm
_PAGE_BOTTOM = 25 * mm
_PAGE_LEFT = 25 * mm
_PAGE_RIGHT = 25 * mm

# 版本定义
VERSIONS = {
    'segmented': {'label': '分段原文', 'field': 'audio_transcript_segmented', 'fallback': 'audio_transcript'},
    'clean': {'label': '清洁版', 'field': 'audio_transcript_clean', 'fallback': None},
    'summary': {'label': '摘要版', 'field': 'audio_summary_structured', 'fallback': 'audio_summary'},
}


def _register_fonts():
    """注册公文字体到 reportlab（带缓存）"""
    if not _REPORTLAB_OK:
        return False
    if 'FangSong' in pdfmetrics.getRegisteredFontNames():
        return True
    ok = True
    for key, name in _FONT_NAMES.items():
        path = _FONT_PATHS[key]
        if not os.path.exists(path):
            logger.warning(f'公文字体缺失: {path}')
            ok = False
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            logger.warning(f'字体注册失败 {name}: {e}')
            ok = False
    return ok


def _strip_markdown(text):
    """移除 markdown 标记，保留纯文本（用于表格单元格）"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _parse_markdown_to_elements(text, styles, font_name):
    """将 Markdown 文本解析为 reportlab flowables 列表（公文格式）"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.colors import HexColor

    elements = []
    in_table = False
    table_rows = []

    def _flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        data = [[Paragraph(_strip_markdown(c), styles['cell']) for c in row] for row in table_rows]
        # 计算列宽：总可用宽度均分
        avail_width = (210 - 50) * mm  # A4 宽 210mm - 左右边距各 25mm
        ncols = max(len(r) for r in table_rows)
        col_widths = [avail_width / ncols] * ncols
        t = Table(data, repeatRows=1, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e0e4e8')),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f0f3f8')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))
        in_table = False
        table_rows = []

    for raw_line in text.strip().split('\n'):
        line = raw_line.strip()
        if not line:
            if in_table:
                _flush_table()
            elements.append(Spacer(1, _LINE_SPACING / 2))
            continue

        # 表格行
        if line.startswith('|') and line.endswith('|') and line.count('|') >= 2:
            if not re.match(r'^\|[-: ]+\|', line):
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if len(cells) >= 2:
                    if not in_table:
                        table_rows = []
                        in_table = True
                    table_rows.append(cells)
                    continue

        # 表格结束
        if in_table:
            _flush_table()

        # 分隔线
        if re.match(r'^[━═-]{5,}', line):
            continue

        # ---- 公文格式标题层级 ----
        if line.startswith('#### '):
            # 三级标题：仿宋加粗
            elements.append(Paragraph(_strip_markdown(line[5:]), styles['h3']))
        elif line.startswith('### '):
            elements.append(Paragraph(_strip_markdown(line[4:]), styles['h2']))
        elif line.startswith('## '):
            elements.append(Paragraph(_strip_markdown(line[3:]), styles['h1']))
        elif line.startswith('# '):
            elements.append(Paragraph(_strip_markdown(line[2:]), styles['h1']))
        elif re.match(r'^[一二三四五六七八九十]+、', line):
            # 一级标题：黑体，如"一、"
            elements.append(Paragraph(_strip_markdown(line), styles['h1']))
        elif re.match(r'^（[一二三四五六七八九十]+）', line):
            # 二级标题：楷体，如"（一）"
            elements.append(Paragraph(_strip_markdown(line), styles['h2']))
        elif re.match(r'^\d+[\.．]', line):
            # 二级标题：楷体，如"1."
            elements.append(Paragraph(_strip_markdown(line), styles['h2']))
        elif line.startswith('- '):
            # 列表项：仿宋正文
            elements.append(Paragraph(f'　{_strip_markdown(line[2:])}', styles['body']))
        elif line.startswith('> '):
            # 引用：楷体
            elements.append(Paragraph(_strip_markdown(line[2:]), styles['quote']))
        else:
            # 正文：仿宋，首行缩进2字符
            elements.append(Paragraph(f'　　{_strip_markdown(line)}', styles['body']))

    if in_table:
        _flush_table()

    return elements


def generate_meeting_pdf(activity, versions, title='活动台账 会议录音总结'):
    """生成录音总结 PDF（公文格式，可多版本合并）。

    Args:
        activity: ActivityLedger / InvestmentActivity 实例
        versions: 要导出的版本列表，如 ['summary'] 或 ['segmented', 'clean', 'summary']
        title: PDF 主标题

    Returns:
        str: PDF 文件绝对路径
    """
    if not _REPORTLAB_OK:
        raise RuntimeError('服务器未安装 reportlab，无法导出 PDF')

    if not _register_fonts():
        raise RuntimeError('未找到公文字体，无法导出 PDF')

    out_dir = os.path.join(current_app.static_folder, 'meetings')
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', (activity.content or '会议总结')[:30])
    file_name = f'{safe_name}_会议总结_{timestamp}.pdf'
    file_path = os.path.join(out_dir, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=_PAGE_TOP,
        bottomMargin=_PAGE_BOTTOM,
        leftMargin=_PAGE_LEFT,
        rightMargin=_PAGE_RIGHT,
        title=title,
    )

    # ---- 公文格式样式 ----
    styles = {
        # 正标题：方正小标宋简体 2号字(22pt)，居中
        'title': ParagraphStyle('title', fontName=_FONT_NAMES['xiaobiaosong'],
                                fontSize=_FONT_SIZE_TITLE, leading=_LINE_SPACING + 4,
                                alignment=1, textColor=HexColor('#000000'),
                                spaceAfter=_LINE_SPACING),
        # 副标题/落款：楷体 3号字
        'subtitle': ParagraphStyle('subtitle', fontName=_FONT_NAMES['kaiti'],
                                   fontSize=_FONT_SIZE_NOTE, leading=_LINE_SPACING,
                                   alignment=1, textColor=HexColor('#000000'),
                                   spaceAfter=_LINE_SPACING),
        # 一级标题：黑体 3号字，如"一、"
        'h1': ParagraphStyle('h1', fontName=_FONT_NAMES['simhei'],
                             fontSize=_FONT_SIZE_H1, leading=_LINE_SPACING,
                             spaceBefore=_LINE_SPACING, spaceAfter=_LINE_SPACING / 2,
                             textColor=HexColor('#000000')),
        # 二级标题：楷体 3号字，如"（一）"或"1."
        'h2': ParagraphStyle('h2', fontName=_FONT_NAMES['kaiti'],
                             fontSize=_FONT_SIZE_H2, leading=_LINE_SPACING,
                             spaceBefore=_LINE_SPACING / 2, spaceAfter=_LINE_SPACING / 2,
                             textColor=HexColor('#000000')),
        # 三级标题：仿宋 3号字加粗
        'h3': ParagraphStyle('h3', fontName=_FONT_NAMES['fangsong'],
                             fontSize=_FONT_SIZE_BODY, leading=_LINE_SPACING,
                             spaceBefore=_LINE_SPACING / 2, spaceAfter=_LINE_SPACING / 2,
                             textColor=HexColor('#000000')),
        # 正文：仿宋 3号字
        'body': ParagraphStyle('body', fontName=_FONT_NAMES['fangsong'],
                               fontSize=_FONT_SIZE_BODY, leading=_LINE_SPACING,
                               spaceAfter=2, wordWrap='CJK',
                               textColor=HexColor('#000000')),
        # 引用/备注：楷体
        'quote': ParagraphStyle('quote', fontName=_FONT_NAMES['kaiti'],
                                fontSize=_FONT_SIZE_NOTE, leading=_LINE_SPACING,
                                leftIndent=12, textColor=HexColor('#000000')),
        # 表格单元格：仿宋 3号字（小号适配）
        'cell': ParagraphStyle('cell', fontName=_FONT_NAMES['fangsong'],
                               fontSize=12, leading=18, wordWrap='CJK',
                               textColor=HexColor('#000000')),
    }

    elements = []

    # ---- 正标题：方正小标宋 2号字 ----
    elements.append(Paragraph(title, styles['title']))
    # 标题与正文间隔1行
    elements.append(Spacer(1, _LINE_SPACING))

    # ---- 副标题：活动内容（楷体） ----
    subtitle = activity.content or '活动台账'
    if len(subtitle) > 80:
        subtitle = subtitle[:80] + '...'
    elements.append(Paragraph(subtitle, styles['subtitle']))

    # ---- 落款时间（楷体） ----
    activity_date = activity.date.strftime('%Y年%m月%d日') if activity.date else '未知日期'
    elements.append(Paragraph(
        f'活动时间：{activity_date}　生成时间：{datetime.now().strftime("%Y年%m月%d日 %H:%M")}',
        styles['subtitle']))
    elements.append(Spacer(1, _LINE_SPACING))

    # ---- 各版本内容 ----
    for i, v in enumerate(versions):
        if v not in VERSIONS:
            continue
        cfg = VERSIONS[v]
        text = getattr(activity, cfg['field'], None) or ''
        if not text and cfg['fallback']:
            text = getattr(activity, cfg['fallback'], None) or ''
        if not text:
            continue

        if i > 0:
            elements.append(PageBreak())

        # 版本标题：黑体 3号
        elements.append(Paragraph(f'{cfg["label"]}', styles['h1']))
        elements.append(Spacer(1, _LINE_SPACING / 2))

        # 解析 Markdown（公文格式）
        elements.extend(_parse_markdown_to_elements(text, styles, _FONT_NAMES['fangsong']))

    doc.build(elements)
    return file_path
