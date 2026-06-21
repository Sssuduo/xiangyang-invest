"""
内容数据迁移脚本
将 国家农高区、襄阳农高区介绍、联系我们 的内容迁移到业务系统对应表中
幂等操作，可重复执行
"""
import sys
from app import create_app
from extensions import db
from models import (
    HomepageConfig, ContactInfo, CarouselPage,
    ProvinceInfo, CityInfo
)

app = create_app()


def migrate_homepage():
    """首页配置迁移"""
    config = HomepageConfig.query.first()
    if not config:
        config = HomepageConfig()
        db.session.add(config)
        print('[首页] 创建新记录')

    changed = False

    defaults = {
        'title_text': '襄阳农高区',
        'subtitle_text': '招商服务一站式平台',
    }

    for field, default_val in defaults.items():
        current = getattr(config, field, '')
        if not current or current == '':
            setattr(config, field, default_val)
            print(f'[首页] {field}: 空 → "{default_val}"')
            changed = True
        else:
            print(f'[首页] {field}: 已有值 "{current}"，跳过')

    if not config.background_image:
        config.background_image = ''
        changed = True

    if changed:
        db.session.commit()
        print('[首页] [OK] 已更新')
    else:
        print('[首页] [OK] 无需更新')


def migrate_contact():
    """联系我们迁移"""
    info = ContactInfo.query.first()
    if not info:
        info = ContactInfo()
        db.session.add(info)
        print('[联系我们] 创建新记录')

    changed = False

    defaults = {
        'name': '任伟',
        'title': '襄阳农业科技园区服务中心 副主任',
        'phone': '13197191493',
        'email': 'renwei@xiangyang.gov.cn',
        'intro': (
            '负责襄阳国家农业科技园区招商引资、企业对接与项目服务工作。\n'
            '欢迎各界企业家、投资机构莅临考察，共谋发展。\n'
            '襄阳农高区将以最大的诚意、最优的服务，为每一位投资者创造最好的发展环境。'
        ),
    }

    for field, default_val in defaults.items():
        current = getattr(info, field, '')
        if not current or current == '':
            setattr(info, field, default_val)
            print(f'[联系我们] {field}: 空 → "{default_val[:40]}..."' if len(default_val) > 40 else f'[联系我们] {field}: 空 → "{default_val}"')
            changed = True
        else:
            print(f'[联系我们] {field}: 已有值，跳过')

    if changed:
        db.session.commit()
        print('[联系我们] [OK] 已更新')
    else:
        print('[联系我们] [OK] 无需更新')


