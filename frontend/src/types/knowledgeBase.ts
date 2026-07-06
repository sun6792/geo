export interface KbCategory {
  id: string
  name: string
  slug: string
  parent_id: string | null
  description: string | null
  sort_order: number
  children: KbCategory[]
  created_at: string
}

export interface KbAsset {
  id: string
  title: string
  slug: string
  asset_type: 'basic' | 'marketing' | 'multimodal'
  content_type: string
  content_text: string | null
  content_json: any | null
  category_id: string | null
  status: string
  version: number
  is_latest: boolean
  tags: string[]
  metadata: Record<string, any>
  file_path: string | null
  file_size_bytes: number | null
  created_by: string
  created_at: string
  updated_at: string
}

export interface KbCategoryCreate {
  name: string
  slug: string
  parent_id?: string | null
  description?: string
}

export interface KbAssetCreate {
  title: string
  slug: string
  asset_type: 'basic' | 'marketing' | 'multimodal'
  content_type?: string
  content_text?: string
  content_json?: any
  category_id?: string
  tags?: string[]
}

export interface KbAssetUpdate {
  title?: string
  content_type?: string
  content_text?: string
  content_json?: any
  category_id?: string
  status?: string
  tags?: string[]
}
