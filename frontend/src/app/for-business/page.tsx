import type { Metadata } from 'next'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import RequestAccessForm from '@/components/business/RequestAccessForm'
import { COVERAGE } from '@/lib/site'

export const metadata: Metadata = {
  title: 'For Business | IngreSure',
  description:
    'Add allergen and dietary safety to checkout, menus, and recipes — clear Safe / Avoid / Depends answers your users can trust.',
}

export default function ForBusinessPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="Dietary safety your users can trust"
        eyebrow={
          <p className="inline-flex items-center rounded-full border border-accent/25 bg-teal-50 px-3 py-1 text-xs font-semibold text-accent">
            Early partner access
          </p>
        }
        description="Help shoppers, diners, and cooks know what fits their diet and allergens — inside the product they already use."
      />

      <div className="space-y-12">
        <ContentSection title="Why platforms partner with us">
          <ul className="space-y-3 text-[15px] leading-[1.65] text-slate-600 md:text-base">
            <li>
              <span className="font-medium text-slate-800">Fewer support tickets &amp; chargebacks</span>
              {' '}— clear answers before purchase, not after someone gets sick or breaks a diet.
            </li>
            <li>
              <span className="font-medium text-slate-800">Trust that scales</span>
              {' '}— {COVERAGE.dietCountLabel.toLowerCase()} and major allergen coverage, with verdicts
              that stay honest when something is unknown.
            </li>
            <li>
              <span className="font-medium text-slate-800">Built for product teams</span>
              {' '}— ingredients in, structured Safe / Avoid / Needs review out. You keep the UX;
              we own the hard safety logic.
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="Where it fits">
          <ul className="list-disc space-y-2.5 pl-5 text-[15px] leading-[1.65] text-slate-600 md:text-base">
            <li>Grocery &amp; delivery checkout</li>
            <li>Restaurant &amp; meal-kit menus</li>
            <li>Recipes, meal planners, and health apps</li>
          </ul>
        </ContentSection>

        <ContentSection title="How it works">
          <ol className="list-decimal space-y-2.5 pl-5 text-[15px] leading-[1.65] text-slate-600 md:text-base">
            <li>Send us the ingredient list from an order, menu item, or recipe.</li>
            <li>We check it against your user&apos;s diet and allergens.</li>
            <li>You show a simple result — safe, avoid, or needs a closer look.</li>
          </ol>
        </ContentSection>

        <ContentSection title="Partner status">
          <p className="text-[15px] leading-[1.65] text-slate-600 md:text-base">
            Core safety engine is live. Partner API access is opening with a small group of
            platforms — usage-based pricing, set together during onboarding.
          </p>
        </ContentSection>

        <ContentSection title="Request early access">
          <p className="text-[15px] leading-[1.65] text-slate-600 md:text-base">
            Tell us what you&apos;re building. We&apos;ll follow up if it&apos;s a fit.
          </p>
          <div className="pt-3">
            <RequestAccessForm />
          </div>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
