CREATE TABLE "schema_migrations" (version varchar(128) primary key);
CREATE TABLE rss_feeds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
, notify_webhook_enabled INTEGER NOT NULL DEFAULT 1, icon_url TEXT, icon_data BLOB, icon_media_type TEXT);
CREATE UNIQUE INDEX idx_rss_feeds_url_unique ON rss_feeds(url);
CREATE TABLE rss_feed_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
, published DATETIME, summary TEXT, webhook_notified INTEGER NOT NULL DEFAULT 0);
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
CREATE INDEX idx_rss_feed_articles_pending_notification
  ON rss_feed_articles(feed_id, webhook_notified, id);
CREATE TABLE news_sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  scrape_config TEXT NOT NULL,
  notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
, icon_url TEXT, icon_data BLOB, icon_media_type TEXT);
CREATE UNIQUE INDEX idx_news_sites_url_unique ON news_sites(url);
CREATE INDEX idx_news_sites_title_id ON news_sites(title, id);
CREATE TABLE news_site_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  published DATETIME,
  webhook_notified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_news_site_articles_site_url_unique
  ON news_site_articles(site_id, url);
CREATE INDEX idx_news_site_articles_site_published_id
  ON news_site_articles(site_id, published, id);
CREATE INDEX idx_news_site_articles_pending_notification
  ON news_site_articles(site_id, webhook_notified, id);
CREATE TABLE news_site_webhooks (
  site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
  webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  PRIMARY KEY (site_id, webhook_id)
);
CREATE VIRTUAL TABLE article_search USING fts5(
  source_type UNINDEXED,
  article_id UNINDEXED,
  source_id UNINDEXED,
  source_title,
  title,
  summary,
  url UNINDEXED,
  published UNINDEXED,
  created_at UNINDEXED,
  tokenize = 'trigram'
)
/* article_search(source_type,article_id,source_id,source_title,title,summary,url,published,created_at) */;
CREATE TABLE 'article_search_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'article_search_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE 'article_search_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4, c5, c6, c7, c8);
CREATE TABLE 'article_search_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE 'article_search_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TRIGGER article_search_rss_insert AFTER INSERT ON rss_feed_articles BEGIN
  INSERT INTO article_search (
    source_type, article_id, source_id, source_title, title, summary, url, published, created_at
  )
  SELECT 'rss', new.id, feeds.id, feeds.title, new.title, new.summary, new.url,
         new.published, new.created_at
  FROM rss_feeds AS feeds WHERE feeds.id = new.feed_id;
END;
CREATE TRIGGER article_search_rss_update AFTER UPDATE ON rss_feed_articles BEGIN
  DELETE FROM article_search WHERE source_type = 'rss' AND article_id = old.id;
  INSERT INTO article_search (
    source_type, article_id, source_id, source_title, title, summary, url, published, created_at
  )
  SELECT 'rss', new.id, feeds.id, feeds.title, new.title, new.summary, new.url,
         new.published, new.created_at
  FROM rss_feeds AS feeds WHERE feeds.id = new.feed_id;
END;
CREATE TRIGGER article_search_rss_delete AFTER DELETE ON rss_feed_articles BEGIN
  DELETE FROM article_search WHERE source_type = 'rss' AND article_id = old.id;
END;
CREATE TRIGGER article_search_custom_insert AFTER INSERT ON news_site_articles BEGIN
  INSERT INTO article_search (
    source_type, article_id, source_id, source_title, title, summary, url, published, created_at
  )
  SELECT 'custom', new.id, sites.id, sites.title, new.title, new.summary, new.url,
         new.published, new.created_at
  FROM news_sites AS sites WHERE sites.id = new.site_id;
END;
CREATE TRIGGER article_search_custom_update AFTER UPDATE ON news_site_articles BEGIN
  DELETE FROM article_search WHERE source_type = 'custom' AND article_id = old.id;
  INSERT INTO article_search (
    source_type, article_id, source_id, source_title, title, summary, url, published, created_at
  )
  SELECT 'custom', new.id, sites.id, sites.title, new.title, new.summary, new.url,
         new.published, new.created_at
  FROM news_sites AS sites WHERE sites.id = new.site_id;
END;
CREATE TRIGGER article_search_custom_delete AFTER DELETE ON news_site_articles BEGIN
  DELETE FROM article_search WHERE source_type = 'custom' AND article_id = old.id;
