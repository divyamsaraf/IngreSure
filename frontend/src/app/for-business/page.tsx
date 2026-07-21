import type { Metadata } from 'next'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import RequestAccessForm from '@/components/business/RequestAccessForm'

export const metadata: Metadata = {
  title: 'For Business | IngreSure',
  description:
    'Reduce allergen and diet mistakes in grocery, delivery, restaurants, and recipes — before they become claims, recalls, or lost customers.',
}

/**
 * Partner sales page (content + sales + risk framing).
 * Outcomes and use cases only — no status boards or engineering dump.
 */
export default function ForBusinessPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="One wrong ingredient can cost more than a refund"
        eyebrow={
          <p className="inline-flex items-center rounded-full border border-accent/25 bg-teal-50 px-3 py-1 text-xs font-semibold text-accent">
            For food businesses &amp; platforms
          </p>
        }
        description="Misclassified food — sold, served, or recommended as safe when it isn’t — drives allergic reactions, lawsuits, recalls, and customers who never return. IngreSure helps you catch the mismatch before it reaches them."
      />

      <div className="space-y-12">
        <ContentSection title="The cost of getting it wrong">
          <p>
            Food businesses lose money when labels, menus, or apps get ingredients wrong. In the
            U.S., labeling errors have been the leading cause of food recalls; industry analysis of
            2024 FDA data estimated about{' '}
            <span className="font-medium text-slate-800">$1.9 billion</span> in direct recall costs
            from label mistakes alone — most tied to undeclared allergens — before lawsuits,
            regulatory action, and brand damage.
          </p>
          <p className="mt-3">
            Restaurants and retailers also face negligence claims when a guest is told a dish is
            safe and it is not. Settlements and verdicts can reach six figures for a single
            incident; fatal undeclared-allergen cases bring far greater human and legal
            consequences.
          </p>
          <p className="mt-3">
            Diet and allergy customers are no longer a niche. They expect a reliable answer at
            checkout, on the menu, or in the app — not a guess.
          </p>
        </ContentSection>

        <ContentSection title="How IngreSure helps">
          <ul className="space-y-3">
            <li>
              <span className="font-medium text-slate-800">Flag risk before the order is final</span>
              {' '}— check ingredients against each customer&apos;s diet and allergens in the flow
              they already use.
            </li>
            <li>
              <span className="font-medium text-slate-800">Stay honest when you are unsure</span>
              {' '}— clear when it fits, clear when it doesn&apos;t, and clear when they should look
              closer — instead of a false &quot;you&apos;re fine.&quot;
            </li>
            <li>
              <span className="font-medium text-slate-800">Protect trust without owning the UI</span>
              {' '}— results appear in your product, under your brand. We stay behind the scenes.
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="Where teams use it">
          <ul className="space-y-3">
            <li>
              <span className="font-medium text-slate-800">Grocery &amp; retail apps</span>
              {' '}— warn shoppers when a product conflicts with their profile before they pay.
            </li>
            <li>
              <span className="font-medium text-slate-800">Delivery &amp; marketplaces</span>
              {' '}— flag risky basket items across many restaurants and stores in one place.
            </li>
            <li>
              <span className="font-medium text-slate-800">Restaurants &amp; meal kits</span>
              {' '}— support menu and recipe checks so guests are not left with &quot;it should be
              fine.&quot;
            </li>
            <li>
              <span className="font-medium text-slate-800">Recipe, meal-plan &amp; wellness apps</span>
              {' '}— personalize without recommending a dish someone cannot eat.
            </li>
            <li>
              <span className="font-medium text-slate-800">Corporate dining &amp; catering</span>
              {' '}— reduce incident risk when serving groups with mixed diets and allergies.
            </li>
            <li>
              <span className="font-medium text-slate-800">CPG &amp; private-label teams</span>
              {' '}— stress-test ingredient lists against diet and allergen profiles before a SKU
              goes live (partner discussion).
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="What we need from you">
          <p className="mb-3">To qualify a partnership, we ask for:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>Company name and a work email</li>
            <li>Your channel (app, checkout, menu, recipes, dining, etc.)</li>
            <li>Rough monthly volume of ingredient checks</li>
            <li>The problem you care about most (allergens, diets, both, or a specific risk)</li>
          </ul>
          <p className="mt-3">
            On a follow-up call we align on how ingredient data reaches us, which diets and
            allergens matter for your users, and how results should appear in your product.
            Pricing is usage-based and set during onboarding — no public rate card.
          </p>
        </ContentSection>

        <ContentSection title="Talk with us">
          <p>
            We take on a small number of partners at a time. This is safety-critical work — we
            onboard carefully.
          </p>
          <p className="mt-3">Share a few details below. If it looks like a fit, we&apos;ll reach out.</p>
          <div className="pt-4">
            <RequestAccessForm />
          </div>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
