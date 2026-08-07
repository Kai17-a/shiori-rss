# API 仕様

FastAPI は `/health`、`/rss-feeds`、`/settings` のルートだけを公開する。

- RSS feed: 作成、一覧、詳細、更新、削除、記事履歴、手動実行
- Settings: Webhook CRUD・疎通確認、定期実行、定期通知、記事概要の設定
- エラー: `{"detail": ...}`。入力不正は 422、未検出は 404、重複は 409、外部通知失敗は 502 とする。
- 一覧: `items`, `total`, `page`, `per_page`, `total_pages` を返す。

詳細な利用者要件は [product requirements](../../product/requirements.md)、ルート一覧は [system design](../../architecture/system-design.md) を参照する。
