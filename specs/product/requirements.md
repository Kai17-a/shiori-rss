# 要件定義書

## はじめに

本ドキュメントは、ブックマーク管理 Web アプリケーション向け REST API の要件を定義する。
API は Python で実装し、データストアには SQLite を使用する。
データモデルは `bookmarks`、RSS、カスタムニュースサイト、フォルダ、タグ、webhook、設定の各テーブルで構成する。

## 用語集

- **API**: ブックマーク管理アプリケーションの REST API サーバー
- **Bookmark**: URL とそのメタデータ（タイトル、説明、お気に入り状態など）を保持するリソース
- **RSS Feed**: RSS または Atom フィードの URL とメタデータを保持するリソース
- **Custom News Site**: RSS を配信しないニュース一覧ページと、LLM が生成したスクレイピング設定を保持するリソース
- **Folder**: ブックマークを整理するためのコンテナリソース
- **Tag**: ブックマークに付与できるラベルリソース（多対多の関係）
- **Webhook**: 外部サービスに通知を送るための URL
- **Client**: API を呼び出すブラウザまたはフロントエンドアプリケーション
- **DB**: SQLite データベース

---

## 要件

### 要件1: ブックマーク管理

**ユーザーストーリー:** 開発者として、ブックマークを登録・閲覧・更新・削除したい。

#### 受け入れ基準

1. WHEN Clientが有効なURL・タイトルを含むPOSTリクエストを `/bookmarks` に送信したとき、THE API SHALL 新しいブックマークをDBに保存し、HTTPステータス201と作成されたブックマークオブジェクト（id, url, title, description, folder_id, is_favorite, tags, created_at, updated_at）を返す。
2. WHEN Clientが `folder_id` を指定してブックマークを作成したとき、THE API SHALL 指定されたフォルダが存在することを確認してから保存する。
3. IF Clientが無効なURL形式を送信したとき、THEN THE API SHALL HTTPステータス422を返す。
4. IF Clientが `title` を省略したとき、THEN THE API SHALL HTTPステータス422を返す。
5. IF Clientが存在しない `folder_id` を指定したとき、THEN THE API SHALL HTTPステータス404を返す。
6. WHEN Clientが `GET /bookmarks` にリクエストを送信したとき、THE API SHALL ブックマーク一覧を返し、`folder_id`、`tag_id`、`q`、`sort`、`page`、`per_page` による絞り込み、ソート、ページングをサポートする。
7. WHEN Clientが `GET /bookmarks` に存在しない `sort` 項目を含めてリクエストを送信したとき、THE API SHALL HTTPステータス422を返す。
8. WHEN Clientが `GET /bookmarks/{id}` にリクエストを送信したとき、THE API SHALL 指定IDのブックマークを返す。
9. WHEN Clientが `PATCH /bookmarks/{id}` にリクエストを送信したとき、THE API SHALL 指定ブックマークを部分更新し、更新後のブックマークを返す。
10. WHEN Clientが `PATCH /bookmarks/by-url?url=...` にリクエストを送信したとき、THE API SHALL 指定URLのブックマークを部分更新し、更新後のブックマークを返す。
11. WHEN Clientが `DELETE /bookmarks/{id}` にリクエストを送信したとき、THE API SHALL 指定ブックマークを削除し、HTTPステータス204を返す。
12. WHEN Clientが `DELETE /bookmarks?url=...` にリクエストを送信したとき、THE API SHALL 指定URLのブックマークを削除し、HTTPステータス204を返す。
13. WHEN Clientが `PATCH /bookmarks/favorite` にリクエストを送信したとき、THE API SHALL 指定ブックマークのお気に入り状態を更新し、更新後のブックマークを返す。

### 要件2: フォルダ管理

**ユーザーストーリー:** 開発者として、ブックマークをフォルダで整理したい。

#### 受け入れ基準

