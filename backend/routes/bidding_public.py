"""揭榜挂帅 — 对外端口 API（揭榜方门户）

- 注册/登录（session: bidding_user_id）
- 公开榜单浏览（匿名可看，仅已发布）
- 提交揭榜申请（登录后，自动邮箱回执，每人每榜限一条有效申请）
- 我的申请 / 项目进展（信息隔离：仅本人数据）
"""
from datetime import date

from flask import request, jsonify, session

from models import BiddingProject, BiddingBid, BiddingUser, BiddingMilestone, BiddingTimeline
from extensions import db
from routes import bidding_public_bp
from services.bidding_service import STAGE_NAME_MAP, TERMINAL_STAGES
from services.email_service import send_register_receipt, send_apply_receipt, email_configured


# ---------------------------------------------------------------------------
# 登录态辅助
# ---------------------------------------------------------------------------

def _current_user():
    uid = session.get('bidding_user_id')
    if not uid:
        return None
    user = db.session.get(BiddingUser, int(uid))
    if user and user.is_active:
        return user
    session.pop('bidding_user_id', None)
    return None


def _login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _current_user()
        if not user:
            return jsonify({'code': 1, 'message': '请先登录'}), 401
        return f(user, *args, **kwargs)
    return decorated


def _board_public_dict(p, user=None):
    """对外展示的榜单信息（不暴露内部评审细节）"""
    return {
        'id': p.id,
        'title': p.title,
        'category_code': p.category_code or '',
        'demander_name': p.demander_name or '',
        'requirement_desc': p.requirement_desc or '',
        # 三段式需求描述（新申报表数据）
        'tech_difficulties': p.tech_difficulties or '',
        'tech_indicators': p.tech_indicators or '',
        'research_content': p.research_content or '',
        'bounty_amount': p.bounty_amount or 0.0,
        'deadline_date': p.deadline_date.isoformat() if p.deadline_date else None,
        'publish_date': p.publish_date.isoformat() if p.publish_date else None,
        'accept_conditions': p.accept_conditions or '',
        'expected_deadline': p.expected_deadline.isoformat() if p.expected_deadline else None,
        'current_stage': p.current_stage,
        'stage_name': STAGE_NAME_MAP.get(p.current_stage, p.current_stage),
        'is_terminal': p.current_stage in TERMINAL_STAGES,
        # 揭榜方登录后可见自己是否已申请
        'applied': False,
    }


# ---------------------------------------------------------------------------
# 注册 / 登录 / 登出
# ---------------------------------------------------------------------------

@bidding_public_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    org_name = (data.get('org_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    contact_name = (data.get('contact_name') or '').strip()
    contact_phone = (data.get('contact_phone') or '').strip()
    org_type = data.get('org_type', '')

    if not org_name:
        return jsonify({'code': 1, 'message': '单位/团队名称不能为空'}), 400
    if not email or '@' not in email:
        return jsonify({'code': 1, 'message': '请填写有效邮箱（用于接收回执通知）'}), 400
    if len(password) < 6:
        return jsonify({'code': 1, 'message': '密码至少 6 位'}), 400

    # 用户名 = 邮箱（唯一）
    if BiddingUser.query.filter_by(username=email).first():
        return jsonify({'code': 1, 'message': '该邮箱已注册，请直接登录'}), 400

    user = BiddingUser(
        username=email,
        org_name=org_name,
        org_type=org_type,
        contact_name=contact_name,
        contact_phone=contact_phone,
        email=email,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # 自动邮箱回执（异步；SMTP 未配置时仅记日志，不阻断注册）
    send_register_receipt(email, email, org_name)

    return jsonify({
        'code': 0,
        'data': user.to_dict(),
        'message': '注册成功，回执邮件已发送至 %s' % email,
        'email_sent': email_configured(),
    })


@bidding_public_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    user = BiddingUser.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'code': 1, 'message': '账号或密码错误'}), 401
    if not user.is_active:
        return jsonify({'code': 1, 'message': '账号已被禁用，请联系农高区招商专班'}), 403
    session['bidding_user_id'] = user.id
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '登录成功'})


@bidding_public_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('bidding_user_id', None)
    return jsonify({'code': 0, 'message': '已登出'})


@bidding_public_bp.route('/me', methods=['GET'])
@_login_required
def me(user):
    return jsonify({'code': 0, 'data': user.to_dict()})


