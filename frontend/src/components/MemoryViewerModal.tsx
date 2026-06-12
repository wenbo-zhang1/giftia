import { useEffect, useState } from 'react'
import { api } from '../api'
import type { MemoryDetail, MemoryDetailResponse, UserProfileData } from '../types'
import './MemoryViewerModal.css'

interface Props {
  onClose: () => void
}

type TabKey = 'profile' | 'memories'

const TAB_LABELS: Record<TabKey, string> = {
  profile: '档案卡',
  memories: '记忆',
}

const CATEGORY_LABELS: Record<string, string> = {
  emotion: '情感',
  fact: '事实',
  relationship: '关系',
  event: '事件',
  preference: '偏好',
  goal: '目标',
  concern: '困扰',
}

const EMOTION_LABELS: Record<string, string> = {
  happy: '开心',
  sad: '难过',
  anxious: '焦虑',
  angry: '生气',
  neutral: '平静',
  excited: '兴奋',
  fearful: '害怕',
  grateful: '感恩',
  lonely: '孤独',
  hopeful: '希望',
  stressed: '压力',
  relieved: '释然',
}

function formatTime(ts: number): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return `${year}-${month}-${day} ${time}`
}

function getTemporalLabel(temporal: Record<string, any>): string | null {
  if (!temporal) return null
  const et = temporal.event_time
  if (et?.description) return et.description
  const tc = temporal.time_context
  if (tc?.season) return tc.season
  if (tc?.life_stage) return tc.life_stage
  return null
}

