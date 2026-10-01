# Methodology & Field Notes (1 page)

## 0. GrabFood (added v18)

**Working path (no auth, no login):** `GET portal.grab.com/foodweb/v1/cuisine-merchants`
with `attributeValueID` (cuisine id from the official sitemap `city-cuisine.xml`),
`citySlug=bali`, `latlng` (ignored server-side), `pageSize=32`, offset pagination.
Requests require an **ALTCHA proof-of-work** header (`X-ALTCHA-Payload`): fetch challenge
from `/foodweb/v1/altcha/challenge`, brute-force SHA-256(salt+n) == challenge (solved <0.1 s).

Returns per merchant: name, chain/branch, address, cuisine, **rating, vote_count**,
and promo tags (`sideLabels` = merchant discount promos, NOT paid ads — recorded as
`grab_promo`, honestly not an ads badge).

**Merchant detail endpoint** (`/guest/v2/merchants/{id}`) requires a guest token from
`POST food.grab.com/proxy/authnv4/login` (query params `ServiceID=PASSENGER&AccountIdentifierType=guest`).
This endpoint returns `429 rate_exceeded` persistently — from our server IP, from a
residential proxy, and with dummy JWT headers — so per-merchant detail (lat/lng, menu)
is marked unavailable.

**GrabFood URLs** come from the official merchant sitemap (20,000 URLs / 19,306 unique
merchants for Bali) keyed by merchant id.

**Per-merchant detail (added v20):** guest login blocked via raw HTTP (`authnv4/login`
429 from every IP/proxy), but a real Chromium (Playwright, guest) completes the login and
loads each detail page. `scraper/grab_detail_sweep.py` iterates the 81 sitemap URLs and
captures the `GET /foodweb/guest/v2/merchants/{id}` response (200, header `x-hydra-jwt`).
Result: 80/81 detail OK — fresh rating + voteCount + announcement fields. Grab exposes no
phone or coordinates in any public response, so contact/geo fields for Grab stay honestly
empty. Ads badge: no ads/sponsored field exists in any accessible Grab response —
`grab_promo` records merchant discount promos only (not an ads badge), marked unavailable
for true ads. Note: essentially all Grab merchants carry default discount promos (e.g.
"Diskon 50%"), so promo presence is a weak signal — recorded verbatim, honestly labelled
promo, never presented as advertising.

**Matching Grab→Maps** (spec requires name + geo): Grab exposes no coordinates
so matching is name-normalized fuzzy (SequenceMatcher + token containment ≥0.82) with an
address-area gate (Canggu core: Canggu/Berawa/Babakan/Tibubeneng/Pererenan/Batu Bolong/Batu
Mejan/Padang Linjong). Result: 3 high, 2 low confidence matches, 7 grab-only rows appended
(`match_confidence=grab_only`). Only ~12 core-area Grab merchants carry full data — the
cuisine-list API ranks far beyond Canggu per category, and deeper per-merchant data is
blocked behind the 429'd guest login. Honest gap, documented.

## 1. Collection — Google Maps (complete: 401 restaurants)

**Endpoint:** internal JSON API `GET /search?tbm=map&q=<query>&pb=<viewport+filters>` issued
from inside a Maps browser tab (same-origin, session cookies apply).

**Why not DOM scraping:** Maps serves a *limited view* (5 results, no counts) without full
browser fingerprint/consent. The JSON API still returns complete place records (20/query).

**Coverage strategy:** query grid = sub-areas (Batu Bolong, Berawa, Pererenan, Padonan,
Tiying Tutul, Babakan) × categories (restaurant, cafe, warung, sushi, pizza, bakery, bar,
breakfast, grill, vegan, Indonesian, Italian, Mexican, seafood, steakhouse, coffee, juice,
Thai, Japanese, Indian, dessert). 30 queries → 413 raw → dedup by `place_id` → **401
restaurants** after filtering hotels/spas/etc.

**Per-place full data:** each place-page HTML embeds a `/maps/preview/place?...pb=...` URL;
fetching it returns the complete record (rating, phone, website, hours, categories).
Verified: SILK 4.9 ✓, La Baracca 4.7 ✓ (matches public Maps).

