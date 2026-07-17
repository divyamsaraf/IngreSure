import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import FaqAccordion from '@/components/content/FaqAccordion'
import { CONTACT_EMAIL } from '@/lib/site'

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
    answer:
      'Currently: Vegan, Halal, Jain, Hindu Vegetarian, and Kosher dietary profiles, along with 14+ common allergens. We are actively expanding this list.',
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
] as const

export default function FaqPage() {
  return (
    <ContentPageLayout>
      <header className="mb-10 border-b border-slate-200 pb-8">
        <h1 className="font-serif text-3xl font-bold text-primary md:text-4xl">
          Frequently Asked Questions
        </h1>
        <p className="mt-3 text-base leading-relaxed text-slate-600">
          Quick answers about how IngreSure works, what we store, and what our verdicts mean.
        </p>
      </header>

      <FaqAccordion items={[...FAQ_ITEMS]} />

      <p className="mt-10 text-base leading-relaxed text-slate-600">
        Still have questions? Email{' '}
        <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-secondary hover:underline">
          {CONTACT_EMAIL}
        </a>{' '}
        or read our{' '}
        <Link href="/privacy-policy" className="font-medium text-secondary hover:underline">
          Privacy Policy
        </Link>
        .
      </p>
    </ContentPageLayout>
  )
}
