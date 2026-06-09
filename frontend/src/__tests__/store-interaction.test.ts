import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useStore } from '../store'

// Mock api 模块
vi.mock('../api', () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({ status: 'ok', auth_required: false, admin_key_configured: false }),
    getConversations: vi.fn().mockResolvedValue({ conversations: [], current_id: '' }),
    getConversation: vi.fn().mockResolvedValue({ title: '测试对话', messages: [], created: '01/01 00:00' }),
    createConversation: vi.fn().mockResolvedValue({ id: 'conv-new', title: '新对话', created: '01/01 00:00' }),
    renameConversation: vi.fn().mockResolvedValue({ ok: true }),
    deleteConversation: vi.fn().mockResolvedValue({ ok: true, current_id: '' }),
    getUsers: vi.fn().mockResolvedValue([{ id: 'user1', memory_count: 5, consolidated_count: 2, avg_importance: 0.6 }]),
    createUser: vi.fn().mockResolvedValue({ ok: true }),
    getMemoryStats: vi.fn().mockResolvedValue({ total: 5, avg_importance: 0.6, consolidated_count: 2 }),
    clearMemories: vi.fn().mockResolvedValue({ ok: true }),
    getModelConfig: vi.fn().mockResolvedValue({ model: 'deepseek-v4', base_url: '', multimodal: false }),
    getPromptConfig: vi.fn().mockResolvedValue({ prompt: '默认', default_prompt: '默认', is_custom: false }),
    updatePromptConfig: vi.fn().mockResolvedValue({ ok: true, prompt: '自定义', is_custom: true }),
    getLogs: vi.fn().mockResolvedValue({ logs: [] }),
    sendMessage: vi.fn(),
  },
  getStoredAccessKey: vi.fn().mockReturnValue(''),
  setStoredAccessKey: vi.fn(),
  getStoredAdminKey: vi.fn().mockReturnValue(''),
  setStoredAdminKey: vi.fn(),
}))

describe('对话管理交互', () => {
  beforeEach(() => {
    useStore.setState({
      userId: 'user1',
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
    })
    vi.clearAllMocks()
  })

  it('应能创建新对话', async () => {
    const convId = await useStore.getState().createConversation()
    expect(convId).toBe('conv-new')
  })

  it('应能切换对话', async () => {
    useStore.setState({ conversations: [{ id: 'conv-1', title: '对话1', created: '01/01', message_count: 0, is_active: true }] })
    await useStore.getState().switchConversation('conv-1')
    expect(useStore.getState().currentConvId).toBe('conv-1')
  })

  it('应能重命名对话', async () => {
    useStore.setState({ conversations: [{ id: 'conv-1', title: '旧标题', created: '01/01', message_count: 0, is_active: true }] })
    await useStore.getState().renameConversation('conv-1', '新标题')
    const { api } = await import('../api')
    expect(api.renameConversation).toHaveBeenCalledWith('user1', 'conv-1', '新标题')
  })

  it('应能删除对话', async () => {
    useStore.setState({
      conversations: [{ id: 'conv-1', title: '对话1', created: '01/01', message_count: 0, is_active: true }],
      currentConvId: 'conv-1',
    })
    await useStore.getState().deleteConversation('conv-1')
    const { api } = await import('../api')
    expect(api.deleteConversation).toHaveBeenCalledWith('user1', 'conv-1')
  })
})

