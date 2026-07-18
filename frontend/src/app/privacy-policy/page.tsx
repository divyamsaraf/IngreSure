import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import { CONTACT_EMAIL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'Privacy Policy | IngreSure',
  description: 'How IngreSure collects and uses data when you check ingredient safety.',
}

export default function PrivacyPolicyPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader title="Privacy Policy" meta="Last updated: June 2026" />

      <div className="space-y-12">
        <ContentSection title="1. Overview">
          <p>
            IngreSure (&quot;we&quot;, &quot;us&quot;) provides ingredient safety guidance based on dietary and
            allergen profiles. This policy explains what we collect when you use the app and why.
          </p>
        </ContentSection>

        <ContentSection title="2. No Account Required">
          <p>
            IngreSure does not require you to create an account or log in. You do not provide a name,
            email, or password to use the core product.
          </p>
        </ContentSection>

        <ContentSection title="3. What We Collect">
          <p>When you use the Grocery Assistant, we collect:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>The ingredient lists or questions you submit</li>
            <li>The verdicts and responses generated for you</li>
            <li>
              A randomly generated, anonymous identifier (not tied to your name, email, or any personal
              account) used to associate your queries within a session and help us debug issues
            </li>
            <li>
              Basic usage analytics via Vercel Analytics (e.g. page views, general device/browser type),
              which does not include the content of your ingredient queries
            </li>
          </ul>
        </ContentSection>

        <ContentSection title="4. Why We Collect It">
          <p>We use this data solely to:</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>Improve the accuracy of our ingredient database and dietary rules engine</li>
            <li>Identify and fix errors in verdicts</li>
            <li>Understand which features are used so we can improve the product</li>
          </ul>
          <p>
            We do not sell this data. We do not use it for advertising. We do not share it with third
            parties for marketing purposes.
          </p>
        </ContentSection>

        <ContentSection title="5. How Processing Works">
          <p>
            All ingredient analysis is performed using our own self-hosted AI model (Llama 3.2, run on
            our own infrastructure). Your ingredient queries are NOT sent to third-party AI providers
            such as OpenAI, Anthropic, or Google. This means your data stays within systems we directly
            control.
          </p>
        </ContentSection>

        <ContentSection title="6. Data Retention">
          <p>
            We currently retain submitted queries and generated verdicts to support ongoing product
            improvement. We do not currently have an automatic deletion schedule. We are working on
            formal retention limits and will update this policy when they are in place. If you would
            like your data removed earlier, contact us using the details below.
          </p>
        </ContentSection>

        <ContentSection title="7. Your Choices">
          <p>
            Because no account or login is required, there is no personal profile tied to your identity
            to access or delete in the traditional sense. If you have concerns about a specific
            submission, you can contact us with approximate date/time of use and we will make reasonable
            efforts to locate and remove the associated record.
          </p>
        </ContentSection>

        <ContentSection title="8. Children&apos;s Privacy">
          <p>
            IngreSure is not directed at children under 13, and we do not knowingly collect data from
            children under 13.
          </p>
        </ContentSection>

        <ContentSection title="9. Changes to This Policy">
          <p>
            We may update this Privacy Policy as the product evolves. Material changes will be reflected
            with an updated &quot;Last updated&quot; date above.
          </p>
        </ContentSection>

        <ContentSection title="10. Contact">
          <p>
            Questions about this policy can be sent to{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="ds-link">
              {CONTACT_EMAIL}
            </a>
            . You can also read our{' '}
            <Link href="/terms-of-service" className="ds-link">
              Terms of Service
            </Link>
            .
          </p>
        </ContentSection>
      </div>
    </ContentPageLayout>
  )
}
