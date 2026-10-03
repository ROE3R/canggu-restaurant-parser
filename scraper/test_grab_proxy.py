#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, proxy={"server":"http://proxy.hypeproxy.site:1012"})
    pg = b.new_page()
    try:
        pg.goto("https://food.grab.com/id/en/restaurants?search=canggu",
                wait_until="domcontentloaded", timeout=80000)
        pg.wait_for_timeout(9000)
        ss = pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")
        d = json.loads(ss)
        cands = {k: v for k, v in d.items() if v and v.count(".")==2 and len(v)>100}
        print("tokens:", list(cands.keys()), [len(v) for v in cands.values()])
        print("title:", pg.title()[:60])
    except Exception as e:
        print("ERR:", str(e)[:150])
    b.close()
