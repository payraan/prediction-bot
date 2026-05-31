// معماری شبکه پیشنهاد شده توسط Claude 3.5
const API_BASE = (() => {
  const base = import.meta.env.VITE_API_BASE;
  if (!base) {
    console.warn('[API] VITE_API_BASE not set! Using fallback.');
    return 'https://web-production-7d823.up.railway.app'; // آدرس بک‌اند شما
  }
  return base.replace(/\/$/, '');
})();

// Cache-busting برای دور زدن کش WebView تلگرام
const addCacheBuster = (url) => {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}_t=${Date.now()}`;
};

async function request(endpoint, options = {}) {
  const url = addCacheBuster(`${API_BASE}${endpoint}`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const err = new Error(error.detail || `HTTP ${response.status}`);
      err.status = response.status;
      throw err;
    }

    return response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') throw new Error('Request timed out after 15s');
    throw err;
  }
}

// === Live Prediction & Prop Markets ===
export const getActiveMarkets = () => request('/api/markets/active');
export const getMyPropAccount = () => request('/api/prop/me');
export const getBalances = () => request('/api/wallet/balances');

export const placeRealPrediction = (marketId, direction, amount) => 
  request(`/api/markets/${marketId}/predict`, {
    method: 'POST',
    body: JSON.stringify({ direction, amount: parseFloat(amount) })
  });

export const placePropPrediction = (marketId, direction, amount, propAccountId) => 
  request('/api/prop/predict', {
    method: 'POST',
    body: JSON.stringify({ 
      prop_account_id: propAccountId,
      market_id: marketId, 
      direction, 
      amount: parseFloat(amount) 
    })
  });

export const buyPropChallenge = (accountSize) => 
  request('/api/prop/buy', {
    method: 'POST',
    body: JSON.stringify({ account_size: parseFloat(accountSize) })
});

export const requestDemoAccount = () => request('/api/prop/demo', { method: 'POST' });

// === Restored Core & Wallet Endpoints ===
export const getMe = () => request('/api/auth/me');
export const getActiveRound = () => request('/api/rounds/active');
export const getPrice = () => request('/api/price');
export const getBetHistory = () => request('/api/predictions/history');
export const getPendingDeposit = (asset, network) => request(`/api/wallet/deposit/pending?asset=${asset}&network=${network}`);
export const requestDeposit = (asset, network) => request('/api/wallet/deposit', { method: 'POST', body: JSON.stringify({ asset, network }) });
export const requestWithdrawal = (to_address, amount, asset, network) => request('/api/wallet/withdraw', { method: 'POST', body: JSON.stringify({ to_address, amount, asset, network }) });

// === Leaderboard Endpoints ===
export const getLeaderboardTop = () => request('/api/leaderboard/top');
export const getMyStats = () => request('/api/leaderboard/me');
