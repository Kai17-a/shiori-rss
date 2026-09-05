export interface DockerImage {
  id: number;
  registry: string;
  repository: string;
  tag: string;
  display_name: string;
  latest_digest: string;
  fetched_at: string;
  created_at: string;
  updated_at: string;
  webhook_ids: number[];
}

export interface DockerImageListResponse {
  items: DockerImage[];
  total: number;
}
