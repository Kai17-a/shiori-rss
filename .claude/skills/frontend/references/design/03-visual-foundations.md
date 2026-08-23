# Visual Foundations

> Part of the [Frontend skill](../../SKILL.md).

## Layout and Alignment

Prefer simple, predictable layouts.

Use grids and alignment deliberately.

Related elements should align visually.

Avoid arbitrary offsets that exist only to make a screen feel less empty.

Use whitespace to separate concepts, not to inflate the interface.

For application interfaces, favor efficient use of screen space over marketing-style spaciousness.

---

## Density and Content Width

Avoid unnecessarily narrow content columns on dashboards, administration screens, developer tools, tables, logs, and monitoring interfaces.

Long-form reading interfaces may use narrower content widths.

Match density to the interface type: transactional and analytical screens can be denser than editorial or promotional ones. See [Principles and Context](01-principles-and-context.md) for interface type profiles.

---

## Spacing

Use a restrained spacing scale.

These are starting points, not compliance targets. Prefer, in order: an existing design system, product-specific tokens, platform or accessibility requirements, then the fallback defaults below.

Default spacing scale:

- 4px
- 8px
- 12px
- 16px
- 24px
- 32px
- 48px

Do not introduce arbitrary spacing values without a clear reason.

Prefer tighter spacing inside a component and larger spacing between separate concepts.

Avoid excessive vertical padding.

Dense interfaces are acceptable when the product requires frequent scanning or comparison.

Density must not compromise readability or interaction target size.

---

## Typography

Typography should communicate hierarchy before decoration does.

These are starting points, not compliance targets. Prefer, in order: an existing design system, product-specific tokens, platform or accessibility requirements, then the fallback defaults below.

Suggested default scale:

- Metadata / auxiliary text: 12px
- Supporting text: 13px
- Body / controls: 14px
- Prominent body text: 16px
- Section heading: 16–18px
- Page heading: 22–28px

Avoid oversized headings in application interfaces.

Do not use marketing-style 40–64px headings unless the interface is actually a landing or marketing page.

Use font weight sparingly.

If everything is bold, nothing is emphasized.

Avoid excessive uppercase text.

Use monospaced typography for information where character structure matters, such as:

- source code
- logs
- IDs
- hashes
- IP addresses
- commands
- file paths
- timestamps when appropriate

---

## Containers and Cards

Do not put every section inside a card.

A card should represent a meaningful self-contained object or group.

Before adding a card, ask whether the same hierarchy can be expressed with:

- spacing
- a section heading
- a divider
- a subtle background
- a table
- a list
- typography

Prefer these simpler structures when possible.

Avoid interfaces composed of many floating rounded rectangles.

Do not nest cards inside cards without a strong structural reason.

---

## Borders, Radius, and Elevation

Use subtle borders to communicate structure.

These are starting points, not compliance targets. Prefer, in order: an existing design system, product-specific tokens, platform or accessibility requirements, then the fallback defaults below.

Suggested defaults:

- Border width: 1px
- Button radius: 6px
- Input radius: 6px
- Panel radius: 6–8px
- Dialog radius: 8–12px

Avoid excessive rounding.

Do not make every component pill-shaped.

Reserve pill shapes for elements that semantically benefit from them, such as:

- tags
- compact filters
- small status indicators

Use elevation (shadow) sparingly.

Shadows are appropriate primarily for layers that actually sit above other content:

- dialogs
- popovers
- dropdowns
- floating menus

Do not add shadows to every panel or card.

---

## Color

Color should communicate state, hierarchy, or identity.

Do not use color merely because an area looks empty.

Use semantic colors consistently for concepts such as:

- success
- warning
- error
- information
- selected state

Avoid excessive saturation.

Do not use several competing accent colors on the same screen.

Do not introduce gradients by default.

Use gradients only when they serve a deliberate visual or product purpose.

Never add a gradient solely to make an interface appear "modern."

Ensure sufficient contrast for text, controls, borders, and interactive states.

---

## Icons

Icons should improve recognition or reduce repeated visual noise.

Do not add icons merely as decoration.

Do not place an icon beside every heading.

Prefer familiar icons for familiar actions.

If the meaning of an icon is ambiguous, include a visible label or accessible tooltip.

Keep icon size and stroke style consistent.

---

## Design Tokens

Design tokens are the named values (color, spacing, typography, radius, border, shadow, motion) that keep an interface visually coherent. Use existing tokens whenever available instead of arbitrary values.

This section covers tokens as a visual-consistency concern: which values exist and when to reuse them. How tokens are named, structured, and consumed in code is an implementation concern — see [Styling, Tokens, and System Components](../implementation/06-styling-tokens-and-system-components.md) in the implementation guide.

---

## Dark Mode

Dark mode should be designed, not produced by mechanically inverting colors.

Maintain hierarchy through:

- surface differences
- borders
- typography contrast
- restrained semantic colors

Avoid pure black backgrounds combined with pure white text unless deliberately required.

Ensure disabled and secondary states remain distinguishable.

Do not make dark-mode borders so subtle that structure disappears.