@bidding_public_bp.route('/me', methods=['PUT'])
@_login_required
def update_me(user):
    data = request.get_json(silent=True) or {}
    if data.get('org_name') is not None:
        user.org_name = (data.get('org_name') or '').strip()
    if data.get('org_type') is not None:
        user.org_type = data.get('org_type')
    if data.get('contact_name') is not None:
        user.contact_name = (data.get('contact_name') or '').strip()
    if data.get('contact_phone') is not None:
        user.contact_phone = (data.get('contact_phone') or '').strip()
    db.session.commit()
    return jsonify({'code': 0, 'data': user.to_dict(), 'message': '已保存'})


@bidding_public_bp.route('/me/password', methods=['POST'])
@_login_required
def change_password(user):
    data = request.get_json(silent=True) or {}
    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''
    if len(new_password) < 6:
        return jsonify({'code': 1, 'message': '新密码至少 6 位'}), 400
    if not user.check_password(old_password):
        return jsonify({'code': 1, 'message': '原密码错误'}), 400
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'code': 0, 'message': '密码已修改，请重新登录'})


# ---------------------------------------------------------------------------
# 公开榜单浏览
# ---------------------------------------------------------------------------

@bidding_public_bp.route('/boards', methods=['GET'])
def list_boards():
    """公开榜单：仅已发布（含已截止，供历史查看）"""
    user = _current_user()
    projects = BiddingProject.query.filter(
        BiddingProject.is_deleted == False,
        BiddingProject.current_stage.in_(['stage3', 'stage4', 'stage5', 'stage6', 'stage7', 'failed', 'cancelled']),
    ).order_by(BiddingProject.publish_date.desc()).all()

    # 已发布标记：stage3+ 或 published；终止态 failed/cancelled 也公开（供查看）
    result = []
    today = date.today()
    for p in projects:
        d = _board_public_dict(p, user)
        d['open'] = (p.current_stage == 'stage3' and p.publish_status == 'published'
                     and p.deadline_date and p.deadline_date >= today)
        if user:
            d['applied'] = BiddingBid.query.filter_by(project_id=p.id, user_id=user.id).first() is not None
        result.append(d)
    return jsonify({'code': 0, 'data': result})


@bidding_public_bp.route('/boards/<int:project_id>', methods=['GET'])
def get_board(project_id):
    p = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not p:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404
    user = _current_user()
    d = _board_public_dict(p, user)
    d['open'] = (p.current_stage == 'stage3' and p.publish_status == 'published'
                 and p.deadline_date and p.deadline_date >= date.today())
    if user:
        d['applied'] = BiddingBid.query.filter_by(project_id=p.id, user_id=user.id).first() is not None
    return jsonify({'code': 0, 'data': d})


# ---------------------------------------------------------------------------
# 提交揭榜申请
# ---------------------------------------------------------------------------

@bidding_public_bp.route('/boards/<int:project_id>/apply', methods=['POST'])
@_login_required
def apply(user, project_id):
    p = BiddingProject.query.filter_by(id=project_id, is_deleted=False).first()
    if not p:
        return jsonify({'code': 1, 'message': '榜单不存在'}), 404

    # 校验：仅 stage3 已发布且在揭榜期内可申请
    if p.current_stage != 'stage3' or p.publish_status != 'published':
        return jsonify({'code': 1, 'message': '该榜单当前不在揭榜期内，无法提交申请'}), 400
    if p.deadline_date and p.deadline_date < date.today():
        return jsonify({'code': 1, 'message': '该榜单已过揭榜截止日期'}), 400

    # 每人每榜限一条有效申请
    existing = BiddingBid.query.filter_by(project_id=p.id, user_id=user.id) \
        .filter(BiddingBid.status.in_(['submitted', 'reviewing', 'selected'])).first()
    if existing:
        return jsonify({'code': 1, 'message': '您已提交过该榜单的揭榜申请，请勿重复提交'}), 400

    data = request.get_json(silent=True) or {}
    tech_solution = (data.get('tech_solution') or '').strip()
    if not tech_solution:
        return jsonify({'code': 1, 'message': '请填写技术方案'}), 400

    bid = BiddingBid(
        project_id=p.id,
        user_id=user.id,
        bidder_name=user.org_name or user.username,
        bidder_type=user.org_type or '企业',
        team_leader=data.get('team_leader') or user.contact_name,
        team_leader_phone=data.get('team_leader_phone') or user.contact_phone,
        tech_solution=tech_solution,
        team_advantage=data.get('team_advantage', ''),
        expected_amount=data.get('expected_amount') or 0.0,
        status='submitted',
    )
    db.session.add(bid)
    db.session.flush()

    # 写入时间线（对外提交自动留痕）
    t = BiddingTimeline(
        project_id=p.id,
        stage=p.current_stage,
        record_type='notice',
        content='【通知】揭榜方 %s 提交揭榜申请' % (user.org_name or user.username),
        files='[]',
        record_by='%s（对外端口）' % (user.org_name or user.username),
    )
    db.session.add(t)
    db.session.commit()

    # 自动邮箱回执
    send_apply_receipt(user.email, user.org_name, p.title, bid.id)

    return jsonify({
        'code': 0,
        'data': bid.to_dict(),
        'message': '揭榜申请已提交，回执邮件已发送至 %s' % user.email,
        'email_sent': email_configured(),
    })


