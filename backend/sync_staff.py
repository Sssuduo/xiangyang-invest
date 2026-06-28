"""
为每个用户（管理员 + 业务用户）创建对应的专班工作人员记录，并关联到业务用户账号
- 有对应 business_user 的：设置 user_id 关联
- 无对应 business_user 的（如 admin 独占）：user_id 置空
用法: python sync_staff.py
"""
from app import create_app
from models import AdminUser, BusinessUser, Staff
from extensions import db

app = create_app()

with app.app_context():
    created = 0
    updated = 0
    skipped = 0

    biz_users = BusinessUser.query.filter_by(is_active=True).all()
    biz_map = {bu.username: bu for bu in biz_users}
    biz_dn_map = {bu.display_name: bu for bu in biz_users}  # display_name → BusinessUser

    # ---- 管理员用户 ----
    admins = AdminUser.query.all()
    for admin in admins:
        name = admin.display_name or admin.username
        existing = Staff.query.filter_by(name=name).first()
        if existing:
            # 找到对应的 business_user
            bu = biz_map.get(admin.username) or biz_dn_map.get(name)
            if bu and existing.user_id != bu.id:
                existing.user_id = bu.id
                updated += 1
                print(f'[更新] {name} → 关联业务用户 {bu.username} (id={bu.id})')
            elif not bu:
                print(f'[跳过] {name} (无对应业务用户)')
                skipped += 1
            else:
                print(f'[跳过] {name} → 已关联 {bu.username}')
                skipped += 1
            continue

        bu = biz_map.get(admin.username) or biz_dn_map.get(name)
        staff = Staff(
            name=name,
            position='农高区创建专班工作人员',
            user_id=bu.id if bu else None,
            sort_order=admin.id,
            is_active=True,
        )
        db.session.add(staff)
        created += 1
        tag = f'business_user_id={bu.id}' if bu else 'NULL'
        print(f'[创建] 管理员 {name} → Staff ({tag})')

    # ---- 业务用户 ----
    for bu in biz_users:
        name = bu.display_name or bu.username
        if bu.username in ('demo',):
            print(f'[跳过] 业务用户 {name} (demo账号)')
            skipped += 1
            continue

        existing = Staff.query.filter_by(name=name).first()
        if existing:
            if existing.user_id != bu.id:
                existing.user_id = bu.id
                updated += 1
                print(f'[更新] {name} → 关联业务用户 {bu.username} (id={bu.id})')
            else:
                print(f'[跳过] 业务用户 {name} → 已关联 {bu.username}')
                skipped += 1
            continue

        staff = Staff(
            name=name,
            position='农高区创建专班工作人员',
            user_id=bu.id,
            sort_order=100 + bu.id,
            is_active=True,
        )
        db.session.add(staff)
        created += 1
        print(f'[创建] 业务用户 {name} → Staff (user_id={bu.id})')

    db.session.commit()
    print(f'\n完成: 新建 {created} 人, 更新 {updated} 人, 跳过 {skipped} 人')
