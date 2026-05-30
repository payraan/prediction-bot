import React, { useState, useEffect } from 'react';
import { getActiveMarkets } from '../api/client';

export default function PropPage({ token }) {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if(token) {
       getActiveMarkets(token).then(data => {
           setMarkets(data);
           setLoading(false);
       }).catch(e => {
           console.error("Error fetching markets:", e);
           setLoading(false);
       });
    }
  }, [token]);

  return (
    <div className="page-container fade-in pb-24 text-right dir-rtl text-white p-4">
      
      {/* هدر صفحه */}
      <div className="bg-gradient-to-r from-blue-700 to-purple-700 rounded-xl p-5 mb-5 shadow-lg">
        <h2 className="text-2xl font-bold mb-2">🌐 پراپ و پالی‌مارکت</h2>
        <p className="text-sm text-blue-100">معامله روی بازارهای جهانی و بومی</p>
      </div>

      {/* داشبورد پراپ */}
      <div className="bg-gray-800 rounded-xl p-5 mb-6 shadow-lg border border-gray-700 text-center">
        <h3 className="text-lg font-bold mb-2 text-gray-200">وضعیت چالش شما</h3>
        <p className="text-sm text-gray-400 mb-4">برای شروع پیش‌بینی روی مارکت‌ها، به یک اکانت پراپ نیاز دارید.</p>
        <button className="bg-green-600 hover:bg-green-500 text-white font-bold py-3 px-4 rounded-lg w-full transition-colors shadow-lg">
          🛒 خرید چالش ۱۰,۰۰۰ دلاری (۵۰ تتر)
        </button>
      </div>

      {/* لیست بازارها */}
      <h3 className="text-xl font-bold mb-4 border-b border-gray-700 pb-2">🔥 بازارهای فعال</h3>
      
      {loading ? (
        <div className="text-center text-gray-400 py-10 animate-pulse">در حال دریافت اطلاعات بازارها... ⏳</div>
      ) : (
        <div className="space-y-4">
          {markets.length === 0 ? (
             <div className="text-center text-gray-400 py-5 bg-gray-800 rounded-xl">هیچ بازار فعالی یافت نشد.</div>
          ) : markets.map(m => (
            <div key={m.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 shadow-md">
              <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-1 rounded mb-3 inline-block border border-blue-800">
                {m.category || 'عمومی'}
              </span>
              <h4 className="text-[15px] font-bold mb-4 leading-relaxed">{m.title}</h4>
              <div className="flex gap-3">
                <button className="flex-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/50 font-bold py-2 rounded-lg transition-colors flex justify-between px-3 items-center">
                  <span className="text-sm">بله (Yes)</span>
                  <span className="text-lg">{m.yes_price}</span>
                </button>
                <button className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/50 font-bold py-2 rounded-lg transition-colors flex justify-between px-3 items-center">
                  <span className="text-sm">خیر (No)</span>
                  <span className="text-lg">{m.no_price}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
