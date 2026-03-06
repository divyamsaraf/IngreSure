import { UserCheck, MessageCircleQuestion, BadgeCheck } from 'lucide-react'

interface StepProps {
  icon: React.ReactNode
  title: string
  body: string
  step: string
}

function HowItWorksStep({ icon, title, body, step }: StepProps) {
  return (
    <div className="flex flex-col rounded-2xl bg-white p-6 shadow-sm shadow-slate-200 ring-1 ring-slate-100">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-700">
          {icon}
        </div>
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {step}
        </span>
      </div>
      <h3 className="mb-2 font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-600">{body}</p>
    </div>
  )
}

export default function HowItWorksSection() {
  return (
    <section className="px-6 py-16 md:py-20 bg-[#F8FAFC]">
      <div className="mx-auto max-w-5xl text-center">
        <h2 className="font-serif text-3xl font-bold text-slate-900 md:text-4xl">
          How IngreSure works
        </h2>
        <p className="mt-3 text-sm text-slate-600 md:text-base">
          Three simple steps to turn confusing labels into clear, personalized answers.
        </p>
      </div>

      <div className="mx-auto mt-10 grid max-w-6xl gap-6 md:mt-14 md:grid-cols-3">
        <HowItWorksStep
          step="Step 1"
          icon={<UserCheck className="h-5 w-5" />}
          title="Set your profile"
          body="Tell us your diet and allergens once — vegan, Halal, lactose-free, nut allergies, and more."
        />
        <HowItWorksStep
          step="Step 2"
          icon={<MessageCircleQuestion className="h-5 w-5" />}
          title="Paste any ingredient list"
          body="Type or paste ingredients from a label, menu, or recipe directly into the chat."
        />
        <HowItWorksStep
          step="Step 3"
          icon={<BadgeCheck className="h-5 w-5" />}
          title="Get instant audits"
          body="See clear Safe / Avoid / Depends verdicts, allergens, and safer alternatives tailored to you."
        />
      </div>
    </section>
  )
}

