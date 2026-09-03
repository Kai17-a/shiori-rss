-- migrate:up
-- Tracks which provider/base URL produced the stored embedding, alongside
-- the existing embedding_model column. Needed because a user can now point
-- the embedding model at a different provider than the chat model (see
-- LLMConfig.embedding_use_separate_provider): two backends can serve a
-- model under the identical name but produce incompatible vectors, so the
-- staleness check that decides whether to re-embed an article must compare
-- the whole connection identity, not just the model name.
ALTER TABLE article_ai_analyses ADD COLUMN embedding_provider TEXT;
ALTER TABLE article_ai_analyses ADD COLUMN embedding_base_url TEXT;

-- migrate:down
ALTER TABLE article_ai_analyses DROP COLUMN embedding_base_url;
ALTER TABLE article_ai_analyses DROP COLUMN embedding_provider;
