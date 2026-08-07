---
name: playwright
description: Use when the task requires automating a real browser from the terminal via Playwright CLI or the bundled wrapper script. Best for navigation, form filling, snapshots, screenshots, data extraction, and UI-flow debugging.
---

# Playwright CLI Skill

Drive a real browser from the terminal using `playwright-cli`.

Prefer the bundled wrapper script so the CLI works even when it is not globally installed.
Treat this skill as CLI-first automation.

Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite Check

Before proposing commands, check whether `bun` is available:

```bash
command -v bun >/dev/null 2>&1
```

If it is not available, pause and ask the user to install Bun.

## Skill Path

Set the path once:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
```

User-scoped skills install under `$CODEX_HOME/skills` by default.

## Quick Start

Use the wrapper script:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

If the user prefers a global install, this is also valid:

```bash
bun add -g @playwright/cli@latest
playwright-cli --help
```

## Core Workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts such as screenshots, PDFs, or traces when useful.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When To Snapshot Again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening or closing modals or menus
- tab switches

Refs can go stale. When a command fails because a ref is missing, snapshot again.

## Recommended Patterns

### Form Fill And Submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug A UI Flow With Traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
"$PWCLI" click e2
"$PWCLI" tracing-stop
```

### Multi-Tab Work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper Script

The wrapper script uses `bunx playwright-cli` so the CLI can run without a global install:

```bash
"$PWCLI" --help
```

Prefer the wrapper unless the repository already standardizes on a global install.

## References

Open only what you need:

- CLI command reference: [references/cli.md](references/cli.md)
- Practical workflows and troubleshooting: [references/workflows.md](references/workflows.md)
- Advanced Playwright API reference: [references/api_references.md](references/api_references.md)

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and explain why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use `output/playwright/` and avoid introducing new top-level artifact folders.
- Default to CLI commands and workflows, not Playwright test specs.
