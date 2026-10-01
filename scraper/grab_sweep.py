#!/usr/bin/env python3
"""GrabFood Bali sweep via portal.grab.com/foodweb + ALTCHA solver. No auth needed."""
import os, sys, json, time, hashlib, base64, requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
      "Accept-Language": "id-ID", "X-Country-Code": "ID"}
LATLNG = "-8.6478,115.1385"
OUT = "/home/agentuser/.hermes/cache/scratch/grab_merchants.json"
CATS_OUT = "/home/agentuser/.hermes/cache/scratch/grab_categories.json"

def altcha():
    r = requests.get("https://portal.grab.com/foodweb/v1/altcha/challenge", headers=UA, timeout=30)
    ch = r.json()
    for n in range(ch["max_number"] + 1):
        if hashlib.sha256((ch["salt"] + str(n)).encode()).hexdigest() == ch["challenge"]:
            break
    UA["X-ALTCHA-Payload"] = base64.b64encode(json.dumps({"algorithm": ch["algorithm"], "challenge": ch["challenge"],
        "number": n, "salt": ch["salt"], "signature": ch["signature"]}).encode()).decode()

def get(url, params, tries=6):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429):
                time.sleep(5 + i * 5); altcha(); continue
            print("HTTP", r.status_code, r.text[:80], flush=True)
        except Exception as e:
            print("ERR", str(e)[:80], flush=True)
        time.sleep(3)
    return None

# 1. cuisine IDs dari sitemap resmi
import re as _re
r0 = requests.get("https://growth-public.grab.com/grabfood-com/sitemap/id/bali/city-cuisine.xml",
                  headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}, timeout=30)
urls = _re.findall(r'<loc>(https://food\.grab\.com/id/id/bali/cuisines/[^<]+)</loc>', r0.text)
cats = []
for u in urls:
    m = _re.match(r'https://food\.grab\.com/id/id/bali/cuisines/([a-z\-]+)-delivery/(\d+)', u)
    if m: cats.append({"name": m.group(1), "shortcutID": m.group(2)})
json.dump(cats, open(CATS_OUT, "w"))
print(f"categories: {len(cats)}", flush=True)

# 2. merchants per category (attributeValueID = shortcutID)
all_m = json.load(open(OUT)) if os.path.exists(OUT) else {}
for ci, cat in enumerate(cats):
    aid = cat.get("shortcutID")
    if not aid: continue
    off = 0
    while True:
        altcha()
        d = get("https://portal.grab.com/foodweb/v1/cuisine-merchants",
                {"attributeValueID": aid, "countryCode": "ID", "citySlug": "bali",
                 "latlng": LATLNG, "offset": off, "pageSize": 32})
        if not d: break
        sr = d.get("searchResult") or {}
        ms = sr.get("searchMerchants") or []
        if not ms: break
        for m in ms:
            mid = m.get("id")
            if mid and mid not in all_m:
                mb = m.get("merchantBrief", {})
                all_m[mid] = {
                    "id": mid,
                    "name": (m.get("address") or {}).get("name"),
                    "chainName": m.get("chainName"),
                    "branchName": m.get("branchName"),
                    "address": (m.get("address") or {}).get("combined_address"),
                    "city": (m.get("address") or {}).get("combined_city"),
                    "cuisine": mb.get("cuisine"),
                    "rating": mb.get("rating"),
                    "vote_count": mb.get("vote_count"),
                    "promo": [p.get("shortDisplayedTag") for p in ((m.get("sideLabels") or {}).get("data") or [])],
                    "delivery_fee": (m.get("estimatedDeliveryFee") or {}).get("priceDisplay"),
                    "delivery_time": m.get("estimatedDeliveryTime"),
                    "open_hours": (mb.get("openHours") or {}).get("displayedHours"),
                    "is_open": (mb.get("openHours") or {}).get("open"),
                    "distance_km": mb.get("distanceInKm"),
                    "category": cat.get("name"),
                    "description": (mb.get("description") or "")[:200],
                }
        total = sr.get("totalCount") or 0
        print(f"[{ci+1}/{len(cats)}] {cat.get('name')}: offset={off} total={total} saved={len(all_m)}", flush=True)
        off += len(ms)
        if off >= (total or 0) or len(ms) < 20:
            break
        time.sleep(1.5)
    json.dump(all_m, open(OUT, "w"))
    time.sleep(1.0)
json.dump(all_m, open(OUT, "w"))
print(f"DONE total merchants: {len(all_m)}", flush=True)
