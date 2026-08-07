use feed_rs::parser;
use reqwest::Url;
use rusqlite::Connection;
use std::collections::HashSet;
use std::error::Error;
use std::time::Duration;

use crate::{
    fetch_rss_feeds, fetch_webhook_endpoints, rss_periodic_execution_enabled,
    rss_webhook_notification_enabled, webhook, webhook_summary_enabled,
};

#[derive(Debug, PartialEq)]
struct FeedArticle {
    title: String,
    link: String,
    published: String,
    summary: String,
}

fn parse_feed_articles(content: &[u8]) -> Result<Vec<FeedArticle>, parser::ParseFeedError> {
    let feed = parser::parse(content)?;
    Ok(feed
        .entries
        .into_iter()
        .map(|entry| {
            let published = entry
                .published
                .or(entry.updated)
                .map(|date| date.to_rfc3339())
                .unwrap_or_else(|| "(no published date)".to_string());
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

pub async fn run_batch(conn: &Connection) -> Result<(), Box<dyn Error>> {
    let rss_feeds = fetch_rss_feeds(conn)?;
    let rss_enabled = rss_periodic_execution_enabled(conn)?;

    if rss_feeds.is_empty() {
        return Ok(());
    }

    if !rss_enabled {
        return Ok(());
    }

    if !rss_webhook_notification_enabled(conn)? {
        return Ok(());
    }
    let include_summary = webhook_summary_enabled(conn)?;

    let webhook_endpoints = fetch_webhook_endpoints(conn)?;
    if webhook_endpoints.is_empty() {
        eprintln!("Not setting webhook URL");
        return Ok(());
    }

    let http_client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()?;

    for rss_feed in rss_feeds {
        if rss_feed.notify_webhook_enabled == 0 {
            continue;
        }
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
        let sent_urls: HashSet<String> = match webhook::load_sent_article_urls(conn, rss_feed.id) {
            Ok(urls) => urls,
            Err(err) => {
                eprintln!(
                    "Skipping RSS feed {}: failed to load sent articles: {}",
                    rss_feed.url, err
                );
                continue;
            }
        };

        let mut articles = Vec::new();
        let mut embeds = Vec::new();
        for item in &feed_articles {
            if sent_urls.contains(&item.link) {
                continue;
            }

            embeds.push(webhook::Embed {
                title: &item.title,
                link: &item.link,
                published: &item.published,
                summary: &item.summary,
            });
            articles.push(webhook::Article {
                url: &item.link,
                title: &item.title,
                published: &item.published,
            });
        }

        if embeds.is_empty() {
            continue;
        }

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
            if let Err(err) = webhook::send_rss_webhook(
                &endpoint.url,
                &rss_feed.title,
                &rss_feed.url,
                &embeds,
                &articles,
                include_summary,
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

        if let Err(err) = webhook::record_sent_articles(conn, rss_feed.id, &articles) {
            eprintln!(
                "Skipping RSS feed {}: failed to record sent articles: {}",
                rss_feed.url, err
            );
            continue;
        }
    }

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
        assert_eq!(articles[0].published, "2026-08-04T05:30:00+00:00");
        assert_eq!(articles[0].summary, "Atom content");
    }
}
