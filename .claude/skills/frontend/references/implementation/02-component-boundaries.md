# Component Boundaries

> Part of the [Frontend skill](../../SKILL.md).

## What Makes a Component Boundary

A good component boundary corresponds to a stable semantic responsibility, not to a visual fragment that happens to look reusable today.

Before extracting a component, be able to name the responsibility it owns in one sentence. If you cannot, the boundary is not ready yet.

---

## Extract When Responsibility Is Stable

Extraction is well supported when several of the following are true:

- it carries the same meaning, behavior, and accessibility contract in every place it is used
- it owns an independent state transition or side-effect boundary
- it encapsulates non-trivial interaction logic
- it is worth testing on its own
- its reason to change differs from its parent's
- it needs to stay consistent as a design-system primitive
- naming it makes the surrounding code easier to read

---

## Keep Simple Markup Inline

Short markup used in exactly one place does not need a component. Extracting it adds an indirection with no payoff: a reader now has to open another file to see three lines of JSX.

---

## Keep Unstable UI Page-Local

Keep UI page-local when any of the following applies:

- it depends heavily on the parent screen's data shape or layout
- extracting it would leave the resulting props more complex than the inline code was
- it looks similar to something else only by coincidence, not because it means the same thing
- the specification is still moving and no stable boundary is visible yet
- the fragment is too small to describe as an independent responsibility

---

## Extract Behavior and Accessibility Contracts

UI with non-trivial keyboard handling, ARIA wiring, or focus management is worth extracting regardless of how simple it looks visually. The value is in not re-implementing the contract correctly at every call site, not in the amount of markup saved.

---

## Reuse Meaning, Not Accidental Visual Similarity

Looking the same is not the same as being the same component. Sharing a domain concept is not the same as sharing a rendering implementation.

Do not force two elements into one component just because they currently render identically. If their meaning diverges, let their implementations diverge too — see [Separate Design Decisions from Implementation Decisions](01-principles-and-boundaries.md#separate-design-decisions-from-implementation-decisions).

---

## Change-Coupling as an Abstraction Signal

Duplicated markup is weak evidence for abstraction on its own. Duplicated *knowledge* — a rule, a contract, a piece of business logic that must change in lockstep across several places — is much stronger evidence.

Before extracting, ask:

> Does this abstraction unify duplicated knowledge, or only duplicated code?

If the answer is only the latter, the duplication may be acceptable.

---

## Splitting and Merging Components

If an existing shared component is accumulating boolean props, style overrides, or per-caller conditionals, its responsibility has likely grown too broad. Consider splitting it back into narrower components rather than adding another flag.

Conversely, if several small components always change together and never vary independently, consider merging them — the split boundary was not tracking a real seam.

---

## Avoid Premature Abstraction

Do not default to turning everything into a shared component, and do not default to inlining everything either. Judge each case against the [Abstraction Promotion Model](01-principles-and-boundaries.md#abstraction-promotion-model): inline markup → page-local component → feature component → shared domain component → design-system primitive.
