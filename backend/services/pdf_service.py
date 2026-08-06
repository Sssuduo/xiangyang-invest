"""
工作台账录音总结 PDF 导出服务 — 公文格式版（GB/T 9704-2012）

将工作台账的录音总结（分段原文/摘要版）导出为 PDF。
支持多版本合并导出（一个 PDF 包含多个版本）。

公文格式（GB/T 9704-2012）：
- 页边距：上3.7cm、下3.5cm、左2.8cm、右2.6cm（版心 156mm×225mm）
- 正标题：方正小标宋简体，二号(22pt)，居中；上空1行、下空1行
- 一级标题（##）：黑体，三号(16pt)，首行缩进2字符，"一、二、三、"
- 二级标题（###）：楷体GB2312，三号(16pt)，首行缩进2字符，"（一）（二）"
- 三级标题（####）：仿宋GB2312加粗，三号(16pt)，"1. 2. 3."
- 正文：仿宋GB2312，三号(16pt)，首行缩进2字符，行距固定值29磅
- 页码：四号半角宋体阿拉伯数字，版心下边缘之下，数字左右各加一字线
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
    'simhei': '/usr/share/fonts/office/黑体.ttf',                   # 一级标题/表头
    'kaiti': '/usr/share/fonts/office/楷体_GB2312.ttf',             # 二级标题
    'fangsong': '/usr/share/fonts/office/仿宋_GB2312.ttf',          # 正文
    'songti': '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',     # 页码（宋体替代）
}

# 字体注册名（reportlab 内使用）
_FONT_NAMES = {
    'xiaobiaosong': 'XiaoBiaoSong',
    'simhei': 'SimHei',
    'kaiti': 'KaiTi',
    'fangsong': 'FangSong',
}

# 字号（pt）：公文 二号=22pt, 三号=16pt, 四号=14pt
_FONT_SIZE_TITLE = 22    # 二号：正标题
_FONT_SIZE_H1 = 16       # 三号：一级标题
_FONT_SIZE_H2 = 16       # 三号：二级标题
_FONT_SIZE_H3 = 16       # 三号：三级标题
_FONT_SIZE_BODY = 16     # 三号：正文
_FONT_SIZE_NOTE = 14     # 四号：页码

# 行距：固定值29磅（国标）
_LINE_SPACING = 29

# 页面设置（GB/T 9704-2012）：上3.7cm 下3.5cm 左2.8cm 右2.6cm
_PAGE_TOP = 37 * mm
_PAGE_BOTTOM = 35 * mm
_PAGE_LEFT = 28 * mm
_PAGE_RIGHT = 26 * mm

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


def _parse_markdown_to_elements(text, styles):
    """将 Markdown 文本解析为 reportlab flowables 列表（GB/T 9704-2012）"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.colors import HexColor

    elements = []
    in_table = False
    table_rows = []
    # 有序列表计数器（按层级）
    order_counters = {}

    def _flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        data = [[Paragraph(_strip_markdown(c), styles['cell']) for c in row] for row in table_rows]
        # 计算列宽：总可用宽度均分
        avail_width = (210 - 28 - 26) * mm  # A4 宽 210mm - 左右边距 28+26mm
        ncols = max(len(r) for r in table_rows)
        col_widths = [avail_width / ncols] * ncols
        t = Table(data, repeatRows=1, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#000000')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
        in_table = False
        table_rows = []

    def _indent2(text):
        """首行缩进2字符（全角空格）"""
        return f'　　{text}'

    for raw_line in text.strip().split('\n'):
        line = raw_line.strip()
        if not line:
            if in_table:
                _flush_table()
            # 空行：不额外加空行（公文不空行），仅块间自然间隔
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

        # 分隔线 → 黑色细实线
        if re.match(r'^[━═-]{5,}', line):
            from reportlab.platypus import HRFlowable
            elements.append(HRFlowable(width='100%', thickness=0.5,
                                       color=HexColor('#000000'),
                                       spaceBefore=6, spaceAfter=6))
            continue

        # ---- 公文格式标题层级 ----
        # 三级标题（####）：仿宋加粗，"1. 2. 3." 或 "一是"
        if line.startswith('#### '):
            content = _strip_markdown(line[5:])
            elements.append(Paragraph(_indent2(f'<b>{content}</b>'), styles['h3']))
        # 二级标题（###）：楷体，"（一）（二）"
        elif line.startswith('### '):
            elements.append(Paragraph(_indent2(_strip_markdown(line[4:])), styles['h2']))
        # 一级标题（##）：黑体，"一、二、"
        elif line.startswith('## '):
            elements.append(Paragraph(_indent2(_strip_markdown(line[3:])), styles['h1']))
        # 文档总标题（#）：小标宋二号（对应正标题）
        elif line.startswith('# '):
            elements.append(Paragraph(_strip_markdown(line[2:]), styles['doc_title']))
        # 一级标题：黑体，"一、"
        elif re.match(r'^[一二三四五六七八九十]+、', line):
            elements.append(Paragraph(_indent2(_strip_markdown(line)), styles['h1']))
        # 二级标题：楷体，"（一）"
        elif re.match(r'^（[一二三四五六七八九十]+）', line):
            elements.append(Paragraph(_indent2(_strip_markdown(line)), styles['h2']))
        # 三级标题：仿宋加粗，"1."
        elif re.match(r'^\d+[\.．]', line):
            elements.append(Paragraph(_indent2(f'<b>{_strip_markdown(line)}</b>'), styles['h3']))
        # 有序列表：按层级匹配序号（一、→（一）→1.→（1））
        elif re.match(r'^\d+[、\)）]', line):
            elements.append(Paragraph(_indent2(_strip_markdown(line)), styles['body']))
        # 无序列表：实心圆点，首行缩进2字符
        elif line.startswith('- '):
            content = _strip_markdown(line[2:])
            elements.append(Paragraph(_indent2(f'● {content}'), styles['body']))
        # 引用块：仿宋，左右缩进2字符
        elif line.startswith('> '):
            elements.append(Paragraph(_indent2(_strip_markdown(line[2:])), styles['quote']))
        # 加粗段落
        elif line.startswith('**') and line.endswith('**') and len(line) > 4:
            elements.append(Paragraph(_indent2(line), styles['body_bold']))
        else:
            # 正文：仿宋，首行缩进2字符
            elements.append(Paragraph(_indent2(_strip_markdown(line)), styles['body']))

    if in_table:
        _flush_table()

    return elements


def generate_meeting_pdf(activity, versions, title='工作台账会议录音总结', cleaned_contents=None):
    """生成工作台账录音总结 PDF（公文格式，可多版本合并）。

    Args:
        activity: ActivityLedger 实例
        versions: 要导出的版本列表，如 ['summary'] 或 ['segmented', 'summary']
        title: PDF 主标题（默认"工作台账会议录音总结"）
        cleaned_contents: 可选 dict {version: 已清洗文本}；提供时优先使用清洗后内容，
                         否则读活动实例的原始字段。

    Returns:
        str: PDF 文件绝对路径
    """
    if not _REPORTLAB_OK:
        raise RuntimeError('服务器未安装 reportlab，无法导出 PDF')

    if not _register_fonts():
        raise RuntimeError('未找到公文字体，无法导出 PDF')

    cleaned_contents = cleaned_contents or {}

    out_dir = os.path.join(current_app.static_folder, 'meetings')
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', (activity.content or '工作台账')[:30])
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

    # ---- 公文格式样式（GB/T 9704-2012） ----
    styles = {
        # 正标题：方正小标宋 二号(22pt) 居中
        'doc_title': ParagraphStyle('doc_title', fontName=_FONT_NAMES['xiaobiaosong'],
                                    fontSize=_FONT_SIZE_TITLE, leading=_LINE_SPACING + 6,
                                    alignment=1, textColor=HexColor('#000000')),
        # 一级标题：黑体 三号(16pt) 首行缩进2
        'h1': ParagraphStyle('h1', fontName=_FONT_NAMES['simhei'],
                             fontSize=_FONT_SIZE_H1, leading=_LINE_SPACING,
                             textColor=HexColor('#000000')),
        # 二级标题：楷体 三号(16pt)
        'h2': ParagraphStyle('h2', fontName=_FONT_NAMES['kaiti'],
                             fontSize=_FONT_SIZE_H2, leading=_LINE_SPACING,
                             textColor=HexColor('#000000')),
        # 三级标题：仿宋加粗 三号(16pt)
        'h3': ParagraphStyle('h3', fontName=_FONT_NAMES['fangsong'],
                             fontSize=_FONT_SIZE_H3, leading=_LINE_SPACING,
                             textColor=HexColor('#000000')),
        # 正文：仿宋 三号(16pt)
        'body': ParagraphStyle('body', fontName=_FONT_NAMES['fangsong'],
                               fontSize=_FONT_SIZE_BODY, leading=_LINE_SPACING,
                               spaceAfter=0, wordWrap='CJK',
                               textColor=HexColor('#000000')),
        # 正文加粗
        'body_bold': ParagraphStyle('body_bold', fontName=_FONT_NAMES['fangsong'],
                                    fontSize=_FONT_SIZE_BODY, leading=_LINE_SPACING,
                                    spaceAfter=0, wordWrap='CJK',
                                    textColor=HexColor('#000000')),
        # 引用：仿宋，左右缩进2字符
        'quote': ParagraphStyle('quote', fontName=_FONT_NAMES['fangsong'],
                                fontSize=_FONT_SIZE_BODY, leading=_LINE_SPACING,
                                leftIndent=16, rightIndent=16,
                                textColor=HexColor('#000000')),
        # 表格表头：黑体
        'th': ParagraphStyle('th', fontName=_FONT_NAMES['simhei'],
                             fontSize=12, leading=18, wordWrap='CJK',
                             textColor=HexColor('#000000')),
        # 表格内容：仿宋
        'cell': ParagraphStyle('cell', fontName=_FONT_NAMES['fangsong'],
                               fontSize=12, leading=18, wordWrap='CJK',
                               textColor=HexColor('#000000')),
    }

    elements = []

    # ---- 正标题：方正小标宋 二号字 居中，上空1行 ----
    elements.append(Spacer(1, _LINE_SPACING))  # 标题上空1行
    elements.append(Paragraph(title, styles['doc_title']))
    elements.append(Spacer(1, _LINE_SPACING))  # 标题下空1行

    # ---- 台账内容（取工作台账 content 字段，正文格式，首行缩进2） ----
    ledger_content = (activity.content or '').strip()
    if ledger_content:
        elements.append(Paragraph(f'　　{ledger_content}', styles['body']))
        elements.append(Spacer(1, _LINE_SPACING))

    # ---- 各版本内容（不含版本标签标题，不含落款时间） ----
    for i, v in enumerate(versions):
        if v not in VERSIONS:
            continue
        # 优先使用公文清洗后的内容，否则读原始字段
        if v in cleaned_contents and cleaned_contents[v]:
            text = cleaned_contents[v]
        else:
            cfg = VERSIONS[v]
            text = getattr(activity, cfg['field'], None) or ''
            if not text and cfg['fallback']:
                text = getattr(activity, cfg['fallback'], None) or ''
        if not text:
            continue

        if i > 0:
            elements.append(PageBreak())

        # 解析 Markdown（公文格式）；不输出版本标签标题（如"分段原文""摘要版"）
        elements.extend(_parse_markdown_to_elements(text, styles))

    doc.build(elements)
    return file_path
