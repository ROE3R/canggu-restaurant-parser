#!/usr/bin/env python3
"""SerpApi phase 3 - oldest review dates, ECONOMY mode.

Strategy (fast + frugal):
  * cheapest-first: places with FEWEST reviews can be walked to the end
    in 1-3 pages, so their oldest date is CONFIRMED, not guessed.
  * MAX_PAGES=3 (8 reviews page 1 + 20/page after = up to 48 reviews deep).
  * every record carries `confirmed` = True only when pagination ended
    naturally; otherwise `truncated` so nothing is overstated.
  * hard budget guard: stop when quota drops below BUDGET_KEEP.
"""
import json, os, time
import requests

KEY = os.environ["SERPAPI_KEY"]
ENRICHED = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
OUT_FILE = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
STATE = "/home/agentuser/.hermes/cache/scratch/serp_p3_state.json"
MAX_PAGES = 3
BUDGET_KEEP = 8          # leave this many searches unused
BASE = "https://serpapi.com/search.json"

def search(s, params):
    r = None
    for t in range(3):
        try:
            r = s.get(BASE, params={**params, "api_key": KEY}, timeout=60)
            if r.status_code == 200:
                return r.json()
            time.sleep(2 + t * 3)
        except Exception:
            time.sleep(2)
    return {"_error": f"HTTP {r.status_code if r is not None else 'net'}"}

def spent(s):
    try:
        d = s.get("https://serpapi.com/account", params={"api_key": KEY}, timeout=30).json()
        return 250 - d.get("plan_searches_left", 0)
    except Exception:
        return None

def main():
    places = json.load(open(ENRICHED))
    dates = json.load(open(OUT_FILE)) if os.path.exists(OUT_FILE) else {}
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"used": 0}

    todo = [p for p in places
            if p.get("review_count") is not None
            and not (dates.get(p["pid"], {}).get("oldest_review"))]
    todo.sort(key=lambda p: p["review_count"])          # cheapest first
    print(f"todo: {len(todo)} places (count range {todo[0]['review_count']}..{todo[-1]['review_count']})", flush=True)

    s = requests.Session()
    used = state.get("used", 0)
    for i, p in enumerate(todo, 1):
        if used >= 250 - BUDGET_KEEP:
            print(f"BUDGET REACHED ({used} searches)", flush=True)
            break
        pid = p["pid"]
        rec = {"oldest_review": None, "newest_review": None,
               "pages_fetched": 0, "confirmed": False, "status": "pending",
               "review_count_at_fetch": p["review_count"]}
        token, best_oldest, newest0 = None, None, None
        exhausted = False
        for page in range(MAX_PAGES):
            params = {"engine": "google_maps_reviews", "place_id": pid,
                      "sort_by": "newestFirst", "hl": "en"}
            if page > 0:
                params["num"] = 20          # up to 20/page after the first
            if token:
                params["next_page_token"] = token
            d = search(s, params)
            used += 1
            if "_error" in d:
                rec["status"] = f"err:{d['_error']}"; break
            if "error" in d:
                print(f"SERPAPI ERR: {d['error'][:110]}", flush=True)
                exhausted = True; break
            revs = d.get("reviews", [])
            rec["pages_fetched"] += 1
            if page == 0 and revs:
                newest0 = revs[0].get("iso_date")
            if revs:
                ld = revs[-1].get("iso_date")
                if ld and (best_oldest is None or ld < best_oldest):
                    best_oldest = ld
            nxt = (d.get("serpapi_pagination") or {}).get("next_page_token")
            if not nxt or not revs:
                exhausted = True
                break
            token = nxt
            time.sleep(0.3)
        rec["oldest_review"] = best_oldest
        rec["newest_review"] = newest0
        rec["confirmed"] = bool(exhausted and best_oldest)
        rec["status"] = ("ok" if best_oldest else "nodates") + ("" if rec["confirmed"] else "|truncated")
        dates[pid] = rec
        if i % 5 == 0:
            json.dump(dates, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
            state["used"] = used
            json.dump(state, open(STATE, "w"))
            conf = sum(1 for v in dates.values() if isinstance(v, dict) and v.get("confirmed"))
            print(f"[{i}/{len(todo)}] used={used} | {p['name'][:26]} oldest={best_oldest} confirmed={rec['confirmed']} | total confirmed={conf}", flush=True)
        time.sleep(0.25)

    json.dump(dates, open(OUT_FILE, "w"), ensure_ascii=False, indent=1)
    state["used"] = used
    json.dump(state, open(STATE, "w"))
    ok = sum(1 for v in dates.values() if isinstance(v, dict) and v.get("oldest_review"))
    conf = sum(1 for v in dates.values() if isinstance(v, dict) and v.get("confirmed"))
    print(f"DONE: used={used} searches | {ok} with oldest date | {conf} confirmed", flush=True)

if __name__ == "__main__":
    main()
