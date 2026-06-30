from models import AdminUser, BusinessUser, Staff, HomepageConfig, ContactInfo, ProvinceInfo, CityInfo
from models import FollowStatusDict, MeetingStatusDict, OrganizationDict, ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict
from models import ExportTemplate, ExportFieldConfig, ImportFieldConfig
from models import InvestmentActivity, ExportFieldConfigActivity, ImportFieldConfigActivity
from models import ImportFieldConfigDemand, ImportFieldConfigConstruction, ImportFieldConfigWorkProgress
from models import ConstructionProjectTypeDict, DispatchStatusDict, IssueTypeDict, ResolutionStatusDict
from models import ConstructionProject, WorkProgress, ProjectIssue, WorkRoadmapItem
from models import PromoVideo
from extensions import db


# 中国 34 个省级行政区（GB/T 2260 编码）
CHINA_PROVINCES = [
    ('110000', '北京市'), ('120000', '天津市'), ('130000', '河北省'),
    ('140000', '山西省'), ('150000', '内蒙古自治区'), ('210000', '辽宁省'),
    ('220000', '吉林省'), ('230000', '黑龙江省'), ('310000', '上海市'),
    ('320000', '江苏省'), ('330000', '浙江省'), ('340000', '安徽省'),
    ('350000', '福建省'), ('360000', '江西省'), ('370000', '山东省'),
    ('410000', '河南省'), ('420000', '湖北省'), ('430000', '湖南省'),
    ('440000', '广东省'), ('450000', '广西壮族自治区'), ('460000', '海南省'),
    ('500000', '重庆市'), ('510000', '四川省'), ('520000', '贵州省'),
    ('530000', '云南省'), ('540000', '西藏自治区'), ('610000', '陕西省'),
    ('620000', '甘肃省'), ('630000', '青海省'), ('640000', '宁夏回族自治区'),
    ('650000', '新疆维吾尔自治区'), ('710000', '台湾省'),
    ('810000', '香港特别行政区'), ('820000', '澳门特别行政区'),
]

# 湖北省 17 个地市州（GB/T 2260 编码）
HUBEI_CITIES = [
    ('420100', '武汉市'), ('420200', '黄石市'), ('420300', '十堰市'),
    ('420500', '宜昌市'), ('420600', '襄阳市'), ('420700', '鄂州市'),
    ('420800', '荆门市'), ('420900', '孝感市'), ('421000', '荆州市'),
    ('421100', '黄冈市'), ('421200', '咸宁市'), ('421300', '随州市'),
    ('422800', '恩施土家族苗族自治州'), ('429004', '仙桃市'),
    ('429005', '潜江市'), ('429006', '天门市'), ('429021', '神农架林区'),
]


