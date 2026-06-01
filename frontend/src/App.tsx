import { useEffect, useState } from 'react'
import { useStore } from './store'
import { getStoredAccessKey, getStoredAdminKey } from './api'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import ErrorBoundary from './components/ErrorBoundary'
import './App.css'

function AuthGate() {
  const setAuthKeys = useStore((s) => s.setAuthKeys)
  const [accessKey, setAccessKey] = useState(getStoredAccessKey())
  const [adminKey, setAdminKey] = useState(getStoredAdminKey())
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!accessKey.trim()) {
      setError('请输入访问密钥')
      return
    }
    setAuthKeys(accessKey.trim(), adminKey.trim())
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="var(--color-accent)">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z" />
          </svg>
        </div>
        <h2 className="auth-title">Giftia 需要验证</h2>
        <p className="auth-desc">此服务已启用访问认证，请输入密钥以继续</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-label">
            访问密钥
            <input
              type="password"
              className="auth-input"
              value={accessKey}
              onChange={(e) => { setAccessKey(e.target.value); setError('') }}
              placeholder="输入访问密钥"
              autoFocus
            />
          </label>
          <label className="auth-label">
            管理员密钥 <span className="auth-optional">（可选）</span>
            <input
              type="password"
              className="auth-input"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="输入管理员密钥"
            />
          </label>
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" className="auth-submit">
            验证并进入
          </button>
        </form>
      </div>
    </div>
  )
}

export default function App() {
  const loadConversations = useStore((s) => s.loadConversations)
  const loadUsers = useStore((s) => s.loadUsers)
  const loadMemoryStats = useStore((s) => s.loadMemoryStats)
  const loadModelConfig = useStore((s) => s.loadModelConfig)
  const currentConvId = useStore((s) => s.currentConvId)
  const loadConversation = useStore((s) => s.loadConversation)
  const checkAuth = useStore((s) => s.checkAuth)
  const authRequired = useStore((s) => s.authRequired)
  const isAuthenticated = useStore((s) => s.isAuthenticated)

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (!isAuthenticated) return
    loadConversations()
    loadUsers()
    loadMemoryStats()
    loadModelConfig()
  }, [isAuthenticated, loadConversations, loadUsers, loadMemoryStats, loadModelConfig])

  useEffect(() => {
    if (currentConvId && isAuthenticated) {
      loadConversation(currentConvId)
    }
  }, [currentConvId, isAuthenticated, loadConversation])

  if (authRequired && !isAuthenticated) {
    return <AuthGate />
  }

  return (
    <ErrorBoundary>
      <div className="app-layout">
        <Sidebar />
        <ChatArea />
      </div>
    </ErrorBoundary>
  )
}
