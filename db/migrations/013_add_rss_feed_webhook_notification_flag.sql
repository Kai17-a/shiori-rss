-- migrate:up
ALTER TABLE rss_feeds
  ADD COLUMN notify_webhook_enabled INTEGER NOT NULL DEFAULT 1;

-- migrate:down
ALTER TABLE rss_feeds DROP COLUMN notify_webhook_enabled;
