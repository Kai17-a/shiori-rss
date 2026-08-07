use rusqlite::{Connection, OptionalExtension, Result};
use std::env;

pub fn database_path() -> String {
    env::var("DATABASE_URL").unwrap_or_else(|_| "data/data.db".to_string())
}

#[derive(Debug)]
pub struct WebhookEndpoint {
    pub id: u32,
    pub url: String,
}

#[derive(Debug)]
pub struct RSSFeed {
    pub id: u32,
    pub url: String,
    pub title: String,
    pub description: Option<String>,
    pub notify_webhook_enabled: i64,
    pub webhook_ids: Vec<u32>,
    pub created_at: String,
    pub updated_at: String,
}

fn has_column(conn: &Connection, table: &str, column: &str) -> Result<bool> {
    let mut stmt = conn.prepare(&format!("PRAGMA table_info({})", table))?;
    let rows = stmt.query_map([], |row| Ok(row.get::<_, String>(1)?))?;
    for row in rows {
        if row? == column {
            return Ok(true);
        }
    }
    Ok(false)
}

fn has_table(conn: &Connection, table: &str) -> Result<bool> {
    let count = conn.query_row(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
        [table],
        |row| row.get::<_, i64>(0),
    )?;
    Ok(count > 0)
}

pub fn fetch_webhook_endpoints(conn: &Connection) -> Result<Vec<WebhookEndpoint>> {
    if has_table(conn, "webhook_endpoints")? {
        let query = if has_column(conn, "webhook_endpoints", "enabled")? {
            "SELECT id, url FROM webhook_endpoints WHERE enabled = 1 ORDER BY id ASC"
        } else {
            "SELECT id, url FROM webhook_endpoints ORDER BY id ASC"
        };
        let mut stmt = conn.prepare(query)?;
        let endpoint_iter = stmt.query_map([], |row| {
            Ok(WebhookEndpoint {
                id: row.get(0)?,
                url: row.get(1)?,
            })
        })?;
        return endpoint_iter.collect();
    }

    let mut stmt =
        conn.prepare("SELECT value FROM app_settings where key = 'default_webhook_url'")?;
    let legacy_iter = stmt.query_map([], |row| {
        Ok(WebhookEndpoint {
            id: 0,
            url: row.get(0)?,
        })
    })?;
    legacy_iter.collect()
}

pub fn rss_periodic_execution_enabled(conn: &Connection) -> Result<bool> {
    let mut stmt = conn.prepare(
        "SELECT rss_periodic_execution_enabled FROM app_settings WHERE key = 'rss_periodic_execution_enabled'",
    )?;
    let value = stmt.query_row([], |row| row.get::<_, i64>(0)).unwrap_or(0);
    Ok(value != 0)
}

pub fn rss_webhook_notification_enabled(conn: &Connection) -> Result<bool> {
    let mut stmt = conn.prepare(
        "SELECT rss_periodic_execution_enabled FROM app_settings WHERE key = 'rss_webhook_notification_enabled'",
    )?;
    let value = stmt.query_row([], |row| row.get::<_, i64>(0)).unwrap_or(0);
    Ok(value != 0)
}

pub fn webhook_summary_enabled(conn: &Connection) -> Result<bool> {
    let value = conn
        .query_row(
            "SELECT value FROM app_settings WHERE key = 'webhook_include_summary_enabled'",
            [],
            |row| row.get::<_, String>(0),
        )
        .optional()?;
    Ok(value.as_deref().unwrap_or("1") != "0")
}

pub fn fetch_rss_feeds(conn: &Connection) -> Result<Vec<RSSFeed>> {
    let has_notify_webhook_enabled = has_column(conn, "rss_feeds", "notify_webhook_enabled")?;
    let query = if has_notify_webhook_enabled {
        "SELECT id, url, title, description, notify_webhook_enabled, created_at, updated_at FROM rss_feeds WHERE notify_webhook_enabled = 1"
    } else {
        "SELECT id, url, title, description, 1 AS notify_webhook_enabled, created_at, updated_at FROM rss_feeds"
    };
    let mut stmt = conn.prepare(query)?;
    let rss_feed_iter = stmt.query_map([], |row| {
        Ok(RSSFeed {
            id: row.get(0)?,
            url: row.get(1)?,
            title: row.get(2)?,
            description: row.get(3)?,
            notify_webhook_enabled: row.get(4)?,
            webhook_ids: Vec::new(),
            created_at: row.get(5)?,
            updated_at: row.get(6)?,
        })
    })?;

    let mut feeds: Vec<RSSFeed> = rss_feed_iter.collect::<Result<Vec<_>>>()?;
    if has_table(conn, "rss_feed_webhooks")? {
        for feed in &mut feeds {
            let mut link_stmt = conn.prepare(
                "SELECT webhook_id FROM rss_feed_webhooks WHERE feed_id = ? ORDER BY webhook_id ASC",
            )?;
            let link_iter = link_stmt.query_map([feed.id], |row| row.get::<_, u32>(0))?;
            feed.webhook_ids = link_iter.collect::<Result<Vec<_>>>()?;
        }
    }
    Ok(feeds)
}
