# テスト観点

## 単体テスト

- `api/tests/test_database.py`
  - 全テーブルの自動作成
  - 初期化の冪等性
  - 全 migration の適用履歴と追加カラム
  - DB 障害時の 500 応答

- `api/tests/test_bookmarks.py`
  - 作成、一覧、詳細、更新、削除
  - 検索、絞り込み、ページング
  - フォルダ関連付け
  - URL 指定削除
  - URL 指定更新とお気に入り切り替え
  - タグ付与・解除
  - バリデーションと重複エラー
  - タグ集合の置き換え
  - description と folder の明示的な解除
  - URL、title、tag_ids への null 指定を 422 で拒否

- `api/tests/test_folders.py`
  - 作成、一覧、更新、削除
  - 参照先更新と 404 応答

- `api/tests/test_tags.py`
  - 作成、一覧、更新、削除
  - 重複エラーと 404 応答

- `api/tests/test_rss_feeds.py`
  - 作成、一覧、詳細、更新、削除
  - 記事一覧、実行、webhook 登録
  - RSS/Atom 以外の URL 拒否
  - webhook 疎通確認
  - Slack webhook URL の登録と疎通確認
  - Microsoft Teams webhook URL の登録、疎通確認、箇条書きタイトルリンクと記事間余白を持ち、罫線と遷移ボタンを持たない Adaptive Card 通知
  - 複数 webhook への送信、一部失敗時の継続、全滅時の 502
  - 無効な webhook URL を手動通知先から除外
  - フィードごとの通知先 webhook 選択の作成・更新・解除、選択先のみへの送信、未存在 ID の 404、重複 ID と null の 422
  - RSS 定期実行設定
  - 新規記事なしメッセージ
  - 既送信記事のスキップ
  - article paging
  - description の明示的な解除
  - URL、title、通知有効フラグへの null 指定を 422 で拒否

- `api/tests/test_metrics.py`
  - ダッシュボード集計

- `api/tests/test_settings.py`
  - webhook サマリー包含設定が未設定時に有効であり、無効へ更新できること
  - webhook 未登録時の空一覧
  - webhook の複数登録と一覧取得
  - webhook URLごとの通知有効状態の更新と未存在 ID の 404
  - 重複 webhook URL の 409
  - webhook 削除と未存在 ID の 404
  - Discord、Slack、Microsoft Teams webhook URL 形式検証
  - ping の 422 と 502
  - RSS 定期実行設定の取得と更新
  - LLM 接続成功後の保存、API key 非公開、接続失敗時の未保存、削除

- `api/tests/test_llm_service.py`
  - Ollama、vLLM、OpenAI 互換 chat completion の endpoint と応答形式
  - LLM scraping analysis JSON の optional summary selector
  - LLM upstream rejection の原因別エラー、reference ID、API key 非記録
  - scraping JSON 不正時の対象 site 取得済みメッセージと安全な診断 log

- `api/tests/test_news_sites.py`
  - LLM 未設定時の登録拒否
  - HTML 解析と実抽出テスト成功後の登録
  - 記事を抽出できない selector の登録拒否と DB 未保存
  - 初回 selector が 0 件の場合の診断情報付き再解析、修正版 selector の保存、同一 selector 再応答時の打ち切り
  - 対象 site の 403/automation block と selector 抽出 0 件の原因別メッセージ・診断 log
  - 手動実行、相対 URL 解決、Webhook 通知、記事履歴、重複通知防止
  - 更新時の任意LLM再解析と、省略時に既存selectorを維持すること
  - 無効な webhook URL を手動通知先から除外
  - 保存済み記事の公開日が解析不能でも一覧全体を 500 にせず、該当日付を `null` として返す
  - URL 重複拒否

## ルート単位の確認観点

- `POST /bookmarks`
  - 正常作成
  - `folder_id` の存在確認
  - `tag_ids` の重複拒否
  - 既存 URL の 409

- `GET /bookmarks`
  - デフォルトページング
  - `page` と `per_page`
  - `folder_id`、`tag_id`、`q` の絞り込み

