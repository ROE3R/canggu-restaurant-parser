# Delivery Summary — Canggu Restaurant Lead Database (2026-10-03)

One clean table: 1,143 restaurants, one row per restaurant, 45 columns.
Files: `canggu_restaurants.csv` (564 KB) + `canggu_restaurants.json`.

## Coverage at a glance

| field | coverage |
|---|---|
| google_maps_url | 401 |
| gofood_url | 423 |
| grabfood_url | 825 (official Grab sitemap) |
| grab_rating / grab_votes | 760 / 762 |
| grab_status | 731 (ACTIVE 607 · NOT_LISTED 48 · CLOSED 2 · no-rating 16) |
| grab_promo (discounts) | 708 |
| grab_ads ("Preferred Merchant" boosted placement) | yes 118 / no 640 |
| gofood_rating_2026 / gofood_votes_2026 | 355 / 355 |
| gofood_since (join date) | 324 |
| gofood review window (texts + dates) | 357 |
| gofood_assured (Merchant Assured badge) | yes 282 / no 141 |
| Google review oldest/newest dates | 393 |
| owner replies scanned (contact mining) | 401 places, 71 new contacts |
| grab_age_rank (registration-age proxy) | 416 |

## What is yes/no and what is empty

- **yes / no** = actually observed on the platform.
- **empty** = could not be observed (restaurant not on the platform, or the
  platform does not expose the field). Empty cells are honest gaps, never guesses.

## Platform ads badges

- **Google Maps** (`ads_google`): "Sponsored" cards captured in a rendered
  search-feed sweep — 3 advertisers at snapshot time. Ads rotate; snapshot only.
- **Grab** (`grab_ads`): explicit "Preferred Merchant" label from the search
  sweep (a paid boosted-placement program). 118 yes / 640 no.
- **GoFood**: no ads column — deliberately. GoFood's entire web codebase
  (search page, listing page, 1.5 MB app bundle) contains zero
  ads/sponsored/promoted references; the "Ad" label exists only inside the
  mobile app feed, served by an authenticated internal API. It cannot be
  obtained from public web data, so the column was not fabricated.

## Known limits (documented, not hidden)

- **Grab review texts/dates**: Grab never exposes them on any public surface
  (web or partner API). `grab_age_rank` is provided as an honest
  registration-age proxy instead.
- **GoFood oldest review date**: the reviews API returns a recent window
  (varies per restaurant, back to ~2022), not the true first-ever review.
  Reported as-is in `gofood_review_oldest_window`.
- **GoFood/Grab rows without a platform URL**: the restaurant could not be
  located on that platform — left empty, flagged in `data_notes`.
- Every empty cell has a reason in `data_notes`. No value is estimated or
  fabricated.

## Sources & method

Full methodology, per-field notes, and the honest list of what is not
obtainable: `docs/METHODOLOGY.md` in
https://github.com/ROE3R/canggu-restaurant-parser
