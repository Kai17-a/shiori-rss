# Frontend 仕様

Nuxt 4 SPA は RSS 専用 UI を提供する。

- `/` はRSS専用ホームとしてフィード一覧、作成・更新・削除、手動取得を直接提供する。
- 旧フィード一覧ルート `/feeds` は提供しない。
- `/feeds/{id}` はフィード詳細と記事履歴を提供する。
- `/` は通常のRSS / Atomと、LLM解析で作るカスタムRSSをタブで切り替え、各タブで登録・一覧・手動取得を提供する。
- `/custom-feeds/{id}` はカスタムRSSの詳細と抽出済み記事を提供する。
- `/settings` は General、Automation、Webhooks、LLM のカテゴリタブを持ち、テーマ、定期取得、全体通知、Webhook、LLM接続設定を提供する。
- 一覧と設定画面は宣伝的なヒーローやキャッチコピーを置かず、操作対象を先頭に表示する。
- サイドバーには All feeds、登録済みフィード、Preferences だけを表示する。
- 旧 `/rss` ルートは提供しない。
- API 呼び出しは `useApi` と `/api` reverse proxy を通す。
