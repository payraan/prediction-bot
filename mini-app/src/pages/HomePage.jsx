import React, { useState, useEffect } from 'react';
import { getMyPropAccount, buyPropChallenge, requestDemoAccount } from '../api/client';
import { Activity, Clock, Target } from 'lucide-react';

export default function HomePage() {
        const [activeTab, setActiveTab] = useState('positions');
  const [loading, setLoading] = useState(true);
  const [propData, setPropData] = useState(null);
  const [isBuying, setIsBuying] = useState(false);

  const plans = [
    { size: 100000, price: 200 },
    { size: 50000, price: 150 },
    { size: 20000, price: 80 },
    { size: 10000, price: 40 },
    { size: 5000, price: 20 },
    { size: 1000, price: 10 },
  ];

  const handleBuyChallenge = async (size, price) => {
    if (!window.confirm(`آیا از پرداخت $${price} برای چالش $${size.toLocaleString()} مطمئن هستید؟ (مبلغ از کیف پول شما کسر خواهد شد)`)) return;
    try {
      setIsBuying(true);
      await buyPropChallenge(size);
      const data = await getMyPropAccount();
      setPropData(data);
    } catch (error) {
      console.error(error);
      alert(error.message || "خطا در خرید چالش. لطفاً ابتدا کیف پول خود را شارژ کنید.");
    } finally {
      setIsBuying(false);
    }
  };

  const handleDemo = async () => {
    try {
      setIsBuying(true);
      await requestDemoAccount();
      const data = await getMyPropAccount();
      setPropData(data);
    } catch (error) {
      console.error(error);
      alert(error.message || "خطا در ساخت حساب دمو.");
    } finally {
      setIsBuying(false);
    }
  };

  useEffect(() => {
    getMyPropAccount()
      .then(data => {
        setPropData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load prop account:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="min-h-screen bg-black flex justify-center items-center text-blue-500">Loading your trading desk...</div>;
  }

  // اگر حساب نداشت
    if (!propData || !propData.has_account) {
    return (
      <div className="min-h-screen bg-black text-gray-200 font-sans pb-24 px-4 pt-6" dir="ltr">
        <div className="text-center mb-6">
           <h1 className="text-2xl font-bold text-white mb-2">Choose Your Challenge</h1>
           <p className="text-gray-500 text-xs">Select an evaluation plan or start with a free demo.</p>
        </div>

        {/* Free Demo Card */}
        <div className="bg-gray-900 border border-blue-500/30 rounded-2xl p-5 mb-6 shadow-[0_0_20px_rgba(59,130,246,0.1)] relative overflow-hidden">
           <div className="absolute -right-10 -top-10 w-32 h-32 bg-blue-600 opacity-20 blur-[40px] rounded-full pointer-events-none"></div>
           <div className="flex justify-between items-center mb-2">
             <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-[10px] font-bold tracking-widest uppercase">Free Sandbox</span>
             <span className="text-2xl font-bold text-white font-mono">$50,000</span>
           </div>
           <p className="text-[11px] text-gray-400 mb-4 pr-10">Practice your strategies with virtual funds and experience the trading dashboard before purchasing a real challenge.</p>
           <button onClick={handleDemo} disabled={isBuying} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-blue-900/40 text-sm disabled:opacity-50">
             {isBuying ? "Processing..." : "Start Free Demo"}
           </button>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <div className="h-[1px] bg-gray-800 flex-1"></div>
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Evaluation Plans</span>
          <div className="h-[1px] bg-gray-800 flex-1"></div>
        </div>
        
        {/* Pricing Grid */}
        <div className="grid grid-cols-2 gap-3">
           {plans.map(p => (
             <div key={p.size} className="bg-[#0b0e14] border border-gray-800 rounded-xl p-4 flex flex-col justify-between hover:border-blue-500/50 transition relative group">
                <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition rounded-xl pointer-events-none"></div>
                <div>
                   <div className="text-lg font-mono font-bold text-white leading-none mb-1">${p.size.toLocaleString()}</div>
                   <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-4">Account Size</div>
                </div>
                
                <button onClick={() => handleBuyChallenge(p.size, p.price)} disabled={isBuying} className="w-full bg-transparent border border-gray-700 group-hover:border-blue-500/50 hover:bg-gray-800 text-white font-bold py-2 rounded-lg text-[11px] transition disabled:opacity-50">
                   Buy for ${p.price}
                </button>
             </div>
           ))}
        </div>
      </div>
    );
  }

  const acc = propData.account;
  const usedDrawdown = acc.peak_balance - acc.virtual_balance;
  const drawdownLimit = acc.starting_balance * (acc.max_total_drawdown_pct / 100);
  const drawdownPct = Math.min(100, (usedDrawdown / drawdownLimit) * 100);
  
  const dailyLossLimit = acc.starting_balance * (acc.max_daily_drawdown_pct / 100);
  const dailyLossPct = Math.min(100, (usedDrawdown / dailyLossLimit) * 100); // ساده شده برای دمو

  const winRate = acc.total_predictions > 0 ? Math.round((acc.winning_predictions / acc.total_predictions) * 100) : 0;


  return (
    <div className="min-h-screen bg-black text-gray-200 font-sans pb-24 px-4 pt-4" dir="ltr">

      {/* Beta Alert Box */}
      <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-2xl p-5 mb-5 text-center w-full shadow-lg">
         <div className="text-yellow-500 font-bold text-sm mb-2 flex justify-center items-center gap-2">
            <span className="text-xl">🚀</span> Beta account controls
         </div>
         <p className="text-xs text-yellow-600/80 mb-4 px-2 leading-relaxed">
           Open a ticket in Discord to reset your beta account, or complete tasks on the waitlist for an automated reset.
         </p>
         <div className="flex justify-center gap-3 w-full">
           <button className="flex-1 border border-yellow-700/50 text-gray-300 text-xs font-bold py-3 rounded-xl hover:bg-gray-800 transition">
             Reset via Discord
           </button>
           <button className="flex-1 bg-blue-600 text-white text-xs font-bold py-3 rounded-xl hover:bg-blue-500 transition shadow-lg shadow-blue-900/20">
             Earn a reset →
           </button>
         </div>
      </div>

      {/* Main Title Section */}
      <div className="text-center w-full mb-6">
         <div className="text-blue-500 text-[10px] font-bold tracking-widest uppercase mb-2">
           PHASE 1 · EVALUATION
         </div>
         <h1 className="text-3xl text-white font-bold mb-2 flex justify-center items-center gap-2">
           Beta Challenge 
           <span className="bg-blue-900/50 border border-blue-800 text-blue-400 text-[10px] px-2 py-0.5 rounded-md">BETA</span>
         </h1>
         <p className="text-xs text-gray-500 flex justify-center gap-2">
           <span>{acc.id.substring(0,8).toUpperCase()}</span><span>|</span><span>$100,000.00</span><span>|</span><span>No profit target</span>
         </p>
         <button className="w-full max-w-xs mx-auto bg-blue-600 text-white text-sm font-bold py-3.5 rounded-xl mt-5 flex justify-center items-center gap-2 shadow-lg shadow-blue-900/30 hover:bg-blue-500 transition">
           Trade now →
         </button>
      </div>

      {/* 1. EQUITY BOX */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full text-center shadow-xl mb-4">
         <div className="text-gray-400 text-xs tracking-widest uppercase mb-2 font-bold">EQUITY</div>
         <div className="text-4xl text-white font-light font-mono mb-3 tracking-tight">${acc.virtual_balance.toLocaleString()}</div>
         <div className="text-green-400 text-sm font-mono flex justify-center items-center gap-2 font-bold">
           <span className="bg-green-500/10 border border-green-500/20 px-2 py-1 rounded">${(acc.virtual_balance - acc.starting_balance).toLocaleString()}</span>
           <span className="text-gray-500 font-normal">${acc.max_total_drawdown_pct}% Total DD Limit</span>
         </div>
      </div>

      {/* 2. CONSTRAINTS BOXES */}
      <div className="space-y-4 mb-4">
         {/* Max Drawdown */}
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full text-center shadow-xl">
            <div className="text-gray-400 text-xs tracking-widest uppercase mb-3 font-bold">Max Drawdown</div>
            <div className="text-lg text-white font-mono mb-1 font-bold">
              0.0% <span className="text-gray-500 text-sm font-normal">/ 100.0% limit</span>
            </div>
            <div className="w-full h-1.5 bg-black rounded-full border border-gray-800 my-4 overflow-hidden">
               <div className="{`w-[${dailyLossPct}%]`} h-full bg-red-500 shadow-[0_0_10px_red]"></div>
            </div>
            <div className="text-xs text-gray-400 flex flex-col gap-1.5 font-mono">
              <span><span className="text-white font-bold">$0.00</span> used</span>
              <span><span className="text-white font-bold">${acc.virtual_balance.toLocaleString()}</span> remaining</span>
            </div>
         </div>

         {/* Daily Loss */}
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full text-center shadow-xl">
            <div className="text-gray-400 text-xs tracking-widest uppercase mb-3 font-bold">Daily Loss</div>
            <div className="text-lg text-white font-mono mb-1 font-bold">
              0.0% <span className="text-gray-500 text-sm font-normal">/ 100.0% limit</span>
            </div>
            <div className="w-full h-1.5 bg-black rounded-full border border-gray-800 my-4 overflow-hidden">
               <div className="{`w-[${dailyLossPct}%]`} h-full bg-red-500 shadow-[0_0_10px_red]"></div>
            </div>
            <div className="text-xs text-gray-400 flex flex-col gap-1.5 font-mono">
              <span><span className="text-white font-bold">$0.00</span> used</span>
              <span><span className="text-white font-bold">$100,000.00</span> remaining</span>
            </div>
         </div>
      </div>

      {/* 3. 4-GRID STATS */}
      <div className="grid grid-cols-2 gap-4 mb-6">
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center shadow-xl flex flex-col justify-center items-center">
            <div className="text-gray-400 text-[10px] tracking-widest uppercase mb-2 font-bold">Open P&L</div>
            <div className="text-green-400 text-xl font-mono font-bold">+$0.00</div>
         </div>
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center shadow-xl flex flex-col justify-center items-center">
            <div className="text-gray-400 text-[10px] tracking-widest uppercase mb-2 font-bold">Peak Equity</div>
            <div className="text-white text-xl font-mono font-bold">$100,033</div>
         </div>
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center shadow-xl flex flex-col justify-center items-center">
            <div className="text-gray-400 text-[10px] tracking-widest uppercase mb-2 font-bold">Win Rate</div>
            <div className="text-green-400 text-xl font-mono font-bold">{winRate}%</div>
         </div>
         <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center shadow-xl flex flex-col justify-center items-center">
            <div className="text-gray-400 text-[10px] tracking-widest uppercase mb-2 font-bold">Min Days</div>
            <div className="text-white text-xl font-mono font-bold">{acc.total_predictions} <span className="text-gray-500 text-sm font-normal">trades</span></div>
         </div>
      </div>

      {/* 4. TABS (CENTERED & SIZED EQUALLY) */}
      <div className="w-full bg-gray-900 border border-gray-800 rounded-xl p-1.5 flex mb-4 shadow-xl">
         {[
           { id: 'positions', label: 'Positions' },
           { id: 'orders', label: 'Open Orders' },
           { id: 'history', label: 'History' }
         ].map(tab => (
           <button
             key={tab.id}
             onClick={() => setActiveTab(tab.id)}
             className={`flex-1 text-center py-2.5 rounded-lg text-xs font-bold transition-all duration-300 ${
               activeTab === tab.id
                 ? 'bg-blue-600 text-white shadow-md'
                 : 'text-gray-400 hover:text-gray-200'
             }`}
           >
             {tab.label}
           </button>
         ))}
      </div>

      {/* 5. TAB CONTENT BOX */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center shadow-xl min-h-[180px] flex flex-col justify-center items-center">
         {activeTab === 'positions' && (
           <div className="animate-in fade-in duration-300 flex flex-col items-center">
             <Activity size={32} className="text-gray-600 mb-3" />
             <p className="text-sm text-gray-200 font-bold mb-1">No open positions</p>
             <p className="text-xs text-gray-500">Go to the markets to start trading.</p>
           </div>
         )}
         {activeTab === 'orders' && (
           <div className="animate-in fade-in duration-300 flex flex-col items-center">
             <Clock size={32} className="text-gray-600 mb-3" />
             <p className="text-sm text-gray-200 font-bold mb-1">No open orders</p>
             <p className="text-xs text-gray-500">Your pending orders will appear here.</p>
           </div>
         )}
         {activeTab === 'history' && (
           <div className="animate-in fade-in duration-300 flex flex-col items-center">
             <Target size={32} className="text-gray-600 mb-3" />
             <p className="text-sm text-gray-200 font-bold mb-1">No trade history</p>
             <p className="text-xs text-gray-500">Complete a trade to see your history.</p>
           </div>
         )}
      </div>
    </div>
  );
}
