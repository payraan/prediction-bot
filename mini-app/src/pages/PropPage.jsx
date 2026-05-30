import React, { useState, useEffect } from 'react';
import { getActiveMarkets } from '../api/client';

export default function PropPage() {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);

  // داده‌های تستی برای نمایش داشبورد پراپ (در آینده از API گرفته می‌شود)
  const propAccount = {
    balance: 10350.00,
    starting: 10000.00,
    targetProfit: 11000.00,
    drawdown: 1.5, // 1.5% افت
    maxDrawdown: 8.0,
    predictions: 14
  };

  const profitPct = ((propAccount.balance - propAccount.starting) / propAccount.starting) * 100;
  const progressToTarget = Math.max(0, Math.min(100, (profitPct / 10) * 100)); // فرض تارگت 10%

  useEffect(() => {
    getActiveMarkets().then(data => {
        // فیلتر کردن بازارهای تستی یا خالی برای زیبایی
        setMarkets(data || []);
        setLoading(false);
    }).catch(e => {
        console.error("Error fetching markets:", e);
        setLoading(false);
    });
  }, []);

  return (
    <div className="page-container fade-in pb-24 text-right dir-rtl text-white p-4">
      
      {/* هدر صفحه */}
      <div className="bg-gradient-to-r from-blue-800 to-indigo-900 rounded-xl p-5 mb-5 shadow-lg border border-blue-500/30">
        <h2 className="text-xl font-bold mb-1">داشبورد چالش پراپ</h2>
        <p className="text-xs text-blue-200">فاز ۱ - حساب ۱۰,۰۰۰ دلاری</p>
      </div>

      {/* آمارهای حساب پراپ */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6 shadow-lg border border-gray-700">
        <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-3">
          <div>
            <p className="text-sm text-gray-400">موجودی مجازی</p>
            <p className="text-xl font-bold text-green-400">${propAccount.balance.toLocaleString()}</p>
          </div>
          <div className="text-left">
            <p className="text-sm text-gray-400">سود فعلی</p>
            <p className="text-lg font-bold text-green-400">+{profitPct.toFixed(2)}%</p>
          </div>
        </div>

        {/* نوار پیشرفت تارگت */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">پیشرفت تا تارگت (۱۰٪)</span>
            <span className="text-blue-400 font-bold">{progressToTarget.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${progressToTarget}%` }}></div>
          </div>
        </div>

        {/* نوار افت سرمایه */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">افت سرمایه (Drawdown)</span>
            <span className="text-red-400 font-bold">{propAccount.drawdown}% / {propAccount.maxDrawdown}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div className="bg-red-500 h-2 rounded-full" style={{ width: `${(propAccount.drawdown / propAccount.maxDrawdown) * 100}%` }}></div>
          </div>
        </div>
        
        <p className="text-xs text-center text-gray-400 mt-2">تعداد پیش‌بینی‌های ثبت شده: <span className="text-white font-bold">{propAccount.predictions}</span></p>
      </div>

      {/* لیست بازارها با طراحی نوارهای بصری */}
      <h3 className="text-lg font-bold mb-4 flex items-center gap-2"><span className="text-blue-400">🔥</span> بازارهای فعال</h3>
      
      {loading ? (
        <div className="text-center text-gray-400 py-10 animate-pulse">در حال دریافت اطلاعات بازارها... ⏳</div>
      ) : (
        <div className="space-y-4">
          {markets.length === 0 ? (
             <div className="text-center text-gray-400 py-5 bg-gray-800 rounded-xl">بازاری یافت نشد.</div>
          ) : markets.map(m => {
            const yesPct = Math.round((m.yes_price || 0.5) * 100);
            const noPct = Math.round((m.no_price || 0.5) * 100);
            
            return (
            <div key={m.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 shadow-md">
              <span className="text-[10px] bg-blue-900/60 text-blue-300 px-2 py-1 rounded mb-2 inline-block">
                {m.category || 'MARKET'}
              </span>
              <h4 className="text-sm font-bold mb-4 leading-relaxed">{m.title}</h4>
              
              <div className="space-y-3">
                {/* دکمه و نوار YES */}
                <div className="relative w-full bg-gray-700/50 rounded-lg overflow-hidden border border-green-500/20 cursor-pointer hover:border-green-500/50 transition-colors">
                  <div className="absolute top-0 right-0 h-full bg-green-500/20" style={{ width: `${yesPct}%` }}></div>
                  <div className="relative flex justify-between items-center px-3 py-2">
                    <span className="text-sm font-bold text-green-400">بله (Yes)</span>
                    <span className="text-sm font-bold text-white">{m.yes_price || '0.00'}</span>
                  </div>
                </div>
                
                {/* دکمه و نوار NO */}
                <div className="relative w-full bg-gray-700/50 rounded-lg overflow-hidden border border-red-500/20 cursor-pointer hover:border-red-500/50 transition-colors">
                  <div className="absolute top-0 right-0 h-full bg-red-500/20" style={{ width: `${noPct}%` }}></div>
                  <div className="relative flex justify-between items-center px-3 py-2">
                    <span className="text-sm font-bold text-red-400">خیر (No)</span>
                    <span className="text-sm font-bold text-white">{m.no_price || '0.00'}</span>
                  </div>
                </div>
              </div>
            </div>
          )})}
        </div>
      )}
    </div>
  );
}
