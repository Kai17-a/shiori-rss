#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)

sh "$repo_root/scripts/testing/test-scheduler-config.sh"

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

# Keep browser tests isolated from the development database and use the same
# clean-database startup path as `mise run e2e`.
sh "$repo_root/scripts/testing/run-e2e-tests.sh"
