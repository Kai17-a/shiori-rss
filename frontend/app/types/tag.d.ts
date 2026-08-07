export interface TagCreateRequest {
  name: string;
  description?: string | null;
}

export interface TagAttachRequest {
  tag_id: number;
}

export interface TagResponse {
  id: number;
  name: string;
  description?: string | null;
}
