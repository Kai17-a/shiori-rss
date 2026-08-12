use rusqlite::Connection;
use shiori_feed_batch::github::run_github_release_batch_with_base;
use wiremock::{
    Mock, MockServer, ResponseTemplate,
    matchers::{method, path},
};

fn database(api_server: &MockServer) -> Connection {
    let conn = Connection::open_in_memory().expect("open database");
    conn.execute_batch(
        r#"
        CREATE TABLE github_repositories (
            id INTEGER PRIMARY KEY, owner TEXT NOT NULL, repository TEXT NOT NULL,
            repository_url TEXT NOT NULL, latest_release_name TEXT NOT NULL,
            latest_release_tag TEXT NOT NULL, latest_release_url TEXT NOT NULL,
            latest_release_body TEXT, latest_release_published_at TEXT NOT NULL,
            latest_notified_release_tag TEXT, fetched_at TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE webhook_endpoints (
            id INTEGER PRIMARY KEY, url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        "#,
    )
    .expect("create schema");
    conn.execute(
        "INSERT INTO github_repositories VALUES (1, 'acme', 'tool', 'https://github.com/acme/tool', 'v1', 'v1', 'https://github.com/acme/tool/releases/tag/v1', NULL, '2026-01-01T00:00:00Z', 'v1', '', '', '')",
        [],
    ).expect("insert repository");
    conn.execute(
        "INSERT INTO webhook_endpoints VALUES (1, ?, 1)",
        [format!("{}/hook", api_server.uri())],
    )
    .expect("insert webhook");
    conn
}

#[tokio::test]
async fn notifies_a_new_release_only_once() {
    let server = MockServer::start().await;
    let conn = database(&server);
    Mock::given(method("GET")).and(path("/repos/acme/tool/releases/latest"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "name": "Version 2", "tag_name": "v2", "html_url": "https://github.com/acme/tool/releases/tag/v2",
            "body": "Changes", "published_at": "2026-08-12T00:00:00Z"
        }))).mount(&server).await;
    Mock::given(method("POST"))
        .and(path("/hook"))
        .respond_with(ResponseTemplate::new(204))
        .mount(&server)
        .await;

    run_github_release_batch_with_base(&conn, &server.uri())
        .await
        .expect("first run");
    run_github_release_batch_with_base(&conn, &server.uri())
        .await
        .expect("second run");

    let notified: String = conn
        .query_row(
            "SELECT latest_notified_release_tag FROM github_repositories",
            [],
            |row| row.get(0),
        )
        .expect("read tag");
    assert_eq!(notified, "v2");
    let requests = server.received_requests().await.expect("requests");
    assert_eq!(
        requests
            .iter()
            .filter(|request| request.method.as_str() == "POST")
            .count(),
        1
    );
    assert!(
        String::from_utf8_lossy(
            &requests
                .iter()
                .find(|request| request.method.as_str() == "POST")
                .expect("webhook request")
                .body
        )
        .contains("Version 2")
    );
}
