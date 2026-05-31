import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, ShieldCheck, Wallet, CheckCircle2, AlertCircle } from 'lucide-react';
import { getActiveMarkets, getMyPropAccount, getBalances, placeRealPrediction, placePropPrediction } from '../api/client';

// ── Categories & Options ──────────────────────────────────────────────────
const CATEGORIES = ['All', 'Politics', 'Sports', 'Crypto', 'Live Up/Down', 'Tech', 'Business', 'Finance', 'Pop Culture', 'Science', 'Geopolitics', 'Weather', 'Global Elections', 'World', 'Earn 4%', 'US Election', 'World Elections', 'United States', 'Iran', 'Other'];

const SORT_OPTIONS = [
  { key: 'vol', label: 'Vol' },
  { key: 'prob', label: 'Prob' },
  { key: 'move7d', label: 'Move 7d' },
];

// ── Formatting Helpers ────────────────────────────────────────────────────
function fmtPrice(p) {
  if (!p && p !== 0) return '—';
  const n = parseFloat(p);
  return isNaN(n) ? '—' : (n * 100).toFixed(0) + '%';
}

function fmtVol(v) {
  if (!v && v !== 0) return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtDate(d) {
  if (!d) return '';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Components ─────────────────────────────────────────────────────────────

// ── Market Chart (Sparkline) ──────────────────────────────────────────────
function MarketChart({ history = [], color }) {
  // Generate pseudo-random mock history if none exists (for visual effect)
  if (!history || history.length === 0) {
    history = Array.from({ length: 20 }, (_, i) => 30 + Math.random() * 40);
  }
  const min = Math.min(...history);
  const max = Math.max(...history);
  const range = max - min || 1;
  const points = history.map((val, i) => {
    const x = (i / (history.length - 1)) * 100;
    const y = 100 - ((val - min) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div style={{ height: 40, width: '100%', opacity: 0.25, marginTop: -15, marginBottom: 10, pointerEvents: 'none' }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
        <polyline fill="none" stroke={color} strokeWidth="3" points={points} vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}

function TickerStrip({ markets }) {
  if (!markets || markets.length === 0) return null;
  const items = markets.slice(0, 10);
  return (
    <div style={{ background: '#0d0d14', borderBottom: '1px solid #1e1e2e', overflow: 'hidden', height: 36, display: 'flex', alignItems: 'center' }}>
      <div style={{ display: 'flex', gap: 0, animation: 'tickerScroll 30s linear infinite', whiteSpace: 'nowrap' }}>
        {[...items, ...items].map((m, i) => (
          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0 20px', fontSize: 12, borderRight: '1px solid #1e1e2e' }}>
             <span style={{ color: '#888', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {m.title.length > 25 ? m.title.slice(0, 25) + '…' : m.title}
            </span>
            <span style={{ color: '#e0e0e0', fontWeight: 600 }}>{fmtPrice(m.yes_price)}</span>
          </span>
        ))}
      </div>
      <style>{`@keyframes tickerScroll { 0% { transform: translateX(0) } 100% { transform: translateX(-50%) } }`}</style>
    </div>
  );
}

function CategoryTabs({ active, onChange }) {
  const ref = useRef(null);
  useEffect(() => {
    const idx = CATEGORIES.indexOf(active);
    if (ref.current) {
      const btns = ref.current.querySelectorAll('button');
      if (btns[idx]) btns[idx].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }, [active]);

  return (
    <div ref={ref} style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid #1e1e2e', scrollbarWidth: 'none', msOverflowStyle: 'none', padding: '0 8px' }}>
      <style>{`::-webkit-scrollbar { display: none }`}</style>
      {CATEGORIES.map(cat => (
        <button key={cat} onClick={() => onChange(cat)} style={{ flexShrink: 0, padding: '12px 14px', background: 'none', border: 'none', borderBottom: active === cat ? '2px solid #4f8ef7' : '2px solid transparent', color: active === cat ? '#fff' : '#666', fontSize: 13, fontWeight: active === cat ? 600 : 400, cursor: 'pointer', whiteSpace: 'nowrap', transition: 'color 0.15s', marginBottom: -1 }}>
          {cat}
        </button>
      ))}
    </div>
  );
}

function SearchBar({ query, onQuery, sort, onSort }) {
  return (
    <div style={{ padding: '12px', display: 'flex', gap: 8, alignItems: 'center' }}>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, background: '#161622', border: '1px solid #2a2a3e', borderRadius: 20, padding: '8px 14px' }}>
        <Search size={14} className="text-zinc-500" />
        <input type="text" placeholder="Search markets..." value={query} onChange={e => onQuery(e.target.value)} style={{ background: 'none', border: 'none', outline: 'none', color: '#ccc', fontSize: 13, width: '100%' }} />
      </div>
      <div style={{ display: 'flex', gap: 4 }}>
        {SORT_OPTIONS.map(s => (
          <button key={s.key} onClick={() => onSort(s.key)} style={{ padding: '6px 12px', borderRadius: 16, border: sort === s.key ? '1px solid #4f8ef7' : '1px solid #2a2a3e', background: sort === s.key ? 'rgba(79,142,247,0.15)' : '#161622', color: sort === s.key ? '#4f8ef7' : '#666', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function MarketCard({ market, onTrade }) {
  const yesPct = Math.round((parseFloat(market.yes_price) || 0.5) * 100);
  const totalVol = (market.total_pool_yes || 0) + (market.total_pool_no || 0);
  
  return (
    <div style={{ background: '#0f0f1a', border: '1px solid #1e1e2e', borderRadius: 12, padding: 16, marginBottom: 12, cursor: 'pointer' }} onClick={() => onTrade(market)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
         <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{market.category || 'MARKET'}</span>
              <span style={{ color: '#333' }}>·</span>
              <span style={{ fontSize: 11, color: '#555' }}>Ends {fmtDate(market.closes_at)}</span>
            </div>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e0e0e0', lineHeight: 1.35, margin: 0 }}>{market.title}</h3>
         </div>
      </div>

      <MarketChart color={yesPct >= 50 ? '#4ade80' : '#f87171'} />
      <div style={{ marginBottom: 12 }}>
        <div style={{ width: '100%', height: 4, background: '#1e1e2e', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${yesPct}%`, height: '100%', background: yesPct >= 50 ? '#4ade80' : '#f87171', borderRadius: 2 }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
            {yesPct}% <span style={{ fontSize: 12, fontWeight: 400, color: '#666', marginLeft: 2 }}>YES</span>
          </span>
          <span style={{ fontSize: 12, color: '#555' }}>Vol {fmtVol(totalVol)}</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={e => { e.stopPropagation(); onTrade(market, 'YES') }} style={{ flex: 1, padding: '10px 0', background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', borderRadius: 8, color: '#4ade80', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>Buy Yes</button>
        <button onClick={e => { e.stopPropagation(); onTrade(market, 'NO') }} style={{ flex: 1, padding: '10px 0', background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8, color: '#f87171', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>Buy No</button>
      </div>
    </div>
  );
}

// ── Main Page Component ───────────────────────────────────────────────────

export default function PropPage() {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('All');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('vol');
  const [debugLog, setDebugLog] = useState('');

  // ── Trade Drawer State ──
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [tradeSide, setTradeSide] = useState('YES');
  const [tradeAmount, setTradeAmount] = useState('');
  const [accountMode, setAccountMode] = useState('DEMO'); // 'DEMO' or 'REAL'
  const [propAccount, setPropAccount] = useState(null);
  const [realBalance, setRealBalance] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tradeStatus, setTradeStatus] = useState(null);

  useEffect(() => {
    Promise.all([
      getActiveMarkets().catch(e => []),
      getMyPropAccount().catch(e => ({ has_account: false })),
      getBalances().catch(e => [])
    ]).then(([marketsData, propData, balancesData]) => {
      let finalMarkets = Array.isArray(marketsData) ? marketsData : (marketsData?.markets || []);
      setMarkets(finalMarkets);
      setDebugLog(`Loaded ${finalMarkets.length} markets`);

      if (propData && propData.has_account) {
        setPropAccount(propData.account);
      } else {
        setAccountMode('REAL');
      }

      const usdtAsset = (balancesData || []).find(b => b.asset === 'USDT');
      if (usdtAsset) setRealBalance(parseFloat(usdtAsset.balance));
      
      setLoading(false);
    });
  }, []);

  const handlePlaceTrade = async () => {
    if (!tradeAmount || parseFloat(tradeAmount) <= 0) { alert("Invalid amount."); return; }
    const amt = parseFloat(tradeAmount);

    if (accountMode === 'DEMO') {
      if (!propAccount) { alert("No active Demo/Prop account."); return; }
      if (amt > propAccount.virtual_balance) { alert("Insufficient Demo balance."); return; }
    } else {
      if (amt > realBalance) { alert("Insufficient Real Wallet balance."); return; }
    }

    try {
      setIsSubmitting(true);
      if (accountMode === 'DEMO') {
        await placePropPrediction(selectedMarket.id, tradeSide, amt, propAccount.id);
        setPropAccount(prev => ({ ...prev, virtual_balance: prev.virtual_balance - amt }));
      } else {
        await placeRealPrediction(selectedMarket.id, tradeSide, amt);
        setRealBalance(prev => prev - amt);
      }
      setTradeStatus('success');
      setTimeout(() => setSelectedMarket(null), 1500);
    } catch (err) {
      setTradeStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filtered = markets
    .filter(m => {
      if (category === 'All') return true;
      const mCat = String(m.category || '').toLowerCase().trim();
      const mTitle = String(m.title || '').toLowerCase().trim();
      const target = category.toLowerCase().trim();

      // ۱. ابتدا فیلترهای هوشمند رقیب برای تب‌های خاص
      if (target === 'us election') return (mCat.includes('politics') || mCat === '') && (mTitle.includes('us') || mTitle.includes('president') || mTitle.includes('trump') || mTitle.includes('biden') || mTitle.includes('harris'));
      if (target === 'world elections') return (mCat.includes('politics') || mCat === '') && !mTitle.includes('us ') && (mTitle.includes('election') || mTitle.includes('minister') || mTitle.includes('president'));
      if (target === 'iran') return mTitle.includes('iran') || mTitle.includes('irgc') || mCat.includes('iran');
      if (target === 'live up/down') return mTitle.includes('hit') || mTitle.includes('price') || mTitle.includes('above');
      if (target === 'earn 4%') return mTitle.includes('rate') || mTitle.includes('fed');
      if (target === 'global elections') return mTitle.includes('election') || mTitle.includes('vote');
      if (target === 'united states') return mTitle.includes('us ') || mTitle.includes('u.s.') || mTitle.includes('america');
      if (target === 'world') return !mTitle.includes('us ') && !mTitle.includes('u.s.') && (mCat.includes('politics') || mCat.includes('geopolitics'));

      // ۲. فیلتر دقیق دسته‌بندی‌های استاندارد (جلوگیری از باگ رشته خالی)
      if (mCat !== '') {
        return mCat === target || mCat.includes(target) || target.includes(mCat);
      }

      // ۳. اگر دسته بندی کلا خالی بود، فقط بر اساس کلمات کلیدی تیتر حدس بزند
      if (target === 'politics') return mTitle.includes('pardon') || mTitle.includes('resign') || mTitle.includes('out by') || mTitle.includes('president') || mTitle.includes('election');
      if (target === 'geopolitics') return mTitle.includes('invades') || mTitle.includes('capture') || mTitle.includes('clash') || mTitle.includes('troops') || mTitle.includes('war');
      if (target === 'sports') return mTitle.includes('cup') || mTitle.includes('champion') || mTitle.includes('nba') || mTitle.includes('ufc') || mTitle.includes('league');
      if (target === 'crypto') return mTitle.includes('bitcoin') || mTitle.includes('solana') || mTitle.includes('ethereum') || mTitle.includes('airdrop') || mTitle.includes('btc');
      if (target === 'tech') return mTitle.includes('openai') || mTitle.includes('gpt') || mTitle.includes('spacex') || mTitle.includes('ai ');

      return false;
    })
    .filter(m => !query || m.title.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => {
      if (sort === 'vol') return ((b.total_pool_yes || 0) + (b.total_pool_no || 0)) - ((a.total_pool_yes || 0) + (a.total_pool_no || 0));
      if (sort === 'prob') return (parseFloat(b.yes_price) || 0) - (parseFloat(a.yes_price) || 0);
      return 0;
    });

  return (
    <div style={{ background: '#09090f', minHeight: '100vh', color: '#e0e0e0', fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif', paddingBottom: 120 }} dir="ltr">
      <TickerStrip markets={markets} />
      <CategoryTabs active={category} onChange={setCategory} />
      <SearchBar query={query} onQuery={setQuery} sort={sort} onSort={setSort} />

      <div style={{ padding: '4px 12px 0' }}>
        {loading && <div style={{ textAlign: 'center', padding: '40px 0', color: '#666', fontSize: 14 }}>Loading Trading Desk...</div>}
        {!loading && filtered.length === 0 && <div style={{ textAlign: 'center', padding: '40px 0', color: '#666', fontSize: 14 }}>No markets found.</div>}
        {!loading && filtered.map(m => <MarketCard key={m.id} market={m} onTrade={(m, s) => { setSelectedMarket(m); setTradeSide(s || 'YES'); setTradeStatus(null); setTradeAmount(''); }} />)}
      </div>

      {/* ── Trading Drawer Modal ── */}
      {selectedMarket && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }} onClick={() => setSelectedMarket(null)}>
          <div style={{ background: '#0f0f1a', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: '20px 16px', maxHeight: '90vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ width: 36, height: 4, background: '#2a2a3e', borderRadius: 2, margin: '0 auto 16px' }} />
            
            {tradeStatus === 'success' ? (
              <div className="py-6 flex flex-col items-center text-center">
                <CheckCircle2 size={44} className="text-emerald-500 mb-2" />
                <p className="font-bold text-white">Prediction Placed!</p>
              </div>
            ) : tradeStatus === 'error' ? (
               <div className="py-6 flex flex-col items-center text-center">
                <AlertCircle size={44} className="text-rose-500 mb-2" />
                <p className="font-bold text-white">Execution Failed</p>
                <button onClick={() => setTradeStatus(null)} className="text-blue-500 text-sm mt-2">Try Again</button>
              </div>
            ) : (
              <>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#e0e0e0', marginBottom: 12, lineHeight: 1.35 }}>{selectedMarket.title}</h3>
                
                {/* Dual Account Switcher */}
                <div className="w-full bg-zinc-950 p-1 rounded-xl flex border border-zinc-800 my-4">
                  <button onClick={() => setAccountMode('DEMO')} className={`flex-1 py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${accountMode === 'DEMO' ? 'bg-blue-600 text-white shadow-md' : 'text-zinc-500'}`}>
                    <ShieldCheck size={14} /> Demo (${propAccount ? Math.round(propAccount.virtual_balance).toLocaleString() : '0'})
                  </button>
                  <button onClick={() => setAccountMode('REAL')} className={`flex-1 py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${accountMode === 'REAL' ? 'bg-blue-600 text-white shadow-md' : 'text-zinc-500'}`}>
                    <Wallet size={14} /> Real (${realBalance.toFixed(2)})
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
                  <button onClick={() => setTradeSide('YES')} style={{ padding: '14px 0', borderRadius: 10, border: 'none', background: tradeSide === 'YES' ? '#4f8ef7' : '#161622', color: tradeSide === 'YES' ? '#fff' : '#555', fontWeight: 700, fontSize: 16, cursor: 'pointer' }}>Yes {fmtPrice(selectedMarket.yes_price)}</button>
                  <button onClick={() => setTradeSide('NO')} style={{ padding: '14px 0', borderRadius: 10, border: 'none', background: tradeSide === 'NO' ? '#1e1e2e' : '#161622', color: tradeSide === 'NO' ? '#ccc' : '#555', fontWeight: 700, fontSize: 16, cursor: 'pointer' }}>No {fmtPrice(selectedMarket.no_price)}</button>
                </div>

                <div style={{ background: '#161622', border: '1px solid #2a2a3e', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: '#555' }}>Amount ($)</span>
                    <span style={{ padding: '2px 8px', background: '#4f8ef722', borderRadius: 4, color: '#4f8ef7', fontSize: 11, fontWeight: 700 }}>USD</span>
                  </div>
                  <input type="number" placeholder="0" value={tradeAmount} onChange={e => setTradeAmount(e.target.value)} style={{ width: '100%', background: 'none', border: 'none', outline: 'none', fontSize: 24, fontWeight: 700, color: '#fff', fontFamily: 'monospace' }} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 16 }}>
                  {[10, 50, 100, 500].map(q => (
                    <button key={q} onClick={() => setTradeAmount(String(q))} style={{ padding: '9px 0', background: tradeAmount == q ? '#4f8ef722' : '#161622', border: tradeAmount == q ? '1px solid #4f8ef755' : '1px solid #2a2a3e', borderRadius: 8, color: tradeAmount == q ? '#4f8ef7' : '#666', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>+${q}</button>
                  ))}
                </div>

                <button onClick={handlePlaceTrade} disabled={isSubmitting || !tradeAmount} style={{ width: '100%', padding: '16px 0', borderRadius: 12, border: 'none', background: !tradeAmount ? '#1e1e2e' : tradeSide === 'YES' ? '#4f8ef7' : '#f87171', color: !tradeAmount ? '#555' : '#fff', fontSize: 16, fontWeight: 800, cursor: !tradeAmount ? 'not-allowed' : 'pointer' }}>
                  {isSubmitting ? 'Processing...' : `Buy ${tradeSide}`}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
