# 概要

この API は、ブックマーク、RSS フィード、LLM-assisted custom news site、フォルダ、タグ、アプリ設定を管理する FastAPI サービスである。

この配下の仕様書は、`specs/product/requirements.md` の要件を実装視点に分解したものとして扱う。
`specs/product/requirements.md` はプロダクト要件、`specs/components/api/` は API の入出力と挙動を中心に記述する。

## 主な特徴

- SQLite による永続化
- ブックマーク、RSS リンク、フォルダ、タグの CRUD
- `metrics` によるダッシュボード集計の取得
- `settings` によるアプリ全体設定の管理
- RSS 実行 API、RSS 記事の保存済み一覧取得、Discord/Slack/Microsoft Teams webhook 通知
- Ollama、vLLM、OpenAI 互換 LLM の疎通確認付き設定保存
- custom news site 登録時の HTML 取得、LLM selector 生成、実抽出テスト
- custom news site の CRUD、手動実行、記事履歴、webhook 通知
- 手動 RSS 実行は API が直接 RSS 取得と webhook 通知を行う
- Rust の `batch` は RSS 定期実行が有効な場合のみ巡回処理を担う
- ブックマークへのタグ付与・解除
- ブックマークのお気に入り状態切り替え
- フォルダとタグの単一取得 API
- `/health` による疎通確認
- webhook 疎通確認用の ping API
- RSS 実行の有効/無効設定
- RSS 定期実行時の webhook 通知有効/無効設定
- 例外ハンドリングと検証エラーの標準化

## 主要ファイル

- [アプリケーション本体](../../../api/main.py)
- [DB 初期化](../../../api/database.py)
- [ブックマークルータ](../../../api/routers/bookmarks.py)
- [RSS ルータ](../../../api/routers/rss_feeds.py)
- [集計ルータ](../../../api/routers/metrics.py)
- [設定ルータ](../../../api/routers/settings.py)
- [Custom news site ルータ](../../../api/routers/news_sites.py)
- [フォルダルータ](../../../api/routers/folders.py)
- [タグルータ](../../../api/routers/tags.py)
- [タグ付与ルータ](../../../api/routers/bookmark_tags.py)
- [ブックマークサービス](../../../api/services/bookmark_service.py)
- [RSS サービス](../../../api/services/rss_feed_service.py)
- [集計サービス](../../../api/services/dashboard_service.py)
- [設定サービス](../../../api/services/settings_service.py)
- [LLM サービス](../../../api/services/llm_service.py)
- [Custom news site サービス](../../../api/services/news_site_service.py)
- [フォルダサービス](../../../api/services/folder_service.py)
- [タグサービス](../../../api/services/tag_service.py)
- [モデル定義](../../../api/model/models.py)

## 仕様の範囲

- 含めるもの
  - HTTP ルート
  - リクエスト/レスポンスの形
  - 代表的な成功・失敗パターン
  - DB 制約に起因する挙動

- 含めないもの
  - UI の見た目
  - フロントエンドの状態管理
  - 実装手順や作業順序
