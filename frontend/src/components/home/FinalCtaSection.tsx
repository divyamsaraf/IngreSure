import { PrimaryChatCta } from '@/components/home/PrimaryChatCta'

export default function FinalCtaSection() {
  return (
    <section className="relative overflow-hidden px-6 py-14 md:py-16">
      <div
        className="absolute inset-0 bg-gradient-to-br from-primary via-[#0c4a45] to-accent"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.35)_1px,transparent_0)] [background-size:28px_28px]"
        aria-hidden
      />
      <div className="relative mx-auto flex max-w-6xl flex-col items-center gap-6 text-center md:flex-row md:items-center md:justify-between md:text-left">
        <div className="max-w-xl space-y-2">
          <h2 className="font-display text-3xl font-bold text-white md:text-4xl">
            Ready when you are
          </h2>
          <p className="text-sm text-teal-50/90 md:text-base">
            One paste. A clear audit. No account, no waitlist.
          </p>
        </div>
        <div className="flex flex-col items-center gap-3 md:items-end">
          {/* CTA #2 of 2 — closing conversion; same destination, closing intent */}
          <PrimaryChatCta
            variant="onDark"
            label="Check a label free"
            aria-label="Check a label free — opens the ingredient chat, no signup required"
          />
          <p className="text-xs text-teal-100/70">Works on your phone · Profile stays local</p>
        </div>
      </div>
    </section>
  )
}
