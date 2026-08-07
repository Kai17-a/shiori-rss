# Batch 仕様

Rust batch は RSS / Atom フィードだけを定期巡回する。

- SQLite の `app_settings`、`rss_feeds`、`rss_feed_webhooks`、`webhook_endpoints`、`rss_feed_articles` を読む。
- 定期実行または定期通知が無効なら終了する。
- 取得と送信はタイムアウトを設け、Webhook の 429 / 5xx を最大3回試行する。
- 未通知記事をフィードごとの選択先へ送り、選択がなければ有効な全送信先へ送る。
- 1件以上の送信成功後だけ記事を記録し、重複通知を防ぐ。
