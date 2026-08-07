-- migrate:up
CREATE INDEX IF NOT EXISTS idx_rss_feed_articles_feed_published_null_id
  ON rss_feed_articles(feed_id, published IS NULL, published DESC, id DESC);

-- migrate:down
DROP INDEX IF EXISTS idx_rss_feed_articles_feed_published_null_id;