1. WHEN Clientが有効な名前を含むPOSTリクエストを `/folders` に送信したとき、THE API SHALL 新しいフォルダをDBに保存し、HTTPステータス201と作成されたフォルダオブジェクト（id, name, description, created_at）を返す。
2. WHEN ClientがGETリクエストを `/folders` に送信したとき、THE API SHALL フォルダ一覧を返す。
3. WHEN ClientがPATCHリクエストを `/folders/{id}` に送信したとき、THE API SHALL 指定フォルダを更新し、更新後のフォルダを返す。
4. WHEN ClientがDELETEリクエストを `/folders/{id}` に送信したとき、THE API SHALL 指定フォルダを削除し、HTTPステータス204を返す。
5. IF Clientが存在しないIDを指定したとき、THEN THE API SHALL HTTPステータス404を返す。
6. WHEN フォルダが削除されたとき、THE API SHALL そのフォルダに属していたブックマークの `folder_id` を `null` に更新する。
7. WHEN Clientがフォルダを作成または更新するとき、THE API SHALL `description` を任意で保持できる。

### 要件3: タグ管理

**ユーザーストーリー:** 開発者として、ブックマークをタグで分類したい。

#### 受け入れ基準

1. WHEN Clientが有効な名前を含むPOSTリクエストを `/tags` に送信したとき、THE API SHALL 新しいタグをDBに保存し、HTTPステータス201と作成されたタグオブジェクト（id, name, description）を返す。
2. WHEN ClientがGETリクエストを `/tags` に送信したとき、THE API SHALL タグ一覧を返す。
3. WHEN ClientがPATCHリクエストを `/tags/{id}` に送信したとき、THE API SHALL 指定タグを更新し、更新後のタグを返す。
4. WHEN ClientがDELETEリクエストを `/tags/{id}` に送信したとき、THE API SHALL 指定タグを削除し、HTTPステータス204を返す。
5. IF Clientが重複するタグ名を作成または更新しようとしたとき、THEN THE API SHALL HTTPステータス409を返す。
6. IF Clientが存在しないIDを指定したとき、THEN THE API SHALL HTTPステータス404を返す。
7. WHEN タグが削除されたとき、THE API SHALL そのタグに関連する `bookmark_tags` レコードも同時に削除する。
8. WHEN Clientがタグを作成または更新するとき、THE API SHALL `description` を任意で保持できる。

### 要件4: ブックマークへのタグ付与・解除

**ユーザーストーリー:** 開発者として、ブックマークにタグを付与または解除したい。

#### 受け入れ基準

1. WHEN Clientが有効な `tag_id` を含むPOSTリクエストを `/bookmarks/{id}/tags` に送信したとき、THE API SHALL 指定されたブックマークとタグの紐付けを保存し、HTTPステータス200と更新後のブックマークオブジェクトを返す。
2. WHEN Clientが `DELETE /bookmarks/{id}/tags/{tag_id}` にリクエストを送信したとき、THE API SHALL 指定されたブックマークとタグの紐付けを削除し、HTTPステータス204を返す。
3. IF Clientが既に紐付け済みのタグを再度付与しようとしたとき、THEN THE API SHALL HTTPステータス409を返す。
4. IF Clientが存在しないブックマークIDまたはタグIDを指定したとき、THEN THE API SHALL HTTPステータス404を返す。

### 要件5: 永続化とエラー処理

**ユーザーストーリー:** 開発者として、データを永続化し、DB障害時に安全に失敗したい。

#### 受け入れ基準

1. THE API SHALL 全データを SQLite データベースファイルに永続化する。
2. THE API SHALL 起動時に bookmarks、RSS、custom news site、folders、tags、webhook、settings の全 migration table が存在しない場合、自動作成する。
3. WHILE APIが動作中のとき、THE API SHALL 全ての書き込み操作をトランザクション内で実行し、エラー発生時にはロールバックする。
4. IF データベースへの接続または書き込みに失敗したとき、THEN THE API SHALL HTTPステータス500を返す。

### 要件6: RSS フィード管理

**ユーザーストーリー:** 開発者として、RSS フィード URL を登録・更新・削除したい。

