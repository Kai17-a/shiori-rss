---
name: frontend
description: Use for any frontend UI work in this repository — building a new screen, modifying an existing one, styling, forms, tables, dialogs, navigation, state/component structure, or reviewing generated UI. Covers both design (how a screen should look and behave) and implementation (component boundaries, state, file layout, styling). Trigger this whenever the task touches index.html, styles.css, app.js, or any screen/UI behavior, even if the request doesn't say "design" or "frontend" explicitly — e.g. "add a filter to the transactions table", "make the drawer usable on mobile", "the budget bar looks off".
---

# Frontend

This repo's frontend guidance is bundled with this skill as two independent but companion sets of reference files: `references/design/` (how a screen should look and behave) and `references/implementation/` (how that decision gets structured as code). This skill is the router: it tells you which of those fourteen files to read for the task at hand, so you don't have to read all of them up front. Read both sides for anything beyond a one-line fix — they're written to be used together.

## Conflict resolution

A real, established pattern already in this codebase outranks every default below. These files describe what to do in the absence of a stronger signal, not a spec to force onto an existing screen. Inspect existing screens, components, and tokens before applying a default from any of these files.

## Always read

Regardless of task size, read these four first:

- `references/design/01-principles-and-context.md` — priorities, interface-type classification, how to resolve ambiguity
- `references/design/07-workflow-and-review.md` — the process and the checks a result must pass before it's done
- `references/implementation/01-principles-and-boundaries.md` — the design/implementation split, the abstraction promotion model
- `references/implementation/07-testing-review-and-workflow.md` — implementation workflow and its own done-checks

## Conditional task map

Read the file(s) matching what the task actually involves — most tasks need one or two of these beyond the four above.

| Task or question | Read |
| --- | --- |
| Information hierarchy, realistic content, progressive disclosure, copy/labels | `references/design/02-information-and-content.md` |
| Layout, spacing, typography, containers/cards, borders, color, icons, tokens, dark mode | `references/design/03-visual-foundations.md` |
| Buttons, forms, tables, navigation, dialogs/drawers/popovers, feedback, destructive actions, charts | `references/design/04-interaction-patterns.md` |
| Loading, empty, error, disabled, responsive, keyboard, accessibility, motion | `references/design/05-states-responsive-accessibility.md` |
| Dashboards/admin-style density, reusing existing visual patterns, avoiding an "AI-generated" look | `references/design/06-product-consistency-and-ai-patterns.md` |
| Should this become a component, and at what boundary? | `references/implementation/02-component-boundaries.md` |
| Props API, variants, composition, controlled/uncontrolled | `references/implementation/03-component-apis-and-composition.md` |
| State, data fetching, side effects, mutations | `references/implementation/04-state-data-and-logic.md` |
| Directory structure, naming, dependency direction | `references/implementation/05-files-naming-and-dependencies.md` |
| Styling approach, consuming design tokens, theming, primitive/pattern/domain layers | `references/implementation/06-styling-tokens-and-system-components.md` |

## Reading sets by task profile

- **Small change to an existing screen** — Always-read set + the one relevant conditional file.
- **New screen or feature** — Always-read set + `02`, `03` and/or `04` (design) + `05` + `06` (design) + whichever implementation files the change actually touches.
- **Review only (no code change yet)** — Always-read set + the relevant conditional file + `06` (design, AI-pattern check).
- **Extracting a shared component out of page-local markup** — Always-read set + `02`, `03` (implementation) + `03` (design, visual foundations).

## Before calling it done

Both sides define a "done" checklist (`references/design/07-workflow-and-review.md` and `references/implementation/07-testing-review-and-workflow.md`). In short: the primary task must be completable by keyboard alone, loading/empty/error/disabled states must actually be rendered and checked (not assumed), the UI must hold up against realistic content (long names, zero values, large numbers), and component boundaries/APIs must be justified by real reuse rather than speculation. Record what was actually checked rather than closing with an unverified "looks good."

## Japanese reference files

`references/ja/design/` and `references/ja/implementation/` mirror the English files 1:1, file-for-file — read these instead when working in Japanese. If you're editing guidance content itself (not just following it), keep both trees in sync.
