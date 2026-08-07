# データと制約

## データモデル

### テーブル

```sql
CREATE TABLE IF NOT EXISTS folders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT,
    folder_id   INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bookmarks_url_unique ON bookmarks(url);

CREATE TABLE IF NOT EXISTS rss_feeds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT,
    notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rss_feeds_url_unique ON rss_feeds(url);

CREATE TABLE IF NOT EXISTS rss_feed_articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id     INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
    url         TEXT    NOT NULL,
    title       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    published   DATETIME
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rss_feed_articles_feed_url_unique
    ON rss_feed_articles(feed_id, url);

CREATE TABLE IF NOT EXISTS news_sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    scrape_config TEXT NOT NULL,
    notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_site_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    published DATETIME
);

CREATE TABLE IF NOT EXISTS news_site_webhooks (
    site_id INTEGER NOT NULL REFERENCES news_sites(id) ON DELETE CASCADE,
    webhook_id INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    PRIMARY KEY (site_id, webhook_id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key         TEXT    PRIMARY KEY,
    value       TEXT    NOT NULL,
    rss_periodic_execution_enabled INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL DEFAULT '',
    url         TEXT    NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_endpoints_url_unique
    ON webhook_endpoints(url);

CREATE TABLE IF NOT EXISTS rss_feed_webhooks (
    feed_id     INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
    webhook_id  INTEGER NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    PRIMARY KEY (feed_id, webhook_id)
);

CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS bookmark_tags (
    bookmark_id INTEGER NOT NULL REFERENCES bookmarks(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (bookmark_id, tag_id)
);
```

## スキーマ

- `BookmarkCreate`
- `BookmarkUpdate`
- `BookmarkFavoriteUpdate`
- `RSSFeedCreate`
- `RSSFeedUpdate`
- `RSSFeedExecuteResponse`
- `SettingsWebhookCreate`
- `SettingsWebhookResponse`
- `SettingsWebhookListResponse`
- `SettingsWebhookPingRequest`
- `SettingsWebhookPingResponse`
- `SettingsRssExecutionUpdate`
- `SettingsRssExecutionResponse`
- `SettingsRssWebhookNotificationUpdate`
- `SettingsRssWebhookNotificationResponse`
- `LLMSettingsUpdate`
- `LLMSettingsResponse`
- `LLMSettingsTestRequest`
- `LLMSettingsTestResponse`
- `NewsSiteCreate`
- `NewsSiteUpdate`
- `NewsSiteResponse`
- `NewsSiteListResponse`
- `NewsSiteArticleResponse`
- `NewsSiteArticleListResponse`
- `NewsSiteExecuteResponse`
- `FolderCreate`
- `FolderUpdate`
- `TagCreate`
- `TagUpdate`
- `TagAttach`
- `BookmarkResponse`
- `BookmarkListResponse`
- `RSSFeedResponse`
- `RSSFeedListResponse`
- `RSSFeedArticleResponse`
- `RSSFeedArticleListResponse`
- `FolderResponse`
- `TagResponse`
- `DashboardMetricsResponse`
- `ErrorResponse`

## 部分更新

- `PATCH /bookmarks/{id}`、`PATCH /bookmarks/by-url`、`PATCH /rss-feeds/{id}`、`PATCH /news-sites/{id}` は、リクエストに含まれないフィールドを変更しない。
- nullable な `description` と bookmark の `folder_id` は、明示した `null` で保存済みの値を解除できる。
- URL、title、bookmark の `tag_ids`、RSS の `notify_webhook_enabled`、`webhook_ids` は明示した `null` を受け付けず、422 を返す。
- RSS の `webhook_ids` に空配列を指定すると通知先選択を解除できる（全 webhook 通知へ戻る）。
- custom news site の `url` を更新すると LLM 再解析と抽出テストを実行し、成功時だけ URL と `scrape_config` を更新する。
- `NewsSiteUpdate.reanalyze` は既定で `false` とし、`true` の場合はURLが変わっていなくてもLLM再解析と抽出テストを実行し、成功時だけ `scrape_config` を更新する。

