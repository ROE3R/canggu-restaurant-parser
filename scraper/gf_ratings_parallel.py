#!/usr/bin/env python3
"""Parallel GoFood ratings sweep — 6 workers, resume-safe."""
import json, os, re, sys, threading, time
sys.path.insert(0, "/home/agentuser/canggu-restaurant-parser")
import pipeline
from concurrent.futures import ThreadPoolExecutor

ROOT = "/home/agentuser/canggu-restaurant-parser"
OUT = ROOT + "/output/gf_ratings.jsonl"
LOCK = threading.Lock()

def done_uids():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                rec = json.loads(line)
                if rec.get("ok"): done.add(rec["uid"])
            except Exception: pass
    return done

def work(url):
    uid = pipeline.gofood_uid(url)
    html = pipeline.bd_fetch(url)
    outlet = pipeline.parse_next_data(html) if html else None
    if outlet:
        core = outlet.get("core") or {}
        rtg = outlet.get("ratings") or {}
        rec = {"uid": uid, "url": url, "ok": True,
               "name": core.get("displayName"),
               "rating": rtg.get("average"), "votes": rtg.get("total"),
               "since": (core.get("createTime") or "")[:10] or None}
    else:
        rec = {"uid": uid, "url": url, "ok": False, "error": "closed_or_fail"}
    with LOCK:
        with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False)+"\n")
        n = len(done_uids())
        print(f"[{n}] {'OK' if rec['ok'] else 'FAIL'} | {rec.get('name') or url[:40]}", flush=True)

targets = json.load(open(ROOT+"/output/targets.json"))
todo = [u for u in targets if pipeline.gofood_uid(u) not in done_uids()]
print(f"parallel sweep: {len(todo)} targets, 6 workers", flush=True)
with ThreadPoolExecutor(6) as ex:
    list(ex.map(work, todo))
print("SWEEP DONE", flush=True)
