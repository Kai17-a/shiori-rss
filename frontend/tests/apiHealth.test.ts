import { describe, expect, it, vi } from "vitest";

import { createApiHealthState, requestApiHealth } from "~/utils/apiHealth";

describe("apiHealth helpers", () => {
  it("creates a predictable empty state", () => {
    expect(createApiHealthState()).toEqual({
      checked: false,
      ok: null,
    });
  });

  it("reports a successful health response", async () => {
    const request = vi.fn().mockResolvedValue({ status: "ok" });

    await expect(requestApiHealth(request)).resolves.toBe(true);
    expect(request).toHaveBeenCalledWith("/health");
  });

  it("reports unexpected and failed health responses as unavailable", async () => {
    await expect(requestApiHealth(vi.fn().mockResolvedValue({ status: "down" }))).resolves.toBe(
      false,
    );
    await expect(requestApiHealth(vi.fn().mockRejectedValue(new Error("offline")))).resolves.toBe(
      false,
    );
  });
});
