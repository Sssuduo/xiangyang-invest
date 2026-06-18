from models import AdminUser, HomepageConfig, ProvinceInfo
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
    try:
        db.session.execute(db.text(
            "ALTER TABLE homepage_config ADD COLUMN carousel_interval INTEGER DEFAULT 8"
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()  # 列已存在则忽略

    # 创建默认管理员账号
    if not AdminUser.query.filter_by(username='admin').first():
        admin = AdminUser(
            username='admin',
            display_name='管理员'
        )
        admin.set_password('changeme123')
        db.session.add(admin)
        print('[种子数据] 管理员账号已创建: admin / changeme123')

    # 创建默认首页配置
    if not HomepageConfig.query.first():
        config = HomepageConfig()
        db.session.add(config)
        print('[种子数据] 首页配置已初始化')

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