END;
CREATE TRIGGER article_search_rss_source_title AFTER UPDATE OF title ON rss_feeds BEGIN
  UPDATE article_search SET source_title = new.title
  WHERE source_type = 'rss' AND source_id = new.id;
END;
CREATE TRIGGER article_search_custom_source_title AFTER UPDATE OF title ON news_sites BEGIN
  UPDATE article_search SET source_title = new.title
  WHERE source_type = 'custom' AND source_id = new.id;
END;
CREATE TABLE article_ai_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'custom')),
  article_id INTEGER NOT NULL,
  content_hash TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  ai_summary TEXT,
  key_points_json TEXT NOT NULL DEFAULT '[]',
  topics_json TEXT NOT NULL DEFAULT '[]',
  keywords_json TEXT NOT NULL DEFAULT '[]',
  entities_json TEXT NOT NULL DEFAULT '[]',
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('completed', 'failed')),
  error_message TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 1,
  analyzed_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (source_type, article_id)
);
CREATE INDEX idx_article_ai_analyses_status_updated
  ON article_ai_analyses(status, updated_at, source_type, article_id);
CREATE INDEX idx_article_ai_analyses_analyzed_tokens
  ON article_ai_analyses(analyzed_at, input_tokens, output_tokens);
CREATE TABLE article_ai_analysis_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'custom')),
  article_id INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  successful INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_article_ai_analysis_usage_created
  ON article_ai_analysis_usage(created_at, input_tokens, output_tokens);
CREATE VIRTUAL TABLE article_ai_search USING fts5(
  source_type UNINDEXED,
  article_id UNINDEXED,
  ai_summary,
  key_points,
  topics,
  keywords,
  entities,
  tokenize = 'trigram'
)
/* article_ai_search(source_type,article_id,ai_summary,key_points,topics,keywords,entities) */;
CREATE TABLE 'article_ai_search_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE 'article_ai_search_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE 'article_ai_search_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4, c5, c6);
CREATE TABLE 'article_ai_search_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE 'article_ai_search_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TRIGGER article_ai_search_insert AFTER INSERT ON article_ai_analyses
WHEN new.status = 'completed' BEGIN
  INSERT INTO article_ai_search (
    source_type, article_id, ai_summary, key_points, topics, keywords, entities
  ) VALUES (
    new.source_type, new.article_id, new.ai_summary, new.key_points_json,
    new.topics_json, new.keywords_json, new.entities_json
  );
END;
CREATE TRIGGER article_ai_search_update AFTER UPDATE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search
  WHERE source_type = old.source_type AND article_id = old.article_id;
  INSERT INTO article_ai_search (
    source_type, article_id, ai_summary, key_points, topics, keywords, entities
  )
  SELECT new.source_type, new.article_id, new.ai_summary, new.key_points_json,
         new.topics_json, new.keywords_json, new.entities_json
  WHERE new.status = 'completed';
END;
CREATE TRIGGER article_ai_search_delete AFTER DELETE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search
  WHERE source_type = old.source_type AND article_id = old.article_id;
END;
CREATE TRIGGER article_ai_analysis_rss_delete AFTER DELETE ON rss_feed_articles BEGIN
  DELETE FROM article_ai_analyses
  WHERE source_type = 'rss' AND article_id = old.id;
END;
CREATE TRIGGER article_ai_analysis_custom_delete AFTER DELETE ON news_site_articles BEGIN
  DELETE FROM article_ai_analyses
  WHERE source_type = 'custom' AND article_id = old.id;
END;
CREATE TABLE github_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    repository TEXT NOT NULL,
    repository_url TEXT NOT NULL,
    latest_release_name TEXT NOT NULL,
    latest_release_tag TEXT NOT NULL,
    latest_release_url TEXT NOT NULL,
    latest_release_body TEXT,
    latest_release_published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
, latest_notified_release_tag TEXT);
CREATE UNIQUE INDEX idx_github_repositories_url_unique
    ON github_repositories(repository_url);
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
  ('202608081200'),
  ('202608081300'),
  ('202608081400'),
  ('202608090945'),
  ('202608091010'),
  ('202608101000'),
  ('202608121631'),
  ('202608121710');
