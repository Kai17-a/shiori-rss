-- migrate:up
CREATE TABLE IF NOT EXISTS webhook_endpoints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_endpoints_url_unique
  ON webhook_endpoints(url);

INSERT INTO webhook_endpoints (url)
SELECT value FROM app_settings
WHERE key = 'default_webhook_url' AND value != '';

-- migrate:down
DELETE FROM app_settings WHERE key = 'default_webhook_url';

INSERT INTO app_settings (key, value)
SELECT 'default_webhook_url', url FROM webhook_endpoints
ORDER BY id ASC LIMIT 1;

DROP TABLE IF EXISTS webhook_endpoints;
