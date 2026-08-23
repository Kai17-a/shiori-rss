# Testing, Review, and Workflow

> Part of the [Frontend skill](../../SKILL.md).

## Implementation Workflow

For non-trivial implementation work, prefer this order:

### 1. Inspect

Look at existing components, hooks, patterns, and the shape of the data before writing anything new.

### 2. Place

Decide where the new code sits on the [abstraction promotion model](01-principles-and-boundaries.md): inline markup, page-local, feature-local, shared domain component, or design-system primitive. Do not default to the most shared tier.

### 3. Implement

Build the primary path using existing primitives, patterns, and conventions.

### 4. Integrate

Wire up data access, state, and side effects following [State, Data, and Logic](04-state-data-and-logic.md).

### 5. Test

Cover the behavior and edge cases described below.

### 6. Review

Perform the checks defined in this document.

Do not start by extracting shared abstractions and try to fit the implementation into them afterward.

---

## Component Testing Strategy

Test the observable behavior and contract of a component, not its internal implementation details.

Prefer tests that exercise a component the way a user or caller would (rendered output, interaction, emitted events) over tests that assert on internal state or private methods.

Do not write a test that only restates the implementation in a different syntax.

---

## Interaction and Accessibility Testing

Verify that primary tasks are completable using the keyboard alone.

Verify that interactive elements have accessible names and that state changes are announced appropriately to assistive technology.

Do not treat accessibility as covered because a test suite passes without any keyboard or screen-reader-oriented assertions.

---

## State and Edge-Case Testing

Cover loading, empty, error, and disabled states for every data-dependent component, not only the ideal populated state.

Test with realistic edge cases: long names, zero items, very large datasets, and missing or malformed data.

---

## Responsive Verification

Verify behavior at multiple representative viewport widths, not only the width used during development.

Confirm that responsive transformations (reflow, column prioritization, drawers) behave as intended rather than merely not crashing.

---

## Review Component Boundaries

During review, check whether component boundaries are justified:

- Is a shared component actually used in more than one place, or extracted speculatively?
- Does a "shared" component carry caller-specific conditionals that suggest it should not be shared yet?
- Is anything abstracted before its API has stabilized?

See [Component Boundaries](02-component-boundaries.md) for the extraction criteria.

---

## Review Public APIs

During review, check whether component APIs express intent:

- Do props read as semantic choices rather than raw styling?
- Is there a boolean-prop combination that should be a union or variant instead?
- Are mutually exclusive states representable at the same time when they should not be?

See [Component APIs and Composition](03-component-apis-and-composition.md) for the API design principles.

---

## Avoid AI-Generated Implementation Patterns

Watch for these implementation habits, which tend to appear in AI-generated code without being justified by actual need:

- Generating many thin, page-specific wrapper components that add no behavior.
- Moving every component into a shared `components/` directory by default.
- Extracting a hook or utility that is used exactly once.
- Growing a component's boolean props into a combinatorial, do-everything API.
- Embedding caller-specific conditionals inside a component meant to be shared.
- Introducing global state the moment props are passed through more than one layer.
- Reaching for Context to solve state that is actually simple and local.
- Wrapping an existing primitive with no added behavior, meaning, or default.
- Generating barrel exports (`index.ts` re-exports) by default across every directory.
- Duplicating a type, schema, or interface instead of reusing the existing one.
- Splitting a component into container and presentational halves purely by convention, with no independent reuse or test benefit.

---

## Evidence to Record

Do not close out a review with only "looks good." Record what was actually verified:

- Which viewport widths were checked.
- Which states (loading, empty, error, disabled, permission-denied) were actually rendered and inspected.
- For any new abstraction (shared component, hook, utility): what concrete, multi-site usage justifies it.

---

## Definition of Done

Implementation work is complete when:

- The component boundaries chosen are justified by actual reuse or a stable, independent responsibility, not speculation.
- Public APIs express intent and avoid boolean-prop explosion or ambiguous state combinations.
- State is classified and placed close to its owner, with no mechanical container/presentation split imposed by convention alone.
- States, edge cases, and responsive behavior have been verified with evidence, not assumed.
- The implementation satisfies the corresponding [Definition of Done](../design/07-workflow-and-review.md) in the design guide.
