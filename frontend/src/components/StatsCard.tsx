import { useStore } from '../store'
import './StatsCard.css'

export default function StatsCard() {
  const memoryStats = useStore((s) => s.memoryStats)
  const userId = useStore((s) => s.userId)

  if (!memoryStats) return null

  const { total, consolidated_count, avg_importance } = memoryStats

  return (
    <div className="stats-card">
      <div className="stats-card-user">
        <div className="stats-card-avatar">{userId.charAt(0).toUpperCase() || 'U'}</div>
        <div>
          <div className="stats-card-user-name">{userId.slice(0, 14)}</div>
          <div className="stats-card-user-label">当前用户</div>
        </div>
      </div>

      {total > 0 ? (
        <>
          <div className="stats-card-divider" />
          <div className="stats-card-grid">
            <div className="stats-card-item">
              <div className="stats-card-value">{total}</div>
              <div className="stats-card-key">记忆总数</div>
            </div>
            <div className="stats-card-item">
              <div className="stats-card-value">{consolidated_count}</div>
              <div className="stats-card-key">巩固记忆</div>
            </div>
            <div className="stats-card-item">
              <div className="stats-card-value">{avg_importance.toFixed(1)}</div>
              <div className="stats-card-key">重要性</div>
            </div>
          </div>
        </>
      ) : (
        <div className="stats-card-empty">暂无记忆数据</div>
      )}
    </div>
  )
}