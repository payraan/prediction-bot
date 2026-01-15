/**
 * صفحه تاریخچه شرط‌ها
 */

import { useState } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useBetHistory } from '../hooks/useApi'

const STATUS_LABELS = {
  PENDING: { text: 'در انتظار', class: 'pending' },
  WON: { text: 'برد ✓', class: 'won' },
  LOST: { text: 'باخت', class: 'lost' },
  REFUNDED: { text: 'برگشت', class: 'refunded' },
}

const FILTERS = [
  { id: 'all', label: 'همه' },
  { id: 'PENDING', label: 'در انتظار' },
  { id: 'WON', label: 'برد' },
  { id: 'LOST', label: 'باخت' },
]

export default function HistoryPage() {
  const { bets, loading, error, refetch } = useBetHistory(50)
  const [filter, setFilter] = useState('all')

  const filteredBets = filter === 'all' 
    ? bets 
    : bets.filter(bet => bet.status === filter)

  if (loading) {
    return (
      <div className="page history-page">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>در حال بارگذاری...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page history-page">
      <div className="history-header">
        <h2>📊 تاریخچه شرط‌ها</h2>
      </div>

      <div className="filter-tabs">
        {FILTERS.map(f => (
          <button
            key={f.id}
            className={`filter-btn ${filter === f.id ? 'active' : ''}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="bets-list">
        {filteredBets.length === 0 ? (
          <div className="empty-state">
            <p>شرطی یافت نشد</p>
          </div>
        ) : (
          filteredBets.map(bet => (
            <div key={bet.id} className={`bet-item ${bet.status.toLowerCase()}`}>
              <div className="bet-main">
                <div className="bet-direction">
                  {bet.direction === 'UP' ? (
                    <TrendingUp className="icon up" size={20} />
                  ) : (
                    <TrendingDown className="icon down" size={20} />
                  )}
                  <span>راند #{bet.round_number}</span>
                </div>
                <div className={`bet-status ${STATUS_LABELS[bet.status]?.class}`}>
                  {STATUS_LABELS[bet.status]?.text || bet.status}
                </div>
              </div>
              
              <div className="bet-details">
                <div className="bet-amount">
                  <span className="label">شرط:</span>
                  <span className="value">{bet.amount} TON</span>
                </div>
                {bet.payout > 0 && (
                  <div className="bet-payout">
                    <span className="label">برد:</span>
                    <span className="value won">+{bet.payout.toFixed(2)} TON</span>
                  </div>
                )}
              </div>
              
              <div className="bet-time">
                {new Date(bet.created_at).toLocaleString('fa-IR')}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
