import Link from 'next/link'
import { BRAND, CONTACT_EMAIL } from '@/lib/site'

const footerLinkClass = 'text-slate-500 transition-colors hover:text-accent'

export default function HomepageFooter() {
  return (
    <footer className="border-t border-slate-200/80 bg-surface/80 py-11 text-sm backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm space-y-1.5">
          <p className="font-display text-[15px] font-semibold tracking-tight text-primary">
            {BRAND.name}
          </p>
          <p className="text-[13px] leading-relaxed text-slate-500">{BRAND.oneLiner}</p>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2.5 text-[13px]" aria-label="Footer">
          <Link href="/about" className={footerLinkClass}>
            About
          </Link>
          <Link href="/faq" className={footerLinkClass}>
            FAQ
          </Link>
          <Link href="/for-business" className={footerLinkClass}>
            For Business
          </Link>
          <a href={`mailto:${CONTACT_EMAIL}`} className={footerLinkClass}>
            Contact
          </a>
          <Link href="/privacy-policy" className={footerLinkClass}>
            Privacy
          </Link>
          <Link href="/terms-of-service" className={footerLinkClass}>
            Terms
          </Link>
        </nav>
        <p className="text-[12px] text-slate-400 md:pt-1 md:text-right">
          &copy; {new Date().getFullYear()} {BRAND.name}
        </p>
      </div>
    </footer>
  )
}
