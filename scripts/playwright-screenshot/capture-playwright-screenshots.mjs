import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const { chromium } = require("@playwright/test");

const screenshotDir = process.env.PLAYWRIGHT_SCREENSHOT_DIR ?? "docs/app-images";
const frontendBaseUrl = process.env.PLAYWRIGHT_FRONTEND_BASE_URL ?? "http://127.0.0.1:3001";

const pages = [
  { path: "/", name: "dashboard" },
  { path: "/bookmarks", name: "bookmarks" },
  { path: "/favorites", name: "favorites" },
  { path: "/folders", name: "folders" },
  { path: "/tags", name: "tags" },
  { path: "/rss", name: "rss" },
  { path: "/settings", name: "settings" },
];
const themes = [
  { name: "light", colorScheme: "light" },
  { name: "dark", colorScheme: "dark" },
];

mkdirSync(screenshotDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
  for (const theme of themes) {
    await page.emulateMedia({ colorScheme: theme.colorScheme });
    for (const entry of pages) {
      await page.goto(new URL(entry.path, frontendBaseUrl).toString(), { waitUntil: "networkidle" });
      const outputPath = join(screenshotDir, `${entry.name}-${theme.name}.png`);
      await page.screenshot({
        path: outputPath,
        fullPage: true,
      });
      console.log(`Saved: ${outputPath}`);
    }
  }
} finally {
  await browser.close();
}
