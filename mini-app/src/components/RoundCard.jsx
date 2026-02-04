/**
 * کارت راند فعال
 */

import { useCountdown } from '../hooks/useApi'

export default function RoundCard({ round, onBet, selectedDirection, betAmount }) {
  const { formatted, isExpired } = useCountdown(round?.seconds_remaining)
  
  // حالت ۱: هیچ راندی نیست
  if (!round) {
    return (
      <div className="round-card empty">
        <p>در انتظار راند جدید...</p>
      </div>
    )
  }

  // حالت ۲: راند LOCKED هست (منتظر نتیجه)
  if (round.ui_state === 'LOCKED_WAITING_RESULT' || round.status === 'LOCKED') {
    return (
      <div className="round-card locked">
        <div className="round-header">
          <span className="round-timer locked">⏳ تا نتیجه: {formatted}</span>
        </div>
        
        <div className="locked-message">
          <span className="lock-icon">🔒</span>
          <p>{round.message_fa || 'راند قفل شد، منتظر نتیجه...'}</p>
          {round.lock_price && (
            <p className="lock-price">قیمت قفل: ${round.lock_price.toLocaleString()}</p>
          )}
        </div>

        <div className="pool-display">
          <div className="pool-bar">
            <div className="pool-up" style={{ width: `${round.total_up > 0 ? (round.total_up / (round.total_up + round.total_down) * 100) : 50}%` }}>
              {round.total_up > 0 ? ((round.total_up / (round.total_up + round.total_down)) * 100).toFixed(0) : 50}%
            </div>
            <div className="pool-down" style={{ width: `${round.total_down > 0 ? (round.total_down / (round.total_up + round.total_down) * 100) : 50}%` }}>
              {round.total_down > 0 ? ((round.total_down / (round.total_up + round.total_down)) * 100).toFixed(0) : 50}%
            </div>
          </div>
          <div className="pool-amounts">
            <span className="up">📈 {(round.total_up || 0).toFixed(2)} TON</span>
            <span className="down">📉 {(round.total_down || 0).toFixed(2)} TON</span>
          </div>
        </div>
      </div>
    )
  }

  // حالت ۳: راند باز برای شرط‌بندی
  const totalPool = (round.total_up || 0) + (round.total_down || 0)
  const upPercent = totalPool > 0 ? ((round.total_up / totalPool) * 100).toFixed(0) : 50
  const downPercent = totalPool > 0 ? ((round.total_down / totalPool) * 100).toFixed(0) : 50

  const isLocked = round.status !== 'BETTING_OPEN' || isExpired

  return (
    <div className="round-card">
      <div className="round-header">
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
