#!/usr/bin/env python3
"""Intercept FULL search responses dgn typed search (app-driven)."""
import json, os, time
from playwright.sync_api import sync_playwright

OUT = "/home/agentuser/.hermes/cache/scratch/grab_search_full2.json"
data = json.load(open(OUT)) if os.path.exists(OUT) else {}
data.setdefault("queries", {})
done = set(data["queries"].keys())
QUERIES = json.load(open('/home/agentuser/.hermes/cache/scratch/grab_sweep_queries.json'))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", locale="id-ID")
    page = ctx.new_page()
    ctx.add_cookies([{"name": "location", "value": json.dumps({"latitude": -8.6538, "longitude": 115.1385, "address": "Canggu", "countryCode": "ID", "isAccurate": True, "addressDetail": "", "noteToDriver": "", "city": "", "cityID": 0, "displayAddress": ""}), "domain": ".grab.com", "path": "/"}])
    resps = []
    def on_resp(r):
        if "guest/v2/search" in r.url:
            try: resps.append(r.text())
            except: pass
    page.on("response", on_resp)
    page.goto("https://food.grab.com/id/en/search", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(10000)
    for q in QUERIES:
        if q in done: continue
        resps.clear()
        inp = None
        for attempt in range(3):
            for i in page.query_selector_all("input"):
                if i.is_visible(): inp = i; break
            if inp: break
            page.reload(timeout=60000, wait_until="domcontentloaded"); page.wait_for_timeout(9000)
        if not inp:
            print(q, "NO INPUT, reload next", flush=True); continue
        try:
            inp.click(); page.keyboard.press("Control+A")
            inp.type(q, delay=40)
            page.keyboard.press("Enter")
            page.wait_for_timeout(8000)
            merchants = []
            for b in resps:
                try:
                    j = json.loads(b)
                    merchants += j.get("searchResult", {}).get("searchMerchants", [])
                except: pass
            data["queries"][q] = merchants
            done.add(q)
            json.dump(data, open(OUT, "w"))
            print(f"[{len(done)}/{len(QUERIES)}] {q}: {len(merchants)}", flush=True)
        except Exception as e:
            print(q, "ERR", str(e)[:80], flush=True)
        time.sleep(1)
    browser.close()
print("DONE", flush=True)
