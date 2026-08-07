# フロー

`batch` は CLI として起動される処理であり、Web アプリのルートや HTTP API は提供しない。

コンテナ起動時は `render-scheduler.sh` が `RSS_CRON_SCHEDULE`（既定値 `0 * * * *`）と batch コマンドから Supercronic の crontab を生成する。時間帯や曜日は cron 式で制限でき、評価するタイムゾーンは `TZ` で指定する。不正な複数行または空の設定ではコンテナを起動しない。

## 起動

1. `main.rs` が `database_path()` で DB パスを決定する
2. `rusqlite::Connection::open(...)` で SQLite DB を開く
3. `run_batch(&conn)` を async 実行する

## 実行フロー

1. `rss_feeds` と `news_sites` から巡回対象を取得する
2. `app_settings` の `rss_periodic_execution_enabled` を確認する
3. RSS フィードと custom news site がともに 0 件の場合は成功扱いで終了する
4. RSS 定期実行が無効な場合は成功扱いで終了する
5. `app_settings` の `rss_webhook_notification_enabled` を確認する
6. RSS webhook 通知が無効な場合は成功扱いで終了する
7. `webhook_endpoints` から有効な webhook URL を取得する
8. 有効な webhook URL が 1 件もない場合は標準エラーへ出力して成功扱いで終了する
9. フィードごとに RSS URL を取得してRSSまたはAtomフィードとして解析する
10. `rss_feed_articles` から送信済み URL を読み込む
11. RSS item の URL が送信済みでなければ通知対象に追加する
12. 通知対象がないフィードはスキップする
13. フィードに通知先 webhook が選択されている場合は選択先のみ、未選択の場合は登録済みの全 webhook へ payload を送信する
14. 1 件でも webhook 送信に成功した場合に `rss_feed_articles` へ送信済み記事を追記する
15. custom news site ごとに URL の HTML と `scrape_config` を読み、CSS selector で最大 100 件の記事を抽出する
16. `news_site_articles` の URL で既通知記事を除外し、通知先選択を適用して webhook へ送信する
17. 1 件でも webhook 送信に成功した場合に `news_site_articles` へ送信済み記事を追記する

RSS 取得と webhook の各送信試行には10秒のタイムアウトを適用し、応答しない外部サービスでbatch全体を無期限に停止させない。

## DB 依存

| Table | Purpose |
| ----- | ------- |
| `app_settings` | `rss_periodic_execution_enabled`、`rss_webhook_notification_enabled` を読む |
| `webhook_endpoints` | 有効な通知先 webhook URL を読む |
| `rss_feeds` | 巡回対象 RSS フィードを読む |
| `rss_feed_webhooks` | フィードごとの通知先 webhook 選択を読む |
| `rss_feed_articles` | 送信済み記事 URL の読み込みと送信成功後の記録を行う |
| `news_sites` | custom news site URL と LLM 生成済み `scrape_config` を読む |
| `news_site_webhooks` | site ごとの通知先 webhook 選択を読む |
| `news_site_articles` | scraped article の送信済み URL を読み書きする |

## webhook 送信

- payload は Discord では `username`、`content`、`embeds`、Slack では Block Kit、Microsoft Teams では Adaptive Card を含む JSON として送信する
- `content` はフィードタイトルと新着件数を含む
- 各 embed は記事タイトル、URL、summary を含む
- embed は 1 リクエストあたり最大 10 件、または概算 6000 文字以内になるように分割する
- 接続エラー、HTTP 429、HTTP 5xx は最大 3 回までリトライする
- webhook が 4xx または 5xx を返した場合、その webhook への送信は失敗扱いとし、他の webhook への送信を続ける
- すべての webhook が失敗した場合、そのフィードは失敗扱いでスキップする

## 失敗時の扱い

- DB を開けない場合は起動全体が失敗する
- 巡回対象取得や設定取得に失敗した場合は `run_batch` がエラーを返す
- 個別フィードまたは custom news site の URL parse、取得、body 読み込み、解析、送信済み URL 読み込み、webhook 送信、送信済み記事記録の失敗は標準エラーへ出力し、その対象だけをスキップする
- 個別フィードの失敗では他フィードの処理を止めない
