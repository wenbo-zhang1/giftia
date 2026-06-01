import { useState, useRef, useCallback } from 'react'
import { useStore } from '../store'
import './ChatInput.css'

export default function ChatInput() {
  const [text, setText] = useState('')
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageData, setImageData] = useState<string | null>(null)
  const isLoading = useStore((s) => s.isLoading)
  const sendMessage = useStore((s) => s.sendMessage)
  const modelConfig = useStore((s) => s.modelConfig)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleSubmit = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    setText('')
    setImagePreview(null)
    setImageData(null)
    const gen = sendMessage(trimmed, imageData || undefined)
    for await (const _ of gen) {
      // consume
    }
  }, [text, isLoading, imageData, sendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      setImagePreview(result)
      setImageData(result)
    }
    reader.readAsDataURL(file)
    if (fileRef.current) fileRef.current.value = ''
  }, [])

  return (
    <div className="chat-input-wrapper">
      {imagePreview && (
        <div className="chat-input-preview">
          <img src={imagePreview} alt="preview" />
          <button className="chat-input-preview-remove" onClick={() => { setImagePreview(null); setImageData(null) }}>
            ✕
          </button>
        </div>
      )}
      <div className="chat-input-container">
        <textarea
          ref={textareaRef}
          className="chat-input-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="和我说说你的心事吧..."
          rows={1}
          disabled={isLoading}
        />
        <div className="chat-input-actions">
          {modelConfig?.multimodal && (
            <>
              <button
                className="chat-input-attach"
                onClick={() => fileRef.current?.click()}
                title="上传图片"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                style={{ display: 'none' }}
                onChange={handleImageUpload}
              />
            </>
          )}
          <button
            className="chat-input-send"
            onClick={handleSubmit}
            disabled={!text.trim() || isLoading}
            title="发送"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}