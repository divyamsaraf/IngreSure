import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import { CONTACT_EMAIL } from '@/lib/site'
import { buildPageMetadata } from '@/lib/seo'

export const metadata: Metadata = buildPageMetadata({
  title: 'Terms of Service',
  description: `Terms for using IngreSure ingredient and allergen safety checks. Contact: ${CONTACT_EMAIL}.`,
  path: '/terms-of-service',
})

export default function TermsOfServicePage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader title="Terms of Service" meta="Last updated: June 2026" />

      <div className="space-y-12">
        <ContentSection title="1. Acceptance of Terms">
          <p>
            By using IngreSure (&quot;the Service&quot;), you agree to these Terms of Service. If you do not
            agree, please do not use the Service.
          </p>
        </ContentSection>

        <ContentSection title="2. What IngreSure Is">
          <p>
            IngreSure provides informational guidance about whether ingredients may be compatible with a
            dietary profile (such as Vegan, Vegetarian, Halal, Jain, Hindu Vegetarian, or Kosher) or
            known allergens,
            based on an ingredient database and automated rules engine.
          </p>
        </ContentSection>

        <ContentSection title="3. Not Medical, Religious, or Certification Advice">
          <p>
            <strong className="font-semibold text-slate-800">IMPORTANT:</strong> IngreSure is an
            informational tool only. It is NOT:
          </p>
          <ul className="list-disc space-y-2 pl-5">
            <li>A medical service, and does not provide medical advice</li>
            <li>
              A substitute for consulting a doctor, allergist, or other qualified healthcare
              professional
            </li>
            <li>
              A religious or certification authority (such as a Halal or Kosher certifying body), and a
              &quot;compliant&quot; result is not a religious certification
            </li>
            <li>A guarantee of accuracy for any specific product, label, or ingredient</li>
          </ul>
          <p>
            You are solely responsible for verifying ingredient safety independently before consuming any
            product, especially in cases involving severe allergies, religious dietary law, or any other
            health-critical decision.
          </p>
        </ContentSection>

        <ContentSection title="4. No Warranty">
          <p>
            The Service is provided &quot;as is&quot; without warranties of any kind, express or implied. We do
            not guarantee that verdicts are complete, accurate, or up to date. Ingredient databases,
            product formulations, and manufacturing processes change, and errors or omissions may occur.
          </p>
        </ContentSection>

        <ContentSection title="5. Limitation of Liability">
          <p>
            To the fullest extent permitted by law, IngreSure and its creators are not liable for any
            direct, indirect, incidental, or consequential damages arising from reliance on information
            provided by the Service, including but not limited to allergic reactions, dietary violations,
            or health outcomes.
          </p>
        </ContentSection>

        <ContentSection title="6. Acceptable Use">
          <p>You agree not to:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>Use the Service for unlawful purposes</li>
            <li>Attempt to abuse, overload, or interfere with the Service&apos;s infrastructure</li>
            <li>
              Use automated systems to scrape or extract data from the Service at scale without
              permission
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="7. Changes to the Service">
          <p>
            We may modify, suspend, or discontinue any part of the Service at any time without notice.
          </p>
        </ContentSection>

        <ContentSection title="8. Changes to These Terms">
          <p>
            We may update these Terms as the product evolves. Continued use of the Service after changes
            constitutes acceptance of the updated Terms.
          </p>
        </ContentSection>

        <ContentSection title="9. Contact">
          <p>
            Questions about these Terms can be sent to{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="ds-link">
              {CONTACT_EMAIL}
            </a>
            . See also our{' '}
            <Link href="/privacy-policy" className="ds-link">
              Privacy Policy
            </Link>
            .
          </p>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