def init_database(app):
    """初始化数据库表和数据"""
    # 创建所有表
    db.create_all()

    # 为已有数据库添加新字段（幂等操作，不丢失数据）
    migrations = [
        "ALTER TABLE homepage_config ADD COLUMN carousel_interval INTEGER DEFAULT 8",
        "ALTER TABLE homepage_config ADD COLUMN carousel_display_mode VARCHAR(20) DEFAULT 'coverflow'",
        "ALTER TABLE homepage_config ADD COLUMN carousel_width INTEGER DEFAULT 85",
        "ALTER TABLE homepage_config ADD COLUMN carousel_height INTEGER DEFAULT 80",
        "ALTER TABLE homepage_config ADD COLUMN presentation_interval INTEGER DEFAULT 5",
        "ALTER TABLE homepage_config ADD COLUMN carousel_autoplay BOOLEAN DEFAULT 1",
        "ALTER TABLE homepage_config ADD COLUMN presentation_autoplay BOOLEAN DEFAULT 1",
        # V3.1: 企业诉求新增字段
        "ALTER TABLE enterprise_demands ADD COLUMN demand_type_code VARCHAR(32) DEFAULT ''",
        "ALTER TABLE enterprise_demands ADD COLUMN unit_code VARCHAR(32) DEFAULT ''",
        # V10.1: 诉求类型支持多选，扩展列宽
        "ALTER TABLE enterprise_demands MODIFY COLUMN demand_type_code VARCHAR(255) DEFAULT ''",
        # V4: 项目投资计划书
        "ALTER TABLE investment_projects ADD COLUMN investment_plan TEXT DEFAULT ''",
        # V5: 导出多模板支持 — 新增 template_id 列，移除旧 field_key 唯一约束
        "ALTER TABLE export_field_config ADD COLUMN template_id INTEGER DEFAULT 1",
        # V5.1: 自定义列 + 投资金额(亿元)
        "ALTER TABLE export_field_config ADD COLUMN is_custom BOOLEAN DEFAULT 0",
        # V8: 项目标签 + 动态标签
        "ALTER TABLE investment_projects ADD COLUMN tags TEXT DEFAULT '[]'",
        "ALTER TABLE investment_activities ADD COLUMN tags TEXT DEFAULT '[]'",
        # 工作进展附件
        "ALTER TABLE work_progress ADD COLUMN files TEXT DEFAULT '[]'",
        # V11: 联系电话
        "ALTER TABLE investment_projects ADD COLUMN person_in_charge_phone VARCHAR(32) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN responsible_person_phone VARCHAR(32) DEFAULT ''",
        # V12: 打印模板 V3 新增字段
        "ALTER TABLE print_template ADD COLUMN sub_title_font_size INTEGER DEFAULT 12",
        "ALTER TABLE print_template ADD COLUMN title_bold BOOLEAN DEFAULT 1",
        "ALTER TABLE print_template ADD COLUMN subtitle_bold BOOLEAN DEFAULT 1",
        "ALTER TABLE print_template ADD COLUMN border_style VARCHAR(20) DEFAULT 'all'",
        "ALTER TABLE print_template ADD COLUMN group_by VARCHAR(64) DEFAULT ''",
        "ALTER TABLE print_template ADD COLUMN template_file VARCHAR(512) DEFAULT ''",
        "ALTER TABLE print_template ADD COLUMN data_start_row INTEGER DEFAULT 3",
        "ALTER TABLE print_template ADD COLUMN header_row INTEGER DEFAULT 2",
        "ALTER TABLE print_template ADD COLUMN title_row INTEGER DEFAULT 1",
        "ALTER TABLE print_template ADD COLUMN has_group_title BOOLEAN DEFAULT 0",
        # V13: Staff 表 + 专班负责人 + 在建项目新字段
        "ALTER TABLE investment_projects ADD COLUMN team_leader_ids TEXT DEFAULT '[]'",
        "ALTER TABLE construction_projects ADD COLUMN construction_location VARCHAR(255) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN start_date VARCHAR(7) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN end_date VARCHAR(7) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN funding_source VARCHAR(255) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN wuhua_platform VARCHAR(8) DEFAULT ''",
        "ALTER TABLE construction_projects ADD COLUMN team_leader_ids TEXT DEFAULT '[]'",
        # V13.4: 招商动态 ↔ 企业诉求 多对多关联表
        "CREATE TABLE IF NOT EXISTS activity_demand_link ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "activity_id INTEGER NOT NULL REFERENCES investment_activities(id) ON DELETE CASCADE, "
        "demand_id INTEGER NOT NULL REFERENCES enterprise_demands(id) ON DELETE CASCADE, "
        "created_at DATETIME DEFAULT (datetime('now')), "
        "UNIQUE(activity_id, demand_id)"
        ")",
    ]
    # 额外：尝试删除旧 field_key 唯一索引（SQLite 可能使用不同索引名）
    drop_index_sqls = [
        "DROP INDEX IF EXISTS ix_export_field_config_field_key",
        "DROP INDEX IF EXISTS uq_export_field_config_field_key",
    ]
    for sql in drop_index_sqls:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
    for sql in migrations:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()  # 列已存在则忽略

    # 创建 contact_info 表（如果不存在——db.create_all 只创建缺失的表）
    try:
        db.create_all()
    except Exception:
        pass

    # 创建默认管理员账号
    if not AdminUser.query.filter_by(username='admin').first():
        admin = AdminUser(
            username='admin',
            display_name='管理员'
        )
        admin.set_password('changeme123')
        db.session.add(admin)
        print('[种子数据] 管理员账号已创建: admin / changeme123')

    # 创建超级管理员 suduo
    if not AdminUser.query.filter_by(username='suduo').first():
        suduo = AdminUser(
            username='suduo',
            display_name='苏铎'
        )
        suduo.set_password('suduo2026')
        db.session.add(suduo)
        print('[种子数据] 超级管理员账号已创建: suduo / suduo2026')

    # 创建默认业务用户
    if not BusinessUser.query.filter_by(username='demo').first():
        demo = BusinessUser(
            username='demo',
            display_name='演示用户',
            is_active=True
        )
        demo.set_password('demo123')
        demo.set_permissions({
            'investment': {'add': True, 'edit': True, 'delete': True, 'batch_delete': True, 'import': True},
            'activity': {'add': True, 'edit': True, 'delete': True, 'batch_delete': True, 'import': True},
            'demand': {'add': True, 'edit': True, 'delete': True, 'batch_delete': True, 'import': True},
            'construction': {'add': True, 'edit': True, 'delete': True, 'batch_delete': True, 'import': True}
        })
        db.session.add(demo)
        print('[种子数据] 业务用户账号已创建: demo / demo123')

    # ---- Staff: 为每个管理员用户创建工作人员记录 ----
    if not Staff.query.first():
        for admin_user in AdminUser.query.all():
            staff = Staff(
                name=admin_user.display_name or admin_user.username,
                position='农高区创建专班工作人员',
                user_id=admin_user.id,
                sort_order=admin_user.id
            )
            db.session.add(staff)
        db.session.commit()
        print(f'[种子数据] 工作人员记录已创建（{AdminUser.query.count()} 人）')

    # 创建默认首页配置
    if not HomepageConfig.query.first():
        config = HomepageConfig()
        db.session.add(config)
        print('[种子数据] 首页配置已初始化')

    # 创建默认联系我们配置
    if not ContactInfo.query.first():
        contact = ContactInfo()
        db.session.add(contact)
        print('[种子数据] 联系我们配置已初始化')

    # 插入中国省份数据（如果不存在）
    china_count = ProvinceInfo.query.filter_by(map_scope='china').count()
    if china_count < 34:
        for code, name in CHINA_PROVINCES:
            if not ProvinceInfo.query.filter_by(region_code=code, map_scope='china').first():
                province = ProvinceInfo(
                    region_code=code,
                    region_name=name,
                    map_scope='china',
                    card_title=name,
                    card_content='',
                    is_highlighted=False
                )
                db.session.add(province)
        print(f'[种子数据] 已插入 {len(CHINA_PROVINCES)} 个省份数据')

    # 插入湖北省城市数据（如果不存在）
    hubei_count = ProvinceInfo.query.filter_by(map_scope='hubei').count()
    if hubei_count < 17:
        for code, name in HUBEI_CITIES:
            if not ProvinceInfo.query.filter_by(region_code=code, map_scope='hubei').first():
                city = ProvinceInfo(
                    region_code=code,
                    region_name=name,
                    map_scope='hubei',
                    card_title=name,
                    card_content='',
                    is_highlighted=False
                )
                db.session.add(city)
        print(f'[种子数据] 已插入 {len(HUBEI_CITIES)} 个湖北城市数据')

    db.session.commit()

    # ---- 招商对接项目库 - 字典种子数据 ----
    _seed_investment_dicts()

    # ---- 导出字段配置 ----
    _seed_export_fields()

    # ---- 导入字段配置 ----
    _seed_import_fields()

    # ---- 招商动态 - 导出字段配置 ----
    _seed_activity_export_fields()

    # ---- 招商动态 - 导入字段配置 ----
    _seed_activity_import_fields()

    # ---- 企业诉求 - 导入字段配置 ----
    _seed_demand_import_fields()

    # ---- 在建项目库 - 字典种子数据 ----
    _seed_construction_dicts()

    # ---- 在建项目 - 导入字段配置 ----
    _seed_construction_import_fields()

    # ---- 工作进展 - 导入字段配置 ----
    _seed_construction_progress_import_fields()

    # ---- 在建项目 - 导出字段配置 ----
    _seed_construction_export_fields()

    # ---- 打印模板（统一模板）字段配置 ----
    _seed_print_fields()
    _seed_construction_print_fields()