- `PATCH /bookmarks/{id}`
  - 部分更新
  - URL 指定更新
  - お気に入り切り替え
  - タグ集合の置き換え
  - 404 と 409

- `PATCH /bookmarks/by-url`
  - 対象 URL の部分更新
  - 存在しない URL の 404
  - URL 重複時の 409

- `DELETE /bookmarks?url=...`
  - URL 指定削除
  - 存在しない URL の 404

- `POST /folders` / `POST /tags`
  - 正常作成
  - 空文字拒否
  - `description` の保存

- `PATCH /folders/{id}` / `PATCH /tags/{id}`
  - 名前更新
  - 重複名 409
  - 存在しない ID の 404

- `POST /bookmarks/{id}/tags`
  - 紐付け追加
  - 重複紐付け 409
  - 存在しない bookmark/tag の 404

- `DELETE /bookmarks/{id}/tags/{tag_id}`
  - 紐付け解除
  - 存在しない bookmark/tag の 404

- `GET /settings/webhooks` / `POST /settings/webhooks` / `DELETE /settings/webhooks/{id}`
  - 一覧取得、名前付き複数登録、削除
  - 重複 URL の 409
  - 空白名の 422
  - Discord、Slack、Microsoft Teams webhook URL の形式検証

- `POST /settings/webhook/ping`
  - 疎通確認
  - 422 と 502

- `GET /settings/rss-execution` / `PUT /settings/rss-execution`
  - 現在値取得
  - 有効/無効更新

- `GET /metrics/dashboard`
  - 総数取得

- `GET /rss-feeds/{id}/articles`
  - API と batch が保存する日時形式の違いにかかわらず `published` の新しい順で返し、日時なしを末尾にする
  - 記事一覧取得
  - `page` と `per_page`
  - 存在しない feed の 404

- `POST /rss-feeds/{id}/execute`
  - webhook 未設定時の 400
  - 新規記事通知
  - 既送信記事スキップ
  - 新規記事なしメッセージ
  - webhook 失敗時の 502

## プロパティテスト

- `api/tests/test_properties.py`
  - 作成のラウンドトリップ
  - 無効 URL の拒否
  - 存在しないリソースの 404
  - フォルダ/タグフィルタの正確性
  - キーワード検索の正確性
  - 部分更新の不変性
  - 削除とカスケード
  - タグ付与・解除のラウンドトリップ
  - URL 指定更新とお気に入り切り替え

## 未カバー範囲

- OpenAPI ドキュメントのスナップショット
- 同時実行時の競合テスト
- 低レベルの SQLite パフォーマンス検証

## 実装候補

- `api/tests/test_database.py`
  - `rss_feed_articles` を含む全テーブル初期化を確認する

- `api/tests/test_bookmarks.py`
  - `PATCH /bookmarks/by-url` の 404/409 を追加する
  - `DELETE /bookmarks?url=...` の 404 を追加する
  - folder/tag `description` を伴う bookmark 関連付けの整合を確認する

- `api/tests/test_folders.py`
  - `description` の create/update round-trip を追加する

- `api/tests/test_tags.py`
  - `description` の create/update round-trip を追加する

- `api/tests/test_settings.py`
  - 未設定 webhook の 404
  - Discord webhook URL host/path 検証
  - ping の upstream failure を 502 へ写像するケース
  - RSS periodic execution の true/false 両遷移

- `api/tests/test_rss_feeds.py`
  - webhook サマリー包含設定が無効な場合に手動実行 payload からサマリーを除外すること
  - `/rss-feeds/{id}/articles` の paging と 404
  - `/rss-feeds/{id}/execute` の 400, 502, no-new-articles message
  - 送信済み article の二重記録防止

- `api/tests/test_metrics.py`
  - `favorites_total` と `rss_feeds_total` の状態遷移反映を追加する

- `api/tests/test_properties.py`
  - URL 指定削除
  - folder/tag `description` を含む部分更新の不変性
