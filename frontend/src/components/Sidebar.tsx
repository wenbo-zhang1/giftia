import { useState } from 'react'
import { useStore } from '../store'
import ConversationList from './ConversationList'
import UserSection from './UserSection'
import StatsCard from './StatsCard'
import ModelDialog from './ModelDialog'
import ConfirmDialog from './ConfirmDialog'
import LogViewerModal from './LogViewerModal'
import PromptDialog from './PromptDialog'
import './Sidebar.css'

export default function Sidebar() {
  const modelConfig = useStore((s) => s.modelConfig)
  const createConversation = useStore((s) => s.createConversation)
  const clearMemories = useStore((s) => s.clearMemories)
  const [showModel, setShowModel] = useState(false)
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)

  const handleNewChat = async () => {
    await createConversation()
  }

  const handleClearMemories = async () => {
    await clearMemories()
    setShowClearConfirm(false)
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <img src="/logo.jpg" alt="Giftia" className="sidebar-brand-logo" />
        </div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-name">Giftia</div>
          <div className="sidebar-brand-sub">AI 情感陪伴</div>
        </div>
        {modelConfig && (
          <button className="sidebar-brand-model" onClick={() => setShowModel(true)} title="当前模型">
            <span className="sidebar-brand-model-dot" />
            <span className="sidebar-brand-model-label">{modelConfig.model}</span>
          </button>
        )}
      </div>

      <button className="sidebar-new-chat" onClick={handleNewChat}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        开启新对话
      </button>

      <ConversationList />

      <div className="sidebar-divider" />

      <UserSection />

      <div className="sidebar-actions">
        <button className="sidebar-action-btn" onClick={() => setShowPrompt(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          自定义人设
        </button>
        <button className="sidebar-action-btn" onClick={() => setShowLogs(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          查看日志
        </button>
        <button className="sidebar-action-btn sidebar-action-btn--danger" onClick={() => setShowClearConfirm(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          清除记忆
        </button>
      </div>

      <StatsCard />

      {showModel && <ModelDialog onClose={() => setShowModel(false)} />}
      {showLogs && <LogViewerModal onClose={() => setShowLogs(false)} />}
      {showPrompt && <PromptDialog onClose={() => setShowPrompt(false)} />}
      {showClearConfirm && (
        <ConfirmDialog
          title="清除记忆"
          message="确定清除此用户的所有记忆？不可撤销。"
          onConfirm={handleClearMemories}
          onCancel={() => setShowClearConfirm(false)}
        />
      )}
    </aside>
  )
}