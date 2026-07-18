import {
  Lock,
  Scale,
  ShieldCheck,
  Utensils,
} from 'lucide-react'
import { COVERAGE, TRUST_SIGNALS } from '@/lib/site'

const ICONS = [ShieldCheck, Utensils, Scale, Lock] as const

/**
 * Full-width trust bar — never squeeze into a narrow hero column.
 * Labels are short; diet list is a wrapping pill row (not truncated prose).
 */
export default function TrustSignals({ className = '' }: { className?: string }) {
  return (
    <div className={`w-full ${className}`.trim()} aria-label="Product trust signals">
      <ul className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        {TRUST_SIGNALS.map((item, i) => {
          const Icon = ICONS[i] ?? ShieldCheck
          return (
            <li
              key={item.label}
              className="flex items-start gap-3 rounded-2xl border border-slate-200/90 bg-white px-3.5 py-3 shadow-[0_1px_0_rgba(15,23,42,0.04)]"
            >
              <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-accent">
                <Icon className="h-4 w-4" strokeWidth={2} aria-hidden />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-tight text-primary">{item.label}</p>
                <p className="mt-0.5 text-xs leading-snug text-slate-500">{item.detail}</p>
              </div>
            </li>
          )
        })}
      </ul>

      {/* Diets as readable pills — never line-clamp a long middot string */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
          Diets covered
        </span>
        {COVERAGE.dietFrameworks.map((diet) => (
          <span
            key={diet}
            className="rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-[12px] font-medium text-slate-700"
          >
            {diet}
          </span>
        ))}
      </div>
    </div>
  )
}
