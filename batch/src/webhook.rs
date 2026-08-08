use std::error::Error;
use std::io;
use std::time::Duration;

use reqwest::Url;
use rusqlite::{Connection, params};

pub(crate) const MAX_EMBED_TITLE_LEN: usize = 256;
// Keep summaries short enough that a 10-embed chunk stays below Discord's
// 6000-character per-message total (title + description per embed) and below
// Slack's 3000-character section block text limit.
pub(crate) const MAX_EMBED_SUMMARY_LEN: usize = 300;

pub(crate) fn truncate(value: &str, max_chars: usize) -> String {
    if value.chars().count() <= max_chars {
        return value.to_string();
    }
    let truncated: String = value.chars().take(max_chars - 1).collect();
    format!("{}…", truncated.trim_end())
}

#[derive(Debug)]
pub struct Embed<'a> {
    pub title: &'a str,
    pub link: &'a str,
    pub published: &'a str,
    pub summary: &'a str,
}

#[derive(Debug)]
pub struct Article<'a> {
    pub url: &'a str,
    pub title: &'a str,
    pub published: &'a str,
}

#[derive(Debug)]
pub struct StoredArticle {
    pub url: String,
    pub title: String,
    pub published: String,
    pub summary: String,
}

fn chunk_embeds<'a>(embeds: &'a [Embed<'a>], include_summary: bool) -> Vec<Vec<&'a Embed<'a>>> {
    let mut chunks = Vec::new();
    let mut current = Vec::new();
    let mut current_len = 0usize;

    for embed in embeds {
        let embed_len = embed.title.len().min(MAX_EMBED_TITLE_LEN)
            + embed.link.len()
            + embed.published.len()
            + if include_summary {
                embed.summary.len().min(MAX_EMBED_SUMMARY_LEN)
            } else {
                0
            };
        if (current.len() >= 10 || current_len + embed_len > 6000) && !current.is_empty() {
            chunks.push(current);
            current = Vec::new();
            current_len = 0;
        }
        current.push(embed);
        current_len += embed_len;
    }

    if !current.is_empty() {
        chunks.push(current);
    }

    chunks
}

pub(crate) fn build_payload(
    webhook_service: &str,
    content: String,
    embeds_payload: Vec<serde_json::Value>,
) -> serde_json::Value {
    match webhook_service {
        "discord" => serde_json::json!({
            "username": "Shiori Keeper",
            "content": content,
            "embeds": embeds_payload,
        }),
        "slack" => {
            let blocks: Vec<serde_json::Value> = std::iter::once(serde_json::json!({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": content,
                }
            }))
            .chain(embeds_payload.into_iter().map(|embed| {
                let title = embed["title"].as_str().unwrap_or("(no title)");
                let url = embed["url"].as_str().unwrap_or("(no link)");
                let description = embed["description"].as_str();
                let mut text = format!("• <{}|{}>", url, title);
                if let Some(description) = description {
                    text = format!("{}\n{}", text, description);
                }
                serde_json::json!({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text,
                    }
                })
            }))
            .collect();
            serde_json::json!({
                "username": "Shiori Keeper",
                "blocks": blocks,
            })
        }
        "teams" => {
            let mut body = vec![serde_json::json!({
                "type": "TextBlock",
                "text": content,
                "size": "Medium",
                "weight": "Bolder",
                "wrap": true,
            })];
            body.extend(embeds_payload.into_iter().map(|embed| {
                let title = embed["title"].as_str().unwrap_or("(no title)");
                let url = embed["url"].as_str().unwrap_or("(no link)");
                let mut items = vec![serde_json::json!({
                    "type": "TextBlock",
                    "text": format!("• [{}]({})", title, url),
                    "weight": "Bolder",
                    "wrap": true,
                })];
                if let Some(summary) = embed["description"].as_str() {
                    items.push(serde_json::json!({
                        "type": "TextBlock",
                        "text": summary,
                        "isSubtle": true,
                        "spacing": "Small",
                        "wrap": true,
                    }));
                }
                serde_json::json!({
                    "type": "Container",
                    "spacing": "Medium",
                    "items": items,
                })
            }));
            serde_json::json!({
                "type": "message",
                "attachments": [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": null,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": body,
                    }
                }]
            })
        }
        _ => serde_json::json!({
            "text": content,
        }),
    }
}

