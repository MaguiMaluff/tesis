#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Load env (tolerate CRLF)
if [[ ! -f ".env" ]]; then
  echo "[dev] Missing .env (create it from .env.example)"
  exit 1
fi
set -a
source <(sed 's/\r$//' .env)
set +a

PORT="${PORT:-3000}"

# Basic checks
command -v python3 >/dev/null || { echo "[dev] python3 not found"; exit 1; }
command -v ngrok >/dev/null || { echo "[dev] ngrok not found"; exit 1; }

# Choose terminal emulator for ngrok
TERM_CMD=""
if command -v x-terminal-emulator >/dev/null; then
  TERM_CMD="x-terminal-emulator -e"
elif command -v gnome-terminal >/dev/null; then
  TERM_CMD="gnome-terminal --"
elif command -v konsole >/dev/null; then
  TERM_CMD="konsole -e"
elif command -v xfce4-terminal >/dev/null; then
  TERM_CMD="xfce4-terminal -e"
fi

if [[ -z "$TERM_CMD" ]]; then
  echo "[dev] No terminal emulator found to open ngrok separately."
  echo "[dev] Install one (e.g. gnome-terminal) or run ngrok manually."
  exit 1
fi

pids=()

start_bg() {
  local name="$1"
  shift
  echo "[dev] starting $name: $*"
  "$@" &
  local pid="$!"
  pids+=("$pid")
  echo "[dev] $name pid=$pid"
}

cleanup() {
  echo
  echo "[dev] stopping..."
  for pid in "${pids[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "[dev] stopped."
}

trap cleanup INT TERM EXIT

echo "[dev] repo=$ROOT_DIR"
echo "[dev] port=$PORT"
echo

# Start backend processes (same terminal output)
start_bg api python3 -m apps.api.app
start_bg worker python3 -m apps.worker.worker
start_bg ai python3 -m apps.worker.ai_runner

echo "[dev] starting ngrok in a new terminal..."
$TERM_CMD "ngrok http $PORT" >/dev/null 2>&1 &

echo
echo "[dev] running."
echo "[dev] local webhook: http://localhost:${PORT}/webhook"
echo "[dev] Ctrl+C to stop everything."
echo

# Keep alive
while true; do sleep 1; done