#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
script_dir=$(cd "$(dirname "$0")" && pwd)

frontend_port=${FRONTEND_PORT:-3001}
api_port=${API_PORT:-8001}
database_path=${DATABASE_URL:-/tmp/bookmark-manager-playwright-screenshots/data.db}
artifact_dir=${PLAYWRIGHT_SCREENSHOT_DIR:-"$repo_root/docs/app-images"}

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
    attempts=${2:-45}

    for i in $(seq 1 "$attempts"); do
        if curl -fsS "$url" >/dev/null; then
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for $url" >&2
    return 1
}

start_api_server() {
    mkdir -p "$(dirname "$database_path")"
    cd "$repo_root"
    UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/uv-cache} mise x -- dbmate -u "sqlite:$database_path" up
    UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/uv-cache} \
    DATABASE_URL="$database_path" \
        uv run --directory "$repo_root/api" uvicorn api.main:app --app-dir "$repo_root" --host 127.0.0.1 --port "$api_port" > /tmp/bookmark-manager-api-playwright.log 2>&1 &
    api_pid=$!
}

start_frontend_server() {
    cd "$repo_root/frontend"
    PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
        bunx nuxt dev --host 0.0.0.0 --port "$frontend_port" --strictPort > /tmp/bookmark-manager-frontend-playwright.log 2>&1 &
    frontend_pid=$!
}

if [ ! -d "$HOME/.cache/ms-playwright" ] || [ -z "$(find "$HOME/.cache/ms-playwright" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]; then
    cd "$repo_root/frontend"
    bunx playwright install --with-deps chromium
fi

mkdir -p "$artifact_dir"

start_api_server
wait_for_url "http://127.0.0.1:$api_port/health"
start_frontend_server

wait_for_url "http://127.0.0.1:$api_port/health"
wait_for_url "http://127.0.0.1:$frontend_port"

PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$api_port" \
PLAYWRIGHT_FRONTEND_BASE_URL="http://127.0.0.1:$frontend_port" \
PLAYWRIGHT_SCREENSHOT_DIR="$artifact_dir" \
UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/uv-cache} \
sh -c "cd '$repo_root/frontend' && bun '$script_dir/capture-playwright-screenshots.mjs' \"\$@\"" sh "$@"
