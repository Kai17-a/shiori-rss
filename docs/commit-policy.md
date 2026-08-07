# コミット規約

このリポジトリでは [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) を基本とする。

## 目的

- 履歴を読みやすくする
- 自動化しやすくする
- revert しやすくする
- code / test / spec の整合性を保つ

## コミットタイプ

- `feat`: 機能追加
- `fix`: 不具合修正
- `docs`: ドキュメントのみ
- `test`: テストのみ
- `refactor`: 振る舞いを変えないリファクタリング
- `chore`: 保守作業
- `revert`: 既存コミットの取り消し

## ルール

- 1 コミットは 1 つの機能単位の変更にする
- 機能単位は、ユーザーに見える振る舞いの追加・修正・削除を 1 つのまとまりとして扱う
- 1 コミットに無関係な修正を混ぜない
- 1 つの機能に紐づくコード・テスト・仕様書は同じコミットに含める
- `revert` したら、対応するテストと設計書・仕様書も戻す
- `rebase` などで履歴を巻き戻した結果、消えた振る舞いの記述は残さない
- 巻き戻し後は、実装・テスト・設計書・仕様書が同じ状態を指すか確認する

## 望ましいコミット例

```text
feat(api): add bookmark tag attachment endpoint
fix(frontend): handle empty settings response
docs(specs): update api traceability for bookmark routes
revert: feat(api): add bookmark tag attachment endpoint
```

## 巻き戻し時の確認

`revert` / `rebase` / `reset` 相当の操作後は、少なくとも次を確認する。

- 変更済みテストが不要になっていないか
- 追加した仕様書や設計書が残っていないか
- 逆に、必要な仕様書更新が巻き戻されていないか
- 実装と仕様の差分が新しく発生していないか
