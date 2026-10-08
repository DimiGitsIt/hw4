# Design Changes

Frontend-only. Navy/gold identity kept; no real Yale images, logos, or text copied.

## Fonts & type scale

- Paired **Fraunces** (a characterful, high-contrast collegiate serif) for all headlines/prices with **Inter** for body text — distinct from the generic sans-everywhere look, and reads as a real storefront rather than a template.
- Both load via Google Fonts with `preconnect` + `font-display: swap`, and every `font-family` ends in a safe system fallback (Georgia/system sans) — if the font CDN fails or is slow, the page still renders immediately and correctly, just with a substitute font.
- One shared type scale (`--fs-display` through `--fs-label`) in `index.css` — every heading, price, and label across the site now pulls from the same few sizes instead of ad hoc values, so hierarchy reads consistently page to page.

## Color & hierarchy

- Kept the existing navy/gold palette but added a few tonal steps (`--cc-navy-deep`, `--cc-gold-deep`, `--cc-image-bg`) for depth in gradients, hovers, and the new neutral image frame.
- Products page got a real header (title + one-line sub-copy) and the two redundant "styles total"/"styles match" lines were collapsed into one dynamic line ("102 styles available" or "30 of 102 styles match").
- Product detail page reordered into a clear read order: category label → name → price + status pill → description → colors → size picker, so the buy-relevant facts (price, stock) sit right under the name instead of after the description.

## Product presentation

- Every product image — card and detail page — now sits in a fixed 1:1 frame with a neutral background and `object-fit: contain`, so photos with black backgrounds, white backgrounds, or odd side-bars all present consistently instead of cropping or stretching.
- Cards get a hover lift + shadow + subtle image zoom, a serif price, and a real **"Sold out"** badge driven by the existing `in_stock` field — no backend change, so the grid only shows this badge where that data already exists (chat-search cards, which don't carry it, simply show none rather than a guess).
- The detail page adds a **"Low stock"/"In stock"/"Sold out"** status pill computed from total inventory across sizes (≤15 units = low), and the old plain HTML size table became a clickable size-chip picker — sold-out sizes are visibly struck through and disabled, available sizes show exact remaining count on selection.

## Motion

- A shared `cc-animate-in` fade-up utility, staggered slightly across grid cards and feature blocks, plus a lightweight page-fade on every route change (remounting a wrapper keyed on the path — no new dependency).
- Hover/press feedback added to buttons, cards, nav links, and the chat toggle/panel.
- Everything respects `prefers-reduced-motion: reduce` via one global rule that collapses all animation/transition durations to near-zero for anyone who's asked for it.

## Chat feel

- Branded gradient header with a small gold "Y" mark, matching the hero's monogram.
- Distinct message styling: the shopper's bubble is a navy-to-blue gradient with a sharp trailing corner; the agent's is white with a soft shadow and a sharp leading corner — readable at a glance who said what.
- The panel now animates open/close (scale + fade from the toggle button) instead of snapping in and out, and mobile gets its own width cap so it never overflows a small screen.
- Chat product cards use the same neutral image frame as the main site, so a result shown in chat looks like it belongs to the same store as the Products page.

## Creative touches (picked two)

1. **"Fresh Off The Press" new-arrivals strip on Home** — a real, live slice of the catalogue (first 4 products from the actual API, not staged/invented), giving the homepage something to browse immediately instead of just a hero and three static feature blurbs.
2. **A varsity-stripe kicker** (two small gold tick-marks flanking a label) above every major section heading — Home's hero, Products, About, and the new-arrivals strip — plus a diagonal pinstripe texture behind the hero and a "breathing" glow on the Y monogram. It's a small, repeatable motif that reads as school-spirit/letterman without borrowing any real Yale mark.

## Why this should help customers stick around and buy

Consistent image framing and a real stock badge mean a shopper can scan the grid and trust what they're seeing is accurate and tidy, not guess from inconsistent photos. Clear price/stock hierarchy and the size picker on the detail page shorten the path from "I like this" to "I can see exactly what to buy." Motion and the chat polish make the site feel maintained and responsive rather than static, which matters for a merch shop competing against the real bookstore on vibe as much as price.
