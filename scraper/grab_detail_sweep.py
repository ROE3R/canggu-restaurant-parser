#!/usr/bin/env python3
"""GrabFood per-merchant detail sweep via Playwright (guest, real browser)."""
import json, os, time, sys
from playwright.sync_api import sync_playwright

OUT = "/home/agentuser/.hermes/cache/scratch/grab_details.json"
IDS = json.load(open('/home/agentuser/.hermes/cache/scratch/grab_detail_ids.json'))
SHARD = os.environ.get("GRAB_SHARD")
if SHARD:
    i, n = map(int, SHARD.split("/"))
    IDS = [x for j, x in enumerate(IDS) if j % n == i]

details = json.load(open(OUT)) if os.path.exists(OUT) else {}
todo = [x for x in IDS if x not in details]
print(f"todo: {len(todo)}", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", locale="id-ID")
    page = ctx.new_page()
    latest = {}
    def on_resp(r):
        if "guest/v2/merchants/" in r.url and r.status == 200:
            try: latest["data"] = r.json()
            except: pass
    page.on("response", on_resp)

    slugmap = json.load(open('/home/agentuser/.hermes/cache/scratch/grab_slugmap.json'))
    for n, gid in enumerate(todo):
        url = slugmap.get(gid)
        if not url:
            continue
        latest.clear()
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            if "data" in latest:
                details[gid] = latest["data"]
            else:
                details[gid] = {"_err": "no_response", "url": url}
        except Exception as e:
            details[gid] = {"_err": str(e)[:120], "url": url}
        if (n+1) % 10 == 0:
            json.dump(details, open(OUT, "w"))
            print(f"[{n+1}/{len(todo)}] ok={sum(1 for v in details.values() if '_err' not in v)}", flush=True)
        time.sleep(1.5)
    json.dump(details, open(OUT, "w"))
    print("DONE", len(details), flush=True)
