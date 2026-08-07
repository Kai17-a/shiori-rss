# Frontend 仕様

Nuxt 4 SPA は RSS 専用 UI を提供する。

- `/` は `/rss` へリダイレクトする。
- `/rss` はフィード一覧、作成・更新・削除、手動実行、定期実行設定を提供する。
- `/rss/{id}` はフィード詳細と記事履歴を提供する。
- `/settings` はテーマ、Webhook、LLM接続設定を提供する。
- サイドバーには RSS、登録済みフィード、Settings だけを表示する。
- API 呼び出しは `useApi` と `/api` reverse proxy を通す。
