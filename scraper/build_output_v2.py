#!/usr/bin/env python3
"""Build v2: merge enriched review counts + extract instagram/email into final CSV/JSON."""
import json, csv, os, re

SRC_ENRICHED = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
REVIEW_DATES = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
WEB_CONTACTS = "/home/agentuser/.hermes/cache/scratch/website_contacts.json"
OUTDIR = "/home/agentuser/canggu-restaurant-parser/output"

places = json.load(open(SRC_ENRICHED))
rdates = json.load(open(REVIEW_DATES)) if os.path.exists(REVIEW_DATES) else {}
wcontacts = json.load(open(WEB_CONTACTS)) if os.path.exists(WEB_CONTACTS) else {}
ADS = "/home/agentuser/.hermes/cache/scratch/ads_by_name.json"
ads_map = json.load(open(ADS)) if os.path.exists(ADS) else {}

def is_restaurant(p):
    cats = " ".join(p.get("cats") or []).lower()
    name = (p.get("name") or "").lower()
    bad = ["hotel", "villa", "hostel", "resort", "spa", "gym", "salon", "laundry",
           "pharmacy", "clinic", "school", "temple", "surf shop", "market"]
    if any(b in cats for b in bad):
        return False
    if any(b in name and "restaurant" not in name and "cafe" not in name for b in bad):
        return False
    return True

def clean_phone(p):
    """Extract a single clean phone from the raw Maps phone structure.
    Structure: [display, [[variants]...], None, digits, None, [tel:, ...], ...]
    Priority: phone_api (API-verified) > first string variant > digits-only entry.
    """
    if p.get("phone_api"):
        return p["phone_api"]
    ph = p.get("phone")
    if isinstance(ph, str):
        return ph
    if not isinstance(ph, list):
        return ""
    # collect string candidates
    def walk(x):
        out = []
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, list):
            for i in x:
                out.extend(walk(i))
        return out
    cands = [s for s in walk(ph)
             if s and not s.startswith("tel:")
             and not re.match(r'^[0-9a-f]{20,}$', s, re.I)
             and re.search(r'\d{6,}', s.replace(" ", "").replace("-", ""))]
    if not cands:
        return ""
    # prefer the formatted display number (has dashes/spaces or +62)
    for s in cands:
        if s.startswith("+62") or "-" in s:
            return s
    return cands[0]

def extract_contacts(p):
    """Pull instagram + email from website field and any embedded strings."""
    blob = json.dumps(p, ensure_ascii=False)
    ig = re.findall(r'instagram\.com/[A-Za-z0-9_.]+/?', blob)
    em = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', blob)
    em = [e for e in em if not e.endswith('.png') and not e.endswith('.jpg')
          and 'google' not in e and 'gstatic' not in e and 'sentry' not in e]
    return ";".join(dict.fromkeys(ig)) or "", ";".join(dict.fromkeys(em)) or ""

resto = [p for p in places if is_restaurant(p)]
rows = []
for p in resto:
    rd = rdates.get(p.get("pid"), {})
    wc = wcontacts.get(p.get("pid"), {})
    ig, em = extract_contacts(p)
    # merge website-derived contacts (lowercase-dedupe)
    web_emails = wc.get("emails") or []
    web_ig = [f"instagram.com/{h}" for h in (wc.get("instagram") or [])]
    em_all = ";".join(dict.fromkeys([e for e in ([em] if em else []) + web_emails if e]))
    ig_all = ";".join(dict.fromkeys([i for i in ([ig] if ig else []) + web_ig if i]))
    fb = ";".join(f"facebook.com/{h}" for h in (wc.get("facebook") or []))
    tt = ";".join(f"tiktok.com/@{h}" for h in (wc.get("tiktok") or []))
    rc = p.get("review_count")
    notes = []
    if rc is None:
        notes.append("review_count unavailable (API quota/403)")
    st = (rd.get("status") or "")
    if rd.get("oldest_review"):
        oldest = rd.get("oldest_review", "")
        newest = rd.get("newest_review", "")
        if "truncated" in st:
            notes.append("oldest_review approximate (pagination cut by SerpApi quota)")
    else:
        oldest = newest = ""
        notes.append("oldest_review unavailable (SerpApi quota; sort oldest unsupported)")
    rows.append({
        "name": p.get("name"),
        "google_maps_url": f"https://www.google.com/maps/place/?q=place_id:{p.get('pid')}",
        "google_place_id": p.get("pid"),
        "rating_google": p.get("rating"),
        "review_count_google": rc if rc is not None else "",
        "oldest_review_date": oldest,
        "newest_review_date": newest,
        "categories": "; ".join(p.get("cats") or []),
        "address": p.get("addr"),
        "latitude": p.get("lat"),
        "longitude": p.get("lng"),
        "phone": clean_phone(p),
        "website": p.get("website") or p.get("website_api") or "",
        "instagram": ig_all,
        "email": em_all,
        "facebook": fb,
        "ads_google": "yes" if p.get("pid") in ads_map else "",
        "tiktok": tt,
        "gofood_url": "",  # skipped per agreement
        "grabfood_url": "",  # CloudFront blocks guest API from all proxy exit IPs tested
        "match_confidence": "",
        "data_notes": "; ".join(notes),
    })

csv_path = os.path.join(OUTDIR, "canggu_restaurants.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

json_path = os.path.join(OUTDIR, "canggu_restaurants.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

n_rc = sum(1 for r in rows if r["review_count_google"] != "")
n_ig = sum(1 for r in rows if r["instagram"])
n_em = sum(1 for r in rows if r["email"])
print(f"restaurants: {len(rows)} (from {len(places)} raw)")
print(f"review_count: {n_rc}/{len(rows)}")
print(f"instagram: {n_ig}, email: {n_em}")
print(f"phone: {sum(1 for r in rows if r['phone'])}, website: {sum(1 for r in rows if r['website'])}")
