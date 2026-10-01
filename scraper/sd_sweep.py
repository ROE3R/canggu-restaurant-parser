#!/usr/bin/env python3
"""Scrape.do reviews sweep - oldest_review_date for remaining places.
Resumable. Uses SD_TOKENS env (comma-separated). sort_by=newest, paginate num=20
until last page -> oldest confirmed. Budget-guarded per token (credits=10/call).
"""
import os, sys, json, time, requests

TOKENS = [t.strip() for t in os.environ.get("SD_TOKENS", "").split(",") if t.strip()]
if not TOKENS:
    sys.exit("SD_TOKENS env required (comma-separated)")
BASE = "https://api.scrape.do/plugin/google/maps/reviews"
STATE_F = os.path.join(os.path.dirname(__file__), "..", "scratch_sd_state.json")
RD_F = "/home/agentuser/.hermes/cache/scratch/review_dates.json"
PL_F = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
CALLS_PER_TOKEN = int(os.environ.get("SD_BUDGET", "90"))  # 1000 credits / 10 = 100, margin

state = json.load(open(STATE_F)) if os.path.exists(STATE_F) else {"calls": {}}
SHARD = os.environ.get("SD_SHARD")  # e.g. "0/4"
RD_F = RD_F.replace(".json", f".shard{SHARD.replace('/', '_')}.json") if SHARD else RD_F
rd = json.load(open(RD_F)) if os.path.exists(RD_F) else {}
places = json.load(open(PL_F))
need = []
for p in places:
    pid = p["pid"]
    v = rd.get(pid, {})
    if p.get("review_count") and not (v or {}).get("oldest_review"):
        cand = p.get("cid") or p.get("ftid") or p.get("data_id")
        need.append((pid, p.get("review_count", 0), cand))
need.sort(key=lambda x: x[1])  # cheapest first
if SHARD:
    i, n = map(int, SHARD.split("/"))
    need = [x for j, x in enumerate(need) if j % n == i]
print(f"todo: {len(need)}")
if not need:
    sys.exit("nothing to do")

tok_idx = 0
for pi, (pid, rcount, ftid) in enumerate(need):
    if not ftid or not str(ftid).startswith("0x"):
        print(f"[{pi}] {pid[:20]} SKIP no ftid ({ftid})")
        continue
    tok = TOKENS[tok_idx % len(TOKENS)]
    used = state["calls"].get(tok, 0)
    if used >= CALLS_PER_TOKEN:
        tok_idx += 1
        if tok_idx >= len(TOKENS):
            print("ALL TOKEN BUDGET EXHAUSTED")
            break
        tok = TOKENS[tok_idx % len(TOKENS)]
        used = state["calls"].get(tok, 0)
    # paginate newest -> last page = oldest
    nxt, oldest, newest, pages = None, None, None, 0
    ok = False
    while True:
        params = {"token": tok, "data_id": ftid, "num": 20, "sort_by": "newest"}
        if nxt:
            params["next_page_token"] = nxt
        try:
            r = requests.get(BASE, params=params, timeout=120)
        except Exception as e:
            print(f"[{pi}] {pid[:24]} FETCH FAIL {e}")
            break
        used += 1
        state["calls"][tok] = used
        if r.status_code == 429:
            print(f"[{pi}] 429 on tok{tok_idx%len(TOKENS)+1} used={used}")
            tok_idx += 1
            if tok_idx >= len(TOKENS):
                print("ALL TOKENS 429/EXHAUSTED")
                break
            continue
        if r.status_code != 200:
            print(f"[{pi}] HTTP {r.status_code} {r.text[:80]}")
            break
        try:
            d = r.json()
        except Exception:
            print(f"[{pi}] bad json")
            break
        revs = d.get("reviews") or []
        if revs:
            if newest is None:
                newest = revs[0].get("iso_date")
            oldest = revs[-1].get("iso_date")
        pages += 1
        nxt = (d.get("pagination") or {}).get("next_page_token")
        if not nxt or pages > 60:  # 60*20=1200 reviews cap
            ok = True
            break
        time.sleep(0.3)
    # save
    rec = rd.get(pid) or {}
    if newest:
        rec["newest_review"] = newest
    if ok and oldest:
        # deepest page reached -> oldest confirmed
        rec["oldest_review"] = oldest
        rec["status"] = "confirmed"
        rec["source"] = "scrapedo"
    elif oldest and pages >= 2:
        rec["status"] = "approximate"
        rec["source"] = "scrapedo"
    rd[pid] = rec
    json.dump(rd, open(RD_F, "w"))
    json.dump(state, open(STATE_F, "w"))
    print(f"[{pi}] {pid[:24]} pages={pages} oldest={oldest} newest={newest} confirmed={ok} used={used}")
    time.sleep(0.3)
json.dump(state, open(STATE_F, "w"))
print("DONE")
