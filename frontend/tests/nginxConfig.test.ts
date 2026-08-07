import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("frontend nginx configuration", () => {
  it("uses relative redirects behind an external reverse proxy", () => {
    const config = readFileSync(new URL("../nginx.conf", import.meta.url), "utf8");

    expect(config).toMatch(/^\s*absolute_redirect\s+off;/m);
  });
});
