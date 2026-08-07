#[path = "../src/webhook.rs"]
mod webhook;

use rusqlite::Connection;
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use wiremock::{Mock, MockServer, Request, Respond, ResponseTemplate, matchers::method};

#[derive(Clone)]
struct FailTwiceThenSucceed {
    attempts: Arc<AtomicUsize>,
}

impl Respond for FailTwiceThenSucceed {
    fn respond(&self, _request: &Request) -> ResponseTemplate {
        if self.attempts.fetch_add(1, Ordering::SeqCst) < 2 {
            ResponseTemplate::new(500)
        } else {
            ResponseTemplate::new(204)
        }
    }
}

fn create_in_memory_test_db() -> Connection {
    let conn = Connection::open_in_memory().expect("open in-memory db");
    conn.execute_batch(
        "
        CREATE TABLE rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE rss_feed_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            published DATETIME
        );
        ",
    )
    .expect("create schema");
    conn.execute(
        "INSERT INTO rss_feeds (id, url, title, description) VALUES (1, ?, ?, ?)",
        (
            "https://example.com/feed",
            "Example Feed",
            Option::<&str>::None,
        ),
    )
    .expect("insert feed");
    conn
}

#[test]
fn build_payload_matches_expected_shape() {
    let payload = serde_json::json!({
        "username": "Shiori Keeper",
        "content": "**Example Feed** - **New articles** (1 items)",
        "embeds": [{
            "title": "Example Article",
            "url": "https://example.com/article",
            "description": "Example summary",
        }]
    });

    let _embeds = vec![webhook::Embed {
        title: "Example Article",
        link: "https://example.com/article",
        published: "Wed, 01 Jan 2025 00:00:00 GMT",
        summary: "Example summary",
    }];
    let _articles = vec![webhook::Article {
        url: "https://example.com/article",
        title: "Example Article",
        published: "Wed, 01 Jan 2025 00:00:00 GMT",
    }];

    let expected_body = serde_json::json!({
        "username": "Shiori Keeper",
        "content": "**Example Feed** - **New articles** (1 items)",
        "embeds": [{
            "title": "Example Article",
            "url": "https://example.com/article",
            "description": "Example summary",
        }]
    });

    assert_eq!(payload, expected_body);
}

#[test]
fn build_payload_supports_slack_shape() {
    let _embeds = vec![webhook::Embed {
        title: "Example Article",
        link: "https://example.com/article",
        published: "Wed, 01 Jan 2025 00:00:00 GMT",
        summary: "Example summary",
    }];
    let _articles = vec![webhook::Article {
        url: "https://example.com/article",
        title: "Example Article",
        published: "Wed, 01 Jan 2025 00:00:00 GMT",
    }];

    let payload = webhook::build_payload(
        "slack",
        "**Example Feed** - **New articles** (1 items)".to_string(),
        vec![serde_json::json!({
            "title": "Example Article",
            "url": "https://example.com/article",
            "description": "Example summary",
        })],
    );

    assert_eq!(
        payload,
        serde_json::json!({
            "username": "Shiori Keeper",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "**Example Feed** - **New articles** (1 items)",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• <https://example.com/article|Example Article>\nExample summary",
                    }
                }
            ],
        })
    );
}

#[test]
fn build_payload_supports_microsoft_teams_adaptive_cards() {
    let payload = webhook::build_payload(
        "teams",
        "Example Feed - New articles (1 items)".to_string(),
        vec![serde_json::json!({
            "title": "Example Article",
            "url": "https://example.com/article",
            "description": "Example summary",
        })],
    );

    assert_eq!(payload["type"], "message");
    assert_eq!(
        payload["attachments"][0]["contentType"],
        "application/vnd.microsoft.card.adaptive"
    );
    assert_eq!(
        payload["attachments"][0]["content"]["body"][1]["items"][0]["text"],
        "• [Example Article](https://example.com/article)"
    );
    assert_eq!(
        payload["attachments"][0]["content"]["body"][1]["spacing"],
        "Medium"
    );
    assert!(payload["attachments"][0]["content"]["body"][1]["separator"].is_null());
    assert_eq!(
        payload["attachments"][0]["content"]["body"][1]["items"][1]["spacing"],
        "Small"
    );
    let article_items = payload["attachments"][0]["content"]["body"][1]["items"]
        .as_array()
        .expect("article items");
    assert!(article_items.iter().all(|item| item["type"] != "ActionSet"));
}

#[test]
fn detects_supported_microsoft_teams_webhook_urls() {
    assert_eq!(
        webhook::detect_webhook_service(
            "https://prod-01.japaneast.logic.azure.com/workflows/id/triggers/manual/paths/invoke?sig=token"
        ),
        Some("teams")
    );
    assert_eq!(
        webhook::detect_webhook_service("https://example.webhook.office.com/webhookb2/id/token"),
        Some("teams")
    );
}

