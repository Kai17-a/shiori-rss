-- migrate:up
ALTER TABLE article_ai_analyses
ADD COLUMN search_aliases_json TEXT NOT NULL DEFAULT '[]';

DROP TRIGGER article_ai_search_insert;
DROP TRIGGER article_ai_search_update;
DROP TRIGGER article_ai_search_delete;
DROP TABLE article_ai_search;

CREATE VIRTUAL TABLE article_ai_search USING fts5(
  source_type UNINDEXED,
  article_id UNINDEXED,
  ai_summary,
  key_points,
  topics,
  keywords,
  entities,
  search_aliases,
  tokenize = 'trigram'
);

INSERT INTO article_ai_search (
  source_type, article_id, ai_summary, key_points, topics, keywords, entities, search_aliases
)
SELECT source_type, article_id, ai_summary, key_points_json, topics_json,
       keywords_json, entities_json, search_aliases_json
FROM article_ai_analyses WHERE status = 'completed';

CREATE TRIGGER article_ai_search_insert AFTER INSERT ON article_ai_analyses
WHEN new.status = 'completed' BEGIN
  INSERT INTO article_ai_search (
    source_type, article_id, ai_summary, key_points, topics, keywords, entities, search_aliases
  ) VALUES (
    new.source_type, new.article_id, new.ai_summary, new.key_points_json,
    new.topics_json, new.keywords_json, new.entities_json, new.search_aliases_json
  );
END;

CREATE TRIGGER article_ai_search_update AFTER UPDATE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search
  WHERE source_type = old.source_type AND article_id = old.article_id;
  INSERT INTO article_ai_search (
    source_type, article_id, ai_summary, key_points, topics, keywords, entities, search_aliases
  )
  SELECT new.source_type, new.article_id, new.ai_summary, new.key_points_json,
         new.topics_json, new.keywords_json, new.entities_json, new.search_aliases_json
  WHERE new.status = 'completed';
END;

CREATE TRIGGER article_ai_search_delete AFTER DELETE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search
  WHERE source_type = old.source_type AND article_id = old.article_id;
END;

-- migrate:down
DROP TRIGGER article_ai_search_insert;
DROP TRIGGER article_ai_search_update;
DROP TRIGGER article_ai_search_delete;
DROP TABLE article_ai_search;
ALTER TABLE article_ai_analyses DROP COLUMN search_aliases_json;

CREATE VIRTUAL TABLE article_ai_search USING fts5(
  source_type UNINDEXED, article_id UNINDEXED, ai_summary, key_points,
  topics, keywords, entities, tokenize = 'trigram'
);
INSERT INTO article_ai_search
SELECT source_type, article_id, ai_summary, key_points_json, topics_json,
       keywords_json, entities_json FROM article_ai_analyses WHERE status = 'completed';
CREATE TRIGGER article_ai_search_insert AFTER INSERT ON article_ai_analyses WHEN new.status = 'completed' BEGIN
  INSERT INTO article_ai_search VALUES (new.source_type, new.article_id, new.ai_summary, new.key_points_json, new.topics_json, new.keywords_json, new.entities_json);
END;
CREATE TRIGGER article_ai_search_update AFTER UPDATE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search WHERE source_type = old.source_type AND article_id = old.article_id;
  INSERT INTO article_ai_search SELECT new.source_type, new.article_id, new.ai_summary, new.key_points_json, new.topics_json, new.keywords_json, new.entities_json WHERE new.status = 'completed';
END;
CREATE TRIGGER article_ai_search_delete AFTER DELETE ON article_ai_analyses BEGIN
  DELETE FROM article_ai_search WHERE source_type = old.source_type AND article_id = old.article_id;
END;
