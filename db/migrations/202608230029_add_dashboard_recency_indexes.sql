-- migrate:up
ALTER TABLE rss_feed_articles ADD COLUMN effective_published_at TEXT
  GENERATED ALWAYS AS (datetime(coalesce(published, created_at))) VIRTUAL;
CREATE INDEX IF NOT EXISTS idx_rss_feed_articles_effective_published_at
  ON rss_feed_articles(effective_published_at);
CREATE INDEX IF NOT EXISTS idx_rss_feed_articles_pending_notification_only
  ON rss_feed_articles(id) WHERE webhook_notified = 0;

ALTER TABLE news_site_articles ADD COLUMN effective_published_at TEXT
  GENERATED ALWAYS AS (datetime(coalesce(published, created_at))) VIRTUAL;
CREATE INDEX IF NOT EXISTS idx_news_site_articles_effective_published_at
  ON news_site_articles(effective_published_at);
CREATE INDEX IF NOT EXISTS idx_news_site_articles_pending_notification_only
  ON news_site_articles(id) WHERE webhook_notified = 0;

-- migrate:down
DROP INDEX IF EXISTS idx_news_site_articles_pending_notification_only;
DROP INDEX IF EXISTS idx_news_site_articles_effective_published_at;
ALTER TABLE news_site_articles DROP COLUMN effective_published_at;
DROP INDEX IF EXISTS idx_rss_feed_articles_pending_notification_only;
DROP INDEX IF EXISTS idx_rss_feed_articles_effective_published_at;
ALTER TABLE rss_feed_articles DROP COLUMN effective_published_at;
