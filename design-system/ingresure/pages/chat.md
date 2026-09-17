# Chat page — design overrides

Extends `../MASTER.md`. Apply when building or reviewing `/chat`.

## Job of the page

Paste ingredients → personalized Safe / Avoid / Depends → enough trust to run again.

## Hierarchy

1. Sticky header: product name + diet pill (accent soft surface)
2. One profile nudge path at a time (banner **or** empty-state link **or** post-audit personalise)
3. Empty: paste-first headline + 3 example chips — **no fake conversation**
4. Results: audit cards nearly full width (not trapped in a narrow bubble)
5. Input: auto-growing textarea; Enter sends, Shift+Enter newline

## Shell / background

- Page: `bg-surface` + soft teal radial wash (aligned with landing)
- Panel: white / 95% + light border + soft shadow + light blur

## Tokens

- Brand chrome → `accent` / teal soft surfaces
- Never `text-blue-*` for Edit/links
- Emerald only via verdict `safe` tokens
- Display titles → `font-display`

## Loading

Dots while pending. No lingering “Analysis complete” label.

## Disclaimer

Short line under input; full legal copy in `title` / `CHAT_PANEL_DISCLAIMER`.

## Out of scope

Recent checks UI is removed from chat.