## レスポンススキーマ

| Schema                      | Fields                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------ |
| `BookmarkResponse`          | `id`, `url`, `title`, `description`, `folder_id`, `is_favorite`, `tags`, `created_at`, `updated_at` |
| `BookmarkListResponse`      | `items`, `total`, `page`, `per_page`, `total_pages`                                  |
| `RSSFeedResponse`           | `id`, `url`, `title`, `description`, `notify_webhook_enabled`, `webhook_ids`, `created_at`, `updated_at` |
| `RSSFeedListResponse`       | `items`, `total`, `page`, `per_page`, `total_pages`                                  |
| `RSSFeedArticleResponse`    | `id`, `feed_id`, `url`, `title`, `published`, `created_at`                           |
| `RSSFeedArticleListResponse`| `items`, `total`, `page`, `per_page`, `total_pages`                                  |
| `RSSFeedExecuteResponse`    | `feed_id`, `title`, `delivered`, `delivered_count`, `message`                         |
| `SettingsWebhookResponse`   | `id`, `name`, `webhook_url`, `enabled`, `created_at`, `updated_at`                   |
| `SettingsWebhookListResponse` | `items`                                                                            |
| `SettingsWebhookPingResponse` | `pong`                                                                             |
| `SettingsRssExecutionResponse` | `enabled`                                                                          |
| `SettingsRssWebhookNotificationResponse` | `enabled`                                                               |
| `LLMSettingsResponse`       | `provider`, `base_url`, `api_key_configured`, `model`                              |
| `NewsSiteResponse`          | `id`, `url`, `title`, `description`, `notify_webhook_enabled`, `webhook_ids`, `created_at`, `updated_at` |
| `NewsSiteListResponse`      | `items`, `total`, `page`, `per_page`, `total_pages`                                |
| `NewsSiteArticleResponse`   | `id`, `site_id`, `url`, `title`, `published`, `created_at`                         |
| `NewsSiteArticleListResponse` | `items`, `total`, `page`, `per_page`, `total_pages`                              |
| `NewsSiteExecuteResponse`   | `site_id`, `title`, `delivered`, `delivered_count`, `message`                       |
| `FolderResponse`            | `id`, `name`, `description`, `created_at`                                             |
| `TagResponse`               | `id`, `name`, `description`                                                          |
| `DashboardMetricsResponse`   | `bookmarks_total`, `folders_total`, `tags_total`, `favorites_total`, `rss_feeds_total`, `news_sites_total` |
| `ErrorResponse`             | `detail`                                                                             |

## 制約

