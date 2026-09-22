#!/bin/bash
# Double-click this file in Finder to install (first run) and launch Hero Studio.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== Hero Studio ==="

# --- Find or install Python 3.11+ ---
PYBIN=""
for cand in python3.11 python3.12 python3.13 "$HOME/.local/bin/python3.11"; do
  if command -v "$cand" >/dev/null 2>&1; then
    PYBIN="$(command -v "$cand")"
    break
  fi
done

if [ -z "$PYBIN" ]; then
  echo "No Python 3.11+ found. Installing one locally via uv (no admin password needed)..."
  if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
  uv python install 3.11
  PYBIN="$(uv python find 3.11)"
fi

echo "Using Python: $PYBIN"

# --- First-run setup ---
if [ ! -d ".venv" ]; then
  echo "First run: setting up (this takes a few minutes)..."
  "$PYBIN" -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
else
  source .venv/bin/activate
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env — add your Runway/Kling API key from the Settings tab once the app opens."
fi

# --- Launch ---
python -m webapp.server
