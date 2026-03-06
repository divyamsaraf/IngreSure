'use client'

import React from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string
  helperText?: string
}

export function Input({ error, helperText, className = '', ...rest }: InputProps) {
  return (
    <div className="w-full space-y-1">
      <input
        className={[
          'w-full rounded-2xl border px-4 py-3 text-sm font-medium text-slate-700 bg-slate-50',
          'focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500',
          error ? 'border-red-300' : 'border-slate-200',
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        {...rest}
      />
      {(helperText || error) && (
        <p className={`text-xs ${error ? 'text-red-600' : 'text-slate-500'}`}>
          {error || helperText}
        </p>
      )}
    </div>
  )
}

