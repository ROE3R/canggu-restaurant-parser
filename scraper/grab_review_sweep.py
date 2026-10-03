#!/usr/bin/env python3
"""Grab review sweep via guest API + passenger_authn_token cookie.
Usage: GRAB_AUTH_COOKIE="passenger_authn_token=...; grabid-openid-authn-ck=..." python grab_review_sweep.py"""
import os, json, time, random, sys

REPO = "/home/agentuser/canggu-restaurant-parser"
MIDS = json.load(open("/tmp/grab_mids.json"))
OUT = f"{REPO}/output/grab_reviews.jsonl"

def load_done():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try: done.add(json.loads(line)["mid"])
            except Exception: pass
    return done

def fetch(session, mid, zones):
    from playwright.sync_api import sync_playwright
    # gunakan pola terbukti: ISP proxy + browser; cookie login diset di context
    cookie_str = os.environ["GRAB_AUTH_COOKIE"]
    cookies = []
    for part in cookie_str.split(";"):
        if "=" in part:
            name, val = part.strip().split("=", 1)
            cookies.append({"name": name, "value": val, "domain": ".grab.com", "path": "/"})
    zn, pw = random.choice(zones)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, proxy={"server": "http://brd.superproxy.io:22225",
            "username": f"brd-customer-hl_a5c1cc91-zone-{zn}-session-revsw{random.randint(1000,9999)}",
            "password": pw}, args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
            viewport={"width": 1366, "height": 900}, locale="id-ID")
        if cookies: ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.goto(f"https://food.grab.com/id/en/restaurant/dummy/{mid}",
                wait_until="domcontentloaded", timeout=70000)
        pg.wait_for_timeout(12000)
        out = pg.evaluate("""async (mid) => {
            try {
                const r = await fetch(`/proxy/foodweb/guest/v2/merchants/${mid}/reviews?limit=50`,
                    {credentials:'include', headers:{'Accept':'application/json'}});
                return r.status + '|' + (await r.text());
            } catch(e) { return 'ERR|' + e.message; }
        }""", mid)
        b.close()
    return out

if __name__ == "__main__":
    if "GRAB_AUTH_COOKIE" not in os.environ:
        print("export GRAB_AUTH_COOKIE dulu"); sys.exit(1)
    zl = json.load(open("/tmp/new_zones.json"))
    done = load_done()
    todo = [m for m in MIDS if m not in done]
    print(f"todo: {len(todo)}/{len(MIDS)}")
    for i, mid in enumerate(todo[:3]):  # test 3 dulu
        res = fetch(None, mid, zl)
        st, body = res.split("|", 1)
        print(f"{i}: {mid} -> {st} len={len(body)}")
        if st == "200":
            with open(OUT, "a") as f:
                f.write(json.dumps({"mid": mid, "reviews": json.loads(body)}, ensure_ascii=False) + "\n")
        time.sleep(random.uniform(20, 40))
