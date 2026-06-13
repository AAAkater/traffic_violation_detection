// === Generic API Response Wrapper ===

export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}

// === Detect ===

export interface DetectionItem {
  quadrant: string
  /** [x1, y1, x2, y2] */
  bbox: [number, number, number, number]
  confidence: number
  class_name: string
}

export interface DetectData {
  image_id: string
  detections: DetectionItem[]
}

// === Judge ===

export interface JudgeData {
  image_id: string
  violated: boolean
  reason?: string
  provider_id: number
  model: string
}

// === History ===

export interface HistoryBoxItem {
  quadrant: string
  /** [x1, y1, x2, y2] */
  bbox: [number, number, number, number]
  confidence: number
  class_name: string
}

export interface HistoryJudgeItem {
  violated: boolean
  reason?: string
  prompt_name?: string | null
  provider_id?: number | null
  model?: string | null
}

export interface HistoryItem {
  image_id: string
  filename: string
  image_url?: string | null
  created_at: string
  detections: HistoryBoxItem[]
  judge?: HistoryJudgeItem | null
}

export interface HistoryPage {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// === Prompt ===

export interface PromptData {
  name: string
  content: string
}

export interface PromptListItem {
  name: string
  content: string
  is_active: boolean
  updated_at: string
}

// === Provider ===

export interface ProviderCreate {
  name: string
  base_url: string
  api_key: string
}

export interface ProviderUpdate {
  name?: string | null
  base_url?: string | null
  api_key?: string | null
}

export interface ProviderData {
  id: number
  name: string
  base_url: string
  api_key: string
  activated_models: string[]
  created_at: string
  updated_at: string
}

export interface ModelInfo {
  id: string
  owned_by?: string
  created?: number | null
}

export interface ProviderModelsData {
  provider_id: number
  provider_name: string
  models: ModelInfo[]
}

export interface ModelActivateRequest {
  model: string
}

export interface ModelDeactivateRequest {
  model: string
}

// === Validation ===

export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface HTTPValidationError {
  detail: ValidationError[]
}
