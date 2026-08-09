import { describe, expect, it } from "vitest";

import {
  ARTICLE_SUMMARY_MAX_LENGTH,
  formatArticleSummary,
} from "../app/utils/articleSummary";

describe("formatArticleSummary", () => {
  it("converts RSS HTML summaries into compact plain text", () => {
    expect(formatArticleSummary("<p>Hello <strong>RSS</strong> &amp; Atom</p>"))
      .toBe("Hello RSS & Atom");
  });

  it("limits summaries to 160 characters without splitting emoji", () => {
    const summary = `記事${"a".repeat(ARTICLE_SUMMARY_MAX_LENGTH - 2)}🙂続き`;
    const formatted = formatArticleSummary(summary);

    expect(Array.from(formatted.slice(0, -1))).toHaveLength(ARTICLE_SUMMARY_MAX_LENGTH);
    expect(formatted.endsWith("…")).toBe(true);
  });

  it("does not add an ellipsis to short summaries", () => {
    expect(formatArticleSummary("Short summary")).toBe("Short summary");
  });
});
