# ルートとフロー

## ルート

| Method | Path                            | Purpose                          |
| ------ | ------------------------------- | -------------------------------- |
| POST   | `/bookmarks`                    | ブックマーク作成                 |
| GET    | `/bookmarks`                    | ブックマーク一覧取得             |
| GET    | `/bookmarks/by-url`             | URL 指定ブックマーク取得         |
| GET    | `/bookmarks/{id}`               | ブックマーク詳細取得             |
| PATCH  | `/bookmarks/{id}`               | ブックマーク部分更新             |
| PATCH  | `/bookmarks/by-url`             | URL 指定ブックマーク部分更新     |
| DELETE | `/bookmarks`                    | 条件指定ブックマーク削除         |
| DELETE | `/bookmarks/by-url`             | URL 指定ブックマーク削除         |
| DELETE | `/bookmarks/{id}`               | ID 指定ブックマーク削除          |
| PATCH  | `/bookmarks/favorite`           | ブックマークのお気に入り状態更新 |
| POST   | `/bookmarks/{id}/tags`          | ブックマークへタグ付与           |
| DELETE | `/bookmarks/{id}/tags/{tag_id}` | ブックマークからタグ解除         |
| GET    | `/metrics/dashboard`            | ダッシュボード用集計取得         |
| POST   | `/folders`                      | フォルダ作成                     |
| GET    | `/folders`                      | フォルダ一覧取得                 |
| GET    | `/folders/{id}`                 | フォルダ詳細取得                 |
| PATCH  | `/folders/{id}`                 | フォルダ更新                     |
| DELETE | `/folders/{id}`                 | フォルダ削除                     |
| POST   | `/tags`                         | タグ作成                         |
| GET    | `/tags`                         | タグ一覧取得                     |
| GET    | `/tags/{id}`                    | タグ詳細取得                     |
| PATCH  | `/tags/{id}`                    | タグ更新                         |
| DELETE | `/tags/{id}`                    | タグ削除                         |
| GET    | `/settings/webhooks`            | webhook 一覧取得                 |
| POST   | `/settings/webhooks`            | webhook 登録                     |
| PATCH  | `/settings/webhooks/{id}`       | webhook 通知有効状態更新         |
| DELETE | `/settings/webhooks/{id}`       | webhook 削除                     |
| POST   | `/settings/webhook/ping`        | webhook 疎通確認                 |
| GET    | `/settings/llm`                 | 保存済み LLM 設定取得            |
| PUT    | `/settings/llm`                 | LLM 疎通確認と設定保存           |
| DELETE | `/settings/llm`                 | LLM 設定削除                     |
| POST   | `/settings/llm/test`            | 入力中または保存済み LLM の疎通確認 |
| GET    | `/settings/rss-execution`       | RSS 定期実行設定取得             |
| PUT    | `/settings/rss-execution`       | RSS 定期実行設定更新             |
| GET    | `/settings/rss-webhook-notification` | RSS 定期実行 webhook 通知設定取得 |
| PUT    | `/settings/rss-webhook-notification` | RSS 定期実行 webhook 通知設定更新 |
| GET/PUT | `/settings/webhook-summary` | 全 webhook 通知のサマリー包含設定取得・更新 |
| POST   | `/rss-feeds`                    | RSS フィード作成                 |
| GET    | `/rss-feeds`                    | RSS フィード一覧取得             |
| GET    | `/rss-feeds/{id}`               | RSS フィード詳細取得             |
| GET    | `/rss-feeds/{id}/articles`      | RSS フィード記事一覧取得         |
| PATCH  | `/rss-feeds/{id}`               | RSS フィード部分更新             |
| DELETE | `/rss-feeds/{id}`               | RSS フィード削除                 |
| POST   | `/rss-feeds/{id}/execute`       | RSS 実行と webhook 通知          |
| POST   | `/news-sites`                   | HTML 解析・抽出テスト後に custom news site 作成 |
| GET    | `/news-sites`                   | custom news site 一覧取得        |
| GET    | `/news-sites/{id}`              | custom news site 詳細取得        |
| GET    | `/news-sites/{id}/articles`     | 保存済み scraped article 一覧取得 |
| PATCH  | `/news-sites/{id}`              | custom news site 部分更新        |
| DELETE | `/news-sites/{id}`              | custom news site 削除            |
| POST   | `/news-sites/{id}/execute`      | HTML scrape と webhook 通知      |
| GET    | `/health`                       | ヘルスチェック                   |

