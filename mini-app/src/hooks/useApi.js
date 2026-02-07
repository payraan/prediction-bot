/**
 * Custom Hooks برای API
 */

import { useState, useEffect, useCallback } from 'react'
import * as api from '../api/client'

// === useMe: اطلاعات کاربر ===
export function useMe() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getMe()
      setUser(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { user, loading, error, refetch: fetch }
}

// === useBalances: موجودی‌های چنددارایی ===
export function useBalances() {
  const [balances, setBalances] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getBalances()
      setBalances(Array.isArray(data) ? data : [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { balances, loading, error, refetch: fetch }
}


// === useActiveRound: راند فعال ===
export function useActiveRound(pollInterval = 3000) {
  const [round, setRound] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    try {
      const data = await api.getActiveRound()
      setRound(data)
      setError(null)
    } catch (err) {
      setError(err.message)
      setRound(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, pollInterval)
    return () => clearInterval(interval)
  }, [fetch, pollInterval])

  return { round, loading, error, refetch: fetch }
}

// === usePrice: قیمت لحظه‌ای ===
export function usePrice(symbol = 'BTCUSDT', pollInterval = 2000) {
  const [price, setPrice] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.getPrice(symbol)
        setPrice(data.price)
      } catch (err) {
        console.error('Price fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetch()
    const interval = setInterval(fetch, pollInterval)
    return () => clearInterval(interval)
  }, [symbol, pollInterval])

  return { price, loading }
}

// === useCountdown: شمارش معکوس با seconds_remaining از سرور ===
export function useCountdown(secondsFromServer) {
  const [seconds, setSeconds] = useState(secondsFromServer || 0)

  useEffect(() => {
    // وقتی مقدار جدید از سرور میاد، آپدیت کن
    if (secondsFromServer !== undefined && secondsFromServer !== null) {
      setSeconds(secondsFromServer)
    }
  }, [secondsFromServer])

  useEffect(() => {
    if (seconds <= 0) return

    const interval = setInterval(() => {
      setSeconds(prev => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [seconds > 0]) // فقط وقتی seconds > 0 هست interval بساز

  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60

  return {
    seconds,
    minutes,
    formatted: `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`,
    isExpired: seconds === 0,
  }
}

// === useBetHistory: تاریخچه شرط‌ها ===
export function useBetHistory(limit = 20) {
  const [bets, setBets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getBetHistory(limit)
      setBets(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { bets, loading, error, refetch: fetch }
}

// === useDeposit: واریز ===
export function useDeposit() {
  const [deposit, setDeposit] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const checkPending = useCallback(async () => {
    try {
      const data = await api.getPendingDeposit()
      setDeposit(data)
    } catch (err) {
      console.error('Check pending error:', err)
    }
  }, [])

  const createRequest = useCallback(async (params = null) => {
    try {
      setLoading(true)
      const data = await api.requestDeposit(params)
      setDeposit(data)
      setError(null)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    checkPending()
  }, [checkPending])

  return { deposit, loading, error, createRequest, checkPending }
}
