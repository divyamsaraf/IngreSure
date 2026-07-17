import type { ReactNode } from 'react'
import HomepageFooter from '@/components/home/HomepageFooter'

interface ContentPageLayoutProps {
  children: ReactNode
}

/** Static / legal pages: matches home surface + max-width rhythm; Navbar comes from root layout. */
export default function ContentPageLayout({ children }: ContentPageLayoutProps) {
  return (
    <div className="min-h-screen bg-surface text-slate-900">
      <main className="mx-auto max-w-3xl px-6 py-12 md:py-16">{children}</main>
      <HomepageFooter />
    </div>
  )
}
