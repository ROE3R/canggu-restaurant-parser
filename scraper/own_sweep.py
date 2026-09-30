#!/usr/bin/env python3
"""OpenWeb Ninja sweep - oldest review dates for remaining places.
Pass 1: 1 request/place (newest date for all remaining).
Pass 2: deep-walk smallest-count places (confirmed oldest) until quota low.
Resumable. Env: OWN_KEY
"""
import json, os, time, math
import requests

KEY = os.environ["OWN_KEY"]
BASE = "https://api.openwebninja.com/local-business-data/business-reviews-v2"
PLACES = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
RDATES = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
STATE = "/home/agentuser/.hermes/cache/scratch/own_state.json"
USED = "/home/agentuser/.hermes/cache/scratch/own_used.json"
MIN_QUOTA = 40

s = requests.Session()
s.headers["x-api-key"] = KEY

def get_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {"pass1_done": False}

def save_dates(rd):
    json.dump(rd, open(RDATES, "w"), ensure_ascii=False, indent=1)

def fetch_page(bid, cursor=None, sort_by="newest", limit=20):
    params = {"business_id": bid, "sort_by": sort_by, "limit": limit, "language": "en"}
    if cursor:
        params["cursor"] = cursor
    for t in range(5):
        try:
            r = s.get(BASE, params=params, timeout=90)
            if r.status_code == 200:
                return r.json(), True
            time.sleep(5 + t * 8)
        except Exception:
            time.sleep(2)
    return None, False

def count_credits():
    # we track ourselves; assume 1 credit per request
    st = json.load(open(USED)) if os.path.exists(USED) else {"requests": 0}
    return st

def bump(st):
    st["requests"] += 1
    json.dump(st, open(USED, "w"))

def main():
    places = json.load(open(PLACES))
    rd = json.load(open(RDATES))
    state = get_state()
    # map name+addr -> business_id not needed; we use ftid (cid pair) stored per place
    todo = [p for p in places
            if p.get("review_count") is not None
            and p.get("cid")
            and not (isinstance(rd.get(p["pid"]), dict)
                     and (rd[p["pid"]].get("oldest_review")
                          or (rd[p["pid"]].get("newest_review") and rd[p["pid"]].get("source") == "openwebninja"))) ]
    todo.sort(key=lambda p: p["review_count"])
    print(f"todo: {len(todo)}", flush=True)

    used = count_credits()

    # PASS 1: newest date for all (1 req each)
    if not state["pass1_done"]:
        for i, p in enumerate(todo, 1):
            if used["requests"] >= 500 - MIN_QUOTA:
                print("BUDGET STOP pass1"); break
            d, ok = fetch_page(p["cid"], limit=20)
            bump(used)
            if not ok:
                print(f"[{i}] {p['name'][:24]} FETCH FAIL", flush=True); continue
            revs = d["data"]["reviews"]
            rec = rd.setdefault(p["pid"], {"oldest_review": None, "newest_review": None,
                                           "confirmed": False, "status": "pending"})
            if revs:
                rec["newest_review"] = revs[0].get("review_datetime_utc")
                rec["oldest_review"] = revs[-1].get("review_datetime_utc")  # partial page
                rec["status"] = "newest_ok|oldest_partial"
                rec["pages_fetched"] = 1
                rec["source"] = "openwebninja"
            else:
                rec["status"] = "noreviews"
                rec["source"] = "openwebninja"
            if i % 20 == 0:
                save_dates(rd)
                print(f"[{i}/{len(todo)}] pass1 ok, used={used['requests']}", flush=True)
            time.sleep(4.0)
        save_dates(rd)
        state["pass1_done"] = True
        json.dump(state, open(STATE, "w"))

    # PASS 2: deep-walk smallest for confirmed oldest
    todo2 = [p for p in places
             if p.get("review_count") is not None
             and p.get("cid")
             and not (isinstance(rd.get(p["pid"]), dict) and rd[p["pid"]].get("confirmed"))]
    todo2.sort(key=lambda p: p["review_count"])
    print(f"pass2 targets: {len(todo2)}", flush=True)
    for i, p in enumerate(todo2, 1):
        if used["requests"] >= 500 - MIN_QUOTA:
            print("BUDGET STOP pass2"); break
        pages = 0
        cursor = None
        oldest, newest = None, None
        while True:
            d, ok = fetch_page(p["cid"], cursor=cursor)
            bump(used)
            if not ok:
                break
            pages += 1
            revs = d["data"]["reviews"]
            if pages == 1 and revs:
                newest = revs[0].get("review_datetime_utc")
            if revs:
                ld = revs[-1].get("review_datetime_utc")
                if ld and (oldest is None or ld < oldest):
                    oldest = ld
            cursor = d["data"].get("cursor")
            if not cursor or not revs:
                break
        rec = rd.setdefault(p["pid"], {})
        rec.update({"oldest_review": oldest, "newest_review": newest,
                    "confirmed": bool(oldest), "pages_fetched": pages,
                    "status": "ok" if oldest else "walk_failed",
                    "source": "openwebninja"})
        save_dates(rd)
        print(f"[{i}] {p['name'][:26]} rc={p['review_count']} pages={pages} oldest={oldest} used={used['requests']}", flush=True)
        time.sleep(4.0)

    save_dates(rd)
    ok = sum(1 for v in rd.values() if isinstance(v, dict) and v.get("oldest_review"))
    conf = sum(1 for v in rd.values() if isinstance(v, dict) and v.get("confirmed"))
    print(f"DONE used={used['requests']} | oldest={ok} confirmed={conf}", flush=True)

if __name__ == "__main__":
    main()
