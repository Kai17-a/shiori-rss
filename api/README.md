# API

このディレクトリは FastAPI バックエンド本体とテストを含む。

## 起動

```bash
api-dev
```

`api-dev` は `fastapi dev` を使って起動する。
起動時に `../db/migrations` の未適用 migration を自動適用する。別の場所から migration を読み込む場合は `MIGRATIONS_DIR` を指定する。
`DATABASE_URL` を省略した場合はリポジトリ直下の `data/data.db` を使う。

## テスト

```bash
python -m pytest -q
uv run ruff check .
```

## 主要ファイル

- [アプリケーション本体](./main.py)
- [DB 初期化](./database.py)
- [モデル定義](./model/models.py)
- [ルータ群](./routers/)
- [サービス層](./services/)
- [リポジトリ層](./repositories/)
- [テスト](./tests/)
