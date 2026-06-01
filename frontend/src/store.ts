import { create } from 'zustand'
import type { Conversation, UserInfo, Message, MemoryStats, ModelConfig, PromptConfig } from './types'
import { api, setStoredAccessKey, setStoredAdminKey } from './api'

let _msgIdCounter = 0
function nextMsgId(): string {
  return `msg_${Date.now()}_${++_msgIdCounter}`
}

interface AppState {
  userId: string
  conversations: Conversation[]
  currentConvId: string | null
  messages: Message[]
  users: UserInfo[]
  memoryStats: MemoryStats | null
  modelConfig: ModelConfig | null
  promptConfig: PromptConfig | null
  isLoading: boolean
  searchQuery: string
  statusText: string
  authRequired: boolean
  isAuthenticated: boolean
  error: string | null
  lastFailedMessage: { content: string; imageData?: string } | null

  setUserId: (id: string) => void
  setSearchQuery: (q: string) => void
  setStatusText: (t: string) => void

  loadConversations: () => Promise<void>
  loadConversation: (convId: string) => Promise<void>
  createConversation: () => Promise<string>
  renameConversation: (convId: string, title: string) => Promise<void>
  deleteConversation: (convId: string) => Promise<void>
  switchConversation: (convId: string) => Promise<void>

  addMessage: (msg: Message) => void
  setMessages: (msgs: Message[]) => void

  loadUsers: () => Promise<void>
  createUser: (userId: string) => Promise<void>
  switchUser: (userId: string) => Promise<void>

  loadMemoryStats: () => Promise<void>
  clearMemories: () => Promise<void>

  loadModelConfig: () => Promise<void>

  loadPromptConfig: () => Promise<void>
  updatePromptConfig: (prompt: string) => Promise<void>
  checkAuth: () => Promise<void>
  setAuthKeys: (accessKey: string, adminKey: string) => void

  sendMessage: (content: string, imageData?: string) => AsyncGenerator<void>
  retryLastMessage: () => AsyncGenerator<void>
}

