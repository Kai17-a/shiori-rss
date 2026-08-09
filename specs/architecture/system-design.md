# RSS アプリ技術設計

## 構成

- `frontend/`: Nuxt 4 SPA。RSS フィード、LLMカスタムRSS、記事履歴、Webhook 設定を提供する。
- `api/`: FastAPI。RSS、LLMカスタムRSS、Webhook、LLM接続設定の REST API を提供する。
- `batch/`: Rust。SQLite から有効な RSS フィードを読み、定期巡回と Webhook 通知を行う。
- `db/`: dbmate の migration と現在の SQLite schema を管理する。

ブラウザ拡張とブックマーク管理は構成に含めない。HTML取得はLLMカスタムRSSのセレクタ生成・記事抽出に限定する。

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック |
| GET | `/dashboard` | 指定日のホームサマリーと記事一覧 |
| POST/GET | `/rss-feeds` | フィード作成・一覧 |
| GET/PATCH/DELETE | `/rss-feeds/{id}` | フィード詳細・更新・削除 |
| GET | `/rss-feeds/{id}/articles` | 記事履歴 |
| POST | `/rss-feeds/{id}/execute` | 手動実行 |
| POST/GET | `/news-sites` | LLMカスタムRSS作成・一覧 |
| GET/PATCH/DELETE | `/news-sites/{id}` | カスタムRSS詳細・更新・削除 |
| GET | `/news-sites/{id}/articles` | カスタムRSS記事履歴 |
| POST | `/news-sites/{id}/execute` | カスタムRSS手動取得 |
| GET/POST | `/settings/webhooks` | Webhook 一覧・作成 |
| PATCH/DELETE | `/settings/webhooks/{id}` | Webhook 有効化・削除 |
| POST | `/settings/webhook/ping` | 疎通確認 |
| GET/PUT | `/settings/rss-execution` | 定期実行設定 |
| GET/PUT | `/settings/rss-webhook-notification` | 定期通知設定 |
| GET/PUT | `/settings/webhook-summary` | 概要通知設定 |
| GET/PUT/DELETE | `/settings/llm` | LLM接続設定の取得・検証付き保存・削除 |
| POST | `/settings/llm/test` | LLM疎通テスト |
| POST | `/ai/chat` | 保存済み記事の横断検索と根拠付きLLM回答 |

## Ask AI フロー

1. LLMが質問を検索キーワード、公開期間、通常RSS・カスタムRSSの種別へ変換する。
2. SQLite FTS5の三文字トークナイザーで、両記事テーブルから同期された検索インデックスを検索する。
3. 一致しない場合は、質問文中の略語・製品名を含む全キーワードの部分一致へ自動的に広げる。それでも一致せず期間指定がある場合は、期間を解除して再検索する。
4. 上位候補の記事タイトル、保存済みサマリー、出典情報をLLMへ渡す。
5. LLMは候補の関連性を判断し、参照番号付きで回答する。
6. APIは回答と候補記事のURLを返し、画面は出典リンクを表示する。

## バッチフロー

1. 定期実行設定を確認する。
2. RSS フィードを読み、Webhook設定の有無に関係なく巡回する。
3. フィードを取得し RSS / Atom を解析する。
4. `rss_feed_articles` に存在しない記事を未通知として保存する。
5. 通知が有効で送信先がある場合、保存済みの未通知記事を送る。
6. 少なくとも1つの送信先で成功した記事を通知済みに更新する。
