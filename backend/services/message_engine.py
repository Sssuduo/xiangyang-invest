"""消息提醒引擎 — 评估规则 + 生成用户消息"""
import json
import re
import html
from datetime import datetime, date
from sqlalchemy import literal
from models import MessageRule, UserMessage, MessageRuleLog
from models import AdminUser, BusinessUser, InvestmentProject
from extensions import db


def _render_template(template: str, variables: dict) -> str:
    """渲染模板,把 {var} 替换为 html.escape 后的值;[text] 保留为链接标记(后续前端处理)"""
    def replacer(m):
        key = m.group(1)
        val = variables.get(key, m.group(0))
        return html.escape(str(val))
    return re.sub(r'\{(\w+)\}', replacer, template)


def _get_users(rule: MessageRule):
    """根据 target_type 返回 [(user_id, user_type), ...]"""
    if rule.target_type == 'all':
        admins = db.session.query(AdminUser.id.label('id'), literal('admin').label('type')).all()
        biz = db.session.query(BusinessUser.id.label('id'), literal('business').label('type')).all()
        return admins + biz
    if rule.target_type == 'specific_users':
        try:
            user_ids = json.loads(rule.target_user_ids or '[]')
        except Exception:
            user_ids = []
        return [(uid, 'admin') for uid in user_ids]
    if rule.target_type == 'project_leaders':
        # 项目负责人(暂返回空,后续扩展)
        return []
    return []


def _get_triggered_sources(rule: MessageRule):
    """根据 condition_type 返回触发源项目列表"""
    today = date.today()

    if rule.condition_type == 'project_no_meeting':
        # 招商项目:未研判 且 首次对接时间超过 threshold_days 天
        projects = InvestmentProject.query.filter(
            InvestmentProject.is_deleted == False,
            InvestmentProject.meeting_status_code == 'not_meeting',
            InvestmentProject.first_contact_date != None,
        ).all()
        return [
            p for p in projects
            if (today - p.first_contact_date).days > rule.threshold_days
        ]

    if rule.condition_type == 'project_no_followup':
        # 招商项目:超期无动态(最近一条 activity 时间超过 threshold_days)
        projects = InvestmentProject.query.filter(
            InvestmentProject.is_deleted == False,
            InvestmentProject.first_contact_date != None,
        ).all()
        triggered = []
        for p in projects:
            from models import InvestmentActivity
            last_act = InvestmentActivity.query.filter_by(project_id=p.id, is_deleted=False if hasattr(InvestmentActivity, 'is_deleted') else True) \
                .order_by(InvestmentActivity.date.desc()).first()
            ref_date = last_act.date if last_act else p.first_contact_date
            if ref_date and (today - ref_date).days > rule.threshold_days:
                triggered.append(p)
        return triggered

    return []


def evaluate_rule(rule: MessageRule) -> int:
    """评估单条规则,生成用户消息。返回生成的消息数。"""
    if not rule.is_active:
        return 0

    sources = _get_triggered_sources(rule)
    if not sources:
        return 0

    users = _get_users(rule)
    if not users:
        return 0

    generated = 0
    for project in sources:
        # 去重:同一 rule+source 不重复生成 pending 消息
        exists_pending = UserMessage.query.filter(
            UserMessage.rule_id == rule.id,
            UserMessage.source_type == 'investment_project',
            UserMessage.source_id == project.id,
            UserMessage.status == 'pending',
        ).first()
        if exists_pending:
            continue

        for user_id, user_type in users:
            # 去重:同一 user+rule+source 不重复
            exists = UserMessage.query.filter(
                UserMessage.user_id == user_id,
                UserMessage.user_type == user_type,
                UserMessage.rule_id == rule.id,
                UserMessage.source_id == project.id,
            ).filter(UserMessage.status.in_(['pending', 'snoozed'])).first()
            if exists:
                continue

            user = AdminUser.query.get(user_id) or BusinessUser.query.get(user_id)
            if not user:
                continue

            variables = {
                'username': getattr(user, 'display_name', None) or user.username,
                'project_name': project.project_name,
                'first_contact_date': project.first_contact_date.isoformat(),
                'threshold_days': str(rule.threshold_days),
                'project_id': str(project.id),
            }
            body = _render_template(rule.body_template, variables)
            title = _render_template(rule.title_template, variables)

            link_query = _render_template(rule.link_query_template, variables)

            msg = UserMessage(
                user_id=user_id,
                user_type=user_type,
                rule_id=rule.id,
                source_type='investment_project',
                source_id=project.id,
                title=title,
                body=body,
                link_route=rule.link_route,
                link_query=link_query,
                status='pending',
            )
            db.session.add(msg)
            generated += 1

    if generated > 0:
        # 写触发日志
        log = MessageRuleLog(
            rule_id=rule.id,
            source_type='investment_project',
            source_id=None,  # 批量触发,不记录单个 source
            user_count=generated,
        )
        db.session.add(log)

    db.session.commit()
    return generated


def evaluate_all_rules() -> int:
    """评估所有启用的规则。返回总生成消息数。"""
    rules = MessageRule.query.filter_by(is_active=True).all()
    total = 0
    for rule in rules:
        try:
            total += evaluate_rule(rule)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(f'[message_engine] 规则 {rule.id} 评估失败: {exc}')
    return total
