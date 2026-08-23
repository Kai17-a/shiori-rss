# Component APIs and Composition

> Part of the [Frontend skill](../../SKILL.md).

## Design APIs Around Intent

Prefer an API that expresses what the caller means over one that only exposes raw styling. A caller writing `<Status status="degraded" />` should not need to know which visual primitive renders it.

---

## Domain Components and UI Primitives

A domain-specific component is not inherently better than a generic primitive — both have a place. A domain component can expose an intent-based API on the outside while reusing an established primitive internally:

```tsx
function Status({ status }: StatusProps) {
  return <Badge tone={statusTone[status]}>{statusLabel[status]}</Badge>;
}
```

Callers use `<Status status="degraded" />` and think in domain terms. Internally, `Status` reuses the `Badge` primitive instead of reimplementing its own badge rendering.

---

## Props versus Composition

Use props when the variation is a small, closed set of configurations. Use children/slots-based composition when callers need to control structure or content that the component should not need to know about in advance.

---

## Variants and Semantic Props

A visual prop such as `variant="primary"` is appropriate on a design-system primitive. On a domain component, prefer a semantic prop over a visual one — `status="degraded"` communicates more than `color="yellow"` and survives a future restyle.

---

## Model Exclusive States with Types

States that cannot occur simultaneously — loading, disabled, error — should not be modeled as independent boolean props. Model them as a union so that contradictory combinations are unrepresentable rather than merely undocumented.

---

## Avoid Boolean Prop Explosion

Each new boolean prop multiplies the number of states callers and maintainers must reason about. When several booleans tend to correlate, replace them with a single prop that names the resulting state directly.

---

## Controlled and Uncontrolled APIs

Do not blend controlled and uncontrolled patterns in the same component. Decide which one the component supports, document it, and keep the value/defaultValue and onChange contract consistent with that choice.

---

## Native Element Attributes and Accessibility

Do not hide native HTML attributes without reason. A component wrapping an interactive element should generally forward standard attributes and accessibility props rather than inventing a narrower replacement API.

---

## Events and Callback Naming

Name callback props after the event they represent (`onSave`, `onStatusChange`), not after the internal mechanism that triggers them. This keeps the API stable even if the internal implementation changes.

---

## Escape Hatches

Provide a limited escape hatch (such as a `className` or style override) for genuine one-off needs, but do not let it become the default way callers use the component. If most callers reach for the escape hatch, the API is missing a case it should support directly.

---

## API Evolution and Backward Compatibility

Before changing an existing component's public API, check what already depends on it. Prefer an additive change over a breaking one when both are reasonable; when a breaking change is unavoidable, update every call site as part of the same change.
