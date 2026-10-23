'use client'

interface ConfirmRestrictionActionsProps {
  disabled?: boolean
  onReply: (text: string) => void
}

export default function ConfirmRestrictionActions({
  disabled,
  onReply,
}: ConfirmRestrictionActionsProps) {
  return (
    <div
      className="mt-3 flex flex-wrap gap-2"
      data-testid="confirm-restriction-actions"
      role="group"
      aria-label="Confirm restriction"
    >
      <button
        type="button"
        data-testid="confirm-yes"
        disabled={disabled}
        onClick={() => onReply('yes')}
        className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-sm font-semibold text-teal-900 hover:bg-teal-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        Yes, save
      </button>
      <button
        type="button"
        data-testid="confirm-no"
        disabled={disabled}
        onClick={() => onReply('no')}
        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        No
      </button>
      <button
        type="button"
        data-testid="confirm-only-today"
        disabled={disabled}
        onClick={() => onReply('only today')}
        className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        Only today
      </button>
    </div>
  )
}