- `bookmarks.url` は HTTP/HTTPS URL のみ受け付ける
- `rss_feeds.url` は HTTP/HTTPS URL のみ受け付ける
- `bookmarks.title` は必須
- `rss_feeds.title` は必須
- `rss_webhook_notification_enabled` は RSS 定期実行時の webhook 通知全体可否を表す
- `rss_webhook_notification_enabled` の既定値は `false` である
- `rss_feeds.notify_webhook_enabled` は batch による RSS 定期実行時の webhook 通知可否を表す
- `rss_feeds.notify_webhook_enabled` の既定値は `true` である
- `rss_feed_webhooks` は RSS フィードごとの通知先 webhook 選択を保持する
- `rss_feed_webhooks` に選択がない RSS フィードは全 webhook へ通知し、選択がある場合は選択した webhook のみへ通知する
- `rss_feed_webhooks` の `webhook_ids` は重複を 422 で拒否し、存在しない webhook ID は 404 を返す
- webhook または RSS フィード削除時は `rss_feed_webhooks` を連動削除する
- `folders.name` と `tags.name` は重複を許可しない
- `bookmarks.url` は一意である
- `rss_feeds.url` は一意である
- `bookmarks.folder_id` は存在しないフォルダを参照できない
- フォルダ削除時は関連ブックマークの `folder_id` を `NULL` にする
- ブックマークまたはタグ削除時は `bookmark_tags` を連動削除する
- SQLite の外部キー制約は `PRAGMA foreign_keys = ON` で有効化する
- DB 障害は 500 として返す
- `settings/webhooks` は Discord、Slack、または Microsoft Teams webhook URL を識別用の名前付きで複数登録する
- webhook 通知の記事タイトルは 256 文字、summary は 300 文字に切り詰める（Discord の embed 上限と Slack の block text 上限を満たすため）
- `webhook_endpoints.name` は必須で、空白のみの名前は 422 を返す
- `webhook_endpoints.url` は一意である
- `webhook_endpoints.enabled` の既定値は `true` で、無効なURLはRSS・Atom・custom newsの通知先から除外する
- webhook一覧は無効なURLも返し、`PATCH /settings/webhooks/{id}` で有効状態を更新する
- Microsoft Teams webhook は Adaptive Card 形式で疎通確認とRSS・custom news通知を送信し、記事タイトルを箇条書きのリンクとして表示する。記事間は罫線ではなく余白で区切り、個別の遷移ボタンは設けない
- `settings/webhook/ping` は送信前確認用の疎通確認 API である
- `settings/rss-execution` は RSS 定期実行フラグを保存する
- `settings/rss-webhook-notification` は RSS 定期実行時の webhook 通知可否を保存する
- `settings/webhook-summary` は全 webhook 通知に記事サマリーを含めるかを保存し、未設定時は有効として扱う
- `rss_feed_articles.url` は同一 feed 内で一意である
- LLM provider は `ollama`、`vllm`、`openai`（OpenAI 互換）のいずれかである
- LLM 設定は接続・model・credential を使った chat completion 成功後だけ保存する
- LLM API key は `app_settings` に保存するが API レスポンスには含めず、`api_key_configured` のみ返す
- custom news site 登録には保存済み LLM 設定が必要で、未設定時は 400 を返す
- custom news site 登録は HTML 取得、LLM selector 生成、実抽出テストの順に行う。記事が 0 件なら取得済み HTML と selector の item/title/link 一致件数を使って LLM 解析を 1 回だけ再試行し、再度 0 件または同一 selector なら 422 を返す
- custom news article の公開日は ISO/RFC 形式または `YYYY.MM.DD` を正規化し、保存済みの解析不能値は警告ログを出してレスポンス上 `null` とする
- custom news site 登録エラーは失敗段階と reference ID を返し、対象 site の 401/403 は認証または自動取得拒否として区別する
- LLM upstream の 401/403、404、429、400/413/422、5xx は原因別の利用者向けメッセージへ写像する
- 診断 log は reference ID、provider、model、query を除いた対象 URL、upstream status、HTML 文字数または最大 500 文字の response preview を記録し、API key と HTML 本文全体は記録しない
- `news_sites.url` は一意で、`scrape_config` は batch でも再利用できる JSON として保存する
- `news_site_articles.url` は同一 site 内で一意である
- `news_site_webhooks` の選択がない site は全 webhook、選択がある site は選択先だけへ通知する
- custom news site 手動実行は 1 件以上の webhook 成功後だけ `news_site_articles` を記録する

## 実装上の補足

