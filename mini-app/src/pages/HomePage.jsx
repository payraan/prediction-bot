/**
 * صفحه اصلی - شرط‌بندی
 */

import { useState } from 'react'
import WebApp from '@twa-dev/sdk'
import PriceDisplay from '../components/PriceDisplay'
import RoundCard from '../components/RoundCard'
import AmountSelector from '../components/AmountSelector'
import { useActiveRound, useMe } from '../hooks/useApi'
import { placeBet } from '../api/client'

export default function HomePage({ onToast }) {
  const { user, refetch: refetchUser } = useMe()
  const { round, refetch: refetchRound } = useActiveRound(3000)
  const [selectedDirection, setSelectedDirection] = useState(null)
  const [betAmount, setBetAmount] = useState(5)
  const [loading, setLoading] = useState(false)

  const balance = user?.balance_available || 0

  const handleBet = async (direction) => {
    if (!round) {
      onToast('راند فعالی وجود ندارد', 'error')
      return
    }

    if (betAmount > balance) {
      onToast('موجودی کافی نیست!', 'error')
      return
    }

    if (betAmount < 1) {
      onToast('حداقل مبلغ شرط 1 TON است', 'error')
      return
    }

    setSelectedDirection(direction)
    setLoading(true)

    try {
      const result = await placeBet(round.id, direction, betAmount)
      
      if (result.success) {
        onToast(result.message, 'success')
        WebApp.HapticFeedback.notificationOccurred('success')
        refetchUser()
        refetchRound()
      } else {
        onToast(result.message, 'error')
        WebApp.HapticFeedback.notificationOccurred('error')
      }
    } catch (err) {
      onToast('خطا در ثبت شرط', 'error')
      WebApp.HapticFeedback.notificationOccurred('error')
    } finally {
      setLoading(false)
      setSelectedDirection(null)
    }
  }

  return (
    <div className="page home-page">
      <PriceDisplay />
      
      <RoundCard
        round={round}
        onBet={handleBet}
        selectedDirection={selectedDirection}
        betAmount={betAmount}
      />
      
      <AmountSelector
        value={betAmount}
        onChange={setBetAmount}
        balance={balance}
      />

      {loading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
        </div>
      )}
    </div>
  )
}
