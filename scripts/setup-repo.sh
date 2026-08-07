#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd)

git -C "$repo_root" config --local core.hooksPath .githooks

printf '%s\n' "Configured local Git hooks path to .githooks"
