# RSS アプリ技術設計

## 構成

- `frontend/`: Nuxt 4 SPA。RSS フィード、LLMカスタムRSS、記事履歴、GitHubリリース、Webhook 設定を提供する。
- `api/`: FastAPI。RSS、LLMカスタムRSS、GitHubリリース、Webhook、LLM接続設定の REST API を提供する。
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
| POST/GET | `/news-sites` | AI生成または手動CSSセレクタによるカスタムRSS作成・一覧 |
| GET/PATCH/DELETE | `/news-sites/{id}` | 設定方式とセレクタを含むカスタムRSS詳細・更新・削除 |
| GET/PUT/DELETE | `/news-sites/{id}/icon` | アップロードアイコンの取得・設定・削除 |
| GET | `/news-sites/{id}/articles` | カスタムRSS記事履歴 |
| POST | `/news-sites/{id}/execute` | カスタムRSS手動取得 |
| GET/POST | `/github-repositories` | GitHubリポジトリ一覧・登録と最新公開リリース取得 |
| POST | `/github-repositories/refresh` | 全登録リポジトリの最新公開リリースを更新 |
| DELETE | `/github-repositories/{id}` | GitHubリポジトリを削除 |
| GET/POST | `/settings/webhooks` | Webhook 一覧・作成 |
| PATCH/DELETE | `/settings/webhooks/{id}` | Webhook 有効化・削除 |
| POST | `/settings/webhook/ping` | 疎通確認 |
| GET/PUT | `/settings/rss-execution` | 定期実行設定 |
| GET/PUT | `/settings/rss-webhook-notification` | 定期通知設定 |
| GET/PUT | `/settings/webhook-summary` | 概要通知設定 |
| GET/PUT | `/settings/webhook-article-limit` | 1回のフィード実行で通知する最新記事数（1〜100件） |
| GET/PUT/DELETE | `/settings/llm` | LLM接続設定の取得・検証付き保存・削除 |
| POST | `/settings/llm/test` | LLM疎通テスト |
| GET/PUT | `/settings/ai-article-analysis` | AI記事事前解析の有効化と上限設定 |
| POST | `/settings/ai-article-analysis/execute` | 定期実行設定に依存しないAI記事解析の手動実行 |
| POST | `/settings/ai-article-analysis/cancel` | 実行中AI解析へ協調停止を要求 |
| DELETE | `/ai/article-analyses/failed` | 失敗したAI解析結果だけを削除 |
| GET | `/settings/ai-article-analysis/status` | 手動・定期AI解析の実行状態、記事進捗、現在の記事、トークン使用量 |
| POST | `/ai/chat` | 保存済み記事の横断検索と根拠付きLLM回答 |
| POST | `/ai/chat/stream` | 出典とLLM回答差分をNDJSONで逐次返すAsk AI |
| GET | `/ai/article-analyses` | 保存済みAI記事解析データの検索・絞り込み・ページング一覧 |

## Ask AI フロー

1. LLMが質問を原文キーワード、日英の対訳・略称・別名、公開期間、通常RSS・カスタムRSSの種別へ変換する。
2. SQLite FTS5の三文字トークナイザーで、両記事テーブルと解析済みAIメタデータから同期された検索インデックスを検索する。
3. 一致しない場合は、質問文中の略語・製品名を含む全キーワードの部分一致へ自動的に広げる。それでも一致せず期間指定がある場合は、期間を解除して再検索する。
4. タイトル・配信元、固有表現、キーワード、多言語aliases、本文・AI要約、固定大分類・要点の順に一致を重み付けし、上位候補のメタデータと出典情報をLLMへ渡す。
5. LLMは候補の関連性を判断する。一覧・検索要求では要求トピックを主題とする記事を選び、事実質問では回答材料になる記事を選ぶ。一覧要求に明記された4文字以上の製品・組織・サービス名が配信元、タイトル、本文、AIメタデータに完全一致する候補は、LLMの空判定だけでは除外しない。
6. APIは回答と候補記事のURLを返し、画面は出典リンクを表示する。
7. ストリーミングAPIは回答本文をLLMから受信した単位で逐次転送し、回答完了後に本文で実際に引用された出典だけを返す。画面はNuxt UI Chatのstreaming状態と自動スクロールを使用する。
8. 継続質問では直近の会話履歴と出典対応表を一時コンテキストとして使い、明示された出典番号を前回の記事へ解決する。会話はDBへ保存しない。

## バッチフロー

1. 定期実行設定を確認する。
2. RSS フィードを読み、Webhook設定の有無に関係なく巡回する。
3. フィードを取得し RSS / Atom を解析する。
4. `rss_feed_articles` に存在しない記事を未通知として保存する。
5. 通知が有効で送信先がある場合、保存済みの未通知記事を公開日時の新しい順に設定上限まで送る。送信成功後は同じバックログ全体を処理済みにして、上限から外れた古い記事を次回送らない。送信失敗時は未処理のまま最新記事から再試行する。DiscordではフィードのアイコンURLをWebhookの `avatar_url` に使う。
6. 少なくとも1つの送信先で成功した記事を通知済みに更新する。
7. AI記事解析が有効なら、対象期間内の未解析・更新済み記事を上限件数までLLMで解析する。
8. 利用量を呼び出し単位で記録し、1日のトークン上限に達する前に解析を停止する。
9. 手動実行では定期解析の有効・無効だけを無視し、同じ件数、対象期間、日次トークン上限と再解析判定を適用する。
10. 登録済みGitHubリポジトリの最新公開リリースを確認し、通知済みタグから更新があれば有効なWebhookへ通知する。

定期巡回の対象は通常RSSだけであり、カスタムRSSの取得はAPIの手動実行が担当する。通常RSSの手動実行もAPIが担当し、自動通知の全体設定とフィード別設定にかかわらず、有効な選択先または有効な全送信先へ未通知記事を送る。