# ---------------------------------------------------------------------------
# 我的申请 / 项目进展（信息隔离）
# ---------------------------------------------------------------------------

@bidding_public_bp.route('/my-applications', methods=['GET'])
@_login_required
def my_applications(user):
    bids = BiddingBid.query.filter_by(user_id=user.id) \
        .order_by(BiddingBid.submitted_at.desc()).all()
    result = []
    for b in bids:
        p = BiddingProject.query.get(b.project_id)
        result.append({
            'id': b.id,
            'project_id': b.project_id,
            'board_title': p.title if p else '',
            'bounty_amount': p.bounty_amount if p else 0.0,
            'bid_status': b.status,
            'score': b.score,
            'submitted_at': b.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if b.submitted_at else None,
            'project_stage': p.current_stage if p else '',
            'project_stage_name': STAGE_NAME_MAP.get(p.current_stage, p.current_stage) if p else '',
            'project_terminal': (p.current_stage in TERMINAL_STAGES) if p else False,
        })
    return jsonify({'code': 0, 'data': result})


@bidding_public_bp.route('/my-applications/<int:bid_id>', methods=['GET'])
@_login_required
def my_application_detail(user, bid_id):
    """我的申请详情：中标后可查看项目进展（阶段/里程碑/时间线/绩效）"""
    bid = BiddingBid.query.filter_by(id=bid_id, user_id=user.id).first()
    if not bid:
        return jsonify({'code': 1, 'message': '申请不存在'}), 404
    p = db.session.get(BiddingProject, bid.project_id)

    data = {
        'id': bid.id,
        'project_id': bid.project_id,
        'board_title': p.title if p else '',
        'board_category': p.category_code if p else '',
        'demander_name': p.demander_name if p else '',
        'requirement_desc': p.requirement_desc if p else '',
        'bounty_amount': p.bounty_amount if p else 0.0,
        'deadline_date': p.deadline_date.isoformat() if (p and p.deadline_date) else None,
        'bid_status': bid.status,
        'score': bid.score,
        'score_note': bid.score_note or '',
        'tech_solution': bid.tech_solution or '',
        'team_advantage': bid.team_advantage or '',
        'expected_amount': bid.expected_amount or 0.0,
        'submitted_at': bid.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if bid.submitted_at else None,
    }

    if p:
        data['project_stage'] = p.current_stage
        data['project_stage_name'] = STAGE_NAME_MAP.get(p.current_stage, p.current_stage)
        data['project_terminal'] = p.current_stage in TERMINAL_STAGES
        data['argument_result'] = p.argument_result or ''       # 论证结论（若被驳回可见原因）
        data['review_result'] = p.review_result or ''
        data['task_amount'] = p.task_amount or 0.0
        data['task_duration'] = p.task_duration or ''
        data['task_date'] = p.task_date.isoformat() if p.task_date else None
        data['task_notes'] = p.task_notes or ''
        data['eval_score'] = p.eval_score
        data['eval_level'] = p.eval_level or ''
        data['eval_report'] = p.eval_report or ''
        data['eval_date'] = p.eval_date.isoformat() if p.eval_date else None

        # 中标后才展示里程碑与时间线
        if bid.status == 'selected' and p.current_stage in ('stage5', 'stage6', 'stage7'):
            data['milestones'] = [m.to_dict() for m in p.milestones.all()]
            data['timeline'] = [t.to_dict() for t in p.timeline.all()]
        else:
            data['milestones'] = []
            data['timeline'] = []

    return jsonify({'code': 0, 'data': data})
