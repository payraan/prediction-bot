import React from 'react';

export default function HistoryPage() {
  // داده‌های تستی برای نمایش ظاهر تاریخچه (بعداً به API متصل می‌شود)
  const mockHistory = [
    { id: 1, market: 'قهرمانی استقلال در لیگ', direction: 'YES', amount: 50, status: 'WON', payout: 95, date: '2026-05-30' },
    { id: 2, market: 'قیمت بیت‌کوین بالای 70k', direction: 'NO', amount: 20, status: 'OPEN', payout: 0, date: '2026-05-29' },
    { id: 3, market: 'دربی پایتخت', direction: 'YES', amount: 100, status: 'LOST', payout: 0, date: '2026-05-28' },
  ];

  return (
    <div className="page-container fade-in pb-24 text-right dir-rtl text-white p-4">
      {/* هدر صفحه */}
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-xl p-5 mb-5 shadow-lg border border-gray-700">
        <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
          <span>📜</span> تاریخچه پیش‌بینی‌ها
        </h2>
        <p className="text-xs text-gray-400">سوابق تریدهای شما در پراپ و دمو</p>
      </div>

      {/* لیست تاریخچه */}
      <div className="space-y-3">
        {mockHistory.map(item => (
          <div key={item.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 shadow-md flex flex-col gap-3">
            <div className="flex justify-between items-start border-b border-gray-700 pb-2">
              <h4 className="text-sm font-bold text-gray-200">{item.market}</h4>
              <span className={`text-[10px] px-2 py-1 rounded font-bold ${
                item.status === 'WON' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                item.status === 'LOST' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
              }`}>
                {item.status === 'WON' ? 'برنده' : item.status === 'LOST' ? 'بازنده' : 'باز (OPEN)'}
              </span>
            </div>
            
            <div className="flex justify-between items-center text-sm">
              <div className="flex flex-col gap-1">
                <span className="text-gray-400 text-[11px]">جهت / مبلغ</span>
                <span className="font-bold text-sm">
                  <span className={item.direction === 'YES' ? 'text-green-400' : 'text-red-400'}>{item.direction}</span> 
                  <span className="text-gray-600 mx-2">|</span> 
                  <span className="text-blue-300">${item.amount}</span>
                </span>
              </div>
              
              <div className="flex flex-col gap-1 text-left">
                <span className="text-gray-400 text-[11px]">دریافتی (Payout)</span>
                <span className="font-bold text-white text-base">${item.payout}</span>
              </div>
            </div>
            <div className="text-[10px] text-gray-500 mt-1">{item.date}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
