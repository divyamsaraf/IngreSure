'use client'

import { useState, type FormEvent } from 'react'

const USE_CASES = [
  'Grocery / retail app',
  'Food delivery / marketplace',
  'Restaurant / meal kit',
  'Recipe or meal-planning app',
  'Corporate dining / catering',
  'CPG / private label',
  'Other',
] as const

type FormState = 'idle' | 'submitting' | 'success' | 'error'

export default function RequestAccessForm() {
  const [companyName, setCompanyName] = useState('')
  const [useCase, setUseCase] = useState<(typeof USE_CASES)[number] | ''>('')
  const [monthlyVolume, setMonthlyVolume] = useState('')
  const [email, setEmail] = useState('')
  const [problemFocus, setProblemFocus] = useState('')
  const [state, setState] = useState<FormState>('idle')
  const [error, setError] = useState('')

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setState('submitting')
    setError('')
    try {
      const res = await fetch('/api/request-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyName,
          use_case: useCase,
          monthly_volume: monthlyVolume,
          email,
          problem_focus: problemFocus || undefined,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setState('error')
        setError(typeof body?.error === 'string' ? body.error : 'Could not submit. Please try again.')
        return
      }
      setState('success')
    } catch {
      setState('error')
      setError('Network error. Please try again.')
    }
  }

  if (state === 'success') {
    return (
      <p
        className="rounded-2xl border border-accent/20 bg-teal-50/90 px-5 py-4 text-[15px] font-medium leading-relaxed text-teal-900"
        role="status"
      >
        Thanks — we&apos;ll be in touch within a few days.
      </p>
    )
  }

  const fieldClass =
    'mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-[15px] text-slate-800 shadow-sm transition-colors placeholder:text-slate-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25'

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-5 rounded-2xl border border-slate-200/80 bg-surface/70 p-5 sm:p-6"
    >
      <div>
        <label htmlFor="company_name" className="block text-[13px] font-medium text-slate-700">
          Company name
        </label>
        <input
          id="company_name"
          name="company_name"
          required
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          className={fieldClass}
          autoComplete="organization"
        />
      </div>
      <div>
        <label htmlFor="use_case" className="block text-[13px] font-medium text-slate-700">
          Use case
        </label>
        <select
          id="use_case"
          name="use_case"
          required
          value={useCase}
          onChange={(e) => setUseCase(e.target.value as (typeof USE_CASES)[number] | '')}
          className={`${fieldClass} cursor-pointer`}
        >
          <option value="" disabled>
            Select one…
          </option>
          {USE_CASES.map((uc) => (
            <option key={uc} value={uc}>
              {uc}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="monthly_volume" className="block text-[13px] font-medium text-slate-700">
          Estimated monthly volume
        </label>
        <input
          id="monthly_volume"
          name="monthly_volume"
          required
          value={monthlyVolume}
          onChange={(e) => setMonthlyVolume(e.target.value)}
          placeholder="e.g. ~10k checks / month"
          className={fieldClass}
        />
      </div>
      <div>
        <label htmlFor="problem_focus" className="block text-[13px] font-medium text-slate-700">
          What risk are you trying to reduce? <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <textarea
          id="problem_focus"
          name="problem_focus"
          rows={3}
          value={problemFocus}
          onChange={(e) => setProblemFocus(e.target.value)}
          placeholder="e.g. allergen flags at checkout, diet filters on menus, recipe personalization…"
          className={`${fieldClass} resize-y min-h-[5.5rem]`}
        />
      </div>
      <div>
        <label htmlFor="email" className="block text-[13px] font-medium text-slate-700">
          Work email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={fieldClass}
          autoComplete="email"
        />
      </div>
      {state === 'error' && error ? (
        <p className="text-[13px] text-avoid" role="alert">
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={state === 'submitting'}
        className="mt-1 w-full cursor-pointer rounded-xl bg-accent px-5 py-3 text-[15px] font-semibold text-white shadow-card transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {state === 'submitting' ? 'Sending…' : 'Request a conversation'}
      </button>
    </form>
  )
}
