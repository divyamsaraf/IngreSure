'use client'

import { ArrowRight, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'

/** Shared label for every "open chat" CTA on the marketing site. */
export const PRIMARY_CHAT_CTA_LABEL = 'Try Grocery Assistant'

export const PRIMARY_CHAT_ARIA_LABEL =
  'Try Grocery Assistant — opens the ingredient chat, no signup required'

type PrimaryChatCtaVariant = 'onLight' | 'onDark' | 'compact'

const sizeForVariant: Record<PrimaryChatCtaVariant, 'lg' | 'md'> = {
  onLight: 'lg',
  onDark: 'lg',
  compact: 'md',
}

/** Layout / ring only — colors come from `Button` `variant="primary"` (single source). */
const variantClass: Record<PrimaryChatCtaVariant, string> = {
  onLight: [
    'gap-2 font-bold',
    'min-h-[52px] min-w-[min(100%,17.5rem)]',
    'shadow-xl shadow-emerald-600/30 ring-2 ring-emerald-500/35 ring-offset-2 ring-offset-[#f8fafc]',
    'hover:ring-emerald-500/55 md:min-h-[56px]',
  ].join(' '),
  onDark: [
    'gap-2 font-bold',
    'min-h-[52px] min-w-[min(100%,17.5rem)]',
    'shadow-xl ring-2 ring-emerald-400/45 ring-offset-2 ring-offset-slate-900',
    'hover:ring-emerald-400/60 md:min-h-[56px]',
  ].join(' '),
  compact: ['gap-2 font-bold', 'min-h-[48px] md:min-h-[52px]'].join(' '),
}

export interface PrimaryChatCtaProps {
  variant: PrimaryChatCtaVariant
  href?: string
  className?: string
  'aria-label'?: string
}

export function PrimaryChatCta({
  variant,
  href = '/chat',
  className = '',
  'aria-label': ariaLabel = PRIMARY_CHAT_ARIA_LABEL,
}: PrimaryChatCtaProps) {
  const isCompact = variant === 'compact'
  const iconClass = isCompact ? 'h-5 w-5 shrink-0' : 'h-5 w-5 shrink-0 md:h-6 md:w-6'
  const arrowClass = isCompact ? 'h-4 w-4 shrink-0 md:h-5 md:w-5' : 'h-5 w-5 shrink-0 md:h-6 md:w-6'

  return (
    <Button
      href={href}
      variant="primary"
      size={sizeForVariant[variant]}
      className={[variantClass[variant], className].filter(Boolean).join(' ')}
      aria-label={ariaLabel}
    >
      <MessageCircle className={iconClass} aria-hidden />
      {PRIMARY_CHAT_CTA_LABEL}
      <ArrowRight className={arrowClass} aria-hidden />
    </Button>
  )
}
