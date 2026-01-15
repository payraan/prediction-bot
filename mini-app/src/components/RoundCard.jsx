/**
 * کارت راند فعال
 */

import { useCountdown } from '../hooks/useApi'

export default function RoundCard({ round, onBet, selectedDirection, betAmount }) {
  // استفاده از seconds_remaining که از API میاد
  const { formatted, isExpired } = useCountdown(round?.seconds_remaining)
  
  if (!round) {
    return (
      <div className="round-card empty">
        <p>در انتظار راند جدید...</p>
      </div>
    )
  }

  const totalPool = (round.total_up || 0) + (round.total_down || 0)
  const upPercent = totalPool > 0 ? ((round.total_up / totalPool) * 100).toFixed(0) : 50
  const downPercent = totalPool > 0 ? ((round.total_down / totalPool) * 100).toFixed(0) : 50

  const isLocked = round.status !== 'BETTING_OPEN' || isExpired

  return (
    <div className="round-card">
      <div className="round-header">
        <span className="round-number">راند #{round.round_number}</span>
        <span className={`round-timer ${isExpired ? 'expired' : ''}`}>
          {isExpired ? 'بسته شد' : formatted}
        </span>
      </div>

      <div className="pool-display">
        <div className="pool-bar">
          <div className="pool-up" style={{ width: `${upPercent}%` }}>
            {upPercent}%
          </div>
          <div className="pool-down" style={{ width: `${downPercent}%` }}>
            {downPercent}%
          </div>
        </div>
        <div className="pool-amounts">
          <span className="up">📈 {(round.total_up || 0).toFixed(2)} TON</span>
          <span className="down">📉 {(round.total_down || 0).toFixed(2)} TON</span>
        </div>
      </div>

      <div className="bet-buttons">
        <button
          className={`bet-btn up ${selectedDirection === 'UP' ? 'selected' : ''}`}
          onClick={() => onBet('UP')}
          disabled={isLocked}
        >
          <span className="btn-icon">📈</span>
          <span className="btn-label">بالا می‌ره</span>
        </button>
        
        <button
          className={`bet-btn down ${selectedDirection === 'DOWN' ? 'selected' : ''}`}
          onClick={() => onBet('DOWN')}
          disabled={isLocked}
        >
          <span className="btn-icon">📉</span>
          <span className="btn-label">پایین می‌ره</span>
        </button>
      </div>
    </div>
  )
}
