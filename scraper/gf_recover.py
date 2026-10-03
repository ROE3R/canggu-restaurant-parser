#!/usr/bin/env python3
"""Recover v2: fast DDG search (8w) + parallel outlet fetch (6w). Resume-safe."""
import csv, json, os, re, sys, threading, urllib.parse, queue
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/agentuser/canggu-restaurant-parser"
OUT = ROOT + "/output/gf_recover.jsonl"
LOCK = threading.Lock()
KEY = open(ROOT+"/.env").read().split("BD_API_KEY=")[1].splitlines()[0]

import requests
def bd(url, timeout=90):
    for _ in range(2):
        try:
            r = requests.post("https://api.brightdata.com/request", headers={"Authorization":"Bearer "+KEY},
              json={"zone": pipeline.BD_ZONE, "url": url, "format": "raw"}, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                return r.text
        except Exception:
            pass
    return None

def ddg_search(name):
    q = urllib.parse.quote(f"site:gofood.co.id {name[:45]} canggu")
    t = bd(f"https://html.duckduckgo.com/html/?q={q}")
    if not t: return []
    links = re.findall(r'gofood\.co\.id/(?:id/)?bali/restaurant/[a-z0-9\-]+-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', t)
    seen, out = set(), []
    for l in links:
        u = "https://" + l.replace("/en/", "/").replace(":443", "")
        if u not in seen: seen.add(u); out.append(u)
    return out[:3]

def fetch_outlet(url):
    html = pipeline.bd_fetch(url)
    o = pipeline.parse_next_data(html) if html else None
    if o:
        core = o.get("core") or {}
        rtg = o.get("ratings") or {}
        return {"official_name": core.get("displayName"),
                "rating": rtg.get("average"), "votes": rtg.get("total"),
                "since": (core.get("createTime") or "")[:10] or None}
    return None

def save(rec):
    with LOCK:
        with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
        n = sum(1 for _ in open(OUT))
    print(f"[{n}] {'FOUND '+rec['found']['official_name'][:32] if rec.get('found') else 'NOT FOUND'} | {rec['name'][:38]}", flush=True)

# --- targets
rows = list(csv.DictReader(open(ROOT+"/output/canggu_restaurants.csv", encoding="utf-8")))
done = set()
if os.path.exists(OUT):
    for line in open(OUT):
        try: done.add(json.loads(line)["idx"])
        except Exception: pass
targets = [(i, r["name"]) for i, r in enumerate(rows)
           if not (r["gofood_url"] or "").strip()
           and ("re-check" in (r["data_notes"] or "") or "not_found_on_gofood" in (r["data_notes"] or ""))
           and i not in done]
print(f"recover v2: {len(targets)} rows", flush=True)

results_q = queue.Queue()

def searcher(item):
    idx, name = item
    cands = ddg_search(name)
    results_q.put((idx, name, cands))

# fase 1: search paralel 8 worker
with ThreadPoolExecutor(8) as ex:
    list(ex.map(searcher, targets))

# fase 2: fetch outlet paralel 6 worker
def fetcher(item):
    idx, name, cands = item
    rec = {"idx": idx, "name": name, "found": None}
    for u in cands:
        d = fetch_outlet(u)
        if d and d.get("official_name"):
            rec["found"] = {"url": u, **d}
            break
    save(rec)

while not results_q.empty():
    batch = [results_q.get() for _ in range(min(12, results_q.qsize()))]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(fetcher, batch))
print("RECOVER DONE", flush=True)
