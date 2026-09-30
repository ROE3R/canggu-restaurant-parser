#!/usr/bin/env python3
"""Build final deliverable CSV/JSON from collected Maps data.

Honest output: fields we could NOT verify are empty + flagged in a notes column,
never invented.
"""
import json, csv, os

SRC = "/home/agentuser/.hermes/cache/scratch/maps_places_clean.json"
OUTDIR = "/home/agentuser/canggu-restaurant-parser/output"
os.makedirs(OUTDIR, exist_ok=True)

places = json.load(open(SRC))

def is_restaurant(p):
    cats = " ".join(p.get("cats") or []).lower()
    name = (p.get("name") or "").lower()
    bad = ["hotel", "villa", "hostel", "resort", "spa", "gym", "salon", "laundry",
           "pharmacy", "clinic", "school", "temple", "beach", "surf shop", "market"]
    if any(b in cats for b in bad):
        return False
    return True

resto = [p for p in places if is_restaurant(p)]

rows = []
for p in resto:
    rows.append({
        "name": p.get("name"),
        "google_maps_url": f"https://www.google.com/maps/place/?q=place_id:{p.get('pid')}",
        "google_place_id": p.get("pid"),
        "google_cid": p.get("cid"),
        "rating_google": p.get("rating"),
        "review_count_google": "",           # not extractable in limited-view mode
        "oldest_review_date": "",            # requires full review list access
        "categories": "; ".join(p.get("cats") or []),
        "address": p.get("addr"),
        "latitude": p.get("lat"),
        "longitude": p.get("lng"),
        "phone": p.get("phone") or "",
        "website": p.get("website") or "",
        "gofood_url": "",                    # skipped per agreement
        "grabfood_url": "",                  # blocked (CloudFront)
        "match_confidence": "",              # needs Grab data
        "data_notes": "review_count+oldest_review unavailable (Maps limited-view); Grabfood blocked",
    })

# CSV
csv_path = os.path.join(OUTDIR, "canggu_restaurants.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# JSON
json_path = os.path.join(OUTDIR, "canggu_restaurants.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print(f"restaurants: {len(rows)} (from {len(places)} raw places)")
print(f"with phone: {sum(1 for r in rows if r['phone'])}")
print(f"with website: {sum(1 for r in rows if r['website'])}")
print(f"with address: {sum(1 for r in rows if r['address'])}")
print(f"with rating: {sum(1 for r in rows if r['rating_google'])}")
print("wrote:", csv_path)
print("wrote:", json_path)
