# 概要

この拡張機能は、現在開いているタブのタイトルと URL を取得し、Shiori Keeper の API サーバーにブックマークを保存する Manifest V3 拡張である。

## 主な特徴

- `browser_extension/entrypoints/popup/` のポップアップ UI から現在タブの情報を取得する
- API サーバー URL を入力欄で変更でき、WebExtension の `browser.storage.local` に保存して復元する
- API サーバー URL のデフォルトは `http://localhost:8000` である
- API `/health` を使って接続確認を行う
- 接続成功時に現在タブの URL で既存ブックマークを取得し、あればフォームに反映する
- `/folders` と `/tags` を取得して、保存時にフォルダとタグを選択できる
- 保存時は `/bookmarks/by-url` で既存ブックマークの更新を試み、`404` の場合のみ `/bookmarks` で新規作成する
- URL による削除を行える
- ポップアップのみで動作し、background worker や content script は登録しない

## 主要ファイル

- [Manifest 設定](../../../browser_extension/wxt.config.ts)
- [ポップアップ UI](../../../browser_extension/entrypoints/popup/App.vue)
- [ポップアップエントリ](../../../browser_extension/entrypoints/popup/main.ts)
- [ポップアップスタイル](../../../browser_extension/entrypoints/popup/style.css)
- [Popup API utility](../../../browser_extension/utils/popupBookmark.ts)
