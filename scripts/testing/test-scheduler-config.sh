#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
renderer="$repo_root/scripts/container/render-scheduler.sh"

news_sites_job="cd /app && python -m api.scripts.run_news_sites"

default_schedule=$(env -u RSS_CRON_SCHEDULE sh "$renderer")
expected_default=$(printf '0 * * * * shiori-feed-batch\n0 * * * * %s' "$news_sites_job")
if [ "$default_schedule" != "$expected_default" ]; then
  echo "Unexpected default RSS schedule: $default_schedule" >&2
  exit 1
fi

active_hours_schedule=$(RSS_CRON_SCHEDULE="0 6-22 * * *" sh "$renderer")
expected_active=$(printf '0 6-22 * * * shiori-feed-batch\n0 6-22 * * * %s' "$news_sites_job")
if [ "$active_hours_schedule" != "$expected_active" ]; then
  echo "Unexpected active-hours RSS schedule: $active_hours_schedule" >&2
  exit 1
fi

if RSS_CRON_SCHEDULE="" sh "$renderer" >/dev/null 2>&1; then
  echo "Empty RSS_CRON_SCHEDULE should fail" >&2
  exit 1
fi

newline_schedule=$(printf '0 * * * *\n* * * * *')
if RSS_CRON_SCHEDULE="$newline_schedule" sh "$renderer" >/dev/null 2>&1; then
  echo "Multiline RSS_CRON_SCHEDULE should fail" >&2
  exit 1
fi
