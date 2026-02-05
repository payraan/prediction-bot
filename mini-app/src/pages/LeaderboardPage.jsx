/**
 * Leaderboard Page
 * صفحه لیدربورد - نمایش Top 50 و آمار خودم
 */

import { useEffect, useState } from 'react'
import WebApp from '@twa-dev/sdk'
import { getLeaderboardTop, getMyStats } from '../api/client'
import { Trophy, TrendingUp, TrendingDown } from 'lucide-react'

export default function LeaderboardPage() {
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState([])
  const [myStats, setMyStats] = useState(null)
  const [error, setError] = useState(null)

  const telegramId = WebApp?.initDataUnsafe?.user?.id

  useEffect(() => {
    let mounted = true

    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [leaderboard, stats] = await Promise.all([
          getLeaderboardTop(50, 0),
          telegramId ? getMyStats(telegramId) : Promise.resolve(null),
        ])

        if (!mounted) return
        setRows(leaderboard || [])
        setMyStats(stats)
      } catch (e) {
        if (!mounted) return
        setError(e?.message || 'خطا در دریافت اطلاعات')
        console.error('Leaderboard error:', e)
      } finally {
        if (!mounted) return
        setLoading(false)
      }
    }

    loadData()
    return () => { mounted = false }
  }, [telegramId])

  if (loading) {
    return (
      <div className="page">
        <div className="card">
          <p style={{ textAlign: 'center', opacity: 0.7 }}>در حال بارگذاری...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <div className="card">
          <p style={{ textAlign: 'center', color: '#ef4444' }}>❌ {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Trophy size={28} color="#FFD700" />
          لیدربورد
        </h2>
        <p style={{ opacity: 0.7, marginTop: 8 }}>50 تریدر برتر</p>
      </div>

      {myStats && (
        <div className="card" style={{ marginBottom: 16, background: 'rgba(255, 215, 0, 0.08)' }}>
          <h3 style={{ marginBottom: 12, fontSize: 16 }}>📊 آمار شما</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div style={{ opacity: 0.7, fontSize: 13 }}>برد / باخت</div>
              <div style={{ fontWeight: 700, marginTop: 4 }}>
                <span style={{ color: '#10b981' }}>{myStats.wins}</span>
                {' / '}
                <span style={{ color: '#ef4444' }}>{myStats.losses}</span>
              </div>
            </div>
            <div>
              <div style={{ opacity: 0.7, fontSize: 13 }}>Win Rate</div>
              <div style={{ fontWeight: 700, marginTop: 4 }}>
                {myStats.win_rate}%
              </div>
            </div>
            <div>
              <div style={{ opacity: 0.7, fontSize: 13 }}>PNL</div>
              <div style={{ fontWeight: 700, marginTop: 4, color: myStats.net_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                {myStats.net_pnl > 0 ? '+' : ''}{myStats.net_pnl} TON
              </div>
            </div>
            <div>
              <div style={{ opacity: 0.7, fontSize: 13 }}>امتیاز</div>
              <div style={{ fontWeight: 700, marginTop: 4, color: '#FFD700' }}>
                {myStats.score}
              </div>
            </div>
          </div>
          {myStats.win_streak > 0 && (
            <div style={{ marginTop: 12, padding: 8, background: 'rgba(16, 185, 129, 0.1)', borderRadius: 8 }}>
              🔥 استریک فعلی: <strong>{myStats.win_streak}</strong> برد
            </div>
          )}
        </div>
      )}

      <div className="card">
        {rows.length === 0 ? (
          <p style={{ textAlign: 'center', opacity: 0.7 }}>هنوز کسی شرط‌بندی نکرده!</p>
        ) : (
          <div>
            {rows.map((row) => {
              const isMe = telegramId && row.telegram_id === telegramId
              const medal = row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : row.rank === 3 ? '🥉' : ''
              
              return (
                <div
                  key={`${row.telegram_id}-${row.rank}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 0',
                    borderBottom: row.rank < rows.length ? '1px solid rgba(255,255,255,0.06)' : 'none',
                    background: isMe ? 'rgba(255, 215, 0, 0.08)' : 'transparent',
                    marginLeft: isMe ? -16 : 0,
                    marginRight: isMe ? -16 : 0,
                    paddingLeft: isMe ? 16 : 0,
                    paddingRight: isMe ? 16 : 0,
                    borderRadius: isMe ? 8 : 0,
                  }}
                >
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', flex: 1 }}>
                    <div style={{ width: 32, fontWeight: 700, fontSize: 16 }}>
                      {medal || `#${row.rank}`}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 15 }}>
                        {row.username ? `@${row.username}` : `User${String(row.telegram_id).slice(-4)}`}
                        {isMe && <span style={{ color: '#FFD700', marginLeft: 6 }}>← شما</span>}
                      </div>
                      <div style={{ opacity: 0.6, fontSize: 12, marginTop: 2 }}>
                        {row.wins}W • {row.losses}L • WR {row.win_rate}%
                      </div>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 800, fontSize: 16, color: '#FFD700' }}>
                      {row.score}
                    </div>
                    <div style={{ opacity: 0.6, fontSize: 11 }}>امتیاز</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
