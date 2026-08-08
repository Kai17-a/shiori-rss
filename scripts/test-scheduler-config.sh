#!/bin/sh
set -eu

repo_root=$(cd "$(dirname "$0")/.." && pwd)
renderer="$repo_root/render-scheduler.sh"

default_schedule=$(env -u RSS_CRON_SCHEDULE sh "$renderer")
if [ "$default_schedule" != "0 * * * * shiori-feed-batch" ]; then
  echo "Unexpected default RSS schedule: $default_schedule" >&2
  exit 1
fi

active_hours_schedule=$(RSS_CRON_SCHEDULE="0 6-22 * * *" sh "$renderer")
if [ "$active_hours_schedule" != "0 6-22 * * * shiori-feed-batch" ]; then
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
