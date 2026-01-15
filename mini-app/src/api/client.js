/**
 * API Client
 * ارتباط با بک‌اند با authentication تلگرام
 */

import WebApp from '@twa-dev/sdk'

const API_BASE = import.meta.env.VITE_API_URL || ''

// گرفتن initData از تلگرام
const getInitData = () => WebApp.initData || ''

// درخواست عمومی
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const headers = {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': getInitData(),
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
export const requestDeposit = (amount = null) =>
  request('/api/deposit/request', {
    method: 'POST',
    body: JSON.stringify({ amount }),
  })

export const getPendingDeposit = () => request('/api/deposit/pending')

export default {
  getMe,
  getActiveRound,
  getRound,
  getPrice,
  placeBet,
  getBetHistory,
  requestDeposit,
  getPendingDeposit,
}
