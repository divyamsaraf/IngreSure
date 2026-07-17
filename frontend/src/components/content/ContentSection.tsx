import type { ReactNode } from 'react'

interface ContentSectionProps {
  title: string
  children: ReactNode
}

export function ContentSection({ title, children }: ContentSectionProps) {
  return (
    <section className="scroll-mt-24">
      <h2 className="font-serif text-xl font-semibold text-primary md:text-2xl">{title}</h2>
      <div className="mt-3 space-y-3 text-base leading-relaxed text-slate-600">{children}</div>
    </section>
  )
}
