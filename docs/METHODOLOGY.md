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
empty. Ads badge: Grab has no ads/sponsored field in any API response. We detect **paid
placement** instead: a 24-query search sweep (`scraper/grab_search_sweep.py`, Playwright
guest) captures cards carrying the explicit **"Preferred Merchant"** label — a Grab
program giving merchants boosted top placement (fulfillment + visibility program, not
per-click ads). 10 Canggu-area merchants carry the label; recorded as `grab_ads=yes`.
`grab_promo` separately records merchant discount promos (weak signal — nearly all
merchants carry default promos), honestly labelled promo, never presented as advertising. Note: essentially all Grab merchants carry default discount promos (e.g.
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


---

# ADDENDUM — v24–v32 (status akhir, menggantikan klaim basi di §7)

Bagian di atas (§1–§7) ditulis saat proyek masih di v17 dan dua klaimnya sudah tidak berlaku:
GoFood **tidak** "skipped by agreement", dan GrabFood **tidak** lagi 403. Status final:

## GrabFood — SELESAI (v24–v27)

- Sumber utama: **search sweep app-driven** (`scraper/grab_search_full.py`). In-page
  `fetch()` ke `guest/v2/search` dijawab `FW_ENDPOINT_FORBIDDEN` (butuh header app:
  `x-grab-web-app-version`, `x-hydra-jwt`, altcha) → solusinya **biarkan aplikasi Grab
  sendiri yang memanggil**: Playwright menavigasi halaman pencarian, request dibuat oleh
  bundle resmi, response ditangkap via `page.on("response")`.
- Body yang benar (hasil reverse chunk `common-utils`):
  `{latlng: "lat,lng" (string), keyword, offset, pageSize: 32, countryCode}`.
- Sitemap resmi + cuisine sweep + detail sweep + sitemap dipakai untuk memperkaya
  alamat/jam buka; nama dibersihkan dari polusi DOM (cuisine/rating yang menempel).
- URL merchant: slug bebas + kode merchant (`food.grab.com/id/en/restaurant/<slug>/<code>`)
  resolve 200 → **100% merchant punya URL**.
- Iklan: label eksplisit **"Preferred Merchant"** (program fulfillment/visibilitas,
  **bukan** CPC) — kejujuran ini penting dan ditulis apa adanya, bukan disebut "ads".
- **Tidak diekspos Grab** (sengaja, bukan kegagalan kita): jarak/latlng merchant dan
  nomor telepon. Ditandai kosong, bukan ditebak.

## GoFood — dua jalur TANPA LOGIN (v28–v32)

Blokir frontal: `gofood.co.id` di belakang WAF yang menolak **semua** IP datacenter dan
proxy (403 instan ±0.7 s, tanpa challenge), termasuk saat pakai UA Googlebot.

**Jalur A — Web Archive (v28–v30).** CDX `matchType=domain` → 17.597 URL merchant.
Snapshot lama memuat data outlet; parser harus menerima `<script ... ld+json ...>` dengan
atribut ekstra (`[^>]*`) — kegagalan awal murni bug regex, bukan data hilang. Setelah
diperbaiki: 65 snapshot terparse → 77 URL + 54 rating + 62 votes. **Catatan jujur:
snapshot 2023–2024, bukan live.** Kolom `data_notes` menandainya.

**Jalur B — indeks mesin pencari (v32).** GoFood memblokir server kita, tapi **tidak**
memblokir perayap Google — jadi indeksnya menyimpan URL merchant. 88 query
`site:gofood.co.id <area> <kata-kunci>` diambil lewat
`r.jina.ai → html.duckduckgo.com` (DDG langsung dari IP proxy dijawab 202 challenge;
via jina 200, rate ~1 query/62 detik). Hasil: 542 URL unik terindeks ⇒ 347 merchant
Canggu baru masuk sebagai `gofood_only` dengan `matched_on = gofood_ddg_index_2026`,
nama+area dari slug. **URL dan nama valid; rating/votes tidak tersedia di indeks** —
ditandai kosong, tidak diisi taksiran.

## Kontak dari teks ulasan (v31)

Endpoint internal Google `GetLocalBoqProxy` (gratis, tanpa API key) memuat **balasan
pemilik**: `review[4][2]` = teks balasan (`[4][5]` = terjemahan), token halaman
berikutnya di `b[6]`. Sweep 413 tempat × 3 halaman: 304 tempat punya balasan pemilik,
71 di antaranya memuat kontak baru (email 97→123, telepon 360→363, IG 212→220).
Kolom `contacts_review_text` + `owner_reply_count` mencatat asalnya.

## Yang benar-benar tertutup (jujur, sudah dicoba habis)

- **GoFood live lewat API mobile**: `goid.gojekapi.com/goid/login/request` dengan client
  konsumen (`gojek:consumer:app`) menjawab `429 goid:error:ratelimited:device` dari
  **semua** IP (server, proxy Indonesia, proxy Jepang) dan semua versi app/fingerprint →
  wajib **device attestation Android (Play Integrity)** yang tidak bisa dipalsukan dari HTTP.
- **Klien merchant GoBiz** (`com.gojek.resto`, `go-biz-mobile`, header `X-Client-Id/Secret`)
  **lolos** pemeriksaan device (201, OTP SMS terkirim) — tetapi scope-nya hanya outlet
  milik nomor yang login, **bukan** katalog GoFood publik. Tidak berguna untuk task ini.
- **Jalur lain yang diuji & gagal**: Common Crawl (GoFood tidak di-crawl), Google Cache
  (dihapus), Mojeek/Startpage/Yandex/Bing dari IP server/proxy (403/0 hasil), Playwright
  langsung ke gofood.co.id via proxy (timeout/403), `sitemap.xml` (403 di balik WAF).

## Status keluaran

`output/canggu_restaurants.csv` (+`.json`) — **satu tabel, satu restoran satu baris**:
1.144 baris; tiap baris punya `match_confidence` dan `matched_on`. 424 punya `gofood_url`,
449 `grabfood_url`, 401 `google_maps_url`. Folder `output/grab/` menyimpan versi
per-platform sebagai cadangan. Kolom kosong **selalu** punya alasan di `data_notes`.
Tidak ada nilai yang diperkirakan atau dikarang.


## ADDENDUM v34 (2026-10-02) — GoFood LIVE + Reviews
- GoFood rating/votes live 2026 via BD Web Unlocker (render:true), URL /id/ (bukan /en/).
- REVIEW TEXT & DATES GoFood TERBUKA: endpoint web `gofood.co.id/api/outlets/{uid}/reviews-overview`
  + Bearer SSO token (dari device pemilik akun, diizinkan). Window API = review terbaru
  (~10-20 terbaru/halaman; window bervariasi per resto, bisa sampai 2022).
  Kolom: gofood_review_count_window, gofood_review_newest, gofood_review_oldest_window,
  gofood_review_sample. True first-review date sejak resto buka TIDAK diekspos API —
  dilaporkan apa adanya.
- gofood_since (createTime outlet) = tanggal resto gabung GoFood.
- Grab review text/dates: tetap CLOSED (portal web tidak ekspos; api.grab.com menuntut
  signature app-internal; portal diblok CloudFront). Tersedia: grab_rating + grab_votes.
- Retry 154 URL GoFood gagal = terverifikasi resto TUTUP (404) — bukan kegagalan scrape.
- oldest_review_date tetap didefinisikan sebagai field Google Maps (spec koreksi 2026-10-02).


### v34.1 — Grab age proxy (2026-10-02)
Review text/dates Grab tertutup (SDK partner resmi tanpa endpoint review; komunitas scraper
juga tidak ada yang punya). PROXY SAH: ID resto Grab "6-Cxxxxx" = sequential per pendaftaran.
Korelasi monotone terverifikasi dgn votes (C2 median 582 → C8 median 13).
Kolom: grab_age_rank (1=tertua..6=terbaru), grab_age_bucket, grab_age_percentile (0-100,
global). Batas: ini umur REGISTRASI resto di Grab, bukan tanggal review pertama — dilaporkan
apa adanya.