## ユーザーフロー

### ブックマーク

- URL とタイトルを入力して作成する
- 一覧で検索・ページング・絞り込みを行う
- 詳細を確認して編集または削除する
- URL 指定で詳細取得する
- URL 指定で詳細なしに部分更新する
- 必要に応じてタグを追加・削除する
- 必要に応じてお気に入り状態を切り替える

### ダッシュボード

- ブックマーク、フォルダ、タグ、お気に入り、RSS フィード、custom news site の総数を確認する

### フォルダ

- フォルダを作成する
- 一覧から対象フォルダへ移動する
- フォルダ名と説明を更新し、不要なら削除する

### タグ

- タグを作成する
- 一覧から対象タグへ移動する
- タグ名と説明を更新し、不要なら削除する

### 設定

- Discord、Slack、または Microsoft Teams webhook URL を識別用の名前付きで複数登録する
- 登録済み webhook の一覧を名前と URL で取得する
- webhook URL ごとに通知の有効/無効を切り替える
- 不要になった webhook を削除する
- webhook の疎通確認を行う
- 重複する webhook URL の登録は 409 を返す
- RSS 定期実行の有効/無効を切り替える
- RSS 定期実行時に webhook 通知を送るかどうかを切り替える
- Ollama、vLLM、OpenAI 互換 endpoint の接続情報をテストしてから保存する
- 保存済み LLM 設定を取得・削除し、API key は登録有無だけを確認する

### RSS

- RSS フィードを登録する
- フィードごとに通知先 webhook を任意で選択する（未選択時は全 webhook へ通知）
- 一覧で検索・ページングを行う
- 詳細を確認して編集または削除する
- 保存済みの記事一覧を確認する
- 手動実行して webhook 通知を送る

### カスタムニュースサイト

- LLM 設定が存在する場合だけ URL を登録する
- URL の HTML を取得し、LLM が CSS selector を生成した後、実際に記事を抽出できることを確認して保存する。抽出が 0 件の場合は、同じ HTML と失敗した selector・一致件数を使って LLM 解析を 1 回だけ再試行する
- 再解析で selector が修正されて抽出に成功した場合は修正版を保存し、同じ selector が返るか再度 0 件になった場合は 422 を返す
- URL 更新時は新しい URL でも HTML 解析と抽出テストを再実行する
- 更新時は任意の `reanalyze` 指定により、現在のURLでもHTML解析と抽出テストを再実行してselectorを更新できる
- 登録・URL 更新の失敗は、対象 site 取得、LLM 接続、LLM upstream rejection、LLM response、selector 抽出のどこで失敗したかを区別し、server log と照合できる reference ID を返す
- 一覧、詳細、記事履歴を確認し、通知先 webhook と定期通知可否を編集する
- 手動実行では保存済み selector を使って未通知記事を抽出し、webhook 成功後に記事 URL を記録する

## 共通レスポンス

- 正常系はリソースモデルを返す
- 一覧はページングレスポンス、または小さなマスタ一覧では配列を返す
- エラーは `{"detail": ...}` 形式で返す
- バリデーションエラーは FastAPI の標準形式を返す

## 受け入れ基準

### ブックマーク

1. `POST /bookmarks` は、有効な URL と title がある場合に 201 を返し、作成済みブックマークを返す。
2. `POST /bookmarks` は、`folder_id` が指定されている場合に存在確認を行う。
3. `POST /bookmarks` は、無効 URL または title 省略時に 422 を返す。
4. `POST /bookmarks` は、存在しない `folder_id` に対して 404 を返す。
5. `GET /bookmarks` は、一覧とページング情報を返す。
6. `GET /bookmarks` は、`folder_id`、`tag_id`、`q`、`is_favorite`、`sort`、`page`、`per_page` を受け付ける。
7. `GET /bookmarks` の `sort` は複数指定でき、指定順に `ORDER BY` を適用する。
8. `GET /bookmarks` の `sort` に存在しない項目が指定された場合は 422 を返す。
9. `GET /bookmarks/{id}` は、対象ブックマークを返す。
10. `GET /bookmarks/by-url` は、URL で対象ブックマークを特定して返す。
11. `PATCH /bookmarks/{id}` は、部分更新を行い更新後リソースを返す。
12. `PATCH /bookmarks/by-url` は、URL で対象ブックマークを特定して部分更新を行う。
13. `DELETE /bookmarks` は、条件に一致するブックマークを削除し、204 を返す。
14. `DELETE /bookmarks` は、`id`、`url`、`title`、`description`、`folder_id`、`is_favorite` を受け付ける。
15. `DELETE /bookmarks` は、指定した条件をすべて AND で評価する。
16. `DELETE /bookmarks` は、どの条件も指定されない場合に 422 を返す。
17. `DELETE /bookmarks/by-url` は、URL で対象ブックマークを特定して削除し、204 を返す。
18. `DELETE /bookmarks/{id}` は、ID で対象ブックマークを特定して削除し、204 を返す。
19. `PATCH /bookmarks/favorite` は、お気に入り状態を更新し更新後リソースを返す。

