# 要件対応表

`specs/product/requirements.md` の要件番号と、この API 仕様書の対応を示す。

## 対応表

| requirements                          | api                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------ |
| 要件1: ブックマーク管理               | `routes-and-flows.md` のブックマーク節、`data-and-constraints.md` の制約 |
| 要件2: フォルダ管理                   | `routes-and-flows.md` のフォルダ節、`data-and-constraints.md` の制約     |
| 要件3: タグ管理                       | `routes-and-flows.md` のタグ節、`data-and-constraints.md` の制約         |
| 要件4: ブックマークへのタグ付与・解除 | `routes-and-flows.md` のタグ付与節                                       |
| 要件5: 永続化とエラー処理             | `data-and-constraints.md` のデータモデル・制約                           |
| 要件6: RSS フィード管理               | `routes-and-flows.md` の RSS 節、`data-and-constraints.md` の制約       |
| 要件7: Webhook 設定、RSS 定期実行、集計 | `routes-and-flows.md` の設定・ダッシュボード節、`data-and-constraints.md` の制約 |
| 要件8: LLM 設定とカスタムニュースサイト | `routes-and-flows.md` の設定・カスタムニュースサイト節、`data-and-constraints.md` の制約 |

## 補足

- `specs/product/requirements.md` は何を作るかを定義する。
- `specs/components/api/` はどう返すか、どう失敗するかを定義する。
- 実装変更時は要件変更より先に API 仕様の差分を確認する。
