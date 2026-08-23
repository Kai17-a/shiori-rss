# Interaction Patterns

> Part of the [Frontend skill](../../SKILL.md).

## Actions and Button Hierarchy

Establish clear action hierarchy.

Typical priority:

1. Primary action
2. Secondary action
3. Tertiary / quiet action
4. Destructive action

A screen should rarely contain several equally prominent primary buttons.

Use destructive styling only for genuinely destructive operations.

Avoid oversized buttons in dense application interfaces.

Button labels should describe the action clearly.

Prefer:

- Create project
- Save changes
- Restart service
- Delete account

over vague labels such as:

- Continue
- Submit
- Confirm

when a more precise label is possible.

---

## Forms and Validation

Keep forms visually calm and predictable.

Always associate labels with controls.

Do not rely on placeholder text as the only label.

Group related fields.

Avoid excessive explanatory text around straightforward inputs.

Show validation errors near the field responsible for the error.

Preserve entered values after validation failures whenever possible.

Distinguish clearly between:

- optional fields
- required fields
- disabled fields
- read-only fields

Do not disable a control without making the reason understandable.

---

## Tables and Data-Dense Interfaces

Use tables when users need to compare attributes across multiple items.

Do not replace suitable tables with collections of cards simply to make the interface look more visual.

For tables:

- align related values consistently
- keep column order stable
- keep row heights reasonably compact
- make sortable columns identifiable
- avoid unnecessary center alignment
- use tabular numbers where appropriate
- preserve important columns at practical viewport sizes
- make row actions discoverable without dominating the row

Statuses should be scannable.

Do not turn every value into a badge.

Plain text is preferable when color or container styling adds no useful meaning.

---

## Navigation

Navigation should reflect the user's mental model of the product.

Do not create navigation categories solely to make the sidebar appear balanced.

Keep labels concise and predictable.

Highlight the current location clearly.

Avoid excessive nested navigation.

For developer tools and administration interfaces, persistent navigation is generally preferable when users frequently switch sections.

Do not consume excessive width with decorative navigation.

---

## Overlays and Disclosure

Choose the overlay that matches how much the interaction should interrupt the user, not by default habit.

### Dialog

Use for a focused task or confirmation important enough to justify interrupting the current flow, such as a short input or a decision the user must make before continuing.

### Drawer

Use to show detail or a secondary task while keeping the surrounding screen's context visible and intact.

### Popover

Use for lightweight, secondary actions or menus anchored to a specific control.

### Inline Disclosure

Use to reveal detail within the same layout when space is limited, without leaving the current context.

Avoid reaching for a confirmation dialog by default. When an action is reversible, prefer undo over a confirmation step.

---

## Feedback and Long-Running Actions

Confirm the outcome of an action, not just that it was submitted.

Distinguish success, failure, and in-progress states clearly.

When applying an optimistic update, define how the interface rolls back and informs the user if the underlying operation fails.

For operations with meaningful duration, show progress rather than an indefinite spinner when progress is knowable.

---

## Destructive Actions and Recovery

Do not default to a confirmation dialog for every destructive action.

Prefer undo as the primary safety mechanism when the action can be reversed.

When confirmation is genuinely necessary, state the scope of the impact explicitly, such as how many items are affected and what will happen to them, rather than a generic "Are you sure?".

---

## Data Visualization

Use a chart when the point is a trend, comparison, or distribution. Use a table when the point is looking up or comparing exact values across many attributes.

Do not add a chart as decoration when the underlying data does not warrant one.

Do not fabricate or simplify data to make a chart look more finished than the data supports.

Do not omit a zero baseline in ways that misrepresent magnitude.

Do not rely on color alone to distinguish series; pair it with labels, position, or pattern.

---