async fn post_with_retry(
    client: &reqwest::Client,
    webhook_url: &str,
    payload: &serde_json::Value,
) -> Result<reqwest::Response, String> {
    let mut last_error: Option<String> = None;
    for attempt in 1..=3 {
        match client.post(webhook_url).json(payload).send().await {
            Ok(response)
                if attempt < 3
                    && (response.status().is_server_error()
                        || response.status() == reqwest::StatusCode::TOO_MANY_REQUESTS) =>
            {
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
            Ok(response) => return Ok(response),
            Err(err) => {
                last_error = Some(err.to_string());
                if attempt < 3 {
                    tokio::time::sleep(Duration::from_millis(500)).await;
                }
            }
        }
    }

    Err(last_error.unwrap_or_else(|| "unknown error".to_string()))
}

pub async fn send_rss_webhook(
    webhook_url: &str,
    feed_title: &str,
    feed_url: &str,
    embeds: &[Embed<'_>],
    articles: &[Article<'_>],
    include_summary: bool,
) -> Result<(), Box<dyn Error>> {
    send_article_webhook(
        webhook_url,
        feed_title,
        feed_url,
        "RSS feed",
        embeds,
        articles,
        include_summary,
    )
    .await
}

async fn send_article_webhook(
    webhook_url: &str,
    source_title: &str,
    source_url: &str,
    source_kind: &str,
    embeds: &[Embed<'_>],
    articles: &[Article<'_>],
    include_summary: bool,
) -> Result<(), Box<dyn Error>> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()?;
    let webhook_service = detect_webhook_service(webhook_url).unwrap_or("discord");
    let embed_chunks = chunk_embeds(embeds, include_summary);

    for (index, chunk) in embed_chunks.iter().enumerate() {
        let mut content = format!(
            "**{}** - **New articles** ({} items)",
            source_title,
            embeds.len()
        );
        if embed_chunks.len() > 1 {
            content = format!("{} [{}]", content, index + 1);
        }

        let embeds_payload: Vec<_> = chunk
            .iter()
            .map(|embed| {
                let mut payload = serde_json::json!({
                    "title": truncate(embed.title, MAX_EMBED_TITLE_LEN),
                    "url": embed.link,
                });
                if include_summary && !embed.summary.is_empty() {
                    payload["description"] =
                        serde_json::json!(truncate(embed.summary, MAX_EMBED_SUMMARY_LEN));
                }
                payload
            })
            .collect();
        let payload = build_payload(webhook_service, content, embeds_payload);

        let response = match post_with_retry(&client, webhook_url, &payload).await {
            Ok(response) => response,
            Err(err) => {
                return Err(io::Error::other(format!(
                    "Skipping {} {}: failed to notify webhook after 3 attempts: {}",
                    source_kind, source_url, err
                ))
                .into());
            }
        };

        if response.status().is_client_error() || response.status().is_server_error() {
            let status = response.status();
            let body = response.text().await.unwrap_or_else(|_| String::new());
            return Err(io::Error::other(format!(
                "Skipping {} {}: webhook returned {}{}",
                source_kind,
                source_url,
                status,
                if body.is_empty() {
                    String::new()
                } else {
                    format!(": {}", body)
                }
            ))
            .into());
        }
    }

    let _ = articles;
    Ok(())
}

pub fn record_pending_articles(
    conn: &Connection,
    feed_id: u32,
    articles: &[StoredArticle],
) -> Result<(), rusqlite::Error> {
    for article in articles {
        conn.execute(
            r#"
            INSERT OR IGNORE INTO rss_feed_articles
                (feed_id, url, title, summary, published, webhook_notified)
            VALUES (?, ?, ?, ?, ?, 0)
            "#,
            params![
                feed_id,
                article.url,
                article.title,
                article.summary,
                article.published
            ],
        )?;
    }

    Ok(())
}

pub fn load_article_urls(
    conn: &Connection,
    feed_id: u32,
) -> Result<std::collections::HashSet<String>, rusqlite::Error> {
    let mut stmt = conn.prepare("SELECT url FROM rss_feed_articles WHERE feed_id = ?")?;
    let rows = stmt.query_map(params![feed_id], |row| row.get::<_, String>(0))?;

    let mut urls = std::collections::HashSet::new();
    for row in rows {
        urls.insert(row?);
    }

    Ok(urls)
}

pub fn load_pending_articles(
    conn: &Connection,
    feed_id: u32,
) -> Result<Vec<StoredArticle>, rusqlite::Error> {
    let mut stmt = conn.prepare(
        r#"
        SELECT url, coalesce(title, '(no title)'), coalesce(published, '(no published date)'),
               coalesce(summary, '(no summary)')
        FROM rss_feed_articles
        WHERE feed_id = ? AND webhook_notified = 0
        ORDER BY id ASC
        "#,
    )?;
    let rows = stmt.query_map(params![feed_id], |row| {
        Ok(StoredArticle {
            url: row.get(0)?,
            title: row.get(1)?,
            published: row.get(2)?,
            summary: row.get(3)?,
        })
    })?;
    rows.collect()
}

pub fn mark_articles_notified(
    conn: &Connection,
    feed_id: u32,
    articles: &[StoredArticle],
) -> Result<(), rusqlite::Error> {
    for article in articles {
        conn.execute(
            "UPDATE rss_feed_articles SET webhook_notified = 1 WHERE feed_id = ? AND url = ?",
            params![feed_id, article.url],
        )?;
    }
    Ok(())
}
pub(crate) fn detect_webhook_service(webhook_url: &str) -> Option<&'static str> {
    let parsed = Url::parse(webhook_url).ok()?;
    let hostname = parsed.host_str().unwrap_or("");
    let path = parsed.path();

    let discord_hosts = [
        "discord.com",
        "www.discord.com",
        "discordapp.com",
        "www.discordapp.com",
    ];
    if (parsed.scheme() == "http" || parsed.scheme() == "https")
        && discord_hosts.contains(&hostname)
        && path.starts_with("/api/webhooks/")
    {
        return Some("discord");
    }

    if (parsed.scheme() == "http" || parsed.scheme() == "https")
        && hostname == "hooks.slack.com"
        && path.starts_with("/services/")
    {
        let parts: Vec<_> = path.split('/').filter(|part| !part.is_empty()).collect();
        if parts.len() == 4 && parts[0] == "services" {
            return Some("slack");
        }
    }

    let legacy_teams = hostname.ends_with(".webhook.office.com") && path.starts_with("/webhookb2/");
    let workflow_teams = hostname.ends_with(".logic.azure.com") && path.starts_with("/workflows/");
    let power_platform_teams = hostname.ends_with(".api.powerplatform.com")
        && path.contains("/workflows/")
        && path.contains("/triggers/");
    if parsed.scheme() == "https" && (legacy_teams || workflow_teams || power_platform_teams) {
        return Some("teams");
    }

    None
}
