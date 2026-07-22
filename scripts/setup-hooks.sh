#!/usr/bin/env bash
# setup-hooks.sh — 为本仓库启用分发式 git hooks（简化 GitFlow 强制流程）
# 用法: bash scripts/setup-hooks.sh
# 任何 clone 本仓库的 agent / 协作者都应运行一次，使 pre-commit / pre-push 生效。
set -e

ROOT="$(git rev-parse --show-toplevel)"

if [ ! -d "$ROOT/.githooks" ]; then
  echo "✗ 未找到 $ROOT/.githooks 目录，无法启用 hooks。" >&2
  exit 1
fi

git config core.hooksPath "$ROOT/.githooks"
chmod +x "$ROOT/.githooks"/* 2>/dev/null || true

echo "✓ core.hooksPath -> $ROOT/.githooks"
echo "  pre-commit / pre-push 将强制执行简化 GitFlow 流程（详见 AGENTS.md）。"
echo "  绕过开关: ALLOW_PROTECTED_COMMIT=1 / ALLOW_PROTECTED_PUSH=1"