### フォルダ

13. `POST /folders` は、201 と作成済みフォルダを返す。
14. `GET /folders` は、フォルダ一覧を配列で返す。
15. `GET /folders/{id}` は、対象フォルダを返す。
16. `PATCH /folders/{id}` は、更新後フォルダを返す。
17. `DELETE /folders/{id}` は、204 を返す。
18. フォルダ削除時は、関連ブックマークの `folder_id` を `NULL` にする。
19. フォルダは `name` に加えて `description` を保持する。

### タグ

19. `POST /tags` は、201 と作成済みタグを返す。
20. `GET /tags` は、タグ一覧を配列で返す。
21. `GET /tags/{id}` は、対象タグを返す。
22. `PATCH /tags/{id}` は、更新後タグを返す。
23. `DELETE /tags/{id}` は、204 を返す。
24. タグ削除時は、関連 `bookmark_tags` を削除する。
25. タグは `name` に加えて `description` を保持する。

### タグ付与

25. `POST /bookmarks/{id}/tags` は、タグ紐付けを追加し更新後ブックマークを返す。
26. `DELETE /bookmarks/{id}/tags/{tag_id}` は、204 を返す。
27. 既に紐付け済みのタグを再度付与すると 409 を返す。
28. 存在しない bookmark/tag のいずれかを指定すると 404 を返す。

### ダッシュボードとヘルス

29. `GET /metrics/dashboard` は、ダッシュボードで使う総数を返す。
30. `GET /health` は、`status: ok` を返す。

### 設定

31. `GET /settings/webhooks` は、登録済み webhook の一覧を返す。
32. `POST /settings/webhooks` は Discord、Slack、または Microsoft Teams webhook URL を登録し 201 を返し、`PATCH /settings/webhooks/{id}` はURLごとの通知有効状態を更新して更新後の webhook を返す。
33. `POST /settings/webhook/ping` は、webhook の疎通確認を行い `pong: true` を返す。
34. `GET /settings/rss-execution` は、RSS 定期実行の有効/無効状態を返す。
35. `PUT /settings/rss-execution` は、RSS 定期実行の有効/無効状態を更新する。
36. `GET /settings/rss-webhook-notification` は、定期実行時に webhook 通知を送るかどうかの全体設定を返す。
37. `PUT /settings/rss-webhook-notification` は、定期実行時に webhook 通知を送るかどうかの全体設定を更新する。
38. `GET /settings/webhook-summary` と `PUT /settings/webhook-summary` は、RSS と custom news site の全 webhook 通知にサマリーを含めるかどうかを取得・更新する。
38. `PUT /settings/llm` は chat completion の成功後だけ設定を保存し、API key 本文は返さない。
39. `POST /settings/llm/test` は入力値を保存せず疎通確認し、省略項目は保存済み設定で補完する。
40. `GET /settings/llm` は未設定時に 404、設定時に `api_key_configured` を含む設定を返す。
41. `DELETE /settings/llm` は保存済み LLM 設定を削除する。

### RSS

42. `POST /rss-feeds` は、201 と作成済み RSS フィードを返す。
43. `GET /rss-feeds` は、RSS フィード一覧とページング情報を返す。
44. `GET /rss-feeds/{id}` は、対象 RSS フィードを返す。
45. `GET /rss-feeds/{id}/articles` は、保存済み記事一覧とページング情報を返す。
46. `PATCH /rss-feeds/{id}` は、部分更新を行い更新後 RSS フィードを返す。
47. `DELETE /rss-feeds/{id}` は、204 を返す。
48. `POST /rss-feeds/{id}/execute` は、RSS を取得して登録済み webhook に通知する。

