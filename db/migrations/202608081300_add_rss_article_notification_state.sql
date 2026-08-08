-- migrate:up
ALTER TABLE rss_feed_articles ADD COLUMN summary TEXT;
ALTER TABLE rss_feed_articles
  ADD COLUMN webhook_notified INTEGER NOT NULL DEFAULT 0;

-- Rows created before this migration represented successfully delivered articles.
UPDATE rss_feed_articles SET webhook_notified = 1;

CREATE INDEX IF NOT EXISTS idx_rss_feed_articles_pending_notification
  ON rss_feed_articles(feed_id, webhook_notified, id);

-- migrate:down
DROP INDEX IF EXISTS idx_rss_feed_articles_pending_notification;
ALTER TABLE rss_feed_articles DROP COLUMN webhook_notified;
ALTER TABLE rss_feed_articles DROP COLUMN summary;
