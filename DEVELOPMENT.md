# 開発ガイド

このドキュメントはローカル開発向けの手順をまとめる。
OSS 利用者向けの案内は [README.md](./README.md) を参照する。

すべての開発コマンドは `mise run <task>` として定義している。利用可能な一覧と説明は `mise tasks` で確認できる。

## ローカル起動

### API

```bash
cd api
api-dev
```

`api-dev` は `fastapi dev` を使って起動する。

### Frontend

```bash
mise install
cd frontend
bun install
bun run dev
```

`bun` は `mise.toml`、CI、Dockerfile で `1.3.12` に固定している。

### 両方まとめて起動

```bash
mise run dev
```

API は `http://127.0.0.1:8000`、frontend は `http://127.0.0.1:3000` で起動し、どちらもリポジトリ直下の `data/data.db` を使う。`API_PORT`、`FRONTEND_PORT`、`DATABASE_URL` で変更できる。

### GitHub Actions をローカル実行

GitHub Actions のワークフローをローカルで再現する場合は `mise exec act -- ...` を使う。

```bash
mise exec -- act pull_request -W .github/workflows/pr-tests.yml
```

`act` は `mise.toml` で管理しているので、先に `mise install` を実行しておく。
別のワークフローを試す場合は、`-W` のパスとイベント名を変える。

```bash
mise exec -- act push -W .github/workflows/release-on-tag.yml
```

### Docker を使う場合

```bash
docker compose up --build
```

`docker-compose.yml` はローカル開発向けのサンプルで、`Dockerfile` をビルドして起動する。

```yaml
services:
  shiori-keeper:
    container_name: shiori-keeper
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: /data/data.db
    ports:
      - "3001:3000"
      - "8005:8000"
    volumes:
      - ./data:/data
```

Docker 起動時は API を `fastapi run api/main.py` で起動し、1 つのコンテナでフロントエンドと API を利用できる。
フロントエンドは `/api` を使い、nginx がそれをコンテナ内の FastAPI (`127.0.0.1:8000`) に転送する。
同じコンテナでは Supercronic がバッチを毎時実行する。API、nginx、Supercronic のいずれかが停止した場合は、残りのプロセスも終了してコンテナを失敗終了させる。
公開イメージの対象アーキテクチャは `linux/amd64` と `linux/arm64` で、dbmate と Supercronic も各アーキテクチャ向けのバイナリを組み込む。
そのため、ホスト側の公開ポートを変えても、ブラウザからは `http://localhost:3001/api/...` のようにアクセスできる。
`docker compose` で `3001:3000` と `8005:8000` に変えた場合も、ブラウザからの API 呼び出しは `http://localhost:3001/api/...` のまま動作する。
API 直アクセスは `http://localhost:8005/...` で行える。
`API_PORT` はコンテナ内の FastAPI 待受ポートを変える場合だけ使う。

### GitHub Packages を使う場合

GitHub Packages の Docker image 公開機能を使う場合は、別途ワークフローを用意する。
`GITHUB_TOKEN` に `packages: write` 権限が付くように設定する。

## Push 前チェック

ローカルから `git push` する前に同じ検査を走らせるには、次を設定する。

```bash
./scripts/setup-repo.sh
```

この設定を入れると、この workspace の `.git/config` にだけ `core.hooksPath` が記録される。
`.githooks/pre-push` が実行され、コミットメッセージの Conventional Commits 検査に加えて、API の `ruff check`、API テスト、frontend の unit test が push 前に走る。

### Git 運用

- ブランチの作成単位は `git flow` に基づく
- 作業は `main` から直接ではなく、用途に応じたブランチを切って進める
- コミットは機能単位にする
- 1 コミットは 1 つの意味のある変更に限定する
- PR 内の作業中コミットは自由だが、マージ前に整理する
- マージ時は squash merge を基本にする
- 変更が完了したら、そのブランチ上で Conventional Commits 形式のコミットにまとめてから共有する
- changelog は `feat`, `fix`, `perf`, `revert` を中心にする

### コミット例

- `feat(frontend): add RSS article filter`
- `fix(api): prevent duplicate feed creation`
- `perf(frontend): reduce feed list rerenders`
- `revert(api): restore feed delete behavior`
- `docs(specs): sync extension flow`
- `chore(deps): update frontend packages`

避ける例:

- `fix stuff`
- `update`
- `WIP`
- `misc changes`

### Changelog の見え方

このリポジトリでは `git-cliff` の changelog に、公開価値のある変更だけを載せる。

```md
## [1.2.3] - 2026-04-19

### Features
- *(frontend)* Add RSS article filter
```

- `fix`, `perf`, `revert` も同じ形式で載る
- `docs`, `test`, `chore`, `ci`, `style`, `refactor` は載せない

push 前に API、batch、frontend、ブラウザ拡張、E2E の lint・型検査・テスト・配布ビルドをまとめて手動実行したい場合は次を使う。

```bash
mise run test-all
```

この workspace でコードやテストを修正したら、最後に変更を commit する。

## テスト

### API

```bash
mise run api-test
```

### Frontend

```bash
mise run frontend-test
mise run frontend-typecheck
mise run e2e
```

`e2e:run` は結果ログを `.artifacts/playwright-e2e.log` に保存する。
`e2e:headed` はブラウザを開いて実行する。
`e2e:run` は API と frontend を個別に起動し、`http://127.0.0.1:8001` と `http://127.0.0.1:3001` を使って E2E を実行する。
初回だけ Playwright の OS 依存ライブラリを `cd frontend && bunx playwright install --with-deps chromium` で導入する。各 E2E スクリプトは、現在の Playwright が要求する Chromium 本体を実行前に確認・導入する。

### Browser Extension

```bash
mise run extension-test
mise run extension-typecheck
mise run extension-build
```

## ローカル URL

- 通常起動のフロントエンド: `http://127.0.0.1:3000`
- 通常起動の API: `http://127.0.0.1:8000`
- E2E のフロントエンド: `http://127.0.0.1:3001`
- E2E の API: `http://127.0.0.1:8001`
