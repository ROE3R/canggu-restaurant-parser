#!/usr/bin/env python3
"""Oldest review dates via SerpApi for the N places with FEWEST reviews.
Paginates up to MAX_PAGES per place. Sort newestFirst so last page holds oldest reviews.
Resumable via OUT_FILE state. Stops when quota exhausted (429/error).
"""
import json, os, time, sys
import requests

KEY = os.environ.get("SERPAPI_KEY", "")
IN_FILE = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
TARGET_N = 60          # places to cover
MAX_PAGES = 5          # max pages per place (8 reviews/page)
BASE = "https://serpapi.com/search.json"

def main():
    places = json.load(open(IN_FILE))
    withcount = [p for p in places if p.get("review_count") is not None]
    withcount.sort(key=lambda p: p["review_count"])          # fewest first
    targets = withcount[:TARGET_N]
    print(f"targets: {len(targets)} places, review_count range {targets[0]['review_count']}..{targets[-1]['review_count']}", flush=True)

    state = {}
    if os.path.exists(OUT_FILE):
        state = json.load(open(OUT_FILE))

    def save():
        json.dump(state, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)

    session = requests.Session()
    def search(params):
        r = None
        for t in range(3):
            try:
                r = session.get(BASE, params={**params, "api_key": KEY}, timeout=60)
                if r.status_code == 200:
                    return r.json()
                time.sleep(3 + t * 4)
            except Exception:
                time.sleep(3)
        return {"_error": f"HTTP {r.status_code if r is not None else 'net'}"}

    done = 0
    for p in targets:
        pid = p["pid"]
        if pid in state and state[pid].get("oldest_review"):
            continue
        rec = {"oldest_review": None, "newest_review": None, "pages_fetched": 0, "status": "pending"}
        token = None
        best_oldest = None
        newest_first_page = None
        for page in range(MAX_PAGES):
            params = {"engine": "google_maps_reviews", "place_id": pid,
                      "sort_by": "newestFirst", "hl": "en"}
            if token:
                params["next_page_token"] = token
            d = search(params)
            if "_error" in d:
                rec["status"] = f"err:{d['_error']}"
                break
            if "error" in d:  # serpapi quota/plan error
                print(f"SERPAPI ERROR: {d['error'][:120]}", flush=True)
                state[pid] = rec
                save()
                print("STOPPING - likely quota exhausted", flush=True)
                return finish(state)
            revs = d.get("reviews", [])
            rec["pages_fetched"] += 1
            if page == 0 and revs:
                newest_first_page = revs[0].get("iso_date")
            if revs:
                last_date = revs[-1].get("iso_date")
                if last_date and (best_oldest is None or last_date < best_oldest):
                    best_oldest = last_date
            nxt = (d.get("serpapi_pagination") or {}).get("next_page_token")
            if not nxt or not revs:
                break
            token = nxt
            time.sleep(0.5)
        rec["oldest_review"] = best_oldest
        rec["newest_review"] = newest_first_page
        rec["status"] = "ok" if best_oldest else "nodates"
        state[pid] = rec
        done += 1
        if done % 5 == 0:
            save()
            print(f"[{done}/{len(targets)}] saved (latest: {p['name'][:30]} oldest={best_oldest})", flush=True)
        time.sleep(0.4)
    save()
    return finish(state)

def finish(state):
    ok = sum(1 for v in state.values() if v.get("oldest_review"))
    print(f"DONE: {ok}/{len(state)} places with oldest_review", flush=True)

if __name__ == "__main__":
    main()