- API は lifespan の開始時に `db/migrations` の未適用 migration を実行し、`schema_migrations` へ適用済みバージョンを記録する。
- API 起動時の migration 適用は冪等で、Docker 起動時に先行する dbmate と同じ適用履歴を共有する。
- `/bookmarks` の一覧は `folder_id`、`tag_id`、`q`、`is_favorite`、`sort`、`page`、`per_page` を受け付ける
- `/bookmarks` の `sort` は `id`、`url`、`title`、`description`、`folder_id`、`is_favorite`、`created_at`、`updated_at` を受け付ける
- `/bookmarks` の `sort` は複数指定でき、左から右へ優先度が高い
- `/bookmarks` の `sort` に存在しない項目が指定された場合は 422 を返す
- `/bookmarks/{id}` は詳細取得と更新対象を兼ねる
- `GET /folders/{id}` は単一フォルダを ID で取得する
- `GET /tags/{id}` は単一タグを ID で取得する
- `DELETE /bookmarks` は `id`、`url`、`title`、`description`、`folder_id`、`is_favorite` の任意組み合わせで対象ブックマークを特定する
- `DELETE /bookmarks` は指定した条件を AND で評価する
- `DELETE /bookmarks` は条件未指定時に 422 を返す
- `PATCH /bookmarks/by-url` は URL で対象ブックマークを特定する
- `PATCH /folders/{id}` と `PATCH /tags/{id}` は partial update として `name` の省略を許可する
- `/bookmarks/{id}/tags` はタグ付与、`DELETE /bookmarks/{id}/tags/{tag_id}` は解除を担当する
- `/metrics/dashboard` はブックマーク、フォルダ、タグ、お気に入り、RSS フィード、custom news site の総数を返す
- `/rss-feeds` は RSS フィードの CRUD を担当する
- `/rss-feeds/{id}/articles` は保存済み RSS 記事を返す
- `/rss-feeds/{id}/articles` は `q`、`published_from`、`published_to`、`page`、`per_page` を受け付ける
- `GET /settings/webhooks` は登録済み webhook の一覧を返す
- `POST /settings/webhooks` は名前付きの webhook URL を登録し、URL 重複時は 409 を返す
- `DELETE /settings/webhooks/{id}` は登録済み webhook を削除する
- `POST /settings/webhook/ping` は webhook 到達確認を行う
- `GET /settings/rss-execution` は RSS 定期実行の現在値を返す
- `PUT /settings/rss-execution` は RSS 定期実行の有効/無効を更新する
- `GET /settings/rss-webhook-notification` は RSS 定期実行時の webhook 通知可否の現在値を返す
- `PUT /settings/rss-webhook-notification` は RSS 定期実行時の webhook 通知可否を更新する
- `POST /rss-feeds/{id}/execute` は API プロセスが RSS を実行し、登録済みの全 webhook に通知する
- `POST /rss-feeds/{id}/execute` は webhook URL 未設定時に 400 を返す
- `POST /rss-feeds/{id}/execute` は全 webhook が失敗した場合に 502 を返し、1 件でも成功した場合は `delivered_count` に成功件数を含めて返す
- `POST /rss-feeds/{id}/execute` は新規記事がない場合も `delivered: true` を返し、`message` に "No new articles found." を含める
- RSS 手動実行の通知送信と `rss_feed_articles` への送信済み記録は API が担当する
- RSS 手動実行は `rss_feeds.notify_webhook_enabled` の値に関わらず webhook 通知を行う
- `batch` は RSS 定期実行が有効な場合だけ巡回し、`rss_feeds.notify_webhook_enabled` が有効な RSS フィードについて未送信記事の通知と `rss_feed_articles` への送信済み記録を担当する
- `batch` は `rss_feed_articles` の `url` を参照して、既に送信済みの記事を webhook 対象から除外する
- `batch` は webhook 送信成功後に `rss_feed_articles` へ記事を追記する
- `/settings/llm` は LLM 設定取得・疎通確認付き保存・削除を担当し、`/settings/llm/test` は保存せず接続を確認する
- `/news-sites` は custom news site の CRUD、`/{id}/articles` は記事履歴、`/{id}/execute` は手動 scrape と通知を担当する
- `batch` は保存済み `news_sites.scrape_config` で custom news site も巡回し、成功後に `news_site_articles` へ記録する
- `BookmarkListResponse.total_pages` はクライアントのページング UI が使えるように返す
