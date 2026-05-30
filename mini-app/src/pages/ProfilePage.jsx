import React from 'react';

export default function ProfilePage({ user }) {
  return (
    <div className="page-container fade-in pb-24 text-right dir-rtl text-white p-4">
      
      {/* هدر پروفایل */}
      <div className="bg-gray-800 rounded-xl p-5 mb-4 shadow-lg border border-gray-700">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <span>👤</span> پروفایل من
        </h2>
        <div className="space-y-2 text-sm text-gray-300">
          <p><span className="text-gray-400">نام:</span> {user?.first_name || 'کاربر'}</p>
          <p><span className="text-gray-400">شناسه تلگرام:</span> {user?.telegram_id}</p>
        </div>
      </div>

      {/* قوانین پراپ فرم */}
      <div className="bg-gray-800 rounded-xl p-5 mb-4 shadow-lg border border-gray-700">
        <h3 className="text-lg font-bold mb-4 text-blue-400 border-b border-gray-700 pb-2">📜 قوانین پراپ فرم</h3>
        <ul className="space-y-4 text-sm text-gray-300">
          <li className="flex flex-col gap-1">
            <strong className="text-white">🎯 تارگت سود:</strong> 
            <span>فاز اول ۱۰٪ | فاز دوم ۵٪</span>
          </li>
          <li className="flex flex-col gap-1">
            <strong className="text-white">📉 افت کل (Drawdown):</strong> 
            <span>حداکثر ۸٪ از موجودی اولیه (استاتیک)</span>
          </li>
          <li className="flex flex-col gap-1">
            <strong className="text-white">🔻 افت روزانه:</strong> 
            <span>حداکثر ۴٪ از اکوئیتی شروع روز</span>
          </li>
          <li className="flex flex-col gap-1">
            <strong className="text-white">🛡 قوانین ضدقمار:</strong> 
            <span>پیش‌بینی فقط روی ضریب‌های ۰.۱۵ تا ۰.۸۵ مجاز است.</span>
          </li>
          <li className="flex flex-col gap-1">
            <strong className="text-white">⚖️ ریسک مجاز:</strong> 
            <span>درگیری حداکثر ۱۵٪ از کل سرمایه روی هر بازار.</span>
          </li>
        </ul>
      </div>
      
      {/* درباره پلتفرم */}
      <div className="bg-gray-800 rounded-xl p-5 shadow-lg border border-gray-700">
        <h3 className="text-lg font-bold mb-3 text-purple-400">💎 درباره سیستم</h3>
        <p className="text-sm text-gray-300 leading-relaxed text-justify">
          شما در حال استفاده از اولین سیستم تأمین سرمایه (Prop Firm) بازارهای پیش‌بینی هستید. 
          با پاس کردن چالش‌ها در محیط شبیه‌ساز، تا ۸۰٪ سود واقعی از معاملات خود دریافت کنید!
        </p>
      </div>
    </div>
  );
}
