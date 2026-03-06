import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

export default function FinalCtaSection() {
  return (
    <section className="px-6 py-16 md:py-20 bg-slate-900 text-slate-50">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 md:flex-row">
        <div className="max-w-xl text-center md:text-left space-y-2">
          <h2 className="font-serif text-3xl font-bold">
            Ready to check your first label?
          </h2>
          <p className="text-sm md:text-base text-slate-300">
            Start a grocery audit in seconds. Paste any ingredient list and get a clear, personalized answer — no signup required.
          </p>
        </div>
        <div className="flex flex-col items-center gap-3">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 rounded-[16px] bg-gradient-to-r from-emerald-500 to-lime-400 px-7 py-3 text-sm font-semibold text-slate-900 shadow-lg shadow-emerald-500/40 transition-transform transition-shadow hover:-translate-y-0.5 hover:shadow-emerald-400/60"
          >
            Start Your First Audit
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="text-[11px] text-slate-400">
            Chat-first, profile-aware ingredient audits • Mobile friendly
          </p>
        </div>
      </div>
    </section>
  )
}

