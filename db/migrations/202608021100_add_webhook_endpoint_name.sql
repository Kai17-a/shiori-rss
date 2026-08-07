-- migrate:up
ALTER TABLE webhook_endpoints
  ADD COLUMN name TEXT NOT NULL DEFAULT '';

UPDATE webhook_endpoints SET name = url WHERE name = '';

-- migrate:down
ALTER TABLE webhook_endpoints
  DROP COLUMN name;
