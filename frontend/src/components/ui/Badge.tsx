import React from 'react'
import clsx from 'clsx'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'gold'
  department?: 'cs' | 'math' | 'ece' | 'chem' | 'bio'
  dot?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  department,
  dot = false,
  className,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide transition-colors'

  const variantStyles = {
    success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    warning: 'bg-amber-50 text-amber-700 border border-amber-200',
    danger: 'bg-red-50 text-red-700 border border-red-200',
    info: 'bg-blue-50 text-blue-700 border border-blue-200',
    neutral: 'bg-slate-100 text-slate-700 border border-slate-200',
    gold: 'bg-amber-100 text-amber-900 border border-amber-300 font-bold',
  }

  const departmentStyles = {
    cs: 'badge-dept-cs',
    math: 'badge-dept-math',
    ece: 'badge-dept-ece',
    chem: 'badge-dept-chem',
    bio: 'badge-dept-bio',
  }

  const dotColors = {
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    danger: 'bg-red-500',
    info: 'bg-blue-500',
    neutral: 'bg-slate-400',
    gold: 'bg-amber-500',
  }

  const selectedStyle = department
    ? departmentStyles[department]
    : variantStyles[variant]

  return (
    <span className={clsx(baseStyles, selectedStyle, className)} {...props}>
      {dot && (
        <span
          className={clsx(
            'w-1.5 h-1.5 rounded-full mr-1.5 flex-shrink-0',
            dotColors[variant]
          )}
        />
      )}
      {children}
    </span>
  )
}

export default Badge
