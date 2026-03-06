export const colors = {
  primary: '#0F172A',       // deep slate blue
  secondary: '#10B981',     // emerald green
  warning: '#F59E0B',       // amber
  danger: '#EF4444',        // red
  background: '#F8FAFC',
  foreground: '#111827',
  neutral: '#E5E7EB',
  surface: '#FFFFFF',
  muted: '#6B7280',
}

export const radii = {
  sm: '8px',
  md: '12px',
  lg: '16px',
}

export const shadows = {
  card: '0 4px 12px rgba(0,0,0,0.06)',
  lift: '0 8px 24px rgba(0,0,0,0.10)',
}

export const spacing = {
  base: 24,
  inner: 12,
}

export const gradients = {
  primaryCta: 'bg-gradient-to-r from-emerald-500 to-lime-400',
  primaryCtaHover: 'hover:from-emerald-500 hover:to-lime-400',
  safe: 'from-emerald-50 to-emerald-100',
  avoid: 'from-rose-50 to-rose-100',
  depends: 'from-amber-50 to-amber-100',
}

export const statusColors = {
  safe: {
    text: 'text-emerald-700',
    pill: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    card: gradients.safe,
  },
  avoid: {
    text: 'text-rose-700',
    pill: 'bg-rose-100 text-rose-800 border-rose-200',
    card: gradients.avoid,
  },
  depends: {
    text: 'text-amber-700',
    pill: 'bg-amber-100 text-amber-800 border-amber-200',
    card: gradients.depends,
  },
} as const

