import { describe, expect, it } from "vitest";

import { formatDateTime } from "../app/utils/dateTime";

describe("formatDateTime", () => {
  it("keeps the publication time represented by the RSS timezone offset", () => {
    expect(formatDateTime("2026-08-04T14:30:00+09:00")).toBe("2026/08/04 14:30:00");
  });

  it("keeps UTC publication times represented as UTC", () => {
    expect(formatDateTime("2026-08-04T05:30:00+00:00")).toBe("2026/08/04 05:30:00");
  });
});
