# Browser Extension

This directory contains the Manifest V3 extension used with Shiori Keeper.

## What it does

- Reads the current tab title and URL from the popup
- Sends bookmarks to a Shiori Keeper API server
- Stores the API server URL with the WebExtension `browser.storage.local` API
- Checks API connectivity from the popup
- Loads folders and tags for bookmark organization
- Updates existing bookmarks by URL and falls back to creation when needed

## Development

- `bun install`
- `bun run dev`
- `bun run build`

## API Check Script

`scripts/check-browser-extension-popup-api-contract.sh` runs the same request shapes used by `entrypoints/popup/App.vue` with `curl`.
It is meant for quick API compatibility checks after backend changes, not for package-managed test runs.

Example:

```bash
bash scripts/check-browser-extension-popup-api-contract.sh http://localhost:8000
```

The extension is built with WXT, Vue 3, and PrimeVue.
It is popup-only and does not inject content scripts or run a background worker.
