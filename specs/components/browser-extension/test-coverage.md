# テスト観点

- API URL の初期値が表示され、手動で変更できること
- API URL の保存と復元ができること
- 現在タブのタイトルと URL が入力欄に反映されること
- `/health` の結果に応じて接続状態が更新されること
- API 接続成功時に URL から既存ブックマークを取得して初期値へ反映すること
- フォルダ一覧とタグ一覧が読み込まれること
- 新規保存、既存ブックマークの更新、URL ベースの削除が実行できること
- 既存ブックマークの取得で `GET /bookmarks/by-url?url=...` を使うこと
- 保存時に `PATCH /bookmarks/by-url` が `404` の場合は `POST /bookmarks` にフォールバックすること
- Close ボタンでポップアップが閉じること
- 保存成功時と削除成功時に完了メッセージが表示されること

## 自動テスト

- `browser_extension/tests/popupBookmark.test.ts`
  - 登録 payload に数値の `folder_id` と `tag_ids` を含める
  - URL 指定 PATCH が成功した場合は POST しない
  - URL 指定 PATCH が 404 の場合だけ POST へフォールバックする
  - 接続成功時の登録、フォルダ取得、タグ取得を各一度だけ実行する
  - 同じ API 接続先の再確認では初期化を繰り返さず、接続先を変更した場合は新たに初期化する

## 実装候補

- popup 初期化テスト
  - `browser.tabs.query`
  - `browser.storage.local.get` と `browser.storage.local.set`
  - `/health` 成功時の既存ブックマーク取得試行
  - `/folders` と `/tags` の取得
  - `/bookmarks/by-url?url=...` の取得と初期値反映

- popup 保存フローテスト
  - `PATCH /bookmarks/by-url?url=...`
  - `PATCH /bookmarks/by-url` が `404` のときは `POST /bookmarks` にフォールバックする
  - folder/tag 選択値が payload に含まれる

- popup 削除/補助操作テスト
  - `DELETE /bookmarks?url=...`
  - Close button による close
