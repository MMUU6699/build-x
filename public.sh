#!/bin/bash
# public.sh — bring the app to the public web in one command.
# Usage: ./public.sh   (run from repo root, via git-bash)
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR="${TEMP:-/tmp}"
KNOWN_BIN="/c/Users/musta/AppData/Local/Temp/opencode/cloudflared.exe"
BIN="${CLOUDFLARED_BIN:-}"
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
  if [ -f "$KNOWN_BIN" ]; then
    BIN="$KNOWN_BIN"
  elif command -v cloudflared >/dev/null 2>&1; then
    BIN="$(command -v cloudflared)"
  else
    BIN="$TEMP_DIR/cloudflared.exe"
  fi
fi
LOG="$TEMP_DIR/opencode-cf-public.log"
ERR="$TEMP_DIR/opencode-cf-public.err"
URL_FILE="$TEMP_DIR/opencode-public-url.txt"

cd "$ROOT" || exit 1

echo "==> [1/3] Ensuring the stack is up..."
./dev.sh up -d >/dev/null 2>&1

echo "==> [2/3] Ensuring cloudflared binary..."
if [ ! -f "$BIN" ]; then
  echo "    downloading cloudflared (first run only)..."
  curl -L -o "$BIN" \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
fi
echo "    using: $BIN"

echo "==> [3/3] Starting the tunnel..."
if ps | grep -q cloudflared; then
  echo "    tunnel already running"
else
  rm -f "$LOG" "$ERR"
  nohup "$BIN" tunnel --url http://localhost:5173 --no-autoupdate >"$LOG" 2>"$ERR" &
  echo "    tunnel starting..."
fi

URL=""
for i in $(seq 1 12); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" "$ERR" 2>/dev/null | tail -1)
  [ -n "$URL" ] && break
  sleep 5
done

if [ -z "$URL" ]; then
  echo "ERROR: could not find the public URL in:" && echo "  $LOG" && echo "  $ERR"
  exit 1
fi

echo "$URL" > "$URL_FILE"
echo ""
echo "=================================================================="
echo "  PUBLIC URL: $URL"
echo "  (saved to $URL_FILE)"
echo "=================================================================="
cmd //c start "$URL" 2>/dev/null || true
