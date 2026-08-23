# Workflow and Review

> Part of the [Frontend skill](../../SKILL.md).

## Design Workflow

For significant frontend work, prefer this order.

### 1. Understand

Inspect:

- surrounding UI
- existing components
- design tokens
- data shape
- user task

### 2. Classify

Decide which [Interface Type Profile](01-principles-and-context.md#interface-type-profiles) the screen belongs to (Transactional, Analytical, Navigational, Editorial, Promotional, or Immersive). This decides the default density, heading scale, card usage, and motion budget for everything that follows.

### 3. Structure

Establish:

- information hierarchy
- layout
- component boundaries

Do not polish yet.

### 4. Implement

Build the primary state using existing design-system components.

### 5. Complete States

Add:

- loading
- empty
- error
- disabled
- responsive behavior

### 6. Polish

Refine:

- spacing
- typography
- alignment
- borders
- color
- motion

### 7. Review

Perform the checks defined in this document.

Do not start with visual polish and attempt to fit the information into it afterward.

---

## Review Generated UI

After generating or modifying a UI, inspect it critically. Do not accept the first result as final.

Fix problems found during this review before considering the UI complete.

---

## Structural Review

- Is the primary task obvious within the first glance?
- Does the order of information match the order of priority?
- Is anything visually prominent without being important?
- Is anything important without being visually prominent?
- Can values that need comparison be scanned side by side?
- Would the layout still make sense if the content were replaced with realistic data?

---

## Behavioral Review

- Can the primary task be completed using the keyboard alone?
- Are loading, empty, error, and permission-denied states implemented, not just the ideal populated state?
- Does the interface hold up with long names, long error messages, zero values, and very large values?
- Does the interface remain usable at smaller viewport sizes?
- Do disabled controls make the reason understandable?

---

## Visual Review

- How many elements are competing for the strongest visual emphasis? Is that count justified by the task?
- Are there unnecessary cards, or cards nested inside cards?
- Are there unnecessary badges applied to ordinary text?
- Are headings sized appropriately for an application interface, not a marketing page?
- Is spacing excessive relative to the information density the product needs?
- Is color doing useful work, or present because an area looked empty?
- Are icons doing useful work, or attached to every heading as decoration?
- Does this look consistent with the rest of the application?
- Does any component look like it exists only because an AI tends to generate it? See [Avoid Generic AI-Generated UI](06-product-consistency-and-ai-patterns.md#avoid-generic-ai-generated-ui).

---

## Evidence to Record

Do not close a review with an unverified "looks good." Record what was actually checked:

- Viewport widths verified (for example, roughly 320px, 768px, and 1440px).
- Whether the primary task was completed using only the keyboard.
- Whether long names, zero results, a failure state, and a permission-denied state were actually rendered and inspected, not assumed.
- If a new UI primitive was introduced, the reason an existing one was insufficient.
- The three most visually prominent elements on the screen, and whether they match the task's actual priority.

---

## Default Visual Direction

Unless the project specifies otherwise, favor:

- restrained
- functional
- compact
- quiet
- precise
- consistent
- content-first
- typography-driven
- border-driven rather than shadow-driven
- minimal but not sparse

The interface should feel designed for repeated use, not designed primarily for a screenshot.

---

## Definition of Done

Design work is done only when the Structural, Behavioral, and Visual review checks pass, the evidence above has been recorded, and the corresponding implementation review has also passed — see [Definition of Done](../implementation/07-testing-review-and-workflow.md#definition-of-done) in the implementation guide. A UI that looks correct but was never checked against real content, keyboard use, or edge-case states is not done.
