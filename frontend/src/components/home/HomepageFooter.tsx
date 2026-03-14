export default function HomepageFooter() {
  return (
    <footer className="bg-slate-900 py-8 text-sm text-slate-300">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 md:flex-row">
        <div className="flex flex-col items-center gap-1 text-center md:items-start md:text-left">
          <p className="font-medium text-slate-100">IngreSure</p>
          <p className="text-[12px] text-slate-400">
            Human-first ingredient intelligence. Built for real-world diets and allergies.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-4 text-[12px] text-slate-400 md:justify-end">
          <span className="cursor-default hover:text-slate-200" title="Coming soon">About</span>
          <a href="mailto:hello@ingresure.com" className="hover:text-slate-200">
            Contact
          </a>
          <span className="cursor-default hover:text-slate-200" title="Coming soon">Privacy Policy</span>
        </div>
        <p className="text-[12px] text-slate-500">
          &copy; {new Date().getFullYear()} IngreSure. All rights reserved.
        </p>
      </div>
    </footer>
  )
}

