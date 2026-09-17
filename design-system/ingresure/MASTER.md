# IngreSure Design System — MASTER

Global source of truth. Page overrides: `design-system/ingresure/pages/`.

## Skills applied

| Skill | How we use it |
|-------|----------------|
| **ui-ux-pro-max** | Tokens, a11y checklist, CTA/focus/contrast rules |
| **taste (design-taste-frontend)** | Anti-slop: no Inter/Fraunces defaults, eyebrow cap, accent lock |
| **stitch-skills** | Requires Stitch MCP — **not connected** in this workspace |
| **frontend-design** | Brand-first hero, real product visual (HeroProductDemo) |

## Code sources

| Concern | File |
|---------|------|
| CSS tokens | `frontend/src/app/globals.css` |
| JS tokens | `frontend/src/theme/tokens.ts` |
| Product copy / coverage | `frontend/src/lib/site.ts` |
| Utilities | `.ds-eyebrow`, `.ds-link`, `.ds-section`, `.font-display` |

## Brand colors

| Token | Hex | Use |
|-------|-----|-----|
| primary | `#0F172A` | Ink / headings |
| accent | `#0F766E` | CTAs, links, nav, brand chrome (**one accent lock**) |
| surface / page bg | `#F8FAFC` | Global `--background` |
| safe / avoid / depends | emerald / red / amber | **Verdicts only** |

## Typography

| Role | Face | Class |
|------|------|-------|
| UI / body | Plus Jakarta Sans | `font-sans` |
| Brand / headlines | Newsreader | `font-display` / `font-serif` |

Avoid: Inter + Playfair + Fraunces (LLM defaults).

## Landing

- Max **2** primary CTAs (hero + close); mid = text link
- Hero visual = `HeroProductDemo` (timed real UI), not fake div chrome
- Trust bar full-width under hero columns
- Eyebrows: max ~1 per 3 sections (prefer How the verdict works only)
- Diets as pills, never middot truncation in cards

## Chat

See `pages/chat.md`. No recent-checks UI. Surface shell + soft teal wash.

## Content pages (About / FAQ / For Business / legal)

- Shell: `ContentPageLayout` — surface wash + soft teal atmosphere + light document panel (`bg-white/85`, soft shadow)
- Measure: `max-w-3xl` (matches chat column)
- Title: `ContentPageHeader` — Newsreader H1 (~30→38px), 15px/16px intro, 13px meta
- Body: `.ds-content-body` — 15px → 16px md, line-height 1.7, slate-600
- Sections: Newsreader H2; `space-y-12` between sections
- Nested cards only for interaction (FAQ accordion, B2B form)

## Nav

Desktop: ≤5 links. Mobile: hamburger menu (all links). B2B pill desktop-only.
