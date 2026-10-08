# Usability Improvements

Four improvements: two front-end, two agent/backend. Each is built to actually change
behavior in the running app, not just exist in code.

## 1. Products page filtering and sorting

**What:** Filter the Products grid by category (garment type), price range, and an
"in stock only" toggle; sort by price (low→high, high→low) or name; a Reset button; a
clear "no products match" message when filters leave nothing.

**Why:** 102 products in one grid is a wall of options. A shopper looking for "a hoodie
under $70 that's actually in stock" currently has to scroll and guess. Filtering turns
browsing into finding, which is the difference between a shopper buying something and
giving up. For the business, "in stock only" also quietly steers shoppers away from
sold-out items instead of them discovering that at checkout.

## 2. Chat polish

**What:** A typing indicator while the agent works (already existed from Problem 5,
kept), starter suggestion chips shown only when the conversation is empty (drawn from
real categories — e.g. "What hoodies do you have?"), auto-scroll to the newest message,
Enter-to-send, and a "Clear conversation" button.

**Why:** A blank chat box is intimidating — most shoppers don't know what's reasonable
to ask a shop bot. Suggestion chips remove that first-message hesitation. Auto-scroll and
Enter-to-send are table-stakes chat UX; without them the panel feels broken the moment a
conversation gets more than a couple of messages long. Clear conversation matters for
privacy and for starting over without a page reload.

## 3. Smarter product search (synonyms, plurals, typos)

**What:** The catalogue search tool now falls back through: exact match → singular/plural
normalization (already existed from Problem 7) → a synonym table grounded in the real
`garment_type` values in the database (e.g. "sweatshirt"/"hoody"/"jumper" → hoodie-family
terms, "tee"/"shirt" → t-shirt) → fuzzy/typo correction against real catalogue vocabulary
using edit-distance matching, before giving up.

**Why:** The brief's own example is the real failure mode: a shopper asking for a
"sweatshirt" or a "hoody" was getting an honest-but-wrong "we don't sell that," even
though the catalogue has dozens of hoodies — the shopper just didn't use our exact
internal garment-type word. That's a lost sale from a vocabulary mismatch, not a real
stock gap. Every fallback stays grounded in actual catalogue data — nothing is invented,
only the search term.

## 4. Sold-out alternatives

**What:** A new tool finds other in-stock products in the same category as a sold-out
item (or sold-out size), returned as the same product-card type the chat already shows.
The agent is instructed to state the sold-out fact plainly first, then offer the
alternatives — never upsell before being honest.

**Why:** Today, "it's sold out" is a dead end — the shopper has to go back and search
again themselves, and often just leaves. Immediately offering a real, in-stock,
same-category alternative keeps them in the conversation and gives the business a shot
at a sale it would otherwise lose outright to a stockout.