#### 受け入れ基準

1. WHEN Clientが有効なフィード URL・タイトルを含む POST リクエストを `/rss-feeds` に送信したとき、THE API SHALL 新しい RSS フィードを DB に保存し、HTTP ステータス 201 と作成された RSS フィードオブジェクトを返す。
2. WHEN Clientが `GET /rss-feeds` にリクエストを送信したとき、THE API SHALL RSS フィード一覧を返し、`q`、`page`、`per_page` による検索とページングをサポートする。
3. WHEN Clientが `GET /rss-feeds/{id}` にリクエストを送信したとき、THE API SHALL 指定 ID の RSS フィードを返す。
4. WHEN Clientが `GET /rss-feeds/{id}/articles` にリクエストを送信したとき、THE API SHALL 保存済み記事一覧を `published` の新しい順（未設定は末尾）で返し、`page` と `per_page` によるページングをサポートする。
5. WHEN Clientが `PATCH /rss-feeds/{id}` にリクエストを送信したとき、THE API SHALL 指定 RSS フィードを部分更新し、更新後の RSS フィードを返す。
6. WHEN Clientが `DELETE /rss-feeds/{id}` にリクエストを送信したとき、THE API SHALL 指定 RSS フィードを削除し、HTTP ステータス 204 を返す。
7. IF Clientが無効な URL 形式を送信したとき、THEN THE API SHALL HTTP ステータス 422 を返す。
8. IF Clientが RSS または Atom フィードではない URL を送信したとき、THEN THE API SHALL HTTP ステータス 422 を返す。
9. IF Clientが重複する RSS フィード URL を作成または更新しようとしたとき、THEN THE API SHALL HTTP ステータス 409 を返す。
10. WHEN Clientが RSS フィードの作成または更新時に `webhook_ids` を指定したとき、THE API SHALL そのフィードの通知先 webhook を指定された webhook のみに限定する。
11. IF RSS フィードに `webhook_ids` が指定されなかったとき、THEN THE API SHALL そのフィードの通知を登録済みの全 webhook に送信する。
12. IF Clientが存在しない webhook ID を `webhook_ids` に含めたとき、THEN THE API SHALL HTTP ステータス 404 を返す。

### 要件7: Webhook 設定、RSS 定期実行、集計

**ユーザーストーリー:** 開発者として、アプリ全体の webhook URL を複数登録し、RSS 実行結果を外部サービスに通知したい。

#### 受け入れ基準