def _seed_investment_dicts():
    """初始化招商对接项目库的字典表"""
    # 跟进状态
    follow_statuses = [
        ('follow_focus', '重点跟进', '#e6a23c', 1),
        ('follow_keep', '保持对接', '#909399', 2),
    ]
    for code, name, color, order in follow_statuses:
        if not FollowStatusDict.query.filter_by(code=code).first():
            db.session.add(FollowStatusDict(code=code, name=name, display_color=color, sort_order=order))

    # 上会状态
    meeting_statuses = [
        ('not_meeting', '未上会', '#909399', 1),
        ('recommend_meeting', '推荐上会', '#409eff', 2),
        ('meeting_done', '已上会', '#67c23a', 3),
    ]
    for code, name, color, order in meeting_statuses:
        if not MeetingStatusDict.query.filter_by(code=code).first():
            db.session.add(MeetingStatusDict(code=code, name=name, display_color=color, sort_order=order))

    # 单位字典
    organizations = [
        ('org_shi_taiban', '市委台办'),
        ('org_shi_laoganju', '市委老干局'),
        ('org_shi_rensheju', '市人社局'),
        ('org_shi_nongyenongcunju', '市农业农村局'),
        ('org_quweiban', '区委办'),
        ('org_zhengfuban', '区政府办'),
        ('org_renda', '区人大常委会'),
        ('org_zhengxie', '区政协'),
        ('org_tongzhanbu', '区委统战部'),
        ('org_zuzhibu', '区委组织部'),
        ('org_shehuibu', '区委社会工作部'),
        ('org_laoganju', '区委老干局'),
        ('org_fagaiwei', '区发改委'),
        ('org_kejingju', '区科经局'),
        ('org_caizhengju', '区财政局'),
        ('org_chengguanju', '区城管局'),
        ('org_nongyenongcunju', '区农业农村局'),
        ('org_xiangzhouguotou', '襄州国投'),
        ('org_xiangbeijianyu', '襄北监狱'),
        ('org_zhaoshang', '区招商服务中心'),
        ('org_nonggaoqu', '农高区创建专班'),
        ('org_rensheju', '区人社局'),
        ('org_zhujianju', '区住建局'),
        ('org_shuanggouzhen', '双沟镇'),
        ('org_jiaotongju', '区交通运输局'),
        ('org_yushanzhen', '峪山镇'),
        ('org_shichangjianduju', '区市场监督局'),
    ]
    for i, (code, name) in enumerate(organizations):
        existing = OrganizationDict.query.filter_by(code=code).first()
        if existing:
            existing.name = name
            existing.sort_order = i + 1
        else:
            db.session.add(OrganizationDict(code=code, name=name, sort_order=i + 1))

    # 项目类型
    project_types = [
        ('type_xuqin', '畜禽粪污循环利用'),
        ('type_yangzhi', '养殖种植'),
        ('type_guangai', '农业灌溉装备'),
        ('type_jiegan', '秸秆综合利用'),
        ('type_sheshi', '设施农业'),
        ('type_hongshu', '红薯精深加工'),
        ('type_shipin', '食品加工'),
        ('type_nongji', '农机装备制造'),
        ('type_zhihui', '智慧农业'),
    ]
    for i, (code, name) in enumerate(project_types):
        existing = ProjectTypeDict.query.filter_by(code=code).first()
        if existing:
            existing.name = name
            existing.sort_order = i + 1
        else:
            db.session.add(ProjectTypeDict(code=code, name=name, sort_order=i + 1))

    # 诉求类型
    demand_types = [
        ('demand_land', '用地保障'),
        ('demand_production', '生产要素保障'),
        ('demand_policy', '政策支持'),
        ('demand_platform', '平台公司参与'),
        ('demand_other', '其它'),
    ]
    for i, (code, name) in enumerate(demand_types):
        existing = DemandTypeDict.query.filter_by(code=code).first()
        if existing:
            existing.name = name
            existing.sort_order = i + 1
        else:
            db.session.add(DemandTypeDict(code=code, name=name, sort_order=i + 1))

    # 项目标签
    project_tags = [
        ('tag_shipin', '食品企业走进农高区'),
    ]
    for i, (code, name) in enumerate(project_tags):
        existing = ProjectTagDict.query.filter_by(code=code).first()
        if existing:
            existing.name = name
            existing.sort_order = i + 1
        else:
            db.session.add(ProjectTagDict(code=code, name=name, sort_order=i + 1))

    # 动态标签
    activity_tags = [
        ('activity_tag_waichu', '外出考察'),
        ('activity_tag_daofang', '到访接待'),
        ('activity_tag_shipin', '食品企业走进农高区活动'),
        ('activity_tag_diaodu', '调度推进'),
    ]
    for i, (code, name) in enumerate(activity_tags):
        existing = ActivityTagDict.query.filter_by(code=code).first()
        if existing:
            existing.name = name
            existing.sort_order = i + 1
        else:
            db.session.add(ActivityTagDict(code=code, name=name, sort_order=i + 1))

    db.session.commit()
    print('[种子数据] 招商对接项目库字典已初始化')


