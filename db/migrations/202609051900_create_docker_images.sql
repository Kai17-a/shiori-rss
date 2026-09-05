-- migrate:up
CREATE TABLE docker_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registry TEXT NOT NULL,
    repository TEXT NOT NULL,
    tag TEXT NOT NULL DEFAULT 'latest',
    display_name TEXT NOT NULL,
    latest_digest TEXT NOT NULL,
    latest_notified_digest TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE UNIQUE INDEX idx_docker_images_reference_unique ON docker_images(registry, repository, tag);

CREATE TABLE docker_image_webhooks (
    image_id INTEGER NOT NULL REFERENCES docker_images(id) ON DELETE CASCADE,
    webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    PRIMARY KEY (image_id, webhook_id)
);

-- migrate:down
DROP TABLE docker_image_webhooks;
DROP TABLE docker_images;
