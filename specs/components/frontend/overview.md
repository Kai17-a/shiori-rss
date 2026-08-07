# 概要

このフロントエンドは、API 経由でブックマーク、お気に入り、RSS フィード、LLM-assisted custom news site、フォルダ、タグ、設定を管理する Nuxt 4 の SPA である。

## 主な特徴

- ダッシュボード型のシェルにサイドバー中心のナビゲーションを持つ
- ブックマーク、RSS フィード、フォルダ、タグの CRUD 画面を持つ
- お気に入り専用の一覧画面を持つ
- フォルダとタグの詳細画面を持つ
- RSS フィードと custom news site の詳細・記事履歴画面を持つ
- フォルダ詳細画面とタグ詳細画面は、それぞれ ID 指定の取得 API を使って対象を先に表示する
- 設定画面はテーマ、webhook、Ollama・vLLM・OpenAI 互換 LLM 接続の管理を担う
- RSS 一覧画面で RSS の定期実行設定を扱う
- 主要な作成・編集・削除フローは E2E で確認する

## 主要ファイル

- [レイアウト](../../../frontend/app/layouts/default.vue)
- [ダッシュボード](../../../frontend/app/pages/index.vue)
- [ブックマーク一覧](../../../frontend/app/pages/bookmarks.vue)
- [お気に入り一覧](../../../frontend/app/pages/favorites.vue)
- [フォルダ一覧](../../../frontend/app/pages/folders/index.vue)
- [フォルダ詳細](../../../frontend/app/pages/folders/[id].vue)
- [タグ一覧](../../../frontend/app/pages/tags/index.vue)
- [タグ詳細](../../../frontend/app/pages/tags/[id].vue)
- [RSS 一覧](../../../frontend/app/pages/rss/index.vue)
- [RSS 詳細](../../../frontend/app/pages/rss/[id].vue)
- [Custom news site 詳細](../../../frontend/app/pages/rss/news/[id].vue)
- [設定画面](../../../frontend/app/pages/settings.vue)
- [API ヘルパー](../../../frontend/app/composables/useBookmarkApi.ts)
- [サイドバーカタログ](../../../frontend/app/composables/useSidebarCatalog.ts)
