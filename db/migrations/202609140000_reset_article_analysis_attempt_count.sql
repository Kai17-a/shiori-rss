-- migrate:up
UPDATE article_ai_analyses
SET attempt_count = CASE
  WHEN status = 'failed' THEN 1
  WHEN status = 'completed' THEN 0
  ELSE attempt_count
END;

-- migrate:down
-- The legacy cumulative attempt counts cannot be reconstructed after normalization.
SELECT 1;
