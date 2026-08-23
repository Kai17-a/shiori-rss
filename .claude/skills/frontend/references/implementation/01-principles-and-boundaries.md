# Implementation Principles and Boundaries

> Part of the [Frontend skill](../../SKILL.md).

## Implementation Principles

The [Frontend skill](../../SKILL.md) decide how a screen should look and behave. This guide decides how that decision gets structured and written as code: when to create a component, how to shape its API, where state lives, and how files are organized.

When implementation choices are unclear, prioritize in this order:

1. Consistency with the existing architecture
2. The smallest stable boundary that solves the actual problem
3. Testability and long-term maintainability
4. The locally "ideal" structure

A structure that is elegant in isolation but inconsistent with the rest of the codebase is not a good outcome.

---

## Preserve Existing Architecture

Follow the project's existing directory structure, state-management patterns, and component-splitting conventions when they exist.

Before introducing a new pattern, look for a similar existing implementation in the codebase and follow it unless there is a specific reason not to.

---

## Separate Design Decisions from Implementation Decisions

Looking the same is not the same as being the same component. Sharing a domain concept is not the same as sharing a rendering implementation.

Visual consistency defined on the design side — such as [Design Tokens](../design/03-visual-foundations.md#design-tokens) — is consumed by many components through shared tokens. It does not require forcing every visually similar element into one large shared component. Two elements can look identical today and still deserve separate implementations if their reasons to change differ.

---

## Choose the Smallest Stable Boundary

Decide a component's boundary once its responsibility is stable, not before.

Avoid premature abstraction. A boundary drawn around a responsibility that is still changing tends to be redrawn anyway, at the cost of an API that nobody was ready to commit to yet.

---

## Colocation Before Sharing

Put new UI or logic next to the place that needs it first. Move it toward a shared location only after it is actually needed in more than one place — see [Component Boundaries](02-component-boundaries.md) for the extraction criteria.

Do not create a shared version of something in anticipation of future reuse that has not happened yet.

---

## Abstraction Promotion Model

Treat component abstraction as a series of promotions, not a single up-front decision:

```text
Inline markup
  → Page-local component
  → Feature component
  → Shared domain component
  → Design-system primitive
```

Promote to the next stage only when there is evidence for it:

- the element is actually used in more than one place, not merely expected to be
- its API has stabilized rather than shifting with each new caller
- the reason it would change is the same across its uses
- its meaning is genuinely shared, not just its current markup

A component moving in the opposite direction is also a valid signal. If a shared component is accumulating boolean props, style overrides, and per-caller conditionals, its responsibility has likely grown too broad — see [Splitting and Merging Components](02-component-boundaries.md#splitting-and-merging-components) for how to respond.

---

## When Requirements or Architecture Are Ambiguous

When more than one implementation approach is reasonable and the trade-offs are meaningful, state the trade-off instead of silently picking one.

Weight the existing codebase's conventions as the strongest evidence for which approach is expected here.
