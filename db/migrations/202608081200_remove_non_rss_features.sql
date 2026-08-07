-- migrate:up
DROP TABLE IF EXISTS news_site_webhooks;
DROP TABLE IF EXISTS news_site_articles;
DROP TABLE IF EXISTS news_sites;
DROP TABLE IF EXISTS bookmark_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS bookmarks;
DROP TABLE IF EXISTS folders;

-- migrate:down
CREATE TABLE IF NOT EXISTS folders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bookmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
  is_favorite INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_unique ON bookmarks(url);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS bookmark_tags (
  bookmark_id INTEGER NOT NULL REFERENCES bookmarks(id) ON DELETE CASCADE,
  tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (bookmark_id, tag_id)
);

CREATE TABLE IF NOT EXISTS news_sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  scrape_config TEXT NOT NULL,
  notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_sites_url_unique ON news_sites(url);

CREATE TABLE IF NOT EXISTS news_site_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  published DATETIME,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_site_webhooks (
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (site_id, webhook_id)
);
