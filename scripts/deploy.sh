#!/bin/bash
# deploy.sh — 生产环境部署脚本
# 用法: ./deploy.sh [分支名，默认 master]
set -e

APP_DIR="/www/wwwroot/invest-app"
BACKUP_DIR="$APP_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BRANCH="${1:-master}"

echo "=============================================="
echo "  襄阳农高区招商系统 - 生产环境部署"
echo "=============================================="
echo "分支: $BRANCH"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ── 1. 数据库备份 ──
echo "[1/6] 备份数据库..."
# 使用 sqlite3 .backup 热备份（与现有 backup_db.sh 一致，保证写操作期间一致性）
if [ -f "$APP_DIR/instance/app.db" ]; then
    sqlite3 "$APP_DIR/instance/app.db" ".backup '$BACKUP_DIR/app_deploy_${TIMESTAMP}.db'"
    echo "  ✓ 已备份到: $BACKUP_DIR/app_deploy_${TIMESTAMP}.db"
else
    echo "  ⚠ 未找到数据库文件，跳过备份"
fi

# ── 2. 代码备份 ──
echo "[2/6] 备份当前代码..."
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/code_deploy_${TIMESTAMP}.tar.gz" \
    --exclude='frontend/node_modules' \
    --exclude='frontend/dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='*.bak' \
    -C "$APP_DIR" . 2>/dev/null || true
echo "  ✓ 已备份到: $BACKUP_DIR/code_deploy_${TIMESTAMP}.tar.gz"

# ── 3. 拉取代码 ──
echo "[3/6] 拉取最新代码..."
cd "$APP_DIR"
git fetch origin --tags
git checkout "$BRANCH"
# 直接对齐远端，避免工作区脏/本地提交导致 pull 冲突使自动部署卡住
git reset --hard "origin/$BRANCH"
CURRENT_TAG=$(git describe --tags 2>/dev/null || echo "无Tag")
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "  ✓ 当前版本: $CURRENT_TAG ($CURRENT_COMMIT)"

# 清除 Python 字节码缓存（避免旧 .pyc 导致路由 404）
echo "  → 清除 __pycache__ ..."
find "$APP_DIR/backend" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR/backend" -name '*.pyc' -delete 2>/dev/null || true
echo "  ✓ 缓存已清除"

# ── 4. 后端依赖更新 ──
echo "[4/6] 更新后端依赖..."
pip3.11 install -r backend/requirements.txt -q 2>&1 | tail -1
echo "  ✓ 依赖更新完成"

# ── 5. 前端构建 ──
echo "[5/6] 构建前端..."
cd "$APP_DIR/frontend"
npm install --silent 2>&1 | tail -1
npm run build 2>&1 | tail -3
cd "$APP_DIR"
echo "  ✓ 前端构建完成"

# ── 5.1 同步 dist 到 static（保留 uploads 目录）──
echo "  → 同步 dist 到 static ..."
if [ -d "$APP_DIR/static/uploads" ]; then
    mv "$APP_DIR/static/uploads" "/tmp/uploads_deploy_backup"
fi
# 优先用 rsync，否则退回 cp
if command -v rsync &>/dev/null; then
    rsync -a --delete --exclude='uploads' "$APP_DIR/frontend/dist/" "$APP_DIR/static/"
else
    # 清空 static 后整体复制（保留目录本身）
    find "$APP_DIR/static" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -exec rm -rf {} + 2>/dev/null || true
    cp -r "$APP_DIR/frontend/dist/"* "$APP_DIR/static/" 2>/dev/null || true
fi
if [ -d "/tmp/uploads_deploy_backup" ]; then
    mv "/tmp/uploads_deploy_backup" "$APP_DIR/static/uploads"
fi
echo "  ✓ dist 已同步到 static"

# ── 6. 重启服务 ──
echo "[6/6] 重启服务..."
systemctl restart invest-app
sleep 2
if systemctl is-active --quiet invest-app; then
    echo "  ✓ invest-app 重启成功"
else
    echo "  ✗ invest-app 启动失败！请检查日志: journalctl -u invest-app -n 30"
    exit 1
fi

systemctl restart nginx
echo "  ✓ nginx 重启成功"

echo ""
echo "=============================================="
echo "  部署完成!"
echo "  版本: $CURRENT_TAG"
echo "  提交: $CURRENT_COMMIT"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
