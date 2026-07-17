import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { CONTACT_EMAIL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'About | IngreSure',
  description: 'What IngreSure is, how it works, and why we built it.',
}

export default function AboutPage() {
  return (
    <ContentPageLayout>
      <header className="mb-10 border-b border-slate-200 pb-8">
        <h1 className="font-serif text-3xl font-bold text-primary md:text-4xl">About IngreSure</h1>
      </header>

      <div className="space-y-6 text-base leading-relaxed text-slate-600">
        <p>
          IngreSure is for people who manage dietary restrictions, allergies, or religious dietary law
          and are tired of manually parsing ingredient labels. Paste a grocery list, a menu, or a
          product label — and get a clear verdict on what fits your profile and what doesn&apos;t, in
          plain language.
        </p>
        <p>
          Under the hood, a deterministic rules engine cross-checks each ingredient against your dietary
          and allergen rules. That engine is backed by a knowledge base merged from Open Food Facts, USDA
          FoodData Central, Wikidata, and official E-number classifications. A self-hosted AI model
          helps parse messy input and explain results — but the safety call itself comes from explicit
          rules, not guesswork.
        </p>
        <p>
          Privacy is part of the design: we run our own model on infrastructure we control rather than
          sending your ingredient queries to third-party AI providers. No account required — you can
          set a profile and start checking labels without handing over your email.
        </p>
        <p>
          IngreSure is an actively evolving project. The ingredient database grows week by week, and
          reports from real users — especially when a verdict looks wrong — directly shape what we fix
          next. If something doesn&apos;t look right, we want to hear from you.
        </p>

        {/* ADD FOUNDER BIO HERE IF DESIRED */}

        <p className="pt-4">
          <Link href="/chat" className="font-medium text-secondary hover:underline">
            Try the Grocery Assistant
          </Link>
          {' · '}
          <Link href="/faq" className="font-medium text-secondary hover:underline">
            FAQ
          </Link>
          {' · '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-secondary hover:underline">
            {CONTACT_EMAIL}
          </a>
        </p>
      </div>
    </ContentPageLayout>
  )
}
