export interface AskAISource {
  reference: string;
  source_type: "rss" | "custom";
  article_id: number;
  source_id: number;
  source_title: string;
  title: string | null;
  summary: string | null;
  url: string;
  published: string | null;
  created_at: string;
}

export interface AskAIResponse {
  answer: string;
  sources: AskAISource[];
}
