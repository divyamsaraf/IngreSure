import type { Metadata } from 'next'
import {
  BRAND,
  CONTACT_EMAIL,
  SEO_KEYWORDS,
  SITE_URL,
  absoluteUrl,
} from '@/lib/site'

type PageSeoInput = {
  title: string
  description: string
  path: string
  keywords?: readonly string[]
  noIndex?: boolean
}

function uniqueKeywords(keywords: readonly string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const k of keywords) {
    const key = k.trim().toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    out.push(k.trim())
  }
  return out
}

/** Shared Next.js Metadata for marketing / content pages. */
export function buildPageMetadata({
  title,
  description,
  path,
  keywords = SEO_KEYWORDS,
  noIndex = false,
}: PageSeoInput): Metadata {
  const url = absoluteUrl(path)
  const fullTitle = title.includes(BRAND.name) ? title : `${title} | ${BRAND.name}`

  return {
    title: fullTitle,
    description,
    keywords: uniqueKeywords(keywords),
    authors: [{ name: BRAND.name, url: SITE_URL }],
    creator: BRAND.name,
    publisher: BRAND.name,
    category: 'food safety',
    alternates: { canonical: url },
    robots: noIndex
      ? { index: false, follow: false }
      : {
          index: true,
          follow: true,
          googleBot: {
            index: true,
            follow: true,
            'max-image-preview': 'large',
            'max-snippet': -1,
            'max-video-preview': -1,
          },
        },
    openGraph: {
      type: 'website',
      locale: 'en_US',
      url,
      siteName: BRAND.name,
      title: fullTitle,
      description,
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description,
    },
  }
}

/** Root layout defaults (home). */
export function buildRootMetadata(): Metadata {
  return {
    metadataBase: new URL(SITE_URL),
    title: {
      default: BRAND.seoTitleDefault,
      template: `%s | ${BRAND.name}`,
    },
    description: BRAND.seoDescriptionDefault,
    applicationName: BRAND.name,
    keywords: uniqueKeywords(SEO_KEYWORDS),
    authors: [{ name: BRAND.name, url: SITE_URL }],
    creator: BRAND.name,
    publisher: BRAND.name,
    formatDetection: { email: false, address: false, telephone: false },
    alternates: { canonical: absoluteUrl('/') },
    manifest: '/manifest.webmanifest',
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-image-preview': 'large',
        'max-snippet': -1,
        'max-video-preview': -1,
      },
    },
    openGraph: {
      type: 'website',
      locale: 'en_US',
      url: absoluteUrl('/'),
      siteName: BRAND.name,
      title: BRAND.seoTitleDefault,
      description: BRAND.seoDescriptionDefault,
    },
    twitter: {
      card: 'summary_large_image',
      title: BRAND.seoTitleDefault,
      description: BRAND.seoDescriptionDefault,
    },
    other: {
      'contact:email': CONTACT_EMAIL,
    },
  }
}

/** JSON-LD graph for Organization + WebSite + SoftwareApplication. */
export function buildSiteJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': `${SITE_URL}/#organization`,
        name: BRAND.name,
        url: SITE_URL,
        email: CONTACT_EMAIL,
        description: BRAND.seoDescriptionDefault,
        sameAs: [],
        knowsAbout: uniqueKeywords(SEO_KEYWORDS).slice(0, 40),
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: BRAND.name,
        description: BRAND.seoDescriptionDefault,
        publisher: { '@id': `${SITE_URL}/#organization` },
        inLanguage: 'en-US',
        keywords: uniqueKeywords(SEO_KEYWORDS).join(', '),
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: `${SITE_URL}/chat`,
          },
          'query-input': 'required name=search_term_string',
        },
      },
      {
        '@type': 'SoftwareApplication',
        '@id': `${SITE_URL}/#app`,
        name: BRAND.name,
        applicationCategory: 'HealthApplication',
        operatingSystem: 'Web',
        url: absoluteUrl('/chat'),
        description: BRAND.seoDescriptionDefault,
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
        provider: { '@id': `${SITE_URL}/#organization` },
      },
    ],
  }
}
