import { readdirSync, readFileSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const appRoot = join(import.meta.dirname, "../app");

const vueFiles = (directory: string): string[] => readdirSync(directory, {
  withFileTypes: true,
}).flatMap((entry) => {
  const path = join(directory, entry.name);
  if (entry.isDirectory()) return vueFiles(path);
  return extname(entry.name) === ".vue" ? [path] : [];
});

describe("async action buttons", () => {
  it("explicitly uses loader-circle for every loading UButton", () => {
    const missingLoadingIcon: string[] = [];

    for (const file of vueFiles(appRoot)) {
      const source = readFileSync(file, "utf8");
      for (const match of source.matchAll(/<UButton\b[\s\S]*?>/g)) {
        const tag = match[0];
        if (tag.includes(":loading=") && !tag.includes('loading-icon="i-lucide-loader-circle"')) {
          const line = source.slice(0, match.index).split("\n").length;
          missingLoadingIcon.push(`${relative(appRoot, file)}:${line}`);
        }
      }
    }

    expect(missingLoadingIcon).toEqual([]);
  });
});
