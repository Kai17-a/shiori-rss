#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")" && pwd)
api_port=${API_PORT:-8000}
frontend_port=${FRONTEND_PORT:-3000}
database_path=${DATABASE_URL:-$repo_root/data/data.db}

cleanup() {
    trap - EXIT INT TERM
    for pid in ${api_pid:-} ${frontend_pid:-}; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in ${api_pid:-} ${frontend_pid:-}; do
        wait "$pid" 2>/dev/null || true
    done
}

terminate() {
    cleanup
    exit 0
}

trap cleanup EXIT
trap terminate INT TERM

DATABASE_URL="$database_path" \
    uv run --directory "$repo_root/api" uvicorn api.main:app \
    --app-dir "$repo_root" --host 127.0.0.1 --port "$api_port" &
api_pid=$!

cd "$repo_root/frontend"
NUXT_TELEMETRY_DISABLED=1 \
    PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
    bunx nuxt dev --host 0.0.0.0 --port "$frontend_port" --strictPort &
frontend_pid=$!

echo "API: http://127.0.0.1:$api_port"
echo "Frontend: http://127.0.0.1:$frontend_port"

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
    sleep 1
done

echo "A local development process stopped; shutting down." >&2
exit 1
