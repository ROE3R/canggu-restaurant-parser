CANGGU RESTAURANT LEAD DATABASE — FINAL DELIVERY (v34)

Dataset: 1,143 restaurants — one row per restaurant, one clean table (CSV + JSON).
Coverage: Canggu, Bali (Kuta Utara area) — Google Maps, GrabFood, GoFood.

============================================================
WHAT'S INSIDE
============================================================

GOOGLE MAPS (401 restaurants)
- Rating, review count, first & latest review dates (393/401)
- Contacts: phone 363 · WhatsApp 360 · website 284 · Instagram 220 ·
  email 123 · Facebook 87 · TikTok 58
- Owner replies to reviews, review-derived contacts (71)
- Ads badge (3)

GRABFOOD (449 restaurants)
- Rating & vote counts (435)
- Ads/preferred-merchant badge (118)
- Restaurant tenure on platform: 439 graded oldest→newest
  (grab_age_rank / grab_age_percentile), derived from Grab's sequential
  restaurant IDs — validated against vote counts (monotonic correlation)
- Note: per-restaurant review text/dates are not exposed by Grab on any
  public surface (partner API included). This is marked honestly.

GOFOOD (424 restaurants) — data pulled live, October 2026
- Rating & vote counts (311)
- Date restaurant joined GoFood (253)
- Actual review texts with dates (295 restaurants, 4,600+ reviews):
  gofood_review_newest, gofood_review_oldest_available,
  gofood_review_count_window, and 2-3 sample reviews per restaurant
- Note: GoFood's API exposes a rolling review window, not the true first
  review ever. Oldest available date is reported as-is.

MATCHING
- Cross-platform matching uses name + address/location, never name-only.
- Every row carries match_confidence + matched_on (method used).

HONESTY NOTE (per project ground rules)
- Fields that could not be obtained are left empty and flagged in
  data_notes. Nothing is fabricated.
- All data from public surfaces only. No client accounts or servers used.

FILES
- canggu_restaurants_v34.csv   — final dataset (1,143 rows, 44 columns)
- canggu_restaurants_v34.json  — same data, JSON
- docs/METHODOLOGY.md          — full methodology, per-platform sources,
                                 limitations & honest gaps
- output/gf_reviews_results.jsonl — raw GoFood review extracts

HOW TO USE FOR LOW-VOLUME TARGETING
- GoFood: small gofood_votes_2026 + recent gofood_since = new/low-volume
- Grab:   low grab_votes + high grab_age_percentile = established but
          underperforming; low percentile = brand-new on Grab
- Filter empty phone/email away, keep match_confidence = high.
