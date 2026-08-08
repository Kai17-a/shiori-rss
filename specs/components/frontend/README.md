# Frontend 仕様

Nuxt 4 SPA は RSS 専用 UI を提供する。

- `/` は `/feeds` へリダイレクトする。
- `/feeds` はRSS専用ホームとしてフィード一覧、作成・更新・削除、手動取得、定期実行設定を提供する。
- `/feeds/{id}` はフィード詳細と記事履歴を提供する。
- `/settings` はテーマ、Webhook、LLM接続設定を提供する。
- サイドバーには All feeds、登録済みフィード、Preferences だけを表示する。
- 旧 `/rss` ルートは提供しない。
- API 呼び出しは `useApi` と `/api` reverse proxy を通す。
