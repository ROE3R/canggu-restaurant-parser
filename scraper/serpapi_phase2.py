#!/usr/bin/env python3
"""Phase 2 SerpApi:
1) review_count for remaining places via type=place (~151 searches)
2) oldest dates for next-cheapest targets (rest ~99 searches)
Resumable; stops cleanly on quota exhaustion.
"""
import json, os, time
import requests

KEY = os.environ["SERPAPI_KEY"]
ENRICHED = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
DATES_FILE = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/serp_phase2_state.json"
BASE = "https://serpapi.com/search.json"

def save(state):
    json.dump(state, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)

def search(session, params):
    r = None
    for t in range(3):
        try:
            r = session.get(BASE, params={**params, "api_key": KEY}, timeout=60)
            if r.status_code == 200:
                return r.json()
            time.sleep(2 + t * 3)
        except Exception:
            time.sleep(3)
    return {"_error": f"HTTP {r.status_code if r is not None else 'net'}"}

def quota_left(session):
    d = session.get("https://serpapi.com/account", params={"api_key": KEY}, timeout=30).json()
    return d.get("plan_searches_left", 0)

def main():
    places = json.load(open(ENRICHED))
    state = json.load(open(OUT_FILE)) if os.path.exists(OUT_FILE) else {"counts": {}, "dates": {}}
    s = requests.Session()

    # --- Phase A: missing review counts ---
    todo_counts = [p for p in places if p.get("review_count") is None and p["pid"] not in state["counts"]]
    print(f"[A] review counts to fetch: {len(todo_counts)}", flush=True)
    for i, p in enumerate(todo_counts, 1):
        if quota_left(s) <= 1:
            print("QUOTA OUT in phase A", flush=True); save(state); return
        d = search(s, {"engine": "google_maps", "type": "place", "place_id": p["pid"], "hl": "en"})
        if "_error" in d:
            state["counts"][p["pid"]] = {"_error": d["_error"]}
        elif "error" in d:
            print(f"SERPAPI ERR: {d['error'][:100]}", flush=True); save(state); return
        else:
            pr = d.get("place_results") or {}
            state["counts"][p["pid"]] = {
                "review_count": pr.get("reviews"),
                "rating": pr.get("rating"),
                "phone": pr.get("phone"),
                "website": pr.get("website"),
            }
            p["review_count"] = pr.get("reviews")
            if pr.get("rating"): p["rating_api"] = pr.get("rating")
            if pr.get("phone"): p["phone_api"] = pr.get("phone")
            if pr.get("website"): p["website_api"] = pr.get("website")
        if i % 15 == 0:
            json.dump(places, open(ENRICHED, "w"), ensure_ascii=False, indent=1)
            save(state)
            print(f"[A] {i}/{len(todo_counts)} saved", flush=True)
        time.sleep(0.3)
    json.dump(places, open(ENRICHED, "w"), ensure_ascii=False, indent=1)
    save(state)
    print(f"[A] DONE. counts now: {sum(1 for p in places if p.get('review_count') is not None)}/{len(places)}", flush=True)

    # --- Phase B: oldest dates, fewest-review-count first ---
    dates = json.load(open(DATES_FILE)) if os.path.exists(DATES_FILE) else {}
    withcount = sorted([p for p in places if p.get("review_count") is not None],
                       key=lambda p: p["review_count"])
    todo_dates = [p for p in withcount
                  if p["pid"] not in dates or not dates[p["pid"]].get("oldest_review")]
    print(f"[B] oldest dates to fetch: {len(todo_dates)}", flush=True)
    for i, p in enumerate(todo_dates, 1):
        if quota_left(s) <= 1:
            print("QUOTA OUT in phase B", flush=True); save(state); return
        pid = p["pid"]
        rec = {"oldest_review": None, "newest_review": None, "pages_fetched": 0, "status": "pending"}
        token, best_oldest, newest0 = None, None, None
        MAX_PAGES = 5
        for page in range(MAX_PAGES):
            params = {"engine": "google_maps_reviews", "place_id": pid,
                      "sort_by": "newestFirst", "hl": "en"}
            if token: params["next_page_token"] = token
            d = search(s, params)
            if "_error" in d:
                rec["status"] = f"err:{d['_error']}"; break
            if "error" in d:
                print(f"SERPAPI ERR: {d['error'][:100]}", flush=True)
                dates[pid] = rec; save(state); return
            revs = d.get("reviews", [])
            rec["pages_fetched"] += 1
            if page == 0 and revs: newest0 = revs[0].get("iso_date")
            if revs:
                ld = revs[-1].get("iso_date")
                if ld and (best_oldest is None or ld < best_oldest): best_oldest = ld
            nxt = (d.get("serpapi_pagination") or {}).get("next_page_token")
            if not nxt or not revs: break
            token = nxt; time.sleep(0.4)
        rec["oldest_review"] = best_oldest
        rec["newest_review"] = newest0
        rec["status"] = "ok" if best_oldest else "nodates"
        dates[pid] = rec
        if i % 5 == 0:
            json.dump(dates, open(DATES_FILE, "w"), ensure_ascii=False, indent=1)
            save(state)
            print(f"[B] {i}/{len(todo_dates)} saved ({p['name'][:28]} oldest={best_oldest})", flush=True)
        time.sleep(0.3)
    json.dump(dates, open(DATES_FILE, "w"), ensure_ascii=False, indent=1)
    save(state)
    ok = sum(1 for v in dates.values() if v.get("oldest_review"))
    print(f"[B] DONE: {ok}/{len(dates)} places with oldest_review", flush=True)

if __name__ == "__main__":
    main()
