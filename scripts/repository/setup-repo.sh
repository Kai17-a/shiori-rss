#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)

cd "$repo_root"

# Migrate repositories that used the former custom .githooks directory.
git config --local --unset-all core.hooksPath 2>/dev/null || true
mise exec -- prek install -f

printf '%s\n' "Installed prek hooks for pre-commit, commit-msg, and pre-push"
