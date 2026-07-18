// LEGACY (commented for reference) — previous landing design, kept intentionally.
// Not built or imported. To restore, uncomment and wire via src/app/page.tsx.
//
// import Link from 'next/link'
// import { CONTACT_EMAIL } from '@/lib/site'
//
// const footerLinkClass = 'hover:text-slate-200 transition-colors'
//
// export default function HomepageFooter() {
//   return (
//     <footer className="bg-slate-900 py-8 text-sm text-slate-300">
//       <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 md:flex-row">
//         <div className="flex flex-col items-center gap-1 text-center md:items-start md:text-left">
//           <p className="font-medium text-slate-100">IngreSure</p>
//           <p className="text-[12px] text-slate-400">
//             Human-first ingredient intelligence. Built for real-world diets and allergies.
//           </p>
//         </div>
//         <nav
//           className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[12px] text-slate-400 md:justify-end"
//           aria-label="Footer"
//         >
//           <Link href="/about" className={footerLinkClass}>
//             About
//           </Link>
//           <Link href="/faq" className={footerLinkClass}>
//             FAQ
//           </Link>
//           <Link href="/for-business" className={footerLinkClass}>
//             For Business
//           </Link>
//           <a href={`mailto:${CONTACT_EMAIL}`} className={footerLinkClass}>
//             Contact
//           </a>
//           <Link href="/privacy-policy" className={footerLinkClass}>
//             Privacy Policy
//           </Link>
//           <Link href="/terms-of-service" className={footerLinkClass}>
//             Terms of Service
//           </Link>
//         </nav>
//         <p className="text-[12px] text-slate-500">
//           &copy; {new Date().getFullYear()} IngreSure. All rights reserved.
//         </p>
//       </div>
//     </footer>
//   )
// }