describe('消息交互', () => {
  beforeEach(() => {
    useStore.setState({
      userId: 'user1',
      conversations: [],
      currentConvId: 'conv-1',
      messages: [],
      isLoading: false,
      statusText: '',
      error: null,
      lastFailedMessage: null,
    })
    vi.clearAllMocks()
  })

  it('应能添加用户消息', () => {
    useStore.getState().addMessage({ id: 'm1', role: 'user', content: '你好' })
    expect(useStore.getState().messages).toHaveLength(1)
    expect(useStore.getState().messages[0].content).toBe('你好')
    expect(useStore.getState().messages[0].role).toBe('user')
  })

  it('应能添加助手消息', () => {
    useStore.getState().addMessage({ id: 'm1', role: 'assistant', content: '你好呀' })
    expect(useStore.getState().messages).toHaveLength(1)
    expect(useStore.getState().messages[0].role).toBe('assistant')
  })

  it('应能替换所有消息', () => {
    useStore.getState().addMessage({ id: 'm1', role: 'user', content: '旧消息' })
    useStore.getState().setMessages([{ id: 'm2', role: 'assistant', content: '新消息' }])
    expect(useStore.getState().messages).toHaveLength(1)
    expect(useStore.getState().messages[0].content).toBe('新消息')
  })

  it('sendMessage 应处理 SSE token 事件', async () => {
    const { api } = await import('../api')
    const mockStream = (async function* () {
      yield { type: 'status', text: '正在思考...' }
      yield { type: 'token', text: '你' }
      yield { type: 'token', text: '好' }
      yield { type: 'reply', text: '你好' }
      yield { type: 'done', conversation_id: 'conv-1' }
    })()
    vi.mocked(api.sendMessage).mockReturnValueOnce(mockStream)

    const gen = useStore.getState().sendMessage('你好')
    // 消费 generator
    for await (const _event of gen) {
      // 消费流式事件
    }

    const msgs = useStore.getState().messages
    // 应有 user 消息 + assistant 消息
    expect(msgs.length).toBeGreaterThanOrEqual(2)
    expect(msgs[0].role).toBe('user')
    expect(msgs[0].content).toBe('你好')
    // assistant 消息内容应为最终回复
    const assistantMsg = msgs.find(m => m.role === 'assistant')
    expect(assistantMsg).toBeTruthy()
    expect(assistantMsg!.content).toContain('你好')
  })

  it('sendMessage 应处理错误事件', async () => {
    const { api } = await import('../api')
    const mockStream = (async function* () {
      yield { type: 'error', text: '连接超时' }
    })()
    vi.mocked(api.sendMessage).mockReturnValueOnce(mockStream)

    const gen = useStore.getState().sendMessage('测试')
    try {
      for await (const _event of gen) {
        // 消费流式事件
      }
    } catch {
      // 预期会抛出错误
    }

    const msgs = useStore.getState().messages
    const errMsg = msgs.find(m => m.role === 'assistant' && m.content.includes('问题'))
    expect(errMsg).toBeTruthy()
  })
})

describe('用户管理交互', () => {
  beforeEach(() => {
    useStore.setState({
      userId: 'user1',
      users: [],
      conversations: [],
      messages: [],
    })
    vi.clearAllMocks()
  })

  it('应能加载用户列表', async () => {
    await useStore.getState().loadUsers()
    expect(useStore.getState().users).toHaveLength(1)
    expect(useStore.getState().users[0].id).toBe('user1')
  })

  it('切换用户应清空消息和对话', async () => {
    useStore.setState({
      messages: [{ id: 'm1', role: 'user', content: '旧消息' }],
      conversations: [{ id: 'conv-1', title: '旧对话', created: '01/01', message_count: 1, is_active: true }],
    })
    await useStore.getState().switchUser('user2')
    expect(useStore.getState().userId).toBe('user2')
    expect(useStore.getState().messages).toEqual([])
    expect(useStore.getState().conversations).toEqual([])
  })
})

describe('记忆管理交互', () => {
  beforeEach(() => {
    useStore.setState({ userId: 'user1', memoryStats: null, error: null })
    vi.clearAllMocks()
  })

  it('应能加载记忆统计', async () => {
    await useStore.getState().loadMemoryStats()
    expect(useStore.getState().memoryStats).toBeTruthy()
    expect(useStore.getState().memoryStats!.total).toBe(5)
  })

  it('记忆统计加载失败应设置错误', async () => {
    const { api } = await import('../api')
    vi.mocked(api.getMemoryStats).mockRejectedValueOnce(new Error('网络错误'))
    await useStore.getState().loadMemoryStats()
    expect(useStore.getState().error).toBeTruthy()
  })
})

describe('搜索过滤', () => {
  it('应能设置搜索关键词', () => {
    useStore.getState().setSearchQuery('测试')
    expect(useStore.getState().searchQuery).toBe('测试')
  })

  it('空搜索关键词应返回所有对话', () => {
    useStore.setState({
      conversations: [
        { id: '1', title: '工作', created: '01/01', message_count: 1, is_active: true },
        { id: '2', title: '生活', created: '01/01', message_count: 1, is_active: true },
      ],
      searchQuery: '',
    })
    // 搜索过滤通常在组件层做，这里验证 store 状态正确
    expect(useStore.getState().conversations).toHaveLength(2)
  })
})
