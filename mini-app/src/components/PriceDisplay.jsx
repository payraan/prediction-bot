/**
 * نمایش قیمت لحظه‌ای
 */

import { TrendingUp, TrendingDown } from 'lucide-react'
import { usePrice } from '../hooks/useApi'

export default function PriceDisplay() {
  const { price, loading } = usePrice('BTCUSDT', 2000)

  return (
    <div className="price-display">
      <div className="price-header">
        <span className="price-symbol">BTC/USDT</span>
        <span className="price-live">● LIVE</span>
      </div>
      <div className="price-value">
        {loading ? (
          <span className="price-skeleton">Loading...</span>
        ) : (
          <span>${parseFloat(price).toLocaleString()}</span>
        )}
      </div>
    </div>
  )
}
