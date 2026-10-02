# Canggu Restaurant Parser

Public-data lead database for restaurants in Canggu, Bali — combining
Google Maps, GrabFood, and GoFood into one table. One row per restaurant,
44 columns, match-confidence on every row.

See [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md) for the plain-language
version and [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for sources,
per-field documentation, and the honest list of what is not obtainable.

## Run it yourself

Requirements: Python 3.10+, a [Bright Data](https://brightdata.com)
account with a Web Unlocker zone (paid per successful request).

```bash
git clone https://github.com/ROE3R/canggu-restaurant-parser
cd canggu-restaurant-parser
pip install -r requirements.txt
cp .env.example .env        # then edit .env with your keys
python pipeline.py all
```

Commands:

| command | what it does |
|---|---|
| `gofood-ratings` | live GoFood ratings/votes via Web Unlocker (resume-safe) |
| `gofood-reviews` | GoFood review texts + dates (needs `GOJEK_SSO_TOKEN` from your own account) |
| `build` | merge collected data into `output/canggu_restaurants.csv` |
| `all` | everything, in order |

Targets are read from `output/targets.json` (list of GoFood URLs), or fall
back to the `gofood_url` column of the existing CSV. Progress is appended
to JSONL files, so you can stop and re-run without losing work.

## What the dataset contains

| source | fields | coverage |
|---|---|---|
| Google Maps | rating, review counts, first/latest review dates, phone, WhatsApp, website, Instagram, email, Facebook, TikTok, ads | 401 |
| GrabFood | rating, votes, promo, ads, restaurant age rank (sequential ID) | 449 |
| GoFood | rating, votes (live), join date, review texts + dates | 424 (311 live) |

## Honesty

Fields that could not be obtained are empty and flagged in `data_notes`.
Notably: Grab does not expose per-restaurant review text or dates on any
public surface (including its partner API) — we document this instead of
faking it. Everything here comes from public pages; no accounts, no
private endpoints.

## Repo structure

```
pipeline.py              main entry point (ratings / reviews / build)
scraper/                 per-platform collectors (Maps, Grab, GoFood contacts/ads/ages)
output/                  targets.json + canggu_restaurants.csv + JSONL progress files
docs/METHODOLOGY.md      sources, field notes, limitations
```
