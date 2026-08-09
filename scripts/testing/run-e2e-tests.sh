#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)

frontend_port=${FRONTEND_PORT:-3001}
api_port=${API_PORT:-8001}
database_path=${DATABASE_URL:-/tmp/rss-feeder-e2e/data.db}

cleanup() {
    if [ -n "${api_pid:-}" ]; then
        kill "$api_pid" 2>/dev/null || true
    fi
    if [ -n "${frontend_pid:-}" ]; then
        kill "$frontend_pid" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

wait_for_url() {
    url=$1
    attempts=${2:-30}

    for i in $(seq 1 "$attempts"); do
        if curl -fsS "$url" >/dev/null; then
            return 0
        fi
        sleep 2
    done

    echo "Timed out waiting for $url" >&2
    return 1
}

start_api_server() {
    mkdir -p "$(dirname "$database_path")"
    cd "$repo_root"
    # Tests assert absolute record counts, so every run needs a clean database.
    rm -f "$database_path"
    mise x -- dbmate -u "sqlite:$database_path" up
    DATABASE_URL="$database_path" \
        uv run --directory "$repo_root/api" uvicorn api.main:app --app-dir "$repo_root" --host 127.0.0.1 --port "$api_port" > /tmp/rss-feeder-api-e2e.log 2>&1 &
    api_pid=$!
}

start_frontend_server() {
    cd "$repo_root/frontend"
    PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
        bunx nuxt dev --host 0.0.0.0 --port "$frontend_port" --strictPort > /tmp/rss-feeder-frontend-e2e.log 2>&1 &
    frontend_pid=$!
}

cd "$repo_root/frontend"
# This is idempotent and installs the exact browser revision required by the
# current Playwright package, even when an older revision is already cached.
bunx playwright install chromium

start_api_server
wait_for_url "http://127.0.0.1:$api_port/health"
start_frontend_server

wait_for_url "http://127.0.0.1:$api_port/health"
wait_for_url "http://127.0.0.1:$frontend_port"

PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
PLAYWRIGHT_FRONTEND_BASE_URL="http://127.0.0.1:$frontend_port" \
bunx playwright test "$@"