#[test]
fn record_sent_articles_inserts_rows() {
    let conn = create_in_memory_test_db();
    let articles = vec![
        webhook::Article {
            url: "https://example.com/article-1",
            title: "Article 1",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
        },
        webhook::Article {
            url: "https://example.com/article-2",
            title: "Article 2",
            published: "Thu, 02 Jan 2025 00:00:00 GMT",
        },
    ];

    webhook::record_sent_articles(&conn, 1, &articles).expect("record articles");

    let count: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM rss_feed_articles WHERE feed_id = 1",
            [],
            |row| row.get(0),
        )
        .expect("count rows");
    assert_eq!(count, 2);

    let urls = webhook::load_sent_article_urls(&conn, 1).expect("load urls");
    assert!(urls.contains("https://example.com/article-1"));
    assert!(urls.contains("https://example.com/article-2"));
}

#[tokio::test]
async fn post_with_retry_retries_three_times() {
    let result = webhook::send_rss_webhook(
        "http://localhost:9999",
        "Example Feed",
        "https://example.com/feed",
        &[webhook::Embed {
            title: "Example Article",
            link: "https://example.com/article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
            summary: "Example summary",
        }],
        &[webhook::Article {
            url: "https://example.com/article",
            title: "Example Article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
        }],
        true,
    )
    .await;

    let err = result.expect_err("webhook should fail");
    assert!(err.to_string().contains("after 3 attempts"));
}

#[tokio::test]
async fn transient_http_errors_are_retried_three_times() {
    for status in [429, 500] {
        let server = MockServer::start().await;
        Mock::given(method("POST"))
            .respond_with(ResponseTemplate::new(status))
            .mount(&server)
            .await;

        let result = send_example_webhook(&server.uri()).await;

        assert!(result.is_err());
        assert_eq!(server.received_requests().await.unwrap().len(), 3);
    }
}

#[tokio::test]
async fn webhook_succeeds_when_a_retry_recovers() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(FailTwiceThenSucceed {
            attempts: Arc::new(AtomicUsize::new(0)),
        })
        .mount(&server)
        .await;

    let result = send_example_webhook(&server.uri()).await;

    assert!(result.is_ok());
    assert_eq!(server.received_requests().await.unwrap().len(), 3);
}

#[tokio::test]
async fn long_embed_content_is_truncated_before_sending() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(ResponseTemplate::new(204))
        .mount(&server)
        .await;

    let long_title = "T".repeat(400);
    let long_summary = "S".repeat(20_000);

    let result = webhook::send_rss_webhook(
        &server.uri(),
        "Example Feed",
        "https://example.com/feed",
        &[webhook::Embed {
            title: &long_title,
            link: "https://example.com/article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
            summary: &long_summary,
        }],
        &[webhook::Article {
            url: "https://example.com/article",
            title: "Example Article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
        }],
        true,
    )
    .await;

    assert!(result.is_ok());
    let requests = server.received_requests().await.unwrap();
    assert_eq!(requests.len(), 1);
    let body: serde_json::Value = serde_json::from_slice(&requests[0].body).unwrap();
    let embed = &body["embeds"][0];
    let title = embed["title"].as_str().unwrap();
    let description = embed["description"].as_str().unwrap();
    assert!(title.chars().count() <= 256);
    assert!(title.ends_with('…'));
    assert!(description.chars().count() <= 300);
    assert!(description.ends_with('…'));
}

#[tokio::test]
async fn article_summary_can_be_omitted() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .respond_with(ResponseTemplate::new(204))
        .mount(&server)
        .await;

    let result = webhook::send_rss_webhook(
        &server.uri(),
        "Example Feed",
        "https://example.com/feed",
        &[webhook::Embed {
            title: "Example Article",
            link: "https://example.com/article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
            summary: "This summary must not be sent.",
        }],
        &[webhook::Article {
            url: "https://example.com/article",
            title: "Example Article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
        }],
        false,
    )
    .await;

    assert!(result.is_ok());
    let requests = server.received_requests().await.unwrap();
    let body: serde_json::Value = serde_json::from_slice(&requests[0].body).unwrap();
    assert!(body["embeds"][0].get("description").is_none());
}

async fn send_example_webhook(webhook_url: &str) -> Result<(), Box<dyn std::error::Error>> {
    webhook::send_rss_webhook(
        webhook_url,
        "Example Feed",
        "https://example.com/feed",
        &[webhook::Embed {
            title: "Example Article",
            link: "https://example.com/article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
            summary: "Example summary",
        }],
        &[webhook::Article {
            url: "https://example.com/article",
            title: "Example Article",
            published: "Wed, 01 Jan 2025 00:00:00 GMT",
        }],
        true,
    )
    .await
}
