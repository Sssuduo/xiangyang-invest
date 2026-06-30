"""回填 investment_projects 和 construction_projects 的 last_updated_at 字段"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # 1. 添加字段（如已存在则忽略）
    for table in ['investment_projects', 'construction_projects']:
        try:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN last_updated_at DATETIME"))
            print(f"[OK] Added last_updated_at to {table}")
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print(f"[SKIP] Column already exists in {table}")
            else:
                print(f"[WARN] {e}")

    # 2. 回填
    db.session.execute(text("""
        UPDATE investment_projects
        SET last_updated_at = COALESCE(updated_at, created_at, datetime('now'))
        WHERE last_updated_at IS NULL
    """))
    db.session.execute(text("""
        UPDATE construction_projects
        SET last_updated_at = COALESCE(updated_at, created_at, datetime('now'))
        WHERE last_updated_at IS NULL
    """))
    db.session.commit()
    print("[OK] Backfilled last_updated_at")

    # 3. 验证
    inv = db.session.execute(text(
        "SELECT count(*) FROM investment_projects WHERE last_updated_at IS NOT NULL"
    )).scalar()
    con = db.session.execute(text(
        "SELECT count(*) FROM construction_projects WHERE last_updated_at IS NOT NULL"
    )).scalar()
    print(f"[OK] Verified: {inv} investment, {con} construction")
