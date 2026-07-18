import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import { CONTACT_EMAIL } from '@/lib/site'

export const metadata: Metadata = {
  title: 'About | IngreSure',
  description: 'What IngreSure is, how it works, and why we built it.',
}

export default function AboutPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader title="About IngreSure" />

      <div className="ds-content-body space-y-5">
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

        <div className="pt-4">
        <ContentSection title="Why I built this">
          <p>
            The originating moment was standing in a grocery aisle with a phone flashlight and a
            half-remembered list of what a vegan friend could eat — staring at an ingredient panel that
            used three different names for the same animal-derived additive. I had already done this
            dance for allergens and for religious dietary rules. Every time, the internet answered with
            a confident paragraph that could not show its work. That gap — between a chatty answer and
            a defensible one — is what IngreSure exists to close.
          </p>
          <p>
            The technical decision that followed was non-negotiable: the safety verdict itself must never
            come from the language model. The LLM can parse a messy pasted label and write the
            explanation in plain English, but Safe / Avoid / Depends is produced by an explicit rules
            engine over a curated ingredient ontology. If those disagree someday, the rules win. That
            split is slower to build than &quot;ask a model,&quot; and it is the reason I trust putting
            this in front of people who actually need the answer.
          </p>
          <p>
            What is still in progress is honest too: coverage grows every week and is not exhaustive;
            some edge-case ingredients still land in Depends when we refuse to guess; the partner API
            is in early access rather than production-hardened with SLAs. If you catch a wrong call,
            that report is how the ontology improves — not a support ticket we hope you forget.
          </p>
        </ContentSection>
        </div>

        <p className="border-t border-slate-200/80 pt-8 text-[15px]">
          <Link href="/chat" className="ds-link">
            Try the Grocery Assistant
          </Link>
          <span className="mx-2 text-slate-300" aria-hidden>
            ·
          </span>
          <Link href="/for-business" className="ds-link">
            For Business
          </Link>
          <span className="mx-2 text-slate-300" aria-hidden>
            ·
          </span>
          <Link href="/faq" className="ds-link">
            FAQ
          </Link>
          <span className="mx-2 text-slate-300" aria-hidden>
            ·
          </span>
          <a href={`mailto:${CONTACT_EMAIL}`} className="ds-link">
            {CONTACT_EMAIL}
          </a>
        </p>
      </div>
    </ContentPageLayout>
  )
}
