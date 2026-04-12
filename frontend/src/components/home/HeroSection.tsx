'use client'

import { ShieldCheck, CheckCircle, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { PrimaryChatCta } from '@/components/home/PrimaryChatCta'

export default function HeroSection() {
  return (
    <header className="relative overflow-hidden bg-gradient-to-br from-slate-100 via-white to-slate-50">
      <div className="absolute -left-32 top-10 h-64 w-64 rounded-full bg-emerald-100 opacity-40 blur-3xl" />
      <div className="absolute -right-24 bottom-0 h-72 w-72 rounded-full bg-lime-100 opacity-40 blur-3xl" />

      <div className="relative mx-auto flex max-w-6xl flex-col gap-10 px-6 py-16 md:flex-row md:items-center md:py-20">
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

        {/* Illustration column */}
        <div className="flex-1">
          <div className="mx-auto max-w-md rounded-3xl bg-white/80 p-5 shadow-xl shadow-slate-200 ring-1 ring-slate-100 backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100">
                  <MessageCircle className="h-6 w-6 text-emerald-700" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-700">IngreSure Assistant</p>
                  <p className="text-[11px] text-slate-400">Deterministic safety engine</p>
                </div>
              </div>
              <div className="flex gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                <span className="h-2 w-2 rounded-full bg-rose-400" />
              </div>
            </div>

            <div className="space-y-3 text-[13px]">
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-slate-900 px-3 py-2 text-slate-50 shadow-sm">
                  I&apos;m Vegan and allergic to peanuts. Is this safe?
                </div>
              </div>
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-slate-50 px-3 py-2 text-slate-700 shadow-sm">
                  I&apos;ve checked your ingredients. You have{' '}
                  <span className="font-semibold text-emerald-700">5 safe ingredients</span>{' '}
                  and <span className="font-semibold text-rose-600">1 ingredient to avoid</span>.
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700">
                  Vegan
                </span>
                <span className="rounded-full bg-sky-50 px-3 py-1 font-medium text-sky-700">
                  Halal
                </span>
                <span className="rounded-full bg-rose-50 px-3 py-1 font-medium text-rose-700">
                  Allergens: Peanuts
                </span>
              </div>
            </div>
          </div>

          <p className="mt-4 text-center text-[11px] text-slate-400">
            Static demo. Live chat runs in your browser with your own profile.
          </p>
        </div>
      </div>
    </header>
  )
}