def migrate_carousel_pages():
    """襄阳农高区介绍 —— 为轮播页填充富文本内容"""
    pages = CarouselPage.query.order_by(CarouselPage.sort_order).all()

    if not pages:
        print('[轮播页] 无记录，跳过')
        return

    # 襄阳农高区介绍内容（按轮播页顺序）
    intro_contents = {
        # 第1页：襄阳农高区概况
        1: (
            '<h2 style="color: #1a3a5c;">襄阳国家农业科技园区</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '<strong>襄阳国家农业科技园区</strong>（简称"襄阳农高区"）位于湖北省襄阳市，'
            '是经科技部批准建设的<strong>国家级农业科技园区</strong>。园区以现代农业科技创新为引领，'
            '致力于打造全国一流的农业高新技术产业示范区。</p>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '园区规划面积<strong>120平方公里</strong>，涵盖核心区、示范区和辐射区三大功能板块，'
            '形成了"一心、两轴、多基地"的空间布局。</p>'
        ),
        # 第2页：区位优势
        2: (
            '<h2 style="color: #1a3a5c;">区位优势</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '襄阳地处<strong>中国中部</strong>，素有"南船北马、七省通衢"之称，'
            '是汉江流域中心城市和湖北省域副中心城市。</p>'
            '<ul style="font-size: 15px; line-height: 2;">'
            '<li>🚄 <strong>高铁枢纽</strong>：郑万高铁、西武高铁、呼南高铁交汇</li>'
            '<li>✈️ <strong>航空交通</strong>：襄阳刘集机场通达全国主要城市</li>'
            '<li>🚢 <strong>水运优势</strong>：汉江黄金水道直达长江</li>'
            '<li>🛣️ <strong>公路网络</strong>：二广、福银、麻竹等多条高速交汇</li>'
            '</ul>'
        ),
        # 第3页：产业基础
        3: (
            '<h2 style="color: #1a3a5c;">产业基础</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '襄阳是<strong>全国重要的商品粮基地</strong>和现代农业示范区，'
            '拥有丰富的农业资源和雄厚的产业基础。</p>'
            '<ul style="font-size: 15px; line-height: 2;">'
            '<li>🌾 <strong>粮食产业</strong>：常年粮食产量超百亿斤</li>'
            '<li>🐄 <strong>畜禽养殖</strong>：规模化养殖水平居全省前列</li>'
            '<li>🌿 <strong>特色种植</strong>：茶叶、食用菌、中药材等特色产业</li>'
            '<li>🔬 <strong>科技支撑</strong>：与华中农业大学、省农科院深度合作</li>'
            '</ul>'
        ),
        # 第4页：重点招商方向
        4: (
            '<h2 style="color: #1a3a5c;">重点招商方向</h2>'
            '<ul style="font-size: 15px; line-height: 2;">'
            '<li>🐷 <strong>畜禽粪污循环利用</strong>：建设有机肥生产、沼气能源化利用项目</li>'
            '<li>🐔 <strong>养殖种植一体化</strong>：现代化养殖基地与种植园区配套建设</li>'
            '<li>💧 <strong>农业灌溉装备</strong>：高效节水灌溉设备研发与制造</li>'
            '<li>🌾 <strong>秸秆综合利用</strong>：秸秆饲料化、能源化、基料化加工</li>'
            '<li>🏭 <strong>设施农业</strong>：智能温室、植物工厂、垂直农业</li>'
            '</ul>'
            '<p style="font-size: 16px; line-height: 1.8; margin-top: 12px;">'
            '园区提供<strong>土地、税收、人才、金融</strong>等全方位政策支持，'
            '诚邀各界投资者共建现代农业产业高地。</p>'
        ),
        # 第5页：政策支持
        5: (
            '<h2 style="color: #1a3a5c;">政策支持</h2>'
            '<ul style="font-size: 15px; line-height: 2;">'
            '<li>🏗️ <strong>土地政策</strong>：优先保障农业高新项目用地指标</li>'
            '<li>💰 <strong>财税优惠</strong>：企业所得税"两免三减半"</li>'
            '<li>🎓 <strong>人才引进</strong>：高层次人才享受安家补贴、子女入学等优待</li>'
            '<li>🔬 <strong>科技扶持</strong>：研发费用加计扣除，创新平台最高500万元奖励</li>'
            '<li>🏦 <strong>金融服务</strong>：产业发展基金、贷款贴息、融资担保</li>'
            '</ul>'
        ),
        # 第6-18页：各产业详细介绍
        6: (
            '<h2 style="color: #1a3a5c;">畜禽粪污循环利用</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '依托襄阳市规模化养殖基地，建设畜禽粪污集中处理中心，'
            '年产有机肥<strong>20万吨</strong>，配套沼气发电项目，'
            '实现养殖废弃物资源化利用。</p>'
        ),
        7: (
            '<h2 style="color: #1a3a5c;">智慧养殖基地</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '建设现代化生猪、肉牛、蛋鸡养殖基地，采用物联网监控、'
            '自动化饲喂、环境智能控制系统，打造数字化养殖示范场。</p>'
        ),
        8: (
            '<h2 style="color: #1a3a5c;">农业灌溉装备制造</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '引进国内外先进灌溉装备制造企业，生产智能水肥一体机、'
            '滴灌管材、喷灌机组等产品，服务华中地区高效节水农业。</p>'
        ),
        9: (
            '<h2 style="color: #1a3a5c;">秸秆综合利用</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '建设秸秆收储运体系，发展秸秆饲料、秸秆板材、秸秆生物质燃料等'
            '深加工项目，年处理秸秆能力<strong>50万吨</strong>。</p>'
        ),
        10: (
            '<h2 style="color: #1a3a5c;">设施农业示范园</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '规划建设<strong>5000亩</strong>智能温室集群，涵盖蔬菜工厂、'
            '花卉种植、种苗繁育等功能区，配套环境自动控制和水肥一体化系统。</p>'
        ),
        11: (
            '<h2 style="color: #1a3a5c;">农产品精深加工</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '依托本地丰富的农产品资源，发展粮食加工、油脂加工、'
            '畜禽屠宰深加工等产业，延伸农业产业链条，提升附加值。</p>'
        ),
        12: (
            '<h2 style="color: #1a3a5c;">冷链物流中心</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '建设<strong>10万吨</strong>级冷链仓储物流基地，配套冷藏库、'
            '冷冻库、气调库及冷链配送车辆，打造鄂西北农产品冷链物流枢纽。</p>'
        ),
        13: (
            '<h2 style="color: #1a3a5c;">农业科技研发</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '与华中农业大学共建<strong>襄阳农业研究院</strong>，'
            '设立博士后工作站和院士专家工作站，开展种业创新、'
            '智慧农业、绿色防控等关键技术攻关。</p>'
        ),
        14: (
            '<h2 style="color: #1a3a5c;">电商与品牌建设</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '打造"襄农优品"区域公用品牌，建设农产品电商产业园，'
            '引入直播带货、社区团购等新业态，推动襄阳农产品走向全国。</p>'
        ),
        15: (
            '<h2 style="color: #1a3a5c;">农旅融合发展</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '依托园区生态资源，开发农业观光、农事体验、科普研学等'
            '旅游产品，建设田园综合体，实现一二三产业融合发展。</p>'
        ),
        16: (
            '<h2 style="color: #1a3a5c;">国际合作</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '积极对接"一带一路"农业合作，引进以色列、荷兰先进农业技术，'
            '建设中外农业科技合作园区，推动襄阳农业国际化发展。</p>'
        ),
        17: (
            '<h2 style="color: #1a3a5c;">营商环境</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '襄阳农高区实行<strong>"一站式"服务</strong>，项目审批全程代办，'
            '涉企收费清单管理，建立企业服务专员制度，'
            '做到"有求必应、无事不扰"。</p>'
        ),
        18: (
            '<h2 style="color: #1a3a5c;">联系我们</h2>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '<strong>襄阳农业科技园区服务中心</strong></p>'
            '<p style="font-size: 16px; line-height: 1.8;">'
            '📍 地址：湖北省襄阳市襄州区航空路169号<br>'
            '📞 电话：0710-1234567<br>'
            '📧 邮箱：invest@xiangyang.gov.cn</p>'
            '<p style="font-size: 16px; line-height: 1.8; margin-top: 12px;">'
            '欢迎各界朋友莅临考察，投资兴业，共赢未来！</p>'
        ),
    }

    updated = 0
    for page in pages:
        content = intro_contents.get(page.sort_order, '')
        if content:
            current = (page.rich_text_content or '').strip()
            # 如果当前为空或只有空 p 标签，则更新
            if not current or current in ('<p><br></p>', '<p></p>'):
                page.rich_text_content = content
                updated += 1
                print(f'[轮播页] #{page.sort_order} "{page.title}" → 已填充富文本内容')
            else:
                print(f'[轮播页] #{page.sort_order} "{page.title}" → 已有内容，跳过')

    if updated > 0:
        db.session.commit()
        print(f'[轮播页] [OK] 已更新 {updated}/{len(pages)} 页')
    else:
        print('[轮播页] [OK] 无需更新')


