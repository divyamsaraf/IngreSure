/** Resolve emoji for a dietary preference from backend `diet_icon` map (matches ChatInterface). */
export function getDietIcon(dietIcon: Record<string, string>, diet: string | undefined): string {
  if (!diet || diet === 'No rules') return dietIcon['No rules'] ?? '🍽️'
  const key = diet.trim()
  const found =
    dietIcon[key] ?? Object.entries(dietIcon).find(([k]) => k.toLowerCase() === key.toLowerCase())?.[1]
  return found ?? '🥗'
}
