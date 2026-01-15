/**
 * Bottom Navigation
 */

import { Home, Wallet, History } from 'lucide-react'

export default function BottomNav({ active, onChange }) {
  const tabs = [
    { id: 'home', label: 'خانه', icon: Home },
    { id: 'wallet', label: 'کیف پول', icon: Wallet },
    { id: 'history', label: 'تاریخچه', icon: History },
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
