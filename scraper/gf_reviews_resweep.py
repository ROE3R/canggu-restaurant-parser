#!/usr/bin/env python3
"""Re-sweep gofood reviews for all valid gofood_url in final CSV."""
import csv, json, os, sys, threading
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/agentuser/canggu-restaurant-parser"
OUT = ROOT + "/output/gf_reviews2.jsonl"
LOCK = threading.Lock()
KEY = open(ROOT+"/.env").read().split("BD_API_KEY=")[1].splitlines()[0]
import requests
TOK = json.load(open("/home/agentuser/.hermes/cache/scratch/harvested_tokens.json"))["gojek_sso_jwe"]

def bd(url):
    for _ in range(2):
        try:
            r = requests.post("https://api.brightdata.com/request", headers={"Authorization":"Bearer "+KEY},
              json={"zone": pipeline.BD_ZONE, "url": url, "format": "raw",
                    "headers": {"Authorization": "Bearer "+TOK}}, timeout=90)
            if r.status_code == 200 and r.text.strip():
                return r.text
        except Exception:
            pass
    return None

def work(row):
    url = row["gofood_url"]
    uid = pipeline.gofood_uid(url)
    if not uid: return
    txt = bd(f"https://gofood.co.id/api/outlets/{uid}/reviews-overview")
    rec = {"uid": uid, "name": row["name"], "ok": False}
    if txt:
        try:
            j = json.loads(txt)
            data = (j.get("reviews") or {}).get("data", [])
            dates = [x.get("createdAt") for x in data if x.get("createdAt")]
            rec.update(ok=True, n_reviews=len(data),
                       newest=max(dates)[:10] if dates else None,
                       oldest=min(dates)[:10] if dates else None,
                       samples=[{"date": x.get("createdAt","")[:10], "rating": x.get("rating"),
                                 "text": (x.get("text") or "")[:150]}
                                for x in data if x.get("text")][:3])
        except Exception:
            pass
    with LOCK:
        with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
        n = sum(1 for _ in open(OUT))
    print(f"[{n}] {'OK '+str(rec.get('n_reviews')) if rec['ok'] else 'FAIL'} | {row['name'][:38]}", flush=True)

rows = list(csv.DictReader(open(ROOT+"/output/canggu_restaurants.csv", encoding="utf-8")))
targets = [r for r in rows if (r["gofood_url"] or "").strip()]
print(f"reviews re-sweep: {len(targets)} rows", flush=True)
with ThreadPoolExecutor(16) as ex:
    list(ex.map(work, targets))
print("RESWEEP DONE", flush=True)
