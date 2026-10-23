import { BETA_BANNER } from '@/constants/disclaimers'

export default function BetaBanner() {
  return (
    <div
      role="status"
      data-testid="beta-banner"
      className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-slate-800"
    >
      <p>{BETA_BANNER}</p>
    </div>
  )
}
