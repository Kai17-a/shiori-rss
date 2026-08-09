-- migrate:up
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
);

INSERT INTO article_search (
  source_type, article_id, source_id, source_title, title, summary, url, published, created_at
)
SELECT
  'rss', articles.id, feeds.id, feeds.title, articles.title, articles.summary,
  articles.url, articles.published, articles.created_at
FROM rss_feed_articles AS articles
JOIN rss_feeds AS feeds ON feeds.id = articles.feed_id;

INSERT INTO article_search (
  source_type, article_id, source_id, source_title, title, summary, url, published, created_at
)
SELECT
  'custom', articles.id, sites.id, sites.title, articles.title, articles.summary,
  articles.url, articles.published, articles.created_at
FROM news_site_articles AS articles
JOIN news_sites AS sites ON sites.id = articles.site_id;

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

-- migrate:down
DROP TRIGGER IF EXISTS article_search_custom_source_title;
DROP TRIGGER IF EXISTS article_search_rss_source_title;
DROP TRIGGER IF EXISTS article_search_custom_delete;
DROP TRIGGER IF EXISTS article_search_custom_update;
DROP TRIGGER IF EXISTS article_search_custom_insert;
DROP TRIGGER IF EXISTS article_search_rss_delete;
DROP TRIGGER IF EXISTS article_search_rss_update;
DROP TRIGGER IF EXISTS article_search_rss_insert;
DROP TABLE IF EXISTS article_search;
