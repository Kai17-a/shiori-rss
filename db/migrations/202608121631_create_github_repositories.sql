-- migrate:up
CREATE TABLE github_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL,
    repository TEXT NOT NULL,
    repository_url TEXT NOT NULL,
    latest_release_name TEXT NOT NULL,
    latest_release_tag TEXT NOT NULL,
    latest_release_url TEXT NOT NULL,
    latest_release_body TEXT,
    latest_release_published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE UNIQUE INDEX idx_github_repositories_url_unique
    ON github_repositories(repository_url);

-- migrate:down
DROP TABLE github_repositories;
