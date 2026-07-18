import type { ReactNode } from 'react'

interface ContentPageHeaderProps {
  title: string
  /** Optional line under the title (e.g. “Last updated”). */
  meta?: string
  /** Optional intro / description under the title. */
  description?: ReactNode
  /** Optional eyebrow / pill above the title. */
  eyebrow?: ReactNode
}

/** Shared page title block — visual only; pass existing copy unchanged. */
export function ContentPageHeader({ title, meta, description, eyebrow }: ContentPageHeaderProps) {
  return (
    <header className="mb-10 border-b border-slate-200/80 pb-8 md:mb-12 md:pb-10">
      {eyebrow ? <div className="mb-4">{eyebrow}</div> : null}
      <h1 className="font-display text-[1.875rem] font-bold leading-[1.15] tracking-tight text-primary md:text-[2.375rem]">
        {title}
      </h1>
      {meta ? (
        <p className="mt-2.5 text-[13px] font-medium tracking-wide text-slate-500">{meta}</p>
      ) : null}
      {description ? (
        <div className="mt-4 max-w-xl text-[15px] leading-relaxed text-slate-600 md:text-base md:leading-[1.65]">
          {description}
        </div>
      ) : null}
    </header>
  )
}
