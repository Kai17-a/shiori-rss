import type { ITTrendResponse } from "~/types";

const mockItems: ITTrendResponse["items"] = [
  {
    id: "coding-agents",
    rank: 1,
    title: "AI coding agents move into team workflows",
    summary:
      "Developers are comparing agent orchestration, review controls, and how coding agents fit into existing CI pipelines.",
    category: "AI",
    momentum: "surging",
    score: 96,
    source_count: 4,
    mention_count: 184,
    sources: ["Hacker News", "GitHub", "Reddit", "Tech media"],
    related_links: [
      { title: "Agent workflows gain wider adoption", url: "https://news.ycombinator.com/", source: "Hacker News" },
      { title: "Popular agent projects this week", url: "https://github.com/trending", source: "GitHub" },
    ],
  },
  {
    id: "post-quantum-crypto",
    rank: 2,
    title: "Post-quantum cryptography migration",
    summary:
      "Cloud providers and security teams are publishing practical migration guidance for quantum-resistant protocols.",
    category: "Security",
    momentum: "rising",
    score: 88,
    source_count: 3,
    mention_count: 121,
    sources: ["Security feeds", "Hacker News", "Tech media"],
    related_links: [
      { title: "Implementation guidance and discussions", url: "https://news.ycombinator.com/", source: "Hacker News" },
    ],
  },
  {
    id: "local-ai",
    rank: 3,
    title: "Smaller models bring more AI workloads on-device",
    summary:
      "New compact models and inference runtimes are making private, offline AI features practical on laptops and phones.",
    category: "AI",
    momentum: "rising",
    score: 84,
    source_count: 4,
    mention_count: 109,
    sources: ["GitHub", "Reddit", "AI newsletters", "Tech media"],
    related_links: [
      { title: "Trending local inference projects", url: "https://github.com/trending", source: "GitHub" },
    ],
  },
  {
    id: "passkeys",
    rank: 4,
    title: "Passkeys expand beyond consumer sign-in",
    summary:
      "Enterprise tooling is adding passkey support while teams work through recovery, device enrollment, and rollout concerns.",
    category: "Security",
    momentum: "steady",
    score: 77,
    source_count: 2,
    mention_count: 76,
    sources: ["Security feeds", "Tech media"],
    related_links: [
      { title: "Passkey deployment discussions", url: "https://www.reddit.com/r/netsec/", source: "Reddit" },
    ],
  },
  {
    id: "open-source-databases",
    rank: 5,
    title: "Embedded and local-first databases keep growing",
    summary:
      "Developers are revisiting embedded databases, synchronization layers, and local-first architecture for resilient apps.",
    category: "Data",
    momentum: "steady",
    score: 71,
    source_count: 3,
    mention_count: 64,
    sources: ["Hacker News", "GitHub", "Developer blogs"],
    related_links: [
      { title: "Database projects developers are watching", url: "https://github.com/trending", source: "GitHub" },
    ],
  },
];

export const fetchMockITTrends = async (): Promise<ITTrendResponse> => {
  await new Promise((resolve) => window.setTimeout(resolve, 350));
  return {
    generated_at: new Date().toISOString(),
    window_hours: 24,
    region: "Global",
    sources: ["Hacker News", "GitHub Trending", "Reddit", "Technology media"],
    items: structuredClone(mockItems),
  };
};
