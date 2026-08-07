-- migrate:up
CREATE TABLE IF NOT EXISTS rss_feed_webhooks (
  feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (feed_id, webhook_id)
);

-- migrate:down
DROP TABLE IF EXISTS rss_feed_webhooks;
