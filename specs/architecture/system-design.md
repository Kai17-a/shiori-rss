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
| GET | `/dashboard` | リクエスト時点から直近24時間のホームサマリーと記事一覧（`limit` は1〜100件） |
| POST/GET | `/rss-feeds` | フィード作成・一覧 |
| GET/PATCH/DELETE | `/rss-feeds/{id}` | フィード詳細・更新・削除 |
| GET/PUT/DELETE | `/rss-feeds/{id}/icon` | アップロードアイコンの取得・設定・削除 |
| GET | `/rss-feeds/{id}/articles` | 記事履歴 |
| POST | `/rss-feeds/{id}/execute` | 手動実行 |
| POST/GET | `/news-sites` | LLMカスタムRSS作成・一覧 |
| GET/PATCH/DELETE | `/news-sites/{id}` | カスタムRSS詳細・更新・削除 |
| GET/PUT/DELETE | `/news-sites/{id}/icon` | アップロードアイコンの取得・設定・削除 |
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
| GET/PUT | `/settings/ai-article-analysis` | AI記事事前解析の有効化と上限設定 |
| POST | `/settings/ai-article-analysis/execute` | 定期実行設定に依存しないAI記事解析の手動実行 |
| POST | `/ai/chat` | 保存済み記事の横断検索と根拠付きLLM回答 |
| POST | `/ai/chat/stream` | 出典とLLM回答差分をNDJSONで逐次返すAsk AI |
| GET | `/ai/article-analyses` | 保存済みAI記事解析データの検索・絞り込み・ページング一覧 |

## Ask AI フロー

1. LLMが質問を検索キーワード、公開期間、通常RSS・カスタムRSSの種別へ変換する。
2. SQLite FTS5の三文字トークナイザーで、両記事テーブルと解析済みAIメタデータから同期された検索インデックスを検索する。
3. 一致しない場合は、質問文中の略語・製品名を含む全キーワードの部分一致へ自動的に広げる。それでも一致せず期間指定がある場合は、期間を解除して再検索する。
4. 上位候補の記事タイトル、保存済みサマリー、利用可能なAI要約・要点・トピック、出典情報をLLMへ渡す。
5. LLMは候補の関連性を判断し、参照番号付きで回答する。
6. APIは回答と候補記事のURLを返し、画面は出典リンクを表示する。
7. ストリーミングAPIは回答本文をLLMから受信した単位で逐次転送し、回答完了後に本文で実際に引用された出典だけを返す。画面はNuxt UI Chatのstreaming状態と自動スクロールを使用する。

## バッチフロー

1. 定期実行設定を確認する。
2. RSS フィードを読み、Webhook設定の有無に関係なく巡回する。
3. フィードを取得し RSS / Atom を解析する。
4. `rss_feed_articles` に存在しない記事を未通知として保存する。
5. 通知が有効で送信先がある場合、保存済みの未通知記事を送る。DiscordではフィードのアイコンURLをWebhookの `avatar_url` に使う。
6. 少なくとも1つの送信先で成功した記事を通知済みに更新する。
7. AI記事解析が有効なら、対象期間内の未解析・更新済み記事を上限件数までLLMで解析する。
8. 利用量を呼び出し単位で記録し、1日のトークン上限に達する前に解析を停止する。
9. 手動実行では定期解析の有効・無効だけを無視し、同じ件数、対象期間、日次トークン上限と再解析判定を適用する。

定期巡回の対象は通常RSSだけであり、カスタムRSSの取得はAPIの手動実行が担当する。通常RSSの手動実行もAPIが担当し、自動通知の全体設定とフィード別設定にかかわらず、有効な選択先または有効な全送信先へ未通知記事を送る。
