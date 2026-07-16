#!/bin/bash
# deploy_prepare.sh — 生产部署前置:上传目录持久化(软链) + 健康检查红线
#
# 核心约定(DEPLOY.md「上传文件持久化」):
#   /www/wwwroot/invest-app/static/uploads 必须是 → /www/wwwroot/invest-app/data/uploads 的软链,
#   这样代码部署(git pull / reset)永远不会动到已上传文件。
#
# 用法:
#   ./scripts/deploy_prepare.sh                 # 默认 APP_DIR
#   APP_DIR=/path/to/invest-app ./scripts/deploy_prepare.sh
#   ./scripts/deploy_prepare.sh --force-sync    # 强制再同步一次存量(幂等,只拷贝缺失的)
#   ./scripts/deploy_prepare.sh --check-only    # 仅软链/权限检查,不做任何写操作
#
# 退出码:
#   0 通过  1 失败(需人工介入)  2 仅警告(软链缺失但目录仍直接存在)
set -euo pipefail

APP_DIR="${APP_DIR:-/www/wwwroot/invest-app}"
PERSIST_DIR="$APP_DIR/data/uploads"
STATIC_DIR="$APP_DIR/static/uploads"
PYTHON="$(command -v python3.11 || command -v python3 || command -v python)"
FORCE_SYNC=0
CHECK_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --force-sync) FORCE_SYNC=1 ;;
        --check-only) CHECK_ONLY=1 ;;
        -h|--help)
            sed -n '1,12p' "$0"
            exit 0
            ;;
    esac
done

fail() { echo "  ✗ $*"; exit 1; }
warn() { echo "  ⚠ $*"; }
ok()   { echo "  ✓ $*"; }

echo "[deploy_prepare] APP_DIR   = $APP_DIR"
echo "[deploy_prepare] PERSIST   = $PERSIST_DIR"
echo "[deploy_prepare] STATIC    = $STATIC_DIR"

# ── 0. 基本目录存在 ──
[ -d "$APP_DIR" ] || fail "APP_DIR 不存在: $APP_DIR"
[ -d "$APP_DIR/static" ] || mkdir -p "$APP_DIR/static"

# ── 1. 构造持久化目录 ──
if [ ! -d "$PERSIST_DIR" ]; then
    if [ "$CHECK_ONLY" = 1 ]; then
        warn "持久化目录不存在(PERSIST_DIR),仅检查模式下跳过创建"; exit 2
    fi
    mkdir -p "$PERSIST_DIR"
    ok "已创建持久化目录 $PERSIST_DIR"
fi

# ── 2. 保证 static/uploads 是指向 data/uploads 的软链 ──
ensure_symlink() {
    if [ -L "$STATIC_DIR" ]; then
        # 已是软链:校验目标
        local cur
        cur="$(readlink -f "$STATIC_DIR" 2>/dev/null || readlink "$STATIC_DIR")"
        if [ "$cur" = "$(readlink -f "$PERSIST_DIR")" ]; then
            ok "软链正确: $STATIC_DIR -> $PERSIST_DIR"
            return 0
        fi
        warn "软链目标异常: $STATIC_DIR -> $cur (期望 $PERSIST_DIR)"
        if [ "$CHECK_ONLY" = 1 ]; then return 2; fi
        rm "$STATIC_DIR"
        ln -s "$PERSIST_DIR" "$STATIC_DIR"
        ok "已重新链接: $STATIC_DIR -> $PERSIST_DIR"
        return 0
    fi

    if [ -d "$STATIC_DIR" ]; then
        # 是实体目录 → 把内容搬走再转型
        warn "$STATIC_DIR 是实体目录(非软链),这会在下次 git pull 时被覆盖"
        if [ "$CHECK_ONLY" = 1 ]; then return 2; fi
        # 只有源里有文件时才搬
        if [ -n "$(ls -A "$STATIC_DIR" 2>/dev/null)" ]; then
            if command -v rsync >/dev/null 2>&1; then
                rsync -a "$STATIC_DIR/" "$PERSIST_DIR/"
            else
                # Windows/精简环境降级:用 cp + mkdir -p
                ( cd "$STATIC_DIR" && find . -type f ) | while IFS= read -r rel; do
                    mkdir -p "$PERSIST_DIR/$(dirname "$rel")"
                    cp -f "$STATIC_DIR/$rel" "$PERSIST_DIR/$rel"
                done
            fi
            ok "已同步存量文件到持久化目录"
        fi
        rm -rf "$STATIC_DIR"
        ln -s "$PERSIST_DIR" "$STATIC_DIR"
        ok "已转型为软链: $STATIC_DIR -> $PERSIST_DIR"
        return 0
    fi

    # 不存在，直接建立软链
    if [ "$CHECK_ONLY" = 1 ]; then
        warn "$STATIC_DIR 不存在,仅检查模式下跳过创建软链"; return 2
    fi
    ln -s "$PERSIST_DIR" "$STATIC_DIR"
    ok "已新建软链: $STATIC_DIR -> $PERSIST_DIR"
}
ensure_symlink

# ── 3. 强制同步模式: 把 static 里现有文件一次性补到 data ──
if [ "$FORCE_SYNC" = 1 ] && [ "$CHECK_ONLY" = 0 ]; then
    echo "[deploy_prepare] 强制同步 static/uploads -> data/uploads ..."
    if command -v rsync >/dev/null 2>&1; then
        rsync -a "$STATIC_DIR/" "$PERSIST_DIR/"
    else
        ( cd "$STATIC_DIR" && find . -type f ) | while IFS= read -r rel; do
            mkdir -p "$PERSIST_DIR/$(dirname "$rel")"
            cp -f "$STATIC_DIR/$rel" "$PERSIST_DIR/$rel"
        done
    fi
    ok "强制同步完成"
fi

# ── 4. 写权限校验 ──
if [ -w "$PERSIST_DIR" ]; then
    ok "持久化目录可写: $PERSIST_DIR"
else
    fail "持久化目录不可写: $PERSIST_DIR (请检查 www / 进程用户权限)"
fi

# ── 5. 健康检查:上传文件数量 与 nginx 可访问性抽样 ──
FILE_COUNT="$(find "$PERSIST_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')"
ok "持久化目录文件数: $FILE_COUNT"

# 抽样 1 个文件测 URL 可访问性(仅当 nginx 在跑时)
SAMPLE_FILE="$(find "$PERSIST_DIR" -type f \( -name '*.jpg' -o -name '*.png' -o -name '*.jpeg' -o -name '*.webp' \) 2>/dev/null | head -1 || true)"
if [ -n "$SAMPLE_FILE" ]; then
    REL="${SAMPLE_FILE#$PERSIST_DIR/}"
    # 用 SERVER_NAME 探测,默认 localhost
    SERVER_NAME="${SERVER_NAME:-localhost}"
    HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://$SERVER_NAME/static/uploads/$REL" || echo '000')"
    if [ "$HTTP_CODE" = "200" ]; then
        ok "nginx 抽样访问正常: /static/uploads/$REL (HTTP $HTTP_CODE)"
    else
        warn "nginx 抽样访问异常: /static/uploads/$REL (HTTP $HTTP_CODE),请核对 nginx location /static/uploads 是否 alias 到 $PERSIST_DIR"
    fi
else
    warn "持久化目录里找不到 jpg/png/jpeg/webp 文件用于 nginx 抽样"
fi

echo
echo "[deploy_prepare] ✅ 准备完成. 文件数=$FILE_COUNT, 静态目录已是软链. 后续 deploy 不再会清空."
exit 0
