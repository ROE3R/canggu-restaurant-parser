# Methodology & Field Notes

## 1. Collection — Google Maps

**Endpoint:** internal JSON API `GET /search?tbm=map&q=<query>&pb=<viewport+filters>` issued
from inside a Maps browser tab (same-origin, session cookies apply).

**Why not DOM scraping:** Maps serves a *limited view* (5 results, no counts) without full
browser fingerprint/consent. The JSON API still returns complete place records (20/query).

**Coverage strategy:** query grid = sub-areas (Batu Bolong, Berawa, Pererenan, Padonan,
Tiying Tutul, Babakan) × categories (restaurant, cafe, warung, sushi, pizza, bakery, bar,
breakfast, grill, vegan, Indonesian, Italian, Mexican, seafood, steakhouse, coffee, juice,
Thai, Japanese, Indian, dessert). 30 queries → 413 raw → dedup by `place_id` → **401
restaurants** after filtering hotels/spas/etc.

**Per-place full data:** each place-page HTML embeds a `/maps/preview/place?...pb=...` URL
with the place's feature id; fetching that returns the complete record (rating, phone,
website, opening hours, categories). Verified: SILK 4.9 ✓, La Baracca 4.7 ✓ (matches
public Maps).

## 2. Collection — GrabFood (in progress)

- CloudFront blocks datacenter IPs → SOCKS5 rotating proxy (user-supplied).
- Chromium cannot authenticate SOCKS → local shim (`socks_shim.py`): plaintext local
  SOCKS5 → authenticated upstream.
- Guest token: app calls `POST /proxy/authnv4/login` → `displayToken` (JWT). Captured OK.
- Search API: `POST /proxy/foodweb/guest/v2/search` `{latlng, keyword, offset, pageSize,
  countryCode, enableGuestEndpoints}` → **401**: the bundle shows a second exchange
  (device token → guestLogin → displayToken in sessionStorage) that is not yet fully
  reproduced. The remaining work: run the login from inside the page *after* the app
  itself has initialized, then reuse its sessionStorage token.
- **Ads badge:** GrabFood search cards mark ads with a "Sponsored"/ad badge element;
  would be read per-card once search results render.

## 3. Matching design (implemented for two-source case)

For each Maps place ↔ GrabFood merchant:

1. **Normalize name** (lowercase, strip punctuation/branch suffixes).
2. **Geo gate:** haversine distance ≤ 150 m (Grab latlng vs Maps latlng). Chains
   (Starbucks etc.) pass only if geo matches → eliminates branch mismatches.
3. **Score:** name similarity (token set ratio) × 0.6 + geo proximity × 0.4.
   Menu-overlap boost (+0.15) when >3 identical dish names.
4. **Confidence tiers:** high ≥ 0.85 (auto-accept), medium 0.7–0.85 (flag for review),
   low < 0.7 (no match). Name-only matches are never accepted alone — the geo gate makes
   chain/branch false positives impossible.

*Not yet executed end-to-end because GrabFood data collection is blocked (see §2).*

## 4. Where it breaks (full honesty list)

- Review **counts** and **oldest review dates**: unavailable in limited-view payloads;
  `listugcposts` RPC returns 400 (bad pb) / 403 (session). Options to unblock: full
  browser session with residential IP + consent cookies, or Google Places API (paid).
- GrabFood API: 401 chain (above) + flaky proxy (~17% request failure rate).
- Google Search fallback: CAPTCHA after moderate volume.
- Field `data_notes` in the CSV marks exactly which cells are empty and why. **No value
  in the output is estimated or fabricated.**
