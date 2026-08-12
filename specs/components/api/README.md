# API 仕様

FastAPI は `/health`、`/dashboard`、`/rss-feeds`、`/news-sites`、`/github-repositories`、`/settings`、`/ai/chat` のルートを公開する。

- RSS feed: 作成、一覧、詳細、更新、削除、通知状態付き記事履歴、Webhookなしでも保存できる手動実行。手動実行は定期通知とフィード別の自動通知設定を参照せず、有効な送信先があれば未通知記事を送る
- Custom RSS: LLM生成または利用者が指定したCSSセレクタによる作成・設定更新、LLM再解析、一覧、詳細、削除、通知状態付き記事履歴、手動取得。手動設定はLLM接続を要求せず、保存前に対象ページでタイトルとリンクを1件以上抽出できることを検証する。設定方式とセレクタは作成・詳細レスポンスへ返す。定期巡回は行わない
- Feed icon: 通常RSS・Custom RSSの外部画像URLを作成・更新APIで受け付け、`/{id}/icon` のGET/PUT/DELETEでアップロード画像を配信・設定・削除する。アップロードはPNG・JPEG・GIF・WebP、最大1 MBとし、公開HTTP(S) URLを同時に保存する
- RSS記事の公開日時はXMLの `pubDate` / `published` を優先し、元のUTCオフセットを保ったISO 8601形式で保存・返却する。
- Dashboard: リクエスト受信時刻を基準に、通常RSS・カスタムRSSの件数、直近24時間の記事数、未通知数、直近24時間の記事を集約して返す。各記事は配信元の設定済みアイコンURLを `source_icon_url` として返す
- GitHub releases: `GET/POST /github-repositories` で登録一覧・追加、`PATCH /github-repositories/{id}` で通知先Webhook選択、`POST /github-repositories/refresh` で全登録先の最新公開リリースを更新し、`DELETE /github-repositories/{id}` で削除する。登録時にも最新1件を取得して保存する。公開リポジトリは認証なしで利用でき、`GITHUB_TOKEN` が設定されていればGitHub APIリクエストに使用する。
- GitHub release notifications: 定期バッチは登録リポジトリの最新公開リリースを確認し、最後に通知成功したタグから変化した場合だけ、リポジトリごとに選択された有効なWebhookへ通知する。未選択時は通知しない。1件以上成功した場合に通知済みタグを更新し、全送信が失敗した場合は次回再試行する。画面からの一括更新は表示キャッシュだけを更新し、未通知判定を失わない。
- Settings: Webhook CRUD・疎通確認、定期実行、定期通知、記事概要、1回のフィード実行で通知する記事上限（既定20件、1〜100件）、デフォルトOFFのAI記事解析と利用上限の設定
- AI article analysis execution: `POST /settings/ai-article-analysis/execute` からRustバッチのAI解析専用モードを同期実行し、処理・成功・失敗・解析済みスキップ件数と日次上限到達状態を返す
- AI article analysis cancellation: `POST /settings/ai-article-analysis/cancel` は現在の実行ロックに紐づく停止要求を保存し、実行中でなければ409を返す
- AI article analysis cleanup: `DELETE /ai/article-analyses/failed` は失敗状態の解析結果だけを削除して削除件数を返す。成功済み結果とトークン使用履歴は維持し、解析実行中は409を返す
- AI article analysis status: `GET /settings/ai-article-analysis/status` はAPIプロセス内の手動実行ロックとSQLiteの有効なバッチロックを確認し、手動・定期のどちらかが実行中なら `running: true` と、対象・処理済み・成功・失敗・スキップ件数、現在の記事タイトル、当日トークン使用量と上限、開始時刻の進捗スナップショットを返す。バッチロックは開始時刻とプロセスIDを保持し、所有プロセスが存在しない場合は孤立ロックを削除する。APIから起動したプロセスの終了時にも成功・失敗を問わず、そのプロセス自身のロックだけを削除する。旧形式の開始時刻だけのロックは、実際のバッチプロセスが存在しない場合に孤立ロックとして削除する
- AI article analysis data: `GET /ai/article-analyses` は記事・配信元情報と解析済みの要約、要点、トピック、キーワード、固有表現、モデル、トークン数、状態、失敗内容を結合して返す。記事・配信元・AI要約の検索、通常RSS・Custom RSSの種別、成功・失敗状態、ページングで絞り込める
- AI article analysis reset: `DELETE /settings/ai-article-analysis/results` は解析が停止中の場合に解析結果を全件削除し、削除件数を返す。FTS検索データはDBトリガーで同期削除するが、日次トークン上限の迂回を防ぐため利用量履歴は保持する。解析中は409を返す
- ローカル開発では `mise run dev` がRustバッチをビルドして `SHIORI_FEED_BATCH_BIN` をAPIへ渡す。本番コンテナではPATH上のインストール済みバイナリを使用する。
- 手動AI解析のRust標準出力・標準エラーはAPIが行単位で `uvicorn.error` ログへ転送し、最終JSONだけをAPIレスポンスへ変換する。
- LLM settings: 接続情報の取得、実接続テスト後の保存、削除、保存前テスト
- Ask AI: 質問を原文検索語と日英の対訳・略称・別名へ展開し、FTS5で保存済み記事と解析済みAIメタデータを検索する。検索順位はタイトル、配信元、Entities、Keywords、多言語aliases、本文、AI要約、Topics・Key pointsの順に主題との一致を重視する。0件の場合は部分一致、期間解除の順に検索条件を自動で広げる。検索候補はLLMの構造化された関連性判定で絞り込み、直接関係する記事だけを回答生成へ渡す。一覧・検索要求は要求トピックを主題とする記事を対象とし、事実質問のような直接回答は要求しない。一覧要求に明記された4文字以上の固有フレーズが配信元、タイトル、本文、AIメタデータに完全一致する候補はLLMの空判定だけで除外しない。LLM未設定時は409を返す
- Ask AI streaming: `POST /ai/chat/stream` はNDJSONで回答差分を逐次返し、回答完了後に実際に引用した出典、続いて完了イベントを返す。エラー時はエラーイベントを返し、OllamaとOpenAI互換のストリーム形式を吸収する。検索候補のうち回答で引用されなかった記事は出典へ含めない
- Ask AI conversation: chat APIは直近8件の会話履歴と直前回答の出典最大10件を任意で受け付ける。`S9` のような出典参照は対応記事へ直接解決して番号を維持する。履歴と出典は永続保存しない。
- エラー: `{"detail": ...}`。入力不正は 422、未検出は 404、重複は 409、外部通知失敗は 502 とする。
- 一覧: `items`, `total`, `page`, `per_page`, `total_pages` を返す。
- Webhook: Discord通知ではフィードの `icon_url` を `avatar_url` に設定する。Incoming Webhookでアイコンを上書きできないSlackとTeamsには追加しない。
- Webhook article limit: `GET/PUT /settings/webhook-article-limit` で `max_articles` を取得・更新する。通常RSSの定期・手動実行とCustom RSSの手動実行は未通知記事を公開日時の新しい順に並べ、最新の上限件数だけを送る。送信成功後は同じバックログの古い記事も処理済みにして次回送信せず、送信失敗時は未通知のまま最新記事から再試行する。
- Microsoft Teams通知の記事リンクは、Adaptive CardのTextBlock内でMarkdownの `- [title](url)` リストとして送る。

詳細な利用者要件は [product requirements](../../product/requirements.md)、ルート一覧は [system design](../../architecture/system-design.md) を参照する。
