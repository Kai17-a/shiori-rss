-- migrate:up
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
CREATE INDEX IF NOT EXISTS idx_news_sites_title_id ON news_sites(title, id);

CREATE TABLE IF NOT EXISTS news_site_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  published DATETIME,
  webhook_notified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_news_site_articles_site_url_unique
  ON news_site_articles(site_id, url);
CREATE INDEX IF NOT EXISTS idx_news_site_articles_site_published_id
  ON news_site_articles(site_id, published, id);
CREATE INDEX IF NOT EXISTS idx_news_site_articles_pending_notification
  ON news_site_articles(site_id, webhook_notified, id);

CREATE TABLE IF NOT EXISTS news_site_webhooks (
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (site_id, webhook_id)
);

-- migrate:down
DROP TABLE IF EXISTS news_site_webhooks;
DROP TABLE IF EXISTS news_site_articles;
DROP TABLE IF EXISTS news_sites;
