# States, Responsive Design, and Accessibility

> Part of the [Frontend skill](../../SKILL.md).

## UI and Data States

Do not implement only the ideal populated state.

For every data-dependent component, consider:

- loading
- empty
- error
- partial failure
- stale data
- disabled
- permission denied

For every interactive control, consider:

- default
- hover
- focus
- active
- selected
- disabled

Do not hide failures behind generic messages if actionable information is available.

Prefer useful errors such as:

`Failed to connect to the database. Last successful connection: 12:42.`

over:

`Something went wrong.`

---

## Empty States

An empty state should explain what is absent and, when appropriate, what the user can do next.

Avoid large decorative illustrations unless they are consistent with the product's established visual language.

A compact empty state is usually sufficient for utility interfaces.

Example:

**No deployments yet**

Deploy an application to see deployment history here.

`Deploy application`

---

## Loading and Progress

Avoid blocking the entire page when only one section is loading.

Preserve stable layout dimensions where practical to reduce layout shifts.

Use skeletons when the final structure is predictable.

Use progress indicators when progress is meaningful.

Do not add artificial loading animations.

---

## Error and Partial Failure

Errors should be proportional to their impact.

A failed background request should not automatically replace the whole page.

Prefer local error presentation for local failures.

Reserve global error states for failures that make the entire screen unusable.

When possible, provide:

- what failed
- relevant context
- whether existing data is still valid
- a recovery action

---

## Disabled, Read-Only, and Permission States

Distinguish clearly between:

- optional fields
- required fields
- disabled fields
- read-only fields
- content hidden or blocked by insufficient permission

Do not disable a control without making the reason understandable.

A permission-denied state should say what access is missing, not just that an action failed.

---

## Responsive Transformation

Responsive design is not simply shrinking the desktop interface.

Determine which information remains essential at each viewport size.

When space becomes constrained:

1. preserve the primary task
2. preserve primary information
3. reduce secondary information
4. move tertiary information behind details
5. change layout when necessary

Do not force complex desktop tables into unusably narrow layouts.

Prefer deliberate transformations such as:

- horizontal scrolling
- column prioritization
- detail drawers
- stacked representations

depending on the task.

---

## Keyboard and Focus

Every primary task must be completable using the keyboard alone.

Ensure:

- logical, predictable tab order
- visible focus indicators on every interactive element
- no keyboard traps
- standard keys behave as expected (Escape closes overlays, Enter submits, arrow keys move within composite widgets)

Do not remove focus outlines without providing an equally visible replacement.

---

## Semantic and Screen Reader Accessibility

Ensure:

- semantic HTML elements over generic `div`/`span` where a native element exists
- accessible names for controls, icons-only buttons, and images
- appropriate form labels, programmatically associated with their controls
- meaningful heading order
- screen-reader-compatible status changes for asynchronous updates (loading, success, error)

Do not communicate important state through color alone.

---

## Contrast, Zoom, and Pointer Targets

Ensure sufficient contrast for text, controls, borders, and interactive states.

Interfaces should remain usable at 200% browser zoom and when only text size is increased; content should reflow rather than clip or overlap.

Provide adequate pointer target size and spacing, especially on touch devices.

Do not design an interaction that depends on hover alone; every hover-revealed action must have a reachable keyboard or touch equivalent.

---

## Motion and Reduced Motion

Motion should explain a relationship or state transition.

Good uses include:

- opening a dialog
- expanding details
- rearranging items
- confirming a state change

Avoid animation that exists only to make the application feel dynamic.

Keep frequent interactions fast.

Avoid exaggerated spring animations in productivity and administration interfaces unless they are deliberately part of the product identity.

Respect reduced-motion preferences.
