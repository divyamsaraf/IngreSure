import type { Metadata } from 'next'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import RequestAccessForm from '@/components/business/RequestAccessForm'

export const metadata: Metadata = {
  title: 'For Business | IngreSure',
  description:
    'Help your customers shop and eat with confidence. IngreSure adds diet and allergen checks to checkout, menus, and recipes.',
}

/**
 * Partner-facing sales page — outcomes only.
 * No product status boards, no engineering internals, no feature dump.
 */
export default function ForBusinessPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="Help every customer eat with confidence"
        eyebrow={
          <p className="inline-flex items-center rounded-full border border-accent/25 bg-teal-50 px-3 py-1 text-xs font-semibold text-accent">
            For food platforms
          </p>
        }
        description="IngreSure sits inside your product and tells each user whether an item fits their diet and allergens — before they buy, cook, or get disappointed."
      />

      <div className="space-y-12">
        <ContentSection title="The opportunity">
          <p>
            Millions of people follow a diet or manage an allergy. Most still guess from labels and
            hope for the best. When they get it wrong, they leave a bad review, open a ticket, or
            never come back.
          </p>
          <p className="mt-3">
            Platforms that answer this clearly win trust — and keep the customer.
          </p>
        </ContentSection>

        <ContentSection title="What IngreSure does for you">
          <ul className="space-y-3">
            <li>
              <span className="font-medium text-slate-800">Protect the moments that matter</span>
              {' '}— checkout, menu browse, and recipe save — with a plain answer: this works for
              them, it doesn&apos;t, or they should take a closer look.
            </li>
            <li>
              <span className="font-medium text-slate-800">Cover the diets your market cares about</span>
              {' '}— including vegan, vegetarian, religious diets, and common allergens.
            </li>
            <li>
              <span className="font-medium text-slate-800">Stay in control of the experience</span>
              {' '}— you keep your brand and UI; we handle the safety check behind the scenes.
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="Built for">
          <ul className="list-disc space-y-2 pl-5">
            <li>Grocery and delivery apps</li>
            <li>Restaurants and meal kits</li>
            <li>Recipe, meal-planning, and wellness products</li>
          </ul>
        </ContentSection>

        <ContentSection title="How it works">
          <ol className="list-decimal space-y-2.5 pl-5">
            <li>Your product sends an ingredient list.</li>
            <li>We check it against that customer&apos;s diet and allergens.</li>
            <li>You show a clear result in your own design.</li>
          </ol>
        </ContentSection>

        <ContentSection title="Talk with us">
          <p>
            We&apos;re taking on a small number of platform partners. Pricing is usage-based and
            set during onboarding — no public rate card yet.
          </p>
          <p className="mt-3">
            Share a bit about your company. If it&apos;s a fit, we&apos;ll reach out.
          </p>
          <div className="pt-4">
            <RequestAccessForm />
          </div>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
