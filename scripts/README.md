# Scripts

実行スクリプトは用途別に配置する。日常的な操作では、パスを直接指定せず `mise run <task>` を使用する。

- `container/`: Dockerイメージの起動とスケジューラー設定
- `development/`: ローカル開発サーバーの起動
- `documentation/`: READMEなどのドキュメント用成果物の生成
- `repository/`: Git hooksなどリポジトリ固有の初期設定
- `testing/`: 単体・統合・E2Eテストの実行補助
- `image-resizer/`, `png2ico/`: 画像アセットを変換する独立したRustツール

タスクを追加・移動した場合は、`mise.toml`とスクリプトを参照するCI・Docker設定も同時に更新する。
