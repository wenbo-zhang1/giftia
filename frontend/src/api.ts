import type { Conversation, UserInfo, MemoryStats, ModelConfig, Message, LogEntry, PromptConfig, MemoryDetailResponse, UserProfileResponse } from './types'

const BASE = '/api'

const ACCESS_KEY_STORAGE = 'xiaoyi_access_key'
const ADMIN_KEY_STORAGE = 'xiaoyi_admin_key'

export function getStoredAccessKey(): string {
  return localStorage.getItem(ACCESS_KEY_STORAGE) || ''
}

export function setStoredAccessKey(key: string) {
  if (key) {
    localStorage.setItem(ACCESS_KEY_STORAGE, key)
  } else {
    localStorage.removeItem(ACCESS_KEY_STORAGE)
  }
}

export function getStoredAdminKey(): string {
  return localStorage.getItem(ADMIN_KEY_STORAGE) || ''
}

export function setStoredAdminKey(key: string) {
  if (key) {
    localStorage.setItem(ADMIN_KEY_STORAGE, key)
  } else {
    localStorage.removeItem(ADMIN_KEY_STORAGE)
  }
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const accessKey = getStoredAccessKey()
  if (accessKey) headers['X-Access-Key'] = accessKey
  const adminKey = getStoredAdminKey()
  if (adminKey) headers['X-Admin-Key'] = adminKey
  return { ...headers, ...extra }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: buildHeaders(options?.headers as Record<string, string> | undefined),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getHealth(): Promise<{ status: string; auth_required: boolean; admin_key_configured: boolean }> {
    return request('/health')
  },

  getConversations(userId: string): Promise<{ conversations: Conversation[]; current_id: string }> {
    return request(`/conversations/${userId}`)
  },

  getConversation(userId: string, convId: string): Promise<{ title: string; messages: Message[]; created: string }> {
    return request(`/conversations/${userId}/${convId}`)
  },

  createConversation(userId: string): Promise<{ id: string; title: string; created: string }> {
    return request(`/conversations/${userId}`, { method: 'POST' })
  },

  renameConversation(userId: string, convId: string, title: string) {
    return request(`/conversations/${userId}/${convId}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    })
  },

  deleteConversation(userId: string, convId: string): Promise<{ ok: boolean; current_id: string }> {
    return request(`/conversations/${userId}/${convId}`, { method: 'DELETE' })
  },

  getUsers(): Promise<UserInfo[]> {
    return request('/users')
  },

  createUser(userId: string) {
    return request(`/users?user_id=${encodeURIComponent(userId)}`, { method: 'POST' })
  },

  getMemoryStats(userId: string): Promise<MemoryStats> {
    return request(`/memory/${userId}/stats`)
  },

  clearMemories(userId: string) {
    return request(`/memory/${userId}`, { method: 'DELETE' })
  },

  getModelConfig(): Promise<ModelConfig> {
    return request('/config/model')
  },

  getPromptConfig(): Promise<PromptConfig> {
    return request('/config/prompt')
  },

  updatePromptConfig(prompt: string): Promise<{ ok: boolean; prompt: string; is_custom: boolean }> {
    return request('/config/prompt', {
      method: 'PUT',
      body: JSON.stringify({ prompt }),
    })
  },

  getLogs(limit = 200): Promise<{ logs: LogEntry[] }> {
    return request(`/logs?limit=${limit}`)
  },

  getMemoryDetail(userId: string): Promise<MemoryDetailResponse> {
    return request(`/memory/${userId}/detail`)
  },

  getUserProfile(userId: string): Promise<UserProfileResponse> {
    return request(`/profile/${userId}`)
  },

  async *sendMessage(
    userId: string,
    message: string,
    conversationId: string | null,
    history: Message[],
    imageData?: string
  ): AsyncGenerator<{ type: string; text?: string; conversation_id?: string }> {
    let lastError: Error | undefined
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 30000)

        let res: Response
        try {
          res = await fetch(`${BASE}/chat/${userId}`, {
            method: 'POST',
            headers: buildHeaders(),
            body: JSON.stringify({
              message,
              conversation_id: conversationId,
              conversation_history: history,
              image_data: imageData || null,
            }),
            signal: controller.signal,
          })
        } finally {
          clearTimeout(timeoutId)
        }

        if (!res.ok) {
          throw new Error(await res.text())
        }

        const reader = res.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') return
              try {
                yield JSON.parse(data)
              } catch {
                /* 跳过格式错误的数据 */
              }
            }
          }
        }

        if (buffer.trim()) {
          for (const line of buffer.split('\n')) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') return
              try { yield JSON.parse(data) } catch { /* 跳过格式错误的数据 */ }
            }
          }
        }
        return
      } catch (e) {
        const isTimeout = e instanceof DOMException && e.name === 'AbortError'
        if (isTimeout) {
          throw new Error('连接超时，请检查网络')
        }
        lastError = e as Error
        if (attempt === 0) {
          continue
        }
        throw lastError
      }
    }
    throw lastError || new Error('连接失败')
  },
}
