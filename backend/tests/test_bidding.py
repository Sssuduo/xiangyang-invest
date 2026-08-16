"""揭榜挂帅模块冒烟测试：状态机边界 + 双端口 API 全流程 + 信息隔离

运行：cd backend && python -m pytest tests/test_bidding.py -v
使用独立临时 SQLite，不污染 instance/app.db。
注意：不跑 seed_data.init_database 全量种子（其 staff 创建逻辑依赖既有库数据，
且 embedding 会触发外部调用），fixture 只建表 + 最小数据。
"""
import os
import sys
import tempfile

# 环境变量必须先于 app 导入（config.py 类定义时读取 DATABASE_URL）
_TMPDIR = tempfile.mkdtemp(prefix='bidding_test_')
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(_TMPDIR, 'test.db')}"
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'test-secret-key'   # 生产配置强制要求 SECRET_KEY

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在 create_app 之前替换 init_database，避免全量 seed
import seed_data as _seed_module  # noqa: E402


def _minimal_init_database(app):
    from extensions import db
    from models import AdminUser, BiddingCategoryDict, Staff
    db.create_all()
    if not AdminUser.query.filter_by(username='admin').first():
        u = AdminUser(username='admin', display_name='管理员')
        u.set_password('changeme123')
        db.session.add(u)
    if not Staff.query.first():
        db.session.add(Staff(name='管理员', position='农高区创建专班工作人员'))
    cats = [
        ('agri_breeding', '粮油作物育种', 1), ('smart_agri', '智慧农业', 2),
        ('food_processing', '食品加工', 3), ('agri_machinery', '农机装备', 4),
        ('bio_breeding', '生物育种', 5), ('facility_agri', '设施农业', 6),
        ('digital_agri', '数字农业', 7), ('other', '其他', 8),
    ]
    for code, name, order in cats:
        if not BiddingCategoryDict.query.filter_by(code=code).first():
            db.session.add(BiddingCategoryDict(code=code, name=name, sort_order=order))
    db.session.commit()


_seed_module.init_database = _minimal_init_database

import pytest  # noqa: E402


@pytest.fixture(scope='module')
def app():
    from app import create_app
    application = create_app('production')
    application.config['TESTING'] = True
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    """已登录 admin 的 client"""
    resp = client.post('/api/admin/login', json={
        'username': 'admin', 'password': 'changeme123',
    })
    assert resp.status_code == 200, resp.get_json()
    return client


def _json(resp):
    return resp.get_json()


# ---------------------------------------------------------------------------
# 状态机纯函数测试
# ---------------------------------------------------------------------------

def test_validate_transition_basic():
    from services.bidding_service import validate_transition, BiddingTransitionError, STAGE_KEYS

    # 正常推进
    assert validate_transition('stage1', 'submit_argument') == 'stage2'
    assert validate_transition('stage2', 'argument_pass') == 'stage3'
    assert validate_transition('stage3', 'expire') == 'stage4'
    assert validate_transition('stage4', 'select_bid') == 'stage5'
    assert validate_transition('stage5', 'sign') == 'stage6'
    assert validate_transition('stage6', 'complete') == 'stage7'
    assert validate_transition('stage7', 'evaluate') == 'stage7'

    # 非法流转
    with pytest.raises(BiddingTransitionError):
        validate_transition('stage1', 'sign')
    with pytest.raises(BiddingTransitionError):
        validate_transition('stage4', 'submit_argument')
    with pytest.raises(BiddingTransitionError):
        validate_transition('stage3', 'select_bid')

    # 终止态拒绝推进（stage7 的 evaluate 除外）
    with pytest.raises(BiddingTransitionError):
        validate_transition('rejected', 'argument_pass')
    assert validate_transition('stage7', 'evaluate') == 'stage7'

    # cancel 任意非终态可用
    for st in STAGE_KEYS:
        if st != 'stage7':
            assert validate_transition(st, 'cancel') == 'cancelled'

    # 未知动作
    with pytest.raises(BiddingTransitionError):
        validate_transition('stage1', 'no_such_action')


# ---------------------------------------------------------------------------
# 双端口 API 全流程
# ---------------------------------------------------------------------------

