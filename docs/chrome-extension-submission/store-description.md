# Chrome Web Store Description

Shiori Keeper is a browser extension for saving the page you are viewing into the Shiori Keeper app with a title, URL, and optional notes. It is designed for people who want to keep bookmarks, folders, tags, and RSS feeds in one place without losing the context of where a link came from.

Open the popup from your browser toolbar, confirm the current page title and URL, choose a folder or tags if needed, and save the bookmark to your Shiori Keeper server. The extension also lets you check the API connection, update existing entries by URL, and delete bookmarks directly from the popup.

## What Shiori Keeper Includes

- Save bookmarks with a title, URL, description, folder, and tags
- Update or delete bookmarks later
- Organize bookmarks with folders and tags
- Search and browse saved links in the main web app
- Track RSS feeds alongside bookmarks
- Configure and test a Discord webhook for RSS notifications
- View counts and recent items on the dashboard

## What the Extension Does

- Captures the current browser tab title and URL
- Stores the API server URL in `chrome.storage.local`
- Sends bookmark data to your Shiori Keeper API server
- Supports quick saving from the popup
- Provides a compact UI for editing and deleting saved bookmarks
- Verifies the API connection before saving

## Notes

- The extension is designed to work with a locally running or self-hosted Shiori Keeper server.
- Existing bookmarks are updated by URL when possible.
- Invalid URLs cannot be saved.

Shiori Keeper helps turn a growing list of saved links into an organized, searchable collection that is easy to maintain over time.

Project link: https://github.com/Kai17-a/shiori-keeper

---

# Chrome ウェブストア向け説明

Shiori Keeper は、閲覧中のページをタイトル、URL、必要に応じたメモ付きで Shiori Keeper アプリに保存できるブラウザ拡張機能です。ブックマーク、フォルダ、タグ、RSS フィードを 1 か所で管理したい人向けに設計されています。

ブラウザのツールバーからポップアップを開き、現在のページのタイトルと URL を確認し、必要に応じてフォルダやタグを選んで、Shiori Keeper サーバーへブックマークを保存します。拡張機能からは API 接続の確認、URL をもとにした既存項目の更新、ポップアップからのブックマーク削除も行えます。

## Shiori Keeper でできること

- タイトル、URL、説明、フォルダ、タグ付きでブックマークを保存する
- 後からブックマークを更新または削除する
- フォルダとタグでブックマークを整理する
- メインの Web アプリで保存したリンクを検索・閲覧する
- ブックマークとあわせて RSS フィードを管理する
- RSS 通知用の Discord Webhook を設定・確認する
- ダッシュボードで件数や最近の項目を確認する

## 拡張機能でできること

- 現在のブラウザタブのタイトルと URL を取得する
- API サーバー URL を `chrome.storage.local` に保存する
- ブックマークデータを Shiori Keeper API サーバーに送信する
- ポップアップから素早く保存できる
- 保存済みブックマークの編集と削除に対応する
- 保存前に API 接続を確認する

## 注意事項

- この拡張機能は、ローカルで動作する Shiori Keeper サーバーまたはセルフホスト環境での利用を前提としています。
- 既存のブックマークは、可能な場合 URL をもとに更新されます。
- 無効な URL は保存できません。

Shiori Keeper は、増え続ける保存リンクを整理し、検索しやすく、維持しやすい形に整えるのに役立ちます。
