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
# 代码备份只含代码，排除：
#   - 用户数据目录（static/uploads、static/meetings、backend/static）——不进代码快照
#   - 备份目录本身（backups）——避免递归包含历史备份导致指数膨胀（曾因此撑爆磁盘）
#   - 构建产物与缓存（node_modules、dist、__pycache__、.git、instance）
tar -czf "$BACKUP_DIR/code_deploy_${TIMESTAMP}.tar.gz" \
    --exclude='frontend/node_modules' \
    --exclude='frontend/dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='*.bak' \
    --exclude='static/uploads' \
    --exclude='static/meetings' \
    --exclude='backend/static' \
    --exclude='backups' \
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
    # 排除 data：static/data/*.json 是地图省份/城市数据，由 git 跟踪但不在 frontend/dist 中，
    # 若被 --delete 清空会导致 ChinaMap.vue 的 fetch 全部 404。故同步时保留该目录。
    rsync -a --delete --exclude='uploads' --exclude='data' "$APP_DIR/frontend/dist/" "$APP_DIR/static/"
else
    # 清空 static 后整体复制（保留目录本身与 data 地图数据）
    find "$APP_DIR/static" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' ! -name 'data' -exec rm -rf {} + 2>/dev/null || true
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

# ── 7. 持久化 nginx /static/uploads/ 配置（防止环境漂移）──
# 历史原因：nginx 的 /static/uploads/ alias 曾被 V15.5 修复为 backend/static/uploads/，
# 但部署流程不动 nginx，导致修复被覆盖回错误目录（缺失 backend 段）。
# 这里做一次幂等的 alias 修正 + 全杀 worker，避免首页轮播第一张图 404 复发。
echo ""
echo "[7/7] 持久化 nginx /static/uploads/ 配置..."

NGINX_CONF="/etc/nginx/conf.d/invest-app.conf"

if [ -f "$NGINX_CONF" ]; then
    # 检测是否存在错误 alias（缺少 backend 段）
    if grep -q "alias /www/wwwroot/invest-app/static/uploads/;" "$NGINX_CONF" 2>/dev/null; then
        echo "  ⚠ 检测到错误 alias，进行修正..."
        # 备份（保留，便于回溯）
        cp -p "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%Y%m%d_%H%M%S)"
        # 文件可能被 chattr +i 锁定，先解锁
        if lsattr "$NGINX_CONF" 2>/dev/null | grep -q '^....i'; then
            chattr -i "$NGINX_CONF"
            echo "  ✓ 已解除 chattr +i 锁定"
        fi
        # 修正 alias
        sed -i 's|alias /www/wwwroot/invest-app/static/uploads/;|alias /www/wwwroot/invest-app/backend/static/uploads/;|' "$NGINX_CONF"
        # 重新锁定（防止误改）
        chattr +i "$NGINX_CONF"
        echo "  ✓ alias 已修正"
        # 验证配置
        if nginx -t 2>/dev/null; then
            echo "  ✓ nginx 配置验证通过"
            # 全杀 worker + reload（避免老 worker 持有旧配置）
            nginx -s stop 2>/dev/null || true
            sleep 1
            nginx 2>/dev/null || nginx -s reload 2>/dev/null || true
            echo "  ✓ nginx 已重启（全杀 worker）"
        else
            echo "  ⚠ nginx 配置验证失败，回滚备份"
            cp -p "${NGINX_CONF}.bak."* "$NGINX_CONF" 2>/dev/null || true
            nginx -s stop 2>/dev/null || true
            sleep 1
            nginx 2>/dev/null || true
        fi
    else
        echo "  ✓ nginx alias 正确，跳过修正"
    fi
else
    echo "  ⚠ 未找到 $NGINX_CONF，跳过 nginx 修正"
fi

echo ""
echo "=============================================="
echo "  最终部署完成"
echo "=============================================="
