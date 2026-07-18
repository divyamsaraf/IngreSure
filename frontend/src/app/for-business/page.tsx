import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import RequestAccessForm from '@/components/business/RequestAccessForm'
import { COVERAGE } from '@/lib/site'

export const metadata: Metadata = {
  title: 'For Business | IngreSure',
  description:
    'Allergen and dietary compliance for platforms — checkout, menu, and recipe flows. Early B2B partner access.',
}

type StatusKind = 'live' | 'in-development' | 'planned'

const STATUS_META: Record<
  StatusKind,
  { label: string; dot: string; text: string }
> = {
  live: {
    label: 'Live',
    dot: 'bg-safe',
    text: 'text-emerald-800',
  },
  'in-development': {
    label: 'In development',
    dot: 'bg-depends',
    text: 'text-amber-800',
  },
  planned: {
    label: 'Planned',
    dot: 'bg-slate-300',
    text: 'text-slate-600',
  },
}

function StatusRow({
  status,
  children,
}: {
  status: StatusKind
  children: ReactNode
}) {
  const meta = STATUS_META[status]
  return (
    <li className="flex items-start gap-3 text-[15px] leading-[1.65] text-slate-600 md:text-base">
      <span
        className={`mt-2 h-2 w-2 shrink-0 rounded-full ${meta.dot}`}
        aria-hidden
      />
      <span>
        <span className={`font-semibold ${meta.text}`}>{meta.label}</span>
        <span className="text-slate-400"> — </span>
        {children}
      </span>
    </li>
  )
}

export default function ForBusinessPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="IngreSure for platforms"
        eyebrow={
          <p className="inline-flex items-center rounded-full border border-accent/25 bg-teal-50 px-3 py-1 text-xs font-semibold text-accent">
            Onboarding early B2B partners
          </p>
        }
        description="Allergen and dietary compliance, built into your checkout, menu, or recipe flow — not bolted on after the fact."
      />

      <div className="space-y-12">
        <ContentSection title="Status">
          <ul className="space-y-3.5" aria-label="Product and API status">
            <StatusRow status="live">
              Ingredient resolution engine, covering {COVERAGE.allergenEngineRuleCount} allergen-related
              rules and {COVERAGE.dietFrameworks.length} dietary frameworks (
              {COVERAGE.dietFrameworks.join(', ')})
            </StatusRow>
            <StatusRow status="in-development">REST API for partner integration</StatusRow>
            <StatusRow status="planned">Multi-region data coverage (EU, Canada, India)</StatusRow>
            <StatusRow status="planned">SLA and rate-limit tiers for production traffic</StatusRow>
          </ul>
        </ContentSection>

        <ContentSection title="How it fits into your product">
          <ol className="list-decimal space-y-2.5 pl-5">
            <li>Your users&apos; ingredient data goes in — a delivery order, a menu item, a recipe.</li>
            <li>IngreSure resolves it against dietary rules and allergen data, not keyword matching.</li>
            <li>
              You get a structured verdict back — safe, avoid, or needs review — to show your users
              directly.
            </li>
          </ol>
        </ContentSection>

        <ContentSection title="Pricing">
          <p>
            <span className="font-medium text-slate-800">Indicative pricing</span> — final tiers will
            be set during early access, based on real partner usage.
          </p>
          <p>Usage-based pricing, discussed directly with early partners.</p>
        </ContentSection>

        <ContentSection title="Talk to us about early access">
          <p>
            We&apos;re onboarding a small number of partners while the API stabilizes. Tell us about
            your use case and we&apos;ll follow up directly.
          </p>
          <div className="pt-3">
            <RequestAccessForm />
          </div>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
