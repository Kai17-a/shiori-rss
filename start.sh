#!/bin/sh
set -eu

export API_PORT="${API_PORT:-8000}"
export DATABASE_URL="${DATABASE_URL:-/data/data.db}"

mkdir -p "$(dirname "$DATABASE_URL")"
./dbmate -u "sqlite:$DATABASE_URL" up

cleanup() {
  trap - EXIT INT TERM
  for pid in ${API_PID:-} ${FRONTEND_PID:-} ${SCHEDULER_PID:-}; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in ${API_PID:-} ${FRONTEND_PID:-} ${SCHEDULER_PID:-}; do
    wait "$pid" 2>/dev/null || true
  done
}

terminate() {
  cleanup
  exit 0
}

trap cleanup EXIT
trap terminate INT TERM

fastapi run api/main.py --port "$API_PORT" &
API_PID=$!

nginx -g 'daemon off;' &
FRONTEND_PID=$!

sh ./render-scheduler.sh > scheduler
supercronic ./scheduler &
SCHEDULER_PID=$!

while kill -0 "$API_PID" 2>/dev/null \
  && kill -0 "$FRONTEND_PID" 2>/dev/null \
  && kill -0 "$SCHEDULER_PID" 2>/dev/null; do
  sleep 1
done

echo "A required process stopped; shutting down the container." >&2
exit 1
