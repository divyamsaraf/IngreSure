import type { Metadata } from 'next'
import ChatInterface from '@/components/chat/ChatInterface'
import { SEO_KEYWORDS_CHAT } from '@/lib/site'
import { buildPageMetadata } from '@/lib/seo'

export const metadata: Metadata = buildPageMetadata({
  title: 'Grocery Assistant — Check ingredients for your diet & allergies',
  description:
    'Paste a grocery list, menu, or product label. Get Safe / Avoid / Depends for vegan, vegetarian, Halal, Kosher, Jain, and common allergens — free, no signup.',
  path: '/chat',
  keywords: SEO_KEYWORDS_CHAT,
})

export default function ChatPage() {
  return (
    <div className="relative flex h-[calc(100vh-64px)] justify-center overflow-hidden bg-surface">
      {/* Soft atmosphere — matches landing, keeps chat calm */}
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(15,118,110,0.07),transparent_55%),radial-gradient(ellipse_at_100%_100%,rgba(15,23,42,0.03),transparent_45%)]"
        aria-hidden
      />
      <div className="relative flex min-h-0 w-full max-w-3xl flex-1 flex-col px-2 py-2 md:px-4 md:py-3">
        <ChatInterface
          apiEndpoint="/api/chat?mode=grocery"
          title="Grocery Assistant"
          subtitle="Rules decide safety · language explains"
          suggestions={[
            'Ingredients: Sugar, Gelatin, Citric Acid, Natural Flavors, Carnauba Wax',
            'Ingredients: Milk, Egg, Soy, Wheat, Peanut. I have a peanut allergy.',
            'Is this Halal? Ingredients: Sugar, Gelatin, Water, Natural Flavors',
          ]}
        />
      </div>
    </div>
  )
}
