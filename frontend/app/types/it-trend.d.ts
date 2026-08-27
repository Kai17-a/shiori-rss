export type ITTrendMomentum = "surging" | "rising" | "steady";

export interface ITTrendLink {
  title: string;
  url: string;
  source: string;
}

export interface ITTrendItem {
  id: string;
  rank: number;
  title: string;
  summary: string;
  category: string;
  momentum: ITTrendMomentum;
  score: number;
  source_count: number;
  mention_count: number;
  sources: string[];
  related_links: ITTrendLink[];
}

export interface ITTrendResponse {
  generated_at: string | null;
  window_hours: number;
  region: string;
  sources: string[];
  ai_summarized: boolean;
  stale: boolean;
  items: ITTrendItem[];
}
