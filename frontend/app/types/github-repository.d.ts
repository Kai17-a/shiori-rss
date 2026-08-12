export interface GitHubRepository {
  id: number;
  owner: string;
  repository: string;
  repository_url: string;
  latest_release_name: string;
  latest_release_tag: string;
  latest_release_url: string;
  latest_release_body: string | null;
  latest_release_published_at: string;
  fetched_at: string;
  created_at: string;
  updated_at: string;
  webhook_ids: number[];
}

export interface GitHubRepositoryListResponse {
  items: GitHubRepository[];
  total: number;
}
