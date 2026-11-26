#!/usr/bin/env bash
# install.sh - check requirements, then link (or copy) this folder into the Claude Code or Antigravity skills directory.
# Usage:  bash install.sh [--antigravity] [--dir PATH] [--copy] [--force]
#   default: ~/.claude/skills/robloxanimax (Claude Code); --antigravity: ~/.gemini/config/skills/robloxanimax
# Needs cinematicanimation, Blender 5.x, Python 3 and ffmpeg. Nothing is downloaded or installed.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.claude/skills/robloxanimax"; AGENT="Claude Code"; COPY=0; FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --antigravity) TARGET="$HOME/.gemini/config/skills/robloxanimax"; AGENT="Antigravity"; shift;;
    --dir) TARGET="${2:?--dir needs a path}"; AGENT="your agent"; shift 2;;
    --copy) COPY=1; shift;;
    --force) FORCE=1; shift;;
    -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done
MISSING=0; ok() { printf '  [ok]   %s\n' "$1"; }; bad() { printf '  [miss] %s\n' "$1"; MISSING=1; }; opt() { printf '  [opt]  %s\n' "$1"; }
echo "robloxanimax: checking requirements"
CK="${CINE_KIT:-$(dirname "$TARGET")/cinematicanimation/blender}"
[ -f "$CK/cine_kit.py" ] && ok "cinematicanimation ($CK)" || bad "cinematicanimation (install it first, or set CINE_KIT to its blender/ folder)"
{ [ -x /Applications/Blender.app/Contents/MacOS/Blender ] || command -v blender >/dev/null; } && ok "Blender" || bad "Blender 5.x"
command -v python3 >/dev/null && ok "python3" || bad "Python 3.9+"
command -v ffmpeg >/dev/null && ok "ffmpeg" || bad "ffmpeg (voice, mix, assembly)"
command -v uv >/dev/null && ok "uv (cast card, with Pillow)" || opt "uv: only for scripts/cast_card.py (or any Python with Pillow)"
grep -q '"meshy"' "$HOME/.claude.json" 2>/dev/null && ok "Meshy MCP server configured" || opt "Meshy MCP server: only to generate new models (https://docs.meshy.ai/en/api/ai)"
[ "$MISSING" = 0 ] || { echo; echo "Install the missing requirements above, then run this again. Nothing was changed." >&2; exit 1; }
echo
if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  [ "$FORCE" = 1 ] || { echo "$TARGET already exists. Re-run with --force to replace it." >&2; exit 1; }
  rm -rf "${TARGET:?}"
fi
mkdir -p "$(dirname "$TARGET")"
if [ "$COPY" = 1 ]; then
  mkdir -p "$TARGET"; (cd "$HERE" && tar --exclude=.git --exclude='examples/*/out' --exclude=__pycache__ -cf - .) | (cd "$TARGET" && tar -xf -)
  echo "Copied to $TARGET"
else
  ln -s "$HERE" "$TARGET"; echo "Linked $TARGET -> $HERE"
fi
echo "Done. In $AGENT, ask for a Roblox animated film with a Meshy cast, or run /robloxanimax."
