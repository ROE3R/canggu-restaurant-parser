#!/usr/bin/env python3
"""Verify each maps_name exists in GoFood POI (serviceable in Bali area)."""
import json, os, sys, threading, csv, urllib.parse
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/agentuser/canggu-restaurant-parser"
OUT = ROOT + "/output/gf_poi.jsonl"
LOCK = threading.Lock()

def done():
    d = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try: d.add(json.loads(line)["name"])
            except Exception: pass
    return d

def work(name_latlng):
    name, lat, lng = name_latlng
    q = f"https://gofood.co.id/api/poi/search?keyword={urllib.parse.quote(name[:60])}&latitude={lat}&longitude={lng}"
    txt = pipeline.bd_fetch(q)  # render=False path? bd_fetch default render True -> override
    # use direct BD call without render:
    import requests
    key = open(ROOT+"/.env").read().split("BD_API_KEY=")[1].splitlines()[0]
    try:
        r = requests.post("https://api.brightdata.com/request", headers={"Authorization":"Bearer "+key},
          json={"zone": pipeline.BD_ZONE, "url": q, "format": "raw"}, timeout=90)
    except requests.RequestException:
        with LOCK:
            print(f"TIMEOUT {name[:40]}", flush=True)
        return
    rec = {"name": name, "ok": False}
    try:
        j = json.loads(r.text)
        hits = j if isinstance(j, list) else []
        rec["ok"] = True
        rec["matches"] = [{"name": h.get("name"), "place_id": h.get("place_id"),
                           "address": h.get("address"), "serviceable": h.get("is_serviceable")}
                          for h in hits[:3]]
    except Exception:
        rec["error"] = "bad_response"
    with LOCK:
        with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
        print(f"[{len(done())}] {'OK' if rec['ok'] else 'ERR'} {name[:40]}", flush=True)

rows = list(csv.DictReader(open(ROOT+"/output/canggu_restaurants.csv", encoding="utf-8")))
targets = [(r["name"], r["latitude"], r["longitude"]) for r in rows if r.get("name")]
todo = [t for t in targets if t[0] not in done()]
print(f"poi verify: {len(todo)} targets", flush=True)
with ThreadPoolExecutor(8) as ex:
    list(ex.map(work, todo))
print("POI DONE", flush=True)
