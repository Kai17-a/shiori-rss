# Product Context and AI-Pattern Avoidance

> Part of the [Frontend skill](../../SKILL.md).

## Product-Specific Design Context

The defaults in this guide are general-purpose. When a project has an established, documented visual language or design system, that language takes precedence over the generic defaults elsewhere in this guide.

Consult existing screens, components, and tokens before applying a default from this guide. See [Interface Type Profiles](01-principles-and-context.md) for how defaults shift by interface type.

---

## Developer and Administration Interfaces

Developer tools, dashboards, observability systems, and administration interfaces should usually favor:

- high information density
- compact spacing
- strong scanning patterns
- restrained color
- subtle borders
- predictable navigation
- readable tables
- useful keyboard interaction
- visible system state
- clear errors
- fast navigation

Avoid turning these products into SaaS marketing dashboards.

Data is the interface.

Do not obscure useful data in favor of decorative visualization.

---

## Reuse Existing Visual Patterns

Before introducing a new visual pattern:

1. inspect existing screens
2. inspect existing components and design tokens
3. reuse an established visual pattern when possible

Do not create a slightly different button, input, modal, status indicator, or panel style when an appropriate pattern already exists.

This section is about visual and stylistic reuse. For guidance on when to extract a shared component versus keep markup page-local, see the [Frontend skill](../../SKILL.md).

---

## Preserve Existing Design During Changes

When modifying an existing screen, make the smallest coherent change.

Do not redesign unrelated parts of the interface.

Preserve unless explicitly required to change:

- layout
- typography
- colors
- navigation
- component conventions
- interaction patterns
- spacing system

If a requested change exposes a broader design problem, identify the problem instead of silently redesigning the application.

---

## Avoid Generic AI-Generated UI

### Why Interfaces Feel Generically Generated

> An interface feels generically generated when its composition remains largely interchangeable after changing the product, task, and content.

This happens for a small number of recurring reasons:

- **Content-independent composition** — the layout is a template that would hold together even without knowing the real data or task.
- **Semantic inflation** — unimportant information is dressed up with cards, badges, icons, color, or oversized headings.
- **Uniform emphasis** — every section gets the same card, the same heading treatment, the same icon, erasing priority.
- **Decorative compensation** — gaps in requirements or content are filled with gradients, fabricated charts, filler copy, or animation instead of being resolved.
- **Pattern completion without evidence** — a familiar template is completed without justification from the actual product ("a dashboard needs three metric cards," "a SaaS app needs a welcome heading").

### Require Evidence for Visual Decisions

Every prominent visual element should be traceable to at least one of:

- task priority
- semantic grouping
- state communication
- scanning or comparison
- interaction affordance
- layer relationship
- established product identity

If an element satisfies none of these, treat it as a candidate for removal or simplification.

Apply this test to specific element types:

- **Card** — does it represent an independent object, a selectable unit, or a movable unit?
- **Badge** — is fast state or category identification actually needed here?
- **Icon** — does it speed up recognition or reduce repeated visual noise, beyond decoration?
- **Color** — does it communicate state, selection, importance, or brand identity?
- **Statistic card** — would this number change the user's first decision?
- **Chart** — does it support comparison or trend reading that a table or text cannot?
- **Motion** — does it explain a spatial relationship, a causal relationship, or a result?

### Common Symptoms

These are non-exhaustive examples of the causes above, grouped for recognition:

**Template composition**
- generic "Welcome back" dashboard headings
- placeholder marketing copy left in a functional interface

**Excessive containers and elevation**
- cards nested inside cards
- unnecessary floating panels
- excessive shadows on panels that do not sit above other content

**Inflated emphasis**
- giant centered headings in an application interface
- an icon beside every heading
- excessive pill-shaped controls
- badge styling applied to ordinary text

**Decorative color and imagery**
- a large gradient hero in a utility interface
- gradient text
- excessive glassmorphism
- decorative blobs
- arbitrary colored circles behind icons
- random gradients with no product purpose

**Unjustified metrics and visualization**
- unnecessary statistics cards
- three or four metric cards at the top of every dashboard regardless of relevance
- fake charts used purely as decoration

**Placeholder content and copy**
- excessive rounded cards used as generic containers
- excessive whitespace with no grouping purpose

**Unnecessary motion**
- needless animations that exist only to feel dynamic

### Exceptions and Product Identity

None of these patterns are universally forbidden.

Use them when justified by the product's [interface type profile](01-principles-and-context.md), its content, or an established design language — Promotional and Immersive interfaces legitimately use different defaults than Transactional or Analytical ones.

An exception should be explainable by purpose or existing product identity, not by "it looks more modern." Do not break existing consistency purely for novelty.

---

## Prefer Coherence over Local Novelty

Consistency usually provides more value than local novelty.

When a new pattern and an existing pattern are both reasonable, prefer the one that keeps the product coherent.