export const useStore = create<AppState>((set, get) => ({
  userId: 'web_user_001',
  conversations: [],
  currentConvId: null,
  messages: [],
  users: [],
  memoryStats: null,
  modelConfig: null,
  promptConfig: null,
  isLoading: false,
  searchQuery: '',
  statusText: '',
  authRequired: false,
  isAuthenticated: true,
  error: null,
  lastFailedMessage: null,

  setUserId: (id) => set({ userId: id }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setStatusText: (t) => set({ statusText: t }),

  loadConversations: async () => {
    const { userId } = get()
    const data = await api.getConversations(userId)
    set({
      conversations: data.conversations,
      currentConvId: data.current_id,
    })
  },

  loadConversation: async (convId) => {
    const { userId } = get()
    const data = await api.getConversation(userId, convId)
    set({
      currentConvId: convId,
      messages: data.messages || [],
    })
  },

  createConversation: async () => {
    const { userId } = get()
    const data = await api.createConversation(userId)
    await get().loadConversations()
    await get().loadConversation(data.id)
    return data.id
  },

  renameConversation: async (convId, title) => {
    const { userId } = get()
    await api.renameConversation(userId, convId, title)
    await get().loadConversations()
  },

  deleteConversation: async (convId) => {
    const { userId, currentConvId } = get()
    const result = await api.deleteConversation(userId, convId)
    if (currentConvId === convId) {
      await get().loadConversation(result.current_id)
    }
    await get().loadConversations()
  },

  switchConversation: async (convId) => {
    await get().loadConversation(convId)
    set({ messages: get().messages })
  },

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),

  loadUsers: async () => {
    const users = await api.getUsers()
    const { userId } = get()
    const exists = users.some((u) => u.id === userId)
    if (!exists && users.length > 0) {
      set({ userId: users[0].id })
    }
    set({ users })
  },

  createUser: async (newUserId) => {
    await api.createUser(newUserId)
    await get().loadUsers()
  },

  switchUser: async (newUserId) => {
    set({ userId: newUserId, messages: [], conversations: [], currentConvId: null })
    await get().loadConversations()
    const { currentConvId } = get()
    if (currentConvId) {
      await get().loadConversation(currentConvId)
    }
    await get().loadMemoryStats()
  },

  loadMemoryStats: async () => {
    const { userId } = get()
    try {
      const stats = await api.getMemoryStats(userId)
      set({ memoryStats: stats, error: null })
    } catch (e) {
      set({ statusText: '记忆统计加载失败', error: '记忆统计加载失败' })
    }
  },

  clearMemories: async () => {
    const { userId } = get()
    await api.clearMemories(userId)
    await Promise.all([get().loadMemoryStats(), get().loadUsers()])
  },

  loadModelConfig: async () => {
    try {
      const config = await api.getModelConfig()
      set({ modelConfig: config, error: null })
    } catch (e) {
      set({ statusText: '模型配置加载失败', error: '模型配置加载失败' })
    }
  },

  loadPromptConfig: async () => {
    try {
      const config = await api.getPromptConfig()
      set({ promptConfig: config, error: null })
    } catch (e) {
      set({ statusText: '人设配置加载失败', error: '人设配置加载失败' })
    }
  },

  updatePromptConfig: async (prompt) => {
    const result = await api.updatePromptConfig(prompt)
    set((s) => ({
      promptConfig: s.promptConfig
        ? { ...s.promptConfig, prompt: result.prompt, is_custom: result.is_custom }
        : { prompt: result.prompt, default_prompt: '', is_custom: result.is_custom },
    }))
  },

  checkAuth: async () => {
    try {
      const health = await api.getHealth()
      const required = health.auth_required
      if (!required) {
        set({ authRequired: false, isAuthenticated: true })
        return
      }
      const storedKey = localStorage.getItem('xiaoyi_access_key')
      if (!storedKey) {
        set({ authRequired: true, isAuthenticated: false })
        return
      }
      try {
        await api.getConversations(get().userId)
        set({ authRequired: true, isAuthenticated: true })
      } catch {
        set({ authRequired: true, isAuthenticated: false })
      }
    } catch {
      set({ authRequired: false, isAuthenticated: true })
    }
  },

  setAuthKeys: (accessKey, adminKey) => {
    setStoredAccessKey(accessKey)
    setStoredAdminKey(adminKey)
    set({ isAuthenticated: true })
  },

  sendMessage: async function* (content, imageData) {
    const { userId, currentConvId, messages } = get()
    set({ isLoading: true, statusText: '', error: null, lastFailedMessage: { content, imageData } })

    const userMsg: Message = { id: nextMsgId(), role: 'user', content, image: imageData || undefined }
    set((s) => ({ messages: [...s.messages, userMsg] }))

    let assistantMsg: Message = { id: nextMsgId(), role: 'assistant', content: '' }
    let assistantAdded = false

    try {
      const stream = api.sendMessage(userId, content, currentConvId, messages, imageData)
      for await (const event of stream) {
        if (event.type === 'status') {
          set({ statusText: event.text || '' })
        } else if (event.type === 'token') {
          if (!assistantAdded) {
            assistantAdded = true
            set((s) => ({ messages: [...s.messages, assistantMsg], isLoading: false, statusText: '' }))
          }
          assistantMsg = { ...assistantMsg, content: assistantMsg.content + (event.text || '') }
          set((s) => ({
            messages: [...s.messages.slice(0, -1), assistantMsg],
          }))
        } else if (event.type === 'reply') {
          const finalContent = event.text || assistantMsg.content
          if (!assistantAdded) {
            assistantAdded = true
            const reply: Message = { role: 'assistant', content: finalContent }
            set((s) => ({ messages: [...s.messages, reply], isLoading: false, statusText: '' }))
          } else {
            assistantMsg = { ...assistantMsg, content: finalContent }
            set((s) => ({
              messages: [...s.messages.slice(0, -1), assistantMsg],
              isLoading: false,
              statusText: '',
            }))
          }
        } else if (event.type === 'done') {
          if (event.conversation_id && !currentConvId) {
            set({ currentConvId: event.conversation_id })
          }
          get().loadConversations()
          get().loadMemoryStats()
          yield
        } else if (event.type === 'error') {
          set({ isLoading: false, statusText: '' })
          throw new Error(event.text || 'Unknown error')
        }
      }
    } catch (e) {
      const errMsg: Message = {
        role: 'assistant',
        content: `抱歉，出现了一些问题：${e instanceof Error ? e.message : '未知错误'}`,
      }
      if (!assistantAdded) {
        set((s) => ({ messages: [...s.messages, errMsg], isLoading: false, statusText: '' }))
      } else {
        set((s) => ({
          messages: [...s.messages.slice(0, -1), errMsg],
          isLoading: false,
          statusText: '',
        }))
      }
    }
  },

  retryLastMessage: async function* () {
    const { lastFailedMessage } = get()
    if (!lastFailedMessage) return
    yield* get().sendMessage(lastFailedMessage.content, lastFailedMessage.imageData)
  },
}))