def _seed_export_fields():
    """初始化导出字段配置（默认模板 + 字段）"""
    # 先确保默认模板存在
    template = ExportTemplate.query.filter_by(entity_type='investment').first()
    if not template:
        template = ExportTemplate(name='默认导出模板', entity_type='investment')
        db.session.add(template)
        db.session.flush()  # 获取 template.id

    fields = [
        ('order_no', '序号', 60, 1),
        ('project_name', '项目名称', 180, 2),
        ('project_type_code', '项目类型', 120, 3),
        ('invest_enterprise', '投资商名称', 160, 4),
        ('enterprise_info', '企业简介', 300, 5),
        ('project_content', '项目对接及进展情况', 300, 6),
        ('invest_amount', '投资金额(万元)', 120, 7),
        ('invest_amount_yi', '投资金额(亿元)', 120, 8),
        ('follow_status_code', '跟进状态', 100, 9),
        ('meeting_status_code', '上会状态', 100, 10),
        ('recommend_unit_code', '推介单位', 140, 11),
        ('responsible_unit_code', '责任单位', 140, 12),
        ('person_in_charge', '责任人', 80, 13),
        ('project_doc', '项目文档', 200, 14),
        ('first_contact_date', '首次对接时间', 120, 15),
        # 聚合字段
        ('activities', '招商动态', 500, 16),
        ('demands', '企业诉求', 500, 17),
        ('resolution', '解决措施', 500, 18),
    ]
    for field_key, field_label, column_width, sort_order in fields:
        existing = ExportFieldConfig.query.filter_by(template_id=template.id, field_key=field_key).first()
        if existing:
            # 更新已存在字段的标签、列宽和排序（保留 is_visible/is_custom）
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
        else:
            db.session.add(ExportFieldConfig(
                template_id=template.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 导出字段配置已初始化')


def _seed_construction_export_fields():
    """初始化在建项目导出字段配置（默认模板 + 字段）"""
    # 先确保默认模板存在
    template = ExportTemplate.query.filter_by(entity_type='construction').first()
    if not template:
        template = ExportTemplate(name='默认导出模板', entity_type='construction')
        db.session.add(template)
        db.session.flush()

    fields = [
        ('order_no', '序号', 60, 1),
        ('project_name', '在建项目名称', 200, 2),
        ('project_type_code', '项目类型', 120, 3),
        ('dispatch_status_code', '调度状态', 100, 4),
        ('construction_content', '建设内容', 400, 5),
        ('construction_unit', '建设单位', 150, 6),
        ('responsible_unit_code', '责任单位', 150, 7),
        ('responsible_person', '责任人', 80, 8),
        ('responsible_person_phone', '联系电话', 130, 9),
        # 聚合字段
        ('work_progresses', '工作进展', 500, 10),
        ('issues', '存在问题', 500, 11),
        ('work_roadmap', '工作路径图', 400, 12),
    ]
    for field_key, field_label, column_width, sort_order in fields:
        existing = ExportFieldConfig.query.filter_by(template_id=template.id, field_key=field_key).first()
        if existing:
            # 更新已存在字段的标签、列宽和排序（保留 is_visible/is_custom）
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
        else:
            db.session.add(ExportFieldConfig(
                template_id=template.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 在建项目导出字段配置已初始化')


def _seed_print_fields():
    """初始化招商项目打印模板字段配置（使用统一 PrintTemplate）"""
    from models import PrintTemplate, PrintFieldConfig

    # ---- 模板1：默认打印模板（A4，通用） —— 仅当 investment 无任何模板时创建 ----
    template1 = PrintTemplate.query.filter_by(entity_type='investment').first()
    if template1:
        template1 = template1  # 已有模板，不创建默认模板
    else:
        template1 = PrintTemplate(name='默认打印模板', entity_type='investment')
        db.session.add(template1)
        db.session.flush()

    fields_v1 = [
        ('order_no', '序号', 60, 1),
        ('project_name', '项目名称', 180, 2),
        ('project_type_code', '项目类型', 120, 3),
        ('invest_enterprise', '投资商名称', 160, 4),
        ('enterprise_info', '企业简介', 300, 5),
        ('project_content', '项目对接及进展情况', 300, 6),
        ('invest_amount', '投资金额(万元)', 120, 7),
        ('invest_amount_yi', '投资金额(亿元)', 120, 8),
        ('follow_status_code', '跟进状态', 100, 9),
        ('meeting_status_code', '上会状态', 100, 10),
        ('recommend_unit_code', '推介单位', 140, 11),
        ('responsible_unit_code', '责任单位', 140, 12),
        ('person_in_charge', '责任人', 80, 13),
        ('_combined_contact', '责任单位/责任人/联系方式', 200, 14),
        ('person_in_charge_phone', '联系电话', 130, 15),
        ('project_doc', '项目文档', 200, 16),
        ('first_contact_date', '首次对接时间', 120, 17),
        ('activities', '招商动态', 500, 18),
        ('demands', '企业诉求', 500, 19),
        ('resolution', '解决措施', 500, 20),
    ]
    for field_key, field_label, column_width, sort_order in fields_v1:
        existing = PrintFieldConfig.query.filter_by(template_id=template1.id, field_key=field_key).first()
        if existing:
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
        else:
            db.session.add(PrintFieldConfig(
                template_id=template1.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))

    # ---- 模板2：内置 A3 模板 [(附件1)襄州农高区招商引资项目清单] ----
    BUILTIN_A3_NAME = '(附件1)襄州农高区招商引资项目清单'
    BUILTIN_A3_NAME_ALT = '[(附件1)襄州农高区招商引资项目清单]'
    template2 = PrintTemplate.query.filter_by(entity_type='investment').filter(
        PrintTemplate.name.in_([BUILTIN_A3_NAME, BUILTIN_A3_NAME_ALT, 'A3 招商项目清单'])
    ).first()
    if not template2:
        template2 = PrintTemplate(
            name=BUILTIN_A3_NAME,
            entity_type='investment',
            paper_size='A3',
            orientation='landscape',
            font_family='宋体',
            font_size=14,
            title_font_family='宋体',
            title_font_size=36,
            table_header_font_family='宋体',
            table_header_font_size=18,
            cell_font_family='宋体',
            cell_font_size=14,
            header_font_size=18,
            sub_title_font_size=28,
            title_bold=True,
            subtitle_bold=True,
            border_style='all',
            margin_top=0.197,
            margin_bottom=0.118,
            margin_left=0.354,
            margin_right=0.118,
        )
        db.session.add(template2)
        db.session.flush()
    else:
        # 确保已有模板的格式参数保持最新
        template2.paper_size = 'A3'
        template2.orientation = 'landscape'
        template2.font_family = '宋体'
        template2.font_size = 14
        template2.title_font_family = '宋体'
        template2.title_font_size = 36
        template2.table_header_font_family = '宋体'
        template2.table_header_font_size = 18
        template2.cell_font_family = '宋体'
        template2.cell_font_size = 14
        template2.header_font_size = 18
        template2.sub_title_font_size = 28
        template2.title_bold = True
        template2.subtitle_bold = True
        template2.border_style = 'all'
        template2.margin_top = 0.197
        template2.margin_bottom = 0.118
        template2.margin_left = 0.354
        template2.margin_right = 0.118

    fields_v2 = [
        # (field_key, field_label, column_width, sort_order)
        # 列宽按 Excel 原始比例换算（A3 横向，10 列总宽≈664字符单位）
        ('order_no',          '序号',               60,   1),
        ('project_name',      '项目名称',           230,  2),
        ('invest_enterprise', '投资商名称',         102,  3),
        ('enterprise_info',   '企业简介',           500,  4),
        ('project_content',   '项目内容',           549,  5),
        ('activities',        '项目对接及进展情况', 1107, 6),
        ('demands',           '企业诉求',           1105, 7),
        ('resolution',        '拟解决措施',         695,  8),
        ('_combined_contact', '责任单位/责任人/联系方式', 164, 9),
        ('_team_followers',   '专班跟进人',         151,  10),
    ]
    for field_key, field_label, column_width, sort_order in fields_v2:
        existing = PrintFieldConfig.query.filter_by(template_id=template2.id, field_key=field_key).first()
        if existing:
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
            if not existing.is_visible:
                existing.is_visible = True
        else:
            db.session.add(PrintFieldConfig(
                template_id=template2.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))

    # ---- A3 模板文件映射 ----
    template_a3_file = '/static/uploads/templates/A3_投资清单_模板.xlsx'
    # 始终更新内置模板的文件路径和名称
    template2.name = BUILTIN_A3_NAME
    template2.template_file = template_a3_file
    template2.data_start_row = 3
    template2.header_row = 2
    template2.title_row = 1
    template2.has_group_title = True
    template2.cell_font_family = '宋体'
    template2.cell_font_size = 18
    template2.table_header_font_family = '宋体'
    template2.table_header_font_size = 18

    # 列映射：模板列字母 → field_key
    from models import TemplateFieldMapping
    a3_column_mappings = [
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
    for idx, (col_letter, col_header, field_key) in enumerate(a3_column_mappings):
        existing_m = TemplateFieldMapping.query.filter_by(
            template_id=template2.id, column_letter=col_letter).first()
        if existing_m:
            existing_m.column_header = col_header
            existing_m.field_key = field_key
            existing_m.sort_order = idx
        else:
            db.session.add(TemplateFieldMapping(
                template_id=template2.id,
                column_letter=col_letter,
                column_header=col_header,
                field_key=field_key,
                sort_order=idx,
            ))

    db.session.commit()
    print('[种子数据] 招商项目打印模板字段已初始化（默认模板 + A3 招商项目清单含文件映射）')


def _seed_construction_print_fields():
    """初始化在建项目打印模板字段配置（使用统一 PrintTemplate）"""
    from models import PrintTemplate, PrintFieldConfig

    template = PrintTemplate.query.filter_by(entity_type='construction').first()
    if not template:
        template = PrintTemplate(name='默认打印模板', entity_type='construction')
        db.session.add(template)
        db.session.flush()

    fields = [
        ('order_no', '序号', 60, 1),
        ('project_name', '在建项目名称', 200, 2),
        ('project_type_code', '项目类型', 120, 3),
        ('dispatch_status_code', '调度状态', 100, 4),
        ('construction_content', '建设内容', 400, 5),
        ('construction_unit', '建设单位', 150, 6),
        ('responsible_unit_code', '责任单位', 150, 7),
        ('responsible_person', '责任人', 80, 8),
        ('responsible_person_phone', '联系电话', 130, 9),
        ('_combined_contact', '责任单位/责任人/联系方式', 200, 10),
        ('work_progresses', '工作进展', 500, 11),
        ('issues', '存在问题', 500, 12),
        ('work_roadmap', '工作路径图', 400, 13),
    ]
    for field_key, field_label, column_width, sort_order in fields:
        existing = PrintFieldConfig.query.filter_by(template_id=template.id, field_key=field_key).first()
        if existing:
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
        else:
            db.session.add(PrintFieldConfig(
                template_id=template.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 在建项目打印模板字段已初始化')

    # ---- 内置 A3 模板 [(附件2)农高区2026年在建项目统计表] ----
    from models import TemplateFieldMapping
    BUILTIN_CONSTRUCTION_NAME = '(附件2)农高区2026年在建项目统计表'
    BUILTIN_CONSTRUCTION_NAME_ALT = '[(附件2)农高区2026年在建项目统计表]'
    template_cons = PrintTemplate.query.filter_by(entity_type='construction').filter(
        PrintTemplate.name.in_([BUILTIN_CONSTRUCTION_NAME, BUILTIN_CONSTRUCTION_NAME_ALT])
    ).first()
    if not template_cons:
        template_cons = PrintTemplate(
            name=BUILTIN_CONSTRUCTION_NAME,
            entity_type='construction',
            paper_size='A3',
            orientation='landscape',
            font_family='微软雅黑',
            font_size=12,
            title_font_family='微软雅黑',
            title_font_size=14,
            table_header_font_family='微软雅黑',
            table_header_font_size=12,
            cell_font_family='微软雅黑',
            cell_font_size=12,
        )
        db.session.add(template_cons)
        db.session.flush()

    # 模板文件映射
    template_cons_file = '/static/uploads/templates/A3_在建项目_模板.xlsx'
    template_cons.name = BUILTIN_CONSTRUCTION_NAME
    template_cons.template_file = template_cons_file
    template_cons.data_start_row = 4
    template_cons.header_row = 3
    template_cons.title_row = 2
    template_cons.has_group_title = True
    template_cons.cell_font_family = '微软雅黑'
    template_cons.cell_font_size = 12
    template_cons.table_header_font_family = '微软雅黑'
    template_cons.table_header_font_size = 12
    template_cons.sub_title_font_size = 20
    template_cons.subtitle_bold = True

    # 列映射：模板列字母 → field_key（14列 A-N）
    cons_column_mappings = [
        ('A', '序号', 'order_no'),
        ('B', '项目名称', 'project_name'),
        ('C', '建设地点', 'construction_location'),
        ('D', '开工时间', 'start_date'),
        ('E', '竣工时间', 'end_date'),
        ('F', '资金来源', 'funding_source'),
        ('G', '建设内容', 'construction_content'),
        ('H', '工作路径图（具体时间节点）', 'work_roadmap'),
        ('I', '周工作进展', 'work_progresses'),
        ('J', '建设单位', 'construction_unit'),
        ('K', '责任单位/责任人', '_combined_contact'),
        ('L', '备注（存在的问题）', 'issues'),
        ('M', '五化平台', 'wuhua_platform'),
        ('N', '专班负责人', '_team_follower_names'),
    ]
    for idx, (col_letter, col_header, field_key) in enumerate(cons_column_mappings):
        existing_m = TemplateFieldMapping.query.filter_by(
            template_id=template_cons.id, column_letter=col_letter).first()
        if existing_m:
            existing_m.column_header = col_header
            existing_m.field_key = field_key
            existing_m.sort_order = idx
        else:
            db.session.add(TemplateFieldMapping(
                template_id=template_cons.id,
                column_letter=col_letter,
                column_header=col_header,
                field_key=field_key,
                sort_order=idx,
            ))

    # 为 A3 模板也创建 PrintFieldConfig 记录（管理后台字段映射下拉框需要）
    cons_a3_fields = [
        ('order_no', '序号', 60, 1),
        ('project_name', '在建项目名称', 200, 2),
        ('project_type_code', '项目类型', 120, 3),
        ('dispatch_status_code', '调度状态', 100, 4),
        ('construction_content', '建设内容', 400, 5),
        ('construction_unit', '建设单位', 150, 6),
        ('responsible_unit_code', '责任单位', 150, 7),
        ('responsible_person', '责任人', 80, 8),
        ('responsible_person_phone', '联系电话', 130, 9),
        ('_combined_contact', '责任单位/责任人/联系方式', 200, 10),
        ('work_progresses', '工作进展', 500, 11),
        ('issues', '存在问题', 500, 12),
        ('work_roadmap', '工作路径图', 400, 13),
    ]
    for field_key, field_label, column_width, sort_order in cons_a3_fields:
        existing = PrintFieldConfig.query.filter_by(
            template_id=template_cons.id, field_key=field_key).first()
        if existing:
            existing.field_label = field_label
            existing.column_width = column_width
            existing.sort_order = sort_order
        else:
            db.session.add(PrintFieldConfig(
                template_id=template_cons.id,
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))

    db.session.commit()
    print('[种子数据] 在建项目 A3 打印模板已初始化（含文件映射 + 字段配置，14列）')


def _seed_import_fields():
    """初始化导入字段配置"""
    fields = [
        ('order_no', '顺序号', True, False, 1),
        ('project_name', '项目名称', True, True, 2),
        ('project_type_code', '项目类型', True, True, 3),
        ('invest_enterprise', '投资商名称', True, True, 4),
        ('enterprise_info', '企业简介', True, True, 5),
        ('project_content', '项目内容', True, True, 6),
        ('invest_amount', '投资金额(万元)', True, True, 7),
        ('follow_status_code', '跟进状态', True, True, 8),
        ('meeting_status_code', '上会状态', True, False, 9),
        ('recommend_unit_code', '推介单位', True, False, 10),
        ('responsible_unit_code', '责任单位', True, True, 11),
        ('person_in_charge', '责任人', True, False, 12),
        ('first_contact_date', '首次对接时间', True, False, 13),
    ]
    for field_key, field_label, is_enabled, is_required, sort_order in fields:
        if not ImportFieldConfig.query.filter_by(field_key=field_key).first():
            db.session.add(ImportFieldConfig(
                field_key=field_key,
                field_label=field_label,
                is_enabled=is_enabled,
                is_required=is_required,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 导入字段配置已初始化')


def _seed_activity_export_fields():
    """初始化招商动态导出字段配置"""
    fields = [
        ('project_name', '所属项目', 180, 1),
        ('date', '日期', 160, 2),
        ('content', '动态内容', 400, 3),
        ('files', '附件', 200, 4),
    ]
    for field_key, field_label, column_width, sort_order in fields:
        if not ExportFieldConfigActivity.query.filter_by(field_key=field_key).first():
            db.session.add(ExportFieldConfigActivity(
                field_key=field_key,
                field_label=field_label,
                is_visible=True,
                column_width=column_width,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 招商动态导出字段配置已初始化')


def _seed_activity_import_fields():
    """初始化招商动态导入字段配置"""
    fields = [
        ('project_id', '项目ID', True, False, 0),     # 数据库主键，模板下载时自动填入
        ('project_name', '所属项目', True, True, 1),
        ('date', '日期', True, False, 2),              # 日期选填
        ('content', '动态内容', True, True, 3),
        ('files', '附件(URL)', True, False, 4),
    ]
    for field_key, field_label, is_enabled, is_required, sort_order in fields:
        if not ImportFieldConfigActivity.query.filter_by(field_key=field_key).first():
            db.session.add(ImportFieldConfigActivity(
                field_key=field_key,
                field_label=field_label,
                is_enabled=is_enabled,
                is_required=is_required,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 招商动态导入字段配置已初始化')


def _seed_demand_import_fields():
    """初始化企业诉求导入字段配置"""
    fields = [
        ('project_id', '项目ID', True, True, 0),
        ('project_name', '所属项目', True, False, 1),
        ('demand_type_code', '诉求类型', True, False, 2),
        ('demand_content', '诉求内容', True, True, 3),
        ('unit_code', '对接单位', True, False, 4),
        ('status', '状态', True, False, 5),
    ]
    for field_key, field_label, is_enabled, is_required, sort_order in fields:
        if not ImportFieldConfigDemand.query.filter_by(field_key=field_key).first():
            db.session.add(ImportFieldConfigDemand(
                field_key=field_key,
                field_label=field_label,
                is_enabled=is_enabled,
                is_required=is_required,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 企业诉求导入字段配置已初始化')


def _seed_construction_dicts():
    """初始化在建项目库的字典表"""
    # 在建项目类型
    project_types = [
        ('type_kechuang', '科创类', 1),
        ('type_zhongyang', '现代种养类', 2),
        ('type_chanye', '产业类', 3),
        ('type_jichusheshi', '基础设施类', 4),
        ('type_shifan', '示范类', 5),
    ]
    for code, name, order in project_types:
        if not ConstructionProjectTypeDict.query.filter_by(code=code).first():
            db.session.add(ConstructionProjectTypeDict(code=code, name=name, sort_order=order))

    # 调度状态
    dispatch_statuses = [
        ('dispatching', '调度中', 1),
        ('no_dispatch', '不予调度', 2),
        ('exited', '退出调度', 3),
    ]
    for code, name, order in dispatch_statuses:
        if not DispatchStatusDict.query.filter_by(code=code).first():
            db.session.add(DispatchStatusDict(code=code, name=name, sort_order=order))

    # 问题类型
    issue_types = [
        ('issue_fund', '资金问题', 1),
    ]
    for code, name, order in issue_types:
        if not IssueTypeDict.query.filter_by(code=code).first():
            db.session.add(IssueTypeDict(code=code, name=name, sort_order=order))

    # 调度问题状态（独立于项目调度状态）
    resolution_statuses = [
        ('pending', '待处理', '#f56c6c', 1),
        ('processing', '处理中', '#e6a23c', 2),
        ('resolved', '已完成', '#67c23a', 3),
    ]
    for code, name, color, order in resolution_statuses:
        existing = ResolutionStatusDict.query.filter_by(code=code).first()
        if existing:
            # V12.1: 更新标签名称（待处理→待回应, 处理中→协调中, 已解决→已回应）
            if existing.name != name:
                existing.name = name
                existing.display_color = color
        else:
            db.session.add(ResolutionStatusDict(code=code, name=name, display_color=color, sort_order=order))

    db.session.commit()
    print('[种子数据] 在建项目库字典已初始化')


def _seed_construction_import_fields():
    """初始化在建项目导入字段配置"""
    fields = [
        ('project_name', '项目名称', True, True, 1),
        ('project_type_code', '项目类型', True, True, 2),
        ('dispatch_status_code', '调度状态', True, True, 3),
        ('construction_content', '建设内容', True, False, 4),
        ('construction_unit', '建设单位', True, False, 5),
        ('responsible_unit_code', '责任单位', True, False, 6),
        ('responsible_person', '责任人', True, False, 7),
        ('responsible_person_phone', '联系电话', True, False, 8),
        ('roadmap_text', '工作路径', True, False, 9),
        ('progress_text', '工作进展', True, False, 10),
        ('issue_text', '调度问题', True, False, 11),
    ]
    for field_key, field_label, is_enabled, is_required, sort_order in fields:
        if not ImportFieldConfigConstruction.query.filter_by(field_key=field_key).first():
            db.session.add(ImportFieldConfigConstruction(
                field_key=field_key,
                field_label=field_label,
                is_enabled=is_enabled,
                is_required=is_required,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 在建项目导入字段配置已初始化')


def _seed_construction_progress_import_fields():
    """初始化工作进展导入字段配置"""
    fields = [
        ('project_name', '所属项目', True, True, 1),
        ('start_date', '开始日期', True, True, 2),
        ('end_date', '结束日期', True, True, 3),
        ('content', '进展内容', True, True, 4),
    ]
    for field_key, field_label, is_enabled, is_required, sort_order in fields:
        if not ImportFieldConfigWorkProgress.query.filter_by(field_key=field_key).first():
            db.session.add(ImportFieldConfigWorkProgress(
                field_key=field_key,
                field_label=field_label,
                is_enabled=is_enabled,
                is_required=is_required,
                sort_order=sort_order
            ))
    db.session.commit()
    print('[种子数据] 工作进展导入字段配置已初始化')
