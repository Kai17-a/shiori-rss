#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)

cleanup() {
    if [ -n "${api_pid:-}" ]; then
        kill "$api_pid" 2>/dev/null || true
    fi
    if [ -n "${frontend_pid:-}" ]; then
        kill "$frontend_pid" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

sh "$repo_root/scripts/testing/test-scheduler-config.sh"

start_api_server() {
    uv run --directory "$repo_root/api" uvicorn api.main:app --app-dir "$repo_root" --host 127.0.0.1 --port 8000 > /tmp/rss-feeder-api.log 2>&1 &
    api_pid=$!
}

start_frontend_server() {
    cd "$repo_root/frontend"
    bunx nuxt dev --host 0.0.0.0 --port 3000 > /tmp/rss-feeder-frontend.log 2>&1 &
    frontend_pid=$!
}

cd "$repo_root/api"
uv run ruff check .
uv run pyright
uv run pytest -q

cd "$repo_root/batch"
cargo fmt --check
cargo check
cargo test

cd "$repo_root/frontend"
bun run typecheck
bun run test
bun run generate

# This is idempotent and installs the exact browser revision required by the
# current Playwright package, even when an older revision is already cached.
cd "$repo_root/frontend"
bunx playwright install chromium

start_api_server
start_frontend_server

for url in http://127.0.0.1:8000/health http://127.0.0.1:3000; do
    for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
        if curl -fsS "$url" >/dev/null; then
            break
        fi
        sleep 2
    done
done

cd "$repo_root/frontend"
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000 \
PLAYWRIGHT_FRONTEND_BASE_URL=http://127.0.0.1:3000 \
bunx playwright test
