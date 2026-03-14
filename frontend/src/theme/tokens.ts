/**
 * Design tokens. Single source for JS-only use (e.g. inline styles, cardBg hex).
 * Brand colors (primary, secondary, safe, avoid, depends) match globals.css; prefer Tailwind classes (bg-primary, bg-secondary, etc.) in components so globals stay the single source for UI.
 * In use: `gradients` (statusColors.card), `statusColors`, `colors`, `cardBg` (IngredientAuditCards).
 */
export const colors = {
  primary: '#0F172A',       // deep slate blue
  secondary: '#10B981',     // emerald green
  safe: '#10B981',
  avoid: '#EF4444',
  depends: '#F59E0B',
  warning: '#F59E0B',
  danger: '#EF4444',
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
  card: '0 2px 8px rgba(0,0,0,0.08)',
  lift: '0 8px 24px rgba(0,0,0,0.10)',
}

export const spacing = {
  base: 24,
  inner: 12,
}

export const gradients = {
  primaryCta: 'bg-gradient-to-r from-[#0F172A] to-[#10B981]',
  primaryCtaHover: 'hover:from-[#0F172A] hover:to-[#10B981]',
  safe: 'from-emerald-50 to-emerald-100',
  avoid: 'from-rose-50 to-rose-100',
  depends: 'from-amber-50 to-amber-100',
}

/** Light background for status cards (left bar + tint). */
export const cardBg = {
  safe: '#F0FDF4',
  avoid: '#FEF2F2',
  depends: '#FFFBEB',
} as const

/** statusColors use Tailwind theme classes (globals.css) for pill/bar so one source of truth. */
export const statusColors = {
  safe: {
    text: 'text-emerald-700',
    pill: 'bg-secondary text-white border-0 shadow-card font-medium',
    card: gradients.safe,
    bar: 'border-secondary',
  },
  avoid: {
    text: 'text-rose-700',
    pill: 'bg-avoid text-white border-0 shadow-card font-medium',
    card: gradients.avoid,
    bar: 'border-avoid',
  },
  depends: {
    text: 'text-amber-700',
    pill: 'bg-depends text-white border-0 shadow-card font-medium',
    card: gradients.depends,
    bar: 'border-depends',
  },
} as const