1. WHEN Clientが識別用の名前と有効な Discord、Slack、または Microsoft Teams webhook URL を含む `POST /settings/webhooks` を送信したとき、THE API SHALL その URL を登録し、HTTP ステータス 201 と登録結果を返す。
2. WHEN Clientが `GET /settings/webhooks` にリクエストを送信したとき、THE API SHALL 登録済み webhook の名前と URL の一覧を返す。
3. WHEN Clientが `DELETE /settings/webhooks/{id}` にリクエストを送信したとき、THE API SHALL 指定 webhook を削除し、HTTP ステータス 204 を返す。
4. IF Clientが Discord、Slack、または Microsoft Teams webhook URL ではない URL を `POST /settings/webhooks` に送信したとき、THEN THE API SHALL HTTP ステータス 422 を返す。
5. IF Clientが空または空白のみの名前を `POST /settings/webhooks` に送信したとき、THEN THE API SHALL HTTP ステータス 422 を返す。
6. IF Clientが登録済みと重複する webhook URL を `POST /settings/webhooks` に送信したとき、THEN THE API SHALL HTTP ステータス 409 を返す。
7. WHEN Clientが `POST /settings/webhook/ping` にリクエストを送信したとき、THE API SHALL webhook の疎通確認を行い、`pong: true` を返す。
8. WHEN Clientが `GET /settings/rss-execution` または `PUT /settings/rss-execution` にリクエストを送信したとき、THE API SHALL RSS 定期実行の有効/無効状態を取得・更新する。
9. WHEN Clientが `GET /metrics/dashboard` にリクエストを送信したとき、THE API SHALL ダッシュボード用の集計値を返す。
10. WHEN Clientが `POST /rss-feeds/{id}/execute` にリクエストを送信したとき、THE API SHALL 指定 RSS フィードを検証し、登録済みの全 webhook URL に通知を送信し、実行結果を返す。
11. IF webhook URL が 1 件も登録されていない状態で `POST /rss-feeds/{id}/execute` が呼ばれたとき、THEN THE API SHALL HTTP ステータス 400 を返す。
12. IF すべての webhook 通知に失敗したとき、THEN THE API SHALL HTTP ステータス 502 を返す。
13. WHEN Clientが `GET /settings/rss-webhook-notification` または `PUT /settings/rss-webhook-notification` にリクエストを送信したとき、THE API SHALL RSS 定期実行時の webhook 通知有効/無効状態を取得・更新する。
14. THE API SHALL Discord、Slack、Microsoft Teams の incoming webhook に対応する。
15. WHEN コンテナを起動するとき、THE SYSTEM SHALL `RSS_CRON_SCHEDULE` の Supercronic 互換 cron 式で定期 batch を起動し、未指定時は毎時 0 分を使用し、`TZ` によるタイムゾーン指定を反映する。
16. WHEN Clientが `GET /settings/webhook-summary` または `PUT /settings/webhook-summary` にリクエストを送信したとき、THE API SHALL webhook 通知に記事サマリーを含めるアプリ全体設定を取得・更新する。未設定時は有効とし、RSS と custom news site の手動実行・定期 batch の全通知に適用する。

### 要件8: LLM 設定とカスタムニュースサイト

**ユーザーストーリー:** 利用者として、RSS を配信しないニュースサイトも RSS と同様に巡回・通知したい。

#### 受け入れ基準

1. WHEN Client が Ollama、vLLM、または OpenAI 互換の接続情報を保存するとき、THE API SHALL 実際の chat completion が成功した場合だけ設定を保存する。
2. THE API SHALL 保存済み API key をレスポンスへ返さず、登録済みかどうかだけを返す。
3. IF LLM 設定がない状態で custom news site を登録しようとしたとき、THEN THE API SHALL HTTP ステータス 400 を返す。
4. WHEN Client が custom news site URL を登録するとき、THE API SHALL HTML を取得し、LLM で記事コンテナ・タイトル・リンク・公開日時・要約の CSS selector を解析する。
5. THE API SHALL 生成した selector で少なくとも 1 件の記事タイトルと HTTP/HTTPS リンクを取得できた場合だけ custom news site を保存し、取得できない場合は 422 を返す。
   - 初回の selector で抽出結果が 0 件の場合、THE API SHALL 取得済み HTML、失敗した selector、一致件数を使って LLM 解析を最大 1 回再試行する。
   - 再解析が同じ selector を返した場合、THE API SHALL 追加の抽出を行わず 422 を返す。
6. THE API SHALL custom news site の一覧・詳細・部分更新・削除・記事履歴・手動実行を提供する。
7. WHEN custom news site を手動実行または batch 巡回するとき、THE SYSTEM SHALL 未通知の記事だけを選択済み webhook（未選択時は全 webhook）へ通知し、1 件以上の送信成功後に記事を記録する。
8. WHEN custom news site の URL を変更するとき、THE API SHALL 新しい HTML の LLM 解析と抽出テストが成功した場合だけ URL とスクレイピング設定を更新する。
9. IF custom news site 登録に失敗したとき、THEN THE API SHALL 対象 site 取得、LLM 接続、LLM upstream rejection、LLM response、selector 抽出の失敗段階を区別したメッセージと log 照合用 reference ID を返す。
10. WHEN custom news site の解析エラーを記録するとき、THE API SHALL provider、model、対象 URL、HTTP status、HTML サイズまたは短い response preview を必要に応じて記録し、API key と HTML 本文全体は記録しない。
