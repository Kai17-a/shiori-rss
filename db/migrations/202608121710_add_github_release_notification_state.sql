-- migrate:up
ALTER TABLE github_repositories ADD COLUMN latest_notified_release_tag TEXT;

UPDATE github_repositories
SET latest_notified_release_tag = latest_release_tag;

-- migrate:down
ALTER TABLE github_repositories DROP COLUMN latest_notified_release_tag;