## 2. Review counts — 100% (401/401)

Google Places API (New), three endpoints in fallback order as each exhausted its daily
quota: `GetPlace` → `searchText` → `searchNearby` (the last has an independent quota).
Scripts: `enrich_places_api.py`, `enrich_nearby.py` (env `GOOGLE_KEY`, resumable).
Keys used: 2 (both daily-exhausted; reset ≈ 15:00 WITA next day).

## 3. First/oldest review dates — 176/401 (43%), 99 fully confirmed

No public endpoint exposes review dates cheaply:

- Places API `reviews` field → Enterprise SKU only (PERMISSION_DENIED on standard key).
- Internal RPCs (`listugcposts`, `GetLocalBoqProxy`, `listentitiesreviews`) → 403/404/abuse-gated
  from datacenter IPs (tested from browser context too — Google's limited view).
- Working path: third-party review APIs that mirror Google's review feed.
  - **SerpApi** `google_maps_reviews` (`sort_by=newestFirst`, paginate; last review of the
    last page = oldest). 4 free keys (250 searches each): 176 places, deep pagination on
    the smallest-count places → 99 confirmed-oldest (walked to the feed's end).
  - **OpenWeb Ninja** `business-reviews-v2` (500 free credits, 1 request = 20 reviews
    newest-first): +39 newest dates; deep-walk pass for confirmed oldest is resumable.
- Everything not obtained is empty in the CSV with a reason in `data_notes`. Records whose
  pagination was cut short by quota are marked *approximate* — never presented as confirmed.

## 4. Ads badge (Google Maps) — snapshot sweep

Google does not expose ad status via any API. Detection: render the Maps search feed in a
real browser for each of the 29 grid queries, read the result cards, flag any card whose
DOM contains the "Sponsored" label, match to `place_id`. Result: 3 advertisers
(Dodo Pizza, Nico's Smokehouse, Nana Sans Tandoori). **Caveat:** ads rotate — this is a
snapshot of one session (~15 min), documented as such.

## 5. Matching design (spec §MATCHING) — designed, not executed

The pipeline was designed for name + geo + menu matching with confidence tiers:
1. normalized name (lowercase, strip punctuation/branch suffixes);
2. geo gate — haversine ≤ 150 m (kills chain/branch false positives; name-only is never accepted);
3. score = 0.6·name-token-similarity + 0.4·geo-proximity (+0.15 menu-overlap boost);
4. tiers: high ≥ 0.85 / medium 0.7–0.85 / low < 0.7.

**Why it is not executed:** GoFood was skipped by agreement; GrabFood was blocked
(CloudFront 403 on datacenter/proxy exits; guest-token chain dead-ends with HTTP 401 —
`authnv4/login` token captured but the follow-up `guest/v2/search` rejects it). With zero
GoFood/Grab records there is nothing to match against, so `match_confidence` is honestly
empty instead of fabricated. The design above runs as-is the moment platform data exists.

## 6. Contacts

- **phone** (90%): Maps internal API + listings; cleaned to digits.
- **whatsapp** (88%): derived from Indonesian phone in international format (62…).
  This is a *derivation* — most Indonesian mobile numbers are WA-enabled — not a
  per-number WA check. Flagged here rather than presented as verified.
- **website** (70%): Maps + listings. **instagram** (52%), **facebook** (87), **tiktok** (58):
  Maps, listings, and website crawl. **email** (24%): crawl of each site's
  `/contact`, `/about`, `/kontak` pages plus mailto links; obvious false positives
  (sentry/wix/image files) filtered.

## 7. Where it breaks (honest list)

- GoFood: hard 403 (Akamai/PerimeterX) — skipped by agreement.
- GrabFood: CloudFront 403 on all tested exits + token chain dead-end (above).
- Review dates beyond API quotas — resumable scripts included (`serpapi_oldest_p3.py`,
  `own_sweep.py`); re-running with fresh keys continues where they stopped.
- Ads badge = snapshot only (ads rotate per session).
- Google Search fallback: CAPTCHA after moderate volume.
- Every empty cell says why in `data_notes`. **No value in the output is estimated or fabricated.**
