# 技術設計書: ブックマーク管理システム

## 概要

本ドキュメントは、ブックマーク管理システムの技術設計を定義する。
Python で API サーバーを実装し、SQLite をデータストアとして使用する。
加えて、Rust の `batch` で RSS と custom news site の定期巡回・webhook 通知を担当し、`browser_extension/` でブラウザからのブックマーク登録 UI を提供する。
ブックマーク・RSS フィード・custom news site・フォルダ・タグ・設定の CRUD と、LLM-assisted HTML scraping、Discord、Slack、Microsoft Teams webhook 通知を提供する。

### 技術スタック

- 言語: Python 3.13+
- Web フレームワーク: FastAPI
- バリデーション: Pydantic v2
- DB: SQLite（標準ライブラリ `sqlite3` を使用）
- テスト: pytest + hypothesis

---

## アーキテクチャ

### レイヤー構成

```
Client (HTTP)
    │
    ▼
┌─────────────────────────────┐
│  Router Layer (FastAPI)     │
│  api/routers/               │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Service Layer              │
│  api/services/              │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Repository Layer           │
│  api/repositories/          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  SQLite Database            │
└─────────────────────────────┘
```

### バッチ処理

```
SQLite Database
    │
    ▼
┌─────────────────────────────┐
│  Batch Job (Rust)           │
│  batch/                     │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Webhook                    │
└─────────────────────────────┘
```

- `batch` は定期実行が有効な場合だけ RSS フィードと custom news site を読み込み、未送信の記事だけを webhook に通知する
- `batch` は送信済み記事を `rss_feed_articles` に記録し、重複通知を避ける
- `batch` は webhook の接続エラー、HTTP 429、HTTP 5xx を最大 3 回までリトライし、最終失敗時は当該フィードをスキップして次へ進む
- `batch` の RSS 取得と webhook の各送信試行は10秒でタイムアウトする
- `batch` は API サーバーとは別プロセスとして動作し、HTTP ルートは持たない

### Chrome Extension

```
Active Browser Tab
    │
    ▼
┌─────────────────────────────┐
│  Chrome Extension Popup     │
│  browser_extension/         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  FastAPI HTTP API           │
└─────────────────────────────┘
```

- popup はアクティブタブの URL とタイトルを初期値として読み込む
- popup は API サーバー URL を `chrome.storage.local` に保存する
- popup は `/health` で API 疎通確認を行う
- popup は URL 検索で既存ブックマークを検出し、既存データをフォームへ反映する
- popup はフォルダとタグの候補を API から読み込み、関連付け付きでブックマークを保存する
- popup はブックマークの作成、更新、URL 指定削除を行う

### ディレクトリ構成

```
shiori-keeper/
├── api/
│   ├── main.py
│   ├── database.py
│   ├── model/
│   ├── routers/
│   ├── services/
│   └── repositories/
├── frontend/
├── browser_extension/
└── specs/
    ├── README.md
    ├── llm-reading-guide.md
    ├── product/
    ├── architecture/
    ├── components/
    │   ├── api/
    │   ├── frontend/
    │   ├── batch/
    │   └── browser-extension/
    └── quality/
        └── observations/
├── batch/
│   ├── Cargo.toml
│   └── src/
│       ├── db.rs
│       ├── lib.rs
│       ├── main.rs
│       └── webhook.rs
```

---

## API

### エンドポイント

