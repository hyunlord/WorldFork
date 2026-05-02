#!/bin/bash
# install_hooks.sh — Git Hooks 설치
# Tier 1.5 D2: pre-commit (Lite) + pre-push (Heavy) 설치
#
# 사용:
#   bash scripts/install_hooks.sh          # 설치
#   bash scripts/install_hooks.sh --check  # 설치 확인

set -u

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOKS_SRC="$PROJECT_ROOT/scripts/hooks"
HOOKS_DST="$PROJECT_ROOT/.git/hooks"

MODE="${1:-install}"

check_hook() {
    local name="$1"
    local dst="$HOOKS_DST/$name"
    if [ -x "$dst" ]; then
        echo "  ✅ $name — installed"
        return 0
    else
        echo "  ❌ $name — missing"
        return 1
    fi
}

if [ "$MODE" = "--check" ]; then
    echo "=== Git Hooks 설치 상태 ==="
    ALL_OK=0
    check_hook pre-commit || ALL_OK=1
    check_hook pre-push   || ALL_OK=1
    exit $ALL_OK
fi

echo "=== Git Hooks 설치 ==="
echo "src: $HOOKS_SRC"
echo "dst: $HOOKS_DST"
echo ""

if [ ! -d "$HOOKS_SRC" ]; then
    echo "❌ scripts/hooks/ 디렉토리 없음"
    exit 1
fi

for hook in pre-commit pre-push; do
    src="$HOOKS_SRC/$hook"
    dst="$HOOKS_DST/$hook"

    if [ ! -f "$src" ]; then
        echo "  ⚠️  $hook: src 없음 ($src) — 스킵"
        continue
    fi

    # 기존 hook 백업
    if [ -f "$dst" ] && [ ! -f "${dst}.bak" ]; then
        cp "$dst" "${dst}.bak"
        echo "  📦 $hook: 기존 hook 백업 → ${hook}.bak"
    fi

    cp "$src" "$dst"
    chmod +x "$dst"
    echo "  ✅ $hook: 설치 완료"
done

echo ""
echo "=== 확인 ==="
bash "$PROJECT_ROOT/scripts/install_hooks.sh" --check
