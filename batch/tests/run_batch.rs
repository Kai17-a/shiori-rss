use rusqlite::Connection;
use shiori_feed_batch::{
    fetch_rss_feeds, fetch_webhook_endpoints, rss_periodic_execution_enabled,
    rss_webhook_notification_enabled, run_batch, webhook_summary_enabled,
};

fn create_in_memory_test_db(enabled: i64) -> Connection {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    conn.execute_batch(
        r#"
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            rss_periodic_execution_enabled INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE webhook_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE rss_feed_webhooks (
            feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
            webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
            PRIMARY KEY (feed_id, webhook_id)
        );
        CREATE TABLE rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE rss_feed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            title TEXT,
            summary TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            published DATETIME,
            webhook_notified INTEGER NOT NULL DEFAULT 0
        );
        "#,
    )
    .expect("create schema");

    conn.execute(
        "INSERT INTO webhook_endpoints (url) VALUES (?)",
        ["https://discord.com/api/webhooks/1/token"],
    )
    .expect("insert webhook endpoint");

    conn.execute(
        "INSERT INTO app_settings (key, value, rss_periodic_execution_enabled) VALUES ('rss_periodic_execution_enabled', ?, ?)",
        (if enabled != 0 { "1" } else { "0" }, enabled),
    )
    .expect("insert settings");

    conn.execute(
        "INSERT INTO rss_feeds (id, url, title, description, notify_webhook_enabled) VALUES (1, ?, ?, ?, 1)",
        (
            "https://example.com/feed.xml",
            "Example Feed",
            Option::<&str>::None,
        ),
    )
    .expect("insert feed");

    conn
}

#[tokio::test]
async fn disabled_rss_periodic_execution_returns_ok_without_fetching() {
    let conn = create_in_memory_test_db(0);

    let result = run_batch(&conn).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn disabled_rss_webhook_notification_returns_ok_without_fetching() {
    let conn = create_in_memory_test_db(1);
    conn.execute(
        "INSERT INTO app_settings (key, value, rss_periodic_execution_enabled) VALUES ('rss_webhook_notification_enabled', ?, ?)",
        ("0", 0),
    )
    .expect("insert notification setting");

    let result = run_batch(&conn).await;
    assert!(result.is_ok());
}

#[test]
fn rss_execution_settings_read_their_own_rows() {
    let conn = create_in_memory_test_db(1);
    conn.execute(
        "INSERT INTO app_settings (key, value, rss_periodic_execution_enabled) VALUES ('rss_webhook_notification_enabled', '1', 1)",
        [],
    )
    .expect("insert notification setting");

    assert!(rss_periodic_execution_enabled(&conn).expect("read periodic setting"));
    assert!(rss_webhook_notification_enabled(&conn).expect("read webhook notification setting"));
}

#[test]
fn webhook_summary_defaults_to_enabled_and_can_be_disabled() {
    let conn = create_in_memory_test_db(1);
    assert!(webhook_summary_enabled(&conn).expect("read default summary setting"));

    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES ('webhook_include_summary_enabled', '0')",
        [],
    )
    .expect("insert summary setting");

    assert!(!webhook_summary_enabled(&conn).expect("read disabled summary setting"));
}

#[test]
fn fetch_webhook_endpoints_reads_multiple_endpoints_in_registration_order() {
    let conn = create_in_memory_test_db(1);
    conn.execute(
        "INSERT INTO webhook_endpoints (url) VALUES (?)",
        ["https://hooks.slack.com/services/xxx/yyy/zzz"],
    )
    .expect("insert second webhook endpoint");

    let endpoints = fetch_webhook_endpoints(&conn).expect("read webhook endpoints");
    let urls: Vec<String> = endpoints
        .iter()
        .map(|endpoint| endpoint.url.clone())
        .collect();
    assert_eq!(
        urls,
        vec![
            "https://discord.com/api/webhooks/1/token".to_string(),
            "https://hooks.slack.com/services/xxx/yyy/zzz".to_string(),
        ]
    );
    assert!(endpoints.iter().all(|endpoint| endpoint.id > 0));
}

#[test]
fn fetch_webhook_endpoints_excludes_disabled_endpoints() {
    let conn = create_in_memory_test_db(1);
    conn.execute(
        "ALTER TABLE webhook_endpoints ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1",
        [],
    )
    .expect("add enabled column");
    conn.execute(
        "INSERT INTO webhook_endpoints (url, enabled) VALUES (?, 0)",
        ["https://hooks.slack.com/services/xxx/yyy/zzz"],
    )
    .expect("insert disabled endpoint");

    let endpoints = fetch_webhook_endpoints(&conn).expect("read enabled endpoints");

    assert_eq!(endpoints.len(), 1);
    assert_eq!(endpoints[0].url, "https://discord.com/api/webhooks/1/token");
}

#[test]
fn fetch_webhook_endpoints_falls_back_to_legacy_app_settings_key() {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    conn.execute_batch(
        "
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            rss_periodic_execution_enabled INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        ",
    )
    .expect("create legacy schema");
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES ('default_webhook_url', ?)",
        ["https://discord.com/api/webhooks/1/token"],
    )
    .expect("insert legacy webhook setting");

    let endpoints = fetch_webhook_endpoints(&conn).expect("read webhook endpoints");
    assert_eq!(endpoints.len(), 1);
    assert_eq!(endpoints[0].url, "https://discord.com/api/webhooks/1/token");
}

#[test]
fn fetch_rss_feeds_loads_selected_webhook_ids() {
    let conn = create_in_memory_test_db(1);
    conn.execute(
        "INSERT INTO webhook_endpoints (url) VALUES (?)",
        ["https://hooks.slack.com/services/xxx/yyy/zzz"],
    )
    .expect("insert second webhook endpoint");
    conn.execute(
        "INSERT INTO rss_feed_webhooks (feed_id, webhook_id) VALUES (1, 2)",
        [],
    )
    .expect("insert feed webhook link");

    let feeds = fetch_rss_feeds(&conn).expect("read rss feeds");
    assert_eq!(feeds.len(), 1);
    assert_eq!(feeds[0].webhook_ids, vec![2]);
}

#[test]
fn fetch_rss_feeds_without_selection_returns_empty_webhook_ids() {
    let conn = create_in_memory_test_db(1);

    let feeds = fetch_rss_feeds(&conn).expect("read rss feeds");
    assert_eq!(feeds.len(), 1);
    assert!(feeds[0].webhook_ids.is_empty());
}
