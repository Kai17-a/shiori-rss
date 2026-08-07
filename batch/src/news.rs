use chrono::{DateTime, NaiveDate, NaiveDateTime};
use reqwest::Url;
use rusqlite::{Connection, params};
use scraper::{ElementRef, Html, Selector};
use serde_json::Value;
use std::collections::HashSet;
use std::error::Error;
use std::io;

const MAX_ARTICLES_PER_RUN: usize = 100;

#[derive(Debug, Clone)]
pub struct ScrapedArticle {
    pub url: String,
    pub title: String,
    pub published: String,
    pub summary: String,
}

fn required_string<'a>(config: &'a Value, key: &str) -> Result<&'a str, Box<dyn Error>> {
    config[key]
        .as_str()
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| io::Error::other(format!("missing scraping setting: {key}")).into())
}

fn optional_string<'a>(config: &'a Value, key: &str) -> Option<&'a str> {
    config[key]
        .as_str()
        .filter(|value| !value.trim().is_empty())
}

fn normalize_published(value: &str) -> Option<String> {
    let candidate = value.trim();
    if candidate.is_empty() {
        return None;
    }
    if let Ok(value) = DateTime::parse_from_rfc3339(candidate) {
        return Some(value.to_rfc3339());
    }
    if let Ok(value) = DateTime::parse_from_rfc2822(candidate) {
        return Some(value.to_rfc3339());
    }
    for format in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"] {
        if let Ok(value) = NaiveDateTime::parse_from_str(candidate, format) {
            return Some(value.format("%Y-%m-%d %H:%M:%S").to_string());
        }
    }
    for format in ["%Y-%m-%d", "%Y.%m.%d"] {
        if let Ok(value) = NaiveDate::parse_from_str(candidate, format) {
            return Some(format!("{} 00:00:00", value.format("%Y-%m-%d")));
        }
    }
    None
}

fn select_value(
    item: &ElementRef<'_>,
    selector_text: Option<&str>,
    attribute: Option<&str>,
) -> Result<Option<String>, Box<dyn Error>> {
    let Some(selector_text) = selector_text else {
        return Ok(None);
    };
    let selector = Selector::parse(selector_text)
        .map_err(|_| io::Error::other(format!("invalid CSS selector: {selector_text}")))?;
    let Some(selected) = item.select(&selector).next() else {
        return Ok(None);
    };
    let value = if let Some(attribute) = attribute {
        selected.value().attr(attribute).map(str::to_string)
    } else {
        let text = selected.text().collect::<Vec<_>>().join(" ");
        let trimmed = text.trim();
        (!trimmed.is_empty()).then(|| trimmed.to_string())
    };
    Ok(value)
}

pub fn extract_news_articles(
    html: &str,
    page_url: &str,
    scrape_config: &str,
) -> Result<Vec<ScrapedArticle>, Box<dyn Error>> {
    let config: Value = serde_json::from_str(scrape_config)?;
    let item_selector_text = required_string(&config, "item_selector")?;
    let title_selector = required_string(&config, "title_selector")?;
    let link_selector = required_string(&config, "link_selector")?;
    let link_attribute = required_string(&config, "link_attribute")?;
    let item_selector = Selector::parse(item_selector_text)
        .map_err(|_| io::Error::other(format!("invalid CSS selector: {item_selector_text}")))?;
    let document = Html::parse_document(html);
    let base_url = Url::parse(page_url)?;
    let mut seen_urls = HashSet::new();
    let mut articles = Vec::new();

    for item in document.select(&item_selector) {
        let Some(link) = select_value(&item, Some(link_selector), Some(link_attribute))? else {
            continue;
        };
        let article_url = match base_url.join(&link) {
            Ok(url) if matches!(url.scheme(), "http" | "https") => url.to_string(),
            _ => continue,
        };
        if !seen_urls.insert(article_url.clone()) {
            continue;
        }
        let Some(title) = select_value(&item, Some(title_selector), None)? else {
            continue;
        };
        let published = select_value(
            &item,
            optional_string(&config, "published_selector"),
            optional_string(&config, "published_attribute"),
        )?
        .and_then(|value| normalize_published(&value))
        .unwrap_or_default();
        let summary = select_value(&item, optional_string(&config, "summary_selector"), None)?
            .unwrap_or_default();
        articles.push(ScrapedArticle {
            url: article_url,
            title,
            published,
            summary,
        });
        if articles.len() >= MAX_ARTICLES_PER_RUN {
            break;
        }
    }
    Ok(articles)
}

pub fn load_sent_article_urls(
    conn: &Connection,
    site_id: u32,
) -> Result<HashSet<String>, rusqlite::Error> {
    let mut stmt = conn.prepare("SELECT url FROM news_site_articles WHERE site_id = ?")?;
    let rows = stmt.query_map(params![site_id], |row| row.get::<_, String>(0))?;
    rows.collect()
}

pub fn record_sent_articles(
    conn: &Connection,
    site_id: u32,
    articles: &[ScrapedArticle],
) -> Result<(), rusqlite::Error> {
    for article in articles {
        conn.execute(
            "INSERT OR IGNORE INTO news_site_articles (site_id, url, title, published) VALUES (?, ?, ?, ?)",
            params![
                site_id,
                article.url,
                article.title,
                if article.published.is_empty() {
                    None
                } else {
                    Some(article.published.as_str())
                }
            ],
        )?;
    }
    Ok(())
}
