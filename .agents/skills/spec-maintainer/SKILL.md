---
name: spec-maintainer
description: Create and maintain repository specifications and design docs under `specs/` so product requirements, API specs, and frontend specs stay organized and searchable.
---

# Spec Maintainer

Use this skill when creating or restructuring documentation under `specs/`.

## Scope

- `specs/product/requirements.md`
- `specs/architecture/system-design.md`
- `specs/components/api/`
- `specs/components/frontend/`
- `specs/components/batch/`
- `specs/components/browser-extension/`
- `specs/quality/observations/`

## Principles

- Keep `specs/product/requirements.md` as the top-level product requirement source.
- Put implementation-facing details in `specs/components/<area>/`.
- Keep sections short and aligned with the current codebase.
- Prefer tables for routes, schemas, constraints, and traceability.
- Update `README.md` links when a specs directory changes.

## Workflow

1. Inspect the current implementation and existing specs.
2. Identify mismatches between code and docs.
3. Update the most specific spec first.
4. Update higher-level docs only if the scope or role changed.
5. Add or refresh traceability links when requirements change.

## Deliverables

- Clear file structure under `specs/`
- Updated routing, schema, and constraint docs
- Cross-links between requirement, API, and frontend specs
