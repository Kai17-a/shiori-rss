# Principles and Context

> Part of the [Frontend skill](../../SKILL.md).

## Core Principles

Design interfaces around the user's task, not around visual decoration.

Prioritize, in order:

1. Usability
2. Information hierarchy
3. Consistency
4. Accessibility
5. Information density appropriate to the product
6. Visual polish
7. Decoration

A visually impressive interface that makes information harder to understand is a design failure.

Prefer interfaces that feel intentionally designed rather than generically generated.

---

## Decision Priority

When a requirement is ambiguous, or two reasonable approaches conflict, do not resolve the gap with arbitrary visual creativity.

Prefer the least surprising solution consistent with, in order:

1. Existing application patterns
2. The established design system
3. Common interaction conventions
4. The user's primary task

When several reasonable alternatives carry meaningful UX trade-offs, state the trade-off instead of silently making a large product decision.

---

## Understand the User and Task

Before implementing a screen, determine:

- Who uses this screen?
- What is the primary task?
- What information must be noticed first?
- What actions are primary?
- What information is secondary or metadata?
- What happens when data is missing?
- What happens when something fails?
- What does the user need to compare?
- What existing patterns in the application should be reused?

Do not start by deciding which cards, gradients, icons, or animations to use.

Start with information hierarchy.

---

## Interface Type Profiles

Before applying defaults from the rest of this guide, classify the screen. Different interface types justify different defaults for density, heading size, card use, motion, and content width.

- **Transactional** — settings, forms, CRUD flows. Favor predictability and low error risk over visual variety.
- **Analytical** — dashboards, monitoring, comparison views. Favor high density, restrained color, and no oversized headings.
- **Navigational** — listing, search, and exploration surfaces. Favor scanability and stable layout over decoration.
- **Editorial** — articles and documentation. Narrower reading widths and more generous typography are appropriate here.
- **Promotional** — landing pages and campaigns. Larger headings, hero sections, and more generous spacing are appropriate here.
- **Immersive** — media and creative tools. Chrome should recede in favor of the content or canvas being worked on.

The default values and rules in the rest of this guide are written primarily for Transactional, Analytical, and Navigational interfaces. Adjust defaults deliberately for Editorial, Promotional, or Immersive work — do not apply dashboard density to a landing page, or landing-page scale to a settings screen.

---

## Resolve Conflicts with Existing Product Patterns

When an existing design system or established pattern in the product conflicts with this guide, preserve the existing product's consistency unless explicitly instructed otherwise.

This guide describes defaults for the absence of a stronger signal. A real, established pattern in the codebase is a stronger signal than any rule here.

---