| Method | Path                            | 説明                     |
| ------ | ------------------------------- | ------------------------ |
| POST   | `/bookmarks`                    | ブックマーク作成         |
| GET    | `/bookmarks`                    | ブックマーク一覧取得     |
| GET    | `/bookmarks/by-url`             | URL 指定ブックマーク取得 |
| GET    | `/bookmarks/{id}`               | ブックマーク詳細取得     |
| PATCH  | `/bookmarks/{id}`               | ブックマーク部分更新     |
| PATCH  | `/bookmarks/by-url`             | URL 指定ブックマーク更新 |
| DELETE | `/bookmarks`                    | 条件指定ブックマーク削除 |
| DELETE | `/bookmarks/by-url`             | URL 指定ブックマーク削除 |
| DELETE | `/bookmarks/{id}`               | ID 指定ブックマーク削除  |
| PATCH  | `/bookmarks/favorite`           | ブックマークのお気に入り状態更新 |
| POST   | `/bookmarks/{id}/tags`          | ブックマークへタグ付与   |
| DELETE | `/bookmarks/{id}/tags/{tag_id}` | ブックマークからタグ解除 |
| GET    | `/metrics/dashboard`            | ダッシュボード集計取得   |
| POST   | `/folders`                      | フォルダ作成             |
| GET    | `/folders`                      | フォルダ一覧取得         |
| GET    | `/folders/{id}`                 | フォルダ詳細取得         |
| PATCH  | `/folders/{id}`                 | フォルダ更新             |
| DELETE | `/folders/{id}`                 | フォルダ削除             |
| POST   | `/tags`                         | タグ作成                 |
| GET    | `/tags`                         | タグ一覧取得             |
| GET    | `/tags/{id}`                    | タグ詳細取得             |
| PATCH  | `/tags/{id}`                    | タグ更新                 |
| DELETE | `/tags/{id}`                    | タグ削除                 |
| PUT    | `/settings/webhook`             | webhook 設定             |
| GET    | `/settings/webhook`             | webhook 取得             |
| POST   | `/settings/webhook/ping`        | webhook 疎通確認         |
| GET    | `/settings/rss-execution`       | RSS 定期実行設定取得     |
| PUT    | `/settings/rss-execution`       | RSS 定期実行設定更新     |
| GET    | `/settings/rss-webhook-notification` | RSS 定期実行 webhook 通知設定取得 |
| PUT    | `/settings/rss-webhook-notification` | RSS 定期実行 webhook 通知設定更新 |
| POST   | `/rss-feeds`                    | RSS フィード作成         |
| GET    | `/rss-feeds`                    | RSS フィード一覧取得     |
| GET    | `/rss-feeds/{id}`               | RSS フィード詳細取得     |
| GET    | `/rss-feeds/{id}/articles`      | RSS フィード記事一覧取得 |
| PATCH  | `/rss-feeds/{id}`               | RSS フィード部分更新     |
| DELETE | `/rss-feeds/{id}`               | RSS フィード削除         |
| POST   | `/rss-feeds/{id}/execute`       | RSS 実行と webhook 通知  |
| GET/PUT/DELETE | `/settings/llm`        | LLM 設定の取得・疎通確認付き保存・削除 |
| POST   | `/settings/llm/test`            | LLM 疎通確認             |
| POST/GET | `/news-sites`                 | custom news site 作成・一覧 |
| GET/PATCH/DELETE | `/news-sites/{id}`    | custom news site 詳細・更新・削除 |
| GET    | `/news-sites/{id}/articles`     | scraped article 一覧     |
| POST   | `/news-sites/{id}/execute`      | HTML scrape と webhook 通知 |
| GET    | `/health`                       | ヘルスチェック           |

### レスポンス方針

- 正常系は各リソースの Pydantic モデルで返す
- 一覧取得は `items` / `total` / `page` / `per_page` / `total_pages` を含むページングレスポンスを返す
- `folders` と `tags` の一覧は配列で返す
- エラーは `{"detail": ...}` 形式を返す
- バリデーションエラーは FastAPI の標準形式を使う

---

## データモデル

DB の全体像は [DB 定義](./data-model.md) に Mermaid ER 図としても記載する。

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

CREATE UNIQUE INDEX idx_bookmarks_url_unique ON bookmarks(url);

CREATE TABLE IF NOT EXISTS rss_feeds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    description TEXT,
    notify_webhook_enabled INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_rss_feeds_url_unique ON rss_feeds(url);

CREATE TABLE IF NOT EXISTS rss_feed_articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id     INTEGER NOT NULL REFERENCES rss_feeds(id) ON DELETE CASCADE,
    url         TEXT    NOT NULL,
    title       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    published   DATETIME
);

CREATE UNIQUE INDEX idx_rss_feed_articles_feed_url_unique
  ON rss_feed_articles(feed_id, url);

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
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_webhook_endpoints_url_unique
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

### 設計上の決定

