import type { ReactNode } from 'react'
import HomepageFooter from '@/components/home/HomepageFooter'

interface ContentPageLayoutProps {
  children: ReactNode
}

/**
 * Shared shell for About / FAQ / legal / For Business.
 * Soft document panel on surface wash — same atmosphere as landing/chat.
 */
export default function ContentPageLayout({ children }: ContentPageLayoutProps) {
  return (
    <div className="relative flex min-h-screen flex-col bg-surface text-slate-900">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_18%_0%,rgba(15,118,110,0.08),transparent_52%),radial-gradient(ellipse_at_100%_70%,rgba(15,23,42,0.03),transparent_45%)]"
        aria-hidden
      />
      <main className="relative mx-auto w-full max-w-3xl flex-1 px-4 pb-16 pt-10 sm:px-6 md:pb-20 md:pt-14">
        <article className="rounded-2xl border border-slate-200/70 bg-white/85 px-5 py-8 shadow-[0_4px_24px_rgba(15,23,42,0.04)] backdrop-blur-sm sm:px-8 sm:py-10 md:px-10 md:py-12">
          {children}
        </article>
      </main>
      <div className="relative mt-auto">
        <HomepageFooter />
      </div>
    </div>
  )
}
