"""
一次性脚本：创建 11 个业务用户账号
运行方式：在项目根目录执行 python scripts/create_business_users.py
"""

import sys
import os

# 将项目根目录添加到 sys.path（兼容本地和服务器环境）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
sys.path.insert(0, BACKEND_DIR)  # 服务器上 backend/ 作为顶层包
sys.path.insert(0, os.path.join(BACKEND_DIR, '..'))  # 本地开发: backend.app

# 尝试两种导入方式
try:
    from app import create_app
    from models import BusinessUser
    from extensions import db
except ImportError:
    from backend.app import create_app
    from backend.models import BusinessUser
    from backend.extensions import db

USERS = [
    ('jiang', '姜主任'),
    ('jing', '靖主任'),
    ('gu', '顾寅祺'),
    ('wang', '王主任'),
    ('cui', '崔主任'),
    ('ren', '任主任'),
    ('qi', '齐群群'),
    ('hou', '侯斌'),
    ('shi', '史主任'),
    ('tao', '陶荣兵'),
    ('sai', '赛主任'),
]

PASSWORD = 'nonggaoqu666'
# 权限：有编辑权限，无删除/批量删除权限
PERMISSIONS = {
    'investment': {'edit': True},
    'activity': {'edit': True},
    'demand': {'edit': True},
}


def main():
    app = create_app()
    with app.app_context():
        for username, display_name in USERS:
            existing = BusinessUser.query.filter_by(username=username).first()
            if existing:
                print(f'[跳过] {username} ({display_name}) — 已存在')
                continue
            user = BusinessUser(username=username, display_name=display_name, is_active=True)
            user.set_password(PASSWORD)
            user.set_permissions(PERMISSIONS)
            db.session.add(user)
            print(f'[创建] {username} ({display_name})')
        db.session.commit()
        print('\n完成！')
        print(f'密码统一为: {PASSWORD}')
        print(f'权限: 可编辑（无删除/批量删除）')


if __name__ == '__main__':
    main()
