import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { LogEntry } from '../types'
import './LogViewerModal.css'

interface Props {
  onClose: () => void
}

export default function LogViewerModal({ onClose }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [paused, setPaused] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const autoScrollRef = useRef(true)
  const intervalRef = useRef<ReturnType<typeof setInterval>>()

  const fetchLogs = async () => {
    try {
      const data = await api.getLogs(300)
      setLogs(data.logs)
    } catch { /* backend may not have restarted yet */ }
  }

  useEffect(() => {
    fetchLogs()
    intervalRef.current = setInterval(() => {
      if (!paused) fetchLogs()
    }, 2000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [paused])

  useEffect(() => {
    if (autoScrollRef.current && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [logs])

  const handleScroll = () => {
    if (!bodyRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = bodyRef.current
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 40
  }

  return (
    <div className="log-viewer-overlay" onClick={onClose}>
      <div className="log-viewer-content" onClick={(e) => e.stopPropagation()}>
        <div className="log-viewer-header">
          <span className="log-viewer-title">系统日志</span>
          <div className="log-viewer-actions">
            <span className="log-viewer-badge">{logs.length}</span>
            <button
              className="log-viewer-btn"
              onClick={() => { setPaused(!paused); if (paused) fetchLogs() }}
            >
              {paused ? '▶ 恢复' : '⏸ 暂停'}
            </button>
            <button className="log-viewer-btn log-viewer-btn--close" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div className="log-viewer-body" ref={bodyRef} onScroll={handleScroll}>
          {logs.length === 0 ? (
            <div className="log-viewer-empty">暂无日志，发送一条消息后即可看到</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="log-viewer-line">
                <span className="log-viewer-index">{i + 1}</span>
                <span className={`log-viewer-level log-level-${log.level}`}>{log.level}</span>
                <span className="log-viewer-text">{log.message}</span>
              </div>
            ))
          )}
        </div>
        <div className="log-viewer-resize-hint" />
      </div>
    </div>
  )
}