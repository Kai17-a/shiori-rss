#!/bin/sh
set -eu

schedule=${RSS_CRON_SCHEDULE-"0 * * * *"}

case "$schedule" in
  *'
'*)
    echo "RSS_CRON_SCHEDULE must contain exactly one cron expression" >&2
    exit 1
    ;;
esac

set -f
set -- $schedule
if [ "$#" -eq 0 ]; then
  echo "RSS_CRON_SCHEDULE must not be empty" >&2
  exit 1
fi

printf '%s shiori-keeper-batch\n' "$schedule"
