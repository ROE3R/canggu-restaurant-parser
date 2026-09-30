# Canggu Restaurant Lead Parser

B2B lead-collection tool: restaurants in **Canggu, Bali** from **Google Maps** (complete),
**GrabFood** (in progress — see Status), matched across platforms with confidence scores.

## Status (honest)

| Source | Status | Coverage |
|---|---|---|
| Google Maps | ✅ **Working** | 401 restaurants, 100% rating/category/address, 90% phone, 71% website, **65% review count** (Google Places API) |
| GrabFood | ⚠️ Blocked from this infra | Guest-token flow built; API returns 401 (CloudFront + token chain) |
| GoFood | ⏭️ Skipped per agreement | — |

## What works

- **Maps internal JSON API** (`/search?tbm=map` with `pb` viewport params) — queried by
  sub-area × category grid (30 queries) → dedup by `place_id` → 401 unique restaurants.
- **Per-place full record** (`/maps/preview/place` pb from place-page HTML) — gives rating,
  phone, website, hours, categories. Verified against known values.
- **Ads badge (Maps):** "Sponsored" flag visible in search feed DOM (e.g. Nico's Smokehouse).

## What does NOT work (documented, not faked)

- **Oldest-review dates** — Google serves a *limited view* from datacenter IPs (no consent /
  fingerprint signals). Review lists are not in the limited-view payload; `listugcposts` RPC
  rejects with 400/403. Review **counts** WERE obtained where quota allowed, via the
  Places API (`GetPlace` + `searchNearby`, separate quotas) — see `scraper/enrich_places_api.py`
  and `scraper/enrich_nearby.py`.
- **GrabFood** — not pursued further (CloudFront blocks the datacenter/rotating-proxy exits
  intermittently; ~1 in 6 requests fail). Guest token obtained via `/proxy/authnv4/login`,
  but the follow-up `guest/v2/search` still 401s.

## Layout

- `scraper/grabfood_scraper.py` — Playwright-based GrabFood client (in-page guest login
  → fetch search API with captured token). Requires the SOCKS shim.
- `scraper/socks_shim.py` — local SOCKS5 shim: unauth local listener → authenticated
  upstream proxy (Chromium can't do SOCKS auth natively). Run on port 1080.
- `scraper/build_output.py` — builds final CSV/JSON, filters non-restaurants,
  leaves unverifiable fields **empty** (never invented).
- `output/canggu_restaurants.csv` / `.json` — final dataset.
- `docs/METHODOLOGY.md` — matching design, blocking notes, field sources.

## Run

```bash
uv venv .venv && uv pip install --python .venv/bin/python playwright requests pysocks
.venv/bin/python -m playwright install chromium

# 1. start proxy shim (edit upstream creds inside)
python scraper/socks_shim.py 1080 &

# 2. GrabFood (optional; currently blocked upstream)
python scraper/grabfood_scraper.py

# 3. rebuild output
python scraper/build_output.py
```

## Data caveats

Every row has `data_notes` explaining exactly which fields could not be collected and why.
Nothing is estimated or synthesized.
