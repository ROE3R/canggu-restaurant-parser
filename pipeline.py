#!/usr/bin/env python3
"""Canggu Restaurant Parser — main pipeline.

Collects public restaurant data (Google Maps, GrabFood, GoFood) and merges
it into one CSV. Credentials come from a .env file, never committed.

Usage:
  python pipeline.py gofood-ratings   # fetch live GoFood ratings via Bright Data
  python pipeline.py gofood-reviews   # fetch GoFood reviews (needs GOJEK_SSO_TOKEN)
  python pipeline.py build            # merge everything into output/canggu_restaurants.csv
  python pipeline.py all              # all of the above, in order

Environment (.env in repo root):
  BD_API_KEY      Bright Data API key (zone web_unlocker1)   [required]
  BD_ZONE         Bright Data zone name                      [default: web_unlocker1]
  GOJEK_SSO_TOKEN Gojek SSO JWT (for GoFood reviews)         [optional]
  GMAPS_API_KEY   Google Places API key                      [optional, for Maps refresh]
"""
import json, os, re, sys, time, csv
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# ---- config ---------------------------------------------------------------
def load_env():
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()
BD_KEY = os.environ.get("BD_API_KEY", "")
BD_ZONE = os.environ.get("BD_ZONE", "web_unlocker1")
GOJEK_TOKEN = os.environ.get("GOJEK_SSO_TOKEN", "")

BD_URL = "https://api.brightdata.com/request"

def bd_fetch(url, extra_headers=None, render=True, timeout=200):
    """Fetch a URL through the Bright Data Web Unlocker. Returns text or None."""
    if not BD_KEY:
        sys.exit("Missing BD_API_KEY. Copy .env.example to .env and fill it in.")
    body = {"zone": BD_ZONE, "url": url, "format": "raw"}
    if render:
        body["render"] = True
    if extra_headers:
        body["headers"] = extra_headers
    for attempt in range(2):
        try:
            r = requests.post(BD_URL, json=body, timeout=timeout,
                              headers={"Authorization": f"Bearer {BD_KEY}"})
            if r.status_code == 200 and len(r.text) > 5000:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(15)
    return None

