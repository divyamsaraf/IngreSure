import { ShieldCheck, CheckCircle, Search } from 'lucide-react'

interface FeatureCardProps {
  icon: React.ReactNode
  title: string
  body: string
}

function FeatureCard({ icon, title, body }: FeatureCardProps) {
  return (
    <div className="group flex flex-col rounded-2xl bg-white p-6 shadow-sm shadow-slate-200 ring-1 ring-slate-100 transition-transform transition-shadow hover:-translate-y-1 hover:shadow-xl hover:shadow-emerald-100">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
        {icon}
      </div>
      <h3 className="mb-2 font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-600">{body}</p>
    </div>
  )
}

export default function FeaturesSection() {
  return (
    <section id="how-it-works" className="px-6 py-16 md:py-20">
      <div className="mx-auto max-w-5xl text-center">
        <h2 className="font-serif text-3xl font-bold text-slate-900 md:text-4xl">
          Why IngreSure works — and why you can trust it
        </h2>
        <p className="mt-3 text-sm text-slate-600 md:text-base">
          Behind every quick answer is a deterministic rules engine, ingredient knowledge base,
          and a safety profile tuned to you.
        </p>
      </div>

      <div className="mx-auto mt-10 grid max-w-6xl gap-6 md:mt-14 md:grid-cols-3">
        <FeatureCard
          icon={<ShieldCheck className="h-7 w-7 text-emerald-600" />}
          title="AI Verification"
          body="Powered by deterministic rules and a smart engine that cross-checks ingredients against strict dietary and allergen rules."
        />
        <FeatureCard
          icon={<CheckCircle className="h-7 w-7 text-emerald-600" />}
          title="Safety First"
          body="Personalized safety verdicts based on your diet, lifestyle, and allergens—no generic answers or vague maybes."
        />
        <FeatureCard
          icon={<Search className="h-7 w-7 text-emerald-600" />}
          title="Smart Search"
          body="Audit long, messy ingredient lists in seconds. Spot hidden animal derivatives or allergy risks instantly."
        />
      </div>
    </section>
  )
}

