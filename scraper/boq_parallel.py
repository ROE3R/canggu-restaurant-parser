#!/usr/bin/env python3
"""BOQ parallel: N workers in threads, each with own random NID, sharded todo."""
import os, sys, json, time, random, string, urllib.parse, datetime, threading, requests

WORKERS = int(os.environ.get("BOQ_WORKERS", "23"))
RD_F = "/home/agentuser/.hermes/cache/scratch/review_dates.boq.json"
PL_F = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
BASE = "https://www.google.com/httpservice/web/PrivateLocalSearchUiDataService/GetLocalBoqProxy"

def new_nid():
    return "".join(random.choices(string.ascii_letters + string.digits + "-_", k=132))

rd = json.load(open(RD_F)) if os.path.exists(RD_F) else {}
places = json.load(open(PL_F))
# hanya resto yang ada di CSV (401)
import csv
csv_pids = {r["google_place_id"] for r in csv.DictReader(open("/home/agentuser/canggu-restaurant-parser/output/canggu_restaurants.csv"))}
need = []
for p in places:
    pid = p["pid"]
    if pid in csv_pids and p.get("review_count") and not (rd.get(pid) or {}).get("oldest_review"):
        fid = p.get("cid")
        if fid and str(fid).startswith("0x"):
            need.append((pid, p.get("review_count", 0), fid))
need.sort(key=lambda x: x[1])
# round-robin ke worker queues
queues = [[] for _ in range(WORKERS)]
for j, x in enumerate(need):
    queues[j % WORKERS].append(x)
print(f"todo: {len(need)} across {WORKERS} workers", flush=True)

lock = threading.Lock()
results = {"ok": 0, "fail": 0}

def ts_date(ms):
    return datetime.datetime.utcfromtimestamp(int(ms) / 1000).date().isoformat()

def fetch(fid, nid, tok=None):
    if tok:
        inner = [None, 2] + [None]*7 + [None, None, [fid]] + [None]*7 + [tok]
    else:
        inner = [None, 2] + [None]*7 + [20, None, [fid]]
    reqpld = [None, [None]*9 + [inner]]
    url = BASE + "?msc=gwsrpc&reqpld=" + urllib.parse.quote(json.dumps(reqpld))
    for attempt in range(15):
        r = requests.get(url, headers={"Cookie": f"NID={nid()}" if callable(nid) else f"NID={nid}",
                                       "Referer": "https://www.google.com/maps/"}, timeout=60)
        body = r.text.strip()
        if r.status_code == 429 or not body.startswith(")]}'"):
            time.sleep(1.0)
            continue  # rotate NID (callable) & retry
        body = body[4:]
        return json.loads(body)
    raise RuntimeError("429 x15")

def worker(wi, q):
    global results
    for pi, (pid, rcount, fid) in enumerate(q):
        tok, oldest, newest, pages, ok = None, None, None, 0, False
        try:
            while pages < 2600:
                d = fetch(fid, new_nid, tok)
                b = d[1][10]
                revs = b[2] or []
                if revs:
                    if newest is None: newest = ts_date(revs[0][2][2])
                    oldest = ts_date(revs[-1][2][2])
                pages += 1
                tok = b[6] if len(b) > 6 and b[6] else None
                if not tok or not revs:
                    ok = True
                    break
                time.sleep(0.5)
        except Exception as e:
            with lock:
                results["fail"] += 1
            print(f"[w{wi}] {pid[:20]} FAIL {e}", flush=True)
            continue
        with lock:
            rec = rd.get(pid) or {}
            if newest: rec["newest_review"] = newest
            if ok and oldest:
                rec["oldest_review"] = oldest
                rec["status"] = "confirmed"
                rec["source"] = "boq"
                results["ok"] += 1
            rd[pid] = rec
            if results["ok"] % 10 == 0:
                json.dump(rd, open(RD_F, "w"))
        print(f"[w{wi}] {pid[:20]} pages={pages} oldest={oldest} confirmed={ok}", flush=True)

threads = [threading.Thread(target=worker, args=(i, q), daemon=True) for i, q in enumerate(queues) if q]
for t in threads: t.start()
for t in threads: t.join()
json.dump(rd, open(RD_F, "w"))
print("DONE", results, flush=True)
