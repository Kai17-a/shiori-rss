# Files, Naming, and Dependencies

> Part of the [Frontend skill](../../SKILL.md).

## Follow Existing Repository Structure

If the repository already has a directory structure, follow it. Introducing a second, competing structure alongside it is worse than keeping an imperfect but consistent one.

---

## Organize by Feature and Ownership

Prefer organizing by feature or domain over organizing by technical layer. A typical shape:

```text
features/
  deployments/
    components/
    hooks/
    api/
    model/
    pages/
ui/
  primitives/
  patterns/
```

Be cautious about adopting Atomic Design (atoms/molecules/organisms) as a standard. It captures visual granularity well but does not capture domain responsibility or reason-to-change, and it tends to invite an AI into a classification exercise instead of a design decision.

---

## Colocate Components, Tests, Stories, and Styles

Keep tests, stories, and styles next to the component they belong to rather than in a parallel directory tree that has to be kept in sync by hand.

---

## File and Component Naming

Follow the project's existing naming conventions. Where none exist, choose names that describe what the thing means over names that describe its current shape or implementation detail.

---

## Public and Private Feature APIs

Do not let other features reach into a feature's internal implementation. Expose a deliberate public surface (an index or a small set of entry points) and treat everything else inside the feature as private to it.

---

## Shared Directory Admission Criteria

`shared/`, `common/`, and `utils/` should require an admission criterion: something is genuinely used from more than one place. Do not place something there in anticipation of future reuse — see [Colocation Before Sharing](01-principles-and-boundaries.md#colocation-before-sharing).

---

## Import Direction and Dependency Boundaries

Keep the dependency direction consistent and avoid cycles between features. A typical rule: `shared` does not depend on any feature; a feature may depend on `shared` and on another feature's public surface, but never on another feature's internals.

---

## Barrel Exports

Do not treat barrel exports (`index.ts` re-exports) as a default pattern to apply everywhere. Use one where it genuinely clarifies a public surface, and skip it where it would encourage a circular dependency or obscure which module actually owns something.

---

## Avoid Generic Dumping Grounds

Do not let `components/` or `utils/` become a place where anything can be placed because no more specific location was considered. A generic-sounding directory is a sign that the underlying organization needs another look, not an invitation to keep adding to it.
