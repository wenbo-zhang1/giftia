export interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  image?: string
}

export interface Conversation {
  id: string
  title: string
  created: string
  message_count: number
  is_active: boolean
  messages?: Message[]
}

export interface UserInfo {
  id: string
  memory_count: number
  consolidated_count: number
  avg_importance: number
}

export interface MemoryStats {
  total: number
  emotion_distribution?: Record<string, number>
  category_distribution?: Record<string, number>
  avg_importance: number
  consolidated_count: number
}

export interface ModelConfig {
  model: string
  base_url: string
  multimodal: boolean
}

export interface LogEntry {
  timestamp: number
  level: string
  message: string
}

export interface SSEEvent {
  type: 'status' | 'token' | 'reply' | 'done' | 'error'
  text?: string
  conversation_id?: string
}

export interface PromptConfig {
  prompt: string
  default_prompt: string
  is_custom: boolean
}

export interface MemoryDetail {
  id: string
  content: string
  emotion: string
  emotion_emoji: string
  emotion_intensity: number
  category: string
  importance: number
  access_count: number
  created_at: number
  last_accessed: number
  is_consolidated: boolean
  tags: string[]
  temporal_data: Record<string, any>
}

export interface WorkingMemory {
  summary: string
  open_topics: string[]
  current_emotion: string
  updated_at: number
}

export interface MemoryDetailResponse {
  layers: {
    core: MemoryDetail[]
    important: MemoryDetail[]
    regular: MemoryDetail[]
  }
  working_memory: WorkingMemory
}

export interface UserProfileData {
  identity: Record<string, any>
  preferences: Record<string, any>
  relationships: Record<string, any>
  emotional_profile: Record<string, any>
}

export interface UserProfileResponse {
  user_id: string
  profile: UserProfileData
  prompt_context: string
  version: number
}