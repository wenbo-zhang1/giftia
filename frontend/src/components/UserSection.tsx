import { useState } from 'react'
import { useStore } from '../store'
import './UserSection.css'

export default function UserSection() {
  const userId = useStore((s) => s.userId)
  const users = useStore((s) => s.users)
  const switchUser = useStore((s) => s.switchUser)
  const createUser = useStore((s) => s.createUser)
  const [newUserId, setNewUserId] = useState('')
  const [showAdd, setShowAdd] = useState(false)

  const handleSwitch = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value
    if (newId !== userId) {
      await switchUser(newId)
    }
  }

  const handleCreate = async () => {
    const trimmed = newUserId.trim()
    if (!trimmed) return
    await createUser(trimmed)
    await switchUser(trimmed)
    setNewUserId('')
    setShowAdd(false)
  }

  return (
    <div className="user-section">
      <div className="user-section-label">用户</div>
      <select
        className="user-section-select"
        value={userId}
        onChange={handleSwitch}
      >
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.id} · {u.memory_count} 记忆
          </option>
        ))}
      </select>

      {!showAdd ? (
        <button className="user-section-add-toggle" onClick={() => setShowAdd(true)}>
          ＋ 添加用户
        </button>
      ) : (
        <div className="user-section-add-form">
          <input
            type="text"
            className="user-section-add-input"
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setShowAdd(false) }}
            placeholder="输入 ID…"
            autoFocus
          />
          <button className="user-section-add-btn" onClick={handleCreate}>创建</button>
          <button className="user-section-add-cancel" onClick={() => setShowAdd(false)}>取消</button>
        </div>
      )}
    </div>
  )
}