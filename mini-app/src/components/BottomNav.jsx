/**
 * Bottom Navigation
 */

import { Home, Wallet, History, Trophy, User, Globe } from 'lucide-react'

export default function BottomNav({ active, onChange }) {
  const tabs = [
    { id: 'home', label: 'خانه', icon: Home },
    { id: 'prop', label: 'مارکت', icon: Globe },
    { id: 'wallet', label: 'ولِت', icon: Wallet },
    { id: 'history', label: 'سوابق', icon: History },
    { id: 'leaderboard', label: 'برترین‌ها', icon: Trophy },
    { id: 'profile', label: 'پروفایل', icon: User },
  ]

  return (
    <nav className="bottom-nav">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`nav-item ${active === tab.id ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          <tab.icon size={24} />
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  )
}
