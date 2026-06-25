"""
权限管理脚本：创建超级管理员 + 升级已有用户权限

功能：
  1. 创建/确保 suduo 管理员账号（拥有最高权限）
  2. 升级所有已有业务用户的权限，为新功能模块补充默认权限
     - 新增模块授予 add/edit/import = True，delete/batch_delete = False

用法：
    python scripts/upgrade_permissions.py

幂等：多次运行不会重复创建用户或覆盖已有更高权限
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, '..'))

try:
    from app import create_app
    from models import AdminUser, BusinessUser
    from extensions import db
except ImportError:
    from backend.app import create_app
    from backend.models import AdminUser, BusinessUser
    from backend.extensions import db

# ============================================================
# 配置
# ============================================================

# 超级管理员
SUPER_ADMIN_USERNAME = 'suduo'
SUPER_ADMIN_PASSWORD = 'suduo2026'
SUPER_ADMIN_DISPLAY = '苏铎'

# 所有已知模块及其支持的权限操作
# 新增模块时只需在这里添加即可
ALL_MODULES = {
    'investment':    ['add', 'edit', 'delete', 'batch_delete', 'import'],
    'activity':      ['add', 'edit', 'delete', 'batch_delete', 'import'],
    'demand':        ['add', 'edit', 'delete', 'batch_delete', 'import'],
    'construction':  ['add', 'edit', 'delete', 'batch_delete', 'import'],
}

# 升级时默认授予的权限（不给 delete / batch_delete）
UPGRADE_DEFAULT_ACTIONS = ['add', 'edit', 'import']


def create_super_admin():
    """创建/确保 suduo 管理员存在"""
    admin = AdminUser.query.filter_by(username=SUPER_ADMIN_USERNAME).first()
    if admin:
        # 确保密码是最新的
        admin.set_password(SUPER_ADMIN_PASSWORD)
        admin.display_name = SUPER_ADMIN_DISPLAY
        print(f'[管理员] {SUPER_ADMIN_USERNAME} 已存在，密码已更新')
    else:
        admin = AdminUser(
            username=SUPER_ADMIN_USERNAME,
            display_name=SUPER_ADMIN_DISPLAY
        )
        admin.set_password(SUPER_ADMIN_PASSWORD)
        db.session.add(admin)
        print(f'[管理员] {SUPER_ADMIN_USERNAME} 已创建')


def create_super_business_user():
    """创建/确保 suduo 业务用户存在（全权限）"""
    user = BusinessUser.query.filter_by(username=SUPER_ADMIN_USERNAME).first()
    full_perms = {
        module: {action: True for action in actions}
        for module, actions in ALL_MODULES.items()
    }

    if user:
        user.set_password(SUPER_ADMIN_PASSWORD)
        user.display_name = SUPER_ADMIN_DISPLAY
        user.is_active = True
        # 始终给满权限
        user.set_permissions(full_perms)
        print(f'[业务用户] {SUPER_ADMIN_USERNAME} 已存在，权限已刷新为全权限')
    else:
        user = BusinessUser(
            username=SUPER_ADMIN_USERNAME,
            display_name=SUPER_ADMIN_DISPLAY,
            is_active=True
        )
        user.set_password(SUPER_ADMIN_PASSWORD)
        user.set_permissions(full_perms)
        db.session.add(user)
        print(f'[业务用户] {SUPER_ADMIN_USERNAME} 已创建（全权限）')


def upgrade_all_business_users():
    """
    升级所有业务用户的权限：
    - 对于用户缺少的模块，授予默认权限（add/edit/import = True）
    - 对于用户已有模块但缺少的操作（如新增 import），补充权限
    - 不会降级已有的 delete / batch_delete 权限
    """
    users = BusinessUser.query.all()
    upgraded_count = 0

    for user in users:
        perms = user.get_permissions()
        modified = False

        for module, actions in ALL_MODULES.items():
            if module not in perms:
                # 新模块：授予默认权限（不给删除）
                perms[module] = {
                    action: (action in UPGRADE_DEFAULT_ACTIONS)
                    for action in actions
                }
                modified = True
            else:
                # 已有模块：补充缺失的操作权限
                for action in actions:
                    if action not in perms[module]:
                        # 新操作：delete 类默认不给
                        perms[module][action] = (action in UPGRADE_DEFAULT_ACTIONS)
                        modified = True

        if modified:
            user.set_permissions(perms)
            upgraded_count += 1
            print(f'  [升级] {user.username} ({user.display_name})')

    return upgraded_count


def main():
    app = create_app()
    with app.app_context():
        print('=' * 60)
        print('权限管理脚本')
        print('=' * 60)

        # 1. 超级管理员
        print('\n--- 超级管理员 ---')
        create_super_admin()

        # 2. 超级业务用户（全权限）
        print('\n--- 超级业务用户 ---')
        create_super_business_user()

        # 3. 升级已有用户
        print('\n--- 升级已有用户权限 ---')
        n = upgrade_all_business_users()
        if n > 0:
            print(f'\n{n} 个用户的权限已升级')
        else:
            print('所有用户权限已是最新，无需升级')

        db.session.commit()
        print('\n完成！')


if __name__ == '__main__':
    main()
