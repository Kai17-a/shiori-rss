# テスト観点

## 単体テスト

- `frontend/tests/bookmarkApi.test.ts`
  - Trailing slash trimming
  - API base fallback resolution
  - Request header construction
  - Error message normalization
  - Frontend API path coverage including bookmarks, folders, tags, RSS feeds, custom news sitesの任意再解析, metrics, LLM settings, and webhook summary settings

- `frontend/tests/sidebarCatalog.test.ts`
  - Empty sidebar state creation
  - Catalog result application
  - RSS フィードと custom news site を含むサイドバーカタログ反映
  - 初回カタログ失敗を未処理例外にせず、強制再取得できること

- `frontend/tests/apiHealth.test.ts`
  - health state の初期値
  - `/health` の正常、異常、通信失敗を利用可否へ正規化すること

- `frontend/tests/nginxConfig.test.ts`
  - 外部 reverse proxy 配下で公開 scheme、host、port を維持する相対 redirect 設定

## E2E テスト

- `frontend/tests/e2e/bookmark-manager.spec.ts`
  - Bookmark の画面上での create, edit、description の解除, search, delete
  - 範囲外の bookmark page を有効なページへ正規化し、検索後に URL と表示を同期すること
  - Favorites page load, 21件以上のページング閲覧, and favorite toggle
  - Folder の画面上での create, rename, detail navigation, detail delete
  - Tag の画面上での create, rename, detail navigation, detail delete
  - RSS feed の画面上での create, edit, detail navigation, 最終ページ削除後のページ正規化, delete
  - RSS feed 作成・編集モーダルでの通知先 webhook 選択（未選択時は全 webhook 通知）
  - Settings page での webhook 複数登録, URLごとの通知有効切り替え, reload 後の状態維持, delete
  - RSS periodic execution toggle
  - Settings page theme toggle

## 未カバー範囲

- ページ/コンポーネント単体のテストはない
- API 初回疎通失敗時のダッシュボードシェル継続描画は明示的に検証していない
- RSS 実行後のサイドバー再同期は明示的に検証していない
- Bookmark 作成時の folder/tag 割り当ては明示的に検証していない
- Folder/Tag 詳細上の関連 bookmark 編集、削除、お気に入り切り替えは明示的に検証していない
- RSS webhook ping、手動実行、記事一覧の paging は明示的に検証していない
- LLM 設定画面と custom news site のブラウザ E2E は、外部 LLM test server を必要とするため明示的に検証していない
- オフラインやバックエンド停止時の描画を、手動のエラー処理以外で明示的に検証するテストはない

## 実装候補

- `frontend/tests/bookmarkApi.test.ts`
  - `/settings/webhooks`, `/settings/webhook/ping`, `/settings/rss-execution`, `/metrics/dashboard`, `/bookmarks/by-url`, `/bookmarks/favorite`, `/rss-feeds/{id}/articles` の request path と body を明示確認する

- `frontend/tests/sidebarCatalog.test.ts`
  - folders/tags に加えて RSS feeds を含む結果が状態へ反映されることを確認する
  - refresh 後に既存 state が最新 catalog へ置き換わることを確認する

- `frontend/tests/apiHealth.test.ts`
  - API 到達成功と失敗で health state が切り替わることを確認する
  - 初回失敗時でも UI 側で致命的エラーにしない前提の state を確認する

- `frontend/tests/e2e/bookmark-manager.spec.ts`
  - `/favorites` で favorite のみが表示され、21件以上をページング閲覧でき、解除で一覧から消えることを確認する
  - bookmark 作成時の folder/tag 割り当てが detail/filter と整合することを確認する
  - `/folders/[id]` と `/tags/[id]` で関連 bookmark の編集、削除、お気に入り切り替え、21件以上のページング閲覧を確認する
  - `/settings` で webhook の load, ping, 複数登録, delete を確認する
  - `/rss` で RSS periodic execution toggle を確認する
  - `/rss/[id]` で article list と paging を確認する
  - `/settings` で theme change が reload 後も維持されることを確認する

## 追加ルール

- フロントエンドに共通 `fetcher` や API 基盤のような横断的な実装を追加した場合は、対応する unit テストか e2e テストも同時に追加する
- `bun run typecheck` でページ、コンポーネント、composable の型整合性を検証する
