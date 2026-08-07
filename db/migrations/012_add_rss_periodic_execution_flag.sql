-- migrate:up
ALTER TABLE app_settings
  ADD COLUMN rss_periodic_execution_enabled INTEGER NOT NULL DEFAULT 0;

-- migrate:down
ALTER TABLE app_settings DROP COLUMN rss_periodic_execution_enabled;
