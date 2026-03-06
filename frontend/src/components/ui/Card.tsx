import React from 'react'
import { radii, shadows } from '@/theme/tokens'

interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={[
        'bg-white',
        'rounded-2xl',
        'shadow-sm',
        'ring-1 ring-slate-100',
        'p-6',
        className,
      ].join(' ')}
      style={{ borderRadius: radii.lg, boxShadow: shadows.card }}
    >
      {children}
    </div>
  )
}