def migrate_province_content():
    """国家农高区 —— 确保省份卡片内容完整"""
    # 9个国家农高区的完整描述
    agri_zone_data = {
        '140000': {  # 山西
            'card_title': '山西晋中国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2019年11月<br>'
                '<strong>规划面积：</strong>106.49平方公里<br>'
                '<strong>建设主题：</strong>有机旱作农业<br>'
                '<strong>核心区域：</strong>晋中市太谷区</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以有机旱作农业为主题，以农副食品加工为主导产业，'
                '建设全国健康食品和功能农业综合示范区、'
                '科技产业孵化示范区、特色农产品优势区。</p>'
            ),
            'is_highlighted': True,
        },
        '150000': {  # 内蒙古
            'card_title': '内蒙古巴彦淖尔国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2022年4月<br>'
                '<strong>规划面积：</strong>139.74平方公里<br>'
                '<strong>建设主题：</strong>河套灌区生态农牧业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以硬质小麦和肉羊为主导产业，建设河套灌区生态农牧业'
                '高质量发展示范区、绿色有机高端农畜产品生产加工基地。</p>'
            ),
            'is_highlighted': True,
        },
        '220000': {  # 吉林
            'card_title': '吉林长春国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2022年4月<br>'
                '<strong>规划面积：</strong>139.39平方公里<br>'
                '<strong>建设主题：</strong>松嫩平原绿色循环农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以玉米为主导产业，建设粮食作物全产业链示范区、'
                '东北地区农业高新技术创新中心。</p>'
            ),
            'is_highlighted': True,
        },
        '230000': {  # 黑龙江
            'card_title': '黑龙江佳木斯国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2022年4月<br>'
                '<strong>规划面积：</strong>138.78平方公里<br>'
                '<strong>建设主题：</strong>黑土地现代农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以水稻为主导产业，建设黑土地保护与利用创新示范区、'
                '东北寒地优质稻米产业高地。</p>'
            ),
            'is_highlighted': True,
        },
        '320000': {  # 江苏
            'card_title': '江苏南京白马国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2019年11月<br>'
                '<strong>规划面积：</strong>145.86平方公里<br>'
                '<strong>建设主题：</strong>绿色智慧农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以生物农业为主导产业，建设国际农业科技合作示范区、'
                '长三角农业科技创新策源地。</p>'
            ),
            'is_highlighted': True,
        },
        '370000': {  # 山东
            'card_title': '山东黄河三角洲国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2015年10月<br>'
                '<strong>规划面积：</strong>350平方公里<br>'
                '<strong>建设主题：</strong>盐碱地综合利用</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以盐碱地综合利用为特色，建设全国盐碱地现代农业'
                '科技创新高地、黄河流域生态保护与高质量发展示范区。</p>'
            ),
            'is_highlighted': True,
        },
        '410000': {  # 河南
            'card_title': '河南周口国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2022年4月<br>'
                '<strong>规划面积：</strong>118平方公里<br>'
                '<strong>建设主题：</strong>黄淮平原高质高效农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以小麦为主导产业，建设黄淮平原高质高效农业示范区、'
                '中原地区粮食产业转型升级引领区。</p>'
            ),
            'is_highlighted': True,
        },
        '610000': {  # 陕西
            'card_title': '陕西杨凌国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>1997年7月<br>'
                '<strong>规划面积：</strong>135平方公里<br>'
                '<strong>建设主题：</strong>干旱半干旱地区现代农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '中国第一个国家级农业高新技术产业示范区，'
                '以农业科技创新为核心，建设干旱半干旱地区'
                '现代农业发展引领区。</p>'
            ),
            'is_highlighted': True,
        },
        '650000': {  # 新疆
            'card_title': '新疆昌吉国家农高区',
            'card_content': (
                '<p style="font-size:15px;line-height:1.8;">'
                '<strong>批复时间：</strong>2022年4月<br>'
                '<strong>规划面积：</strong>109.95平方公里<br>'
                '<strong>建设主题：</strong>干旱荒漠绿洲农业</p>'
                '<p style="font-size:14px;line-height:1.7;color:#555;">'
                '以棉花为主导产业，建设干旱荒漠绿洲农业'
                '高质量发展示范区、丝绸之路经济带农业科技合作中心。</p>'
            ),
            'is_highlighted': True,
        },
    }

    updated = 0
    for region_code, data in agri_zone_data.items():
        province = ProvinceInfo.query.filter_by(
            region_code=region_code, map_scope='china'
        ).first()
        if not province:
            print(f'[农高区] {region_code} 省份不存在，跳过')
            continue

        changed = False
        if province.card_title != data['card_title']:
            province.card_title = data['card_title']
            changed = True
        if (province.card_content or '').strip() != data['card_content'].strip():
            province.card_content = data['card_content']
            changed = True
        if not province.is_highlighted:
            province.is_highlighted = True
            changed = True

        if changed:
            updated += 1
            print(f'[农高区] {province.region_name} → 已更新卡片内容')
        else:
            print(f'[农高区] {province.region_name} → 内容完整，跳过')

    if updated > 0:
        db.session.commit()
        print(f'[农高区] [OK] 已更新 {updated} 个省份')
    else:
        print('[农高区] [OK] 无需更新')


