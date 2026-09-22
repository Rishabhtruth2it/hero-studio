#!/bin/bash
# Hero Studio.app launcher — starts the local server (if needed) and opens
# it in an app-style window. @@PROJECT_DIR@@ is filled in by build-app.sh.
set -u

PROJECT="@@PROJECT_DIR@@"
PORT=8765
LOG="$HOME/Library/Logs/HeroStudio.log"

export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

fail() { /usr/bin/osascript -e "display alert \"Hero Studio\" message \"$1\"" >/dev/null 2>&1; exit 1; }

[ -d "$PROJECT" ] || fail "Project folder not found at $PROJECT."
cd "$PROJECT" || fail "Cannot enter $PROJECT"
mkdir -p "$(dirname "$LOG")"
echo "=== launch $(date) ===" >> "$LOG"

# First-run setup: create the venv and install deps if they're missing.
if [ ! -d ".venv" ]; then
  PYBIN=""
  for cand in python3.11 python3.12 python3.13; do
    command -v "$cand" >/dev/null 2>&1 && PYBIN="$(command -v "$cand")" && break
  done
  [ -n "$PYBIN" ] || fail "No Python 3.11+ found. Install it, then reopen Hero Studio."
  "$PYBIN" -m venv .venv >> "$LOG" 2>&1 || fail "Could not create the virtual environment. See $LOG"
  ./.venv/bin/pip install --upgrade pip -q >> "$LOG" 2>&1
  ./.venv/bin/pip install -r requirements.txt -q >> "$LOG" 2>&1 || fail "Dependency install failed. See $LOG"
fi
[ -f ".env" ] || cp .env.example .env

# Always start a fresh server so every launch runs the current code.
pkill -f "uvicorn webapp.server:app" 2>/dev/null || true
sleep 1
nohup ./.venv/bin/python -m uvicorn webapp.server:app --host 127.0.0.1 --port "$PORT" --log-level warning >> "$LOG" 2>&1 &

for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || fail "Hero Studio did not start. See $LOG"

URL="http://127.0.0.1:$PORT"
# Call the browser binary directly, not `open -na` — when the browser is
# already running (the common case), `open -na ... --args` silently drops
# the args and just focuses the existing window instead of opening an
# app-mode one.
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
EDGE="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
if [ -x "$CHROME" ]; then
  "$CHROME" --app="$URL" --new-window >> "$LOG" 2>&1 &
elif [ -x "$BRAVE" ]; then
  "$BRAVE" --app="$URL" --new-window >> "$LOG" 2>&1 &
elif [ -x "$EDGE" ]; then
  "$EDGE" --app="$URL" --new-window >> "$LOG" 2>&1 &
else
  open "$URL"
fi
