use chrono::DateTime;
use feed_rs::parser;
use quick_xml::Reader;
use quick_xml::events::Event;
use reqwest::Url;
use rusqlite::Connection;
use std::collections::HashSet;
use std::error::Error;
use std::time::Duration;

use crate::{
    analysis::run_article_analysis, fetch_rss_feeds, fetch_webhook_endpoints,
    rss_periodic_execution_enabled, rss_webhook_notification_enabled, webhook,
    webhook_article_limit, webhook_summary_enabled,
};

#[derive(Debug, PartialEq)]
struct FeedArticle {
    title: String,
    link: String,
    published: String,
    summary: String,
}

fn normalize_source_published(value: &str) -> Option<String> {
    DateTime::parse_from_rfc3339(value)
        .or_else(|_| DateTime::parse_from_rfc2822(value))
        .ok()
        .map(|date| date.to_rfc3339())
}

fn extract_source_published(content: &[u8]) -> Vec<Option<String>> {
    let mut reader = Reader::from_reader(content);
    reader.config_mut().trim_text(true);
    let mut dates = Vec::new();
    let mut in_article = false;
    let mut capture_published = false;
    let mut capture_updated = false;
    let mut published = None;
    let mut updated = None;

    loop {
        match reader.read_event() {
            Ok(Event::Start(event)) => match event.local_name().as_ref() {
                b"item" | b"entry" => {
                    in_article = true;
                    published = None;
                    updated = None;
                }
                b"pubDate" | b"published" if in_article => capture_published = true,
                b"updated" if in_article => capture_updated = true,
                _ => {}
            },
            Ok(Event::Text(text)) if capture_published => {
                published = text.decode().ok().map(|value| value.trim().to_string());
            }
            Ok(Event::Text(text)) if capture_updated => {
                updated = text.decode().ok().map(|value| value.trim().to_string());
            }
            Ok(Event::End(event)) => match event.local_name().as_ref() {
                b"pubDate" | b"published" => capture_published = false,
                b"updated" => capture_updated = false,
                b"item" | b"entry" if in_article => {
                    dates.push(published.take().or_else(|| updated.take()));
                    in_article = false;
                }
                _ => {}
            },
            Ok(Event::Eof) | Err(_) => break,
            _ => {}
        }
    }

    dates
}

fn parse_feed_articles(content: &[u8]) -> Result<Vec<FeedArticle>, parser::ParseFeedError> {
    let feed = parser::parse(content)?;
    let source_dates = extract_source_published(content);
    Ok(feed
        .entries
        .into_iter()
        .enumerate()
        .map(|(index, entry)| {
            let parsed_published = entry
                .published
                .or(entry.updated)
                .map(|date| date.to_rfc3339())
                .unwrap_or_else(|| "(no published date)".to_string());
            let published = source_dates
                .get(index)
                .and_then(|value| value.as_deref())
                .and_then(normalize_source_published)
                .unwrap_or(parsed_published);
            FeedArticle {
                title: entry
                    .title
                    .map(|title| title.content)
                    .unwrap_or_else(|| "(no title)".to_string()),
                link: entry
                    .links
                    .iter()
                    .find(|link| link.rel.as_deref() == Some("alternate"))
                    .or_else(|| entry.links.iter().find(|link| link.rel.is_none()))
                    .or_else(|| entry.links.first())
                    .map(|link| link.href.clone())
                    .unwrap_or_else(|| "(no link)".to_string()),
                published,
                summary: entry
                    .summary
                    .map(|summary| summary.content)
                    .or_else(|| entry.content.and_then(|content| content.body))
                    .unwrap_or_else(|| "(no summary)".to_string()),
            }
        })
        .collect())
}

