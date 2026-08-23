"""Cron entrypoint for custom news-site (scraped RSS) periodic checks.

Standard RSS feeds are checked on a schedule by the Rust `shiori-feed-batch`
binary. Custom news sites use LLM-derived CSS selectors (Python-only logic,
see NewsSiteService), so they get their own lightweight entrypoint here
instead, invoked by the same cron schedule
(see scripts/container/render-scheduler.sh).

Run directly against the database, like the Rust batch does, rather than
through the API over HTTP, so this doesn't depend on the API process being
up at the moment cron fires.
"""

import logging

from api.services.news_site_service import NewsSiteService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main() -> None:
    NewsSiteService().execute_due()


if __name__ == "__main__":
    main()
