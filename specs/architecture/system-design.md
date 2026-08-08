# RSS アプリ技術設計

## 構成

- `frontend/`: Nuxt 4 SPA。RSS フィード、記事履歴、Webhook 設定を提供する。
- `api/`: FastAPI。RSS、Webhook、LLM接続設定の REST API を提供する。
- `batch/`: Rust。SQLite から有効な RSS フィードを読み、定期巡回と Webhook 通知を行う。
- `db/`: dbmate の migration と現在の SQLite schema を管理する。

ブラウザ拡張、ブックマーク管理、HTML スクレイピングは構成に含めない。

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック |
| POST/GET | `/rss-feeds` | フィード作成・一覧 |
| GET/PATCH/DELETE | `/rss-feeds/{id}` | フィード詳細・更新・削除 |
| GET | `/rss-feeds/{id}/articles` | 記事履歴 |
| POST | `/rss-feeds/{id}/execute` | 手動実行 |
| GET/POST | `/settings/webhooks` | Webhook 一覧・作成 |
| PATCH/DELETE | `/settings/webhooks/{id}` | Webhook 有効化・削除 |
| POST | `/settings/webhook/ping` | 疎通確認 |
| GET/PUT | `/settings/rss-execution` | 定期実行設定 |
| GET/PUT | `/settings/rss-webhook-notification` | 定期通知設定 |
| GET/PUT | `/settings/webhook-summary` | 概要通知設定 |
| GET/PUT/DELETE | `/settings/llm` | LLM接続設定の取得・検証付き保存・削除 |
| POST | `/settings/llm/test` | LLM疎通テスト |

## バッチフロー

1. 定期実行設定を確認する。
2. RSS フィードを読み、Webhook設定の有無に関係なく巡回する。
3. フィードを取得し RSS / Atom を解析する。
4. `rss_feed_articles` に存在しない記事を未通知として保存する。
5. 通知が有効で送信先がある場合、保存済みの未通知記事を送る。
6. 少なくとも1つの送信先で成功した記事を通知済みに更新する。
