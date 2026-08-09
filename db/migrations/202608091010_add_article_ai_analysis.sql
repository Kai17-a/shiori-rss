-- migrate:up
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
);

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

-- migrate:down
DROP TRIGGER IF EXISTS article_ai_analysis_custom_delete;
DROP TRIGGER IF EXISTS article_ai_analysis_rss_delete;
DROP TRIGGER IF EXISTS article_ai_search_delete;
DROP TRIGGER IF EXISTS article_ai_search_update;
DROP TRIGGER IF EXISTS article_ai_search_insert;
DROP TABLE IF EXISTS article_ai_search;
DROP INDEX IF EXISTS idx_article_ai_analysis_usage_created;
DROP TABLE IF EXISTS article_ai_analysis_usage;
DROP INDEX IF EXISTS idx_article_ai_analyses_analyzed_tokens;
DROP INDEX IF EXISTS idx_article_ai_analyses_status_updated;
DROP TABLE IF EXISTS article_ai_analyses;
