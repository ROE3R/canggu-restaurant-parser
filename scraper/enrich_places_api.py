#!/usr/bin/env python3
"""Enrich via GetPlace by place_id (exact). GetPlace quota is separate from searchText."""
import json, time, os
import requests

KEY = os.environ.get("GMAPS_API_KEY", "SET_GMAPS_API_KEY_ENV_VAR")
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
FIELDS = "id,displayName,rating,userRatingCount,formattedAddress,nationalPhoneNumber,websiteUri,primaryTypeDisplayName,location"

def get_place(pid, tries=4):
    for t in range(tries):
        try:
            r = requests.get(f"https://places.googleapis.com/v1/places/{pid}",
                headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELDS}, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(8 + t * 8); continue
            if r.status_code in (500, 503):
                time.sleep(5); continue
            return {"_error": f"{r.status_code} {r.text[:100]}"}
        except Exception:
            time.sleep(4)
    return {"_error": "retries exhausted"}

def main():
    places = json.load(open(OUT_FILE))
    todo = [p for p in places if p.get("review_count") is None]
    print(f"{len(places)} total, {len(todo)} to fetch", flush=True)
    for i, p in enumerate(todo, 1):
        d = get_place(p["pid"])
        if "_error" in d:
            p["api_error"] = d["_error"]
            if "429" not in d["_error"]:
                print(f"  [{i}/{len(todo)}] {p['name'][:30]} ERR {d['_error'][:50]}", flush=True)
        else:
            p.pop("api_error", None)
            p["review_count"] = d.get("userRatingCount")
            p["rating_api"] = d.get("rating")
            p["phone_api"] = d.get("nationalPhoneNumber")
            p["website_api"] = d.get("websiteUri")
            p["primary_type"] = (d.get("primaryTypeDisplayName") or {}).get("text")
        if i % 10 == 0:
            json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
            ok = sum(1 for x in places if x.get("review_count") is not None)
            print(f"  [{i}/{len(todo)}] ok={ok}", flush=True)
        time.sleep(1.0)
    json.dump(places, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for x in places if x.get("review_count") is not None)
    print(f"DONE: {ok}/{len(places)} with review_count")

if __name__ == "__main__":
    main()
