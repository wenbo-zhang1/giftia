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