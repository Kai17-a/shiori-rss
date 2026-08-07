---
name: spec-implementation-sync
description: Audit the current implementation against `specs/`, then update only the affected spec files to match the live behavior without changing source code. Use when the user asks to compare implementation and specs, refresh design docs, or synchronize `specs/` with frontend/api/batch/chrome-extension behavior.
---

# Spec Implementation Sync

Use this skill when the task is to bring `specs/` in line with the current implementation and source code must not be changed.

## Workflow

1. Read repository guidance first.
   - `README.md`
   - `specs/llm-reading-guide.md`
   - Follow any reading order or official references linked there before judging discrepancies.
2. Identify the implementation areas relevant to the request.
   - Typical splits in this repository: `frontend/`, `api/`, `batch/`, `chrome-extension/`
3. Compare implementation against the most specific spec first.
   - Start with `specs/components/frontend/*`, `specs/components/api/*`, `specs/components/batch/*`, or `specs/components/browser-extension/*`
   - Then update higher-level docs such as `specs/architecture/system-design.md`, `specs/product/requirements.md`, and `specs/llm-reading-guide.md` only if needed
4. Prefer implementation as the source of truth unless the user says otherwise.
5. Edit only files under `specs/` unless the user explicitly expands the scope.

## What To Check

- Routes and page structure
- User flows and UI responsibilities
- API endpoints, request/response shapes, and error behavior
- Data model and constraints
- Runtime ownership boundaries
  - Example: whether behavior is handled by API or `batch`
- Extension behavior and popup flows
- Traceability docs when requirement headings or layer boundaries changed

## Editing Rules

- Do not change application code.
- Do not leave outdated behavior in docs when a more specific spec exists.
- Prefer small, direct corrections over rewrites.
- Keep terminology consistent across `requirements`, `design`, and area-specific specs.
- If a spec file already has unrelated user changes, preserve them and make the smallest compatible update.

## Practical Heuristics

- If a feature moved screens, update the route/flow spec and any overview that mentions ownership.
- If an endpoint exists in routers or models but not in specs, add it.
- If a field exists in response models or DB schema but not in specs, document it.
- If a document claims a component owns behavior that the implementation moved elsewhere, fix the ownership description.
- If a dedicated spec exists for an area, update that file before touching `specs/architecture/system-design.md`.

## Expected Output

- `specs/` reflects the current implementation
- No source files outside `specs/` are modified
- Final summary lists which spec files were updated and the main mismatches corrected
