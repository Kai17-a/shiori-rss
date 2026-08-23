# Styling, Tokens, and System Components

> Part of the [Frontend skill](../../SKILL.md).

## Use Existing Styling Conventions

Follow the styling approach already used in the project (CSS Modules, Tailwind, CSS-in-JS, vanilla-extract, or another system).

Do not introduce a second styling system alongside an existing one without a deliberate, discussed reason.

Match existing conventions for class naming, file colocation, and style composition.

---

## Consume Design Tokens

Use existing design tokens (color, spacing, typography, radius, shadow, motion) through their defined reference (CSS variables, a theme object, utility classes) rather than hardcoding raw values.

If a value is not covered by an existing token, prefer the closest existing token before introducing a new raw value.

Design tokens express *what* the interface should look like; this file governs how components *consume* them in code. See [Visual Foundations](../design/03-visual-foundations.md) in the design guide for the token values and visual principles themselves.

---

## Primitive, Pattern, and Domain Layers

Separate styling responsibility into layers:

- **Primitive** — base building blocks (Button, Input, Card, Dialog) that own their own styling and expose a constrained API.
- **Pattern** — compositions of multiple primitives (a form field group, a toolbar) that arrange primitives but rarely introduce new raw styling.
- **Domain** — product-specific components (`DeploymentStatus`, `InvoiceTable`) that consume primitives and patterns and add domain meaning, not new visual styling.

Domain components should rarely define raw colors, spacing, or typography directly. If a domain component needs a visual value no primitive exposes, treat that as a signal to extend the primitive or token set, not to hardcode a one-off.

---

## Variants and Styling Boundaries

Expose style variation through a constrained set of variants (`variant`, `tone`, `size`) rather than an open styling escape hatch.

Do not let every call site pass arbitrary inline styles or override internal class names of a primitive.

A primitive with an unbounded style API is not meaningfully different from no primitive at all.

---

## Responsive Styling

Follow the project's existing breakpoint definitions and responsive conventions.

Do not invent new breakpoint values inside an individual component.

Keep responsive logic close to the layout it affects; avoid duplicating the same breakpoint checks across unrelated components.

---

## Theme and Dark-Mode Implementation

Implement dark mode by switching theme tokens, not by mechanically inverting colors at the component level.

Components should reference semantic tokens (`surface`, `border`, `text-secondary`) rather than hardcoded light-mode colors with manual dark-mode overrides scattered per component.

See [Dark Mode](../design/03-visual-foundations.md) in the design guide for the visual principles this implementation should satisfy.

---

## Avoid Arbitrary Values and One-Off Overrides

Avoid magic numbers and one-off CSS overrides scoped to a single component when an existing token or utility already covers the case.

A one-off override is a signal worth noticing: either the token set is missing something real, or the component is drifting from the established visual system.

---

## Do Not Wrap Primitives Without Added Meaning

Do not create a component that only re-exports a primitive with the same props and no added behavior, meaning, or default.

A wrapper is justified when it fixes defaults for a domain use case, encodes a semantic contract (see [Component APIs and Composition](02-component-boundaries.md)), or composes multiple primitives into a reusable pattern.

---

## Coordinate Changes with the Design Guidelines

Changes to tokens or primitives affect visual consistency across the whole product.

Before changing a token value or a primitive's default styling, check that the change does not conflict with [Visual Foundations](../design/03-visual-foundations.md) or [Product Consistency and AI Patterns](../design/06-product-consistency-and-ai-patterns.md) in the design guide. When it does, resolve the conflict explicitly rather than letting the two guides drift apart.
