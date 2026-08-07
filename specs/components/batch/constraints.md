# 制約

## 実行条件

- `batch` は API サーバーとは別プロセスとして実行する
- `RSS_CRON_SCHEDULE` 未指定時は `0 * * * *` として毎時 0 分に実行する
- `RSS_CRON_SCHEDULE` は単一の Supercronic 互換 cron 式とし、改行または空値を拒否する
- 実行時刻のタイムゾーンはコンテナの `TZ` に従う
- `DATABASE_URL` は SQLite DB ファイルパスとして扱う
- `DATABASE_URL` 未指定時は `data/data.db` を使う
- DB スキーマは API と dbmate migration が用意したものを前提とする
- `batch` 自身は migration を適用しない

## 設定

- `rss_periodic_execution_enabled` が無効な場合、RSS 巡回は行わない
- `rss_webhook_notification_enabled` が無効な場合、RSS 巡回と webhook 通知は行わない
- `webhook_endpoints` に有効な webhook URL が 1 件もない場合、RSS 巡回と webhook 通知は行わない
- フィード単位の `rss_feeds.notify_webhook_enabled` が無効な RSS フィードは通知対象にしない
- フィードに通知先 webhook の選択がある場合は選択した webhook のみに送信し、選択がない場合は全 webhook に送信する
- `news_sites.notify_webhook_enabled` が無効な custom news site は通知対象にしない
- custom news site に通知先選択がある場合は選択先のみ、選択がない場合は全 webhook に送信する
- 選択された webhook が 1 件も存在しないフィードはスキップする

## RSS と記事記録

- RSS URL は `reqwest::Url::parse` で解釈できる必要がある
- RSS 取得は10秒でタイムアウトし、当該フィードだけをスキップする
- 取得結果は `feed-rs` でRSSまたはAtomフィードとして解析できる必要がある
- item の `link` がない場合は `"(no link)"` を URL として扱う
- item の `title` がない場合は `"(no title)"` をタイトルとして扱う
- published はRSSの `pubDate` またはAtomの `published`、`updated` から取得してRFC 3339へ正規化し、いずれもない場合は `"(no published date)"` として扱う
- summary はRSS・Atomのsummary相当フィールド、contentの順で採用し、どちらもない場合は `"(no summary)"` とする
- 送信済み判定は `rss_feed_articles.url` で行う
- 送信済み記事の記録は `INSERT OR IGNORE` を使い、重複 URL を二重登録しない

## Custom news site と記事記録

- batch は LLM を呼び出さず、登録時に保存された `news_sites.scrape_config` の CSS selector を再利用する
- `scrape_config` は item、title、link の selector と link attribute を必須とし、published と summary selector は任意とする
- 相対リンクは site URL を基準に HTTP/HTTPS の絶対 URL へ解決する
- 1 回の巡回で抽出する記事は先頭 100 件までとする
- 送信済み判定は `news_site_articles.url` で行い、1 件以上の webhook 成功後に `INSERT OR IGNORE` で記録する
- scraped article の公開日は ISO/RFC 形式または `YYYY.MM.DD` を正規化し、解析不能な値は `NULL` として記録する

## 後方互換

- `rss_feeds.notify_webhook_enabled` 列がない DB では、全 RSS フィードを通知対象として扱う
- `rss_feed_articles.published` 列がない DB では、`published` を除外して送信済み記事を記録する
- `webhook_endpoints` テーブルがない DB では、`app_settings.default_webhook_url` を通知先として扱う
- `webhook_endpoints.enabled` 列がない DB では、登録済みの全 webhook URL を有効として扱う
- `rss_feed_webhooks` テーブルがない DB では、全 RSS フィードを通知先未選択（全 webhook 通知）として扱う

## webhook

- batch は webhook URL から Discord、Slack、Microsoft Teams を識別する
- `webhook_include_summary_enabled` が `0` の場合は RSS と custom news site の通知 payload から記事サマリーを除外し、設定行がない場合は含める
- Discord には `username`、`content`、`embeds`、Slack には Block Kit、Microsoft Teams には Adaptive Card 形式を送る
- Microsoft Teams の記事タイトルは箇条書きの Markdown link とし、記事間は罫線ではなく余白で区切り、`Action.OpenUrl` ボタンは送らない
- 記事タイトルは 256 文字、summary は 300 文字に切り詰めてから payload に載せる（Discord の embed 上限と Slack の block text 上限を満たすため）
- embed のチャンクサイズ見積もりには切り詰め後の文字数を使う
- webhook の各送信試行は10秒でタイムアウトする
- webhook の接続エラー、HTTP 429、HTTP 5xx は最大 3 回リトライする
- リトライ間隔は 500ms とする
- リトライ後の HTTP 429/5xx と、それ以外の HTTP 4xx は当該 webhook 単位の失敗として扱う
- 有効な webhook へ送信し、1 件でも成功すれば当該フィードの記事を送信済みとして記録する
- すべての webhook が失敗したフィードはスキップする
