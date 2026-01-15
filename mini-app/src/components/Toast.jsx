/**
 * Toast Notifications
 */

import { useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function Toast({ message, type = 'info', onClose, duration = 3000 }) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onClose])

  const icons = {
    success: <CheckCircle size={20} />,
    error: <XCircle size={20} />,
    info: <AlertCircle size={20} />,
  }

  return (
    <div className={`toast ${type}`}>
      {icons[type]}
      <span>{message}</span>
    </div>
  )
}
