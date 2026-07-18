import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import FaqAccordion from '@/components/content/FaqAccordion'
import { CONTACT_EMAIL, COVERAGE_DIETS_AND_ALLERGENS_SUMMARY } from '@/lib/site'

export const metadata: Metadata = {
  title: 'FAQ | IngreSure',
  description: 'Frequently asked questions about IngreSure ingredient safety checks.',
}

const FAQ_ITEMS = [
  {
    question: 'Is IngreSure a certified Halal/Kosher/Vegan verification service?',
    answer:
      'No. IngreSure provides informational guidance based on ingredient data and dietary rules, but it is not a certifying body. For products requiring formal certification (e.g. religious dietary law, legal allergen labeling), always check for official certification marks or consult the relevant certifying authority.',
  },
  {
    question: 'Can I trust the "Safe" verdict completely?',
    answer:
      'IngreSure is built on a deterministic rules engine and a growing ingredient knowledge base, and we work hard to make verdicts accurate. However, ingredient databases can have gaps, and product formulations can change. Always double check ingredient safety yourself, especially for severe allergies.',
  },
  {
    question: 'Do I need to create an account?',
    answer:
      'No. IngreSure works without login or signup. Just set your dietary profile and start pasting ingredient lists.',
  },
  {
    question: 'What happens to the ingredient lists I paste in?',
    answer:
      'We store your queries and the verdicts generated to help us improve accuracy and fix issues. We do not require or collect your name, email, or any personal account information. See our Privacy Policy for details.',
  },
  {
    question: 'Does my data get sent to an external AI company?',
    answer:
      'No. IngreSure runs its own AI model on our own infrastructure. Your ingredient queries are never sent to third-party AI providers.',
  },
  {
    question: 'Which diets and allergens does IngreSure support?',
    answer: COVERAGE_DIETS_AND_ALLERGENS_SUMMARY,
  },
  {
    question: 'I think a verdict was wrong. What should I do?',
    answer:
      'Please contact us — reports like this directly help us fix the ingredient database. Include the ingredient list and what you expected if possible.',
  },
  {
    question: 'Is there an API for businesses?',
    answer:
      "We're actively developing a B2B API for grocery, delivery, and food platforms. Contact us to learn more.",
  },
]

export default function FaqPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="Frequently Asked Questions"
        description="Quick answers about how IngreSure works, what we store, and what our verdicts mean."
      />

      <FaqAccordion items={[...FAQ_ITEMS]} />

      <p className="ds-content-body mt-10 border-t border-slate-200/80 pt-8">
        Still have questions? Email{' '}
        <a href={`mailto:${CONTACT_EMAIL}`} className="ds-link">
          {CONTACT_EMAIL}
        </a>{' '}
        or read our{' '}
        <Link href="/privacy-policy" className="ds-link">
          Privacy Policy
        </Link>
        .
      </p>
    </ContentPageLayout>
  )
}
