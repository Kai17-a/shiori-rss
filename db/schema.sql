CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE rss_feeds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
, notify_webhook_enabled INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX idx_rss_feeds_url_unique ON rss_feeds(url);
CREATE TABLE rss_feed_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
, published DATETIME);
CREATE UNIQUE INDEX idx_rss_feed_articles_feed_url_unique
  ON rss_feed_articles(feed_id, url);
CREATE TABLE app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
, rss_periodic_execution_enabled INTEGER NOT NULL DEFAULT 0);
CREATE INDEX idx_rss_feeds_title_id
  ON rss_feeds(title ASC, id ASC);
CREATE INDEX idx_rss_feed_articles_feed_published_id
  ON rss_feed_articles(feed_id, published DESC, id DESC);
CREATE INDEX idx_rss_feed_articles_feed_published_null_id
  ON rss_feed_articles(feed_id, published IS NULL, published DESC, id DESC);
CREATE TABLE webhook_endpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
, name TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX idx_webhook_endpoints_url_unique
  ON webhook_endpoints(url);
CREATE TABLE rss_feed_webhooks (
  feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (feed_id, webhook_id)
);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('010'),
  ('011'),
  ('012'),
  ('013'),
  ('202604251114'),
  ('202604251124'),
  ('202608021000'),
  ('202608021100'),
  ('202608021200'),
  ('202608021300'),
  ('202608041600'),
  ('202608081200');
