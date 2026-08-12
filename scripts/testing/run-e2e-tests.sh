#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
temporary_directory=""

available_port() {
    python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

frontend_port=${FRONTEND_PORT:-$(available_port)}
api_port=${API_PORT:-$(available_port)}
if [ "$frontend_port" = "$api_port" ]; then
    api_port=$(available_port)
fi

if [ -n "${DATABASE_URL:-}" ]; then
    database_path=$DATABASE_URL
else
    temporary_directory=$(mktemp -d /tmp/rss-feeder-e2e.XXXXXX)
    database_path="$temporary_directory/data.db"
fi

cleanup() {
    if [ -n "${api_pid:-}" ]; then
        kill "$api_pid" 2>/dev/null || true
    fi
    if [ -n "${frontend_pid:-}" ]; then
        kill "$frontend_pid" 2>/dev/null || true
    fi
    if [ -n "$temporary_directory" ]; then
        rm -rf "$temporary_directory"
    fi
}

trap cleanup EXIT INT TERM

wait_for_url() {
    url=$1
    process_id=$2
    attempts=${3:-30}

    for i in $(seq 1 "$attempts"); do
        if curl -fsS "$url" >/dev/null; then
            return 0
        fi
        if ! kill -0 "$process_id" 2>/dev/null; then
            echo "Process $process_id stopped while waiting for $url" >&2
            return 1
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
wait_for_url "http://127.0.0.1:$api_port/health" "$api_pid"
start_frontend_server

wait_for_url "http://127.0.0.1:$api_port/health" "$api_pid"
wait_for_url "http://127.0.0.1:$frontend_port" "$frontend_pid"

PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
PLAYWRIGHT_FRONTEND_BASE_URL="http://127.0.0.1:$frontend_port" \
bunx playwright test "$@"
