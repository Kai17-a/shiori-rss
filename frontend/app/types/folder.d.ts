export interface FolderCreateRequest {
  name: string;
  description?: string | null;
}

export interface FolderResponse {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
}
