# Batch 仕様

Rust batch は RSS / Atom フィードだけを定期巡回する。

- SQLite の `app_settings`、`rss_feeds`、`rss_feed_webhooks`、`webhook_endpoints`、`rss_feed_articles` を読む。
- 定期実行が無効なら終了する。定期通知が無効でも取得と未通知記事の保存は行う。
- 取得と送信はタイムアウトを設け、Webhook の 429 / 5xx を最大3回試行する。
- 未通知記事をフィードごとの選択先へ送り、選択がなければ有効な全送信先へ送る。
- Webhookがなくても記事を未通知として記録し、1件以上の送信成功後だけ通知済みに更新する。
- RSS記事の公開日時はXMLの `pubDate` / `published` を優先し、元のUTCオフセットを保ったISO 8601形式で保存する。公開日時がないAtom記事では `updated` を使用する。
