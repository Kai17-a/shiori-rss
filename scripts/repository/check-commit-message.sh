#!/bin/sh
set -eu

commit_message_file=$1
subject=$(sed -n '1p' "$commit_message_file")
pattern='^(feat|fix|docs|test|refactor|chore|revert)(\([a-z0-9-]+\))?: .+'

if printf '%s\n' "$subject" | grep -Eq "$pattern"; then
    exit 0
fi

printf '%s\n' "Commit message must follow Conventional Commits: type(scope): subject" >&2
exit 1