### カスタムニュースサイト

49. `POST /news-sites` は LLM 未設定時に 400 を返す。
50. `POST /news-sites` は HTML 取得、LLM selector 生成、1 件以上の記事抽出がすべて成功した場合だけ 201 を返す。
51. `GET /news-sites` と `GET /news-sites/{id}` は一覧・詳細を返し、内部の `scrape_config` は公開しない。
52. `PATCH /news-sites/{id}` の URL 変更または任意の `reanalyze: true` は再解析・再テストを行い、失敗時はselectorを更新しない。
53. `GET /news-sites/{id}/articles` は保存済み記事一覧とページング情報を返す。
54. `POST /news-sites/{id}/execute` は未通知記事を選択対象 webhook へ通知し、1 件以上成功した場合だけ記事を記録する。
55. `DELETE /news-sites/{id}` はサイト、記事、webhook 関連を連動削除して 204 を返す。
56. 対象 site が 401/403 を返す場合は、LLM 解析前に認証または自動取得拒否の可能性を含む 422 を返す。
57. LLM 解析の 502 は接続失敗、upstream HTTP rejection、protocol response 不正、message content 欠落、scraping JSON 不正を区別し、reference ID を含む。

### `GET /metrics/dashboard`

Response:

```json
{
  "bookmarks_total": 12,
  "folders_total": 3,
  "tags_total": 8,
  "favorites_total": 4,
  "rss_feeds_total": 2,
  "news_sites_total": 1
}
```

### `POST /bookmarks`

Request:

```json
{
  "url": "https://example.com",
  "title": "Example",
  "description": "Optional",
  "folder_id": 1,
  "tag_ids": [1, 2]
}
```

Response:

```json
{
  "id": 1,
  "url": "https://example.com/",
  "title": "Example",
  "description": "Optional",
  "folder_id": 1,
  "is_favorite": false,
  "tags": [
    { "id": 1, "name": "tag-a", "description": null },
    { "id": 2, "name": "tag-b", "description": null }
  ],
  "created_at": "2026-04-11T00:00:00",
  "updated_at": "2026-04-11T00:00:00"
}
```

- 成功時の `tags` は空配列または関連タグ配列になる
- `is_favorite` は作成時に指定しなければ `false` になる
- `tag_ids` は重複不可で、重複時は 422 を返す
- 既存 URL は 409 を返す

### `GET /bookmarks`

- `folder_id` でフォルダ絞り込みを行う
- `tag_id` でタグ絞り込みを行う
- `q` でタイトル、URL、説明を検索する
- `is_favorite` でお気に入り状態を絞り込む
- `page` と `per_page` でページングする

