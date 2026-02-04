/**
 * صفحه کیف پول
 */

import { useState } from 'react'
import { Copy, Check, Send } from 'lucide-react'
import WebApp from '@twa-dev/sdk'
import { useMe, useDeposit } from '../hooks/useApi'
import { requestWithdrawal } from '../api/client'

export default function WalletPage({ onToast }) {
  const { user, loading: userLoading, refetch } = useMe()
  const { deposit, loading: depositLoading, createRequest } = useDeposit()
  const [copied, setCopied] = useState(null)
  const [activeTab, setActiveTab] = useState('deposit') // deposit | withdraw
  
  // Withdrawal state
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawAddress, setWithdrawAddress] = useState('')
  const [withdrawLoading, setWithdrawLoading] = useState(false)

  const balance = user?.balance_available || 0
  const locked = user?.balance_locked || 0

  const handleDeposit = async () => {
    try {
      await createRequest()
      onToast('درخواست واریز ایجاد شد', 'success')
    } catch (err) {
      onToast('خطا در ایجاد درخواست', 'error')
    }
  }

  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount)
    
    if (!amount || amount < 1) {
      onToast('حداقل برداشت 1 TON است', 'error')
      return
    }
    
    if (amount > balance) {
      onToast('موجودی کافی نیست', 'error')
      return
    }
    
    if (!withdrawAddress || withdrawAddress.length < 20) {
      onToast('آدرس کیف پول نامعتبر است', 'error')
      return
    }
    
    setWithdrawLoading(true)
    
    try {
      const result = await requestWithdrawal(amount, withdrawAddress)
      
      if (result.id) {
        onToast(`درخواست برداشت ${amount} TON ثبت شد`, 'success')
        WebApp.HapticFeedback.notificationOccurred('success')
        setWithdrawAmount('')
        setWithdrawAddress('')
        refetch()
      } else {
        onToast(result.detail || 'خطا در ثبت درخواست', 'error')
      }
    } catch (err) {
      onToast('خطا در ثبت درخواست برداشت', 'error')
    } finally {
      setWithdrawLoading(false)
    }
  }

  const copyToClipboard = async (text, type) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      WebApp.HapticFeedback.notificationOccurred('success')
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      onToast('خطا در کپی', 'error')
    }
  }

  return (
    <div className="page wallet-page">
      <div className="wallet-header">
        <h2>💰 کیف پول</h2>
      </div>

      <div className="balance-card">
        <div className="balance-item main">
          <span className="label">موجودی قابل استفاده</span>
          <span className="value">{balance.toFixed(4)} TON</span>
        </div>
        <div className="balance-item">
          <span className="label">در شرط‌بندی</span>
          <span className="value locked">{locked.toFixed(4)} TON</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="wallet-tabs">
        <button 
          className={`tab ${activeTab === 'deposit' ? 'active' : ''}`}
          onClick={() => setActiveTab('deposit')}
        >
          📥 واریز
        </button>
        <button 
          className={`tab ${activeTab === 'withdraw' ? 'active' : ''}`}
          onClick={() => setActiveTab('withdraw')}
        >
          📤 برداشت
        </button>
      </div>

      {/* Deposit Tab */}
      {activeTab === 'deposit' && (
        <div className="deposit-section">
          {!deposit ? (
            <button 
              className="deposit-btn"
              onClick={handleDeposit}
              disabled={depositLoading}
            >
              {depositLoading ? 'در حال ایجاد...' : '+ ایجاد درخواست واریز'}
            </button>
          ) : (
            <div className="deposit-info">
              <div className="info-box warning">
                <span>⚠️ حتماً memo را وارد کنید!</span>
              </div>

              <div className="deposit-field">
                <label>آدرس ولت:</label>
                <div className="field-value">
                  <span className="address">{deposit.to_address}</span>
                  <button 
                    className="copy-btn"
                    onClick={() => copyToClipboard(deposit.to_address, 'address')}
                  >
                    {copied === 'address' ? <Check size={18} /> : <Copy size={18} />}
                  </button>
                </div>
              </div>

              <div className="deposit-field memo">
                <label>Memo (ضروری):</label>
                <div className="field-value">
                  <span className="memo-value">{deposit.memo}</span>
                  <button 
                    className="copy-btn"
                    onClick={() => copyToClipboard(deposit.memo, 'memo')}
                  >
                    {copied === 'memo' ? <Check size={18} /> : <Copy size={18} />}
                  </button>
                </div>
              </div>

              {deposit.expected_amount && (
                <div className="deposit-field">
                  <label>مبلغ:</label>
                  <span>{deposit.expected_amount} TON</span>
                </div>
              )}

              <div className="deposit-field">
                <label>انقضا:</label>
                <span>{new Date(deposit.expires_at).toLocaleString('fa-IR')}</span>
              </div>

              <div className="info-box">
                <p>پس از واریز، موجودی شما به صورت خودکار شارژ می‌شود.</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Withdraw Tab */}
      {activeTab === 'withdraw' && (
        <div className="withdraw-section">
          <div className="withdraw-form">
            <div className="form-field">
              <label>مبلغ برداشت (TON)</label>
              <input
                type="number"
                placeholder="حداقل 1 TON"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                min="1"
                step="0.1"
              />
              <span className="hint">موجودی: {balance.toFixed(4)} TON</span>
            </div>

            <div className="form-field">
              <label>آدرس کیف پول مقصد</label>
              <input
                type="text"
                placeholder="آدرس TON wallet..."
                value={withdrawAddress}
                onChange={(e) => setWithdrawAddress(e.target.value)}
              />
            </div>

            <div className="info-box">
              <p>⏱ برداشت زیر 50 TON: خودکار</p>
              <p>👨‍💼 برداشت بالای 50 TON: نیاز به تأیید ادمین</p>
            </div>

            <button 
              className="withdraw-btn"
              onClick={handleWithdraw}
              disabled={withdrawLoading || !withdrawAmount || !withdrawAddress}
            >
              {withdrawLoading ? (
                'در حال ثبت...'
              ) : (
                <>
                  <Send size={18} />
                  ثبت درخواست برداشت
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
