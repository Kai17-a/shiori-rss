# LLM 読み学習ガイド

このドキュメントは、このリポジトリで作業する LLM が先に読むことを想定した入口である。
Nuxt、Python、Nuxt UI、TypeScript の実装方針を短く集約し、参照順を明確にする。

## 読む順番

1. [README.md](../README.md)
1. [Specs index](./README.md)
1. [要件定義](./product/requirements.md)
1. [技術設計](./architecture/system-design.md)
1. [DB 定義](./architecture/data-model.md)
1. [フロントエンド仕様](./components/frontend/README.md)
1. [API仕様](./components/api/README.md)
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

### Batch

- `batch/` は Rust 製の通常RSS定期巡回・保存済み記事AI解析プロセスである
- API サーバーとは別プロセスとして動作し、HTTP ルートは持たない
- SQLite の `app_settings`、通常RSS、通常RSS・カスタムRSSの記事、AI解析結果・使用量テーブルを直接読む
- Webhook送信成功後に `rss_feed_articles.webhook_notified` を更新する
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
