import type { Metadata } from 'next'
import Link from 'next/link'
import ContentPageLayout from '@/components/content/ContentPageLayout'
import { ContentPageHeader } from '@/components/content/ContentPageHeader'
import { ContentSection } from '@/components/content/ContentSection'
import { BRAND, CONTACT_EMAIL, COVERAGE } from '@/lib/site'
import { buildPageMetadata } from '@/lib/seo'

export const metadata: Metadata = buildPageMetadata({
  title: 'About IngreSure',
  description:
    'Why we built IngreSure: clear diet and allergen answers for grocery lists and labels — rules decide safety, not AI guesswork. No signup required.',
  path: '/about',
})

/**
 * About page — mission and trust for people (and a light path for platforms).
 * Content / editorial voice; no status boards or eng changelog.
 */
export default function AboutPage() {
  return (
    <ContentPageLayout>
      <ContentPageHeader
        title="About IngreSure"
        description={`${BRAND.oneLiner}`}
      />

      <div className="ds-content-body space-y-10">
        <ContentSection title="Why this exists">
          <p>
            For millions of people, eating is not casual. An allergy can mean a trip to the ER. A
            religious or ethical diet can mean carefully reading every label. Getting it wrong is not
            a small inconvenience — it can be a medical emergency, a broken trust, or a meal someone
            cannot share with the people they love.
          </p>
          <p className="mt-3">
            The wider food world feels that cost too. Label mistakes — especially undeclared allergens
            — have been the leading driver of U.S. food recalls, with industry analysis putting direct
            recall costs from labeling errors alone in the billions in a single year. Restaurants and
            retailers face claims when a guest is told something is safe and it is not.
          </p>
          <p className="mt-3">
            Most people still do the hard part alone: phone flashlight in a grocery aisle, three
            different names for the same additive, and a confident internet answer that cannot show
            its work. IngreSure exists to close that gap — for the person checking a label, and for
            the products that want to help them.
          </p>
        </ContentSection>

        <ContentSection title="What we do">
          <p>
            Set a simple profile — your diet and allergens — then paste a grocery list, a menu, or a
            product label. We return a clear verdict on what fits and what doesn&apos;t, in plain
            language.
          </p>
          <p className="mt-3">
            We support {COVERAGE.dietFrameworks.length} diet frameworks (
            {COVERAGE.dietFrameworks.join(', ')}) and major allergen checks. When we are not sure, we
            say so — we would rather tell you to look closer than invent a false &quot;you&apos;re
            fine.&quot;
          </p>
        </ContentSection>

        <ContentSection title="How we decide">
          <p>
            The safety call comes from explicit rules over curated food knowledge — not from an AI
            guessing. Language can help parse a messy label and explain the result; it does not get
            to override the rules. If those ever disagree, the rules win.
          </p>
          <p className="mt-3">
            That choice is slower to build than &quot;ask a chatbot.&quot; It is also why we are
            willing to put this in front of people who actually need a defensible answer.
          </p>
        </ContentSection>

        <ContentSection title="Privacy">
          <p>
            No account required. You can set a profile and start checking labels without handing over
            your email. We run our own language model on infrastructure we control, rather than
            sending your ingredient queries to third-party AI providers by default.
          </p>
        </ContentSection>

        <ContentSection title="Why I built this">
          <p>
            The originating moment was standing in a grocery aisle with a phone flashlight and a
            half-remembered list of what a vegan friend could eat — staring at an ingredient panel
            that used three different names for the same animal-derived additive. I had already done
            this dance for allergens and for religious dietary rules. Every time, the internet
            answered with a confident paragraph that could not show its work.
          </p>
          <p className="mt-3">
            Coverage grows every week and is not exhaustive. Some edge cases still land in
            &quot;Depends&quot; when we refuse to guess. If a verdict looks wrong, that report is how
            we improve — we want to hear from you.
          </p>
        </ContentSection>

        <ContentSection title="For companies">
          <p>
            If you run a grocery app, delivery marketplace, restaurant, meal kit, or recipe product,
            the same problem shows up as lost trust, support load, and real liability when food is
            misclassified. We work with a small number of platform partners —{' '}
            <Link href="/for-business" className="ds-link">
              see For Business
            </Link>
            .
          </p>
        </ContentSection>

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
