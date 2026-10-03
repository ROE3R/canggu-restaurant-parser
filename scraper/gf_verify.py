#!/usr/bin/env python3
"""Verify all gofood_url matches: fetch page, extract official displayName, compare."""
import json, os, re, sys, threading
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/agentuser/canggu-restaurant-parser"
OUT = ROOT + "/output/gf_verify.jsonl"
LOCK = threading.Lock()

def done():
    d = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try: d.add(json.loads(line)["uid"])
            except Exception: pass
    return d

def work(row_url_name):
    name, url = row_url_name
    url = url.replace(":443", "")
    if not url.startswith("http"): url = "https://" + url.replace("/en/", "/").replace("/english/", "/").replace("/id/bali/", "/bali/")
    uid = pipeline.gofood_uid(url)
    html = pipeline.bd_fetch(url)
    outlet = pipeline.parse_next_data(html) if html else None
    if outlet:
        core = outlet.get("core") or {}
        rec = {"uid": uid, "url": url, "maps_name": name,
               "official_name": core.get("displayName"), "ok": True}
    else:
        import re as _re
        m = _re.search(r'"errorCode":\s*(\d+)', html or "")
        rec = {"uid": uid, "url": url, "maps_name": name, "official_name": None,
               "ok": False, "error": "errorCode "+m.group(1) if m else "no_data"}
    with LOCK:
        with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
        print(f"[{len(done())}] {name[:35]} -> {rec.get('official_name') or rec.get('error')}", flush=True)

import csv
rows = list(csv.DictReader(open(ROOT+"/output/canggu_restaurants.csv", encoding="utf-8")))
targets = [(r["name"], r["gofood_url"]) for r in rows if r.get("gofood_url")]
todo = [(n,u) for n,u in targets if pipeline.gofood_uid(u) not in done()]
print(f"verify: {len(todo)} targets", flush=True)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, todo))
print("VERIFY DONE", flush=True)
