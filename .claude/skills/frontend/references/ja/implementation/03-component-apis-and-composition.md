# コンポーネントAPIと合成

> [frontendスキル](../../../SKILL.md)の一部です。

## 意図を中心にAPIを設計する

生のスタイリングだけを公開するAPIより、呼び出し元の意図を表現するAPIを優先してください。`<Status status="degraded" />`と書く呼び出し元は、それを描画しているのがどのビジュアルprimitiveかを知る必要がないはずです。

---

## ドメインコンポーネントとUI primitive

ドメイン固有のコンポーネントが、汎用的なprimitiveより本質的に優れているわけではありません。両方に居場所があります。ドメインコンポーネントは、外部には意図ベースのAPIを公開しつつ、内部では確立されたprimitiveを再利用できます。

```tsx
function Status({ status }: StatusProps) {
  return <Badge tone={statusTone[status]}>{statusLabel[status]}</Badge>;
}
```

呼び出し元は`<Status status="degraded" />`と書き、ドメインの言葉で考えます。内部実装では、独自にバッジの描画を再実装するのではなく`Badge`というprimitiveを再利用しています。

---

## Props と composition の使い分け

バリエーションが小さく閉じた集合である場合はpropsを使ってください。呼び出し元がそのコンポーネントに事前に知らせる必要のない構造やコンテンツを制御したい場合は、children/slotsによるcompositionを使ってください。

---

## variantとsemantic prop

`variant="primary"`のようなvisual propは、デザインシステムのprimitiveでは妥当です。ドメインコンポーネントでは、visual propよりsemantic propを優先してください。`status="degraded"`は`color="yellow"`より多くを伝え、将来のスタイル変更にも耐えられます。

---

## 相互排他的な状態は型で表現する

loading・disabled・errorのように同時には起こり得ない状態を、独立した複数のboolean propsとしてモデル化しないでください。union型として表現し、矛盾する組み合わせが単に「ドキュメント化されていない」のではなく「表現不可能」になるようにしてください。

---

## boolean propsの組み合わせ爆発を避ける

boolean propが増えるたびに、呼び出し元と保守者が考慮すべき状態の数が掛け算的に増えます。複数のbooleanが連動する傾向がある場合は、それらを結果として生じる状態を直接表す単一のpropに置き換えてください。

---

## controlled/uncontrolled APIを混在させない

同じコンポーネント内でcontrolledパターンとuncontrolledパターンを混在させないでください。どちらをサポートするかを決めて明文化し、value/defaultValueとonChangeの契約をその選択と一貫させてください。

---

## Native要素の属性とアクセシビリティ

理由なくnative HTML属性を隠さないでください。インタラクティブな要素をラップするコンポーネントは、独自の狭い代替APIを発明するのではなく、標準的な属性やアクセシビリティ関連のpropsを基本的にそのまま透過させてください。

---

## イベントとコールバックの命名

コールバックpropの名前は、それをトリガーする内部の仕組みではなく、それが表すイベントにちなんで付けてください(`onSave`, `onStatusChange`)。こうしておくと、内部実装が変わってもAPIは安定したままになります。

---

## Escape hatch

本当に一回限りのニーズのために、限定的なescape hatch(`className`やスタイルの上書き等)を用意してかまいません。ただし、それが呼び出し元の標準的な使い方にならないようにしてください。多くの呼び出し元がescape hatchに頼っている場合、そのAPIは本来直接サポートすべきケースを欠いています。

---

## APIの進化と後方互換性

既存コンポーネントの公開APIを変更する前に、何がすでにそれに依存しているかを確認してください。両方が妥当な場合は破壊的変更より追加的な変更を優先し、破壊的変更が避けられない場合は、同じ変更の一部としてすべての呼び出し箇所を更新してください。
