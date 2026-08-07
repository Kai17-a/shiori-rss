-- migrate:up
ALTER TABLE webhook_endpoints
  ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1;

-- migrate:down
ALTER TABLE webhook_endpoints
  DROP COLUMN enabled;
