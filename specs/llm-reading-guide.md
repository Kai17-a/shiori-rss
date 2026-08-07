# LLM 読み学習ガイド

このドキュメントは、このリポジトリで作業する LLM が先に読むことを想定した入口である。
Nuxt、Python、Nuxt UI、TypeScript の実装方針を短く集約し、参照順を明確にする。

## 読む順番

1. [README.md](../README.md)
1. [Specs index](./README.md)
1. [要件定義](./product/requirements.md)
1. [技術設計](./architecture/system-design.md)
1. [DB 定義](./architecture/data-model.md)
1. [Chrome 拡張機能仕様](./components/browser-extension/README.md)
1. [フロントエンド概要](./components/frontend/overview.md)
1. [フロントエンド制約](./components/frontend/constraints.md)
1. [API概要](./components/api/overview.md)
1. [APIデータと制約](./components/api/data-and-constraints.md)
1. [Batch 仕様](./components/batch/README.md)
1. 公式 LLM 参照資料
   - https://nuxt.com/modules/llms
   - https://nuxt.com/llms-full.txt
   - https://ui.nuxt.com/llms.txt
   - https://ui.nuxt.com/llms-full.txt
   - https://vuejs.org/llms-full.txt

## 技術別の重点

### Nuxt

- フロントエンドは `frontend/` 配下の Nuxt 4 SPA である
- `ssr: false` のクライアントサイドアプリとして動作する
- 画面は `app/pages/` のファイルベースルーティングで構成する
- 共通シェルは `app/layouts/default.vue` に集約する
- Nuxt の公式 LLM 参照資料も確認する
  - https://nuxt.com/modules/llms
  - https://nuxt.com/llms-full.txt

### Nuxt UI

- UI は `@nuxt/ui` を使って構成する
- ダッシュボード型レイアウト、サイドバー、フォーム、モーダル、トーストを中心に組み立てる
- 既存の Nuxt UI テーマとレスポンシブ制約を壊さない
- Nuxt UI の公式 LLM 参照資料も確認する
  - https://ui.nuxt.com/llms.txt
  - https://ui.nuxt.com/llms-full.txt

### TypeScript

- フロントエンドの実装は TypeScript 前提で統一する
- `frontend/app/composables/` と `frontend/app/utils/` に責務を分ける
- 型定義は `frontend/app/types/` に寄せる
- API との入出力は型を明示し、`any` に逃がさない
- Vue の公式 LLM 参照資料も確認する
  - https://vuejs.org/llms-full.txt

### Python

- バックエンドは `api/` 配下の Python 3.13+ の FastAPI サービスである
- ルータ、サービス、リポジトリ、モデルのレイヤー分離を維持する
- DB は SQLite を使用し、外部キー制約とエラー処理を明示的に扱う
- テストは `pytest` と `hypothesis` を中心に見る

### Chrome Extension

- 拡張機能は `browser_extension/` 配下にある Manifest V3 のブラウザ拡張である
- ポップアップ UI から現在タブのタイトルと URL を取り込み、API サーバーへブックマークを送信する
- API 接続確認、既存ブックマークの読み込み、削除もポップアップから行える
- 設計や申請文面を更新する場合は、拡張機能の仕様も `specs/components/browser-extension/` に反映する

### Batch

- `batch/` は Rust 製の RSS 定期巡回プロセスである
- API サーバーとは別プロセスとして動作し、HTTP ルートは持たない
- SQLite の `app_settings`、`rss_feeds`、`rss_feed_articles` を直接読む
- webhook 送信成功後に `rss_feed_articles` へ送信済み記事を記録する
- Rust SQLite access を変更する場合は `.agents/skills/learning/references/rustqlite/llm.txt` も確認する

## 参照すべき実装ファイル

### フロントエンド

- [Nuxt 設定](../frontend/nuxt.config.ts)
- [ルート一覧](../frontend/app/pages/)
- [レイアウト](../frontend/app/layouts/default.vue)
- [共通コンポーネント](../frontend/app/components/)
- [Composable](../frontend/app/composables/)
- [ユーティリティ](../frontend/app/utils/)
- [型定義](../frontend/app/types/)

### Chrome Extension

- [拡張機能仕様](./components/browser-extension/README.md)
- [Manifest 設定](../browser_extension/wxt.config.ts)
- [ポップアップ UI](../browser_extension/entrypoints/popup/App.vue)
- [ポップアップエントリ](../browser_extension/entrypoints/popup/main.ts)
- [ポップアップスタイル](../browser_extension/entrypoints/popup/style.css)
- [Background](../browser_extension/entrypoints/background.ts)
- [Content Script](../browser_extension/entrypoints/content.ts)

### Batch

- [Batch 仕様](./components/batch/README.md)
- [エントリポイント](../batch/src/main.rs)
- [DB アクセス](../batch/src/db.rs)
- [実行フロー](../batch/src/runner.rs)
- [webhook 送信](../batch/src/webhook.rs)

### API

- [Python プロジェクト設定](../api/pyproject.toml)
- [アプリケーション本体](../api/main.py)
- [DB 初期化](../api/database.py)
- [ルータ群](../api/routers/)
- [サービス層](../api/services/)
- [リポジトリ層](../api/repositories/)
- [モデル定義](../api/model/)

## 期待する読み方

- 先に仕様を読む
- 次に実装ファイルを読む
- 迷ったら既存の仕様と実装の整合性を優先する
- 新しい実装は、既存の構造と命名を壊さずに追加する
- changelog 対象は公開価値のある `feat`, `fix`, `perf`, `revert` に寄せ、内部整理や作業用コミットは changelog 出力に載せない
