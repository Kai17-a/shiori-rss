-- migrate:up
-- The article_ai_embeddings vec0 virtual table is NOT created here: dbmate's
-- sqlite driver has no sqlite-vec extension loaded, so a `CREATE VIRTUAL
-- TABLE ... USING vec0(...)` statement fails migration application with
-- "no such module: vec0". It is instead created idempotently by
-- api.database.ensure_vector_search_schema(), which loads the extension
-- before running the DDL. See that function for the exact table definition.
ALTER TABLE article_ai_analyses ADD COLUMN embedding BLOB;
ALTER TABLE article_ai_analyses ADD COLUMN embedding_content_hash TEXT;
ALTER TABLE article_ai_analyses ADD COLUMN embedding_model TEXT;
ALTER TABLE article_ai_analyses ADD COLUMN embedding_dim INTEGER;
ALTER TABLE article_ai_analyses ADD COLUMN embedding_updated_at TEXT;

-- migrate:down
-- article_ai_embeddings (if created) is dropped the same way it's created:
-- via a connection with the vec extension loaded, not by dbmate. Running
-- this down migration alone leaves it in place if it exists.
ALTER TABLE article_ai_analyses DROP COLUMN embedding_updated_at;
ALTER TABLE article_ai_analyses DROP COLUMN embedding_dim;
ALTER TABLE article_ai_analyses DROP COLUMN embedding_model;
ALTER TABLE article_ai_analyses DROP COLUMN embedding_content_hash;
ALTER TABLE article_ai_analyses DROP COLUMN embedding;
