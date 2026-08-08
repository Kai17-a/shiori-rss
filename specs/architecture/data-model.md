# DB 定義

```mermaid
erDiagram
    RSS_FEEDS ||--o{ RSS_FEED_ARTICLES : contains
    RSS_FEEDS ||--o{ RSS_FEED_WEBHOOKS : selects
    WEBHOOK_ENDPOINTS ||--o{ RSS_FEED_WEBHOOKS : receives
    NEWS_SITES ||--o{ NEWS_SITE_ARTICLES : contains
    NEWS_SITES ||--o{ NEWS_SITE_WEBHOOKS : selects
    WEBHOOK_ENDPOINTS ||--o{ NEWS_SITE_WEBHOOKS : receives

    RSS_FEEDS {
        INTEGER id PK
        TEXT url UK
        TEXT title
        TEXT description
        INTEGER notify_webhook_enabled
        TEXT created_at
        TEXT updated_at
    }
    RSS_FEED_ARTICLES {
        INTEGER id PK
        INTEGER feed_id FK
        TEXT url
        TEXT title
        TEXT summary
        DATETIME published
        INTEGER webhook_notified
        TEXT created_at
    }
    WEBHOOK_ENDPOINTS {
        INTEGER id PK
        TEXT name
        TEXT url UK
        INTEGER enabled
        TEXT created_at
        TEXT updated_at
    }
    RSS_FEED_WEBHOOKS {
        INTEGER feed_id PK,FK
        INTEGER webhook_id PK,FK
    }
    NEWS_SITES {
        INTEGER id PK
        TEXT url UK
        TEXT title
        TEXT description
        TEXT scrape_config
        INTEGER notify_webhook_enabled
        TEXT created_at
        TEXT updated_at
    }
    NEWS_SITE_ARTICLES {
        INTEGER id PK
        INTEGER site_id FK
        TEXT url
        TEXT title
        TEXT summary
        DATETIME published
        INTEGER webhook_notified
        TEXT created_at
    }
    NEWS_SITE_WEBHOOKS {
        INTEGER site_id PK,FK
        INTEGER webhook_id PK,FK
    }
    APP_SETTINGS {
        TEXT key PK
        TEXT value
        TEXT updated_at
    }
```

`rss_feed_articles.webhook_notified` と `news_site_articles.webhook_notified` は1件以上の送信先への通知成功後だけ真になる。未通知行はWebhook登録後の実行で再送対象になる。`app_settings` で `rss_periodic_execution_enabled`、`rss_webhook_notification_enabled`、`webhook_include_summary_enabled` に加え、`llm_provider`、`llm_base_url`、`llm_api_key`、`llm_model` を保持する。LLM API key はAPIレスポンスへ返さない。ブックマーク、フォルダ、タグのテーブルは現行スキーマに存在しない。
