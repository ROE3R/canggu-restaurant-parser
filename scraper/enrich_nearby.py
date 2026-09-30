#!/usr/bin/env python3
"""Enrich via searchNearby (separate quota!). Sweep Canggu grid, match by place_id."""
import json, time, os
import requests

KEY = "SET_GMAPS_API_KEY_ENV_VAR"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
FIELDS = "places.id,places.rating,places.userRatingCount,places.nationalPhoneNumber,places.websiteUri,places.primaryTypeDisplayName"
CENTER = (-8.6478, 115.1385)
STEP_LAT = 0.009   # ~1.0 km
STEP_LNG = 0.0095
RADIUS = 800       # meters, circles overlap

def sweep(center, radius, tries=4):
    for t in range(tries):
        try:
            r = requests.post("https://places.googleapis.com/v1/places:searchNearby",
                headers={"X-Goog-Api-Key": KEY, "Content-Type": "application/json",
                         "X-Goog-FieldMask": FIELDS},
                json={"locationRestriction": {"circle": {"center": {"latitude": center[0], "longitude": center[1]}, "radius": radius}},
                      "includedTypes": ["restaurant", "cafe", "bar", "coffee_shop", "bakery", "meal_takeaway", "meal_delivery"],
                      "maxResultCount": 20}, timeout=30)
            if r.status_code == 200:
                return r.json().get("places") or []
            if r.status_code == 429:
                time.sleep(10 + t * 10); continue
            print(f"  err {r.status_code} {r.text[:80]}", flush=True)
            return []
        except Exception:
            time.sleep(5)
    return []

def targeted(p, radius=60):
    """searchNearby centered exactly on the missing place's own coords."""
    try:
        r = requests.post("https://places.googleapis.com/v1/places:searchNearby",
            headers={"X-Goog-Api-Key": KEY, "Content-Type": "application/json",
                     "X-Goog-FieldMask": FIELDS},
            json={"locationRestriction": {"circle": {"center": {"latitude": p["lat"], "longitude": p["lng"]}, "radius": radius}},
                  "maxResultCount": 20}, timeout=30)
        if r.status_code == 200:
            return r.json().get("places") or []
        return []
    except Exception:
        return []

def main():
    places = json.load(open(OUT_FILE))
    by_pid = {p["pid"]: p for p in places}
    need = {p["pid"] for p in places if p.get("review_count") is None}
    print(f"need review_count for {len(need)} places", flush=True)

    # Phase 1: targeted per-place (exact coords)
    todo = [p for p in places if p["pid"] in need and p.get("lat") and p.get("lng")]
    print(f"phase 1: targeted {len(todo)} places", flush=True)
    for i, p in enumerate(todo, 1):
        res = targeted(p)
        for pl in res:
            pid = pl.get("id")
            if pid in need:
                q = by_pid[pid]
                q["review_count"] = pl.get("userRatingCount")
                q["rating_api"] = pl.get("rating")
                q["phone_api"] = pl.get("nationalPhoneNumber")
                q["website_api"] = pl.get("websiteUri")
                q["primary_type"] = (pl.get("primaryTypeDisplayName") or {}).get("text")
                need.discard(pid)
        if i % 10 == 0:
            json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
            ok_total = sum(1 for x in places if x.get("review_count") is not None)
            print(f"  [{i}/{len(todo)}] ok={ok_total}, need {len(need)}", flush=True)
        if not need:
            break
        time.sleep(1.0)

    found = 0
    if not need:
        json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
        print("ALL DONE in phase 1", flush=True)
        return
    lat0, lng0 = CENTER
    # grid covering Canggu/Berawa/Pererenan (~3km x 2.5km)
    lats = [lat0 + d * STEP_LAT for d in (-1, -0.5, 0, 0.5, 1)]
    lngs = [lng0 + d * STEP_LNG for d in (-1.5, -1, -0.5, 0, 0.5, 1, 1.5)]
    cells = [(la, ln) for la in lats for ln in lngs]
    print(f"{len(cells)} grid cells", flush=True)

    for ci, (la, ln) in enumerate(cells, 1):
        res = sweep((la, ln), RADIUS)
        got = 0
        for pl in res:
            pid = pl.get("id")
            if pid in need:
                p = by_pid[pid]
                p["review_count"] = pl.get("userRatingCount")
                p["rating_api"] = pl.get("rating")
                p["phone_api"] = pl.get("nationalPhoneNumber")
                p["website_api"] = pl.get("websiteUri")
                p["primary_type"] = (pl.get("primaryTypeDisplayName") or {}).get("text")
                need.discard(pid)
                found += 1
                got += 1
        ok_total = sum(1 for x in places if x.get("review_count") is not None)
        print(f"cell {ci}/{len(cells)}: {len(res)} places, matched {got} -> total ok {ok_total}, need {len(need)}", flush=True)
        json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
        if not need:
            print("ALL DONE", flush=True)
            break
        time.sleep(1.5)

    json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
    ok_total = sum(1 for x in places if x.get("review_count") is not None)
    print(f"FINAL: {ok_total}/{len(places)}, still missing {len(need)}", flush=True)

if __name__ == "__main__":
    main()
