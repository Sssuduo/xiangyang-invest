"""生产环境导入招商项目打印模板：农高区招商引资项目研判清单（A4）
仅做 DB 插入，模板文件已通过 SCP 上传到 uploads/templates/ 目录
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app import create_app
from extensions import db
from models import PrintTemplate, PrintFieldConfig, TemplateFieldMapping
from datetime import datetime

TEMPLATE_FILE = '/static/uploads/templates/20260630_163709_imported_a4.xlsx'
TEMPLATE_NAME = '农高区招商引资项目研判清单'

app = create_app()
with app.app_context():
    # 检查是否已存在同名模板
    existing = PrintTemplate.query.filter_by(name=TEMPLATE_NAME, entity_type='investment').first()
    if existing:
        print(f'[SKIP] Template "{TEMPLATE_NAME}" already exists (id={existing.id})')
        sys.exit(0)

    # 1. 创建 PrintTemplate
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
        template_file=TEMPLATE_FILE,
        data_start_row=3,
        header_row=2,
        title_row=1,
        has_group_title=False,
    )
    db.session.add(template)
    db.session.flush()
    print(f'[OK] Created template id={template.id}')

    # 2. 字段配置
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
    for fk, fl, cw, so in fields:
        db.session.add(PrintFieldConfig(
            template_id=template.id,
            field_key=fk, field_label=fl,
            is_visible=True, column_width=cw, sort_order=so,
        ))
    print(f'[OK] {len(fields)} field configs')

    # 3. 列映射
    mappings = [
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
    for idx, (cl, ch, fk) in enumerate(mappings):
        db.session.add(TemplateFieldMapping(
            template_id=template.id,
            column_letter=cl, column_header=ch,
            field_key=fk, sort_order=idx,
        ))
    print(f'[OK] {len(mappings)} column mappings')

    db.session.commit()
    print(f'\n[DONE] Template "{TEMPLATE_NAME}" imported!')