export default function MemoryViewerModal({ onClose }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>('profile')
  const [loading, setLoading] = useState(true)
  const [memoryData, setMemoryData] = useState<MemoryDetailResponse | null>(null)
  const [profile, setProfile] = useState<UserProfileData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const userId = 'web_user_001' // current user
        const [memRes, profRes] = await Promise.all([
          api.getMemoryDetail(userId),
          api.getUserProfile(userId),
        ])
        setMemoryData(memRes)
        setProfile(profRes.profile)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const tabs: TabKey[] = ['profile', 'memories']

  const totalMemories = memoryData
    ? (memoryData.layers.core?.length ?? 0) +
      (memoryData.layers.important?.length ?? 0) +
      (memoryData.layers.regular?.length ?? 0)
    : 0

  const getTabCount = (tab: TabKey): number => {
    if (tab === 'profile') return -1
    return totalMemories
  }

  // 合并所有层级记忆，按创建时间倒序，附带层级标记
  const allMemories: (MemoryDetail & { layer: 'core' | 'important' | 'regular' })[] = []
  if (memoryData) {
    for (const m of memoryData.layers.core ?? []) allMemories.push({ ...m, layer: 'core' })
    for (const m of memoryData.layers.important ?? []) allMemories.push({ ...m, layer: 'important' })
    for (const m of memoryData.layers.regular ?? []) allMemories.push({ ...m, layer: 'regular' })
    allMemories.sort((a, b) => b.created_at - a.created_at)
  }

  return (
    <div className="mem-viewer-overlay" onClick={onClose}>
      <div className="mem-viewer-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="mem-viewer-header">
          <span className="mem-viewer-title">记忆查看器</span>
          <button className="mem-viewer-close" onClick={onClose}>&times;</button>
        </div>

        {/* Working Memory Summary */}
        {memoryData?.working_memory && memoryData.working_memory.summary && (
          <div className="mem-working-bar">
            <div className="mem-working-label">工作记忆</div>
            <div className="mem-working-summary">{memoryData.working_memory.summary}</div>
            {memoryData.working_memory.open_topics.length > 0 && (
              <div className="mem-working-topics">
                {memoryData.working_memory.open_topics.map((t, i) => (
                  <span key={i} className="mem-topic-tag">{t}</span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tabs */}
        <div className="mem-viewer-tabs">
          {tabs.map((tab) => {
            const count = getTabCount(tab)
            return (
              <button
                key={tab}
                className={`mem-tab ${activeTab === tab ? 'mem-tab--active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {TAB_LABELS[tab]}
                {count >= 0 && <span className="mem-tab-count">{count}</span>}
              </button>
            )
          })}
        </div>

        {/* Body */}
        <div className="mem-viewer-body">
          {loading && <div className="mem-viewer-loading">加载中...</div>}
          {error && <div className="mem-viewer-error">{error}</div>}

          {!loading && !error && activeTab === 'profile' && profile && (
            <ProfileView profile={profile} coreMemories={memoryData?.layers.core ?? []} />
          )}
          {!loading && !error && activeTab === 'memories' && (
            <MemoryList memories={allMemories} />
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Profile Tab ── */
function ProfileView({ profile, coreMemories }: { profile: UserProfileData; coreMemories: MemoryDetail[] }) {
  const { identity, preferences, relationships, emotional_profile } = profile

  const hasData = (obj: Record<string, any>) =>
    Object.values(obj).some((v) => v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0))

  const isEmpty =
    !hasData(identity) && !hasData(preferences) && !hasData(relationships) && !hasData(emotional_profile)
    && coreMemories.length === 0

  if (isEmpty) {
    return <div className="mem-empty">暂无档案信息，多聊聊就会自动建立</div>
  }

  return (
    <div className="mem-profile">
      {hasData(identity) && (
        <Section title="基本信息">
          <KVGrid data={identity} labelMap={{
            name: '姓名', age: '年龄', gender: '性别',
            occupation: '职业', location: '地点', education: '学历',
          }} />
        </Section>
      )}

      {hasData(preferences) && (
        <Section title="喜好偏好">
          {Object.entries(preferences).map(([key, val]) => {
            if (!val || (Array.isArray(val) && val.length === 0)) return null
            const items = Array.isArray(val) ? val : [val]
            return (
              <div key={key} className="mem-pref-row">
                <span className="mem-pref-key">{prefLabel(key)}</span>
                <div className="mem-pref-tags">
                  {items.map((item: string, i: number) => (
                    <span key={i} className="mem-pref-tag">{item}</span>
                  ))}
                </div>
              </div>
            )
          })}
        </Section>
      )}

      {hasData(relationships) && (
        <Section title="人际关系">
          {relationships.family && relationships.family.length > 0 && (
            <div className="mem-rel-group">
              <div className="mem-rel-label">家人</div>
              {relationships.family.map((r: any, i: number) => (
                <div key={i} className="mem-rel-item">
                  <span className="mem-rel-relation">{r.relation}</span>
                  {r.name && <span className="mem-rel-name">{r.name}</span>}
                  {r.description && <span className="mem-rel-desc">{r.description}</span>}
                </div>
              ))}
            </div>
          )}
          {relationships.friends && relationships.friends.length > 0 && (
            <div className="mem-rel-group">
              <div className="mem-rel-label">朋友</div>
              {relationships.friends.map((r: any, i: number) => (
                <div key={i} className="mem-rel-item">
                  {r.name && <span className="mem-rel-name">{r.name}</span>}
                  {r.description && <span className="mem-rel-desc">{r.description}</span>}
                </div>
              ))}
            </div>
          )}
          {relationships.romantic && (
            <div className="mem-rel-group">
              <div className="mem-rel-label">感情</div>
              <div className="mem-rel-item">
                {relationships.romantic.status && (
                  <span className="mem-rel-desc">{relationships.romantic.status}</span>
                )}
                {relationships.romantic.partner_name && (
                  <span className="mem-rel-name">{relationships.romantic.partner_name}</span>
                )}
              </div>
            </div>
          )}
        </Section>
      )}

      {hasData(emotional_profile) && (
        <Section title="情感模式">
          {emotional_profile.recent_mood_trend && (
            <div className="mem-emo-row">
              <span className="mem-emo-key">近期心情</span>
              <span className="mem-emo-val">{emotional_profile.recent_mood_trend}</span>
            </div>
          )}
          {emotional_profile.common_triggers?.length > 0 && (
            <div className="mem-emo-row">
              <span className="mem-emo-key">触发因素</span>
              <div className="mem-pref-tags">
                {emotional_profile.common_triggers.map((t: string, i: number) => (
                  <span key={i} className="mem-pref-tag mem-pref-tag--warn">{t}</span>
                ))}
              </div>
            </div>
          )}
          {emotional_profile.coping_strategies?.length > 0 && (
            <div className="mem-emo-row">
              <span className="mem-emo-key">应对策略</span>
              <div className="mem-pref-tags">
                {emotional_profile.coping_strategies.map((t: string, i: number) => (
                  <span key={i} className="mem-pref-tag">{t}</span>
                ))}
              </div>
            </div>
          )}
          {emotional_profile.support_preferences && (
            <div className="mem-emo-row">
              <span className="mem-emo-key">支持偏好</span>
              <span className="mem-emo-val">{emotional_profile.support_preferences}</span>
            </div>
          )}
        </Section>
      )}

      {coreMemories.length > 0 && (
        <Section title="核心记忆">
          <div className="mem-core-list">
            {coreMemories.map((m) => (
              <div key={m.id} className="mem-core-card">
                <span className="mem-core-emoji">{m.emotion_emoji}</span>
                <span className="mem-core-content">{m.content}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}

/* ── Memory List Tab ── */

const LAYER_BADGES: Record<string, { label: string; cls: string }> = {
  core:      { label: '核心', cls: 'mem-layer--core' },
  important: { label: '重要', cls: 'mem-layer--important' },
  regular:   { label: '常规', cls: 'mem-layer--regular' },
}

function MemoryList({ memories }: { memories: (MemoryDetail & { layer: 'core' | 'important' | 'regular' })[] }) {
  if (memories.length === 0) {
    return <div className="mem-empty">暂无记忆</div>
  }

  return (
    <div className="mem-list">
      {memories.map((m) => {
        const temporalLabel = getTemporalLabel(m.temporal_data)
        const badge = LAYER_BADGES[m.layer]
        return (
          <div key={m.id} className="mem-card">
            <div className="mem-card-header">
              <span className={`mem-layer-badge ${badge.cls}`}>{badge.label}</span>
              <span className="mem-card-emoji">{m.emotion_emoji}</span>
              <span className="mem-card-emotion">
                {EMOTION_LABELS[m.emotion] || m.emotion}
              </span>
              <span className="mem-card-category">
                {CATEGORY_LABELS[m.category] || m.category}
              </span>
              <span className="mem-card-time">{formatTime(m.created_at)}</span>
            </div>

            <div className="mem-card-content">{m.content}</div>

            {(temporalLabel || m.tags.length > 0) && (
              <div className="mem-card-tags">
                {temporalLabel && <span className="mem-tag mem-tag--time">{temporalLabel}</span>}
                {m.tags.map((t, i) => (
                  <span key={i} className="mem-tag">{t}</span>
                ))}
              </div>
            )}

            <div className="mem-card-meta">
              {m.is_consolidated && <span className="mem-meta-badge">已巩固</span>}
              <span className="mem-meta-count">检索 {m.access_count} 次</span>
              <span className="mem-meta-count">重要性 {(m.importance * 100).toFixed(0)}%</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── Shared Sub-components ── */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mem-section">
      <div className="mem-section-title">{title}</div>
      {children}
    </div>
  )
}

function KVGrid({ data, labelMap }: { data: Record<string, any>; labelMap: Record<string, string> }) {
  return (
    <div className="mem-kv-grid">
      {Object.entries(data).map(([key, val]) => {
        if (val === null || val === undefined || val === '') return null
        return (
          <div key={key} className="mem-kv-item">
            <span className="mem-kv-key">{labelMap[key] || key}</span>
            <span className="mem-kv-val">{String(val)}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ── Helpers ── */
function prefLabel(key: string): string {
  const map: Record<string, string> = {
    hobbies: '爱好', music: '音乐', movies: '电影',
    books: '书籍', food: '美食', travel: '旅行', other: '其他',
  }
  return map[key] || key
}
