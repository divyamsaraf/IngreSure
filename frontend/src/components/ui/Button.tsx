'use client'

import React from 'react'
import Link from 'next/link'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface BaseProps {
  variant?: Variant
  size?: Size
  className?: string
  children: React.ReactNode
}

type ButtonAsButton = BaseProps & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'className'> & { href?: never }
type ButtonAsLink = BaseProps & Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'className'> & { href: string }
type ButtonProps = ButtonAsButton | ButtonAsLink

export function Button(props: ButtonProps) {
  const {
    variant = 'primary',
    size = 'md',
    className = '',
    children,
    href,
    ...rest
  } = props

  const base =
    'inline-flex items-center justify-center font-semibold transition-transform transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 disabled:opacity-60 disabled:pointer-events-none'

  const variantClasses: Record<Variant, string> = {
    primary: 'bg-gradient-to-r from-primary to-secondary text-white shadow-lg shadow-emerald-500/30 hover:-translate-y-0.5 hover:shadow-emerald-500/50',
    secondary:
      'bg-white text-slate-800 border border-slate-200 hover:bg-slate-50 hover:-translate-y-0.5 shadow-sm',
    ghost: 'bg-transparent text-slate-800 hover:bg-slate-50',
  }

  const sizeClasses: Record<Size, string> = {
    sm: 'px-3 py-1.5 text-xs rounded-[12px]',
    md: 'px-5 py-2.5 text-sm rounded-[16px]',
    lg: 'px-7 py-3.5 text-base rounded-2xl md:px-9 md:py-4 md:text-lg',
  }

  const composed = [base, variantClasses[variant as Variant], sizeClasses[size as Size], className]
    .filter(Boolean)
    .join(' ')

  if (href) {
    return (
      <Link href={href} className={composed} {...(rest as Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, keyof BaseProps | 'href'>)}>
        {children}
      </Link>
    )
  }

  return (
    <button className={composed} {...(rest as Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, keyof BaseProps>)}>
      {children}
    </button>
  )
}

