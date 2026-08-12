-- migrate:up
CREATE TABLE github_repository_webhooks (
    repository_id INTEGER NOT NULL REFERENCES github_repositories(id) ON DELETE CASCADE,
    webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    PRIMARY KEY (repository_id, webhook_id)
);

INSERT INTO github_repository_webhooks (repository_id, webhook_id)
SELECT repository.id, webhook.id
FROM github_repositories repository
CROSS JOIN webhook_endpoints webhook;

-- migrate:down
DROP TABLE github_repository_webhooks;
