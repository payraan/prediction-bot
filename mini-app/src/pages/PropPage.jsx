import React, { useState, useEffect, useRef } from 'react';
import { Search, ShieldCheck, Wallet, CheckCircle2, AlertCircle, TrendingUp } from 'lucide-react';
import { getActiveMarkets, getMyPropAccount, getBalances, placeRealPrediction, placePropPrediction } from '../api/client';

const CATEGORIES = ['All', 'Politics', 'Sports', 'Crypto', 'Live Up/Down', 'Tech', 'Business', 'Finance', 'Pop Culture', 'Science', 'Geopolitics', 'Weather', 'Other'];

function fmtPrice(p) {
  if (!p && p !== 0) return '—';
  return (parseFloat(p) * 100).toFixed(0) + '%';
}

function fmtVol(v) {
  if (!v) return '$0';
  const n = parseFloat(v);
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function SparklineChart({ history = [], width = 120, height = 40, color = '#4ade80' }) {
  if (!history || history.length < 2) {
    history = [50, 52, 48, 55, 60, 58, 62, 65, 63, 70];
  }
  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;
  const points = history.map((v, i) => {
    const x = (i / (history.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 6) - 3;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <polyline fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" points={points} />
    </svg>
  );
}

export default function PropPage() {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('All');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('vol');
  
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [tradeSide, setTradeSide] = useState('YES');
  const [tradeAmount, setTradeAmount] = useState('');
  const [accountMode, setAccountMode] = useState('DEMO');
  const [propAccount, setPropAccount] = useState(null);
  const [realBalance, setRealBalance] = useState(0);

  useEffect(() => {
    Promise.all([
      getActiveMarkets().catch(() => []),
      getMyPropAccount().catch(() => ({ has_account: false })),
      getBalances().catch(() => [])
    ]).then(([marketsData, propData, balancesData]) => {
      const finalMarkets = Array.isArray(marketsData) ? marketsData : (marketsData?.markets || []);
      setMarkets(finalMarkets);
      if (propData?.has_account) setPropAccount(propData.account);
      const usdt = (balancesData || []).find(b => b.asset === 'USDT');
      if (usdt) setRealBalance(parseFloat(usdt.balance));
      setLoading(false);
    });
  }, []);

  const filtered = markets.filter(m => {
    if (category === 'All') return true;
    const mCat = String(m.category || 'Other');
    const mTitle = String(m.title || '').toLowerCase();
    
    if (category === 'Live Up/Down') return mTitle.includes('hit') || mTitle.includes('price') || mTitle.includes('above');
    return mCat === category;
  }).filter(m => !query || m.title.toLowerCase().includes(query.toLowerCase()));

  const topMarket = markets[0];

  return (
    <div style={{ background: '#09090f', minHeight: '100vh', color: '#e0e0e0', paddingBottom: 120 }}>
      
      {/* 📈 Top Featured Market Chart (Like Competitor UI) 📈 */}
      {topMarket && category === 'All' && (
        <div style={{ background: '#0d0d14', padding: 20, borderBottom: '1px solid #1e1e2e', position: 'relative' }}>
          <span style={{ fontSize: 11, color: '#4f8ef7', fontWeight: 700, textTransform: 'uppercase' }}>{topMarket.category}</span>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginTop: 4, marginBottom: 16 }}>{topMarket.title}</h2>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '20px 0' }}>
            <div>
              <div style={{ fontSize: 12, color: '#555' }}>Yes Price</div>
              <div style={{ fontSize: 32, fontWeight: 800, color: '#4ade80' }}>{fmtPrice(topMarket.yes_price)}</div>
            </div>
            <SparklineChart width={200} height={60} color="#4ade80" />
          </div>
        </div>
      )}

      {/* Categories Menu */}
      <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid #1e1e2e', padding: '4px 8px' }}>
        {CATEGORIES.map(cat => (
          <button key={cat} onClick={() => setCategory(cat)} style={{ flexShrink: 0, padding: '12px 14px', background: 'none', border: 'none', borderBottom: category === cat ? '2px solid #4f8ef7' : '2px solid transparent', color: category === cat ? '#fff' : '#555', fontSize: 13, fontWeight: 600 }}>
            {cat}
          </button>
        ))}
      </div>

      {/* Search Header */}
      <div style={{ padding: 12, display: 'flex', gap: 8 }}>
        <input type="text" placeholder="Search live trading desks..." value={query} onChange={e => setQuery(e.target.value)} style={{ flex: 1, background: '#161622', border: '1px solid #2a2a3e', borderRadius: 20, padding: '8px 14px', color: '#fff', outline: 'none', fontSize: 13 }} />
      </div>

      {/* Markets List */}
      <div style={{ padding: '0 12px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#666' }}>Loading Orderbook Data...</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#666' }}>No active pools available in this tab.</div>
        ) : (
          filtered.map(m => (
            <div key={m.id} style={{ background: '#0f0f1a', border: '1px solid #1e1e2e', borderRadius: 12, padding: 16, marginBottom: 12, position: 'relative' }} onClick={() => { setSelectedMarket(m); setTradeAmount(''); }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 10, color: '#6b7280', fontWeight: 700 }}>{m.category}</span>
                <SparklineChart width={60} height={20} color={parseFloat(m.yes_price) >= 0.5 ? '#4ade80' : '#f87171'} />
              </div>
              <h4 style={{ fontSize: 14, fontWeight: 600, color: '#ddd', marginBottom: 12 }}>{m.title}</h4>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#fff' }}>{fmtPrice(m.yes_price)} <span style={{ fontSize: 11, color: '#555' }}>YES</span></span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button style={{ background: 'rgba(74,222,128,0.1)', border: '1px solid #4ade80', color: '#4ade80', padding: '6px 16px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>Buy</button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Trading Drawer Logic */}
      {selectedMarket && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }} onClick={() => setSelectedMarket(null)}>
          <div style={{ background: '#0f0f1a', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20 }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>{selectedMarket.title}</h3>
            
            <div style={{ display: 'flex', background: '#000', padding: 4, borderRadius: 10, marginBottom: 16 }}>
              <button onClick={() => setAccountMode('DEMO')} style={{ flex: 1, py: 8, background: accountMode === 'DEMO' ? '#2563eb' : 'none', border: 'none', color: '#fff', borderRadius: 6, fontSize: 12, fontWeight: 700, padding: '8px 0' }}>Demo Account</button>
              <button onClick={() => setAccountMode('REAL')} style={{ flex: 1, py: 8, background: accountMode === 'REAL' ? '#2563eb' : 'none', border: 'none', color: '#fff', borderRadius: 6, fontSize: 12, fontWeight: 700, padding: '8px 0' }}>Real Wallet</button>
            </div>

            <button onClick={() => setSelectedMarket(null)} style={{ width: '100%', padding: 14, background: '#1e1e2e', border: 'none', color: '#fff', borderRadius: 10, fontWeight: 700 }}>Close Drawer</button>
          </div>
        </div>
      )}
    </div>
  );
}
