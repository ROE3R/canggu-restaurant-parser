# Canggu Restaurant Lead Parser

B2B lead-collection tool: **401 restaurants in Canggu, Bali** from **Google Maps**,
enriched with activity signals (review counts, review dates, ads badge) and contacts
(phone/WA/IG/email/website/FB/TikTok) for cold-outreach targeting.

GoFood was skipped per agreement; GrabFood was blocked at the CloudFront/token layer
(documented in `docs/METHODOLOGY.md`) — both are honestly empty columns rather than faked.

## Dataset (output/canggu_restaurants.csv / .json — one row per restaurant)

| Field | Coverage | Source |
|---|---|---|
| name, google_maps_url, google_place_id | 100% | Maps internal search API |
| categories / cuisine, address, lat/lng | 100% | Maps internal API |
| rating_google | 100% | Maps internal API |
| review_count_google | **100%** | Google Places API (GetPlace/searchText/searchNearby) + SerpApi |
| oldest_review_date | 176/401 (43%), 99 fully confirmed | SerpApi + OpenWebNinja reviews APIs |
| newest_review_date | 215/401 (53%) | same |
| ads_google | 3 advertisers (snapshot) | DOM sweep of 29 Maps search queries |
| phone | 360 (90%) | Maps + listings |
| whatsapp | 352 (88%) | derived from phone (62-prefix format; derivation, not per-number verified) |
| website | 284 (70%) | Maps + listings |
| instagram | 212 (52%) | Maps + listings + website crawl |
| email | 97 (24%) | website crawl (contact/about pages) |
| facebook / tiktok | 87 / 58 | website crawl |
| gofood_url / grabfood_url / match_confidence | 0% | platform blocked / out of scope — see honesty note |
| data_notes | per-row | what is missing and why |

## Repo layout

- `scraper/maps_places_scraper.py` — Maps discovery via internal `/search?tbm=map` JSON API (Playwright, in-page fetch)
- `scraper/enrich_places_api.py` — review counts via Places API (GetPlace / searchText), env `GOOGLE_KEY`
- `scraper/enrich_nearby.py` — review counts via Places API `searchNearby` (separate quota), env `GOOGLE_KEY`
- `scraper/serpapi_oldest.py` / `serpapi_oldest_p3.py` / `serpapi_phase2.py` — review dates via SerpApi, env `SERPAPI_KEY`, resumable
- `scraper/own_sweep.py` — review dates via OpenWebNinja API, env `OWN_KEY`, resumable
- `scraper/website_contacts.py` — crawls each restaurant website for emails + social links
- `scraper/ads_sweep.py` — ads badge via DOM "Sponsored" detection on search feeds
- `scraper/build_output_v2.py` — merges all sources into the final CSV/JSON (honest empty fields + data_notes)
- `docs/METHODOLOGY.md` — one-page note: blocking, matching design, ads, first-review-date, break points

## Run

```bash
uv venv .venv && uv pip install --python .venv/bin/python playwright requests
.venv/bin/python -m playwright install chromium

# enrich review counts (Google Places key)
GOOGLE_KEY=... python scraper/enrich_places_api.py
# review dates (SerpApi / OpenWebNinja keys)
SERPAPI_KEY=... python scraper/serpapi_oldest.py
OWN_KEY=... python scraper/own_sweep.py
# contacts from websites
python scraper/website_contacts.py
# ads badge
python scraper/ads_sweep.py
# build final
python scraper/build_output_v2.py
```

All credentials come from environment variables — nothing is hardcoded.

## Honesty statement

Every field that could not be obtained is **empty with a reason in `data_notes`** — nothing is
invented. Blocked items: GoFood (Akamai 403), GrabFood (CloudFront 403 + token chain dead-end),
oldest dates beyond API quotas, ads beyond the snapshot sweep. See `docs/METHODOLOGY.md`.