def test_full_flow(admin_client, app):
    """内部登记 → 论证 → 发榜 → 外部揭榜 → 定标 → 签订 → 过程管理 → 绩效评价"""
    with app.app_context():
        from models import BiddingProject
        BiddingProject.query.delete()
        from extensions import db
        db.session.commit()

    # 1. 内部登记需求（stage1，新建企业模式：org_name + 资质数组 → 企业档案创建路径）
    resp = admin_client.post('/api/admin/bidding/projects', json={
        'title': '水稻抗病分子育种关键技术攻关',
        'category_code': 'agri_breeding',
        'demander_name': '湖北某某种业有限公司',
        'org_name': '湖北某某种业有限公司',
        'demander_contact': '张工',
        'demander_phone': '0710-1234567',
        'demand_source': '企业申报',
        'requirement_desc': '需要抗稻瘟病的水稻新品种育种关键技术',
        'expected_budget': 200,
        'expected_deadline': '2027-12-31',
        # 企业概况（申报表）
        'enterprise_address': '襄州区机场路一号',
        'enterprise_qualifications': ['高新技术企业', '“专精特新”小巨人'],
        'industry_code': '农、林、牧、渔业',
        'registered_capital': '1.44亿',
        'founded_year': '1996年',
        'staff_size': '220',
        'enterprise_nature': '民营',
        'main_products': '水稻种子选育、加工、销售',
        'last_year_revenue': '3.61亿',
        # 需求描述（三段式）
        'tech_difficulties': '抗病性与高产性状的遗传聚合难；优异种质资源匮乏',
        'tech_indicators': '育成抗病新品种1-2个，较对照增产5%以上',
        'research_content': '挖掘抗病关键基因，开发分子标记；创制聚合双优性状的新种质',
        # 合作意向
        'short_term_cooperation': ['技术诊断指导', '专题培训'],
        'long_term_cooperation': ['联合开发', '委托研发'],
        'expert_intent': 'yes',
        'expert_names': '李教授（华中农业大学）',
    })
    assert resp.status_code == 200, _json(resp)
    pid = _json(resp)['data']['id']

    # 申报表字段回读校验
    d = _json(resp)['data']
    assert d['enterprise_address'] == '襄州区机场路一号'
    assert '高新技术企业' in d['enterprise_qualifications']
    assert d['tech_indicators'].startswith('育成抗病新品种')
    assert d['long_term_cooperation'] == ['联合开发', '委托研发']
    assert d['expert_intent'] == 'yes'

    # 2. 提交论证（stage1 → stage2）
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'submit_argument'})
    assert _json(resp)['code'] == 0, _json(resp)

    # 3. 论证通过（stage2 → stage3）
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'argument_pass',
        'argument_experts': [{'name': '李教授', 'org': '华中农业大学', 'title': '教授'}],
        'argument_opinion': '技术需求真实，建议发榜',
        'argument_result': '同意发榜',
    })
    assert _json(resp)['code'] == 0, _json(resp)
    assert _json(resp)['data']['current_stage'] == 'stage3'

    # 非法流转：stage3 不能 select_bid
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'select_bid'})
    assert resp.status_code == 400, _json(resp)

    # 4. 发布公告（要求截止日期，缺失应 400）
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'publish', 'bounty_amount': 200, 'accept_conditions': '具有种质资源库的高校优先',
    })
    assert resp.status_code == 400, _json(resp)
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'publish', 'bounty_amount': 200, 'deadline_date': '2026-12-31',
        'accept_conditions': '具有种质资源库的高校优先',
    })
    assert _json(resp)['code'] == 0, _json(resp)

    # 5. 对外注册揭榜方 + 登录 + 浏览榜单
    resp = admin_client.post('/api/bidding/register', json={
        'org_name': '华中农业大学水稻团队',
        'org_type': '高校',
        'contact_name': '王教授',
        'contact_phone': '13800000000',
        'email': 'team@hau.edu.cn',
        'password': 'secret123',
    })
    assert resp.status_code == 200, _json(resp)
    assert _json(resp)['email_sent'] is False  # SMTP 未配置，降级不阻断

    resp = admin_client.post('/api/bidding/login', json={
        'username': 'team@hau.edu.cn', 'password': 'secret123',
    })
    assert _json(resp)['code'] == 0, _json(resp)

    resp = admin_client.get('/api/bidding/boards')
    boards = _json(resp)['data']
    assert len(boards) == 1
    assert boards[0]['open'] is True

    # 6. 提交揭榜申请
    resp = admin_client.post(f'/api/bidding/boards/{pid}/apply', json={
        'tech_solution': '利用分子标记辅助选择育种，3年育成抗病品种',
        'team_advantage': '拥有种质资源库与分子育种平台',
        'expected_amount': 180,
    })
    assert _json(resp)['code'] == 0, _json(resp)
    bid_id = _json(resp)['data']['id']

    # 重复申请应 400
    resp = admin_client.post(f'/api/bidding/boards/{pid}/apply', json={'tech_solution': '重复'})
    assert resp.status_code == 400, _json(resp)

    # 匿名不能查看我的申请
    resp = admin_client.post('/api/bidding/logout', json={})
    resp = admin_client.get('/api/bidding/my-applications')
    assert resp.status_code == 401

    # 7. 内部截止揭榜 + 定标（stage3 → stage4 → stage5）
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'expire'})
    assert _json(resp)['data']['current_stage'] == 'stage4'

    # 外部提交的申请在内部可见（is_external=True）
    resp = admin_client.get(f'/api/admin/bidding/projects/{pid}')
    bids = _json(resp)['data']['bids']
    assert len(bids) == 1 and bids[0]['is_external'] is True

    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'select_bid', 'bid_id': bid_id, 'review_result': '技术方案可行，评分最高',
    })
    assert _json(resp)['code'] == 0, _json(resp)
    assert _json(resp)['data']['current_stage'] == 'stage5'

    # 8. 任务签订（stage5 → stage6）
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'sign', 'task_amount': 180, 'task_duration': '24个月', 'task_date': '2027-01-15',
    })
    assert _json(resp)['code'] == 0, _json(resp)

    # 添加里程碑
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/milestones', json={
        'content': '完成抗病基因聚合', 'planned_date': '2027-06-30',
    })
    assert _json(resp)['code'] == 0, _json(resp)
    mid = _json(resp)['data']['id']

    # 9. 揭榜方登录查看进展（中标后可见里程碑/时间线）
    resp = admin_client.post('/api/bidding/login', json={
        'username': 'team@hau.edu.cn', 'password': 'secret123',
    })
    resp = admin_client.get(f'/api/bidding/my-applications/{bid_id}')
    detail = _json(resp)['data']
    assert detail['bid_status'] == 'selected'
    assert len(detail['milestones']) == 1

    # 10. 过程管理核查里程碑 → 实施完成 → 绩效评价
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/milestones/{mid}/status', json={
        'status': 'done', 'result_note': '已完成基因聚合',
    })
    assert _json(resp)['code'] == 0, _json(resp)

    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'complete'})
    assert _json(resp)['data']['current_stage'] == 'stage7'

    # 绩效评价缺评分应 400
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'evaluate', 'eval_level': '优秀',
    })
    assert resp.status_code == 400, _json(resp)

    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'evaluate', 'eval_score': 92, 'eval_level': '优秀',
        'eval_report': '超额完成育种指标，推荐成果转化',
    })
    assert _json(resp)['code'] == 0, _json(resp)

    # 11. 揭榜方查看绩效结果
    resp = admin_client.get(f'/api/bidding/my-applications/{bid_id}')
    detail = _json(resp)['data']
    assert detail['eval_level'] == '优秀'
    assert detail['eval_score'] == 92
    assert detail['project_stage'] == 'stage7'

    # 12. 时间线已自动记录流转
    resp = admin_client.get(f'/api/admin/bidding/projects/{pid}')
    timeline = _json(resp)['data']['timeline']
    assert len(timeline) >= 8  # 创建 + 每次流转 + 服务记录

    # 看板统计
    resp = admin_client.get('/api/admin/bidding/stats')
    stats = _json(resp)['data']
    assert stats['total'] == 1
    assert stats['stage_counts']['stage7'] == 1


