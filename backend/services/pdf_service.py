"""
录音总结 PDF 导出服务

将活动台账/招商动态的录音总结（分段原文/清洁版/摘要版）导出为 PDF。
支持多版本合并导出（一个 PDF 包含多个版本）。

依赖：reportlab（已安装）+ 文泉驿微米黑中文字体（/usr/share/fonts/wqy-microhei/wqy-microhei.ttc）
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
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak)
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False

# 中文字体路径候选
_FONT_CANDIDATES = [
    '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
    '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
]

# 版本定义
VERSIONS = {
    'segmented': {'label': '分段原文', 'field': 'audio_transcript_segmented', 'fallback': 'audio_transcript'},
    'clean': {'label': '清洁版', 'field': 'audio_transcript_clean', 'fallback': None},
    'summary': {'label': '摘要版', 'field': 'audio_summary_structured', 'fallback': 'audio_summary'},
}


def _find_font():
    """查找可用的中文字体文件"""
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _register_fonts():
    """注册中文字体到 reportlab（带缓存）"""
    if not _REPORTLAB_OK:
        return False
    if 'WenQuanYiMicroHei' in pdfmetrics.getRegisteredFontNames():
        return True
    font_path = _find_font()
    if not font_path:
        logger.warning('未找到中文字体，PDF 中文可能乱码')
        return False
    try:
        pdfmetrics.registerFont(TTFont('WenQuanYiMicroHei', font_path))
        return True
    except Exception as e:
        logger.warning(f'字体注册失败: {e}')
        return False


def _strip_markdown(text):
    """移除 markdown 标记，保留纯文本（用于表格单元格）"""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _parse_markdown_to_elements(text, styles, font_name):
    """将 Markdown 文本解析为 reportlab flowables 列表"""
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
        # 计算列宽：总可用宽度均分，避免单元格内容过长导致负宽
        from reportlab.lib.units import mm as _mm
        avail_width = (210 - 40) * _mm  # A4 宽 210mm - 左右边距各 20mm
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
            elements.append(Spacer(1, 6))
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

        # 标题层级
        if line.startswith('#### '):
            elements.append(Paragraph(f'<font color="#5a6c7d">{_strip_markdown(line[5:])}</font>', styles['h4']))
        elif line.startswith('### '):
            elements.append(Paragraph(f'<font color="#2a5a8c">{_strip_markdown(line[4:])}</font>', styles['h3']))
        elif line.startswith('## '):
            elements.append(Paragraph(f'<font color="#1a3a5c"><b>{_strip_markdown(line[3:])}</b></font>', styles['h2']))
        elif line.startswith('# '):
            elements.append(Paragraph(f'<font color="#1a3a5c"><b>{_strip_markdown(line[2:])}</b></font>', styles['h1']))
        elif re.match(r'^[一二三四五六七八九十]、', line):
            elements.append(Paragraph(f'<b>{_strip_markdown(line)}</b>', styles['h2']))
        elif line.startswith('- '):
            content = _strip_markdown(line[2:])
            elements.append(Paragraph(f'• {content}', styles['body']))
        elif line.startswith('> '):
            elements.append(Paragraph(f'<font color="#5a6c7d"><i>{_strip_markdown(line[2:])}</i></font>', styles['quote']))
        else:
            elements.append(Paragraph(_strip_markdown(line), styles['body']))

    if in_table:
        _flush_table()

    return elements


def generate_meeting_pdf(activity, versions, title='活动台账 会议录音总结'):
    """生成录音总结 PDF（可多版本合并）。

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
        raise RuntimeError('未找到中文字体，无法导出 PDF')
    font_name = 'WenQuanYiMicroHei'

    out_dir = os.path.join(current_app.static_folder, 'meetings')
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', (activity.content or '会议总结')[:30])
    file_name = f'{safe_name}_会议总结_{timestamp}.pdf'
    file_path = os.path.join(out_dir, file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=title,
    )

    styles = {
        'h1': ParagraphStyle('h1', fontName=font_name, fontSize=16, leading=22,
                             spaceBefore=12, spaceAfter=6, textColor=HexColor('#1a3a5c')),
        'h2': ParagraphStyle('h2', fontName=font_name, fontSize=14, leading=20,
                             spaceBefore=10, spaceAfter=4, textColor=HexColor('#1a3a5c')),
        'h3': ParagraphStyle('h3', fontName=font_name, fontSize=12, leading=18,
                             spaceBefore=8, spaceAfter=3, textColor=HexColor('#2a5a8c')),
        'h4': ParagraphStyle('h4', fontName=font_name, fontSize=11, leading=16,
                             spaceBefore=6, spaceAfter=2, textColor=HexColor('#5a6c7d')),
        'body': ParagraphStyle('body', fontName=font_name, fontSize=10.5, leading=17,
                               spaceAfter=4, wordWrap='CJK'),
        'quote': ParagraphStyle('quote', fontName=font_name, fontSize=10, leading=16,
                                leftIndent=12, textColor=HexColor('#5a6c7d')),
        'cell': ParagraphStyle('cell', fontName=font_name, fontSize=9, leading=14, wordWrap='CJK'),
    }

    elements = []

    # 封面标题
    elements.append(Paragraph(f'<b>{title}</b>', ParagraphStyle(
        'cover', fontName=font_name, fontSize=20, leading=28,
        alignment=1, textColor=HexColor('#1a3a5c'))))

    # 副标题（活动内容）
    subtitle = activity.content or '活动台账'
    if len(subtitle) > 80:
        subtitle = subtitle[:80] + '...'
    elements.append(Paragraph(subtitle, ParagraphStyle(
        'sub', fontName=font_name, fontSize=12, leading=18,
        alignment=1, textColor=HexColor('#606266'), spaceBefore=6)))

    # 日期信息
    activity_date = activity.date.strftime('%Y年%m月%d日') if activity.date else '未知日期'
    elements.append(Paragraph(
        f'活动时间: {activity_date}    生成时间: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}',
        ParagraphStyle('info', fontName=font_name, fontSize=9, leading=14,
                       alignment=1, textColor=HexColor('#909399'), spaceBefore=4)))
    elements.append(Spacer(1, 16))

    # 各版本内容
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

        # 版本标题
        elements.append(Paragraph(f'<b>【{cfg["label"]}】</b>', ParagraphStyle(
            'ver', fontName=font_name, fontSize=14, leading=20,
            textColor=HexColor('#1a3a5c'), spaceBefore=8, spaceAfter=8)))

        # 解析 Markdown
        elements.extend(_parse_markdown_to_elements(text, styles, font_name))

    doc.build(elements)
    return file_path
