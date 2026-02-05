/**
 * TON Prediction Mini App
 * Main Application Component
 */

import { useState, useEffect } from 'react'
import WebApp from '@twa-dev/sdk'

import BottomNav from './components/BottomNav'
import Toast from './components/Toast'
import HomePage from './pages/HomePage'
import WalletPage from './pages/WalletPage'
import HistoryPage from './pages/HistoryPage'
import LeaderboardPage from './pages/LeaderboardPage'

import './styles/main.css'

function App() {
  const [activePage, setActivePage] = useState('home')
  const [toast, setToast] = useState(null)
  const [user, setUser] = useState(null)

  useEffect(() => {
    // Initialize Telegram WebApp
    WebApp.ready()
    WebApp.expand()
    
    // Set theme
    document.body.style.backgroundColor = WebApp.backgroundColor || '#0a0a0f'
    
    // Get user from Telegram
    if (WebApp.initDataUnsafe?.user) {
      setUser(WebApp.initDataUnsafe.user)
    }
  }, [])

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
  }

  const hideToast = () => {
    setToast(null)
  }

  const renderPage = () => {
    switch (activePage) {
      case 'home':
        return <HomePage onToast={showToast} />
      case 'wallet':
        return <WalletPage onToast={showToast} />
      case 'history':
        return <HistoryPage />
      case 'leaderboard':
        return <LeaderboardPage />
      default:
        return <HomePage onToast={showToast} />
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎯 TON Prediction</h1>
        {user && <p className="welcome">سلام {user.first_name}! 👋</p>}
      </header>

      <main>
        {renderPage()}
      </main>

      <BottomNav 
        active={activePage} 
        onChange={setActivePage} 
      />

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={hideToast}
        />
      )}
    </div>
  )
}

export default App
