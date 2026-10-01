#!/usr/bin/env python3
"""BOQ sweep - GetLocalBoqProxy (Google internal, FREE, no API key).
Needs GOOGLE_NID env (NID cookie from a real browser). Paginates newest->last page = oldest confirmed.
Resumable via review_dates.boq shard file. 20 reviews/page, unlimited, just needs fresh NID if it dies.
"""
import os, sys, json, time, random, string, urllib.parse, datetime, requests

def new_nid():
    return "".join(random.choices(string.ascii_letters + string.digits + "-_", k=132))
NID = os.environ.get("GOOGLE_NID", "") or new_nid()
BASE = "https://www.google.com/httpservice/web/PrivateLocalSearchUiDataService/GetLocalBoqProxy"
SHARD = os.environ.get("BOQ_SHARD", "")
RD_F = "/home/agentuser/.hermes/cache/scratch/review_dates.boq.json"
if SHARD:
    RD_F = RD_F.replace(".json", f".s{SHARD.replace('/','_')}.json")
PL_F = "/home/agentuser/.hermes/cache/scratch/places_enriched.json"
HDRS = {"Cookie": f"NID={NID}", "Referer": "https://www.google.com/maps/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
MAX_PAGES = 300  # Google caps ~300 reviews via this endpoint per repo docs

rd = json.load(open(RD_F)) if os.path.exists(RD_F) else {}
places = json.load(open(PL_F))
need = []
for p in places:
    pid = p["pid"]
    if p.get("review_count") and not (rd.get(pid) or {}).get("oldest_review"):
        fid = p.get("cid")
        if fid and str(fid).startswith("0x"):
            need.append((pid, p.get("review_count", 0), fid))
need.sort(key=lambda x: x[1])  # cheapest first
if SHARD:
    _i, _n = map(int, SHARD.split("/"))
    need = [x for j, x in enumerate(need) if j % _n == _i]
print(f"todo: {len(need)}", flush=True)

def fetch(fid, tok=None):
    if tok:
        inner = [None, 2] + [None]*7 + [None, None, [fid]] + [None]*7 + [tok]
    else:
        inner = [None, 2] + [None]*7 + [20, None, [fid]]
    reqpld = [None, [None]*9 + [inner]]
    url = BASE + "?msc=gwsrpc&reqpld=" + urllib.parse.quote(json.dumps(reqpld))
    global NID
    for attempt in range(12):
        r = requests.get(url, headers={**HDRS, "Cookie": f"NID={NID}"}, timeout=60)
        if r.status_code == 429:
            NID = new_nid()  # fresh identity = fresh quota
            time.sleep(1.0)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        break
    else:
        raise RuntimeError("429 x12")
    body = r.text.strip()
    if body.startswith(")]}'"):
        body = body[4:]
    return json.loads(body)

def ts_date(ms):
    return datetime.datetime.utcfromtimestamp(int(ms) / 1000).date().isoformat()

for pi, (pid, rcount, fid) in enumerate(need):
    tok, oldest, newest, pages = None, None, None, 0
    ok = False
    try:
        while pages < MAX_PAGES:
            d = fetch(fid, tok)
            b = d[1][10]
            revs = b[2] or []
            if revs:
                if newest is None:
                    newest = ts_date(revs[0][2][2])
                oldest = ts_date(revs[-1][2][2])
            pages += 1
            tok = b[6] if len(b) > 6 and b[6] else None
            if not tok or not revs:
                ok = True
                break
            time.sleep(0.4)
    except Exception as e:
        print(f"[{pi}] {pid[:22]} FAIL {e}", flush=True)
        # NID expired/blocked -> stop, save progress
        json.dump(rd, open(RD_F, "w"))
        sys.exit(f"STOPPED at {pi} ({e})")
    rec = rd.get(pid) or {}
    if newest:
        rec["newest_review"] = newest
    if ok and oldest:
        rec["oldest_review"] = oldest
        rec["status"] = "confirmed"
        rec["source"] = "boq"
    rd[pid] = rec
    if pi % 5 == 0 or ok:
        json.dump(rd, open(RD_F, "w"))
    print(f"[{pi}] {pid[:22]} pages={pages} oldest={oldest} newest={newest} confirmed={ok}", flush=True)
    time.sleep(0.4)
json.dump(rd, open(RD_F, "w"))
print("DONE", flush=True)