Response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "per_page": 20,
  "total_pages": 0
}
```

- `total_pages` は総件数と `per_page` から算出する
- 該当件数がない場合は `items` を空配列で返す

### `PATCH /bookmarks/by-url`

- `url` クエリパラメータで対象ブックマークを特定する
- `PATCH /bookmarks/{id}` と同じ更新ルールを使う
- 存在しない URL は 404 を返す

### `GET /bookmarks/by-url`

- `url` クエリパラメータで対象ブックマークを特定する
- 存在しない URL は 404 を返す

### `DELETE /bookmarks?...`

- `id`、`url`、`title`、`description`、`folder_id`、`is_favorite` のうち 1 つ以上のクエリパラメータで対象ブックマークを特定する
- 指定された条件をすべて AND で満たすブックマークを削除する
- どの条件も指定されない場合は 422 を返す
- 成功時は 204 を返す

### `PATCH /bookmarks/{id}`

- 指定された項目のみ更新する
- `tag_ids` が含まれる場合はタグ集合を置き換える
- 未指定の項目は既存値を保持する
- 存在しない ID は 404 を返す
- URL 変更後に重複があれば 409 を返す

### `PATCH /bookmarks/favorite`

Request:

```json
{
  "bookmark_id": 1,
  "is_favorite": true
}
```

- `bookmark_id` で対象ブックマークを特定する
- `is_favorite` を指定値に更新する
- 存在しない `bookmark_id` は 404 を返す

### `POST /bookmarks/{id}/tags`

Request:

```json
{ "tag_id": 1 }
```

- 既存の紐付けなら 409 を返す
- 成功時は更新後のブックマークを返す
- 存在しない bookmark/tag は 404 を返す

### `DELETE /bookmarks/{id}/tags/{tag_id}`

- 紐付けを削除する
- 成功時は 204 を返す
- 存在しない bookmark/tag は 404 を返す

### `POST /folders`

Request:

```json
{ "name": "Work", "description": "Team notes" }
```

Response:

```json
{
  "id": 1,
  "name": "Work",
  "description": "Team notes",
  "created_at": "2026-04-11T00:00:00"
}
```

### `GET /folders`

- レスポンスは配列で返す
- `name` と `id` の昇順で返す

### `GET /folders/{id}`

- 指定 ID のフォルダを返す
- 存在しない ID は 404 を返す

### `PATCH /folders/{id}`

- 名前を更新する
- `description` も更新できる
- 重複名は 409 を返す
- 存在しない ID は 404 を返す

### `POST /tags`

Request:

```json
{ "name": "python", "description": "Programming language" }
```

Response:

```json
{ "id": 1, "name": "python", "description": "Programming language" }
```

### `GET /tags`

- レスポンスは配列で返す
- `name` と `id` の昇順で返す

### `GET /tags/{id}`

- 指定 ID のタグを返す
- 存在しない ID は 404 を返す

### `PATCH /tags/{id}`

- 名前を更新する
- `description` も更新できる
- 重複名は 409 を返す
- 存在しない ID は 404 を返す

### `GET /settings/webhooks`

```json
{
  "items": [
    {
      "id": 1,
      "name": "Discord alerts",
      "webhook_url": "https://discord.com/api/webhooks/1/token",
      "created_at": "2026-08-02 10:00:00",
      "updated_at": "2026-08-02 10:00:00"
    }
  ]
}
```

### `POST /settings/webhooks`

Request:

```json
{ "name": "Discord alerts", "webhook_url": "https://discord.com/api/webhooks/1/token" }
```

Response (201):

```json
{
  "id": 1,
  "name": "Discord alerts",
  "webhook_url": "https://discord.com/api/webhooks/1/token",
  "created_at": "2026-08-02 10:00:00",
  "updated_at": "2026-08-02 10:00:00"
}
```

- `name` は必須で、空白のみの場合は 422 を返す
- 登録済みと同じ URL は 409 を返す

### `DELETE /settings/webhooks/{id}`

- 204 を返す
- 存在しない ID は 404 を返す

### `POST /settings/webhook/ping`

Request:

```json
{ "webhook_url": "https://discord.com/api/webhooks/1/token" }
```

Response:

```json
{ "pong": true }
```

### `GET /settings/rss-execution`

```json
{ "enabled": false }
```

### `PUT /settings/rss-execution`

Request:

```json
{ "enabled": true }
```

Response:

```json
{ "enabled": true }
```

### `GET /settings/rss-webhook-notification`

```json
{ "enabled": false }
```

### `PUT /settings/rss-webhook-notification`

Request:

```json
{ "enabled": true }
```

Response:

```json
{ "enabled": true }
```

### `GET /rss-feeds/{id}`

- 指定 ID の RSS フィードを返す

### `GET /rss-feeds/{id}/articles`

- 保存済み記事の一覧を返す
- `published` を日時として比較し、新しい記事から古い記事の順で返す。`published` がない記事は末尾に配置する
- `q`、`published_from`、`published_to`、`page`、`per_page` を受け付ける

Response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "per_page": 20,
  "total_pages": 0
}
```

### `POST /rss-feeds/{id}/execute`

- フィード URL を取得して RSS として解析する
- 登録済み webhook URL がない場合は 400 を返す
- フィードに通知先 webhook が選択されている場合は選択先のみ、未選択の場合は登録済みの全 webhook に送信する
- 新規記事のみ webhook に送信する
- 一部の webhook が失敗しても、1 件でも成功すれば成功として `delivered_count` に成功件数を返す
- すべての webhook が失敗した場合は 502 を返し、記事は送信済みに記録しない
- `notify_webhook_enabled` は batch の定期実行でのみ参照する
- 新規記事がない場合も成功として扱い、メッセージを返す
- 送信済み記事は `rss_feed_articles` に保存済みとして追記する

### `GET /health`

Response:

```json
{ "status": "ok" }
```
