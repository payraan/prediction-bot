import React, { useState, useEffect } from 'react';
import { Search, Coins, Clock, X, CheckCircle2, AlertCircle, Wallet, ShieldCheck } from 'lucide-react';
import { getActiveMarkets, getMyPropAccount, getBalances, placeRealPrediction, placePropPrediction } from '../api/client';

export default function PropPage() {
  const [markets, setMarkets] = useState([]);
  const [filteredMarkets, setFilteredMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  
  // دیتای حساب‌ها
  const [propAccount, setPropAccount] = useState(null);
  const [realBalance, setRealBalance] = useState(0);

  // استیت‌های مدال معامله
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [tradeDirection, setTradeDirection] = useState('YES');
  const [tradeAmount, setTradeAmount] = useState('');
  const [accountMode, setAccountMode] = useState('DEMO'); // 'DEMO' (Prop) یا 'REAL'
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tradeStatus, setTradeStatus] = useState(null);
  const [debugLog, setDebugLog] = useState('Init...');;

  const categories = ['All', 'Politics', 'Crypto', 'Sports', 'Pop Culture'];

  useEffect(() => {
    setDebugLog('Requesting data...');
    Promise.all([
      getActiveMarkets()
        .then(res => {
          let mData = res;
          if (res && !Array.isArray(res)) {
            mData = res.markets || res.items || res.data || [];
          }
          return mData;
        })
        .catch(err => {
          setDebugLog(prev => prev + ` | API_ERR: ${err.message}`);
          return [];
        }),
      getMyPropAccount().catch(err => {
        return { has_account: false }; // ارور نداشتن حساب دمو را نادیده بگیر
      }),
      getBalances().catch(err => {
        return []; // ارور ولت را نادیده بگیر
      })
    ])
      .then(([marketsData, propData, balancesData]) => {
        setDebugLog(prev => prev + ` | Mkts Found: ${marketsData?.length || 0}`);
        
        setMarkets(marketsData || []);
        setFilteredMarkets(marketsData || []);
        
        if (propData && propData.has_account) {
          setPropAccount(propData.account);
          setAccountMode('DEMO');
        } else {
          setAccountMode('REAL');
        }

        const usdtAsset = (balancesData || []).find(b => b.asset === 'USDT');
        if (usdtAsset) setRealBalance(parseFloat(usdtAsset.balance));
        
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    let result = markets;
    if (selectedCategory !== 'All') {
      result = result.filter(m => m.category?.toLowerCase() === selectedCategory.toLowerCase());
    }
    if (searchQuery.trim() !== '') {
      result = result.filter(m => m.title?.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    setFilteredMarkets(result);
  }, [searchQuery, selectedCategory, markets]);

  const openTradeModal = (market, direction) => {
    setSelectedMarket(market);
    setTradeDirection(direction);
    setTradeAmount('');
    setTradeStatus(null);
  };

  const handlePlaceTrade = async () => {
    if (!tradeAmount || parseFloat(tradeAmount) <= 0) {
      alert("Please enter a valid amount.");
      return;
    }

    const currentAmount = parseFloat(tradeAmount);

    // اعتبارسنجی موجودی بر اساس مود انتخابی کاربر
    if (accountMode === 'DEMO') {
      if (!propAccount) {
        alert("You don't have an active Demo/Prop account. Please activate one on the Dashboard.");
        return;
      }
      if (currentAmount > propAccount.virtual_balance) {
        alert("Insufficient Demo/Prop balance.");
        return;
      }
    } else {
      if (currentAmount > realBalance) {
        alert("Insufficient Real Wallet balance. Please deposit USDT.");
        return;
      }
    }

    try {
      setIsSubmitting(true);
      if (accountMode === 'DEMO') {
        await placePropPrediction(selectedMarket.id, tradeDirection, currentAmount, propAccount.id);
        setPropAccount(prev => ({ ...prev, virtual_balance: prev.virtual_balance - currentAmount }));
      } else {
        await placeRealPrediction(selectedMarket.id, tradeDirection, currentAmount);
        setRealBalance(prev => prev - currentAmount);
      }
      
      setTradeStatus('success');
      setTimeout(() => setSelectedMarket(null), 1500);
    } catch (err) {
      console.error(err);
      setTradeStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-black flex justify-center items-center text-blue-500 font-bold">Loading Live Trading Desk...</div>;
  }

  return (
    <div className="min-h-screen bg-black text-gray-200 font-sans pb-24 px-4 pt-4 text-center flex flex-col items-center" dir="ltr">
      
      {/* 🔴 Debugger Banner 🔴 */}
      <div className="w-full max-w-sm mb-3 bg-red-900/30 border border-red-500/50 text-[10px] text-red-200 p-2 rounded-lg font-mono text-left break-words">
        DEBUG LOG: {debugLog}
      </div>
      
      {/* Search Bar (Perfectly Centered & Proportional) */}
      <div className="relative w-full max-w-sm mb-4">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600" size={16} />
        <input 
          type="text"
          placeholder="Search live markets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 pl-11 pr-4 text-xs text-white focus:outline-none focus:border-blue-500 text-center placeholder-zinc-600 font-medium"
        />
      </div>

      {/* Categories Horizontal Pills */}
      <div className="flex justify-center gap-1.5 overflow-x-auto no-scrollbar pb-4 w-full max-w-sm">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3.5 py-1.5 rounded-full text-[11px] font-bold transition-all ${
              selectedCategory === cat 
                ? 'bg-blue-600 text-white shadow-md' 
                : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:text-white'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Live Market Cards Stack */}
      <div className="space-y-4 w-full max-w-sm mt-1">
        {filteredMarkets.length === 0 ? (
          <div className="text-center py-10 text-zinc-600 border border-zinc-900 rounded-2xl bg-zinc-950/20 text-xs">
            No active prediction markets available.
          </div>
        ) : filteredMarkets.map(m => {
          const yesPct = Math.round((m.yes_price || 0.5) * 100);
          const noPct = Math.round((m.no_price || 0.5) * 100);

          return (
            <div key={m.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 shadow-xl flex flex-col items-center justify-center">
              
              <span className="bg-zinc-800 border border-zinc-700 text-zinc-400 text-[9px] font-bold px-2.5 py-0.5 rounded-full tracking-wider uppercase mb-3">
                {m.category || 'MARKET'}
              </span>

              <h3 className="text-sm font-bold text-white leading-relaxed mb-4 px-2 max-w-xs">
                {m.title}
              </h3>

              <div className="flex justify-center gap-4 text-[10px] text-zinc-500 font-mono mb-4 border-t border-b border-zinc-800/50 py-2 w-full">
                <div className="flex items-center gap-1"><Coins size={11} className="text-blue-500" /> Vol: <span className="text-zinc-300 font-bold">$12.4K</span></div>
                <div className="flex items-center gap-1"><Clock size={11} className="text-amber-600" /> Ends: <span className="text-zinc-300 font-bold">Live Mirror</span></div>
              </div>

              {/* YES / NO Side-by-Side Grid */}
              <div className="grid grid-cols-2 gap-3 w-full">
                <button onClick={() => openTradeModal(m, 'YES')} className="bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-xl p-3 flex flex-col items-center justify-center active:scale-95 transition-transform">
                  <span className="text-[10px] font-bold text-emerald-400 mb-0.5">Buy YES</span>
                  <span className="text-base font-mono text-white font-bold">{yesPct}%</span>
                </button>
                <button onClick={() => openTradeModal(m, 'NO')} className="bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl p-3 flex flex-col items-center justify-center active:scale-95 transition-transform">
                  <span className="text-[10px] font-bold text-rose-400 mb-0.5">Buy NO</span>
                  <span className="text-base font-mono text-white font-bold">{noPct}%</span>
                </button>
              </div>

            </div>
          );
        })}
      </div>

      {/* ====== PREMIUM INTERACTIVE TRADING DRAWER / MODAL ====== */}
      {selectedMarket && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs z-50 flex items-end justify-center animate-in fade-in duration-150">
          <div className="bg-zinc-900 border-t border-zinc-800 w-full max-w-md rounded-t-2xl p-5 shadow-2xl flex flex-col items-center animate-in slide-in-from-bottom duration-250">
            
            {/* Close Handle Header */}
            <div className="flex justify-between items-center w-full border-b border-zinc-800 pb-2.5 mb-2">
              <div className="w-6 h-6"></div>
              <h4 className="text-[10px] font-bold text-zinc-500 tracking-widest uppercase">Order Execution Desk</h4>
              <button onClick={() => setSelectedMarket(null)} className="p-1 rounded-full bg-zinc-800 text-zinc-400 hover:text-white"><X size={14} /></button>
            </div>

            {tradeStatus === 'success' ? (
              <div className="py-6 flex flex-col items-center gap-2 text-center animate-in zoom-in-75">
                <CheckCircle2 size={44} className="text-emerald-500" />
                <p className="text-sm font-bold text-white">Prediction Registered!</p>
                <p className="text-[11px] text-zinc-500">Balance updated successfully.</p>
              </div>
            ) : tradeStatus === 'error' ? (
              <div className="py-6 flex flex-col items-center gap-2 text-center animate-in zoom-in-75">
                <AlertCircle size={44} className="text-rose-500" />
                <p className="text-sm font-bold text-white">Execution Refused</p>
                <p className="text-[11px] text-zinc-500">Check server response or connection limits.</p>
                <button onClick={() => setTradeStatus(null)} className="text-xs text-blue-500 font-bold underline mt-1">Try Again</button>
              </div>
            ) : (
              <>
                {/* ACCOUNT CONTEXT DUAL SWITCHER (THE CORE REQUEST) */}
                <div className="w-full max-w-xs bg-zinc-950 p-1 rounded-xl flex border border-zinc-800 my-2">
                  <button 
                    onClick={() => setAccountMode('DEMO')}
                    className={`flex-1 py-2 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1.5 ${
                      accountMode === 'DEMO' ? 'bg-blue-600 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    <ShieldCheck size={12} />
                    Demo/Prop ({propAccount ? `$${Math.round(propAccount.virtual_balance).toLocaleString()}` : '$0'})
                  </button>
                  <button 
                    onClick={() => setAccountMode('REAL')}
                    className={`flex-1 py-2 rounded-lg text-[11px] font-bold transition-all flex items-center justify-center gap-1.5 ${
                      accountMode === 'REAL' ? 'bg-blue-600 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    <Wallet size={12} />
                    Real Wallet (${realBalance.toFixed(2)})
                  </button>
                </div>

                {/* Market Summary */}
                <p className="text-xs font-bold text-white mt-2 px-4 max-w-xs">{selectedMarket.title}</p>
                <div className="text-[11px] mt-1.5 mb-2 font-medium">
                  Outcome Specified: <span className={`font-mono font-bold px-2 py-0.5 rounded text-[10px] ${tradeDirection === 'YES' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>{tradeDirection}</span>
                </div>

                {/* Centered Amount Input Field */}
                <div className="w-full max-w-xs mt-2 relative">
                  <input 
                    type="number"
                    placeholder="Enter prediction amount"
                    value={tradeAmount}
                    onChange={(e) => setTradeAmount(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded-xl py-3 px-4 text-center font-mono font-bold text-base text-white focus:outline-none focus:border-blue-500 placeholder-zinc-700"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold font-mono text-zinc-500">USD</span>
                </div>

                {/* Quick Shortcuts */}
                <div className="flex gap-1.5 justify-center w-full max-w-xs mt-2">
                  {[10, 50, 100, 500].map(amt => (
                    <button key={amt} onClick={() => setTradeAmount(amt.toString())} className="flex-1 bg-zinc-800 border border-zinc-700/40 text-white font-mono text-[11px] font-bold py-1.5 rounded-lg active:scale-95 transition-transform">
                      +${amt}
                    </button>
                  ))}
                </div>

                {/* Submission Action Button */}
                <button
                  onClick={handlePlaceTrade}
                  disabled={isSubmitting}
                  className={`w-full max-w-xs font-bold py-3.5 rounded-xl shadow-lg text-white text-xs uppercase tracking-wider mt-4 transition-colors ${
                    tradeDirection === 'YES' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'
                  } disabled:opacity-50`}
                >
                  {isSubmitting ? "Transmitting..." : `Confirm ${tradeDirection} Order`}
                </button>
              </>
            )}

          </div>
        </div>
      )}

    </div>
  );
}
