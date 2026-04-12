import { PrimaryChatCta } from '@/components/home/PrimaryChatCta'

export default function FinalCtaSection() {
  return (
    <section className="px-6 py-16 md:py-20 bg-slate-900 text-slate-50">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 md:flex-row">
        <div className="max-w-xl space-y-2 text-center md:text-left">
          <h2 className="font-serif text-3xl font-bold">
            Ready to check your first label?
          </h2>
          <p className="text-sm md:text-base text-slate-300">
            Start a grocery audit in seconds. Paste any ingredient list and get a clear, personalized answer — no signup required.
          </p>
        </div>
        <div className="flex flex-col items-center gap-3 md:items-end">
          <PrimaryChatCta variant="onDark" />
          <p className="max-w-xs text-center text-xs text-slate-400 md:text-right">
            Opens the chat • No signup • Works on your phone
          </p>
        </div>
      </div>
    </section>
  )
}
