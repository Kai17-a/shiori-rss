# API 仕様

FastAPI は `/health`、`/dashboard`、`/rss-feeds`、`/news-sites`、`/settings`、`/ai/chat` のルートを公開する。

- RSS feed: 作成、一覧、詳細、更新、削除、通知状態付き記事履歴、Webhookなしでも保存できる手動実行。手動実行は定期通知とフィード別の自動通知設定を参照せず、有効な送信先があれば未通知記事を送る
- Custom RSS: LLMによる作成・再解析、一覧、詳細、更新、削除、通知状態付き記事履歴、手動取得。定期巡回は行わない
- Feed icon: 通常RSS・Custom RSSの外部画像URLを作成・更新APIで受け付け、`/{id}/icon` のGET/PUT/DELETEでアップロード画像を配信・設定・削除する。アップロードはPNG・JPEG・GIF・WebP、最大1 MBとし、公開HTTP(S) URLを同時に保存する
- RSS記事の公開日時はXMLの `pubDate` / `published` を優先し、元のUTCオフセットを保ったISO 8601形式で保存・返却する。
- Dashboard: リクエスト受信時刻を基準に、通常RSS・カスタムRSSの件数、直近24時間の記事数、未通知数、直近24時間の記事を集約して返す。各記事は配信元の設定済みアイコンURLを `source_icon_url` として返す
- Settings: Webhook CRUD・疎通確認、定期実行、定期通知、記事概要、デフォルトOFFのAI記事解析と利用上限の設定
- AI article analysis execution: `POST /settings/ai-article-analysis/execute` からRustバッチのAI解析専用モードを同期実行し、処理・成功・失敗・解析済みスキップ件数と日次上限到達状態を返す
- AI article analysis status: `GET /settings/ai-article-analysis/status` はAPIプロセス内の手動実行ロックとSQLiteの有効なバッチロックを確認し、手動・定期のどちらかが実行中なら `running: true` を返す。バッチロックは開始時刻とプロセスIDを保持し、所有プロセスが存在しない場合は孤立ロックを削除する。APIから起動したプロセスの終了時にも成功・失敗を問わず、そのプロセス自身のロックだけを削除する。旧形式の開始時刻だけのロックは、実際のバッチプロセスが存在しない場合に孤立ロックとして削除する
- AI article analysis data: `GET /ai/article-analyses` は記事・配信元情報と解析済みの要約、要点、トピック、キーワード、固有表現、モデル、トークン数、状態、失敗内容を結合して返す。記事・配信元・AI要約の検索、通常RSS・Custom RSSの種別、成功・失敗状態、ページングで絞り込める
- ローカル開発では `mise run dev` がRustバッチをビルドして `SHIORI_FEED_BATCH_BIN` をAPIへ渡す。本番コンテナではPATH上のインストール済みバイナリを使用する。
- 手動AI解析のRust標準出力・標準エラーはAPIが行単位で `uvicorn.error` ログへ転送し、最終JSONだけをAPIレスポンスへ変換する。
- LLM settings: 接続情報の取得、実接続テスト後の保存、削除、保存前テスト
- Ask AI: 質問をLLMで検索条件へ変換し、FTS5で保存済み記事と解析済みAIメタデータを検索する。0件の場合は部分一致、期間解除の順に検索条件を自動で広げる。検索候補はLLMの構造化された関連性判定で絞り込み、直接関係する記事だけを回答生成へ渡す。一覧・検索要求は要求トピックを主題とする記事を対象とし、事実質問のような直接回答は要求しない。一覧要求に明記された4文字以上の固有フレーズが配信元、タイトル、本文、AIメタデータに完全一致する候補はLLMの空判定だけで除外しない。LLM未設定時は409を返す
- Ask AI streaming: `POST /ai/chat/stream` はNDJSONで回答差分を逐次返し、回答完了後に実際に引用した出典、続いて完了イベントを返す。エラー時はエラーイベントを返し、OllamaとOpenAI互換のストリーム形式を吸収する。検索候補のうち回答で引用されなかった記事は出典へ含めない
- エラー: `{"detail": ...}`。入力不正は 422、未検出は 404、重複は 409、外部通知失敗は 502 とする。
- 一覧: `items`, `total`, `page`, `per_page`, `total_pages` を返す。
- Webhook: Discord通知ではフィードの `icon_url` を `avatar_url` に設定する。Incoming Webhookでアイコンを上書きできないSlackとTeamsには追加しない。
- Microsoft Teams通知の記事リンクは、Adaptive CardのTextBlock内でMarkdownの `- [title](url)` リストとして送る。

詳細な利用者要件は [product requirements](../../product/requirements.md)、ルート一覧は [system design](../../architecture/system-design.md) を参照する。
