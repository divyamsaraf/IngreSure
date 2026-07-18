import type { ReactNode } from 'react'

interface ContentSectionProps {
  title: string
  children: ReactNode
}

export function ContentSection({ title, children }: ContentSectionProps) {
  return (
    <section className="scroll-mt-24">
      <h2 className="font-display text-xl font-semibold tracking-tight text-primary md:text-[1.35rem]">
        {title}
      </h2>
      <div className="ds-content-body mt-3.5 space-y-3.5">{children}</div>
    </section>
  )
}
