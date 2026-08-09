# API 仕様

FastAPI は `/health`、`/dashboard`、`/rss-feeds`、`/news-sites`、`/settings`、`/ai/chat` のルートを公開する。

- RSS feed: 作成、一覧、詳細、更新、削除、通知状態付き記事履歴、Webhookなしでも保存できる手動実行
- RSS記事の公開日時はXMLの `pubDate` / `published` を優先し、元のUTCオフセットを保ったISO 8601形式で保存・返却する。
- Dashboard: リクエスト受信時刻を基準に、通常RSS・カスタムRSSの件数、直近24時間の記事数、未通知数、直近24時間の記事を集約して返す
- Settings: Webhook CRUD・疎通確認、定期実行、定期通知、記事概要、デフォルトOFFのAI記事解析と利用上限の設定
- AI article analysis execution: `POST /settings/ai-article-analysis/execute` からRustバッチのAI解析専用モードを同期実行し、処理・成功・失敗・解析済みスキップ件数と日次上限到達状態を返す
- LLM settings: 接続情報の取得、実接続テスト後の保存、削除、保存前テスト
- Ask AI: 質問をLLMで検索条件へ変換し、FTS5で保存済み記事と解析済みAIメタデータを検索して、出典記事付きの回答を生成する。0件の場合は部分一致、期間解除の順に検索条件を自動で広げる。LLM未設定時は409を返す
- エラー: `{"detail": ...}`。入力不正は 422、未検出は 404、重複は 409、外部通知失敗は 502 とする。
- 一覧: `items`, `total`, `page`, `per_page`, `total_pages` を返す。

詳細な利用者要件は [product requirements](../../product/requirements.md)、ルート一覧は [system design](../../architecture/system-design.md) を参照する。
