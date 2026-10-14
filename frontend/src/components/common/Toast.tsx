import React, { useEffect } from 'react'
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'

export interface ToastProps {
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  onClose: () => void
  duration?: number
}

export const Toast: React.FC<ToastProps> = ({
  type,
  message,
  onClose,
  duration = 4000,
}) => {
  useEffect(() => {
    if (duration <= 0) return
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [onClose, duration])

  const styles = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800 shadow-emerald-900/10',
    error: 'bg-red-50 border-red-200 text-red-800 shadow-red-900/10',
    warning: 'bg-amber-50 border-amber-200 text-amber-800 shadow-amber-900/10',
    info: 'bg-blue-50 border-blue-200 text-blue-800 shadow-blue-900/10',
  }

  const iconMap = {
    success: <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />,
    info: <Info className="w-5 h-5 text-blue-600 flex-shrink-0" />,
  }

  return (
    <div
      role="alert"
      data-testid="toast"
      data-toast-type={type}
      className={`fixed bottom-5 right-5 z-50 flex items-center space-x-3 p-4 rounded-xl border shadow-lg transition-all transform animate-in fade-in slide-in-from-bottom-2 duration-200 ${styles[type]}`}
    >
      {iconMap[type]}
      <span className="text-sm font-medium pr-2">{message}</span>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close notification"
        className="p-1 rounded-lg hover:bg-black/5 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-current"
      >
        <X className="w-4 h-4 opacity-70 hover:opacity-100" />
      </button>
    </div>
  )
}

export default Toast
