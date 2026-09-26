import React from 'react'
import { Info, CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react'
import clsx from 'clsx'

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'danger'
  title?: string
  icon?: boolean | React.ReactNode
  onClose?: () => void
}

const variantStyles = {
  info: {
    container: 'bg-blue-50/80 border-blue-200 text-blue-900',
    iconColor: 'text-blue-600',
    icon: Info,
  },
  success: {
    container: 'bg-emerald-50/80 border-emerald-200 text-emerald-900',
    iconColor: 'text-emerald-600',
    icon: CheckCircle2,
  },
  warning: {
    container: 'bg-amber-50/80 border-amber-200 text-amber-900',
    iconColor: 'text-amber-600',
    icon: AlertTriangle,
  },
  danger: {
    container: 'bg-red-50/80 border-red-200 text-red-900',
    iconColor: 'text-red-600',
    icon: AlertCircle,
  },
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = 'info',
  title,
  icon = true,
  onClose,
  className,
  ...props
}) => {
  const current = variantStyles[variant]
  const IconComponent = current.icon

  return (
    <div
      role="alert"
      className={clsx(
        'p-4 rounded-2xl border flex items-start space-x-3 text-xs leading-relaxed transition-all duration-200',
        current.container,
        className
      )}
      {...props}
    >
      {icon && (
        <span className={clsx('flex-shrink-0 mt-0.5', current.iconColor)}>
          {React.isValidElement(icon) ? icon : <IconComponent className="w-5 h-5" />}
        </span>
      )}

      <div className="flex-1 space-y-0.5">
        {title && <h5 className="font-bold text-sm tracking-tight">{title}</h5>}
        <div>{children}</div>
      </div>

      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss alert"
          className="flex-shrink-0 text-slate-400 hover:text-slate-600 p-0.5 rounded-lg hover:bg-black/5 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export default Alert