def parse_next_data(html):
    """Extract the outlet object from a GoFood page."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))["props"]["pageProps"]["outlet"]
    except (KeyError, json.JSONDecodeError):
        return None

def gofood_uid(url):
    m = re.search(r'-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', url or "")
    return m.group(1) if m else None

# ---- targets --------------------------------------------------------------
def load_targets():
    """Restaurant URLs to process: from output/targets.json if present, else from CSV."""
    tfile = OUT / "targets.json"
    if tfile.exists():
        return json.loads(tfile.read_text())
    csvf = OUT / "canggu_restaurants.csv"
    urls = []
    if csvf.exists():
        for row in csv.DictReader(open(csvf, encoding="utf-8")):
            if row.get("gofood_url"):
                urls.append(row["gofood_url"])
    return sorted(set(urls))

def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def done_uids(path):
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    done.add(rec["uid"])
            except (json.JSONDecodeError, KeyError):
                pass
    return done

# ---- commands -------------------------------------------------------------
def cmd_gofood_ratings():
    targets = load_targets()
    out = OUT / "gf_ratings.jsonl"
    done = done_uids(out)
    todo = [u for u in targets if gofood_uid(u) not in done]
    print(f"GoFood ratings: {len(todo)} to fetch ({len(done)} already done)")
    for i, url in enumerate(todo):
        uid = gofood_uid(url)
        html = bd_fetch(url)
        outlet = parse_next_data(html) if html else None
        if outlet:
            core = outlet.get("core") or {}
            rtg = outlet.get("ratings") or {}
            since = (core.get("createTime") or "")[:10] or None
            rec = {"uid": uid, "url": url, "ok": True,
                   "name": core.get("displayName"),
                   "rating": rtg.get("average"),
                   "votes": rtg.get("total"),
                   "since": since}
        else:
            rec = {"uid": uid, "url": url, "ok": False, "error": "closed_or_fail"}
        append_jsonl(out, rec)
        print(f"[{i+1}/{len(todo)}] {'OK' if rec['ok'] else rec.get('error')} | {rec.get('name') or url[:50]}")
        time.sleep(5)

def cmd_gofood_reviews():
    if not GOJEK_TOKEN:
        sys.exit("Missing GOJEK_SSO_TOKEN — required for the reviews endpoint.")
    targets = load_targets()
    out = OUT / "gf_reviews.jsonl"
    done = done_uids(out)
    todo = [u for u in targets if gofood_uid(u) not in done]
    print(f"GoFood reviews: {len(todo)} to fetch ({len(done)} already done)")
    headers = {"Authorization": f"Bearer {GOJEK_TOKEN}", "Accept": "application/json",
               "User-Agent": "Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile"}
    # validate the token once before spending requests on every target
    probe = bd_fetch(f"https://gofood.co.id/api/outlets/{gofood_uid(todo[0])}/reviews-overview",
                     extra_headers=headers, render=False)
    try:
        json.loads(probe or "")
    except json.JSONDecodeError:
        sys.exit("GOJEK_SSO_TOKEN rejected (empty/HTML response) — renew the token first.")
    for i, url in enumerate(todo):
        uid = gofood_uid(url)
        text = bd_fetch(f"https://gofood.co.id/api/outlets/{uid}/reviews-overview",
                        extra_headers=headers, render=False)
        rec = {"uid": uid, "url": url, "ok": False}
        if text:
            try:
                j = json.loads(text)
                data = (j.get("reviews") or {}).get("data", [])
                dates = [x.get("createdAt") for x in data if x.get("createdAt")]
                rec.update(ok=True, n_reviews=len(data),
                           newest=max(dates)[:10] if dates else None,
                           oldest=min(dates)[:10] if dates else None,
                           samples=[{"date": x.get("createdAt", "")[:10],
                                     "rating": x.get("rating"),
                                     "text": (x.get("text") or "")[:200]}
                                    for x in data if x.get("text")][:3])
            except json.JSONDecodeError:
                pass
        append_jsonl(out, rec)
        print(f"[{i+1}/{len(todo)}] {'OK ' + str(rec.get('n_reviews')) if rec['ok'] else 'FAIL'} | {url[:50]}")
        time.sleep(2)  # this endpoint is light; workers can be raised if the zone allows

def cmd_build():
    ratings = {}
    rf = OUT / "gf_ratings.jsonl"
    if rf.exists():
        for line in open(rf, encoding="utf-8"):
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    ratings[rec["uid"]] = rec
            except json.JSONDecodeError:
                pass
    reviews = {}
    vf = OUT / "gf_reviews.jsonl"
    if vf.exists():
        for line in open(vf, encoding="utf-8"):
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    reviews[rec["uid"]] = rec
            except json.JSONDecodeError:
                pass
    csvf = OUT / "canggu_restaurants.csv"
    if not csvf.exists():
        sys.exit("output/canggu_restaurants.csv not found — base dataset required.")
    rows = list(csv.DictReader(open(csvf, encoding="utf-8")))
    fields = list(rows[0].keys())
    for c in ["gofood_rating_2026", "gofood_votes_2026", "gofood_since",
              "gofood_review_count_window", "gofood_review_newest",
              "gofood_review_oldest_window", "gofood_review_sample"]:
        if c not in fields:
            fields.append(c)
    n = 0
    for row in rows:
        uid = gofood_uid(row.get("gofood_url"))
        rat = ratings.get(uid)
        rev = reviews.get(uid)
        if rat:
            row["gofood_rating_2026"] = rat.get("rating") or ""
            row["gofood_votes_2026"] = rat.get("votes") or ""
            row["gofood_since"] = rat.get("since") or ""
        if rev:
            row["gofood_review_count_window"] = rev.get("n_reviews") or ""
            row["gofood_review_newest"] = rev.get("newest") or ""
            row["gofood_review_oldest_window"] = rev.get("oldest") or ""
            row["gofood_review_sample"] = " | ".join(
                f"[{s['date']} r{s['rating']}] {s['text'][:60]}" for s in rev.get("samples", []))
            n += 1
    with open(csvf, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Built: {len(rows)} rows, {len(ratings)} GoFood ratings, {len(reviews)} review sets merged.")

COMMANDS = {"gofood-ratings": cmd_gofood_ratings,
            "gofood-reviews": cmd_gofood_reviews,
            "build": cmd_build}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()

if __name__ == "__main__":
    main()