def test_information_isolation(admin_client):
    """揭榜方之间信息隔离：他人看不到我的申请"""
    # 注册第二个用户
    admin_client.post('/api/bidding/register', json={
        'org_name': '湖北农科院团队', 'org_type': '科研院所',
        'contact_name': '陈研究员', 'contact_phone': '13900000000',
        'email': 'team2@hbaas.cn', 'password': 'secret456',
    })
    resp = admin_client.post('/api/bidding/login', json={
        'username': 'team2@hbaas.cn', 'password': 'secret456',
    })
    assert _json(resp)['code'] == 0

    resp = admin_client.get('/api/bidding/my-applications')
    assert _json(resp)['data'] == []  # 看不到第一个用户的申请


def test_terminate_flows(admin_client, app):
    """论证驳回 / 流标 / 取消 三条终止路径"""
    with app.app_context():
        from models import BiddingProject
        from extensions import db
        BiddingProject.query.delete()
        db.session.commit()

    # 论证驳回
    resp = admin_client.post('/api/admin/bidding/projects', json={
        'title': '驳回案例', 'demander_name': '测试企业A', 'org_name': '测试企业A',
    })
    pid = _json(resp)['data']['id']
    admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'submit_argument'})
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={
        'action': 'argument_reject', 'argument_result': '需求已由企业自行解决',
    })
    assert _json(resp)['data']['current_stage'] == 'rejected'
    # 终态后任何推进被拒
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid}/transition', json={'action': 'argument_pass'})
    assert resp.status_code == 400

    # 流标
    resp = admin_client.post('/api/admin/bidding/projects', json={
        'title': '流标案例', 'demander_name': '测试企业B', 'org_name': '测试企业B',
    })
    pid2 = _json(resp)['data']['id']
    for action in ('submit_argument', 'argument_pass', 'publish'):
        payload = {'action': action}
        if action == 'publish':
            payload['deadline_date'] = '2026-12-31'
        admin_client.post(f'/api/admin/bidding/projects/{pid2}/transition', json=payload)
    admin_client.post(f'/api/admin/bidding/projects/{pid2}/transition', json={'action': 'expire'})
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid2}/transition', json={
        'action': 'fail_bid', 'review_result': '无符合条件揭榜方',
    })
    assert _json(resp)['data']['current_stage'] == 'failed'

    # 任意阶段取消
    resp = admin_client.post('/api/admin/bidding/projects', json={
        'title': '取消案例', 'demander_name': '测试企业C', 'org_name': '测试企业C',
    })
    pid3 = _json(resp)['data']['id']
    resp = admin_client.post(f'/api/admin/bidding/projects/{pid3}/transition', json={
        'action': 'cancel', 'reason': '企业撤回需求',
    })
    assert _json(resp)['data']['current_stage'] == 'cancelled'
