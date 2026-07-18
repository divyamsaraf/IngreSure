'use client'

import { PrimaryChatCta } from '@/components/home/PrimaryChatCta'
import TrustSignals from '@/components/home/TrustSignals'
import HeroProductDemo from '@/components/home/HeroProductDemo'
import { BRAND } from '@/lib/site'

export default function HeroSection() {
  return (
    <header className="relative overflow-hidden border-b border-slate-200/80 bg-surface">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_18%_0%,rgba(15,118,110,0.09),transparent_50%),radial-gradient(ellipse_at_100%_30%,rgba(15,23,42,0.035),transparent_40%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-y-0 right-0 hidden w-[55%] opacity-[0.18] md:block"
        style={{
          backgroundImage: 'url(/images/hero-atmosphere.webp)',
          backgroundSize: 'cover',
          backgroundPosition: 'center right',
          maskImage: 'linear-gradient(to left, black 20%, transparent 95%)',
          WebkitMaskImage: 'linear-gradient(to left, black 20%, transparent 95%)',
        }}
        aria-hidden
      />

      <div className="relative mx-auto max-w-6xl px-6 pb-10 pt-12 md:pb-12 md:pt-14">
        <div className="grid gap-10 md:grid-cols-12 md:items-center md:gap-10">
          <div className="md:col-span-5">
            <p className="font-display text-[1.65rem] font-semibold tracking-tight text-primary md:text-[1.85rem]">
              {BRAND.name}
            </p>
            <h1 className="mt-3 font-display text-[2.35rem] font-bold leading-[1.08] tracking-tight text-primary md:text-5xl lg:text-[3.15rem]">
              Eat with confidence.
              <span className="mt-1 block text-accent">Know what&apos;s inside.</span>
            </h1>
            <p className="mt-4 max-w-md text-[15px] leading-relaxed text-slate-600 md:text-base">
              Paste a label or menu. Get Safe / Avoid / Depends for your diet and allergens — rules
              decide safety; language only explains.
            </p>

            <div className="mt-7 flex flex-col gap-2.5">
              <PrimaryChatCta variant="onLight" />
              <p className="text-sm text-slate-500">
                Opens the chat · No signup ·{' '}
                <button
                  type="button"
                  className="cursor-pointer font-medium text-accent underline-offset-2 hover:underline"
                  onClick={() => {
                    document
                      .getElementById('how-verdict-works')
                      ?.scrollIntoView({ behavior: 'smooth' })
                  }}
                >
                  How the verdict works
                </button>
              </p>
            </div>
          </div>

          <div className="md:col-span-7">
            <HeroProductDemo />
          </div>
        </div>

        {/* Full width under both columns — readable on every breakpoint */}
        <TrustSignals className="mt-10 border-t border-slate-200/80 pt-8" />
      </div>
    </header>
  )
}
