/**
 * صفحه کیف پول
 */

import { useState } from 'react'
import { Copy, Check, QrCode } from 'lucide-react'
import WebApp from '@twa-dev/sdk'
import { useMe, useDeposit } from '../hooks/useApi'

export default function WalletPage({ onToast }) {
  const { user, loading: userLoading, refetch } = useMe()
  const { deposit, loading: depositLoading, createRequest } = useDeposit()
  const [copied, setCopied] = useState(null)

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

      <div className="deposit-section">
        <h3>واریز TON</h3>
        
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
    </div>
  )
}