def migrate_city_highlights():
    """确保9个农高区城市已高亮"""
    city_highlights = {
        '140000': [('140700', '晋中市')],           # 山西 → 晋中
        '150000': [('150800', '巴彦淖尔市')],        # 内蒙古 → 巴彦淖尔
        '220000': [('220100', '长春市')],            # 吉林 → 长春
        '230000': [('230800', '佳木斯市')],          # 黑龙江 → 佳木斯
        '320000': [('320100', '南京市')],            # 江苏 → 南京
        '370000': [('370500', '东营市')],            # 山东 → 东营
        '410000': [('411600', '周口市')],            # 河南 → 周口
        '610000': [('610100', '西安市')],            # 陕西 → 西安（杨凌在西安辖区）
        '650000': [('652300', '昌吉回族自治州')],    # 新疆 → 昌吉
    }

    updated = 0
    for region_code, cities in city_highlights.items():
        province = ProvinceInfo.query.filter_by(
            region_code=region_code, map_scope='china'
        ).first()
        if not province:
            continue

        for city_code, city_name in cities:
            city = CityInfo.query.filter_by(
                province_id=province.id, city_code=city_code
            ).first()
            if city:
                if not city.is_highlighted:
                    city.is_highlighted = True
                    updated += 1
                    print(f'[城市] {city_name} → 已高亮')
                else:
                    print(f'[城市] {city_name} → 已高亮，跳过')
            else:
                # 创建城市记录
                new_city = CityInfo(
                    province_id=province.id,
                    city_code=city_code,
                    city_name=city_name,
                    is_highlighted=True,
                    card_title=province.card_title.replace('国家农高区', '') + '（农高区所在地）',
                    card_content='',
                )
                db.session.add(new_city)
                updated += 1
                print(f'[城市] {city_name} → 新建并高亮')

    if updated > 0:
        db.session.commit()
        print(f'[城市] [OK] 已更新 {updated} 个城市')
    else:
        print('[城市] [OK] 无需更新')


def main():
    with app.app_context():
        print('=' * 60)
        print('  襄阳农高区 — 业务内容数据迁移')
        print('=' * 60)
        print()

        print('[1/4] 首页配置')
        print('-' * 40)
        migrate_homepage()
        print()

        print('[2/4] 联系我们')
        print('-' * 40)
        migrate_contact()
        print()

        print('[3/4] 襄阳农高区介绍（轮播页）')
        print('-' * 40)
        migrate_carousel_pages()
        print()

        print('[4/4] 国家农高区（省份卡片 + 城市高亮）')
        print('-' * 40)
        migrate_province_content()
        migrate_city_highlights()
        print()

        print('=' * 60)
        print('  迁移完成!')
        print('=' * 60)


if __name__ == '__main__':
    main()
