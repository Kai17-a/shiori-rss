# 概要

`batch/` は、SQLite に保存された RSS フィードと custom news site を定期巡回し、新着記事を webhook へ通知する Rust 製バッチである。
API サーバーとは別プロセスとして動作し、HTTP ルートは持たない。

## 主な特徴

- `DATABASE_URL` で指定された SQLite DB を開く
- `DATABASE_URL` 未指定時は `data/data.db` を使う
- コンテナは `RSS_CRON_SCHEDULE` の cron 式で batch を起動し、未指定時は毎時 0 分に実行する
- cron のタイムゾーンはコンテナの `TZ` で指定する
- `app_settings` から RSS 定期実行、webhook 通知、記事サマリー包含の全体設定を読む
- `webhook_endpoints` から有効な通知先 webhook URL を読む
- `rss_feeds.notify_webhook_enabled = 1` の RSS フィードのみを巡回対象にする
- `rss_feed_webhooks` でフィードごとに選択された通知先がある場合は、その webhook のみへ送信する
- `news_sites.notify_webhook_enabled = 1` の custom news site を巡回し、保存済み JSON の CSS selector で HTML を解析する
- `news_site_webhooks` の選択がある場合は選択先のみ、未選択時は全 webhook へ送信する
- `news_site_articles` の URL で既通知記事を除外し、送信成功後に記録する
- RSS URL を取得し、RSSまたはAtomフィードとして解析する
- `rss_feed_articles` に保存済みの URL を読み、既送信記事を除外する
- 新着記事を Discord、Slack、または Microsoft Teams 向けの webhook payload として有効な webhook へ送信する
- 1 件でも webhook 送信に成功した後に `rss_feed_articles` へ送信済み記事を記録する
- フィード単位の失敗はログ出力してスキップし、他フィードの処理を継続する

## 主要ファイル

- [エントリポイント](../../../batch/src/main.rs)
- [ライブラリ公開](../../../batch/src/lib.rs)
- [DB アクセス](../../../batch/src/db.rs)
- [実行フロー](../../../batch/src/runner.rs)
- [webhook 送信と記事記録](../../../batch/src/webhook.rs)
- [Custom news scraping](../../../batch/src/news.rs)
- [Cargo 設定](../../../batch/Cargo.toml)

## 技術スタック

- Rust 2024 edition
- `tokio` による async 実行
- `rusqlite` による SQLite アクセス
- `reqwest` による RSS と webhook の HTTP 通信
- `feed-rs` crate によるRSS・Atomフィード解析
- `scraper` crate による HTML/CSS selector 解析
- `serde_json` による webhook payload 構築
