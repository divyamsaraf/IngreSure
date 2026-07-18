import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

export default function BusinessBridgeSection() {
  return (
    <section className="px-6 py-14 md:py-16">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 rounded-2xl border border-slate-200 bg-white px-6 py-8 md:flex-row md:items-center md:justify-between md:px-10 md:py-10">
        <div className="max-w-xl">
          <h2 className="font-display text-2xl font-bold tracking-tight text-primary md:text-3xl">
            Building checkout, menus, or recipes?
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600 md:text-base">
            We&apos;re onboarding early partners for allergen and dietary compliance inside your
            product flow — not bolted on after the fact.
          </p>
        </div>
        <Link
          href="/for-business"
          className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-accent/30 bg-teal-50 px-5 py-3 text-sm font-semibold text-accent transition-colors hover:bg-teal-100/80 md:self-center"
        >
          IngreSure for platforms
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </section>
  )
}
