import React from 'react'
import { statusColors } from '@/theme/tokens'

type Status = keyof typeof statusColors

interface PillProps {
  children: React.ReactNode
  className?: string
}

export function Pill({ children, className = '' }: PillProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium transition-colors transition-shadow',
        'hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40',
        className,
      ].join(' ')}
    >
      {children}
    </span>
  )
}

interface StatusPillProps {
  status: Status
  children: React.ReactNode
  className?: string
}

export function StatusPill({ status, children, className = '' }: StatusPillProps) {
  const color = statusColors[status].pill
  return (
    <Pill className={`${color} border ${className}`}>
      {children}
    </Pill>
  )
}

