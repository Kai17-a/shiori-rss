---
name: spec-sync
description: Keep design docs and specifications in sync with feature additions or behavior changes by updating `specs/` alongside code changes.
---

# Spec Sync

Use this skill when code changes affect behavior, data flow, UI flow, APIs, or constraints.

## Trigger cases

- New feature
- Removed feature
- Changed endpoint behavior
- Changed schema or validation
- Changed UI flow
- Changed error handling
- Changed database constraints

## Required actions

1. Update the relevant implementation files.
2. Update the most specific spec file first.
3. Update related docs in `specs/` if behavior changed.
4. Update traceability or references if the change crosses layers.
5. Review `README.md` links if directories or doc roles changed.

## Editing rules

- Do not leave docs describing old behavior.
- Do not update only high-level docs when a detailed spec exists.
- Prefer small, direct edits over large rewrites unless the feature boundary changed.
- Keep terminology consistent across code and docs.

## Output expectation

- Every behavior change should leave the corresponding spec current.
- Every new feature should have a matching spec update before the task is considered done.
