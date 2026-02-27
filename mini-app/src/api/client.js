/**
 * API Client
 * ارتباط با بک‌اند با authentication تلگرام
 */

import WebApp from '@twa-dev/sdk'

// در production به Railway وصل میشه
console.log('VITE_API_BASE =', import.meta.env.VITE_API_BASE)
const API_BASE =
  import.meta.env.VITE_API_BASE || ''

// گرفتن initData از تلگرام
const getInitData = () => WebApp.initData || ''

// هدرهای عمومی
const getHeaders = () => ({
  'Content-Type': 'application/json',
  'X-Telegram-Init-Data': getInitData(),
})

// درخواست عمومی
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const headers = {
    ...getHeaders(),
    ...options.headers,
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    
    return response.json()
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error)
    throw error
  }
}

// === User ===
export const getMe = () => request('/api/user/me')
export const getBalances = () => request('/api/user/balances')

// === Round ===
export const getActiveRound = () => request('/api/round/active')
export const getRound = (id) => request(`/api/round/${id}`)

// === Price ===
export const getPrice = (symbol = 'BTCUSDT') => request(`/api/price/${symbol}`)

// === Betting ===
export const placeBet = (roundId, direction, amount) => 
  request('/api/bet/place', {
    method: 'POST',
    body: JSON.stringify({
      round_id: roundId,
      direction: direction.toUpperCase(),
      amount: parseFloat(amount),
    }),
  })

export const getBetHistory = (limit = 20) => 
  request(`/api/bet/history?limit=${limit}`)

// === Deposit ===
export const requestDeposit = (params = null) => {
  // Important: if params is null/undefined, do NOT send {amount: null}
  // Send {} so backend can apply defaults safely (or throw clean 400 if needed)
  let payload = {}

  if (params && typeof params === 'object') {
    payload = params
  } else if (params !== null && params !== undefined) {
    payload = { amount: params }
  }

  return request('/api/deposit/request', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export const getPendingDeposit = (asset, network) => {
  const params = new URLSearchParams()
  if (asset) params.set('asset', asset)
  if (network) params.set('network', network)
  const qs = params.toString()
  return request(qs ? `/api/deposit/pending?${qs}` : '/api/deposit/pending')
}

// === Withdrawal ===
export const requestWithdrawal = (amount, toAddress) =>
  request('/api/withdrawal/request', {
    method: 'POST',
    body: JSON.stringify({ amount, to_address: toAddress }),
  })

export const getWithdrawalHistory = (limit = 20) =>
  request(`/api/withdrawal/history?limit=${limit}`)

// === Leaderboard ===
export const getLeaderboardTop = (limit = 50, offset = 0) =>
  request(`/leaderboard/top?limit=${limit}&offset=${offset}`)

export const getMyStats = (telegramId) =>
  request(`/leaderboard/me?telegram_id=${telegramId}`)

export default {
  getMe,
  getBalances,
  getActiveRound,
  getRound,
  getPrice,
  placeBet,
  getBetHistory,
  requestDeposit,
  getPendingDeposit,
  requestWithdrawal,
  getWithdrawalHistory,
  getLeaderboardTop,
  getMyStats,
}