- `folders.id` は削除時に `bookmarks.folder_id` を `NULL` にする
- `bookmark_tags` はブックマーク・タグ削除時に連動削除する
- SQLite の外部キー制約は接続時に `PRAGMA foreign_keys = ON` で有効化する
- `bookmarks.url`、`rss_feeds.url`、`folders.name`、`tags.name` は DB 一意制約と事前チェックの両方で重複を防ぐ
- `app_settings` はアプリ全体設定のキーバリューストアとして扱う
- `app_settings` の `llm_*` key は provider、base URL、API key、model を保持し、API key はレスポンスへ返さない
- `webhook_endpoints` は RSS 通知先の webhook URL を識別用の名前付きで複数保持し、URL の一意制約で重複登録を防ぐ
- `webhook_endpoints.url` は Discord、Slack、または Microsoft Teams webhook URL だけを許可する
- `webhook_endpoints.name` は一覧表示で通知先を識別するためのラベルで、空白のみの名前は拒否する
- `rss_feed_webhooks` は RSS フィードごとの通知先 webhook 選択を保持し、選択がないフィードは全 webhook へ通知、選択があるフィードは選択先のみへ通知する
- webhook または RSS フィード削除時は `rss_feed_webhooks` を連動削除する
- `rss_periodic_execution_enabled` は RSS 定期実行の有効/無効を保持する
- `rss_webhook_notification_enabled` は RSS 定期実行時に webhook 通知を送るかを保持する
- `rss_feeds.notify_webhook_enabled` は batch による RSS 定期実行時に webhook 通知するかを保持する
- `rss_feeds.notify_webhook_enabled` の既定値は `1` である
- `rss_webhook_notification_enabled` の既定値は `0` である
- RSS 実行 API は `webhook_endpoints` 未登録時に 400 を返し、登録済みの全 webhook へ送信する
- RSS 手動実行の送信本体は API が担当する
- `batch` は RSS 定期実行が有効なときだけ RSS 巡回を行う
- `batch` は `rss_webhook_notification_enabled` が無効な場合、RSS 巡回自体を行わない
- `batch` は `rss_feeds.notify_webhook_enabled` が無効な RSS フィードを通知対象から除外する
- `batch` は `rss_feed_articles` を参照して既送信記事を除外し、送信成功後に同テーブルへ記録する
- custom news site 登録は LLM 設定必須で、HTML 取得、selector 生成、実抽出テストの成功後だけ `news_sites` へ保存する
- custom news site 解析失敗は全段階で共通 reference ID を使い、利用者向け error と、secret/HTML 全文を含まない server log を対応付ける
- API と batch は `news_sites.scrape_config` を共有し、`news_site_articles` で重複通知を防止する
- `batch` は webhook の接続エラー、HTTP 429、HTTP 5xx を最大 3 回までリトライし、失敗したフィードはスキップする

### Pydantic スキーマ

```python
class BookmarkCreate(BaseModel):
    url: AnyHttpUrl
    title: str
    description: str | None = None
    folder_id: int | None = None
    tag_ids: list[int] | None = None

class BookmarkUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    title: str | None = None
    description: str | None = None
    folder_id: int | None = None
    tag_ids: list[int] | None = None

class BookmarkFavoriteUpdate(BaseModel):
    bookmark_id: int
    is_favorite: bool

class FolderCreate(BaseModel):
    name: str
    description: str | None = None

class FolderUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class TagCreate(BaseModel):
    name: str
    description: str | None = None

class TagUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class TagAttach(BaseModel):
    tag_id: int

class RSSFeedCreate(BaseModel):
    url: AnyHttpUrl
    title: str
    description: str | None = None

class RSSFeedUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    title: str | None = None
    description: str | None = None

class SettingsWebhookUpdate(BaseModel):
    webhook_url: AnyHttpUrl

class SettingsWebhookPingRequest(BaseModel):
    webhook_url: str

class SettingsWebhookPingResponse(BaseModel):
    pong: bool

class SettingsRssExecutionUpdate(BaseModel):
    enabled: bool

class SettingsRssExecutionResponse(BaseModel):
    enabled: bool

class TagResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

class FolderResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime

class BookmarkResponse(BaseModel):
    id: int
    url: str
    title: str
    description: str | None
    folder_id: int | None
    is_favorite: bool
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime

class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class RSSFeedResponse(BaseModel):
    id: int
    url: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

class RSSFeedArticleResponse(BaseModel):
    id: int
    feed_id: int
    url: str
    title: str | None = None
    published: datetime | None = None
    created_at: datetime

class RSSFeedArticleListResponse(BaseModel):
    items: list[RSSFeedArticleResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class RSSFeedListResponse(BaseModel):
    items: list[RSSFeedResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class RSSFeedExecuteResponse(BaseModel):
    feed_id: int
    title: str
    webhook_url: str
    delivered: bool
    message: str | None = None

class DashboardMetricsResponse(BaseModel):
    bookmarks_total: int
    folders_total: int
    tags_total: int
    favorites_total: int
    rss_feeds_total: int
    news_sites_total: int
```

---

## 運用上の補足

- 未知の SQLite エラーは 500 に変換する
- アプリ起動時に初期化処理を実行する
- RSS 実行は実際の RSS/Atom フィード URL のみ許可する
- Webhook は Discord、Slack、Microsoft Teams に対応する
