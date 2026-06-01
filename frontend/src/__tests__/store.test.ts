import { describe, it, expect, beforeEach } from 'vitest'
import { useStore } from '../store'

describe('useStore', () => {
  beforeEach(() => {
    useStore.setState({
      userId: 'test_user',
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
  })

  it('should set userId', () => {
    useStore.getState().setUserId('new_user')
    expect(useStore.getState().userId).toBe('new_user')
  })

  it('should add a message', () => {
    useStore.getState().addMessage({ id: '1', role: 'user', content: 'hello' })
    expect(useStore.getState().messages).toHaveLength(1)
    expect(useStore.getState().messages[0].content).toBe('hello')
  })

  it('should set messages', () => {
    useStore
      .getState()
      .setMessages([{ id: '1', role: 'assistant', content: 'hi' }])
    expect(useStore.getState().messages).toHaveLength(1)
  })

  it('should set search query', () => {
    useStore.getState().setSearchQuery('test')
    expect(useStore.getState().searchQuery).toBe('test')
  })

  it('should set status text', () => {
    useStore.getState().setStatusText('loading...')
    expect(useStore.getState().statusText).toBe('loading...')
  })

  it('should set auth keys and authenticate', () => {
    useStore.getState().setAuthKeys('access', 'admin')
    expect(useStore.getState().isAuthenticated).toBe(true)
  })
})