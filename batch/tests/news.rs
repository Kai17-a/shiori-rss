use rusqlite::Connection;
use shiori_keeper_batch::news::{
    extract_news_articles, load_sent_article_urls, record_sent_articles,
};

const SCRAPE_CONFIG: &str = r#"{
  "site_title": "Example News",
  "item_selector": ".news-item",
  "title_selector": "h2 a",
  "link_selector": "h2 a",
  "link_attribute": "href",
  "published_selector": "time",
  "published_attribute": "datetime",
  "summary_selector": ".summary"
}"#;

#[test]
fn extracts_articles_with_relative_urls_and_optional_metadata() {
    let html = r#"
      <article class="news-item">
        <h2><a href="/articles/first">First article</a></h2>
        <time datetime="2026-08-01T10:00:00+09:00">August 1</time>
        <p class="summary">First summary</p>
      </article>
      <article class="news-item">
        <h2><a href="https://example.com/articles/second">Second article</a></h2>
      </article>
    "#;

    let articles = extract_news_articles(html, "https://example.com/news", SCRAPE_CONFIG)
        .expect("extract articles");

    assert_eq!(articles.len(), 2);
    assert_eq!(articles[0].url, "https://example.com/articles/first");
    assert_eq!(articles[0].title, "First article");
    assert_eq!(articles[0].published, "2026-08-01T10:00:00+09:00");
    assert_eq!(articles[0].summary, "First summary");
    assert_eq!(articles[1].summary, "");
}

#[test]
fn normalizes_dotted_dates_and_discards_invalid_dates() {
    let html = r#"
      <article class="news-item">
        <h2><a href="/articles/dotted">Dotted date</a></h2>
        <time datetime="2026.08.03">August 3</time>
      </article>
      <article class="news-item">
        <h2><a href="/articles/invalid">Invalid date</a></h2>
        <time datetime="not-a-date">Unknown</time>
      </article>
    "#;

    let articles = extract_news_articles(html, "https://example.com/news", SCRAPE_CONFIG)
        .expect("extract articles");

    assert_eq!(articles[0].published, "2026-08-03 00:00:00");
    assert_eq!(articles[1].published, "");
}

#[test]
fn records_and_loads_sent_news_articles() {
    let conn = Connection::open_in_memory().expect("open db");
    conn.execute_batch(
        "
        CREATE TABLE news_sites (
          id INTEGER PRIMARY KEY,
          url TEXT NOT NULL,
          title TEXT NOT NULL,
          scrape_config TEXT NOT NULL,
          notify_webhook_enabled INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE news_site_articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
          url TEXT NOT NULL,
          title TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          published DATETIME,
          UNIQUE(site_id, url)
        );
        INSERT INTO news_sites (id, url, title, scrape_config)
        VALUES (1, 'https://example.com/news', 'Example News', '{}');
        ",
    )
    .expect("create schema");
    let articles = extract_news_articles(
        r#"<article class="news-item"><h2><a href="/first">First</a></h2></article>"#,
        "https://example.com/news",
        SCRAPE_CONFIG,
    )
    .expect("extract articles");

    record_sent_articles(&conn, 1, &articles).expect("record articles");
    record_sent_articles(&conn, 1, &articles).expect("record idempotently");

    let urls = load_sent_article_urls(&conn, 1).expect("load sent URLs");
    assert_eq!(urls.len(), 1);
    assert!(urls.contains("https://example.com/first"));
}

#[test]
fn rejects_invalid_scraping_selectors() {
    let invalid = SCRAPE_CONFIG.replace(".news-item", "[");
    let result = extract_news_articles("<article></article>", "https://example.com", &invalid);

    assert!(result.is_err());
}

#[test]
fn skips_articles_without_an_extracted_title() {
    let html = r#"<article><a href="/one">Link text outside title selector</a></article>"#;
    let config = r#"{
        "item_selector": "article",
        "title_selector": ".missing-title",
        "link_selector": "a",
        "link_attribute": "href"
    }"#;

    let articles = extract_news_articles(html, "https://example.com/news", config).unwrap();

    assert!(articles.is_empty());
}
