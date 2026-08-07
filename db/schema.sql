CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE folders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE bookmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
  is_favorite INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_bookmarks_url_unique ON bookmarks(url);
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
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);
CREATE TABLE bookmark_tags (
  bookmark_id INTEGER NOT NULL REFERENCES bookmarks(id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (bookmark_id, tag_id)
);
CREATE INDEX idx_bookmarks_created_id
  ON bookmarks(created_at DESC, id DESC);
CREATE INDEX idx_bookmarks_folder_created_id
  ON bookmarks(folder_id, created_at DESC, id DESC);
CREATE INDEX idx_bookmarks_favorite_created_id
  ON bookmarks(is_favorite, created_at DESC, id DESC);
CREATE INDEX idx_bookmark_tags_tag_bookmark
  ON bookmark_tags(tag_id, bookmark_id);
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
CREATE TABLE news_sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  scrape_config TEXT NOT NULL,
  notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_news_sites_url_unique ON news_sites(url);
CREATE INDEX idx_news_sites_title_id ON news_sites(title, id);
CREATE TABLE news_site_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  published DATETIME
);
CREATE UNIQUE INDEX idx_news_site_articles_site_url_unique
  ON news_site_articles(site_id, url);
CREATE INDEX idx_news_site_articles_site_published_id
  ON news_site_articles(site_id, published, id);
CREATE TABLE news_site_webhooks (
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (site_id, webhook_id)
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
  ('202608041600');
