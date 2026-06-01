#!/usr/bin/env bash
# Install boss-greeting-rank skill for OpenClaw or Cursor (symlink).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-}"

usage() {
  echo "Usage: $0 <openclaw|cursor>"
  echo ""
  echo "  openclaw  -> ~/.openclaw/skills/boss-greeting-rank"
  echo "  cursor    -> ~/.cursor/skills/boss-greeting-rank"
  exit 1
}

[[ -n "$TARGET" ]] || usage

case "$TARGET" in
  openclaw)
    DEST="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/skills}/boss-greeting-rank"
    ;;
  cursor)
    DEST="${CURSOR_SKILLS_DIR:-$HOME/.cursor/skills}/boss-greeting-rank"
    ;;
  *)
    usage
    ;;
esac

mkdir -p "$(dirname "$DEST")"
if [[ -e "$DEST" && ! -L "$DEST" ]]; then
  echo "Refusing to overwrite non-symlink: $DEST" >&2
  exit 1
fi
ln -sfn "$REPO_DIR" "$DEST"
chmod +x "$REPO_DIR/scripts/"*.py 2>/dev/null || true
chmod +x "$REPO_DIR/install.sh" 2>/dev/null || true

echo "Installed boss-greeting-rank -> $DEST"
echo "Next: ensure @reconcrap/boss-recommend-mcp >= 2.0.57 (see runtime/README.md)"
