"""导入招商项目打印模板：农高区招商引资项目研判清单（A4）"""
import sys, os, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app import create_app
from extensions import db
from models import PrintTemplate, PrintFieldConfig, TemplateFieldMapping
from datetime import datetime

SOURCE_EXCEL = r'H:\桌面\农高区招商引资项目研判清单.xlsx'
TEMPLATE_NAME = '农高区招商引资项目研判清单'
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'uploads', 'templates')

app = create_app()
with app.app_context():
    # 1. 复制 Excel 文件到 templates 目录
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest_filename = f'{timestamp}_imported_a4.xlsx'
    dest_path = os.path.join(TEMPLATE_DIR, dest_filename)
    shutil.copy2(SOURCE_EXCEL, dest_path)
    rel_path = f'/static/uploads/templates/{dest_filename}'
    print(f'[OK] 文件已复制: {dest_path}')

    # 2. 创建 PrintTemplate 记录
    template = PrintTemplate(
        name=TEMPLATE_NAME,
        entity_type='investment',
        paper_size='A4',
        orientation='landscape',
        font_family='宋体',
        font_size=12,
        title_font_family='宋体',
        title_font_size=24,
        table_header_font_family='宋体',
        table_header_font_size=14,
        cell_font_family='宋体',
        cell_font_size=12,
        header_font_size=14,
        sub_title_font_size=16,
        title_bold=True,
        subtitle_bold=True,
        border_style='all',
        margin_top=0.3,
        margin_bottom=0.3,
        margin_left=0.4,
        margin_right=0.4,
        template_file=rel_path,
        data_start_row=3,
        header_row=2,
        title_row=1,
        has_group_title=False,
    )
    db.session.add(template)
    db.session.flush()
    print(f'[OK] 模板已创建: id={template.id}, name={TEMPLATE_NAME}, paper=A4')

    # 3. 创建字段配置（与 Excel 列匹配的字段）
    fields = [
        ('order_no',          '序号',               60,   1),
        ('project_name',      '项目名称',           230,  2),
        ('invest_enterprise', '投资商名称',         160,  3),
        ('enterprise_info',   '企业简介',           500,  4),
        ('project_content',   '项目内容',           549,  5),
        ('activities',        '项目对接及进展情况', 800,  6),
        ('demands',           '企业诉求',           800,  7),
        ('resolution',        '拟解决措施',         500,  8),
        ('_combined_contact', '责任单位/责任人/联系方式', 164, 9),
        ('_team_followers',   '专班跟进人',         151,  10),
    ]
    for field_key, field_label, column_width, sort_order in fields:
        db.session.add(PrintFieldConfig(
            template_id=template.id,
            field_key=field_key,
            field_label=field_label,
            is_visible=True,
            column_width=column_width,
            sort_order=sort_order,
        ))
    print(f'[OK] {len(fields)} 个字段配置已创建')

    # 4. 创建列映射（解析 Excel 的 header_row=2）
    column_mappings = [
        ('A', '序号',               'order_no'),
        ('B', '项目名称',           'project_name'),
        ('C', '投资商名称',         'invest_enterprise'),
        ('D', '企业简介',           'enterprise_info'),
        ('E', '项目内容',           'project_content'),
        ('F', '项目对接及进展情况', 'activities'),
        ('G', '企业诉求',           'demands'),
        ('H', '拟解决措施',         'resolution'),
        ('I', '责任单位',           '_combined_contact'),
        ('J', '专班跟进人',         '_team_followers'),
    ]
    for idx, (col_letter, col_header, field_key) in enumerate(column_mappings):
        db.session.add(TemplateFieldMapping(
            template_id=template.id,
            column_letter=col_letter,
            column_header=col_header,
            field_key=field_key,
            sort_order=idx,
        ))
    print(f'[OK] {len(column_mappings)} 条列映射已创建')

    db.session.commit()
    print(f'\n[完成] 打印模板 "{TEMPLATE_NAME}" 导入成功！')
    print(f'  模板ID: {template.id}')
    print(f'  纸张: A4 横向')
    print(f'  文件: {rel_path}')
    print(f'  数据起始行: 3 | 标题行: 1 | 表头行: 2')
    print(f'  列映射: A-J 全部已匹配')
