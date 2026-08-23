# State, Data, and Logic

> Part of the [Frontend skill](../../SKILL.md).

## Classify State

Decide what kind of state something is before deciding where it lives:

- **Server state** — data owned by a backend, fetched and cached locally
- **URL state** — state that should be reflected in and driven by the URL (query params, path)
- **Shared client state** — state needed by multiple, not-nearby components
- **Local UI state** — display state scoped to a single component
- **Derived state** — a value computable from other state; do not store it separately

---

## Keep State Close to Its Owner

Place state at the closest common owner of the components that need it — but do not stop there. Also ask who decides when it changes, and whether it needs to stay synchronized with the URL or the server. Those answers sometimes point further up or down the tree than "closest common ancestor" alone would suggest.

---

## Separate Data Access from Rendering When Useful

Giving server data fetching, mutations, URL state, and external subscriptions an explicit boundary is often useful, but it is not a rule to apply everywhere. Do it when there is a concrete payoff: independent testability, more than one real data source, or actual reuse — not by default on every component that happens to fetch something.

---

## Side Effects and External Synchronization

Give side effects (subscriptions, synchronization with systems outside the component tree) an explicit, visible boundary rather than scattering them across render logic.

---

## Mutations, Optimistic Updates, and Recovery

Any optimistic update needs a defined rollback path and a way to surface the failure if the mutation does not succeed. Do not apply an optimistic update without also handling the case where it has to be undone. See [States and Recovery](../design/05-states-responsive-accessibility.md) on the design side for how that failure should be presented.

---

## Custom Hooks and Logic Extraction

Extract domain logic into a hook or service once it is genuinely shared across more than one place. Do not extract a hook for logic used exactly once — that only adds a layer of indirection with no reuse to justify it.

---

## Context and Global State

Do not reach for Context or global state to solve simple local state, and do not introduce global state the moment you notice prop drilling. Prop drilling through two or three levels is often cheaper to read than the indirection a global store introduces.

---

## Avoid Mechanical Container/Presentation Splits

Always separating a component into a "container" and a "presentational" half is an outdated default that tends to multiply files without benefit. Create a separate presentational component only when it earns its keep — independent testability, more than one data source, or genuine reuse — not as a blanket rule applied to every component that touches data.

---

## Error and Async Boundaries

Scope error handling for async and data-fetching failures to the affected part of the UI rather than letting it take down the whole screen. See [Error and Partial Failure](../design/05-states-responsive-accessibility.md) on the design side for how the resulting state should look.
