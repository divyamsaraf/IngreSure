'use client'

import Link from 'next/link'
import { ShieldCheck, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { PrimaryChatCta } from '@/components/home/PrimaryChatCta'

export default function HeroSection() {
  return (
    <header className="bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-16 md:flex-row md:items-center md:py-20">
        {/* Text column */}
        <div className="flex-1 space-y-6">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Ingredient intelligence for real people
          </p>
          <h1 className="font-serif text-4xl font-bold leading-tight text-primary md:text-5xl">
            Eat with Confidence.<br className="hidden md:block" />
            <span className="md:ml-1">Know What&apos;s Inside.</span>
          </h1>
          <p className="max-w-xl text-base font-medium text-slate-600 md:text-lg">
            Get personalized ingredient audits for your diet and lifestyle. No login, no forms —
            just paste your label or menu and get a clear, human explanation.
          </p>

          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-4">
              <PrimaryChatCta variant="onLight" />
              <Button
                variant="secondary"
                size="sm"
                type="button"
                onClick={() => {
                  const el = document.getElementById('how-it-works')
                  el?.scrollIntoView({ behavior: 'smooth' })
                }}
              >
                See how it works
              </Button>
            </div>
            <p className="max-w-lg text-sm font-medium leading-relaxed text-slate-600">
              Opens the chat — paste a label or ask in plain English. No signup.
            </p>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 shadow-sm">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              No signup. No account needed.
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 shadow-sm">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              Personalized to your diet &amp; allergies.
            </span>
          </div>
        </div>

        {/* Result screenshot */}
        <div className="flex-1">
          <Link
            href="/chat"
            className="mx-auto block max-w-md transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary/40 focus-visible:ring-offset-2 rounded-3xl"
            aria-label="Open IngreSure chat to analyze your ingredients"
          >
            <img
              src="/images/hero-result.webp"
              alt="IngreSure analyzing a food ingredient list and flagging unsafe ingredients for a Vegan user with a full plain-English explanation"
              width={448}
              height={520}
              className="h-auto w-full max-w-md rounded-3xl shadow-card"
            />
          </Link>
        </div>
      </div>
    </header>
  )
}