async fn run_rss_batch(conn: &Connection) -> Result<(), Box<dyn Error>> {
    let rss_feeds = fetch_rss_feeds(conn)?;
    let rss_enabled = rss_periodic_execution_enabled(conn)?;

    if rss_feeds.is_empty() {
        return Ok(());
    }

    if !rss_enabled {
        return Ok(());
    }

    let notification_enabled = rss_webhook_notification_enabled(conn)?;
    let include_summary = webhook_summary_enabled(conn)?;
    let article_limit = webhook_article_limit(conn)?;

    let webhook_endpoints = fetch_webhook_endpoints(conn)?;

    let http_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()?;

    for rss_feed in rss_feeds {
        let url = match Url::parse(&rss_feed.url) {
            Ok(url) => url,
            Err(err) => {
                eprintln!("Skipping invalid RSS URL {}: {}", rss_feed.url, err);
                continue;
            }
        };
        let content = match http_client.get(url).send().await {
            Ok(response) => match response.bytes().await {
                Ok(content) => content,
                Err(err) => {
                    eprintln!(
                        "Skipping RSS feed {}: failed to read body: {}",
                        rss_feed.url, err
                    );
                    continue;
                }
            },
            Err(err) => {
                eprintln!(
                    "Skipping RSS feed {}: request failed: {}",
                    rss_feed.url, err
                );
                continue;
            }
        };
        let feed_articles = match parse_feed_articles(&content) {
            Ok(articles) => articles,
            Err(err) => {
                eprintln!(
                    "Skipping RSS feed {}: failed to parse channel: {}",
                    rss_feed.url, err
                );
                continue;
            }
        };
        let fetched_urls: HashSet<String> = match webhook::load_article_urls(conn, rss_feed.id) {
            Ok(urls) => urls,
            Err(err) => {
                eprintln!(
                    "Skipping RSS feed {}: failed to load sent articles: {}",
                    rss_feed.url, err
                );
                continue;
            }
        };

        let mut new_articles = Vec::new();
        for item in &feed_articles {
            if fetched_urls.contains(&item.link) {
                continue;
            }
            new_articles.push(webhook::StoredArticle {
                url: item.link.clone(),
                title: item.title.clone(),
                published: item.published.clone(),
                summary: item.summary.clone(),
            });
        }

        if let Err(err) = webhook::record_pending_articles(conn, rss_feed.id, &new_articles) {
            eprintln!(
                "Skipping RSS feed {}: failed to record articles: {}",
                rss_feed.url, err
            );
            continue;
        }

        if !notification_enabled || rss_feed.notify_webhook_enabled == 0 {
            continue;
        }

        let pending_articles = match webhook::load_pending_articles(conn, rss_feed.id) {
            Ok(articles) => articles,
            Err(err) => {
                eprintln!(
                    "Skipping RSS feed {}: failed to load pending articles: {}",
                    rss_feed.url, err
                );
                continue;
            }
        };
        if pending_articles.is_empty() {
            continue;
        }
        let notification_count = pending_articles.len().min(article_limit);
        let notification_articles = &pending_articles[..notification_count];

        let embeds: Vec<webhook::Embed<'_>> = notification_articles
            .iter()
            .map(|article| webhook::Embed {
                title: &article.title,
                link: &article.url,
                published: &article.published,
                summary: &article.summary,
            })
            .collect();
        let articles: Vec<webhook::Article<'_>> = notification_articles
            .iter()
            .map(|article| webhook::Article {
                url: &article.url,
                title: &article.title,
                published: &article.published,
            })
            .collect();

        let targets: Vec<&crate::WebhookEndpoint> = if rss_feed.webhook_ids.is_empty() {
            webhook_endpoints.iter().collect()
        } else {
            webhook_endpoints
                .iter()
                .filter(|endpoint| rss_feed.webhook_ids.contains(&endpoint.id))
                .collect()
        };
        if targets.is_empty() {
            eprintln!(
                "Skipping RSS feed {}: no matching webhook endpoints",
                rss_feed.url
            );
            continue;
        }

        let mut delivered = false;
        for endpoint in targets {
            if let Err(err) = webhook::send_rss_webhook_with_icon(
                &endpoint.url,
                &rss_feed.title,
                &rss_feed.url,
                &embeds,
                &articles,
                include_summary,
                rss_feed.icon_url.as_deref(),
            )
            .await
            {
                eprintln!("{}", err);
                continue;
            }
            delivered = true;
        }

        if !delivered {
            continue;
        }

        if let Err(err) = webhook::mark_articles_notified(conn, rss_feed.id, &pending_articles) {
            eprintln!(
                "Skipping RSS feed {}: failed to mark articles notified: {}",
                rss_feed.url, err
            );
            continue;
        }
    }

    Ok(())
}

pub async fn run_batch(conn: &Connection) -> Result<(), Box<dyn Error>> {
    run_rss_batch(conn).await?;
    run_article_analysis(conn).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::parse_feed_articles;

    #[test]
    fn parses_rss_articles() {
        let content = br#"<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
              <channel>
                <title>Example RSS</title>
                <link>https://example.com/</link>
                <description>Example feed</description>
                <item>
                  <title>RSS article</title>
                  <link>https://example.com/rss-article</link>
                  <pubDate>Mon, 04 Aug 2025 06:00:00 +0000</pubDate>
                  <description>RSS summary</description>
                </item>
              </channel>
            </rss>"#;

        let articles = parse_feed_articles(content).expect("parse RSS feed");

        assert_eq!(articles.len(), 1);
        assert_eq!(articles[0].title, "RSS article");
        assert_eq!(articles[0].link, "https://example.com/rss-article");
        assert_eq!(articles[0].published, "2025-08-04T06:00:00+00:00");
        assert_eq!(articles[0].summary, "RSS summary");
    }

    #[test]
    fn parses_atom_articles() {
        let content = br#"<?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <title>Example Atom</title>
              <id>https://example.com/atom</id>
              <updated>2026-08-04T06:00:00Z</updated>
              <entry>
                <title>Atom article</title>
                <id>https://example.com/atom-article</id>
                <link rel="self" href="https://example.com/atom-article.atom" />
                <link rel="alternate" href="https://example.com/atom-article" />
                <published>2026-08-04T14:30:00+09:00</published>
                <updated>2026-08-04T14:35:00+09:00</updated>
                <content type="text">Atom content</content>
              </entry>
            </feed>"#;

        let articles = parse_feed_articles(content).expect("parse Atom feed");

        assert_eq!(articles.len(), 1);
        assert_eq!(articles[0].title, "Atom article");
        assert_eq!(articles[0].link, "https://example.com/atom-article");
        assert_eq!(articles[0].published, "2026-08-04T14:30:00+09:00");
        assert_eq!(articles[0].summary, "Atom content");
    }
}
