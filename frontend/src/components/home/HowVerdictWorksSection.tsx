import type { ReactNode } from 'react'
import Link from 'next/link'
import { ArrowRight, FileText, Scale, Sparkles } from 'lucide-react'

/**
 * Explains the product differentiator in plain language for consumers + evaluators.
 */
export default function HowVerdictWorksSection() {
  return (
    <section id="how-verdict-works" className="scroll-mt-24 bg-surface px-6 py-14 md:py-16">
      <div className="mx-auto max-w-6xl">
        <div className="max-w-2xl">
          <p className="ds-eyebrow">How a check works</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-primary md:text-4xl">
            The safety call is never a guess.
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-slate-600 md:text-base">
            IngreSure separates two jobs on purpose. A rules engine decides Safe, Avoid, or Depends
            against your diet and allergens. A language model only explains that result in plain
            English — it cannot override the engine.
          </p>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch md:gap-2">
          <FlowCard
            icon={<FileText className="h-5 w-5" aria-hidden />}
            step="1"
            title="Paste what you have"
            body="A grocery label, menu line, or recipe list. Typos and messy formatting are fine."
          />
          <FlowArrow />
          <FlowCard
            icon={<Scale className="h-5 w-5" aria-hidden />}
            step="2"
            title="Rules score each ingredient"
            body="Every item is checked against your profile — diet frameworks, allergens, and known derivatives."
            emphasize
          />
          <FlowArrow />
          <FlowCard
            icon={<Sparkles className="h-5 w-5" aria-hidden />}
            step="3"
            title="You get a clear explanation"
            body="Why it was flagged, what to watch for, and safer swaps when we know them."
          />
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-accent/25 bg-teal-50/60 p-5 md:p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              Makes the verdict
            </p>
            <p className="mt-2 font-display text-xl font-semibold text-primary">Compliance engine</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Deterministic Safe / Avoid / Depends from curated ingredient rules. If the model and the
              engine disagree, the engine wins — every time.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
              Writes the explanation
            </p>
            <p className="mt-2 font-display text-xl font-semibold text-primary">Local language model</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Helps parse messy input and turn the structured result into readable guidance. It does
              not invent the safety call.
            </p>
          </div>
        </div>

        <p className="mt-8 text-sm text-slate-500">
          <Link
            href="/about"
            className="inline-flex items-center gap-1.5 font-medium text-accent underline-offset-2 hover:underline"
          >
            Why we built it this way
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </p>
      </div>
    </section>
  )
}

function FlowArrow() {
  return (
    <div className="hidden items-center justify-center text-slate-300 md:flex" aria-hidden>
      <ArrowRight className="h-5 w-5" />
    </div>
  )
}

function FlowCard({
  icon,
  step,
  title,
  body,
  emphasize = false,
}: {
  icon: ReactNode
  step: string
  title: string
  body: string
  emphasize?: boolean
}) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        emphasize
          ? 'border-accent/30 bg-white shadow-[0_12px_40px_rgba(15,118,110,0.08)]'
          : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-3">
        <span
          className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${
            emphasize ? 'bg-accent text-white' : 'bg-teal-50 text-accent'
          }`}
        >
          {icon}
        </span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Step {step}
        </span>
      </div>
      <h3 className="mt-4 text-base font-semibold text-primary">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{body}</p>
    </div>
  )
}
