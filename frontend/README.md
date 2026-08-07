# Frontend

このディレクトリは Nuxt 4 の SPA を含む。

## 起動

```bash
bun install
bun run dev
```

## テスト

```bash
bun run test
bun run typecheck
bun run e2e
bun run e2e:run
bun run e2e:headed
```

共通 `fetcher` や API 基盤のような横断的な実装を追加したときは、対応する unit テストか e2e テストも同時に追加する。

## 主要ファイル

- [Nuxt 設定](./nuxt.config.ts)
- [アプリ本体](./app/)
- [Playwright 設定](./playwright.config.ts)
- [Vitest 設定](./vitest.config.ts)
- [テスト](./tests/)
