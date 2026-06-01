import { useEffect, useState } from 'react'
import { useStore } from '../store'
import './PromptDialog.css'

interface Props {
  onClose: () => void
}

export default function PromptDialog({ onClose }: Props) {
  const promptConfig = useStore((s) => s.promptConfig)
  const loadPromptConfig = useStore((s) => s.loadPromptConfig)
  const updatePromptConfig = useStore((s) => s.updatePromptConfig)

  const [editing, setEditing] = useState(false)
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadPromptConfig()
  }, [loadPromptConfig])

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  const handleStartEdit = () => {
    setText(promptConfig?.prompt || '')
    setEditing(true)
    setMessage(null)
  }

  const handleReset = () => {
    setText(promptConfig?.default_prompt || '')
    setMessage(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      await updatePromptConfig(text)
      await loadPromptConfig()
      setEditing(false)
      setMessage({ type: 'success', text: '人设已保存，新对话即刻生效' })
    } catch (e) {
      setMessage({ type: 'error', text: `保存失败：${e instanceof Error ? e.message : '未知错误'}` })
    } finally {
      setSaving(false)
    }
  }

  const isCustom = promptConfig?.is_custom

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content prompt-dialog" onClick={(e) => e.stopPropagation()}>
        <h3 className="dialog-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8, verticalAlign: -3 }}>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          自定义人设
        </h3>

        <p className="prompt-dialog-desc">
          自定义你的 AI 情感伴侣的性格、说话风格和身份设定。修改后立即生效，无需重启服务。
        </p>

        {isCustom && !editing && (
          <div className="prompt-dialog-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style={{ marginRight: 4 }}>
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            当前使用自定义人设
          </div>
        )}

        {!editing ? (
          <div className="prompt-dialog-preview">
            <div className="prompt-dialog-preview-label">
              当前人设
              {isCustom && <span className="prompt-dialog-custom-tag">自定义</span>}
            </div>
            <pre className="prompt-dialog-preview-text">{promptConfig?.prompt || '加载中...'}</pre>
            <div className="prompt-dialog-actions">
              <button className="dialog-btn dialog-btn--primary" onClick={handleStartEdit}>
                {isCustom ? '修改人设' : '自定义人设'}
              </button>
              <button className="dialog-btn dialog-btn--secondary" onClick={onClose}>
                关闭
              </button>
            </div>
          </div>
        ) : (
          <div className="prompt-dialog-editor">
            <div className="prompt-dialog-editor-label">编辑人设提示词</div>
            <textarea
              className="prompt-dialog-textarea"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="描述你想要的 AI 伴侣的性格、身份、说话风格..."
              rows={12}
              autoFocus
            />
            <div className="prompt-dialog-char-count">
              {text.length} / 5000
            </div>
            <div className="prompt-dialog-editor-tips">
              <p>💡 提示：好的提示词应该包含：</p>
              <ul>
                <li>身份设定（名字、性格、关系）</li>
                <li>说话风格（语气、用词习惯）</li>
                <li>行为规则（如何回应用户）</li>
              </ul>
            </div>
            <div className="prompt-dialog-actions">
              <button
                className="dialog-btn dialog-btn--primary"
                onClick={handleSave}
                disabled={saving || text.length > 5000}
              >
                {saving ? '保存中...' : '保存并生效'}
              </button>
              <button className="dialog-btn dialog-btn--secondary" onClick={handleReset}>
                恢复默认
              </button>
              <button
                className="dialog-btn dialog-btn--secondary"
                onClick={() => { setEditing(false); setMessage(null) }}
              >
                取消
              </button>
            </div>
          </div>
        )}

        {message && (
          <div className={`prompt-dialog-message prompt-dialog-message--${message.type}`}>
            {message.text}
          </div>
        )}
      </div>
    </div>
  )
}
